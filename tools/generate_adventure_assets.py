"""
產生「沖繩大冒險」所需的音效素材與背景音樂。
所有素材皆由合成音訊演算法（DSP / Karplus-Strong / FM / Noise synthesis）與 ffmpeg 產生，
確保 100% 原創、免版權、乾淨無雜音。
"""

import math
import random
import subprocess
import wave
from pathlib import Path
import numpy as np

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
RATE = 44100


def save_wav(path: Path, data: np.ndarray, rate: int = RATE):
    """將 float32 (-1.0 ~ 1.0) 轉成 16-bit PCM WAV。"""
    data = np.clip(data, -0.98, 0.98)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def make_single_clap(decay=0.08, tone_freq=950, rate=RATE):
    """單個拍手聲（帶共振的雜訊衝擊）。"""
    n = int(rate * 0.15)
    t = np.linspace(0, 0.15, n, endpoint=False)
    # 衝擊噪音
    noise = np.random.uniform(-1, 1, n)
    env = np.exp(-t / decay)
    # 掌心共鳴
    res = np.sin(2 * np.pi * tone_freq * t) * 0.4
    return (noise * 0.8 + res) * env


def gen_clap():
    """單次清脆拍手。"""
    clap = make_single_clap(decay=0.045, tone_freq=1100)
    save_wav(ASSETS_DIR / "sfx_clap.wav", clap)
    print("Generated sfx_clap.wav")


def gen_highfive():
    """擊掌（更扎實明亮的啪一聲）。"""
    n = int(RATE * 0.25)
    t = np.linspace(0, 0.25, n, endpoint=False)
    noise = np.random.uniform(-1, 1, n)
    # 雙層衰減：極快的高頻瞬態 + 扎實中頻
    env_fast = np.exp(-t / 0.015)
    env_body = np.exp(-t / 0.06)
    tone = np.sin(2 * np.pi * 1400 * t) * 0.5
    data = (noise * 0.9 * env_fast + (noise * 0.5 + tone) * env_body) * 1.2
    save_wav(ASSETS_DIR / "sfx_highfive.wav", data)
    print("Generated sfx_highfive.wav")


def gen_applause(duration=4.5):
    """眾人群體拍手掌聲。"""
    n = int(RATE * duration)
    total = np.zeros(n)
    num_people = 35
    for _ in range(num_people):
        # 每個人拍手頻率略有不同
        interval = random.uniform(0.18, 0.28)
        cur = random.uniform(0, 0.3)
        while cur < duration - 0.15:
            clap = make_single_clap(decay=random.uniform(0.03, 0.06), tone_freq=random.uniform(800, 1400))
            idx = int(cur * RATE)
            end_idx = min(n, idx + len(clap))
            total[idx:end_idx] += clap[: end_idx - idx] * random.uniform(0.3, 0.7)
            cur += interval * random.uniform(0.9, 1.1)

    # 前後淡入淡出
    fade_in = int(RATE * 0.6)
    fade_out = int(RATE * 1.2)
    total[:fade_in] *= np.linspace(0, 1, fade_in)
    total[-fade_out:] *= np.linspace(1, 0, fade_out)
    # 標準化
    total = total / (np.max(np.abs(total)) + 1e-6) * 0.85
    save_wav(ASSETS_DIR / "sfx_applause.wav", total)
    print("Generated sfx_applause.wav")


