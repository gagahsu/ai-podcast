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


def sil(sec):
    return b"\0\0" * int(R * sec)


def run(*args, mode="good"):
    """在暫存資料夾裡用假 SDK 執行主程式，回傳 (exit code, 輸出)。"""
    tmp = tempfile.mkdtemp()
    try:
        env = dict(os.environ, PYTHONPATH=str(FAKE), FAKE_MODE=mode, PYTHONIOENCODING="utf-8")
        p = subprocess.run([sys.executable, str(ROOT / "generate_episode.py"), str(EPISODE),
                            "--rpm", "6000", *args], cwd=tmp, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode, p.stdout + p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class TestScript(unittest.TestCase):
    def test_parse(self):
        lines = [i for i in g.parse_script(EPISODE) if i[0] == "line"]
        self.assertEqual(len(lines), 47)
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
        pcm = tone(2) + sil(1.4) + tone(0.04) + sil(1.4) + tone(2)
        pieces, why = g.split_on_silence(g.Audio(pcm, R), ["一二三四五六", "七八九十一二"])
        self.assertIsNotNone(pieces, why)


if __name__ == "__main__":
    unittest.main()
