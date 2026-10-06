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
import math
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
    """讀 KEY=VALUE 格式的 .env，**.env 優先**：有填值的會蓋掉環境變數（Windows 使用者環境變數裡的舊 key
    曾經默默蓋掉 .env 的新 key）。.env 裡留空的不覆蓋。設 NO_DOTENV=1 就不讀（測試用）。"""
    if os.environ.get("NO_DOTENV") == "1" or not path.exists():
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
        if value:
            os.environ[key] = value
        else:
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
    "許谷達": ("Leda", "5-year-old cheerful, energetic boy, storytelling to classmates, lively and expressive"),
    "許奈娥": ("Aoede", "5-year-old sweet, cheerful, imaginative girl, storytelling to classmates, cute and expressive"),
}

DEFAULT_RATE = 24000  # Gemini TTS 輸出的取樣率（若回傳 WAV，會以檔頭為準）
API_TIMEOUT_SEC = 300  # 一個批次的請求最多等多久（整批旁白約 2 分鐘的音訊，正常一兩分鐘內就回來）
LINE_GAP_SEC = 0.6    # 每句之間的預設間隔
LOUDNESS = "-16"      # Podcast 常見的響度標準（LUFS）
PEAK_LIMIT = 0.79     # 峰值上限（約 -2 dBFS，留給 mp3 編碼的餘裕）

# 音效與背景：腳本裡的名稱 → (assets/ 裡的檔案, 相對人聲的 dB)。
# 程式會先量每個檔案的響度，所以 dB 是「比人聲小多少」，換素材不用重調。
# 下載來源與授權記在 assets/SOURCES.md（素材本身不進版控）。
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR") or Path(__file__).resolve().parent / "assets")
SOUNDS = {
    "開場鈴": ("windchimes.ogg", -8),
    "搖籃曲": ("chopin_prelude_op28_13.mp3", -18),
    "放鬆音樂": ("wandering.wav", -18),
    "夜晚蟲鳴": ("night_crickets.wav", -24),
    "河水": ("river_flowing.wav", -24),
    # 助眠尾段用：上面兩個用 atempo 放慢到 0.7 倍（做法見 assets/SOURCES.md）
    "夜晚蟲鳴慢": ("night_crickets_slow.wav", -24),
    "河水慢": ("river_flowing_slow.wav", -24),
    "貓頭鷹": ("scops_owl.ogg", -18),  # 疊在台詞底下，不會被 ducking，所以小聲一點
    # 從 ep02 旁白配音切出來再拉長的呼吸聲（做法見 assets/SOURCES.md）。None = 保持原音量，本來就跟人聲一樣大
    "吸氣1": ("narrator_inhale_1.wav", None),
    "吸氣2": ("narrator_inhale_2.wav", None),
    "吐氣": ("narrator_exhale.wav", None),
    # 從舊版 ep03 配音切出來的哈欠（新版的 <yawn> 只念成一口氣），在人工切點檔用「音效:名稱」接進句子裡。
    # 已經調成跟新版同一角色的說話音量，所以是 None（做法見 assets/SOURCES.md）
    "哈欠棉棉1": ("yawn_mianmian_1.wav", None),
    "哈欠棉棉2": ("yawn_mianmian_2.wav", None),
    "哈欠栗栗": ("yawn_lili.wav", None),
    "哈欠咕咕爺爺": ("yawn_gugu.wav", None),
    "哈欠旁白": ("yawn_narrator.wav", None),
    # 沖繩大冒險用素材
    "沖繩冒險": ("okinawa_adventure_bgm.mp3", -20),
    "水滴泡泡": ("sfx_bubbles.wav", -18),
    "水花": ("sfx_splash.wav", -14),
    "拍手": ("sfx_clap.wav", -10),
    "擊掌": ("sfx_highfive.wav", -8),
    "拍手歡呼": ("sfx_cheer.wav", -16),
    "水中氣泡": ("sfx_water_bubbles.wav", -16),
    "肚子咕嚕": ("sfx_stomach.wav", -12),
    "烤肉滋滋": ("sfx_sizzle.wav", -16),
    "掌聲": ("sfx_applause.wav", -14),
    # 澎湖大冒險用素材
    "澎湖冒險": ("penghu_adventure_bgm.mp3", -20),
    "飛機咻": ("sfx_airplane.wav", -12),
    "海浪": ("sfx_waves.wav", -20),
    "煙火": ("sfx_fireworks.wav", -10),
    "悶煙火": ("sfx_fireworks_muffled.wav", -14),
}
BGM_DB = -20          # --bgm 指定的整集背景音樂，相對人聲的 dB
BG_FADE_IN = 3.0      # 背景淡入秒數
BG_FADE_OUT = 8.0     # 背景淡出秒數（[背景 停]、換下一段背景、整集結尾）
DUCK_DB = -4          # 有人說話時，背景再降低多少 dB（輕微，幾乎察覺不到）
DUCK_RAMP = 1.0       # 降低與恢復各花幾秒
BG_COMP_ABOVE = 2     # 背景比自己的平均音量大這麼多 dB 以上，就開始壓縮
BG_COMP_RATIO = 4     # 壓縮比（超出的部分只留 1/4）
BREATH_BELOW_DB = 15  # [音效 X 剪 自動]：句尾氣音至少要比台詞小這麼多 dB，才敢剪
BREATH_MAX_TRIM = 1.0 # …而且最多剪這麼多秒

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
SFX_RE = re.compile(r"^\[音效\s+(\S+?)(\s+疊)?(?:\s+剪\s*(?:([\d.]+)\s*秒|(自動)))?\]$")
BG_RE = re.compile(r"^\[背景\s+(.+?)\]$")
BG_STOP_RE = re.compile(r"^停(?:\s+([\d.]+)\s*秒)?$")
SHARED_RE = re.compile(r"^\[共用\s+(\S+)\]$")
VOL_RE = re.compile(r"^\[音量\s*([+-]?[\d.]+)\s*dB\]$", re.I)