def gen_cheer(duration=3.8):
    """掌聲加歡呼聲。"""
    # 先做基底掌聲
    n = int(RATE * duration)
    total = np.zeros(n)
    for _ in range(30):
        interval = random.uniform(0.18, 0.26)
        cur = random.uniform(0, 0.2)
        while cur < duration - 0.15:
            clap = make_single_clap(decay=0.04, tone_freq=random.uniform(900, 1300))
            idx = int(cur * RATE)
            end_idx = min(n, idx + len(clap))
            total[idx:end_idx] += clap[: end_idx - idx] * random.uniform(0.3, 0.6)
            cur += interval * random.uniform(0.9, 1.1)

    t = np.linspace(0, duration, n, endpoint=False)
    # 加上群眾歡呼的共鳴聲 (Whooa / Yay)
    cheer_env = np.sin(np.pi * np.clip(t / 3.0, 0, 1)) ** 2
    formant1 = np.sin(2 * np.pi * 550 * t) * 0.2
    formant2 = np.sin(2 * np.pi * 880 * t) * 0.25
    cheer_noise = np.random.uniform(-0.15, 0.15, n)
    cheer = (formant1 + formant2 + cheer_noise) * cheer_env * 0.5
    total = total + cheer
    total[: int(RATE * 0.4)] *= np.linspace(0, 1, int(RATE * 0.4))
    total[-int(RATE * 1.0) :] *= np.linspace(1, 0, int(RATE * 1.0))
    total = total / (np.max(np.abs(total)) + 1e-6) * 0.88
    save_wav(ASSETS_DIR / "sfx_cheer.wav", total)
    print("Generated sfx_cheer.wav")


def gen_bubbles(filename="sfx_bubbles.wav", count=12, duration=2.2):
    """水流與冒泡泡水聲。"""
    n = int(RATE * duration)
    data = np.zeros(n)
    for _ in range(count):
        start_t = random.uniform(0.1, duration - 0.4)
        bubble_len = random.uniform(0.04, 0.08)
        bn = int(RATE * bubble_len)
        bt = np.linspace(0, bubble_len, bn, endpoint=False)
        # 氣泡頻率向上滑動
        f0 = random.uniform(400, 700)
        f1 = f0 * random.uniform(1.8, 2.5)
        freq = np.linspace(f0, f1, bn)
        phase = 2 * np.pi * np.cumsum(freq) / RATE
        env = np.sin(np.pi * bt / bubble_len) ** 1.5
        bubble = np.sin(phase) * env * random.uniform(0.5, 0.9)
        idx = int(start_t * RATE)
        end_idx = min(n, idx + bn)
        data[idx:end_idx] += bubble[: end_idx - idx]

    # 加一點柔和流水背景
    water = np.random.uniform(-0.06, 0.06, n)
    data += water
    data = data / (np.max(np.abs(data)) + 1e-6) * 0.75
    save_wav(ASSETS_DIR / filename, data)
    print(f"Generated {filename}")


