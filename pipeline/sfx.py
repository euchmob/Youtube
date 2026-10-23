"""Synthesize the edit's sound effects (whoosh, impact, riser, sub drop) as 48 kHz stereo WAVs."""
import os, wave, numpy as np

SR = 48000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx")
rng = np.random.default_rng(7)


def save(name, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def swept_noise(dur, f0, f1, q=1.5, frame=1024):
    """Noise through a band-pass whose centre glides from f0 to f1 (overlap-add STFT filter)."""
    n = int(dur * SR)
    noise = rng.standard_normal(n + frame)
    out = np.zeros(n + frame)
    win = np.hanning(frame)
    freqs = np.fft.rfftfreq(frame, 1 / SR)
    for i in range(0, n, frame // 2):
        fc = f0 * (f1 / f0) ** (i / n)
        bw = fc / q
        gain = np.exp(-0.5 * ((freqs - fc) / bw) ** 2)
        seg = np.fft.irfft(np.fft.rfft(noise[i:i + frame] * win) * gain)
        out[i:i + frame] += seg
    return out[:n]


def env(n, attack, release, curve=2.0):
    t = np.linspace(0, 1, n)
    a = np.clip(t / attack, 0, 1) ** curve
    r = np.clip((1 - t) / release, 0, 1) ** curve
    return a * r


def whoosh(dur=0.45):
    n = int(dur * SR)
    x = swept_noise(dur, 300, 4500) * env(n, 0.6, 0.4, 1.6)
    pan = np.linspace(-0.6, 0.6, n)          # move left to right
    return np.stack([x * (1 - pan) / 2, x * (1 + pan) / 2], 1)


def impact(dur=1.8):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 38 + 50 * np.exp(-t * 9)                       # pitch drop
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6)
    crack = swept_noise(dur, 2500, 400, q=0.8) * np.exp(-t * 14)
    return np.tanh(2.2 * (body + 0.35 * crack))


def riser(dur=3.0):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = swept_noise(dur, 400, 7000, q=1.2)
    f = 180 * (6.5 ** (t / dur))
    tone = sum(np.sin(2 * np.pi * np.cumsum(f * k) / SR) / k for k in (1, 1.5, 2))
    e = (t / dur) ** 2.5
    return (0.7 * noise + 0.25 * tone) * e


def subdrop(dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 30 + 90 * np.exp(-t * 4)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    save("whoosh", whoosh())
    save("whoosh_long", whoosh(0.8))
    save("impact", impact())
    save("riser", riser())
    save("subdrop", subdrop())
    print("sfx written to", OUT)
