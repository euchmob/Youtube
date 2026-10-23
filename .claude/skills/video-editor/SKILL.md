---
name: video-editor
description: עורך סרטונים — making YouTube Shorts edits from Avatar series (currently Avatar: Seven Havens). Use for ANY request to make, plan, edit or improve a video/short/edit for the user's YouTube channel. Holds the user's taste rules, what they liked and disliked, and the working technical pipeline.
---

# עורך סרטונים (Video Editor)

The user makes YouTube Shorts edits about Avatar (right now: **Avatar: Seven Havens**).
This skill is the memory of their taste. **Keep it updated:** after every video, add what the
user liked to "Liked" and delete/replace anything they disliked. Their feedback always wins over
anything written here.

Talk to the user in Hebrew. They follow along from their phone.

## Workflow (always in this order)

1. **Know the series first.** Read `series-notes.md` (episodes, characters, themes, theories).
   Refresh it with a web search when new episodes have aired.
2. **Pitch before building (rule 8).** Before downloading/rendering anything expensive, send the
   user: the video idea in one line, the clip list (episode + scene, in order), the music choice,
   and the **script word-for-word** exactly as it will be heard/captioned. Wait for approval.
3. Find clean source clips, build, verify (captions-vs-speech check), send.
4. Update this skill with the feedback.

## The user's rules

1. **Understand the series** — the hottest theories, the most interesting moments of each
   episode. Use that to pick ideas fans care about.
2. **Clean, good-quality clips.** Do NOT use TikTok reposts with burned-in subtitles/meme text and
   then try to erase them. Search harder for clean HD sources, even if it takes longer.
3. **One topic per video, in series order.** Every clip must serve the single topic (e.g. "Pavi is
   afraid of being the Avatar"). Clips must follow the show's chronology — never show episode 3
   and then episode 1.
3b. **The script must tell a story, not list clips.** One through-line (e.g. "the twins remember
   nothing, and every adult around them hides something"): hook question → clues → twist → payoff,
   ideally ending on an open question that makes viewers comment. Every scene answers the previous
   scene's question and raises the next. When pitching, explain how each beat connects.
   Never state a fan theory as fact — let the edit imply it.
4. **Creative, alive transitions.** The video must feel energetic and alive — vary transitions
   (punch-in zooms, whip/blur, flash, shake on impacts, speed ramps, light leaks, match cuts).
   Don't repeat the same transition every cut.
5. **Music is the most important part.** Use music from **Avatar: The Last Airbender** (the
   original series score). Pick the track that best fits the mood and the timeline (build-ups
   landing on the emotional beat, drops on cuts). Keep searching for the best-fitting track.
6. **Captions appear only while someone is speaking.** A caption over silence = viewers leave.
   A short hold after a line ends is OK. Also: avoid long silent stretches in the video overall.
7. **Caption design:** glowing, beautiful, feels like it belongs to the Avatar world.
   **Every character gets their own colour** chosen from their personality/element; when that
   character speaks, their captions use that colour. Decide the palette before building.
8. **Pitch first** (see workflow) — don't burn tokens/time before the user approves the plan.
9. **Visuals:** the show already looks good — push it a bit further so it pops on a Shorts feed
   (contrast, saturation, warm/cool split, bloom/glow, subtle grain, vignette). Lively, eye-catching.

## Format

- Vertical **1080x1920** for YouTube Shorts, ~30-55 s.
- Loudness ≈ -14 LUFS, true peak -1 dB. Dialogue clearly above the music (music ducks under speech).

## Liked

- Glowing word-by-word captions that pop in as each word is spoken (first two edits).
- Warm colour grade with glow.

## Disliked (don't do again)

- Just cutting the official trailer — too easy/boring. Use real episode scenes.
- TikTok clips with burned-in text (even after removal, it's not clean).
- Captions that show while nobody is speaking.
- Mixing topics / jumping around the timeline.
- Ideas built on old episodes (pitched eps 1-3 "Pavi's fear" → "not interesting"). **Build ideas
  from the most recent batch of episodes** (when asked: eps 4-6) — that's what's relevant to viewers now.

## Character caption palette (Seven Havens)

Decide/confirm per video; keep consistent across videos once the user approves.
See `series-notes.md` for personalities. Current proposal:

| Character | Colour | Why |
|---|---|---|
| Pavi (Avatar, earthbender twin) | gold-amber `#FFC93C` + white-gold glow | Avatar light, warmth, earth |
| Nisha (twin, earthbender) | jade green `#4CE08A` | earthbender, fierce/loyal |
| Jae (Brigade airbender, narrator) | sky silver-white `#E6F3FF` + soft blue glow | air, calm, by-the-schedule |
| Karthik (Brigade commander) | deep orange `#FF8A2E` | leader, Brigade orange uniform |
| Korra (past Avatar) | cyan/Avatar-state white `#B8F4FF` | spirit / Avatar State |
| Villains / Faceless | blood red `#FF3B3B` | threat |
| Others | soft white `#F2F2F2` | neutral |

## Technical pipeline (what works in the cloud container)

Scripts live in `pipeline/` in this repo.

- **Clean clip sources:** the official YouTube channel "Avatar Legends" posts clean HD episode
  clips — best source. Paramount+ is DRM (unusable). Trailer is on Dailymotion but only 288p.
  Don't try to bypass bot-checks (Invidious/Anubis, Cloudflare) — not allowed.
- **Downloads:** YouTube blocks the cloud IP ("Sign in to confirm you're not a bot") — needs
  the user's `cookies.txt` (`yt-dlp --cookies cookies.txt`), or run the session on the user's
  computer, or the user uploads the clips. TikTok works with
  `yt-dlp --impersonate chrome` (needs `pip install curl_cffi`) but official TikToks have
  burned-in text → avoid (rule 2). Dailymotion only serves 288p anonymously.
- **Speech/captions:** separate vocals with Demucs (`python3 -m demucs --two-stems=vocals`),
  transcribe the vocal stem with faster-whisper `large-v3` (word timestamps), then snap every
  word onto voiced frames of the vocal stem (`pipeline/build_short.py: verified_words`) and clip
  caption events to voiced frames. Verify: zero caption frames over silence (±40 ms).
  Whisper mishears names: Ellora, Jae, Pavi, Nisha, Karthik — fix them.
- **Mix:** vocal stem + music (sidechain-ducked by dialogue) + SFX (`pipeline/sfx.py` synthesizes
  whoosh/impact/riser/subdrop) → loudnorm -14 LUFS.
- **Captions:** ASS rendered by ffmpeg/libass. Glow = 3 layers (wide blur, tight blur, crisp core).
  Font: Inter Display Black (installed); consider an Avatar-style display font.
- Output video is ~100+ MB — never commit .mp4 (GitHub 100 MB limit); send via SendUserFile.
