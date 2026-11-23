"""drawkit: shared skia helpers for the POWER BALLS props.

Fonts, outlined text, paints, easing curves and the gold crown. Every skia prop folder carries an
identical copy of this file so each folder runs on its own.

Fonts are not bundled. The code looks for Poppins-{SemiBold,Bold,ExtraBold,Black}.ttf in, in order:
$PROPS_FONT_DIR, ./fonts, ../fonts, ../../fonts, ../../shared/fonts, then the usual system font folders.
Get them with `python drawkit.py --fetch-fonts` (downloads into ./fonts) or from
https://fonts.google.com/specimen/Poppins.
"""
import os
import sys
from pathlib import Path

import skia

# ---------------------------------------------------------------- settings
FONT_FAMILY = 'Poppins'
FONT_WEIGHTS = ['SemiBold', 'Bold', 'ExtraBold', 'Black']
FONTSOURCE_VERSION = '5.3.0'      # the exact build used in the video (@fontsource/poppins, latin subset)
DARK = '#110C1C'                  # outline and drop-shadow color for the big text
CROWN = dict(outline='#965F0A', gold='#FFC832', band='#EBA519', jewel='#FFECAA')

HERE = Path(__file__).resolve().parent
_TF = {}
_FONTS = {}


# ---------------------------------------------------------------- colors and paints
def rgb(c):
    """'#RRGGBB' or (r, g, b) -> (r, g, b) ints."""
    if isinstance(c, str):
        c = c.lstrip('#')
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    return c


def hexc(c):
    r, g, b = rgb(c)
    return '#%02X%02X%02X' % (int(r), int(g), int(b))


def C(c, a=255):
    c = rgb(c)
    return skia.Color(int(c[0]), int(c[1]), int(c[2]), int(max(0, min(255, a))))


def mix(c1, c2, t):
    c1, c2 = rgb(c1), rgb(c2)
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))


def fill(c, a=255):
    return skia.Paint(AntiAlias=True, Color=C(c, a))


def stroke(c, w, a=255, cap=skia.Paint.kRound_Cap):
    p = skia.Paint(AntiAlias=True, Color=C(c, a), Style=skia.Paint.kStroke_Style, StrokeWidth=w)
    p.setStrokeCap(cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def new_surface(w, h):
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(w, h, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))


def save_png(surface, path):
    surface.makeImageSnapshot().save(str(path), skia.kPNG)


