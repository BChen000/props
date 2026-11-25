---
name: add-props-to-repo
description: Package reusable animation props from the current project into GJ's BChen000/props GitHub repo (prop folders, READMEs, previews), test them, and open a PR.
---

# Add props to BChen000/props

The repo holds reusable building blocks, so future animations are faster and match the style of GJ's other videos. It's public.

## 1. Attach and read
1. `add_repo` owner BChen000, repo props, access push.
2. `git clone --depth 1 https://github.com/BChen000/props /home/claude/props` (allow a long timeout).
3. `register_repo_root`.
4. Read `CLAUDE.md` (conventions and prop index), and one or two existing prop READMEs in the same channel, to match their format.

## 2. Conventions
- **Layout:** `<channel>/<prop-name>/`, lowercase with dashes. Channels are:
  - `ball-sims` (Marble Pop)
  - `kids-songs` (Rabbit Rhymes / Story Time with Kenji)
  - `animal-docs` (Wildlore)
  - `shared`
- **Each prop folder holds:**
  - runnable code with a settings block at the top, holding the shipped values and overridable from the environment or command line
  - `style.json`
  - `README.md`
  - `preview.png`
  - `assets/`, only if needed
- **README sections:** a title and a summary paragraph (its first sentence becomes the index line), the preview image, `**Used in:**` (with what was verified), `## Files`, `## Reuse` (commands), `## Gotchas`, `## What it can't do`, `## Dependencies (tested)`.
- **Never commit:**
  - finished videos
  - font files: write a `get_fonts.py` instead
  - model weights: write a downloader instead
  - photos of real people
  - files over 25 MB
  - third-party assets of unclear licence: document them and their sources in the README instead
  - third-party assets of clear licence: download them instead, like `animal-docs/wildlore-blender-kit/get_assets.py`. It pins a commit, checks each file's SHA-256, and records the licences and credit line in `ASSET_LICENSES.md`. Find a file's origin by hashing it against candidate repos (a `git clone --filter=blob:none --depth 1` lists a repo's files without downloading them).

## 3. Make the code portable
- **Paths:** replace absolute paths with paths relative to the script (`HERE = os.path.dirname(os.path.abspath(__file__))`), plus env overrides. Sibling props are imported via `../<prop>`.
- **Outputs:** write to `out/` or `build/`, and add a `.gitignore` for them plus `fonts/`, `models/` and `__pycache__/`.
- **Setup:** if the prop needs a new package, font or tool, add it to that channel's section of `setup.sh`.

## 4. Test from the clone (required)
- Run every script from the repo folder. For Blender scenes, use a low resolution such as `RES=540x960` with few samples.
- Where you can, show the shipped outputs are reproduced: pixel-diff images, byte-compare MIDI or filters, sample-compare audio stems.
- Run every example in the README.
- In the README, state only what you actually verified.

## 5. Previews
Downscale to about 720x1280 PNG, around 1-2 MB at most. For audio props, draw a waveform or timeline. For pipelines, draw a contact sheet of the shots.

## 6. Index, commit, push, PR
1. Run `python update_index.py`, which regenerates the prop index in `CLAUDE.md`.
2. Branch: `git checkout -b add-<topic>`.
3. Commit, ending the message with the session's attribution lines.
4. Push: `git -c push.negotiate=true push -u origin add-<topic>`.
5. Open the PR with the REST API, because `gh pr create` fails (GraphQL is blocked):
   ```bash
   gh api repos/BChen000/props/pulls -f title='...' -f head='add-<topic>' -f base='main' -F body=@/tmp/pr_body.md
   ```
6. If main moved on, rebase before pushing: `git fetch --depth=50 origin main && git rebase --onto origin/main <commit before yours>`.
7. Give GJ the PR link. Merge only when he asks: `gh api -X PUT repos/BChen000/props/pulls/<n>/merge`.
