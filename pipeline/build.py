"""Build the Seven Havens edit: cut segments, grade, burn word-by-word glowing captions."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src", "xb6oohi.mp4")
WORDS = os.path.join(ROOT, "src", "xb6oohi.large.json")
if not os.path.exists(WORDS):
    WORDS = os.path.join(ROOT, "src", "xb6oohi.words.json")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "seven_havens_edit.mp4")

W, H = 1920, 1080
PIC_H = 804                      # 2.39:1 picture inside 16:9 frame
BAR = (H - PIC_H) // 2

# (source start, source end, flash on entry)
SEGS = [
    (5.00, 9.30, False),     # My whole life I was taught to hate the Avatar
    (11.20, 14.20, True),    # Everything got turned upside down
    (40.30, 48.30, True),    # Why do you look like me... sisters
    (55.20, 58.90, True),    # I will severely punish whoever is hiding the Avatar
    (59.40, 64.10, False),   # I can't be an Avatar. I'm no warrior
    (64.30, 69.90, True),    # And the last one doomed the world
    (86.50, 90.60, True),    # Find her. No matter the cost.
    (99.80, 103.60, True),   # The world isn't as black and white as you think
    (103.60, 110.80, False), # action montage (music)
    (110.90, 119.30, True),  # Whatever we discover, we'll face it together. Promise.
    (124.00, 130.40, True),  # title card
]

# Word fixes for mis-hearings, keyed by rounded source start time of the word.
FIXES = json.load(open(os.path.join(HERE, "fixes.json"))) if os.path.exists(os.path.join(HERE, "fixes.json")) else {}

ACTIVE = "&H3CC9FF&"   # gold   (ASS is BGR)
ACTIVE_GLOW = "&H0060FF&"  # deep orange
PAST = "&HFFFFFF&"
PAST_GLOW = "&H1E8CFF&"


def ts(t):
    t = max(0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def load_words():
    out = []
    for seg in json.load(open(WORDS)):
        for w in seg["words"]:
            fix = FIXES.get(f"{w['s']:.2f}", w["w"])
            txt, st = (fix, w["s"]) if isinstance(fix, str) else fix
            # whisper often stretches a word's start back into the preceding pause
            st = max(st, w["e"] - 0.45) if isinstance(fix, str) else st
            if txt:
                out.append({"w": txt, "s": st, "e": max(w["e"], st + 0.15)})
    return out


def chunk(words):
    """Group words into short caption phrases."""
    phrases, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > 0.55 or cur[-1]["w"][-1:] in ".?!,"):
            phrases.append(cur); cur = []
        cur.append(w)
    if cur:
        phrases.append(cur)
    chunks = []
    for p in phrases:  # split long phrases into balanced lines of <= 4 words
        n = -(-len(p) // 4)
        size = -(-len(p) // n)
        chunks += [p[i:i + size] for i in range(0, len(p), size)]
    return chunks


def esc(s):
    return s.replace("{", "(").replace("}", ")")


def caption_events(chunks, next_starts):
    ev = []
    y = BAR + PIC_H - 70
    for ci, c in enumerate(chunks):
        end_all = min(c[-1]["e"] + 0.45, next_starts[ci] - 0.02)
        for i, w in enumerate(c):
            st = w["s"]
            en = c[i + 1]["s"] if i + 1 < len(c) else end_all
            if en <= st:
                continue
            for layer, glow in ((0, 'wide'), (1, 'tight'), (2, None)):
                parts = []
                for j, x in enumerate(c):
                    word = esc(x["w"].upper())
                    if j > i:
                        parts.append("{\\alpha&HFF&}" + word)
                        continue
                    if glow:
                        col = ACTIVE_GLOW if j == i else PAST_GLOW
                        tag = f"{{\\alpha&H00&\\1a&HFF&\\3c{col}\\3a&H{'30' if j == i else '90'}&}}"
                    else:
                        col = ACTIVE if j == i else PAST
                        tag = f"{{\\alpha&H00&\\1c{col}}}"
                    if j == i:
                        # pop in: start big and transparent, settle quickly
                        tag = tag[:-1] + "\\fscx125\\fscy125\\t(0,140,\\fscx100\\fscy100)}"
                    parts.append(tag + word)
                text = " ".join(parts)
                if glow == 'wide':
                    base = "{\\an2\\pos(%d,%d)\\bord22\\blur28\\shad0}" % (W // 2, y)
                elif glow == 'tight':
                    base = "{\\an2\\pos(%d,%d)\\bord7\\blur7\\shad0}" % (W // 2, y)
                else:
                    base = "{\\an2\\pos(%d,%d)\\bord3\\3c&H101010&\\blur1.2\\shad0}" % (W // 2, y)
                ev.append((layer, st, en, base + text))
    return ev


def flash_events(cut_times):
    ev = []
    box = "m 0 0 l %d 0 l %d %d l 0 %d" % (W, W, H, H)
    for t in cut_times:
        ev.append((5, t, t + 0.22,
                   "{\\an7\\pos(0,0)\\bord0\\shad0\\1c&HD8F0FF&\\alpha&H50&\\t(0,220,\\alpha&HFF&)\\p1}" + box))
    return ev


def main():
    words = load_words()
    out_words, cuts, t = [], [], 0.0
    for (a, b, flash) in SEGS:
        if flash and t > 0:
            cuts.append(t)
        for w in words:
            if a - 0.3 <= w["s"] < b - 0.1 and w["e"] <= b + 0.15:
                out_words.append({"w": w["w"], "s": t + max(w["s"], a) - a, "e": t + min(w["e"], b) - a})
        t += b - a
    total = t
    chunks = chunk(out_words)
    nexts = [chunks[i + 1][0]["s"] for i in range(len(chunks) - 1)] + [total]
    events = caption_events(chunks, nexts) + flash_events(cuts)

    ass = os.path.join(HERE, "captions.ass")
    with open(ass, "w") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display Black,100,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,2,0,1,3,0,2,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
        for layer, st, en, txt in sorted(events, key=lambda e: (e[1], e[0])):
            f.write(f"Dialogue: {layer},{ts(st)},{ts(en)},Cap,,0,0,0,,{txt}\n")

    # filter graph: trim + short audio fades per segment, concat, grade, letterbox, captions
    fc = []
    for i, (a, b, _) in enumerate(SEGS):
        d = b - a
        fc.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}]")
        fc.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={d-0.06:.3f}:d=0.06[a{i}]")
    fc.append("".join(f"[v{i}][a{i}]" for i in range(len(SEGS))) + f"concat=n={len(SEGS)}:v=1:a=1[vc][ac]")
    crop_h = round(512 / 2.39 / 2) * 2
    fc.append(
        f"[vc]crop=512:{crop_h}:0:(ih-{crop_h})/2,"
        "hqdn3d=1.5:1.5:3:3,"
        f"scale={W}:{PIC_H}:flags=lanczos,"
        "unsharp=7:7:0.9:5:5:0,"
        "eq=contrast=1.08:saturation=1.28:gamma=0.98,"
        "colorbalance=rs=0.04:gs=0.0:bs=-0.05:rh=0.05:bh=-0.03,"
        "curves=master='0/0 0.25/0.21 0.5/0.5 0.78/0.83 1/1',"
        "vignette=PI/5,"
        f"pad={W}:{H}:0:{BAR}:black,"
        "noise=alls=3:allf=t,"
        f"ass='{ass}',format=yuv420p[vo]")
    fc.append("[ac]loudnorm=I=-14:TP=-1.0:LRA=11,aresample=48000[ao]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", SRC, "-filter_complex", ";".join(fc),
           "-map", "[vo]", "-map", "[ao]", "-r", "24000/1001",
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-c:a", "aac", "-b:a", "256k",
           "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    print(f"done: {OUT} ({total:.1f}s)")


if __name__ == "__main__":
    main()
