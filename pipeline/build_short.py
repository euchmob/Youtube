"""Build the vertical Seven Havens short.

Video: official Avatar Legends clips (episodes 4-6), burned-in text removed, per-segment motion
(slow push-in, punch-in, shake, flash), colour grade with bloom.
Audio: Demucs vocal stems + music bed ducked under dialogue + synthesized SFX.
Captions: word-by-word glowing ASS captions, shown ONLY while a word is actually being spoken
(each word must be confirmed by voice-activity detection on the isolated vocal stem).
"""
import json, os, subprocess, sys
import cv2, numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from detext import clean  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TMP = os.path.join(ROOT, "short_tmp")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "seven_havens_short.mp4")
W, H, FPS = 1080, 1920, 24000 / 1001

CLIPS = {
    "R": ("7698858853059857677", [(0.09, 0.26), (0.64, 0.80)]),   # raven message
    "N": ("7697048875479174414", [(0.22, 0.37), (0.64, 0.80)]),   # Nisha's secret
    "W": ("7698826910213754126", [(0.09, 0.20), (0.64, 0.80)]),   # White Lotus
    "B": ("7699491922594761997", [(0.66, 0.86)]),                 # the Brigade
}

# (clip, source start, source end, entry effect)
SEGS = [
    ("R", 1.95, 5.56, "flash"),
    ("N", 0.00, 5.05, "punch"),
    ("W", 0.55, 3.50, "punch"),
    ("W", 15.35, 17.20, "punch"),
    ("B", 4.30, 5.85, "shake"),
    ("B", 11.75, 15.95, "flash"),
    ("B", 18.10, 34.50, "punch"),
    ("B", 37.70, 39.90, "logo"),
]

FIX = {"Allura.": "Ellora.", "Elora": "Ellora", "Jay.": "Jae.", "order": "Order", "white": "White"}
EMPHASIS = {"AVATAR.", "SECRET,", "LOTUS?", "BRIGADE", "HERO.", "TERRIFIED,", "COMMANDER.", "DOORS!"}

MUSIC = os.path.join(ROOT, "music", "Five_Armies.mp3")
MUSIC_START = 62.0

GOLD, GOLD_GLOW = "&H3CC9FF&", "&H0060FF&"
WHITE, WHITE_GLOW = "&HFFFFFF&", "&H1E8CFF&"
FIRE, FIRE_GLOW = "&H2E7BFF&", "&H0018E0&"


# ---------------------------------------------------------------- speech-verified words
def max_dur(word):
    return 0.14 + 0.075 * sum(c.isalpha() for c in word)


def active_mask(env):
    """10 ms frames where the isolated vocal stem carries real voice energy (short gaps bridged)."""
    env = np.array(env)
    thr = max(np.percentile(env, 95) - 28, -50)
    act = env > thr
    gap = 0
    for i in range(len(act)):                     # bridge gaps < 100 ms inside a word/phrase
        if act[i]:
            if 0 < gap < 10:
                act[i - gap:i] = True
            gap = 0
        else:
            gap += 1
    return act


def verified_words(vid, a, b):
    """Words inside [a, b], each snapped onto the frames where the voice is actually sounding.

    A word with no voice energy anywhere near its whisper timing is dropped, so a caption can
    never appear over silence or music.
    """
    d = json.load(open(os.path.join(ROOT, "sep", f"{vid}.json")))
    act = active_mask(d["env"])
    # contiguous voiced bursts, in seconds
    bursts, i = [], 0
    while i < len(act):
        if act[i]:
            j = i
            while j + 1 < len(act) and act[j + 1]:
                j += 1
            if j - i >= 4:                          # ignore blips shorter than 50 ms
                bursts.append((i / 100, (j + 1) / 100))
            i = j + 1
        else:
            i += 1
    out, prev_s = [], -1.0
    for w in d["words"]:
        s, e = w["s"], w["e"]
        s = max(s, e - max_dur(w["w"]))            # whisper stretches starts back into pauses
        # the burst overlapping the word itself; else the next burst starting just after it
        best, ov = None, 0.0
        for b0, b1 in bursts:
            o = min(e, b1) - max(s, b0)
            if o > ov:
                best, ov = (b0, b1), o
        if best is None:
            later = [bb for bb in bursts if s <= bb[0] <= e + 0.25]
            best = later[0] if later else None
        if best is None:
            continue                                # no voice near this word -> never shown
        s2 = max(s, best[0], prev_s + 0.06)
        e2 = min(max(e, s2 + 0.08), best[1])
        if e2 - s2 < 0.04:
            continue
        prev_s = s2
        if s2 < a - 0.02 or s2 > b - 0.05:
            continue
        txt = FIX.get(w["w"], w["w"])
        out.append({"w": txt, "s": max(s2, a), "e": min(e2, b)})
    return out


