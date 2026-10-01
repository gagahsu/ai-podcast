"""
為什麼森林：把腳本 .md 轉成一集 podcast 音檔（Gemini 3.8 TTS）。詳細說明見 README.md。

    py generate_episode.py episodes/ep01_moon.md --dry-run   # 只解析腳本，不呼叫 API
    py generate_episode.py episodes/ep01_moon.md --limit 5   # 只生成前 5 句試聽
    py generate_episode.py episodes/ep01_moon.md             # 生成整集到 build/
    py generate_episode.py episodes/ep01_moon.md --inspect   # 分析已生成的批次音檔（不花額度）

切句流程（分批模式）：靜音偵測 → 分不清就改用 Whisper 對齊腳本 → 還是不行就停下來。
"""

import argparse
import warnings
import base64
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from array import array
from functools import lru_cache
from pathlib import Path

warnings.filterwarnings("ignore", message="Interactions usage is experimental")

# Windows 的預設編碼（cp950）會讓中文訊息變亂碼，強制改用 UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# ---- 設定 ----------------------------------------------------------------

def load_env(path):
    """讀 KEY=VALUE 格式的 .env；已經在環境變數裡的不覆蓋（PowerShell 設的優先）。"""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (s.strip() for s in line.split("=", 1))
        if value[:1] in "\"'" and value[-1:] == value[:1] and len(value) > 1:
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()  # 允許行尾註解
        os.environ.setdefault(key, value)


load_env(Path(__file__).resolve().parent / ".env")

MODEL =os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")

# 角色 → (聲音, 基本風格)。基本風格會跟每句的導演提示合併成 style 欄位，不會被念出來。
# 官方建議 style 用簡短英文；寫太長（例如一整段角色設定）反而容易讓聲音飄掉。
# 口音由聲音本身決定：想要台灣口音，請在 AI Studio 的聲音清單挑 zh-TW 的聲音換上。
CHARACTERS = {
    "旁白": ("Sulafat", "gentle mother telling a bedtime story, warm and soft"),
    "栗栗": ("Leda", "young curious child, lively but not shrill"),
    "棉棉": ("Achernar", "sleepy little child, soft and slow"),
    "咕咕爺爺": ("Gacrux", "kind old grandfather, slow, with a smile"),
}

DEFAULT_RATE = 24000  # Gemini TTS 輸出的取樣率（若回傳 WAV，會以檔頭為準）
LINE_GAP_SEC = 0.6    # 每句之間的預設間隔
BGM_VOLUME = 0.08     # 背景音樂相對音量
LOUDNESS = "-16"      # Podcast 常見的響度標準（LUFS）

# 分批模式
BATCH_SEPARATOR = " <long pause>"  # 插在句子之間的停頓標記（實測約 3 秒，足夠跟逗號分開）
SILENCE_PEAK = 600    # 低於這個振幅（約 -35 dBFS）視為靜音
MIN_GAP_SEC = 0.3     # 句間停頓至少要這麼長才算
EDGE_PAD_SEC = 0.05   # 切下來的每句前後保留一點點空白
GAP_MARGIN = 1.3      # 句間停頓至少要比句中最長的停頓長 30%，才敢下刀
BLIP_SEC = 0.15       # 兩段靜音之間的聲音短於這個長度（換氣、雜訊），視為同一段停頓
BLIP_PEAK = 2600      # …而且要夠輕（約 -22 dBFS）。實測雜訊峰值 2–6%，短音節（咕、嗯）都 13% 以上
                      # 沒有這個條件，句首的「咕」（約 0.15 秒）會被當雜訊吃掉，切出來少一個字

# 睡前慢速朗讀大約每秒 3 個字；生成的音訊如果長得離譜，通常是模型把說明也念出來了
CHARS_PER_SEC = 3.0
TOO_LONG_RATIO = 2.5

# ---- 解析腳本 ------------------------------------------------------------

