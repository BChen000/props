"""Downloads the fonts into fonts/ (all SIL Open Font License, from google/fonts): Poppins ExtraBold (captions,
counters, titles), Caveat Brush (the shadow's red handwriting) and Bangers (the what-if look's punch captions).
Checks SHA-256 and skips files already present.

  python get_fonts.py
"""
import hashlib
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl/'
FONTS = {
    'Poppins-ExtraBold.ttf': (GF + 'poppins/Poppins-ExtraBold.ttf', 'f2ab17c1a63a0ecc12c2461848fc8a469395e3cd2d641803e889c643d9f958e1'),
    'CaveatBrush-Regular.ttf': (GF + 'caveatbrush/CaveatBrush-Regular.ttf', 'e565bd7bffd895ca64f8d1cb77c816b9b38d9c010246386a07c9648592f6f282'),
    'Bangers-Regular.ttf': (GF + 'bangers/Bangers-Regular.ttf', '4160a7311de9342674cce9160cde9fcbb30f48190397d86ff1b70b455af65824'),
}


def main():
    d = os.path.join(HERE, 'fonts')
    os.makedirs(d, exist_ok=True)
    for name, (url, sha) in FONTS.items():
        p = os.path.join(d, name)
        if os.path.exists(p) and hashlib.sha256(open(p, 'rb').read()).hexdigest() == sha:
            print('  ok      ', name)
            continue
        data = urllib.request.urlopen(url, timeout=60).read()
        got = hashlib.sha256(data).hexdigest()
        if got != sha:
            raise SystemExit(f'{name}: SHA-256 {got} does not match {sha} (upstream changed; check the file and update)')
        open(p, 'wb').write(data)
        print('  wrote   ', name, len(data), 'bytes')


if __name__ == '__main__':
    main()
