"""Downloads the episode's three display fonts into fonts/ from google/fonts at a pinned commit, checking SHA-256.

  Special Elite (typewriter; Apache 2.0, Astigmatic), Permanent Marker (marker; Apache 2.0, Font Diner),
  Anton (condensed headlines and the 3D chart numbers; SIL OFL 1.1, Vernon Adams).
  python3 get_fonts.py          (skips files that are already there and match)
"""
import hashlib
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('DI_FONTS', os.path.join(HERE, 'fonts'))
COMMIT = '5026800714d07231937d92eb4cceabf06e05d74e'
FILES = {
    'SpecialElite-Regular.ttf': ('apache/specialelite', 'a776fcb4ceb8bdf03e2967688ebdad42680de5b91a7e62c17e718ae212d14bc4'),
    'PermanentMarker-Regular.ttf': ('apache/permanentmarker', '28f82c8a7943cb8e9d599f8554da1d4fc75dbcf69b9885ad6c0611d20c6946c5'),
    'Anton-Regular.ttf': ('ofl/anton', 'a4ba3a92350ebb031da0cb47630ac49eb265082ca1bc0450442f4a83ab947cab'),
}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    bad = 0
    for name, (d, want) in FILES.items():
        p = os.path.join(OUT, name)
        if os.path.exists(p) and sha(p) == want:
            print(f'ok       {name}')
            continue
        url = f'https://raw.githubusercontent.com/google/fonts/{COMMIT}/{d}/{name}'
        urllib.request.urlretrieve(url, p + '.part')
        if sha(p + '.part') != want:
            os.remove(p + '.part'); print(f'FAILED   {name}: checksum mismatch'); bad += 1; continue
        os.replace(p + '.part', p)
        print(f'fetched  {name}')
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