LINE_RE = re.compile(r"^@(\S+)\s*(?:\{([^}]*)\})?\s*(.+)$")
PAUSE_RE = re.compile(r"^\[停頓\s*([\d.]+)\s*秒\]$")


def parse_script(path):
    items = []
    for n, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if m := PAUSE_RE.match(line):
            items.append(("pause", float(m.group(1))))
        elif m := LINE_RE.match(line):
            speaker, direction, text = m.group(1), (m.group(2) or "").strip(), m.group(3).strip()
            if speaker not in CHARACTERS:
                sys.exit(f"第 {n} 行：未知角色「{speaker}」，請在 CHARACTERS 裡新增")
            items.append(("line", speaker, direction, text))
    return items


def style_for(speaker, direction):
    _, base = CHARACTERS[speaker]
    return f"{base}, {direction}" if direction else base


# ---- 音訊工具 ------------------------------------------------------------

class Audio:
    """16-bit 單聲道 PCM 與它的取樣率。"""

    def __init__(self, pcm, rate):
        self.pcm, self.rate = pcm, rate

    @property
    def seconds(self):
        return len(self.pcm) / 2 / self.rate

    @classmethod
    def from_api(cls, data):
        raw = base64.b64decode(data) if isinstance(data, str) else data
        if raw[:4] == b"RIFF":
            with wave.open(io.BytesIO(raw)) as wf:
                if wf.getsampwidth() != 2 or wf.getnchannels() != 1:
                    sys.exit(f"不支援的音訊格式：{wf.getnchannels()} 聲道、{wf.getsampwidth() * 8} bit")
                return cls(wf.readframes(wf.getnframes()), wf.getframerate())
        return cls(raw, DEFAULT_RATE)

    @classmethod
    def load(cls, path):
        with wave.open(str(path)) as wf:
            return cls(wf.readframes(wf.getnframes()), wf.getframerate())

    def save(self, path):
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.rate)
            wf.writeframes(self.pcm)


TAG_RE = re.compile(r"<[^>]+>")


def expected_seconds(texts):
    return sum(len(TAG_RE.sub("", t)) for t in texts) / CHARS_PER_SEC


# ---- 呼叫 API ------------------------------------------------------------

_last_call = 0.0


class Gemini:
    """先用免費 key；免費的每日額度用完，有設付費 key 就換過去繼續。"""

    def __init__(self, genai, free_key, paid_key):
        self._genai, self._paid_key = genai, paid_key
        self.on_paid = not free_key
        self.client = genai.Client(api_key=free_key or paid_key)

    @property
    def interactions(self):
        return self.client.interactions

    def switch_to_paid(self):
        if self.on_paid or not self._paid_key:
            return False
        self.client = self._genai.Client(api_key=self._paid_key)
        self.on_paid = True
        return True


def _call_api(client, contents, voice, min_interval):
    """contents: [(台詞, style), ...]。依每分鐘上限排隊，遇到 429 依建議秒數等待後重試。"""
    global _last_call

    body = [{
        "type": "user_input",
        "content": [{
            "type": "text",
            "text": text,
            "annotations": [{"type": "speech_metadata", "style": style}],
        } for text, style in contents],
    }]
    for attempt in range(1, 8):
        wait = _last_call + min_interval - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            return client.interactions.create(
                model=MODEL,
                input=body,
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": voice}]},
            )
        except Exception as e:  # Interactions API 的錯誤類別跟舊 API 不同，用狀態碼判斷
            code = getattr(e, "status_code", None) or getattr(e, "code", None)
            if code != 429:
                raise
            msg = str(e)
            if "PerDay" in msg:
                if client.switch_to_paid():
                    print("    免費 key 今天的額度用完了，改用付費 key（GEMINI_API_KEY_PAID）繼續")
                    continue
                which = "付費 key" if client.on_paid else "免費 key"
                sys.exit(
                    f"\n{which}今天在這個模型的額度已用完。已生成的部分都快取在 build/segments/，"
                    "明天再跑同一個指令就會從中斷處繼續。"
                )
            m = re.search(r"retry in ([\d.]+)s", msg)
            delay = float(m.group(1)) + 2 if m else 30
            print(f"    超過每分鐘上限，等 {delay:.0f} 秒後重試（第 {attempt} 次）")
            time.sleep(delay)
    sys.exit("重試太多次仍然失敗，請稍後再跑一次（已生成的部分會保留）")


