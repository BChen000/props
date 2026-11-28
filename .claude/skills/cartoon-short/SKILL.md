---
name: cartoon-short
description: Make a narrated vertical cartoon Short from shared/cartoon-shorts in GJ's BChen000/props repo - a motivational Short (lit bean or stick figure) or a Short in one of the five cartoon looks (what-if, palace, castle, desert, pill).
---

# Cartoon Short

`shared/cartoon-shorts` makes narrated, captioned 1080×1920 Shorts at 30 fps in skia-python, with no Blender and no GPU. A Short takes 1–4 minutes to render on a 2-core cloud session.

Every Short is one episode file in `episodes/`, built with `python make_short.py <episode>`. Read the prop's README for the API.

## Pick a style
| Style | How | Start from |
|---|---|---|
| Lit bean (white bean person, red-rimmed shadow, gold captions) | default | `five_more_minutes`, `one_more_video`, `when_im_ready`, `two_paths`, `one_percent`, `future_you` |
| Stick figure (same Shorts, stick people) | `--style stick` | any motivational episode |
| What-if (black heads, big eyes, clothes, HUD counters) | `cast.person(..., 'whatif')`, `CAPTIONS = 'punch'` | `look_whatif` + a motivational episode's structure |
| Palace (big toon heads, crowns, red/purple/gold) | `'palace'`, `CAPTIONS = 'outline'` | `look_palace` |
| Castle (white peg people, checkered floor) | `'castle'`, `CAPTIONS = 'outline'` | `look_castle` |
| Desert (small tunic workers, sand, diagrams) | `'desert'`, `CAPTIONS = 'karaoke'` | `look_desert` |
| Pill (bowl-cut pill people, town) | `'pill'`, `CAPTIONS = 'outline'` | `look_pill` |
| Island stickman (bare black stick figure) | `shared/stickman-style/build.py` | its `STORY` |

The `look_*` reels have no narration: they show each look's people and its six props (`cast_props.KITS`).

## Steps
1. **Set up:** `./setup.sh cartoon-shorts` from the repo root. It installs the packages, fonts, the Kokoro voice model and the Whisper checker.
2. **Copy the closest episode** to `episodes/<new_name>.py` and set `NAME`.
   - **Script:**
     - `SCRIPT` lines are `dict(scene, v, text, key, pre, ...)`.
     - `v` is the voice: `nar` (narrator), `sha` (the shadow's red handwriting), `old`, `story` (cartoon looks) or `None` for a silent beat.
     - `|` in `text` sets the caption breaks; `key` lists the highlighted words.
   - **Scenes:** `SCENES` maps names to `draw(c, t, x)`. `x.T` and `x.E` are the lines' start and end times in the scene.
     - Draw the lit and stick people with `humanoid.figure` and the cartoon looks with `cast.person`.
     - Draw props with `cast_props`, in a hand via `hold=`.
     - Add counters with `hud`, `day=` or `bubble`.
   - **Sound:**
     - `SCORE` is the motivational score (dark start, beat from the `title` scene) or `dict(kind='bed', ...)` (see `showcase.BEDS`).
     - `SFX(tl, spans, rng)` returns `(time, sound, gain)`.
   - **Thumbnail:** `THUMB_T` picks the thumbnail time.
3. **Check every spoken line** with `python check_lines.py <name>`. It mixes the soundtrack in seconds, without picture.
   - Reword any line marked CHECK and check again. Test rewrites fast with `--try "nar:..."`.
   - What helps: plain words, a stressed last word, one more word of context.
   - Clear loud sound effects from under the words.
4. **Look before rendering:** run `python make_short.py <name> --stills` and fix anything that overlaps the captions or is cut off.
5. **Render:** `python make_short.py <name>` (add `--style stick` for stick figures).
   - The result is `build/<name>/<name>.mp4` and `thumb.png`.
   - To redo some scenes only, use `--only 2,5`.
6. **Deliver** the mp4, the thumbnail, a title and a short description.
   - Thumbnails have no text. The engine turns captions, counters and bubbles off for them.
   - Motivational titles so far are the episode's phrase in capitals with a full stop: "5 MORE MINUTES.", "TWO PATHS.".
7. **Give back:** use the `add-props-to-repo` skill to add any new episode, set or prop, then open a PR.

## Rules GJ set
- **The bean person stays bald:** no hair tuft. The cartoon looks keep their own hair and hats.
- **Motivational Shorts:**
  - Take the mood of Day One Films (shadow inner voice, red handwriting, DAY counters), never their titles, lines or scenes.
  - No insults on the punching bag.
  - No mirror or staircase scenes.
- **Copying from references:** take a channel's look, never its stories, titles or characters. No copyrighted characters: no Goku, no Dragon Ball. Write original premises.
- **Narration** runs at normal speed: Kokoro at the speeds in `settings.VOICES`.
