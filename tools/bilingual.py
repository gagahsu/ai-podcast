"""英文版的翻譯核對稿：把英文腳本和中文腳本的台詞一句一句配對。不呼叫 API。

    py tools/bilingual.py episodes/en/ep01_moon_en.md    # 寫 build/ep01_moon_en.bilingual.txt

英文腳本 episodes/en/epNN_xxx_en.md 對應中文腳本 episodes/epNN_xxx.md。英文版是逐句翻譯：
兩邊（不含 [共用 …] 段落）的句數、說話的角色順序都要一樣，對不上就停下來列出第一個不同的地方，不猜。
聲音標記（<chuckle> 等）不放進對照稿。共用段落（開場、放鬆、咕咕爺爺登場）每集一樣，也不放。
對照稿是給使用者核對翻譯用的，不放進節目說明（節目說明只寫總結）。
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import generate_episode as g  # noqa: E402

EN_NAMES = {"旁白": "Narrator", "栗栗": "Lili", "棉棉": "Mumu", "咕咕爺爺": "Grandpa Gugu"}


def chinese_script(en_path):
    en_path = Path(en_path)
    if not en_path.stem.endswith("_en"):
        sys.exit(f"{en_path.name} 不是英文版腳本（檔名要以 _en 結尾）")
    return ROOT / "episodes" / f"{en_path.stem[:-3]}.md"


def clean(text, zh=False):
    """去掉聲音標記；中文再拿掉標記留下的空白（「咕咕爺爺，<chuckle> 為什麼」→「咕咕爺爺，為什麼」）。"""
    text = re.sub(r"\s+", " ", g.TAG_RE.sub("", text)).strip()
    return re.sub(r"(?<=[^\x00-\x7f]) | (?=[^\x00-\x7f])", "", text) if zh else text


def pair_lines(en_path, zh_path):
    """回傳 [(角色, 英文, 中文), ...]；句數或角色順序對不上就停下來。"""
    en = [it for it in g.parse_script(en_path) if it[0] == "line"]
    zh = [it for it in g.parse_script(zh_path) if it[0] == "line"]
    for n, (e, z) in enumerate(zip(en, zh), 1):
        if e[1] != z[1]:
            sys.exit(f"第 {n} 句的角色不同：英文是 {e[1]}「{clean(e[3])[:30]}」，中文是 {z[1]}「{clean(z[3], zh=True)[:20]}」。"
                     "英文版要逐句翻譯，句子順序跟中文版一樣")
    if len(en) != len(zh):
        sys.exit(f"句數不同：英文 {len(en)} 句、中文 {len(zh)} 句（不含共用段落）。英文版要逐句翻譯")
    return [(e[1], clean(e[3]), clean(z[3], zh=True)) for e, z in zip(en, zh)]


def bilingual_text(pairs):
    blocks = []
    for sp, en, zh in pairs:
        blocks.append(f"{EN_NAMES.get(sp, sp)}: {en}\n{sp}：{zh}")
    return "\n\n".join(blocks) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("script", help="英文版腳本（episodes/en/epNN_xxx_en.md）")
    args = ap.parse_args()
    zh_path = chinese_script(args.script)
    if not zh_path.exists():
        sys.exit(f"找不到對應的中文腳本 {zh_path}")
    text = bilingual_text(pair_lines(args.script, zh_path))
    out = Path("build") / f"{Path(args.script).stem}.bilingual.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"已輸出 {out}（{text.count(chr(10) + chr(10)) + 1} 句，英文版跟中文版逐句對得上）")


if __name__ == "__main__":
    main()
