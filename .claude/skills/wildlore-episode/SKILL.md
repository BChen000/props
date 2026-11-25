---
name: wildlore-episode
description: Make a Wildlore nature-documentary Short about a fictional species in Blender, starting from the animal-docs props in GJ's BChen000/props repo.
---

# Wildlore episode

Wildlore is GJ's channel of sincere, NatGeo-style documentaries about fictional creatures and plants.
- Format: vertical 1080x1920 at 24 fps, narrated by an older British voice.
- Tone: played straight, never a parody.
- Animation: GJ cares most about no clipping and no bad animation.

## 1. Start from the props repo (don't rebuild what exists)
1. `add_repo` BChen000/props (read access).
2. `git clone --depth 1 https://github.com/BChen000/props /home/claude/props`.
3. Read `CLAUDE.md` for the prop index, then the READMEs in `animal-docs/`. The core pieces are:
   - `wildlore-blender-kit/bblib.py`: render look, worlds, camera, lights, animation helpers, bramble plant, forest set
   - `wildlore-narrator`: the Kokoro voice
   - `wildlore-episode-pipeline`: timeline, score, mix and ffmpeg assembly
   - `wildlore-title`: thumbnail title
4. Check the creature and plant props (`robin`, `blue-raspberry`, `dragons`, ...) for anything reusable.
5. For creatures over painted skies, volcanoes, karst mist, storms or rain (fast on CPU), use the Two Dragons stack:
   - `dragons` (bpy 5.3 Cycles)
   - `wildlore-2d-comp`
   - `creature-sfx`
   - `two-dragons-episode`, the complete pipeline of a 2:53 episode

## 2. Set up once per session
```bash
cd /home/claude/props && ./setup.sh animal-docs
```
This installs the Python packages, Cinzel and Cormorant fonts, the Kokoro model and the asset pack. The pack is the HDRIs, textures and bee the episode used: 56 MB, downloaded from their original GitHub repos into `WILDLORE_ASSETS` (default `/home/claude/assets`), pinned and hash-checked. It also checks Blender 4.0/4.1 (EEVEE Legacy), ffmpeg, FluidSynth with FluidR3_GM and xvfb.

## 3. Script and voice
1. Use GJ's script as given: one narration line per row in `lines.txt`.
2. Audition hard words with `narrate.py --say`.
3. Add phoneme fixes for any mispronunciations.
4. Run `narrate.py lines.txt --out $WILDLORE_WORK/vo --polish`.
5. Keep the voice at normal speed. GJ rejected a 1.34× read as "too sped up". Budget about 330 words for a Short under 3:00.
6. Check every line with `shared/narration-check/check.py words` until there are 0 errors. Then run `phrases` for the cut points.

## 4. Shots
Each shot is its own script importing `bblib`.
- **Drafts:** draft at `RES=540x960` and check part of a shot with `FRANGE=a-b`.
- **Check stills first:** before any full render, look at stills of the busiest frames, checking for interpenetration, popping and anything sinking into surfaces.
- **Full renders:** 3 TAA samples. Expect 10-25 s a frame on 2 CPU cores, so queue the shots and render them one at a time.
- **Temp files:** never let two jobs share a temp file name.
- **Macro shots:** use the short-lens, small-sensor trick for depth of field (see the kit README).

## 5. Timeline, sound and edit
1. In `timeline.py`, set `SEGS` (shots, frames, crossfades) and `VO` (line anchors). Run it until there are no overlaps.
2. Rewrite the cue sheet in `score.py`, then run `render_score.sh`.
3. Rewrite the per-shot effect cues in `mix.py`, then run it.
4. In `assemble.py`, set the title, species and captions. The title card sits at 64.5 % height with the species name under it, and the WILDLORE end card comes last. Loudness is -14 LUFS.

## 6. Review
Have an independent subagent review the rough cut and the final, from extracted frames and contact sheets. It should check for:
- clipping
- stiff or broken motion
- caption and title safe zones
- audio sync

Fix every must-fix item before delivering.

`two-dragons-episode/review_brief.md` is a tested brief. It also covers:
- joins inside renders that were extended or patched: compare crops of the eye and skin, which whole-frame scans miss
- whether each shot matches the narration's words

After fixing, resume the same reviewer for a verification pass.

## 7. Thumbnail, title and description
- **Thumbnail still:** render a still with the top third calm (a macro or creature close-up), then run `wildlore_title.py`. Check it at 180x320, and keep text out of the bottom 20 % (YouTube's overlay).
- **Title:** a curiosity question the video answers, which complements the thumbnail text instead of repeating it. Example: "What Makes the Blue Raspberry Blue?"
- **Description:** a short in-character hook paragraph, then `Species: <Latin name>` (plus `Rare variant:` if there is one), then a would-you-rather question, then 3 hashtags (creature tag, #mythicalcreatures, #naturedocumentary). If the episode used the kit's asset pack, the last line is the credit line from `wildlore-blender-kit/ASSET_LICENSES.md`: the bee and the bark are CC BY 4.0.
- **Style:** no emoji, and no "doesn't exist" disclaimers.
- **Deliver:** the final mp4, the thumbnail JPG, and `title_and_description.txt`.

## 8. Give back
Add any new reusable creature, plant, material or scene to the props repo under `animal-docs/` (skill: `add-props-to-repo`).
