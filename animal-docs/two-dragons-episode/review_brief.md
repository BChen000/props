# Review brief template (Wildlore episode)

GJ asks for an independent review of every Wildlore episode by a separate subagent. This is the brief "The Two Dragons" used across three passes; the third pass found a real blocker the maker's own checks had missed. Copy it, fill in the `<...>` parts and the episode's facts, and give the subagent only this brief plus file paths, never your own conclusions.

---

# Review brief: "<TITLE>" (Wildlore fantasy nature-documentary Short)

You are an independent reviewer. You did not make this video. Find mistakes; do not praise it.
Every issue needs a timestamp (seconds) or frame number, what is wrong, and how bad it is
(BLOCKER = must fix before publishing, MAJOR = clearly visible or audible, MINOR = polish).

## Files
- Final video: `<WORK>/<FILE>.mp4` (1080x1920, 24 fps, AAC audio; must be under 3:00)
- Narration script (spoken verbatim, in order): `<episode>/script.txt`
- Narration timeline: `<WORK>/vo/timeline.json`; phrase timings: `<WORK>/vo/phrases.json`
- Raw narration: `<WORK>/vo/vo_raw.wav`; final mix: `<WORK>/audio/final_audio.wav`
- Shot list with first frames: `<episode>/shots2d.py` (`CUTS`, `TOTAL`)
- Blender renders: `<WORK>/renders/<shot>/####.png` (+ `meta.json`)
- Speech recognizer: `python <repo>/shared/narration-check/check.py words <script> <wav> --timeline <timeline>`, or
  `from asr import transcribe; transcribe(path, t0, t1)` with `<repo>/shared/narration-check` on `sys.path`.
  It writes numbers as digits ("One" -> "1"); `check.py` already allows for that.
- ffmpeg/ffprobe, numpy, opencv, PIL, soundfile and pyloudnorm are installed. Look at images with your Read tool.
- Work only in `<review folder>`. Do not modify, re-render or re-encode anything outside it. The machine has 2 CPU
  cores: decode the whole video at full size at most once or twice; downscaled scans plus targeted full-size grabs work.

## What it is supposed to be
A sincere (not parody) nature documentary in an older British narrator's voice about <SPECIES>. <Describe each creature's
look and setting, the title card text, the species labels and the end card, so the reviewer can spot wrong content.>

## Check the picture
1. Grab frames at least every 0.5 s and around every cut; look at full size wherever something looks off.
2. Look for: geometry through geometry (wings through the body, teeth through the jaw, feet sinking into or floating
   above rock, whiskers through the head), texture flicker, popping between frames, black or blank frames, a creature
   missing or awkwardly cut off, compositing errors (floating, wrong scale, hard edges or halos, background seams or
   tiling), fire not coming from the mouth, a misaligned split-screen divider, text misspelled, cut off or over the
   subject, effects drawn in front of the creature that should be behind it (lightning).
3. **Joins inside shots.** If any render was extended or patched after a model change, compare crops of the eye and
   the skin across the join frame by frame. Whole-frame difference scans miss these because grain dominates them: in
   "The Two Dragons" a changed eye shape at a join was invisible to the scanner and obvious in a 6x crop.
4. Frozen picture: a creature that stops moving while the shot continues (a render that ran out of frames), fire that
   freezes or jumps.
5. Does each shot match what the narrator says at that moment? Use `phrases.json`. List the key word cues and check
   each (for example: wings opening on "powerful wings", fire on "ignite", the roar on "territorial aggression").

## Check the sound
1. Transcribe the final mix line by line and compare with the script word for word.
2. Loudness about -14 LUFS integrated, true peak below -1 dBTP, no clipping, no clicks at line joins, no long gaps.
3. Effects against picture: fire roar under every fire shot, thunder just after each lightning flash, the roar with the
   open-mouth roar, whooshes with the fastest motion, wingbeat flaps matching the sprite's downstrokes, rain only under
   rain shots, no water or weather sounds under shots that have none.
4. Music: any tempo lurch or note pile-up at cuts (the score is time-warped to the edit).
5. Video and audio durations match; total under 3:00.

## Report format
Markdown grouped by BLOCKER / MAJOR / MINOR. Each item: timestamps, what is wrong, evidence (frame file or
measurement), suggested fix. End with one line: publishable as-is, or not.

---

## Follow-up pass
After fixing, resume the same reviewer (not a new one) with a short list of what changed and ask it to verify only
those fixes and check for regressions, in the same format. In "The Two Dragons" that pass took 13 minutes, against
35 for the full review.
