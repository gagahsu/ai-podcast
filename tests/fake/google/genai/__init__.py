"""假的 google.genai，給測試用：不連網、不花額度。

FAKE_MODE 環境變數：
  good  每句之間停頓 0.8~1.5 秒（比句中停頓長，靜音就切得開）
  wav   同 good，但回傳帶 WAV 檔頭的音訊
  long  音訊長度是正常的 4 倍（模擬模型把設定也念出來）
"""
import base64
import io
import math
import os
import random
import re
import wave
from array import array

from . import errors, types  # noqa: F401

__version__ = "2.1.0"
calls = {"n": 0}
RATE = 24000
_TAG = re.compile(r"<[^>]+>")


class _NS:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _tone(sec):
    return array("h", [int(8000 * math.sin(i / 5)) for i in range(int(RATE * sec))]).tobytes()


def _sil(sec):
    return b"\0\0" * int(RATE * sec)


class _Interactions:
    def create(self, model, input, response_format, generation_config):
        calls["n"] += 1
        mode = os.environ.get("FAKE_MODE", "good")
        parts = input[0]["content"]
        assert all(p["annotations"][0]["type"] == "speech_metadata" for p in parts)
        out = _sil(0.3)
        for k, p in enumerate(parts):
            dur = max(len(_TAG.sub("", p["text"]).strip()), 1) / 3.0
            if mode == "long":
                dur *= 4
            out += _tone(dur * 0.6) + _sil(0.2) + _tone(dur * 0.4)
            if k < len(parts) - 1:
                out += _sil(random.uniform(0.8, 1.5))
        out += _sil(0.4)
        if mode == "wav":
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes(out)
            out = buf.getvalue()
        return _NS(output_audio=_NS(data=base64.b64encode(out).decode()))


class Client:
    def __init__(self, *a, **kw):
        self.interactions = _Interactions()
