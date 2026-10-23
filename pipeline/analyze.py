"""Transcribe separated vocals with word timings and compute verified speech regions."""
import sys, json, subprocess, numpy as np
from faster_whisper import WhisperModel
from faster_whisper.vad import get_speech_timestamps, VadOptions

def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

m = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=4)
for vid in sys.argv[1:]:
    a = load(f"sep/out/htdemucs/{vid}/vocals.wav")
    vad = get_speech_timestamps(a, VadOptions(threshold=0.5, min_silence_duration_ms=150, speech_pad_ms=30))
    regions = [(r["start"] / 16000, r["end"] / 16000) for r in vad]
    # 10 ms RMS envelope of the vocal stem, in dB
    hop = 160
    env = [float(20 * np.log10(np.sqrt(np.mean(a[i:i + hop] ** 2)) + 1e-9)) for i in range(0, len(a) - hop, hop)]
    segs, _ = m.transcribe(a, word_timestamps=True, vad_filter=True, beam_size=5, language="en",
                           condition_on_previous_text=False)
    words = []
    for s in segs:
        print(f"{s.start:6.2f}-{s.end:6.2f} {s.text.strip()}", flush=True)
        words += [{"w": w.word.strip(), "s": w.start, "e": w.end, "p": w.probability} for w in s.words]
    json.dump({"words": words, "vad": regions, "env": env}, open(f"sep/{vid}.json", "w"))
    print("====", vid, "vad:", " ".join(f"{x:.2f}-{y:.2f}" for x, y in regions), flush=True)
