import sys, json
from faster_whisper import WhisperModel
m = WhisperModel("medium.en", device="cpu", compute_type="int8", cpu_threads=4)
for path in sys.argv[1:]:
    import subprocess, numpy as np
    a = np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",path,"-ac","1","-ar","16000","-f","s16le","-"],capture_output=True).stdout, np.int16).astype(np.float32)/32768
    segs, _ = m.transcribe(a, word_timestamps=True, vad_filter=True, beam_size=5)
    out = []
    for s in segs:
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                    "words": [{"w": w.word.strip(), "s": w.start, "e": w.end, "p": w.probability} for w in s.words]})
        print(f"{s.start:7.2f}-{s.end:7.2f} {s.text.strip()}", flush=True)
    json.dump(out, open(path.rsplit('.',1)[0] + ".words.json", "w"), indent=1)
    print("====", path, flush=True)