def gen_splash():
    """落水與水花飛濺。"""
    duration = 1.0
    n = int(RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # 衝擊聲 (低頻 thud)
    thud_env = np.exp(-t / 0.08)
    thud = np.sin(2 * np.pi * 120 * t) * thud_env * 0.7
    # 飛濺水花 (噪音快速衰減帶抖動)
    splash_env = np.exp(-t / 0.28) * (1 + 0.3 * np.sin(2 * np.pi * 18 * t))
    splash_noise = np.random.uniform(-1, 1, n) * splash_env * 0.5
    data = (thud + splash_noise) * 0.9
    save_wav(ASSETS_DIR / "sfx_splash.wav", data)
    print("Generated sfx_splash.wav")


def gen_stomach():
    """肚子咕嚕叫聲。"""
    duration = 1.6
    n = int(RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # 頻率調變 (FM)
    carrier_freq = 95.0
    mod_freq = 9.0
    mod_depth = 35.0
    fm = np.sin(2 * np.pi * carrier_freq * t + mod_depth * np.sin(2 * np.pi * mod_freq * t))
    # 肚皮起伏包絡
    envelope = np.sin(np.pi * t / duration) ** 2 * (1 + 0.4 * np.sin(2 * np.pi * 4 * t))
    data = fm * envelope * 0.8
    save_wav(ASSETS_DIR / "sfx_stomach.wav", data)
    print("Generated sfx_stomach.wav")


def gen_sizzle(duration=3.2):
    """烤肉滋滋響聲。"""
    n = int(RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # 高頻白噪音基底
    noise = np.random.uniform(-0.25, 0.25, n)
    # 油滴爆裂聲 (隨機突波 pops)
    num_pops = int(duration * 65)
    pops = np.zeros(n)
    for _ in range(num_pops):
        pos = random.randint(0, n - 400)
        pop_len = random.randint(150, 350)
        pt = np.linspace(0, 1, pop_len)
        pop_wave = np.sin(2 * np.pi * random.uniform(2000, 4500) * pt / RATE) * np.exp(-pt * 8)
        pops[pos : pos + pop_len] += pop_wave * random.uniform(0.4, 0.9)

    data = noise + pops
    fade = int(RATE * 0.3)
    data[:fade] *= np.linspace(0, 1, fade)
    data[-fade:] *= np.linspace(1, 0, fade)
    data = data / (np.max(np.abs(data)) + 1e-6) * 0.8
    save_wav(ASSETS_DIR / "sfx_sizzle.wav", data)
    print("Generated sfx_sizzle.wav")


def gen_bgm(duration=85.0):
    """
    合成輕快活潑的沖繩夏日童趣冒險 BGM（烏克麗麗/木琴/輕快律動）。
    120 BPM, 4/4 拍, C 大調。
    """
    bpm = 120
    beat_sec = 60.0 / bpm
    bar_sec = beat_sec * 4.0
    total_samples = int(RATE * duration)
    audio = np.zeros(total_samples)

    # 音符頻率 (Hz)
    notes = {
        "C3": 130.81, "G3": 196.00, "A3": 220.00, "F3": 174.61,
        "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23,
        "G4": 392.00, "A4": 440.00, "B4": 493.88,
        "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99,
    }

    # 和弦序列 (每個和弦 1 小節 2 秒)：C -> G -> Am -> F
    progression = [
        ("C3", ["C4", "E4", "G4", "C5"]),
        ("G3", ["B4", "D4", "G4", "D5"]),
        ("A3", ["C4", "E4", "A4", "E5"]),
        ("F3", ["C4", "F4", "A4", "C5"]),
    ]

    # 木琴旋律音符（童趣跳躍）
    melody_patterns = [
        # 第 1 句 (C 和弦)
        [(0.0, "C5", 0.25), (0.5, "E5", 0.25), (1.0, "G5", 0.35), (1.5, "E5", 0.25)],
        # 第 2 句 (G 和弦)
        [(0.0, "D5", 0.25), (0.5, "G4", 0.25), (1.0, "B4", 0.25), (1.5, "D5", 0.35)],
        # 第 3 句 (Am 和弦)
        [(0.0, "C5", 0.25), (0.5, "E5", 0.25), (1.0, "A4", 0.35), (1.5, "C5", 0.25)],
        # 第 4 句 (F 和弦)
        [(0.0, "A4", 0.25), (0.5, "F4", 0.25), (1.0, "G4", 0.25), (1.5, "C5", 0.5)],
    ]

    def render_pluck(freq, dur, decay=4.0):
        """合成彈撥/敲擊樂器音色。"""
        n = int(RATE * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        # 基頻 + 2次諧波 + 3次諧波
        wave = (
            np.sin(2 * np.pi * freq * t) * 0.7
            + np.sin(2 * np.pi * freq * 2 * t) * 0.25
            + np.sin(2 * np.pi * freq * 3 * t) * 0.1
        )
        env = np.exp(-t * decay)
        return wave * env

    cur_time = 0.0
    bar_idx = 0
    while cur_time < duration - 2.0:
        prog_step = bar_idx % 4
        bass_note, chord_notes = progression[prog_step]

        # 1. 低音貝斯 (每個小節 1拍與 3拍)
        for beat in [0.0, 1.0]:
            t_offset = cur_time + beat * (beat_sec * 2)
            if t_offset + 0.8 < duration:
                idx = int(t_offset * RATE)
                sample = render_pluck(notes[bass_note], 0.6, decay=3.0) * 0.35
                end_idx = min(total_samples, idx + len(sample))
                audio[idx:end_idx] += sample[: end_idx - idx]

        # 2. 烏克麗麗刷弦 (八分音符切分跳躍)
        for subbeat in [0.5, 1.0, 1.5, 2.5, 3.0, 3.5]:
            t_offset = cur_time + subbeat * beat_sec
            if t_offset + 0.4 < duration:
                idx = int(t_offset * RATE)
                for cn in chord_notes:
                    sample = render_pluck(notes[cn], 0.35, decay=6.0) * 0.08
                    end_idx = min(total_samples, idx + len(sample))
                    audio[idx:end_idx] += sample[: end_idx - idx]

        # 3. 木琴跳躍旋律
        pattern = melody_patterns[prog_step]
        for note_offset, note_name, note_dur in pattern:
            t_offset = cur_time + note_offset * (beat_sec * 2)
            if t_offset + note_dur < duration:
                idx = int(t_offset * RATE)
                sample = render_pluck(notes[note_name], note_dur, decay=5.0) * 0.28
                end_idx = min(total_samples, idx + len(sample))
                audio[idx:end_idx] += sample[: end_idx - idx]

        cur_time += bar_sec
        bar_idx += 1

    # 淡入與淡出
    fade_in = int(RATE * 1.5)
    fade_out = int(RATE * 3.5)
    audio[:fade_in] *= np.linspace(0, 1, fade_in)
    audio[-fade_out:] *= np.linspace(1, 0, fade_out)

    # 正規化音量
    audio = audio / (np.max(np.abs(audio)) + 1e-6) * 0.85
    wav_path = ASSETS_DIR / "okinawa_adventure_bgm.wav"
    mp3_path = ASSETS_DIR / "okinawa_adventure_bgm.mp3"
    save_wav(wav_path, audio)

    # 轉為 MP3
    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-codec:a", "libmp3lame", "-b:a", "192k",
        str(mp3_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if wav_path.exists():
        wav_path.unlink()
    print(f"Generated {mp3_path.name} (length: {duration}s)")


def gen_airplane(duration=3.2):
    """飛機呼嘯飛過（都卜勒調變白噪音）。"""
    n = int(RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # 音量包絡：靠近時變大，掠過後拉長衰減
    env = np.exp(-((t - 1.2) ** 2) / 0.35)
    noise = np.random.uniform(-1, 1, n)
    # 都卜勒音調滑移 (接近 850Hz -> 遠離 320Hz)
    freq = 850.0 - 530.0 / (1.0 + np.exp(-(t - 1.2) * 5.0))
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    tone = (np.sin(phase) + 0.3 * np.sin(phase * 2.0)) * 0.4
    data = (noise * 0.6 + tone) * env * 0.85
    save_wav(ASSETS_DIR / "sfx_airplane.wav", data)
    print("Generated sfx_airplane.wav")


def gen_waves(duration=5.0):
    """海島沙灘海浪拍打聲（緩緩湧上沙灘又退去）。"""
    n = int(RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # 兩波海浪
    wave_env1 = np.sin(np.pi * np.clip(t / 3.0, 0, 1)) ** 2
    wave_env2 = np.sin(np.pi * np.clip((t - 1.8) / 3.2, 0, 1)) ** 2
    env = wave_env1 * 0.8 + wave_env2 * 0.6
    noise = np.random.uniform(-0.8, 0.8, n)
    # 柔和低頻海洋浪潮
    low_rumble = np.sin(2 * np.pi * 55 * t) * 0.25 * env
    data = (noise * 0.6 + low_rumble) * env
    fade = int(RATE * 0.5)
    data[:fade] *= np.linspace(0, 1, fade)
    data[-fade:] *= np.linspace(1, 0, fade)
    data = data / (np.max(np.abs(data)) + 1e-6) * 0.75
    save_wav(ASSETS_DIR / "sfx_waves.wav", data)
    print("Generated sfx_waves.wav")


def gen_fireworks(duration=4.2):
    """澎湖國際花火節煙火（哨音上升 + 巨大爆炸 + 燦爛劈啪聲）。"""
    n = int(RATE * duration)
    total = np.zeros(n)
    t = np.linspace(0, duration, n, endpoint=False)

    # 1. 升空哨音 (0 ~ 1.0s)
    whistle_len = int(RATE * 1.0)
    wt = t[:whistle_len]
    w_freq = np.linspace(700, 2200, whistle_len)
    w_phase = 2 * np.pi * np.cumsum(w_freq) / RATE
    w_env = (wt / 1.0) ** 1.8
    total[:whistle_len] += np.sin(w_phase) * w_env * 0.35

    # 2. 巨大主爆炸 (1.0s 瞬間)
    boom_start = int(RATE * 0.98)
    boom_len = int(RATE * 1.8)
    bt = np.linspace(0, 1.8, boom_len, endpoint=False)
    boom_env = np.exp(-bt / 0.25)
    boom_thud = np.sin(2 * np.pi * 58 * bt) * boom_env * 0.8
    boom_noise = np.random.uniform(-1, 1, boom_len) * np.exp(-bt / 0.12) * 0.9
    total[boom_start : boom_start + boom_len] += (boom_thud + boom_noise) * 0.85

    # 3. 散開劈啪火星 (1.2s ~ 3.8s)
    for _ in range(40):
        pos = int(RATE * random.uniform(1.2, 3.4))
        crackle_len = random.randint(120, 260)
        c_wave = np.random.uniform(-1, 1, crackle_len) * np.exp(-np.linspace(0, 4, crackle_len))
        if pos + crackle_len < n:
            total[pos : pos + crackle_len] += c_wave * random.uniform(0.3, 0.7)

    fade_out = int(RATE * 0.8)
    total[-fade_out:] *= np.linspace(1, 0, fade_out)
    total = total / (np.max(np.abs(total)) + 1e-6) * 0.9
    save_wav(ASSETS_DIR / "sfx_fireworks.wav", total)
    print("Generated sfx_fireworks.wav")


def gen_fireworks_muffled(duration=3.6):
    """戴上耳塞後的沉悶低音煙火聲（波、波、波）。"""
    n = int(RATE * duration)
    total = np.zeros(n)
    # 三次沉悶低沉微弱衝擊「波、波、波」
    for delay in [0.2, 1.1, 2.0]:
        start = int(RATE * delay)
        pop_len = int(RATE * 0.4)
        pt = np.linspace(0, 0.4, pop_len, endpoint=False)
        pop = np.sin(2 * np.pi * 75 * pt) * np.exp(-pt / 0.08) * 0.5
        total[start : start + pop_len] += pop

    fade_out = int(RATE * 0.5)
    total[-fade_out:] *= np.linspace(1, 0, fade_out)
    total = total / (np.max(np.abs(total)) + 1e-6) * 0.65
    save_wav(ASSETS_DIR / "sfx_fireworks_muffled.wav", total)
    print("Generated sfx_fireworks_muffled.wav")


def gen_penghu_bgm(duration=90.0):
    """澎湖冒險 BGM：甜美、充滿想像力與海島微風的童趣輕快音樂（G 大調）。"""
    bpm = 116
    beat_sec = 60.0 / bpm
    bar_sec = beat_sec * 4.0
    total_samples = int(RATE * duration)
    audio = np.zeros(total_samples)

    notes = {
        "G3": 196.00, "D3": 146.83, "E3": 164.81, "C3": 130.81,
        "G4": 392.00, "B4": 493.88, "D4": 293.66, "E4": 329.63,
        "C4": 261.63, "F#4": 369.99, "A4": 440.00,
        "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99, "B5": 987.77,
    }

    # 和弦進行：G -> D -> Em -> C
    progression = [
        ("G3", ["G4", "B4", "D5", "G5"]),
        ("D3", ["F#4", "A4", "D5", "F#4"]),
        ("E3", ["G4", "B4", "E5", "G4"]),
        ("C3", ["G4", "C4", "E4", "C5"]),
    ]

    # 甜美鐘琴/木琴輕快跳躍旋律
    melody_patterns = [
        [(0.0, "G5", 0.3), (0.5, "B5", 0.25), (1.0, "D5", 0.35), (1.5, "B5", 0.25)],
        [(0.0, "A4", 0.3), (0.5, "D5", 0.25), (1.0, "F#4", 0.35), (1.5, "A4", 0.25)],
        [(0.0, "G5", 0.3), (0.5, "E5", 0.25), (1.0, "G5", 0.35), (1.5, "E5", 0.25)],
        [(0.0, "E5", 0.3), (0.5, "D5", 0.25), (1.0, "C5", 0.35), (1.5, "G5", 0.45)],
    ]

    def render_bell(freq, dur, decay=3.5):
        n = int(RATE * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        # 晶亮透明的鐘琴/鋼片琴音色 (帶高頻共振)
        wave = (
            np.sin(2 * np.pi * freq * t) * 0.65
            + np.sin(2 * np.pi * freq * 2.756 * t) * 0.25
            + np.sin(2 * np.pi * freq * 5.404 * t) * 0.1
        )
        return wave * np.exp(-t * decay)

    def render_pluck(freq, dur, decay=4.5):
        n = int(RATE * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        wave = np.sin(2 * np.pi * freq * t) * 0.7 + np.sin(2 * np.pi * freq * 2 * t) * 0.3
        return wave * np.exp(-t * decay)

    cur_time = 0.0
    bar_idx = 0
    while cur_time < duration - 2.0:
        prog_step = bar_idx % 4
        bass_note, chord_notes = progression[prog_step]

        # 貝斯
        for beat in [0.0, 1.0]:
            t_offset = cur_time + beat * (beat_sec * 2)
            if t_offset + 0.8 < duration:
                idx = int(t_offset * RATE)
                sample = render_pluck(notes[bass_note], 0.6, decay=2.8) * 0.32
                end_idx = min(total_samples, idx + len(sample))
                audio[idx:end_idx] += sample[: end_idx - idx]

        # 烏克麗麗輕巧刷弦
        for subbeat in [0.5, 1.0, 1.5, 2.5, 3.0, 3.5]:
            t_offset = cur_time + subbeat * beat_sec
            if t_offset + 0.35 < duration:
                idx = int(t_offset * RATE)
                for cn in chord_notes:
                    sample = render_pluck(notes[cn], 0.32, decay=6.5) * 0.075
                    end_idx = min(total_samples, idx + len(sample))
                    audio[idx:end_idx] += sample[: end_idx - idx]

        # 鐘琴主旋律（晶亮夢幻）
        pattern = melody_patterns[prog_step]
        for note_offset, note_name, note_dur in pattern:
            t_offset = cur_time + note_offset * (beat_sec * 2)
            if t_offset + note_dur < duration:
                idx = int(t_offset * RATE)
                sample = render_bell(notes[note_name], note_dur, decay=4.2) * 0.26
                end_idx = min(total_samples, idx + len(sample))
                audio[idx:end_idx] += sample[: end_idx - idx]

        cur_time += bar_sec
        bar_idx += 1

    fade_in = int(RATE * 1.5)
    fade_out = int(RATE * 3.5)
    audio[:fade_in] *= np.linspace(0, 1, fade_in)
    audio[-fade_out:] *= np.linspace(1, 0, fade_out)
    audio = audio / (np.max(np.abs(audio)) + 1e-6) * 0.85

    wav_path = ASSETS_DIR / "penghu_adventure_bgm.wav"
    mp3_path = ASSETS_DIR / "penghu_adventure_bgm.mp3"
    save_wav(wav_path, audio)

    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-codec:a", "libmp3lame", "-b:a", "192k",
        str(mp3_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if wav_path.exists():
        wav_path.unlink()
    print(f"Generated {mp3_path.name} (length: {duration}s)")


def main():
    print("Generating assets for Okinawa and Penghu Adventures...")
    gen_clap()
    gen_highfive()
    gen_applause()
    gen_cheer()
    gen_bubbles("sfx_bubbles.wav", count=14, duration=2.5)
    gen_bubbles("sfx_water_bubbles.wav", count=18, duration=2.8)
    gen_splash()
    gen_stomach()
    gen_sizzle()
    gen_bgm()
    # 澎湖素材
    gen_airplane()
    gen_waves()
    gen_fireworks()
    gen_fireworks_muffled()
    gen_penghu_bgm()
    print("All assets generated successfully!")


if __name__ == "__main__":
    main()
