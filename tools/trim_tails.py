"""找出句尾夾著「下一口氣」的句子，寫成人工切點檔，把它剪掉。不呼叫 API。

Gemini 一次念好幾句時，會在下一句之前吸一口氣（約跟說話一樣大聲，Whisper 常聽成「嗯」「是啊」）。
自動切句在句間的靜音下刀，這口氣常被分到上一句的句尾：念完、停一秒、突然一聲吸氣。
ep07 使用者試聽時聽到（像哈欠或喘氣），ep08 一集就有 7 句。

    py tools/trim_tails.py episodes/ep08_owl.md           # 只列出有問題的句子
    py tools/trim_tails.py episodes/ep08_owl.md --write   # 寫 build/segments/<批次>.cuts.txt

寫好之後用 `generate_episode.py <腳本> --offline` 重新組裝：人工切點一樣會逐句做語音辨識核對。

只剪「看得出來」的情況，分不清就不剪（多聽到一口氣沒關係，剪到台詞就糟了）：
- 辨識結果的最後一個字要跟台詞的最後一個字同音（確定 Whisper 有聽到句尾）。不比聲調：句尾的語氣詞
  常被寫成另一個字（ep08「好厲害喔」→「好厉害哦」，喔 o1、哦 o2）
- 最後一個字之後要先安靜下來（連續 QUIET_SEC 秒低於 QUIET_DB），之後才又出現大於 LOUD_DB 的聲音
- 那段聲音不能太長（MAX_BURST_SEC），太長可能是沒辨識到的台詞
- 台詞以聲音標記結尾（例如 <yawn>）的不碰：句尾的聲音可能就是它
已經有切點檔的批次只檢查、不改寫（可能是人工調過的）；共用片段（assets/shared/）不處理。
"""
import argparse
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import generate_episode as g  # noqa: E402

FRAME_SEC = 0.05
LOUD_DB = -35         # 句尾之後超過這個音量，算「又有聲音」
QUIET_DB = -50        # 低於這個音量算安靜
QUIET_SEC = 0.15      # 最後一個字之後，要連續安靜這麼久，才算念完
MIN_GAP_SEC = 0.3     # 念完到那段聲音之間至少要安靜這麼久
MAX_BURST_SEC = 1.5   # 那段聲音最長這麼久（ep08 實測 0.5–1.1 秒）
END_PAD_SEC = 0.1     # 句尾多留一點點
TAG_END_RE = re.compile(r"<[^>]+>\W*$")