OFFLINE = False  # --offline：只用快取，絕不呼叫 API


def request_audio(client, contents, voice, min_interval, label):
    """送出一次請求並取出音訊；空回應最多重試 3 次。"""
    if OFFLINE:
        sys.exit(f"\n--offline 模式：快取裡沒有「{label}」，不呼叫 API，先停在這裡。")
    for attempt in range(1, 4):
        resp = _call_api(client, contents, voice, min_interval)
        data = getattr(getattr(resp, "output_audio", None), "data", None)
        if data:
            return Audio.from_api(data)
        print(f"    沒有收到音訊（{str(resp)[:120]}），重試第 {attempt} 次")
    sys.exit(f"「{label}」連續 3 次沒有音訊。可以改寫這一句或拿掉導演提示再試。已生成的部分會保留。")


def _cache_path(cache_dir, prefix, voice, contents):
    key = hashlib.sha1(f"{MODEL}|{voice}|{contents!r}".encode()).hexdigest()[:16]
    return cache_dir / f"{prefix}{key}.wav"


# ---- 逐句模式 ------------------------------------------------------------

def synthesize(client, speaker, direction, text, cache_dir, min_interval):
    voice, _ = CHARACTERS[speaker]
    contents = [(text, style_for(speaker, direction))]
    path = _cache_path(cache_dir, "", voice, contents)
    if path.exists():
        return Audio.load(path), True
    audio = request_audio(client, contents, voice, min_interval, text[:20])
    if audio.seconds > expected_seconds([text]) * TOO_LONG_RATIO + 3:
        print(f"    注意：這句生成了 {audio.seconds:.0f} 秒，比預期長很多，可能念了多餘的內容")
    audio.save(path)
    return audio, False


# ---- 分批模式：同一個角色的台詞一次生成，再用靜音切開 ------------------------