# 共用片段：每集都一樣的段落（開場、放鬆、咕咕爺爺登場）寫在 SHARED_SCRIPT，腳本用 [共用 名稱] 引用。
# 共用的台詞另成一批生成，快取放在 SHARED_DIR（進版控）：每集送出的內容相同，只有第一次花額度，
# 而且每集的招牌段落聲音都一樣。
SHARED_SCRIPT = Path(__file__).resolve().parent / "episodes" / "shared.md"
SHARED_DIR = Path(os.environ.get("SHARED_DIR") or ASSETS_DIR / "shared")


def parse_script(path):
    """回傳項目清單：("line", 角色, 導演提示, 台詞)、("pause", 秒)、("sfx", 名稱, 是否疊上去)、
    ("bg", (名稱, …), 淡出秒數或 None)、("shared", 名稱)、("vol", dB)。背景名稱是空的 tuple 代表 [背景 停]。"""
    return _parse_lines(Path(path).read_text(encoding="utf-8").splitlines(), Path(path).name)


def _parse_lines(lines, where, first_line=1):
    items = []
    for n, raw in enumerate(lines, first_line):
        n = f"{where} 第 {n}"
        line = raw.strip()
        if m := SHARED_RE.match(line):
            items.append(("shared", m.group(1)))
        elif m := PAUSE_RE.match(line):
            items.append(("pause", float(m.group(1))))
        elif m := VOL_RE.match(line):
            items.append(("vol", float(m.group(1))))
        elif m := SFX_RE.match(line):
            if m.group(1) not in SOUNDS:
                sys.exit(f"{n} 行：未知音效「{m.group(1)}」，請在 SOUNDS 裡新增")
            trim = "自動" if m.group(4) else float(m.group(3)) if m.group(3) else 0.0
            if trim and (m.group(2) or not items or items[-1][0] != "line"):
                sys.exit(f"{n} 行：「剪」只能用在緊接著台詞的插入型音效（剪掉那句台詞的句尾）")
            items.append(("sfx", m.group(1), bool(m.group(2)), trim))
        elif m := BG_RE.match(line):
            if stop := BG_STOP_RE.match(m.group(1)):
                items.append(("bg", (), float(stop.group(1)) if stop.group(1) else None))
                continue
            names = tuple(m.group(1).split())   # 可以同時播多個，例如 [背景 夜晚蟲鳴 河水]
            for name in names:
                if name not in SOUNDS:
                    sys.exit(f"{n} 行：未知背景「{name}」，請在 SOUNDS 裡新增")
            items.append(("bg", names, None))
        elif m := LINE_RE.match(line):
            speaker, direction, text = m.group(1), (m.group(2) or "").strip(), m.group(3).strip()
            if speaker not in CHARACTERS:
                sys.exit(f"{n} 行：未知角色「{speaker}」，請在 CHARACTERS 裡新增")
            items.append(("line", speaker, direction, text))
    return items


def shared_sections():
    """SHARED_SCRIPT 裡的「## 名稱」段落 → 項目清單。"""
    sections, name, start, buf = {}, None, 0, []
    lines = SHARED_SCRIPT.read_text(encoding="utf-8").splitlines() + ["## "]
    for n, raw in enumerate(lines, 1):
        if raw.startswith("## "):
            if name:
                sections[name] = _parse_lines(buf, SHARED_SCRIPT.name, start)
            name, start, buf = raw[3:].strip(), n + 1, []
        elif name:
            buf.append(raw)
    return sections


