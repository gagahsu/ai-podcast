"""篩選背景素材：找出「突然冒出來、帶音高」的聲音（鳥叫、蛙叫、人聲、碰撞、頌缽）。

我們沒辦法每個候選都用耳朵聽完，先用這支程式把有問題的排除。Freesound 頁面上的試聽 mp3 不用登入就能下載，可以直接拿來篩。

    py tools/screen_audio.py 檔案1 檔案2 ...

判讀：
- 「突發事件」：0.1 秒內比整體中位數大 6 dB 以上，或某個頻率特別突出（鳥叫、蛙叫是窄頻，水聲是寬頻）。
  最突出頻率是 0 或 20 Hz 的，是聽不到的低頻隆隆聲，可以忽略。
- 「音量起伏」：0.1 秒音量的標準差。環境音最好在 2 dB 以下。
- 實例：ep02 原本的河水素材（BurghRecords #446019）在 15.6、19.7、21、23.3 秒被抓到 4 個鳥叫，跟人耳聽到的一致。
"""
import subprocess
import sys

import numpy as np

R = 16000
N = R // 10  # 0.1 秒一格


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(R), "-f", "s16le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(float)


def screen(path):
    a = load(path)
    fr = a[: len(a) // N * N].reshape(-1, N)
    lv = 10 * np.log10((fr ** 2).mean(1) + 1e-9)
    med = np.median(lv)
    spec = np.abs(np.fft.rfft(fr * np.hanning(N), axis=1))
    base = np.median(spec, axis=0) + 1e-9
    tonal = (spec / base).max(1)
    f = np.fft.rfftfreq(N, 1 / R)
    centroid = (spec * f).sum(1) / (spec.sum(1) + 1e-9)
    events = []
    for i in np.where((lv > med + 6) | (tonal > 25))[0]:
        if not events or i - events[-1][-1] > 3:
            events.append([i])
        else:
            events[-1].append(i)
    secs = len(fr) / 10
    print(f"\n== {path}  {secs:.0f} 秒")
    print(f"  音量起伏（0.1 秒的標準差）{lv.std():.1f} dB，頻譜重心 {np.median(centroid):.0f} Hz")
    print(f"  突發事件 {len(events)} 個（每分鐘 {len(events) / secs * 60:.1f} 個）")
    for ev in events[:12]:
        i = max(ev, key=lambda k: lv[k])
        print(f"    {ev[0] / 10:6.1f} 秒  +{lv[i] - med:4.1f} dB  音高強度 {tonal[ev].max():5.0f}  "
              f"最突出 {f[np.argmax(spec[i] / base)]:.0f} Hz")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        screen(p)