def _silent_runs(audio):
    """回傳 (句中靜音區段, 聲音開始, 聲音結束)；單位是樣本。"""
    frame = audio.rate // 50  # 20 毫秒一格
    samples = array("h")
    samples.frombytes(audio.pcm[: len(audio.pcm) // 2 * 2])
    if sys.byteorder == "big":
        samples.byteswap()
    loud = [max(map(abs, samples[i:i + frame])) >= SILENCE_PEAK
            for i in range(0, len(samples), frame)]
    if True not in loud:
        return None
    first, last = loud.index(True), len(loud) - 1 - loud[::-1].index(True)
    runs, start = [], None
    for i in range(first, last + 1):
        if not loud[i] and start is None:
            start = i
        elif loud[i] and start is not None:
            runs.append((start * frame, i * frame))
            start = None
    # 停頓中間偶爾會有一小聲（換氣、雜訊），會把一段長停頓切成兩段，這裡把它們接回去
    # 只接「又短又輕」的；短但響的是真的音節，不能吃掉
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= BLIP_SEC * audio.rate \
                and max(map(abs, samples[merged[-1][1]:r[0]])) < BLIP_PEAK:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    return merged, first * frame, min((last + 1) * frame, len(samples))


def split_on_silence(audio, texts):
    """把含多句的音訊切回一句一句。

    挑最長的 n-1 段停頓當切點，但只有在「句間停頓明顯比句中停頓長」時才切；
    分不清楚就回傳 (None, 原因)，寧可不切也不要切錯位置。
    """
    n = len(texts)
    found = _silent_runs(audio)
    if found is None:
        return None, "整段都是靜音"
    runs, head, tail = found
    rate = audio.rate
    cuts = []
    if n > 1:
        runs = sorted(runs, key=lambda r: r[1] - r[0], reverse=True)
        if len(runs) < n - 1 or runs[n - 2][1] - runs[n - 2][0] < MIN_GAP_SEC * rate:
            count = sum(1 for r in runs if r[1] - r[0] >= MIN_GAP_SEC * rate)
            return None, f"預期 {n - 1} 個句間停頓，只找到 {count} 個"
        chosen = runs[: n - 1]
        if len(runs) >= n and (runs[n - 1][1] - runs[n - 1][0]) * GAP_MARGIN > chosen[-1][1] - chosen[-1][0]:
            gaps = "、".join(f"{(r[1] - r[0]) / rate:.2f}" for r in runs[: n + 2])
            return None, f"句中停頓跟句間停頓一樣長，分不清切點（最長的幾段靜音：{gaps} 秒）"
        cuts = sorted(chosen)

    pad = int(EDGE_PAD_SEC * rate)
    total = len(audio.pcm) // 2
    bounds = [head] + [x for c in cuts for x in c] + [tail]
    pieces = []
    for i in range(0, len(bounds), 2):
        a, b = max(bounds[i] - pad, 0), min(bounds[i + 1] + pad, total)
        pieces.append(Audio(audio.pcm[a * 2:b * 2], rate))
    return pieces, None


# ---- 用語音辨識找切點（需要 faster-whisper）--------------------------------

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")   # 有裝好 CUDA 函式庫可設成 cuda
MAX_DIFF_RATIO = 0.15  # 切出來的每句，辨識內容跟台詞最多可以差幾成的字（容許辨識錯字）
PUNCT_RE = re.compile(r"[\s，。、！？；：「」『』（）…—,.!?;:'\"()\-]+")
_whisper = None


def _norm(text):
    return PUNCT_RE.sub("", TAG_RE.sub("", text))


def _to_simplified(text):
    """Whisper 常把中文辨識成簡體字；比對前把兩邊都轉成簡體，繁簡差異就不會被當成錯字。
    需要 opencc（pip install opencc-python-reimplemented），沒裝就原樣比對。"""
    global _opencc
    if _opencc is None:
        try:
            from opencc import OpenCC
            _opencc = OpenCC("t2s")
        except ImportError:
            _opencc = False
    if not _opencc:
        return text
    out = _opencc.convert(text)
    return out if len(out) == len(text) else text


_opencc = None


@lru_cache(maxsize=None)
def _sound(ch):
    """一個字的拼音（含聲調），用來忽略同音字的差異。沒裝 pypinyin 或不是中文就回傳原字。
    逐字轉換（不看上下文），兩邊同一個字一定得到同一個音，所以多音字不會造成誤報。"""
    try:
        from pypinyin import pinyin, Style
    except ImportError:
        return ch
    return pinyin(ch, style=Style.TONE3, errors=lambda x: [x])[0][0]


def _sounds(text):
    """把文字轉成「每字一個拼音」的清單，長度不變；台詞和辨識結果改比這個，
    Whisper 把「栗栗」聽成「莉莉」這類同音字就不會被當成錯字。"""
    return [_sound(c) for c in _to_simplified(text)]


def _load_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        print(f"    載入語音辨識模型 {WHISPER_MODEL}（{WHISPER_DEVICE}）…")
        _whisper = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE,
                                compute_type="int8" if WHISPER_DEVICE == "cpu" else "float16")
    return _whisper


def transcribe_chars(audio):
    """回傳 [(字, 開始秒, 結束秒), ...]，每個中文字一筆。

    不要給 initial_prompt：給了台詞當提示，Whisper 會把提示「續寫」出來而不是聽音檔，
    開頭就變亂碼（咕咕爺爺 12 句實測：有提示 1/4 對齊成功，沒提示 3/3，而且快 4 倍）。"""
    import numpy as np
    model = _load_whisper()
    samples = np.frombuffer(audio.pcm, dtype="<i2").astype("float32") / 32768
    if audio.rate != 16000:  # Whisper 需要 16kHz
        idx = np.arange(0, len(samples), audio.rate / 16000)
        samples = np.interp(idx, np.arange(len(samples)), samples).astype("float32")
    segments, _ = model.transcribe(samples, language="zh", word_timestamps=True,
                                   vad_filter=False,
                                   condition_on_previous_text=True)
    chars = []
    for seg in segments:
        for w in seg.words or []:
            t = _norm(w.word)
            if not t:
                continue
            step = (w.end - w.start) / len(t)
            chars += [(c, w.start + i * step, w.start + (i + 1) * step) for i, c in enumerate(t)]
    return chars


def align_cuts(texts, chars):
    """把腳本台詞跟辨識結果逐字對齊，回傳每句之間的 (前一句結束秒, 下一句開始秒)。

    對不上的地方（辨識錯字、簡體字）會跳過，只用對得上的字定位；
    句子邊界附近如果完全對不上，回傳 (None, 原因)。"""
    from difflib import SequenceMatcher
    lines = [_norm(t) for t in texts]
    exp = _sounds("".join(lines))
    asr = _sounds("".join(c for c, _, _ in chars))  # 逐字轉換，長度不變
    sm = SequenceMatcher(None, exp, asr, autojunk=False)
    mapping = {}
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            mapping[a + k] = b + k
    if len(mapping) < 0.5 * len(exp):
        return None, f"語音辨識結果跟台詞只對上 {len(mapping)}/{len(exp)} 個字"

    line_times, pos = [], 0
    for line in lines:  # 每句對上的字的中間時間，用來事後檢查切得對不對
        line_times.append([(chars[mapping[j]][1] + chars[mapping[j]][2]) / 2
                           for j in range(pos, pos + len(line)) if j in mapping])
        pos += len(line)
    bounds, pos = [], 0
    for i, line in enumerate(lines[:-1]):
        end_idx, start_idx = pos + len(line) - 1, pos + len(line)
        pos += len(line)
        # 往前找這句最後一個對得上的字、往後找下一句第一個對得上的字（最多差 3 個字）
        e = next((j for j in range(end_idx, max(end_idx - 4, -1), -1) if j in mapping), None)
        s = next((j for j in range(start_idx, start_idx + 4) if j in mapping), None)
        if e is None or s is None or mapping[s] <= mapping[e]:
            return None, f"第 {i + 1} 句和第 {i + 2} 句的交界對不上辨識結果"
        # exact：交界那個字本身有對上。沒對上的一側只是估計，可能落在句中的停頓上
        bounds.append((chars[mapping[e]][2], chars[mapping[s]][1], e == end_idx, s == start_idx))
    return (bounds, line_times), None


def split_with_whisper(audio, texts):
    """用語音辨識找每句的交界，再在交界附近最長的靜音處下刀。"""
    try:
        chars = transcribe_chars(audio)
    except ImportError:
        return None, "沒有安裝 faster-whisper（pip install faster-whisper）"
    except Exception as e:  # 模型下載失敗、CUDA 函式庫缺少等
        return None, f"語音辨識失敗：{e}"
    result, why = align_cuts(texts, chars)
    if result is None:
        return None, why
    bounds, line_times = result
    found = _silent_runs(audio)
    runs = found[0] if found else []
    rate = audio.rate
    cut_points = []
    prev = 0
    for end_s, start_s, end_exact, start_exact in bounds:
        # 在「前一句最後一個字」和「下一句第一個字」之間找靜音
        lo, hi = int((end_s - 0.1) * rate), int((start_s + 0.1) * rate)
        inside = [r for r in runs if r[1] > lo and r[0] < hi and r[0] >= prev]
        if inside and end_exact and not start_exact:
            r = min(inside)                    # 前一句的結尾是準的：取它後面第一段靜音
        elif inside and start_exact and not end_exact:
            r = max(inside)                    # 下一句的開頭是準的：取它前面最後一段靜音
        elif inside:
            r = max(inside, key=lambda r: min(r[1], hi) - max(r[0], lo))
        else:
            mid = int((end_s + start_s) / 2 * rate)
            r = (mid, mid)
        cut_points.append(r)
        prev = r[1]
    head = found[1] if found else 0
    tail = found[2] if found else len(audio.pcm) // 2
    pad = int(EDGE_PAD_SEC * rate)
    total = len(audio.pcm) // 2
    edges = [head] + [x for c in cut_points for x in c] + [tail]
    pieces = []
    for i in range(0, len(edges), 2):
        a, b = max(edges[i] - pad, 0), min(edges[i + 1] + pad, total)
        if b <= a:
            return None, f"第 {i // 2 + 1} 句切出來是空的"
        # 檢查：切出來這段裡辨識到的字，要跟這句台詞幾乎一樣（多一截、少一截都會被抓到）
        from difflib import SequenceMatcher
        heard_text = "".join(c for c, st, en in chars if a / rate <= (st + en) / 2 <= b / rate)
        heard, want = _sounds(heard_text), _sounds(_norm(texts[i // 2]))
        same = sum(m.size for m in SequenceMatcher(None, want, heard, autojunk=False).get_matching_blocks())
        diff = max(len(want), len(heard)) - same   # 對不上的字數（錯字算一個）
        if diff > 2 + MAX_DIFF_RATIO * len(want):
            return None, (f"第 {i // 2 + 1} 句切出來的內容跟台詞差了 {diff} 個字"
                          f"（聽到「{heard_text[:24]}」）")
        pieces.append(Audio(audio.pcm[a * 2:b * 2], rate))
    return pieces, None


def synthesize_batch(client, speaker, entries, cache_dir, min_interval):
    """entries: [(導演提示, 台詞), ...]。成功回傳每句的 Audio，失敗回傳 None。"""
    voice, _ = CHARACTERS[speaker]
    contents = [
        (text + (BATCH_SEPARATOR if i < len(entries) - 1 else ""), style_for(speaker, d))
        for i, (d, text) in enumerate(entries)
    ]
    path = _cache_path(cache_dir, "batch_", voice, contents)
    cached = path.exists()
    if cached:
        audio = Audio.load(path)
    else:
        audio = request_audio(client, contents, voice, min_interval, f"{speaker} 的 {len(entries)} 句")
        audio.save(path)
    tag = "（快取）" if cached else ""

    limit = expected_seconds([t for _, t in entries]) * TOO_LONG_RATIO + 2 * len(entries)
    if audio.seconds > limit:
        # 這種情況改用逐句模式通常也一樣，而且會燒掉大量額度，所以直接停下來
        sys.exit(
            f"\n{tag}{speaker}：生成了 {audio.seconds:.0f} 秒，遠超過預期（約 "
            f"{expected_seconds([t for _, t in entries]):.0f} 秒），模型可能把設定也念出來了。\n"
            f"請確認使用的是 gemini-3.8 系列的 TTS 模型（目前：{MODEL}）。\n"
            f"原始音檔在 {path}，可以聽聽看它多念了什麼；確認原因後刪掉這個檔再重跑。"
        )
    texts = [t for _, t in entries]
    pieces, why = split_on_silence(audio, texts)
    if pieces is None and len(entries) > 1:
        print(f"  {tag}{speaker}：只靠停頓切不開（{why.split('（')[0]}），改用語音辨識找切點")
        pieces, why = split_with_whisper(audio, texts)
        if pieces is not None:
            why = None
            tag += "（語音辨識）"
    if pieces is None:
        print(f"  {tag}{speaker}：{len(entries)} 句一次生成，但切不開：{why}")
        return None
    secs = "、".join(f"{p.seconds:.1f}" for p in pieces)
    print(f"  {tag}{speaker}：{len(entries)} 句一次生成並切開（各 {secs} 秒）")
    return pieces


def inspect_batches():
    """列出每個批次音檔裡最長的幾段靜音，用來判斷句間停頓跟句中停頓差多少。"""
    files = sorted(Path("build/segments").glob("batch_*.wav"))
    if not files:
        print("build/segments/ 裡沒有批次音檔")
        return
    for f in files:
        audio = Audio.load(f)
        found = _silent_runs(audio)
        if not found:
            print(f"{f.name}：整段都是靜音")
            continue
        runs = sorted((r[1] - r[0]) / audio.rate for r in found[0])[::-1]
        print(f"\n{f.name}（{audio.seconds:.0f} 秒，{len(runs)} 段靜音）")
        print("  由長到短：" + "、".join(f"{x:.2f}" for x in runs[:15]))


# ---- 主流程 --------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--dry-run", action="store_true", help="只解析與估算，不呼叫 API")
    ap.add_argument("--bgm", help="背景音樂檔（會循環播放並在結尾淡出）")
    ap.add_argument("--rpm", type=float, default=3,
                    help="每分鐘最多呼叫幾次 API（免費方案是 3，付費方案可以調高）")
    ap.add_argument("--limit", type=int, help="只生成前 N 句，用來先試聽")
    ap.add_argument("--inspect", action="store_true",
                    help="分析 build/segments 裡已生成的批次音檔的靜音長度（不呼叫 API）")
    ap.add_argument("--offline", action="store_true",
                    help="只用 build/segments 裡的快取，絕不呼叫 API（測試切句用）")
    ap.add_argument("--fallback", action="store_true",
                    help="分批切不開的角色，自動改用逐句模式生成（會用掉較多額度）")
    ap.add_argument("--per-line", action="store_true",
                    help="一句一次請求（語氣控制最精準，但請求次數多，適合付費方案）")
    ap.add_argument("--no-paid", action="store_true",
                    help="不使用付費 key；免費額度用完就停下")
    args = ap.parse_args()

    if args.inspect:
        inspect_batches()
        return

    items = parse_script(args.script)
    lines = [i for i in items if i[0] == "line"]
    pauses = sum(i[1] for i in items if i[0] == "pause")
    est = expected_seconds([i[3] for i in lines]) + pauses + LINE_GAP_SEC * len(lines)
    print(f"模型：{MODEL}")
    print(f"{len(lines)} 句、{sum(len(TAG_RE.sub('', i[3])) for i in lines)} 字、停頓 {pauses:.0f} 秒，"
          f"預估長度約 {est / 60:.1f} 分鐘")
    for speaker in CHARACTERS:
        print(f"  {speaker}：{sum(1 for i in lines if i[1] == speaker)} 句")

    if args.dry_run:
        _, sp, d, t = lines[0]
        print(f"\n第一句送出的內容：\n  台詞：{t}\n  style：{style_for(sp, d)}")
        return

    global OFFLINE
    OFFLINE = args.offline
    from google import genai

    client = None
    if not OFFLINE:
        free_key = os.environ.get("GEMINI_API_KEY", "").strip()
        paid_key = "" if args.no_paid else os.environ.get("GEMINI_API_KEY_PAID", "").strip()
        if not free_key and not paid_key:
            sys.exit("找不到 API 金鑰：請在 .env 設定 GEMINI_API_KEY（範例見 .env.example）")
        client = Gemini(genai, free_key, paid_key)
        print("金鑰：" + ("只有付費 key" if not free_key else
                         "免費 key，用完改用付費 key" if paid_key else "只用免費 key"))
    import google.genai as _g
    major = int(re.match(r"\d+", getattr(_g, "__version__", "0")).group())
    if not OFFLINE and (major < 2 or not hasattr(client, "interactions")):
        sys.exit(f"google-genai 版本太舊（目前 {getattr(_g, '__version__', '?')}），"
                 "Gemini 3.8 TTS 需要 2.0 以上，請先執行：pip install -U google-genai")
    stem = Path(args.script).stem
    build = Path("build")
    cache = build / "segments"
    cache.mkdir(parents=True, exist_ok=True)

    if args.limit:
        cut = [i for i, it in enumerate(items) if it[0] == "line"][: args.limit][-1]
        items = items[: cut + 2]
        stem += f"_first{args.limit}"
    min_interval = 60 / args.rpm + 1
    line_idx = [i for i, it in enumerate(items) if it[0] == "line"]
    speakers = list(dict.fromkeys(items[i][1] for i in line_idx))
    if args.per_line:
        print(f"逐句模式：最多 {len(line_idx)} 次請求（已快取的會略過）")
    else:
        print(f"分批模式：每個角色一次請求，共 {len(speakers)} 次")

    rendered = {}
    failed = []
    if not args.per_line:
        for sp in speakers:
            idxs = [i for i in line_idx if items[i][1] == sp]
            pieces = synthesize_batch(client, sp, [items[i][2:] for i in idxs], cache, min_interval)
            if pieces:
                rendered.update(zip(idxs, pieces))
            elif args.fallback:
                print(f"    {sp} 的台詞改用逐句模式生成（會多花 {len(idxs)} 次請求）")
            else:
                failed.append(sp)
        if failed:
            sys.exit(
                f"\n{'、'.join(failed)} 切不開，先停下來，不自動改成逐句生成（避免用光額度）。\n"
                "批次音檔已存在 build/segments/，可以用 --inspect 看停頓長度；\n"
                "要改成逐句生成切不開的角色，請加上 --fallback 再跑一次（其他角色會直接用快取）。"
            )

    for n, i in enumerate(line_idx, 1):
        if i in rendered:
            continue
        _, speaker, direction, text = items[i]
        audio, cached = synthesize(client, speaker, direction, text, cache, min_interval)
        print(f"[{n}/{len(line_idx)}] {'（快取）' if cached else ''}{speaker}：{text[:20]}…")
        rendered[i] = audio

    rate = next(iter(rendered.values())).rate
    if any(a.rate != rate for a in rendered.values()):
        sys.exit("各段音訊的取樣率不一致，請刪掉 build/segments/ 後重跑")

    def silence(sec):
        return b"\x00\x00" * int(rate * sec)

    pcm = bytearray()
    for i, item in enumerate(items):
        if item[0] == "pause":
            pcm += silence(item[1])
        else:
            pcm += rendered[i].pcm + silence(LINE_GAP_SEC)
    episode = Audio(bytes(pcm), rate)

    wav_path = build / f"{stem}.wav"
    episode.save(wav_path)
    print(f"已輸出 {wav_path}（{episode.seconds / 60:.1f} 分鐘）")

    if not shutil.which("ffmpeg"):
        print("找不到 ffmpeg，略過 mp3 輸出、響度標準化與背景音樂")
        return

    mp3_path = build / f"{stem}.mp3"
    fade_start = max(episode.seconds - 8, 0)
    if args.bgm:
        filt = (
            f"[1:a]volume={BGM_VOLUME},afade=t=out:st={fade_start}:d=8[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0,"
            f"loudnorm=I={LOUDNESS}:TP=-1.5:LRA=11[out]"
        )
        cmd = ["ffmpeg", "-y", "-i", str(wav_path), "-stream_loop", "-1", "-i", args.bgm,
               "-filter_complex", filt, "-map", "[out]"]
    else:
        cmd = ["ffmpeg", "-y", "-i", str(wav_path), "-af", f"loudnorm=I={LOUDNESS}:TP=-1.5:LRA=11"]
    cmd += ["-ac", "1", "-ar", "44100", "-b:a", "96k", str(mp3_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"已輸出 {mp3_path}")


if __name__ == "__main__":
    main()