def expand_shared(items):
    """把 [共用 名稱] 換成共用片段的內容。回傳 (新的項目清單, 共用台詞的位置)。"""
    if not any(it[0] == "shared" for it in items):
        return items, set()
    sections = shared_sections()
    out, shared = [], set()
    for it in items:
        if it[0] != "shared":
            out.append(it)
            continue
        if it[1] not in sections:
            sys.exit(f"未知的共用片段「{it[1]}」，{SHARED_SCRIPT.name} 裡有：{'、'.join(sections)}")
        for sub in sections[it[1]]:
            if sub[0] == "shared":
                sys.exit(f"共用片段「{it[1]}」裡不能再引用共用片段")
            if sub[0] == "line":
                shared.add(len(out))
            out.append(sub)
    return out, shared


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
        self.client = self._client(free_key or paid_key)

    def _client(self, key):
        # 不設逾時的話，伺服器斷線時程式會一直等下去（ep06 卡了 10 分鐘以上）
        return self._genai.Client(api_key=key, http_options={"timeout": API_TIMEOUT_SEC * 1000})

    @property
    def interactions(self):
        return self.client.interactions

    def switch_to_paid(self):
        if self.on_paid or not self._paid_key:
            return False
        self.client = self._client(self._paid_key)
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
            if "timeout" in type(e).__name__.lower():
                # 不自動重試：伺服器可能已經生成完、只是沒送回來，這次可能已算進額度
                sys.exit(f"\n等了 {API_TIMEOUT_SEC} 秒沒有回應（{type(e).__name__}）。已生成的批次都快取在 "
                         "build/segments/；這一批可能已經算進今天的額度，要重跑請自己決定。")
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
        pieces[-1].start = a
    return pieces, None


# ---- 用語音辨識找切點（需要 faster-whisper）--------------------------------

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")   # 有裝好 CUDA 函式庫可設成 cuda
MAX_DIFF_RATIO = 0.15  # 切出來的每句，辨識內容跟台詞最多可以差幾成的字（容許辨識錯字）
# 靜音切開後也用語音辨識逐句核對內容。離線測試用合成音訊（聽不出字），用 ASR_CHECK=0 關掉
ASR_CHECK = os.environ.get("ASR_CHECK", "1") != "0"
# ~：Whisper 會把拉長的音寫成「啊~~~」，不是字（ep03 棉棉）
PUNCT_RE = re.compile(r"[\s，。、！？；：「」『』（）…—~～,.!?;:'\"()\-]+")
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


def _content_mismatch(n, heard_text, text):
    """切出來的第 n 句，辨識內容跟台詞差太多就回傳原因（多一截、少一截、錯位都會被抓到）。"""
    from difflib import SequenceMatcher
    heard, want = _sounds(heard_text), _sounds(_norm(text))
    same = sum(m.size for m in SequenceMatcher(None, want, heard, autojunk=False).get_matching_blocks())
    diff = max(len(want), len(heard)) - same   # 對不上的字數（錯字算一個）
    if diff > 2 + MAX_DIFF_RATIO * len(want):
        return f"第 {n} 句切出來的內容跟台詞差了 {diff} 個字（聽到「{heard_text[:24]}」）"
    return None


