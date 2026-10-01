"""不連網的測試：用 tests/fake 裡的假 SDK 和合成音訊。

執行：python -m unittest discover -s tests -v
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import generate_episode as g  # noqa: E402

EPISODE = ROOT / "episodes" / "ep01_moon.md"
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


def run(*args, mode="good", free="fake-free", paid=""):
    """在暫存資料夾裡用假 SDK 執行主程式，回傳 (exit code, 輸出)。
    金鑰明確傳入，蓋過使用者 .env 裡的真金鑰（環境變數優先於 .env）。"""
    tmp = tempfile.mkdtemp()
    try:
        env = dict(os.environ, PYTHONPATH=str(FAKE), FAKE_MODE=mode, PYTHONIOENCODING="utf-8",
                   GEMINI_API_KEY=free, GEMINI_API_KEY_PAID=paid)
        p = subprocess.run([sys.executable, str(ROOT / "generate_episode.py"), str(EPISODE),
                            "--rpm", "6000", *args], cwd=tmp, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode, p.stdout + p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class TestScript(unittest.TestCase):
    def test_parse(self):
        lines = [i for i in g.parse_script(EPISODE) if i[0] == "line"]
        self.assertEqual(len(lines), 46)
        self.assertEqual({l[1] for l in lines}, set(g.CHARACTERS))

    def test_directions_are_short_english(self):
        # 3.8 TTS 會把文字全部念出來，所以導演提示只能放在 style，而且要短
        for _, sp, d, text in (i for i in g.parse_script(EPISODE) if i[0] == "line"):
            self.assertTrue(d.isascii(), f"導演提示不是英文：{d}")
            self.assertNotIn("{", text)
            self.assertNotIn("[停頓", text)


class TestPipeline(unittest.TestCase):
    def test_batch_mode_four_requests(self):
        code, out = run()
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("一次生成並切開"), 4, out)

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
                "# 註解\nT_ENV_A=abc  # 行尾註解\nT_ENV_B=\"x # y\"\nT_ENV_C=from-file\n",
                encoding="utf-8")
            os.environ["T_ENV_C"] = "from-shell"
            g.load_env(tmp / ".env")
            self.assertEqual(os.environ["T_ENV_A"], "abc")
            self.assertEqual(os.environ["T_ENV_B"], "x # y")
            self.assertEqual(os.environ["T_ENV_C"], "from-shell")   # 已設的不覆蓋
        finally:
            for k in ("T_ENV_A", "T_ENV_B", "T_ENV_C"):
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


if __name__ == "__main__":
    unittest.main()