def lines_from(words):
    lines, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > 0.30 or cur[-1]["w"][-1:] in ".?!"):
            lines.append(cur); cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    res = []
    for ln in lines:                                # balanced lines of <= 3 words
        n = -(-len(ln) // 3)
        sizes = [len(ln) // n + (1 if r < len(ln) % n else 0) for r in range(n)]
        i = 0
        for k in sizes:
            res.append(ln[i:i + k]); i += k
    return res


# ---------------------------------------------------------------- captions (ASS)
def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def esc(s):
    return s.replace("{", "(").replace("}", ")")


def caption_events(lines, seg_bounds):
    ev = []
    y = 1400
    for li, ln in enumerate(lines):
        # visible strictly from first word onset to last word offset (+60 ms), never into next line/segment
        hard_end = ln[-1]["e"] + 0.06
        if li + 1 < len(lines):
            hard_end = min(hard_end, lines[li + 1][0]["s"] - 0.01)
        for s0, s1 in seg_bounds:
            if s0 <= ln[0]["s"] < s1:
                hard_end = min(hard_end, s1 - 0.01)
        for i, w in enumerate(ln):
            st = w["s"]
            en = ln[i + 1]["s"] if i + 1 < len(ln) else hard_end
            if en - st < 0.02:
                continue
            for layer, mode in ((0, "wide"), (1, "tight"), (2, "core")):
                parts = []
                for j, x in enumerate(ln):
                    word = esc(x["w"].upper())
                    if j > i:
                        parts.append("{\\alpha&HFF&}" + word)
                        continue
                    emph = word in EMPHASIS
                    if j == i:
                        fill, glow = (FIRE, FIRE_GLOW) if emph else (GOLD, GOLD_GLOW)
                    else:
                        fill, glow = (FIRE, FIRE_GLOW) if emph else (WHITE, WHITE_GLOW)
                    if mode == "core":
                        tag = f"\\alpha&H00&\\1c{fill}"
                    else:
                        tag = f"\\alpha&H00&\\1a&HFF&\\3c{glow}\\3a&H{'20' if j == i else '80'}&"
                    if j == i:
                        tag += "\\fscx135\\fscy135\\t(0,120,\\fscx100\\fscy100)"
                    parts.append("{" + tag + "}" + word)
                if mode == "wide":
                    base = "{\\an5\\pos(%d,%d)\\bord26\\blur30\\shad0}" % (W // 2, y)
                elif mode == "tight":
                    base = "{\\an5\\pos(%d,%d)\\bord8\\blur8\\shad0}" % (W // 2, y)
                else:
                    base = "{\\an5\\pos(%d,%d)\\bord3\\3c&H101010&\\blur1\\shad0}" % (W // 2, y)
                ev.append((layer, st, en, base + " ".join(parts)))
    return ev


def write_ass(path, events):
    with open(path, "w") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display Black,92,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,1,0,1,3,0,5,30,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
        for layer, st, en, txt in sorted(events, key=lambda e: (e[1], e[0])):
            f.write(f"Dialogue: {layer},{ts(st)},{ts(en)},Cap,,0,0,0,,{txt}\n")


# ---------------------------------------------------------------- per-segment video
def render_segment(i, clip, a, b, fx):
    vid, bands = CLIPS[clip]
    out = os.path.join(TMP, f"seg{i}.mp4")
    dur = b - a
    if os.environ.get("REUSE") and os.path.exists(out):
        return out, dur
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-i", os.path.join(ROOT, "tk", vid + ".mp4"),
                            "-t", f"{dur:.3f}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", "24000/1001", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
                            "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    n = 0
    frame_bytes = W * H * 3
    while True:
        buf = dec.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
        t = n / FPS
        if fx != "logo":
            img, _ = clean(img, bands)
        # motion: slow push-in + entry punch / shake
        z = 1.04 + 0.05 * t / max(dur, 0.1)
        dx = dy = 0.0
        if fx in ("punch", "flash", "shake"):
            z += 0.16 * max(0.0, 1 - t / 0.25) ** 2
        if fx == "shake":
            k = max(0.0, 1 - t / 0.9)
            dx, dy = 22 * k * np.sin(t * 71), 16 * k * np.cos(t * 53)
        if fx == "logo":
            z = 1.0 + 0.10 * max(0.0, 1 - t / 0.35) ** 2 + 0.03 * t / dur
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
        M[0, 2] += dx; M[1, 2] += dy
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        # light flash on entry
        if fx in ("flash", "shake", "logo"):
            fa = 0.75 * max(0.0, 1 - t / 0.2)
            if fa > 0:
                img = cv2.addWeighted(img, 1 - fa, np.full_like(img, 255), fa, 0)
        enc.stdin.write(img.tobytes())
        n += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    return out, n / FPS


def main():
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    seg_files, words, bounds, cuts, t = [], [], [], [], 0.0
    for i, (clip, a, b, fx) in enumerate(SEGS):
        f, d = render_segment(i, clip, a, b, fx)
        seg_files.append(f)
        vid = CLIPS[clip][0]
        for w in verified_words(vid, a, b):
            words.append({"w": w["w"], "s": t + w["s"] - a, "e": t + w["e"] - a})
        bounds.append((t, t + (b - a)))
        cuts.append((t, fx))
        t += b - a
        print(f"segment {i} done ({d:.2f}s)", flush=True)
    total = t

    lines = lines_from(words)
    # voiced timeline of the finished cut (10 ms); captions are clipped to it so that
    # nothing is ever on screen while nobody is speaking
    voiced = []
    for clip, a, b, fx in SEGS:
        act = active_mask(json.load(open(os.path.join(ROOT, "sep", f"{CLIPS[clip][0]}.json")))["env"])
        voiced += list(act[int(round(a * 100)):int(round(b * 100))])
    voiced = np.convolve(np.array(voiced, int), np.ones(9, int), "same") > 0   # +-40 ms tolerance
    events = []
    for layer, st, en, txt in caption_events(lines, bounds):
        i0, i1 = int(round(st * 100)), int(round(en * 100))
        k = i0
        while k < i1:
            if k < len(voiced) and voiced[k]:
                j = k
                while j < i1 and j < len(voiced) and voiced[j]:
                    j += 1
                if j - k >= 3:
                    # keep the pop-in animation only on the first piece of a word
                    events.append((layer, k / 100, j / 100, txt if k == i0 else txt.replace("\\fscx135\\fscy135\\t(0,120,\\fscx100\\fscy100)", "")))
                k = j
            else:
                k += 1
    ass = os.path.join(TMP, "captions.ass")
    write_ass(ass, events)
    json.dump(lines, open(os.path.join(TMP, "lines.json"), "w"), indent=1)

    # ---- audio graph
    inputs = []
    for f in seg_files:
        inputs += ["-i", f]
    vocal_idx = []
    for clip, a, b, fx in SEGS:
        vocal_idx.append(len(inputs) // 2)
        inputs += ["-i", os.path.join(ROOT, "sep", "out", "htdemucs", CLIPS[clip][0], "vocals.wav")]
    music_idx = len(inputs) // 2
    inputs += ["-ss", str(MUSIC_START), "-i", MUSIC]
    sfx = {}
    for name in ("whoosh", "whoosh_long", "impact", "riser", "subdrop"):
        sfx[name] = music_idx + 1 + len(sfx)
        inputs += ["-i", os.path.join(HERE, "sfx", name + ".wav")]

    fc = []
    n = len(SEGS)
    fc.append("".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vcat]")
    fc.append("[vcat]split[vb][vg];[vg]gblur=sigma=28,eq=brightness=0.02[glow];"
              "[vb][glow]blend=all_mode=screen:all_opacity=0.16,"
              "eq=contrast=1.07:saturation=1.16,"
              "curves=master='0/0 0.25/0.22 0.5/0.5 0.8/0.84 1/1',"
              "colorbalance=rs=0.03:bs=-0.03:rh=0.04:bh=-0.02,"
              "vignette=PI/4.5,noise=alls=4:allf=t,"
              f"ass='{ass}',format=yuv420p[vout]")
    for k, (clip, a, b, fx) in enumerate(SEGS):
        d = b - a
        fc.append(f"[{vocal_idx[k]}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000,"
                  f"afade=t=in:d=0.015,afade=t=out:st={d - 0.03:.3f}:d=0.03[v{k}]")
    fc.append("".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1,volume=1.6[dlg]")
    fc.append("[dlg]asplit[dlg1][dlgsc]")
    fc.append(f"[{music_idx}:a]atrim=0:{total + 0.5},asetpts=PTS-STARTPTS,aresample=48000,"
              f"volume='0.55+0.45*min(1,t/{total * 0.75:.2f})':eval=frame,"
              f"afade=t=out:st={total - 1.4:.2f}:d=1.4[mus]")
    fc.append("[mus][dlgsc]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350:makeup=1[musd]")
    # SFX placement
    uses = []                                   # (sfx name, label, start time, volume)
    def place(name, at, vol):
        uses.append((name, f"s{len(uses)}", at, vol))
    for (ct, fx), (b0, _) in zip(cuts[1:], bounds[1:]):
        place("whoosh", ct - 0.22, 0.45)
        if fx == "shake":
            place("impact", ct, 0.8)
        if fx == "flash":
            place("subdrop", ct, 0.6)
    logo_t = bounds[-1][0]
    place("riser", logo_t - 3.0, 0.25)
    place("impact", logo_t, 1.0)
    place("subdrop", logo_t, 0.8)
    for name, idx in sfx.items():
        mine = [u for u in uses if u[0] == name]
        if not mine:
            continue
        fc.append(f"[{idx}:a]asplit={len(mine)}" + "".join(f"[{u[1]}in]" for u in mine))
        for _, lab, at, vol in mine:
            ms = max(0, int(at * 1000))
            fc.append(f"[{lab}in]volume={vol},adelay={ms}|{ms}[{lab}]")
    fx_tracks = [u[1] for u in uses]
    mix_in = "[dlg1][musd]" + "".join(f"[{l}]" for l in fx_tracks)
    fc.append(f"{mix_in}amix=inputs={2 + len(fx_tracks)}:normalize=0:duration=first,"
              "loudnorm=I=-14:TP=-1.0:LRA=11,aresample=48000[aout]")

    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}", "-r", "24000/1001",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    print(f"done: {OUT} ({total:.1f}s)")


if __name__ == "__main__":
    main()