def check_pieces(pieces, texts):
    """逐句辨識切好的音訊，跟台詞比對。靜音切割只看句數對不對，模型多念一句、
    又剛好有兩句黏在一起時句數會對上，卻整段錯位（ep04 旁白實際發生過），所以一定要核對。
    回傳 None（沒問題）或原因。"""
    if not ASR_CHECK:
        return None
    try:
        for n, (piece, text) in enumerate(zip(pieces, texts), 1):
            if getattr(piece, "ear_checked", False):   # 使用者親耳聽過（cuts.txt 寫了「人耳確認」）
                continue
            heard = "".join(c for c, _, _ in transcribe_chars(getattr(piece, "speech_only", piece)))
            if why := _content_mismatch(n, heard, text):
                return why
    except ImportError:
        print("    注意：沒有安裝 faster-whisper，靜音切開的句子沒有核對內容，試聽時要特別注意有沒有錯位")
    return None


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
        heard_text = "".join(c for c, st, en in chars if a / rate <= (st + en) / 2 <= b / rate)
        if why := _content_mismatch(i // 2 + 1, heard_text, texts[i // 2]):
            return None, why
        pieces.append(Audio(audio.pcm[a * 2:b * 2], rate))
        pieces[-1].start = a
    return pieces, None


EAR_CHECKED = "人耳確認"
CUT_SFX = "音效:"


def manual_cuts(audio, cuts_path, count):
    """人工切點：批次音檔旁的 <批次檔名>.cuts.txt，每行一句「開始秒 結束秒」（# 之後是註解）。
    一行也可以寫好幾段「開始 結束 開始 結束 …」，接起來當一句，用來剪掉句中不要的聲音
    （例如 <exhales> 念出來的短吐氣聲）。
    用在模型念錯（例如同一句念兩次）、自動切不開，但音檔本身可以用的時候，不必再花額度。
    行數跟句數不合、秒數超出音檔或順序顛倒就停下來，不猜。
    秒數後面寫「人耳確認」：使用者聽過、確定內容對，這句就不做語音辨識核對（例如很輕的氣音，
    Whisper 每次聽成不同的字；ep01 咕咕爺爺的「晚安，栗栗」被聽成「哇蜜蜜」）。只有使用者親耳聽過才能加。
    兩組秒數之間（或最前、最後）可以寫「音效:名稱」（SOUNDS 裡的名稱），把那個音效接進這句，
    用來把模型念得不好的聲音標記換成別的錄音（ep03：<yawn> 只念成一口氣，換成舊版配音的哈欠）。
    語音辨識核對只聽台詞的部分，不含接進來的音效。"""
    lines, ear = [], set()
    for raw in cuts_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#")[0].strip()
        if line.endswith(EAR_CHECKED):
            line = line[:-len(EAR_CHECKED)].strip()
            ear.add(len(lines))
        if line:
            nums, inserts = [], {}   # inserts：第幾組秒數之前 → 音效名稱們
            for tok in line.split():
                if tok.startswith(CUT_SFX):
                    name = tok[len(CUT_SFX):]
                    if name not in SOUNDS or len(nums) % 2:
                        nums = []
                        break
                    inserts.setdefault(len(nums) // 2, []).append(name)
                    continue
                try:
                    nums.append(float(tok))
                except ValueError:
                    nums = []
                    break
            if not nums or len(nums) % 2:
                sys.exit(f"\n{cuts_path}：看不懂這一行「{raw}」，格式是「開始秒 結束秒」（可以寫好幾組，"
                         f"組和組之間可以寫「{CUT_SFX}名稱」，名稱要在 SOUNDS 裡）。")
            lines.append((nums, inserts))
    if len(lines) != count:
        sys.exit(f"\n{cuts_path}：寫了 {len(lines)} 句，但這批有 {count} 句。")
    pieces = []
    for i, (nums, inserts) in enumerate(lines, 1):
        if nums != sorted(nums) or len(set(nums)) != len(nums) or not 0 <= nums[0] or nums[-1] > audio.seconds + 0.01:
            sys.exit(f"\n{cuts_path}：第 {i} 句的秒數 {nums} 不合理（要由小到大，音檔長 {audio.seconds:.2f} 秒）。")
        speech = [audio.pcm[int(a * audio.rate) * 2:int(b * audio.rate) * 2]
                  for a, b in zip(nums[::2], nums[1::2])]
        pcm = b""
        for k in range(len(speech) + 1):
            pcm += b"".join(decode_sound(name, audio.rate) for name in inserts.get(k, []))
            pcm += speech[k] if k < len(speech) else b""
        piece = Audio(pcm, audio.rate)
        piece.ear_checked = (i - 1) in ear
        if inserts:
            piece.speech_only = Audio(b"".join(speech), audio.rate)
        pieces.append(piece)
    return pieces


def batch_request(speaker, entries, cache_dir):
    """一批要送出的內容和它的快取檔路徑。entries: [(導演提示, 台詞), ...]。"""
    voice, _ = CHARACTERS[speaker]
    contents = [
        (text + (BATCH_SEPARATOR if i < len(entries) - 1 else ""), style_for(speaker, d))
        for i, (d, text) in enumerate(entries)
    ]
    return voice, contents, _cache_path(cache_dir, "batch_", voice, contents)


def auto_split(audio, texts, label, tag=""):
    """自動切句：先靜音切割（切完逐句核對內容），不行再用語音辨識。回傳 (pieces, 原因, tag)。
    每段 piece.start 是它在批次音檔裡的起點（取樣數），tools/trim_tails.py 用來寫人工切點。"""
    pieces, why = split_on_silence(audio, texts)
    if pieces is not None and len(texts) > 1 and (bad := check_pieces(pieces, texts)):
        print(f"  {tag}{label}：靜音切開的內容對不上台詞：{bad}")
        pieces, why = None, "靜音切開了，但內容對不上"
    if pieces is None and len(texts) > 1:
        print(f"  {tag}{label}：只靠停頓切不開（{why.split('（')[0]}），改用語音辨識找切點")
        pieces, why = split_with_whisper(audio, texts)
        if pieces is not None:
            why = None
            tag += "（語音辨識）"
    return pieces, why, tag


def synthesize_batch(client, speaker, entries, cache_dir, min_interval, label=None):
    """entries: [(導演提示, 台詞), ...]。成功回傳每句的 Audio，失敗回傳 None。"""
    label = label or speaker
    voice, contents, path = batch_request(speaker, entries, cache_dir)
    cached = path.exists()
    if cached:
        audio = Audio.load(path)
    else:
        audio = request_audio(client, contents, voice, min_interval, f"{label} 的 {len(entries)} 句")
        audio.save(path)
    tag = "（快取）" if cached else ""

    limit = expected_seconds([t for _, t in entries]) * TOO_LONG_RATIO + 2 * len(entries)
    if audio.seconds > limit:
        # 這種情況改用逐句模式通常也一樣，而且會燒掉大量額度，所以直接停下來
        sys.exit(
            f"\n{tag}{label}：生成了 {audio.seconds:.0f} 秒，遠超過預期（約 "
            f"{expected_seconds([t for _, t in entries]):.0f} 秒），模型可能把設定也念出來了。\n"
            f"請確認使用的是 gemini-3.8 系列的 TTS 模型（目前：{MODEL}）。\n"
            f"原始音檔在 {path}，可以聽聽看它多念了什麼；確認原因後刪掉這個檔再重跑。"
        )
    texts = [t for _, t in entries]
    cuts_path = path.with_suffix(".cuts.txt")
    if cuts_path.exists():
        pieces = manual_cuts(audio, cuts_path, len(entries))
        if bad := check_pieces(pieces, texts):   # 人工切點也要核對，秒數寫錯一樣會錯位
            sys.exit(f"\n{cuts_path}：照人工切點切出來的內容對不上台詞：{bad}")
        secs = "、".join(f"{p.seconds:.1f}" for p in pieces)
        print(f"  {tag}（人工切點）{label}：{len(entries)} 句照 {cuts_path.name} 切開（各 {secs} 秒）")
        if ear := [n for n, p in enumerate(pieces, 1) if p.ear_checked]:
            print(f"    第 {'、'.join(map(str, ear))} 句標了「{EAR_CHECKED}」，沒有用語音辨識核對")
        return pieces
    pieces, why, tag = auto_split(audio, texts, label, tag)
    if pieces is None:
        print(f"  {tag}{label}：{len(entries)} 句一次生成，但切不開：{why}")
        print(f"    批次音檔：{path}（聽過、音檔本身可用的話，可以寫 {cuts_path.name} 人工指定切點）")
        return None
    secs = "、".join(f"{p.seconds:.1f}" for p in pieces)
    print(f"  {tag}{label}：{len(entries)} 句一次生成並切開（各 {secs} 秒）")
    return pieces


# ---- 音效與背景 ----------------------------------------------------------


def sound_path(name):
    return ASSETS_DIR / SOUNDS[name][0]


def sound_files(items, bgm):
    """這一集用到的素材：[(名稱, 檔案)]。有 --bgm 時，腳本裡的 [背景] 會被忽略。"""
    names = [i[1] for i in items if i[0] == "sfx"]
    names += [] if bgm else [n for i in items if i[0] == "bg" for n in i[1]]
    files = [(n, sound_path(n)) for n in dict.fromkeys(names)]
    return files + ([("--bgm", Path(bgm))] if bgm else [])


def check_sounds(items, bgm):
    """列出素材並檢查檔案與 ffmpeg 都在，回傳缺少的東西。"""
    files = sound_files(items, bgm)
    if not files:
        return []
    if bgm and any(i[0] == "bg" for i in items):
        print("有指定 --bgm，腳本裡的 [背景] 會被忽略")
    print("音效與背景：")
    missing = []
    for name, path in files:
        print(f"  {name}：{path}" + ("" if path.exists() else "（找不到）"))
        if not path.exists():
            missing.append(str(path))
    if not find_ffmpeg():
        missing.append("ffmpeg")
    return missing


# 試跑一次本程式用到、舊版 ffmpeg 沒有的功能（ebur128 framelog=quiet、amix normalize 都是 4.4 以後才有）
FFMPEG_PROBE = ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.2",
                "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.2", "-filter_complex",
                "[0:a][1:a]amix=inputs=2:duration=first:normalize=0,adelay=10:all=1,"
                "asetnsamples=n=480:p=0,volume='1':eval=frame,acompressor,aresample=96000,"
                "alimiter=level=false,ebur128=framelog=quiet:peak=true",
                "-c:a", "libmp3lame", "-f", "null", "-"]


def _ffmpeg_works(exe):
    try:
        p = subprocess.run([exe, "-hide_banner", "-nostats", *FFMPEG_PROBE],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return p.returncode == 0


@lru_cache(maxsize=None)
def find_ffmpeg():
    """找一個功能夠用的 ffmpeg，找不到回傳 None。
    電腦上常有好幾個 ffmpeg（例如 miniconda 附的 4.3），PATH 順序不同就會拿到舊版、跑到一半才失敗，
    所以依 PATH 順序逐一試跑，用第一個能用的。.env 或環境變數設 FFMPEG＝完整路徑 就只用那一個。"""
    if exe := os.environ.get("FFMPEG", "").strip():
        if _ffmpeg_works(exe):
            return exe
        sys.exit(f"FFMPEG 指定的 {exe} 不能用（找不到，或版本太舊，需要 4.4 以上）")
    skipped = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not (exe := shutil.which("ffmpeg", path=d)) or exe in skipped:
            continue
        if _ffmpeg_works(exe):
            if skipped:
                print(f"使用 ffmpeg：{exe}（略過不支援的舊版：{'、'.join(skipped)}）")
            return exe
        skipped.append(exe)
    if skipped:
        print(f"找到的 ffmpeg 都太舊（需要 4.4 以上）：{'、'.join(skipped)}")
    return None


def run_ffmpeg(args):
    p = subprocess.run([find_ffmpeg() or "ffmpeg", "-hide_banner", "-nostats", "-y", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        sys.exit(f"ffmpeg 執行失敗：\n{p.stderr[-1500:]}")
    return p


@lru_cache(maxsize=None)
def measure_lufs(path):
    """整個檔案的響度（LUFS）。"""
    p = run_ffmpeg(["-i", str(path), "-af", "ebur128=framelog=quiet", "-f", "null", "-"])
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)[-1])


def gain_db(path, rel_db):
    """把素材調到「人聲響度 + rel_db」需要的增益。rel_db 是 None 就保持原音量。"""
    return 0.0 if rel_db is None else float(LOUDNESS) + rel_db - measure_lufs(path)


def decode_sound(name, rate):
    """把插入型音效解碼成跟人聲相同格式的 PCM，並調好音量。"""
    path = sound_path(name)
    p = subprocess.run([find_ffmpeg() or "ffmpeg", "-v", "error", "-i", str(path),
                        "-af", f"volume={gain_db(path, SOUNDS[name][1]):.2f}dB",
                        "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"], capture_output=True)
    if p.returncode:
        sys.exit(f"讀不了音效 {path}：{p.stderr.decode('utf-8', 'replace').strip()}")
    return p.stdout


def trailing_breath(audio):
    """量句尾被切斷的氣音有多長（秒），給 [音效 X 剪 自動] 用。
    只認「台詞 → 一段安靜 → 句尾一小段比台詞小很多的聲音」；分不清就回傳 0（不剪），
    因為多聽到半口氣沒關係，剪到台詞就糟了。回傳 (秒數, 說明)。"""
    a = array("h", audio.pcm)
    n = audio.rate // 100   # 10 毫秒一格
    levels = []
    for k in range(len(a) // n):
        frame = a[k * n:(k + 1) * n]
        levels.append(20 * math.log10(math.sqrt(sum(x * x for x in frame) / n) + 1))
    # 停頓裡的雜訊每 10 毫秒會跳動好幾 dB，先取前後 5 格的中位數再判斷
    levels = [sorted(levels[max(k - 2, 0):k + 3])[len(levels[max(k - 2, 0):k + 3]) // 2]
              for k in range(len(levels))]
    if len(levels) < 50:
        return 0.0, "句子太短"
    ordered = sorted(levels)
    floor, speech = ordered[len(levels) // 10], ordered[len(levels) * 95 // 100]
    quiet = lambda lv: lv < floor + 10
    k = len(levels)
    while k and quiet(levels[k - 1]):          # 最後面可能還有一點空白
        k -= 1
    end = k
    while k and not quiet(levels[k - 1]):      # 往前找出句尾那段聲音
        k -= 1
    start = k
    if start == end:
        return 0.0, "句尾沒有氣音"
    if max(levels[start:end]) > speech - BREATH_BELOW_DB:
        return 0.0, "句尾的聲音太大，可能是台詞"
    gap = 0
    while k and quiet(levels[k - 1]) and gap < 30:
        k -= 1
        gap += 1
    if gap < 15:
        return 0.0, "句尾的聲音前面沒有明顯的停頓，分不清是不是台詞"
    secs = (len(levels) - start) / 100 + 0.05   # 氣音是慢慢變大的，起點多留一點
    if secs > BREATH_MAX_TRIM:
        return 0.0, f"句尾的聲音長達 {secs:.2f} 秒，不像被切斷的氣音"
    return secs, "找到句尾氣音"


def scale(audio, db):
    """把一句台詞調大或調小 db 分貝（超過範圍的取樣點夾住，不會繞回去變爆音）。"""
    k = 10 ** (db / 20)
    a = array("h", audio.pcm)
    return Audio(array("h", (max(-32768, min(32767, round(v * k))) for v in a)).tobytes(), audio.rate)


def assemble(items, rendered, rate, insert_pcm):
    """把台詞、停頓、插入型音效接成人聲軌。
    同時記下疊加音效 [(秒, 名稱)]、背景 [(名稱, 開始秒, 停止秒或 None, 淡出秒數或 None)]、
    說話區間 [(開始, 結束)]。"""
    pcm = bytearray()
    overlays, backgrounds, speech = [], [], []
    current = ((), 0.0)  # 正在播的背景：(名稱們, 開始秒數)
    vol = 0.0             # [音量 N dB]：之後的台詞都調這麼多，直到下一個 [音量]（TTS 有時把該輕的句子念得比較大聲）

    def now():
        return len(pcm) / 2 / rate

    for i, item in enumerate(items):
        if item[0] == "pause":
            pcm += b"\x00\x00" * int(rate * item[1])
        elif item[0] == "line":
            start = now()
            last_line = rendered[i] if not vol else scale(rendered[i], vol)
            pcm += last_line.pcm
            speech.append((start, now()))
            pcm += b"\x00\x00" * int(rate * LINE_GAP_SEC)
        elif item[0] == "sfx" and item[2]:
            overlays.append((now(), item[1]))
        elif item[0] == "sfx":
            trim = item[3]
            if trim == "自動":
                trim, why = trailing_breath(last_line)
                print(f"  [音效 {item[1]}]：{why}，剪掉句尾 {trim:.2f} 秒")
            if item[3]:   # 剪掉前一句的句間空白和句尾（例如被切句切斷的半口氣），換成這個音效
                del pcm[len(pcm) - 2 * (int(rate * LINE_GAP_SEC) + int(rate * trim)):]
                speech[-1] = (speech[-1][0], min(speech[-1][1], now()))
            pcm += insert_pcm(item[1])
        elif item[0] == "vol":
            vol = item[1]
        elif item[0] == "bg":
            names, start = current
            backgrounds += [(name, start, now(), item[2]) for name in names]
            current = (item[1], now())
    names, start = current
    backgrounds += [(name, start, None, None) for name in names]
    return Audio(bytes(pcm), rate), overlays, backgrounds, speech


def background_tracks(backgrounds, total, bgm):
    """每段背景要怎麼播：[(檔案, 相對 dB, 開始, 開始淡出, 結束)]。--bgm 會蓋掉腳本裡的 [背景]。
    遇到 [背景 停] 或下一段背景就開始淡出（新的同時淡入，等於交叉淡化）；沒停的播到結尾前淡出。
    淡出秒數預設 BG_FADE_OUT，[背景 停 N秒] 可以指定。"""
    if bgm:
        return [(Path(bgm), BGM_DB, 0.0, max(total - BG_FADE_OUT, 0.0), total)]
    tracks = []
    for name, start, stop, fade in backgrounds:
        if stop is None:
            fade_at, end = max(total - BG_FADE_OUT, start), total
        else:
            fade_at, end = stop, min(stop + (fade or BG_FADE_OUT), total)
        if end > start:
            tracks.append((sound_path(name), SOUNDS[name][1], start, fade_at, end))
    return tracks


def duck_spans(speech):
    """把說話區間合併：兩句之間短到來不及恢復音量的，就當成同一段。"""
    spans = []
    for s, e in speech:
        if spans and s - DUCK_RAMP <= spans[-1][1] + DUCK_RAMP:
            spans[-1][1] = max(spans[-1][1], e)
        else:
            spans.append([s, e])
    return spans


def duck_expr(speech):
    """給 ffmpeg volume 濾鏡的運算式：說話時降低 DUCK_DB，前後各用 DUCK_RAMP 秒平滑過渡。
    合併後的區間（含過渡）互不重疊，所以可以直接相加。"""
    r = DUCK_RAMP
    terms = [f"clip(min((t-{s - r:.3f})/{r},({e + r:.3f}-t)/{r}),0,1)" for s, e in duck_spans(speech)]
    return f"pow(10,{DUCK_DB / 20}*({'+'.join(terms)}))" if terms else "1"


def mix(voice_path, out_path, rate, overlays, tracks, speech):
    """用 ffmpeg 把疊加音效和背景混進人聲軌。"""
    inputs, chains, labels = ["-i", str(voice_path)], [], ["[0:a]"]
    fmt = f"aformat=channel_layouts=mono,aresample={rate}"
    for t, name in overlays:
        k = len(labels)
        path = sound_path(name)
        inputs += ["-i", str(path)]
        chains.append(f"[{k}:a]{fmt},volume={gain_db(path, SOUNDS[name][1]):.2f}dB,"
                      f"adelay={t * 1000:.0f}:all=1[s{k}]")
        labels.append(f"[s{k}]")
    duck = duck_expr(speech)
    for path, rel_db, start, fade_at, end in tracks:
        k = len(labels)
        inputs += ["-stream_loop", "-1", "-i", str(path)]
        # asetnsamples 把 frame 切成 20 毫秒，volume 的運算式才會逐小段更新
        # 壓縮：比這段背景的平均音量大 BG_COMP_ABOVE dB 以上的部分壓小（鋼琴曲樂句變大聲時才不會蓋過說話）
        threshold = max(10 ** ((float(LOUDNESS) + (rel_db or 0) + BG_COMP_ABOVE) / 20), 0.001)
        chains.append(
            f"[{k}:a]{fmt},volume={gain_db(path, rel_db):.2f}dB,"
            f"acompressor=threshold={threshold:.5f}:ratio={BG_COMP_RATIO}:attack=20:release=400:knee=4,"
            f"atrim=duration={end - start:.3f},"
            f"afade=t=in:d={max(min(BG_FADE_IN, fade_at - start), 0.01):.3f},"
            f"afade=t=out:st={fade_at - start:.3f}:d={max(end - fade_at, 0.01):.3f},"
            f"adelay={start * 1000:.0f}:all=1,asetnsamples=n={rate // 50}:p=0,"
            f"volume='{duck}':eval=frame[s{k}]")
        labels.append(f"[s{k}]")
    chains.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0[out]")
    run_ffmpeg([*inputs, "-filter_complex", ";".join(chains), "-map", "[out]", "-ac", "1", str(out_path)])


def export_mp3(src, mp3_path):
    """響度標準化：先量整集響度，再用同一個固定增益調到 LOUDNESS，零星的峰值交給限制器壓住。
    不用 loudnorm：Gemini 配音的峰值本來就接近 0 dBFS，loudnorm 的固定增益模式做不到，
    會退回動態模式，在停頓時把背景拉大聲。"""
    gain = float(LOUDNESS) - measure_lufs(src)
    run_ffmpeg(["-i", str(src), "-af",
                # 先升取樣再壓峰值，才抓得到取樣點之間的峰值（不然 mp3 的真峰值會超過 0 dB）
                f"volume={gain:.2f}dB,aresample=96000,alimiter=limit={PEAK_LIMIT}:attack=5:release=50:level=false",
                "-ac", "1", "-ar", "44100", "-b:a", "96k", str(mp3_path)])


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
    ap.add_argument("--bgm", help="整集用這個背景音樂（循環、結尾淡出），蓋掉腳本裡的 [背景]")
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

    items, shared = expand_shared(parse_script(args.script))
    lines = [i for i in items if i[0] == "line"]
    pauses = sum(i[1] for i in items if i[0] == "pause")
    est = expected_seconds([i[3] for i in lines]) + pauses + LINE_GAP_SEC * len(lines)
    print(f"模型：{MODEL}")
    print(f"{len(lines)} 句、{sum(len(TAG_RE.sub('', i[3])) for i in lines)} 字、停頓 {pauses:.0f} 秒，"
          f"預估長度約 {est / 60:.1f} 分鐘")
    for speaker in CHARACTERS:   # 只列這集有台詞的角色（CHARACTERS 裡也有其他系列的角色）
        if count := sum(1 for i in lines if i[1] == speaker):
            print(f"  {speaker}：{count} 句")
    if shared:
        print(f"  其中 {len(shared)} 句是共用片段（快取在 {SHARED_DIR}，生成過就不再花額度）")

    if args.dry_run:
        if missing := check_sounds(items, args.bgm):
            print(f"缺少：{'、'.join(missing)}（素材下載來源見 assets/SOURCES.md）")
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
        shared = {i for i in shared if i <= cut}
        stem += f"_first{args.limit}"
    # 素材有問題要在呼叫 API 之前就停下，不然額度花了卻組不成一集
    if missing := check_sounds(items, args.bgm):
        sys.exit(f"缺少：{'、'.join(missing)}（素材下載來源見 assets/SOURCES.md）")
    for _, path in sound_files(items, args.bgm):
        measure_lufs(path)
    min_interval = 60 / args.rpm + 1
    line_idx = [i for i, it in enumerate(items) if it[0] == "line"]
    # 一批 = (角色, 是否共用)；共用的台詞自成一批，快取放 SHARED_DIR
    groups = list(dict.fromkeys((items[i][1], i in shared) for i in line_idx))
    if shared:
        SHARED_DIR.mkdir(parents=True, exist_ok=True)
    if args.per_line:
        print(f"逐句模式：最多 {len(line_idx)} 次請求（已快取的會略過）")
    else:
        print(f"分批模式：每個角色一次請求，共 {len(groups)} 批（已快取的不花額度）")

    rendered = {}
    failed = []
    if not args.per_line:
        for sp, is_shared in groups:
            idxs = [i for i in line_idx if items[i][1] == sp and (i in shared) == is_shared]
            pieces = synthesize_batch(client, sp, [items[i][2:] for i in idxs],
                                      SHARED_DIR if is_shared else cache, min_interval,
                                      label=f"{sp}（共用）" if is_shared else sp)
            if pieces:
                rendered.update(zip(idxs, pieces))
            elif args.fallback:
                print(f"    {sp} 的台詞改用逐句模式生成（會多花 {len(idxs)} 次請求）")
            else:
                failed.append(f"{sp}（共用）" if is_shared else sp)
        if failed:
            sys.exit(
                f"\n{'、'.join(failed)} 切不開，先停下來，不自動改成逐句生成（避免用光額度）。\n"
                "批次音檔已存在 build/segments/，可以用 --inspect 看停頓長度；\n"
                "要改成逐句生成切不開的角色，請加上 --fallback 再跑一次（其他角色會直接用快取）；\n"
                "或在批次音檔旁寫 .cuts.txt 人工指定每句的開始、結束秒數（不花額度）。"
            )

    for n, i in enumerate(line_idx, 1):
        if i in rendered:
            continue
        _, speaker, direction, text = items[i]
        audio, cached = synthesize(client, speaker, direction, text,
                                   SHARED_DIR if i in shared else cache, min_interval)
        print(f"[{n}/{len(line_idx)}] {'（快取）' if cached else ''}{speaker}：{text[:20]}…")
        rendered[i] = audio

    rate = next(iter(rendered.values())).rate
    if any(a.rate != rate for a in rendered.values()):
        sys.exit("各段音訊的取樣率不一致，請刪掉 build/segments/ 後重跑")

    episode, overlays, backgrounds, speech = assemble(
        items, rendered, rate, lambda name: decode_sound(name, rate))
    wav_path = build / f"{stem}.wav"
    episode.save(wav_path)
    print(f"已輸出 {wav_path}（{episode.seconds / 60:.1f} 分鐘）")

    if not find_ffmpeg():
        print("找不到能用的 ffmpeg（需要 4.4 以上），略過 mp3 輸出與響度標準化")
        return

    tracks = background_tracks(backgrounds, episode.seconds, args.bgm)
    if overlays or tracks:
        mixed = build / f"{stem}_mix.wav"
        mix(wav_path, mixed, rate, overlays, tracks, speech)
        print(f"已混入 {len(overlays)} 個疊加音效、{len(tracks)} 段背景：{mixed}")
    else:
        mixed = wav_path
    mp3_path = build / f"{stem}.mp3"
    export_mp3(mixed, mp3_path)
    print(f"已輸出 {mp3_path}")


if __name__ == "__main__":
    main()
