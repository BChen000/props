# Working in this repo

This repo holds the code behind GJ's YouTube Shorts. When he asks for a new video, start from the closest prop here instead of building from scratch: each one already solves a format's look, physics, audio, HUD and delivery. The index of every prop, with run commands, setup flags and times, is in `README.md`. Read it first.

## A new video
1. Pick the closest complete generator in `README.md` and read its README: Reuse, Gotchas, What worked on YouTube, Dependencies.
2. Run `./setup.sh` with that prop's flags, e.g. `./setup.sh --blender4`. The pip groups take ~30 s; Blender takes a few minutes.
3. Change only what the new idea needs: `settings.py`, song or timing files. Keep the rest.
4. Before any long render, render a few frames (every Blender generator has a test or stills mode) and look at them.
5. Start the full render in the background and poll it in the same turn (background jobs stop a few minutes after a turn ends). Generators skip finished frames, so a stopped render resumes.
6. Deliver the mp4, a thumbnail, and a title and description in the style the prop's README says worked. Thumbnails have no text unless GJ asks: his best Shorts had text-free thumbnails.
7. Save the work back (below).

## The machine
- Claude cloud sessions: Ubuntu 24.04, 2 CPU cores, ~7 GB RAM, no GPU, Python 3.13.18 at `/usr/local` (plain `pip install` works), apt available.
- No GPU means Blender renders on the CPU: 1 to 2.5 hours per Blender video. That is the bottleneck, so check frames before committing to a full render.
- If GJ's Mac is linked to the chat (Claude desktop app, + → Add folder) or he runs Claude Code on it, render there instead: his GPU is far faster.

## Adding or updating a prop
- Folder: `<channel>/<prop-name>/`, lowercase with dashes. `ball-sims/` is Marble Pop; other channels get their own folder, and parts shared across channels go in `shared/`.
- Contents: runnable code with the settings at the top (`settings.py`), `style.json` (the look as numbers: canvas, colours, fonts, camera, render, audio, YouTube copy), `README.md`, `preview.png`, and `assets/` only if needed.
- README sections, in order: a summary paragraph with the run time, **Used in:** (video and date), the preview, Files, Reuse (commands with timings), What worked on YouTube (title, thumbnail, description), Gotchas, What it can't do, Dependencies with versions.
- The shipped settings should reproduce the delivered video. Say in the README how you checked.
- Never commit rendered videos, font files, photos of real people, `build/` output or any file over 25 MB. Audio is synthesized (no samples, no licensed music), and melodies must be public domain.
- When you add a prop, add it to `README.md`'s index and give `setup.sh` any new install flag it needs.
- Git: commit on a branch and open a pull request. Merge only when GJ asks.

## YouTube copy
- Titles: short and easy for young kids to understand, built on suspense or what's unique (e.g. `1 Face vs 1,000,000 Faces Blanket 🤯`).
- Descriptions: a one-line premise, a "Pick your … in the comments" line with coloured circles, `Made with …`, then a few hashtags.
