"""不連網的測試：用 tests/fake 裡的假 SDK 和合成音訊。

執行：python -m unittest discover -s tests -v
"""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["NO_DOTENV"] = "1"   # 不讀真的 .env：.env 優先，會蓋掉測試設的假 key（子程序也會繼承這個設定）
import generate_episode as g  # noqa: E402

EPISODE = ROOT / "episodes" / "ep01_moon.md"
EPISODE_SFX = ROOT / "episodes" / "ep02_fish.md"   # 有音效與背景標記的樣本
FAKE = ROOT / "tests" / "fake"
R = 24000
_T = array("h", [8000 if (k // 40) % 2 else -8000 for k in range(480)]).tobytes()


def tone(sec):
    n = int(R * sec)
    return (_T * (n // 480 + 1))[: n * 2]


def quiet(sec):
    """很輕的雜訊（峰值約 5%），像換氣。"""
    n = int(R * sec)
    return array("h", [1600 if (k // 40) % 2 else -1600 for k in range(n)]).tobytes()


def sil(sec):
    return b"\0\0" * int(R * sec)


def write_wav(path, pcm, rate=R):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def read_wav(path):
    with wave.open(str(path)) as wf:
        return array("h", wf.readframes(wf.getnframes())), wf.getframerate()


FAKE_ASSETS = None


def setUpModule():
    """合成的假素材（不靠使用者下載的真素材）。副檔名照 SOUNDS，內容都是 WAV，ffmpeg 會自己判斷格式。"""
    global FAKE_ASSETS
    FAKE_ASSETS = Path(tempfile.mkdtemp())
    for filename, _ in g.SOUNDS.values():
        write_wav(FAKE_ASSETS / filename, tone(2))


def tearDownModule():
    shutil.rmtree(FAKE_ASSETS, ignore_errors=True)


def run(*args, mode="good", free="fake-free", paid="", assets=None, episode=EPISODE):
    """在暫存資料夾裡用假 SDK 執行主程式，回傳 (exit code, 輸出)。
    金鑰明確傳入，蓋過使用者 .env 裡的真金鑰（環境變數優先於 .env）。"""
    tmp = tempfile.mkdtemp()
    if not assets and FAKE_ASSETS:
        shutil.rmtree(FAKE_ASSETS / "shared", ignore_errors=True)
    try:
        env = dict(os.environ, PYTHONPATH=str(FAKE), FAKE_MODE=mode, PYTHONIOENCODING="utf-8",
                   GEMINI_API_KEY=free, GEMINI_API_KEY_PAID=paid,
                   ASSETS_DIR=str(assets or FAKE_ASSETS),
                   ASR_CHECK="0")   # 合成音訊聽不出字，不做內容核對（另有單元測試）
        p = subprocess.run([sys.executable, str(ROOT / "generate_episode.py"), str(episode),
                            "--rpm", "6000", *args], cwd=tmp, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode, p.stdout + p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class TestScript(unittest.TestCase):
    def test_parse(self):
        items, shared = g.expand_shared(g.parse_script(EPISODE))
        lines = [i for i in items if i[0] == "line"]
        self.assertEqual(len(lines), 48)
        self.assertEqual(len(shared), 9)
        self.assertEqual({l[1] for l in lines}, {"旁白", "栗栗", "棉棉", "咕咕爺爺"})

    def test_directions_are_short_english(self):
        # 3.8 TTS 會把文字全部念出來，所以導演提示只能放在 style，而且要短
        items, _ = g.expand_shared(g.parse_script(EPISODE))
        for _, sp, d, text in (i for i in items if i[0] == "line"):
            self.assertTrue(d.isascii(), f"導演提示不是英文：{d}")
            self.assertNotIn("{", text)
            self.assertNotIn("[停頓", text)


class TestPipeline(unittest.TestCase):
    def test_batch_mode_requests(self):
        code, out = run()
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("一次生成並切開"), 5, out)   # 1 批共用 + 4 批角色

    def test_timeline_only_skips_audio_export(self):
        code, out = run("--limit", "5", "--timeline-only")
        self.assertEqual(code, 0, out)
        self.assertIn("timeline.json", out)
        self.assertNotIn("_first5.mp3", out)
        self.assertNotIn("_first5.wav", out)

    def test_wav_response(self):
        code, out = run("--limit", "5", mode="wav")
        self.assertEqual(code, 0, out)

    def test_stops_when_audio_too_long(self):
        code, out = run("--limit", "5", mode="long")
        self.assertNotEqual(code, 0)
        self.assertIn("遠超過預期", out)


class TestApiKeys(unittest.TestCase):
    def test_switches_to_paid_key_when_free_quota_used_up(self):
        code, out = run("--limit", "5", mode="quota", paid="fake-paid")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("額度用完了，改用付費 key"), 1, out)

    def test_stops_without_paid_key(self):
        code, out = run("--limit", "5", mode="quota")
        self.assertNotEqual(code, 0)
        self.assertIn("免費 key今天在這個模型的額度已用完", out)

    def test_no_paid_flag_keeps_free_only(self):
        code, out = run("--limit", "5", "--no-paid", mode="quota", paid="fake-paid")
        self.assertNotEqual(code, 0)
        self.assertIn("金鑰：只用免費 key", out)
        self.assertNotIn("額度用完了，改用付費 key", out)

    def test_missing_keys(self):
        code, out = run("--limit", "5", free="")
        self.assertNotEqual(code, 0)
        self.assertIn("找不到 API 金鑰", out)

    def test_load_env(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / ".env").write_text(
                "# 註解\nT_ENV_A=abc  # 行尾註解\nT_ENV_B=\"x # y\"\nT_ENV_C=from-file\nT_ENV_D=\n",
                encoding="utf-8")
            os.environ["T_ENV_C"] = "from-shell"
            os.environ["T_ENV_D"] = "from-shell"
            saved = os.environ.pop("NO_DOTENV", None)
            try:
                g.load_env(tmp / ".env")
            finally:
                if saved is not None:
                    os.environ["NO_DOTENV"] = saved
            self.assertEqual(os.environ["T_ENV_A"], "abc")
            self.assertEqual(os.environ["T_ENV_B"], "x # y")
            self.assertEqual(os.environ["T_ENV_C"], "from-file")    # .env 優先
            self.assertEqual(os.environ["T_ENV_D"], "from-shell")   # .env 留空的不覆蓋
        finally:
            for k in ("T_ENV_A", "T_ENV_B", "T_ENV_C", "T_ENV_D"):
                os.environ.pop(k, None)
            shutil.rmtree(tmp, ignore_errors=True)


class TestSilenceSplit(unittest.TestCase):
    texts = [i[3] for i in g.parse_script(EPISODE) if i[0] == "line" and i[1] == "旁白"]

    def synth(self, seed, gap_range):
        random.seed(seed)
        pcm, truth = bytearray(sil(0.3)), []
        for k, t in enumerate(self.texts):
            clean = g._norm(t)
            dur = len(clean) / random.uniform(2.2, 4.0)
            pieces = [p for p in g.PUNCT_RE.split(g.TAG_RE.sub("", t)) if p]
            seg = b""
            for j, _ in enumerate(pieces):
                seg += tone(dur / len(pieces))
                if j < len(pieces) - 1:
                    seg += sil(random.uniform(0.3, 1.6))
            truth.append(len(seg) / 2 / R)
            pcm += seg
            if k < len(self.texts) - 1:
                pcm += sil(random.uniform(*gap_range))
        return g.Audio(bytes(pcm + sil(0.4)), R), truth

    def test_clear_gaps_split_correctly(self):
        for seed in range(10):
            audio, truth = self.synth(seed, (2.5, 3.0))
            pieces, why = g.split_on_silence(audio, self.texts)
            self.assertIsNotNone(pieces, why)
            for p, t in zip(pieces, truth):
                self.assertAlmostEqual(p.seconds - 0.1, t, delta=0.15)

    def test_ambiguous_gaps_refuse_instead_of_cutting_wrong(self):
        for seed in range(10):
            audio, _ = self.synth(seed, (1.0, 2.5))
            pieces, _ = g.split_on_silence(audio, self.texts)
            self.assertIsNone(pieces)

    def test_blip_inside_pause_is_merged(self):
        pcm = tone(2) + sil(1.4) + quiet(0.04) + sil(1.4) + tone(2)   # 輕輕的雜訊
        pieces, why = g.split_on_silence(g.Audio(pcm, R), ["一二三四五六", "七八九十一二"])
        self.assertIsNotNone(pieces, why)

    def test_loud_short_syllable_is_not_swallowed(self):
        # 句首的短音節（例如「咕咕」的第一個咕，約 0.15 秒、很響）不能被當雜訊併進前面的停頓
        pcm = tone(2) + sil(1.4) + tone(0.15) + sil(0.06) + tone(2)
        runs, _, _ = g._silent_runs(g.Audio(pcm, R))
        self.assertEqual(len(runs), 2)


class TestWhisperCheck(unittest.TestCase):
    """用假的辨識結果測 split_with_whisper：同音字要容忍，內容真的不同還是要被擋下。"""

    TEXTS = ["晚安，栗栗。", "你們先看看路邊這朵小白花"]

    def split(self, heard1, heard2):
        pcm = tone(2) + sil(1.0) + tone(3)   # 第 1 句 0–2 秒，第 2 句 3–6 秒
        chars = []
        for heard, t0, t1 in ((heard1, 0.0, 2.0), (heard2, 3.0, 6.0)):
            step = (t1 - t0) / len(heard)
            chars += [(c, t0 + i * step, t0 + (i + 1) * step) for i, c in enumerate(heard)]
        old, g.transcribe_chars = g.transcribe_chars, lambda audio: chars
        try:
            return g.split_with_whisper(g.Audio(pcm, R), self.TEXTS)
        finally:
            g.transcribe_chars = old

    def test_homophones_are_tolerated(self):
        self.assertEqual(g._sounds("栗栗"), g._sounds("莉莉"))
        pieces, why = self.split("晚安莉莉", "你们先看看路边这朵小白花")   # 同音字＋簡體
        self.assertIsNotNone(pieces, why)

    def test_different_content_is_still_rejected(self):
        self.assertNotEqual(g._sounds("栗栗"), g._sounds("棉棉"))
        pieces, _ = self.split("月亮離我們非常遠", "你們先看看路邊這朵小白花")
        self.assertIsNone(pieces)

    def test_drawn_out_sound_tilde_is_not_a_char(self):
        # Whisper 把拉長的「啊」寫成「啊~~~」，~ 不能算成多出來的字（ep03 棉棉）
        heard = g._norm("啊~~~好困喔")
        self.assertEqual(heard, "啊好困喔")
        self.assertIsNone(g._content_mismatch(1, heard, "啊……好睏喔。<yawn>"))


class TestSilenceSplitContentCheck(unittest.TestCase):
    """靜音切開、句數也對，但內容錯位（模型多念一句又有兩句黏在一起）時，要被擋下來。"""

    TEXTS = ["晚安，栗栗。", "你們先看看路邊這朵小白花"]

    def check(self, heard):
        pieces = [g.Audio(tone(1), R), g.Audio(tone(1), R)]
        it = iter(heard)
        old, g.transcribe_chars = g.transcribe_chars, lambda audio: [(c, 0.0, 0.1) for c in next(it)]
        old_flag, g.ASR_CHECK = g.ASR_CHECK, True
        try:
            return g.check_pieces(pieces, self.TEXTS)
        finally:
            g.transcribe_chars, g.ASR_CHECK = old, old_flag

    def test_matching_content_passes(self):
        self.assertIsNone(self.check(["晚安莉莉", "你们先看看路边这朵小白花"]))

    def test_shifted_content_is_rejected(self):
        self.assertIn("第 2 句", self.check(["晚安栗栗", "晚安栗栗"]))


class TestShared(unittest.TestCase):
    """共用片段：[共用 名稱] 展開成 episodes/shared.md 的內容；共用台詞自成一批，第二集起直接用快取。"""

    EP = ROOT / "episodes" / "ep04_stars.md"

    def test_expand(self):
        items, shared = g.expand_shared(g.parse_script(self.EP))
        self.assertFalse(any(it[0] == "shared" for it in items))
        self.assertEqual(len(shared), 9)   # 開場 2 句、放鬆 6 句、咕咕爺爺登場 1 句
        self.assertEqual(items[0], ("bg", ("搖籃曲",), None))
        self.assertTrue(all(items[i][0] == "line" and items[i][1] == "旁白" for i in shared))
        self.assertIn(("sfx", "貓頭鷹", True, 0.0), items)

    def test_unknown_name_stops(self):
        with self.assertRaises(SystemExit):
            g.expand_shared([("shared", "不存在")])

    def test_shared_batch_is_cached_across_episodes(self):
        with tempfile.TemporaryDirectory() as d:
            assets = Path(d)
            for filename, _ in g.SOUNDS.values():
                shutil.copy(FAKE_ASSETS / filename, assets / filename)
            code, out = run(assets=assets, episode=self.EP)
            self.assertEqual(code, 0, out)
            self.assertIn("共 5 批", out)
            self.assertTrue(list((assets / "shared").glob("batch_*.wav")))
            code, out = run(assets=assets, episode=self.EP)   # 另一個 build/（新的一集），共用那批要用快取
            self.assertEqual(code, 0, out)
            self.assertIn("（快取）旁白（共用）", out)
            self.assertNotIn("（快取）栗栗", out)


class TestManualCuts(unittest.TestCase):
    """人工切點（<批次>.cuts.txt）：照秒數切；行數不合、秒數超出音檔都要停下來，不猜。"""

    def cut(self, text, count):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "batch_x.cuts.txt"
            path.write_text(text, encoding="utf-8")
            return g.manual_cuts(g.Audio(tone(2) + sil(1.0) + tone(3), R), path, count)

    def test_cuts_by_seconds_and_skips_comments(self):
        pieces = self.cut("# 註解\n0 2   # 第一句\n\n3.0 6.0\n", 2)
        self.assertEqual([round(p.seconds, 3) for p in pieces], [2.0, 3.0])

    def test_multiple_spans_are_joined(self):
        pieces = self.cut("0 1 3 4\n4.5 6\n", 2)   # 第 1 句跳過 1–3 秒
        self.assertEqual([round(p.seconds, 3) for p in pieces], [2.0, 1.5])

    def test_ear_checked_line_skips_asr_check_only_for_that_line(self):
        pieces = self.cut("0 2 人耳確認  # 氣音，使用者聽過\n3.0 6.0\n", 2)
        self.assertEqual([p.ear_checked for p in pieces], [True, False])
        self.assertEqual([round(p.seconds, 3) for p in pieces], [2.0, 3.0])
        old = g.ASR_CHECK
        try:
            g.ASR_CHECK = True
            seen = []
            orig = g.transcribe_chars
            g.transcribe_chars = lambda piece: seen.append(piece) or [(c, 0, 0) for c in "第二句"]
            self.assertIsNone(g.check_pieces(pieces, ["第一句", "第二句"]))
            self.assertEqual(seen, [pieces[1]])   # 只核對沒標記的那句
        finally:
            g.ASR_CHECK = old
            g.transcribe_chars = orig

    def test_sound_inserted_between_spans_but_not_asr_checked(self):
        orig, g.decode_sound = g.decode_sound, lambda name, rate: sil(0.5)
        try:
            pieces = self.cut("0 1 音效:哈欠旁白 1.5 2\n音效:哈欠旁白 3 6 音效:哈欠旁白\n", 2)
        finally:
            g.decode_sound = orig
        self.assertEqual([round(p.seconds, 3) for p in pieces], [2.0, 4.0])
        self.assertEqual([round(p.speech_only.seconds, 3) for p in pieces], [1.5, 3.0])
        old, orig = g.ASR_CHECK, g.transcribe_chars
        try:
            g.ASR_CHECK, seen = True, []
            g.transcribe_chars = lambda piece: seen.append(piece) or [(c, 0, 0) for c in "第一句"]
            g.check_pieces(pieces[:1], ["第一句"])
            self.assertIs(seen[0], pieces[0].speech_only)   # 只聽台詞，不聽接進來的音效
        finally:
            g.ASR_CHECK, g.transcribe_chars = old, orig

    def test_sound_only_line_replaces_whole_sentence_and_is_asr_checked(self):
        orig, g.decode_sound = g.decode_sound, lambda name, rate: sil(0.5)
        try:
            pieces = self.cut("0 2\n音效:哈欠旁白   # 整句換成另一段錄音\n", 2)
        finally:
            g.decode_sound = orig
        self.assertEqual([round(p.seconds, 3) for p in pieces], [2.0, 0.5])
        self.assertFalse(hasattr(pieces[1], "speech_only"))
        old, orig = g.ASR_CHECK, g.transcribe_chars
        try:
            g.ASR_CHECK, seen = True, []
            g.transcribe_chars = lambda piece: seen.append(piece) or [(c, 0, 0) for c in "晚安"]
            g.check_pieces(pieces[1:], ["晚安"])
            self.assertIs(seen[0], pieces[1])   # 核對的是換進來的那段錄音
        finally:
            g.ASR_CHECK, g.transcribe_chars = old, orig

    def test_wrong_count_or_range_stops(self):
        for text, count in (("0 2\n", 2), ("0 2\n3 9\n", 2), ("2 1\n3 6\n", 2), ("0 2 3\n3 6\n", 2),
                            ("0 3 2 4\n4.5 6\n", 2),
                            ("0 1 音效:沒有這個 1.5 2\n3 6\n", 2),   # 不在 SOUNDS 裡
                            ("音效:沒有這個\n3 6\n", 2),            # 只有音效，但不在 SOUNDS 裡
                            ("音效:哈欠旁白 abc\n3 6\n", 2),        # 音效後面接看不懂的字
                            ("0 音效:哈欠旁白 1 3 6\n3 6\n", 2)):    # 插在一組秒數中間
            with self.subTest(text=text), self.assertRaises(SystemExit):
                self.cut(text, count)


def rms_db(samples):
    import math
    return 10 * math.log10(sum(x * x for x in samples) / len(samples) + 1e-9)


class TestSounds(unittest.TestCase):
    def parse(self, body):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "ep.md").write_text(body, encoding="utf-8")
            return g.parse_script(tmp / "ep.md")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_markers(self):
        items = self.parse("[背景 搖籃曲]\n[音效 開場鈴]\n[音效 貓頭鷹 疊]\n@旁白 晚安。\n[背景 停]\n")
        self.assertEqual(items[:3], [("bg", ("搖籃曲",), None), ("sfx", "開場鈴", False, 0.0),
                                     ("sfx", "貓頭鷹", True, 0.0)])
        self.assertEqual(items[-1], ("bg", (), None))

    def test_parse_layered_background_and_long_fade(self):
        items = self.parse("[背景 夜晚蟲鳴 河水]\n[停頓 600秒]\n[背景 停 180秒]\n")
        self.assertEqual(items, [("bg", ("夜晚蟲鳴", "河水"), None), ("pause", 600.0), ("bg", (), 180.0)])
        with self.assertRaises(SystemExit):
            self.parse("[背景 夜晚蟲鳴 打雷]\n")

    def test_unknown_sound_stops(self):
        with self.assertRaises(SystemExit) as cm:
            self.parse("@旁白 晚安。\n[音效 打雷]\n")
        self.assertIn("未知音效「打雷」", str(cm.exception))

    def test_assemble_timeline(self):
        items = [("bg", ("搖籃曲",), None), ("sfx", "開場鈴", False, 0.0), ("line", "旁白", "", "一"),
                 ("sfx", "貓頭鷹", True, 0.0), ("pause", 2.0), ("line", "旁白", "", "二"), ("bg", (), None)]
        rendered = {2: g.Audio(tone(1), R), 5: g.Audio(tone(1), R)}
        ep, overlays, backgrounds, speech = g.assemble(items, rendered, R, lambda name: sil(0.5))
        gap = g.LINE_GAP_SEC
        end1 = 1.5 + gap
        self.assertAlmostEqual(ep.seconds, end1 + 2 + 1 + gap, places=3)   # 插入的音效有佔時間
        self.assertEqual(overlays, [(end1, "貓頭鷹")])                     # 疊上去的不佔時間
        self.assertEqual(speech, [(0.5, 1.5), (end1 + 2, end1 + 3)])
        self.assertEqual(backgrounds, [("搖籃曲", 0.0, ep.seconds, None)])

    def test_write_timeline(self):
        items = [("sfx", "開場鈴", False, 0.0), ("line", "旁白", "warm", "一<chuckle>"),
                 ("pause", 2.0), ("line", "栗栗", "", "二")]
        rendered = {1: g.Audio(tone(1), R), 3: g.Audio(tone(1), R)}
        ep, _, _, speech = g.assemble(items, rendered, R, lambda name: sil(0.5))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "t.json"
            g.write_timeline(items, speech, ep.seconds, path)
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(data["seconds"], ep.seconds, places=3)
        self.assertEqual([(l["speaker"], l["text"]) for l in data["lines"]], [("旁白", "一<chuckle>"), ("栗栗", "二")])
        self.assertEqual(data["lines"][0]["start"], 0.5)
        self.assertAlmostEqual(data["lines"][1]["start"], 1.5 + g.LINE_GAP_SEC + 2, places=3)

    def test_volume_marker_applies_until_next_marker(self):
        # [音量 -6dB] 之後的台詞都變小聲，直到下一個 [音量]；不影響送出的內容（快取鍵）
        items = self.parse("@旁白 一。\n[音量 -6dB]\n@旁白 二。\n@旁白 三。\n[音量 0dB]\n@旁白 四。\n")
        self.assertEqual([i for i in items if i[0] == "vol"], [("vol", -6.0), ("vol", 0.0)])
        lines = [k for k, i in enumerate(items) if i[0] == "line"]
        ep, _, _, speech = g.assemble(items, {k: g.Audio(tone(1), R) for k in lines}, R, None)
        a = array("h", ep.pcm)
        levels = [rms_db(a[int((s + 0.1) * R):int((e - 0.1) * R)]) for s, e in speech]
        for got, want in zip(levels, [0, -6, -6, 0]):
            self.assertAlmostEqual(got - levels[0], want, delta=0.1)

    def test_trim_replaces_line_tail(self):
        # [音效 吸氣1 剪 0.4秒]：剪掉前一句的句間空白和句尾 0.4 秒（被切斷的半口氣），再接上音效
        items = self.parse("@旁白 吸氣。\n[音效 吸氣1 剪 0.4秒]\n")
        self.assertEqual(items[-1], ("sfx", "吸氣1", False, 0.4))
        ep, _, _, speech = g.assemble(items, {0: g.Audio(tone(2), R)}, R, lambda name: sil(1))
        self.assertAlmostEqual(ep.seconds, 2 - 0.4 + 1, places=3)
        self.assertEqual(speech, [(0.0, 1.6)])
        with self.assertRaises(SystemExit):   # 前面不是台詞就不能剪
            self.parse("@旁白 吸氣。\n[停頓 1秒]\n[音效 吸氣1 剪 0.4秒]\n")

    def test_auto_trim_finds_cut_off_breath(self):
        breath = array("h", [600 if (k // 40) % 2 else -600 for k in range(int(R * 0.4))]).tobytes()
        secs, why = g.trailing_breath(g.Audio(tone(2) + sil(0.4) + breath, R))
        self.assertAlmostEqual(secs, 0.45, delta=0.06, msg=why)
        self.assertEqual(self.parse("@旁白 吸氣。\n[音效 吸氣1 剪 自動]\n")[-1], ("sfx", "吸氣1", False, "自動"))

    def test_auto_trim_refuses_when_unsure(self):
        # 分不清就不剪：剪到台詞比多聽到半口氣糟糕得多
        breath = array("h", [600 if (k // 40) % 2 else -600 for k in range(int(R * 0.4))]).tobytes()
        cases = {
            "句尾就是台詞": tone(2),
            "氣音前面沒有停頓": tone(2) + breath,
            "停頓後面是大聲的字": tone(2) + sil(0.4) + tone(0.3),
            "句尾的聲音太長": tone(2) + sil(0.4) + breath * 4,
        }
        for name, pcm in cases.items():
            secs, why = g.trailing_breath(g.Audio(pcm, R))
            self.assertEqual(secs, 0.0, f"{name}：{why}")

    def test_assemble_layered_backgrounds(self):
        items = [("bg", ("搖籃曲",), None), ("pause", 10.0), ("bg", ("夜晚蟲鳴", "河水"), None),
                 ("pause", 20.0), ("bg", (), 5.0), ("pause", 5.0)]
        _, _, backgrounds, _ = g.assemble(items, {}, R, None)
        self.assertEqual(backgrounds, [("搖籃曲", 0.0, 10.0, None),
                                       ("夜晚蟲鳴", 10.0, 30.0, 5.0), ("河水", 10.0, 30.0, 5.0)])

    def test_background_tracks(self):
        fo = g.BG_FADE_OUT
        lull, crick = g.sound_path("搖籃曲"), g.sound_path("夜晚蟲鳴")
        tracks = g.background_tracks([("搖籃曲", 0.0, 50.0, None), ("夜晚蟲鳴", 50.0, None, None)], 100.0, None)
        # 換背景時交叉淡化；沒停的在結尾前淡出
        self.assertEqual([t[0] for t in tracks], [lull, crick])
        self.assertEqual(tracks[0][2:], (0.0, 50.0, 50.0 + fo))
        self.assertEqual(tracks[1][2:], (50.0, 100.0 - fo, 100.0))
        # 停在快結尾的地方：淡出被壓縮到結尾為止
        self.assertEqual(g.background_tracks([("搖籃曲", 90.0, 95.0, None)], 97.0, None)[0][2:], (90.0, 95.0, 97.0))
        # [背景 停 N秒] 指定淡出長度
        self.assertEqual(g.background_tracks([("河水", 10.0, 400.0, 180.0)], 600.0, None)[0][2:],
                         (10.0, 400.0, 580.0))
        # --bgm 蓋掉腳本裡的背景
        tracks = g.background_tracks([("搖籃曲", 0.0, 50.0, None)], 100.0, "x.mp3")
        self.assertEqual(tracks, [(Path("x.mp3"), g.BGM_DB, 0.0, 100.0 - fo, 100.0)])

    def test_duck_spans_merge_short_gaps(self):
        r = g.DUCK_RAMP
        spans = g.duck_spans([(0, 2), (2 + 2 * r - 0.1, 5), (5 + 2 * r + 0.5, 8)])
        self.assertEqual(spans, [[0, 5], [5 + 2 * r + 0.5, 8]])

    @unittest.skipUnless(shutil.which("ffmpeg"), "需要 ffmpeg")
    def test_mix_overlay_position_and_ducking(self):
        tmp = Path(tempfile.mkdtemp())
        old = g.ASSETS_DIR
        try:
            g.ASSETS_DIR = FAKE_ASSETS
            voice, out = tmp / "voice.wav", tmp / "mix.wav"
            write_wav(voice, sil(12))   # 人聲軌是靜音，混出來的就只有音效和背景
            # 疊加音效：起點要準
            g.mix(voice, out, R, [(1.5, "貓頭鷹")], [], [])
            a, _ = read_wav(out)
            onset = next(k for k, x in enumerate(a) if abs(x) > 100) / R
            self.assertAlmostEqual(onset, 1.5, delta=0.02)
            # 背景：4–6 秒有人說話，那段要比沒人說話時小 DUCK_DB
            track = (g.sound_path("搖籃曲"), -20, 0.0, 10.0, 12.0)
            g.mix(voice, out, R, [], [track], [(4.0, 6.0)])
            a, _ = read_wav(out)
            ducked = rms_db(a[int(4.2 * R):int(5.8 * R)])
            normal = rms_db(a[int(7.2 * R):int(9.5 * R)])
            self.assertAlmostEqual(ducked - normal, g.DUCK_DB, delta=0.5)
            self.assertLess(rms_db(a[int(11.9 * R):]), normal - 20)   # 結尾已淡出
        finally:
            g.ASSETS_DIR = old
            shutil.rmtree(tmp, ignore_errors=True)

    def test_full_episode_with_sounds(self):
        code, out = run(episode=EPISODE_SFX)
        self.assertEqual(code, 0, out)
        self.assertIn("已混入 1 個疊加音效、7 段背景", out)

    @unittest.skipUnless(shutil.which("ffmpeg"), "需要 ffmpeg")
    def test_export_hits_loudness_without_clipping(self):
        # 真的配音峰值接近 0 dBFS、整體卻偏小聲：要放大到目標響度，又不能讓峰值爆掉
        tmp = Path(tempfile.mkdtemp())
        try:
            # 小聲的句子（峰值約 -20 dBFS）偶爾夾著頂到 0 dBFS 的尖峰，再加長停頓
            speech = array("h", [3000 if (k // 40) % 2 else -3000 for k in range(R)])
            for k in range(0, R, 12000):   # 每 0.5 秒一個極短的尖峰（像爆破音）
                speech[k:k + 6] = array("h", [32000] * 6)
            write_wav(tmp / "in.wav", (speech.tobytes() + sil(3)) * 8)
            self.assertGreater(float(g.LOUDNESS) - g.measure_lufs(tmp / "in.wav"), 3)   # 要放大，限制器才有事做
            g.export_mp3(tmp / "in.wav", tmp / "out.mp3")
            p = g.run_ffmpeg(["-i", str(tmp / "out.mp3"), "-af", "ebur128=framelog=quiet:peak=true",
                              "-f", "null", "-"])
            loudness = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)[-1])
            peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)[-1])
            self.assertAlmostEqual(loudness, float(g.LOUDNESS), delta=1.0)
            self.assertLessEqual(peak, -1.0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @unittest.skipUnless(g.find_ffmpeg(), "需要 4.4 以上的 ffmpeg")
    def test_find_ffmpeg_skips_old_version_first_on_path(self):
        # PATH 最前面的 ffmpeg 不能用（像 miniconda 附的 4.3）：要略過它，用後面能用的那個
        tmp = Path(tempfile.mkdtemp())
        name = "ffmpeg.bat" if os.name == "nt" else "ffmpeg"
        (tmp / name).write_text("@exit /b 1\n" if os.name == "nt" else "#!/bin/sh\nexit 1\n")
        (tmp / name).chmod(0o755)
        old = os.environ.copy()
        try:
            os.environ.pop("FFMPEG", None)
            os.environ["PATH"] = str(tmp) + os.pathsep + os.environ["PATH"]
            g.find_ffmpeg.cache_clear()
            exe = g.find_ffmpeg()
            self.assertIsNotNone(exe)
            self.assertNotEqual(Path(exe).parent, tmp)
            os.environ["FFMPEG"] = str(tmp / name)   # 指定了不能用的就停下，不自己換
            g.find_ffmpeg.cache_clear()
            with self.assertRaises(SystemExit):
                g.find_ffmpeg()
        finally:
            os.environ.clear()
            os.environ.update(old)
            g.find_ffmpeg.cache_clear()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_asset_stops_before_api(self):
        empty = Path(tempfile.mkdtemp())
        try:
            code, out = run("--limit", "5", assets=empty, episode=EPISODE_SFX)
            self.assertNotEqual(code, 0)
            self.assertIn("缺少", out)
            self.assertNotIn("一次生成", out)   # 還沒花到額度
            code, out = run("--dry-run", assets=empty, episode=EPISODE_SFX)
            self.assertEqual(code, 0, out)
            self.assertIn("night_crickets.wav（找不到）", out)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_bgm_flag_overrides_script(self):
        code, out = run("--limit", "5", "--bgm", str(FAKE_ASSETS / g.SOUNDS["搖籃曲"][0]), episode=EPISODE_SFX)
        self.assertEqual(code, 0, out)
        self.assertIn("腳本裡的 [背景] 會被忽略", out)
        self.assertIn("已混入 0 個疊加音效、1 段背景", out)


sys.path.insert(0, str(ROOT / "tools"))
import trim_tails  # noqa: E402


class TestTrimTails(unittest.TestCase):
    """tools/trim_tails.py：只剪「念完 → 安靜 → 一小段大聲的聲音」，分不清就不剪。"""

    TEXT = "晚安，栗栗。"

    @staticmethod
    def chars(text, t0, t1):
        step = (t1 - t0) / len(text)
        return [(c, t0 + i * step, t0 + (i + 1) * step) for i, c in enumerate(text)]

    def tail(self, pcm, text=TEXT, heard="晚安莉莉", end=2.0):
        return trim_tails.find_tail(g.Audio(pcm, R), text, self.chars(heard, 0.0, end))

    def test_breath_after_pause_is_trimmed(self):
        end, msg = self.tail(tone(2) + sil(1.0) + tone(0.5) + sil(0.2))
        self.assertAlmostEqual(end, 2.1, places=2)   # 剪到念完＋0.1 秒，台詞不受影響
        self.assertIn("句尾後", msg)

    def test_final_particle_tone_is_ignored(self):
        # 句尾語氣詞常被寫成同音不同調的字（ep08「好厲害喔」→「好厉害哦」）
        end, _ = self.tail(tone(2) + sil(1.0) + tone(0.5) + sil(0.2), text="好厲害喔。", heard="好厉害哦")
        self.assertAlmostEqual(end, 2.1, places=2)

    def test_clean_tail_is_left_alone(self):
        self.assertEqual(self.tail(tone(2) + sil(1.5)), (None, None))
        # 很輕的氣息（約 -40 dB，ep08 實測念完之後常有）不剪
        breath = array("h", [300 if (k // 40) % 2 else -300 for k in range(int(R * 0.5))]).tobytes()
        self.assertEqual(self.tail(tone(2) + sil(1.0) + breath + sil(0.2)), (None, None))

    def test_unclear_cases_are_not_trimmed(self):
        cases = {
            "最後一個字對不上（Whisper 可能漏聽了句尾）": dict(heard="晚安"),
            "聲音太長，可能是沒辨識到的台詞": dict(pcm=tone(2) + sil(1.0) + tone(2.0) + sil(0.2)),
            "停頓太短": dict(pcm=tone(2) + sil(0.2) + tone(0.5) + sil(0.2)),
            "台詞以聲音標記結尾": dict(text="好睏喔。<yawn>", heard="好困哦"),
        }
        for name, kw in cases.items():
            with self.subTest(name):
                kw.setdefault("pcm", tone(2) + sil(1.0) + tone(0.5) + sil(0.2))
                end, msg = self.tail(**kw)
                self.assertIsNone(end)

    def test_written_cuts_round_trip(self):
        pcm = tone(2) + sil(1.0) + tone(0.5) + sil(1.0) + tone(3)
        a, b = g.Audio(pcm[:int(3.5 * R) * 2], R), g.Audio(pcm[int(4.5 * R) * 2:], R)
        a.start, b.start = 0, int(4.5 * R)
        text = trim_tails.cuts_text("ep99 旁白", [a, b], [2.1, None], R)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "batch_x.cuts.txt"
            path.write_text(text, encoding="utf-8")
            pieces = g.manual_cuts(g.Audio(pcm, R), path, 2)
        self.assertEqual([round(p.seconds, 2) for p in pieces], [2.1, 3.0])


if __name__ == "__main__":
    unittest.main()
