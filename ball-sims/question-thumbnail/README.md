# question-thumbnail

A 1080×1920 Shorts thumbnail template with a big two-line question over a game scene. Line 1 is white, and line 2 is huge yellow with a warm glow. Both have a thick dark outline and a drop shadow. A glowing crown sits between the text and the scene.

The default scene is the Ring Escape arena, zoomed 1.5× at 5.2 s: the marbles have motion trails, ring 3 has just shattered, and no marble has a crown or holder ring, so the winner isn't spoiled. It promises what the video's opening delivers (who gets out of the rings first).

**Used in:** Ring Escape (Nov 2026). Running `python question_thumbnail.py` with the shipped settings reproduces the delivered thumbnail pixel-for-pixel, both the PNG and the JPEG.

## Files
- `question_thumbnail.py`: the module and CLI.
- `style.json`: text sizes, colours, outline, crown and scene placement.
- `preview.png`: the Ring Escape thumbnail, rendered by this code.

## Reuse
```bash
python question_thumbnail.py                                   # out/thumbnail.png + out/thumbnail.jpg
python question_thumbnail.py --line1 "WHO WINS" --line2 "THE CROWN?"
python question_thumbnail.py --scene ../ring-escape/out/stills/f0330.png --line1 "WHICH COLOR" --line2 "ESCAPES?"
```
- `--scene` takes any 1080×1920 image as the backdrop, e.g. a still from another ball-sim template.
- The settings to change are at the top of the file: texts, sizes, colours, crown position, scene time and zoom.
- Keep the text in the top ~25 % and leave the bottom ~10 % quiet, because YouTube overlays the view count there on channel pages.
- Custom Shorts thumbnails are uploaded in YouTube Studio on a computer. If your channel can't upload one yet, pick the video's first frame in the frame picker; Ring Escape's frame 0 is built to work as a cover.
- Don't commit `out/`.

## Dependencies (tested)
- `../neon-kit` and `../crown-icon`
- skia-python 144.1, Pillow 12.3.0 (JPEG), Python 3.13.18
- DejaVu Sans Bold 2.37 (run `python ../neon-kit/get_fonts.py`; font files aren't in the repo)
- For the default Ring Escape scene only: `../ring-escape` and the props it uses (including `../battle-fx`, `../style-kit` and `../sword`), plus numba 0.68.1, numpy 2.5.3 and pycairo 1.29.2. With `--scene <image>` none of these are needed.

No photos or third-party images are used.