def levels(audio):
    """每 FRAME_SEC 秒的音量（dBFS）。"""
    from array import array
    a = array("h", audio.pcm)
    n = int(audio.rate * FRAME_SEC)
    out = []
    for k in range(len(a) // n):
        frame = a[k * n:(k + 1) * n]
        rms = math.sqrt(sum(x * x for x in frame) / n)
        out.append(20 * math.log10(rms / 32768 + 1e-9))
    return out


def find_tail(audio, text, chars):
    """回傳 (新的句尾秒數, 說明)。不用剪或分不清時，秒數是 None；說明是 None 表示句尾乾淨。"""
    if TAG_END_RE.search(text):
        return None, None
    if not chars:
        return None, "辨識不到字，分不清句尾在哪"
    want = g._sounds(g._norm(text))
    heard = g._sounds(g._norm("".join(c for c, _, _ in chars)))
    if not want or not heard or want[-1].rstrip("012345") != heard[-1].rstrip("012345"):
        return None, "辨識結果的最後一個字跟台詞對不上，分不清句尾在哪"
    lv = levels(audio)
    need = round(QUIET_SEC / FRAME_SEC)
    k = int(chars[-1][2] / FRAME_SEC)
    while k + need <= len(lv) and not all(v < QUIET_DB for v in lv[k:k + need]):
        k += 1
    if k + need > len(lv):
        return None, None   # 念到最後都沒安靜下來：後面沒有別的聲音
    loud = [j for j in range(k, len(lv)) if lv[j] > LOUD_DB]
    if not loud:
        return None, None
    peak = max(lv[j] for j in loud)
    if (loud[-1] - loud[0] + 1) * FRAME_SEC > MAX_BURST_SEC:
        return None, f"句尾後的聲音長達 {(loud[-1] - loud[0] + 1) * FRAME_SEC:.1f} 秒，可能是沒辨識到的台詞"
    if (loud[0] - k) * FRAME_SEC < MIN_GAP_SEC:
        return None, "句尾跟後面的聲音之間沒有明顯的停頓"
    return k * FRAME_SEC + END_PAD_SEC, f"句尾後 {(loud[0] - k) * FRAME_SEC:.1f} 秒有一段聲音（峰 {peak:.0f} dB）"


def cuts_text(title, pieces, ends, rate):
    """pieces 的起點＋新句尾（None = 不改）→ 切點檔內容。"""
    changed = [n for n, e in enumerate(ends, 1) if e is not None]
    rows = [f"# {title}：自動切句的結果照抄，",
            f"# 第 {'、'.join(map(str, changed))} 句的句尾夾著下一口氣（大聲的吸氣聲），"
            "剪到最後一個字念完（tools/trim_tails.py）。"]
    for p, e in zip(pieces, ends):
        a = p.start / rate
        b = a + (e if e is not None else p.seconds)
        note = f"   # 原本到 {a + p.seconds:.3f}" if e is not None else ""
        rows.append(f"{a:.3f} {b:.3f}{note}")
    return "\n".join(rows) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("script")
    ap.add_argument("--write", action="store_true", help="寫入切點檔（預設只列出）")
    args = ap.parse_args()

    items, shared = g.expand_shared(g.parse_script(Path(args.script)))
    cache = Path("build/segments")
    line_idx = [i for i, it in enumerate(items) if it[0] == "line" and i not in shared]
    found_any = False
    for sp in dict.fromkeys(items[i][1] for i in line_idx):
        idxs = [i for i in line_idx if items[i][1] == sp]
        entries = [items[i][2:] for i in idxs]
        texts = [t for _, t in entries]
        _, _, path = g.batch_request(sp, entries, cache)
        if not path.exists():
            print(f"{sp}：還沒生成（{path.name} 不存在），略過")
            continue
        audio = g.Audio.load(path)
        cuts_path = path.with_suffix(".cuts.txt")
        manual = cuts_path.exists()
        if manual:
            pieces = g.manual_cuts(audio, cuts_path, len(entries))
        else:
            pieces, why, _ = g.auto_split(audio, texts, sp)
            if pieces is None:
                print(f"{sp}：自動切不開（{why}），先照 CLAUDE.md 處理切句")
                continue
        ends, noted = [], False
        for n, (piece, text) in enumerate(zip(pieces, texts), 1):
            if getattr(piece, "ear_checked", False):   # 「人耳確認」：使用者聽過、刻意這樣剪的
                ends.append(None)
                continue
            end, msg = find_tail(piece, text, g.transcribe_chars(piece))
            ends.append(end)
            if msg:
                found_any = noted = True
                act = f"剪到 {end:.2f} 秒（原本 {piece.seconds:.2f}）" if end is not None else "不剪，請用耳朵聽"
                print(f"{sp} 第 {n} 句「{text[:16]}」：{msg}，{act}")
        if not noted:
            print(f"{sp}：句尾都乾淨")
        if all(e is None for e in ends):
            continue
        if manual:
            print(f"  {sp} 已經有切點檔 {cuts_path.name}，不改寫；要剪請手動改上面那幾句的結束秒數")
        elif args.write:
            cuts_path.write_text(cuts_text(f"{Path(args.script).stem} {sp}", pieces, ends, audio.rate),
                                 encoding="utf-8")
            print(f"  已寫入 {cuts_path}")
    if found_any and args.write:
        print(f"\n接著執行：py generate_episode.py {args.script} --offline（人工切點會逐句核對內容）")
    elif found_any:
        print("\n加上 --write 寫入切點檔")


if __name__ == "__main__":
    main()