# ---------------------------------------------------------------- easing
def ease_out_back(x):
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def clamp01(x):
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------- fonts
def font_dirs():
    dirs = []
    env = os.environ.get('PROPS_FONT_DIR')
    if env:
        dirs.append(Path(env))
    dirs += [HERE / 'fonts', HERE.parent / 'fonts', HERE.parent.parent / 'fonts',
             HERE.parent.parent / 'shared' / 'fonts']
    home = Path.home()
    dirs += [home / 'Library' / 'Fonts', Path('/Library/Fonts'), home / '.fonts', home / '.local' / 'share' / 'fonts',
             Path('/usr/share/fonts'), Path('/usr/local/share/fonts'),
             Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts']
    return dirs


def _find_in(d, name):
    p = d / name
    if p.exists():
        return p
    if str(d).startswith(('/usr/share/fonts', '/usr/local/share/fonts')) and d.exists():
        hits = sorted(d.rglob(name))
        return hits[0] if hits else None
    return None


def find_fonts():
    names = {w: f'{FONT_FAMILY}-{w}.ttf' for w in FONT_WEIGHTS}
    for d in font_dirs():
        found = {w: _find_in(d, n) for w, n in names.items()}
        if all(found.values()):
            return found
    found = {}
    for w, n in names.items():
        for d in font_dirs():
            p = _find_in(d, n)
            if p:
                found[w] = p
                break
    missing = [names[w] for w in FONT_WEIGHTS if w not in found]
    if missing:
        raise FileNotFoundError(
            f'Missing fonts {missing}. Run `python {Path(__file__).name} --fetch-fonts` (saves into '
            f'{HERE / "fonts"}), or download Poppins from https://fonts.google.com/specimen/Poppins into a '
            f'fonts/ folder, or point PROPS_FONT_DIR at a folder holding them.')
    return found


def typeface(weight):
    if not _TF:
        for w, p in find_fonts().items():
            _TF[w] = skia.Typeface.MakeFromFile(str(p))
    return _TF[weight]


def font(weight, size):
    k = (weight, round(size, 1))
    f = _FONTS.get(k)
    if f is None:
        f = skia.Font(typeface(weight), size)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setSubpixel(True)
        _FONTS[k] = f
    return f


def fetch_fonts(dest=None):
    """Download the 4 Poppins weights into dest (default ./fonts).

    Tries the exact files the video used first (@fontsource/poppins latin woff2 via jsDelivr, then
    `npm pack`), converting them to TTF with fontTools (+ brotli); falls back to Google Fonts' TTFs.
    """
    import io
    import shutil
    import subprocess
    import tarfile
    import tempfile
    import urllib.request
    dest = Path(dest or HERE / 'fonts')
    dest.mkdir(parents=True, exist_ok=True)
    weights = {'SemiBold': 600, 'Bold': 700, 'ExtraBold': 800, 'Black': 900}

    def woff2_to_ttf(data, out):
        from fontTools.ttLib import TTFont
        f = TTFont(io.BytesIO(data))
        f.flavor = None
        f.save(str(out))

    try:
        for name, w in weights.items():
            url = (f'https://cdn.jsdelivr.net/npm/@fontsource/poppins@{FONTSOURCE_VERSION}/files/'
                   f'poppins-latin-{w}-normal.woff2')
            woff2_to_ttf(urllib.request.urlopen(url, timeout=30).read(), dest / f'Poppins-{name}.ttf')
        return 'fontsource (jsDelivr)'
    except Exception as e:
        print('jsDelivr failed:', e)
    if shutil.which('npm'):
        try:
            with tempfile.TemporaryDirectory() as td:
                subprocess.run(['npm', 'pack', f'@fontsource/poppins@{FONTSOURCE_VERSION}'], cwd=td, check=True,
                               capture_output=True)
                tgz = next(Path(td).glob('*.tgz'))
                with tarfile.open(tgz) as tf:
                    for name, w in weights.items():
                        member = tf.getmember(f'package/files/poppins-latin-{w}-normal.woff2')
                        woff2_to_ttf(tf.extractfile(member).read(), dest / f'Poppins-{name}.ttf')
            return 'fontsource (npm)'
        except Exception as e:
            print('npm failed:', e)
    for name in weights:
        url = f'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-{name}.ttf'
        (dest / f'Poppins-{name}.ttf').write_bytes(urllib.request.urlopen(url, timeout=30).read())
    return 'Google Fonts (GitHub)'


# ---------------------------------------------------------------- text and shapes
def text(c, s, x, y, size, weight='Black', col=(255, 255, 255), a=255, outline=None, ow=0, align='center',
         caps=True, shadow=0, max_w=None):
    """Draw s centered on (x, y) (cap-height centered when caps=True). Returns the text width."""
    f = font(weight, size)
    w = f.measureText(s)
    if max_w and w > max_w:
        size = size * max_w / w
        f = font(weight, size)
        w = f.measureText(s)
    m = f.getMetrics()
    base = y + (m.fCapHeight / 2 if caps else -(m.fAscent + m.fDescent) / 2)
    if align == 'center':
        x0 = x - w / 2
    elif align == 'left':
        x0 = x
    else:
        x0 = x - w
    blob = skia.TextBlob.MakeFromString(s, f)
    dark = rgb(DARK)
    if shadow:
        c.drawTextBlob(blob, x0, base + shadow, stroke(dark, ow + 2, a * 0.8) if outline else fill(dark, a * 0.8))
    if outline is not None and ow > 0:
        c.drawTextBlob(blob, x0, base, stroke(outline, ow, a))
    c.drawTextBlob(blob, x0, base, fill(col, a))
    return w


def crown(c, x, y, w, a=255):
    """Gold crown centered at (x, y), w px wide."""
    s = w / 100.0
    path = skia.Path()
    pts = [(-46, 30), (-50, -22), (-24, 6), (0, -34), (24, 6), (50, -22), (46, 30)]
    path.moveTo(x + pts[0][0] * s, y + pts[0][1] * s)
    for px, py in pts[1:]:
        path.lineTo(x + px * s, y + py * s)
    path.close()
    c.drawPath(path, stroke(CROWN['outline'], 7 * s, a))
    c.drawPath(path, fill(CROWN['gold'], a))
    c.drawRect(skia.Rect(x - 46 * s, y + 20 * s, x + 46 * s, y + 32 * s), fill(CROWN['band'], a))
    for px, py in [(-50, -22), (0, -34), (50, -22)]:
        c.drawCircle(x + px * s, y + py * s, 7 * s, stroke(CROWN['outline'], 4 * s, a))
        c.drawCircle(x + px * s, y + py * s, 7 * s, fill(CROWN['jewel'], a))


def style():
    return {
        'fonts': {'family': FONT_FAMILY, 'weights': FONT_WEIGHTS,
                  'source': f'@fontsource/poppins@{FONTSOURCE_VERSION} latin subset (woff2 -> ttf); same design as '
                            'https://fonts.google.com/specimen/Poppins',
                  'rendering': 'skia anti-aliased edging, subpixel positioning'},
        'outline_color': DARK,
        'crown': CROWN,
    }


if __name__ == '__main__':
    if '--fetch-fonts' in sys.argv:
        i = sys.argv.index('--fetch-fonts')
        dest = sys.argv[i + 1] if len(sys.argv) > i + 1 else None
        print('fonts from', fetch_fonts(dest), '->', Path(dest or HERE / 'fonts').resolve())
    else:
        print({w: str(p) for w, p in find_fonts().items()})
