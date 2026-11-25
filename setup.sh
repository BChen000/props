#!/bin/bash
# One-step setup for a fresh session (Claude cloud sessions are Ubuntu 24.04, 2 CPU cores, no GPU).
# Always installs numpy, scipy, Pillow, matplotlib and ffmpeg; add the groups your prop needs:
#   --bpy       Blender 5.3 as a Python module (pip bpy==5.3.0, ~370 MB)   cloth-faces, glass-shatter, xylophone-*, marble-*
#   --blender4  Blender 4.0.2 from apt (EEVEE Legacy)                      marble-song-battle
#   --skia      skia-python 144.1 + fonttools/brotli                      ability-*, battle-overlays/-screen-layout, fighter-cards,
#                                                                         impact-fx, neon-*, escape-rings, question-thumbnail, ring-escape
#   --cairo     pycairo 1.29.2 (builds against libcairo2-dev)             style-kit and the Sword Roulette props
#   --numba     numba 0.68.1                                              ring-escape
#   --opencv    opencv-python                                            marble-plate-compositor, xylophone-song-template
#   --exr       OpenEXR 3.5 + scikit-image 0.26                           cloth-faces, glass-shatter
#   --pybullet  pybullet 3.2.7 (builds from source on Python 3.13: slow)  glass-shatter
#   --fonts     Poppins (style-kit) and DejaVu Sans Bold (neon-kit)
#   --all       everything above
# Usage:  ./setup.sh --blender4                 PY=/path/to/python ./setup.sh --skia --fonts
set -e
cd "$(dirname "$0")"
PY=${PY:-python3}
want() { [[ " $ARGS " == *" --all "* || " $ARGS " == *" $1 "* ]]; }
ARGS="$*"
PIPFLAGS="-q --root-user-action=ignore"
IN_VENV=$($PY -c "import sys; print(int(sys.prefix != sys.base_prefix))")
if [ "$IN_VENV" = "0" ] && ! $PY -m pip install -q --dry-run pip >/dev/null 2>&1; then PIPFLAGS="-q --root-user-action=ignore --break-system-packages"; fi
pipi() { echo "pip: $*"; $PY -m pip install $PIPFLAGS "$@"; }
SUDO=""; [ "$(id -u)" != "0" ] && command -v sudo >/dev/null && SUDO="sudo"
apti() {
  if ! command -v apt-get >/dev/null; then echo "no apt-get: install $* yourself (e.g. brew on a Mac)"; return 0; fi
  echo "apt: $*"; $SUDO apt-get install -y -qq --no-install-recommends "$@" >/dev/null 2>&1 || { $SUDO apt-get update -qq >/dev/null 2>&1; $SUDO apt-get install -y -qq --no-install-recommends "$@" >/dev/null; }
}

pipi numpy scipy pillow matplotlib
command -v ffmpeg >/dev/null || apti ffmpeg
want --bpy && pipi bpy==5.3.0
if want --blender4; then
  if command -v blender >/dev/null && blender --version 2>/dev/null | grep -qE "Blender 4\.[01]\."; then echo "blender 4.0/4.1 already installed"
  else apti blender; fi
  blender --version 2>/dev/null | head -1
fi
want --skia && pipi skia-python==144.1 fonttools brotli
if want --cairo; then apti libcairo2-dev pkg-config; pipi pycairo==1.29.2; fi
want --numba && pipi numba==0.68.1
want --opencv && pipi opencv-python
want --exr && pipi OpenEXR==3.5.* scikit-image==0.26.*
want --pybullet && pipi pybullet==3.2.7
if want --fonts; then
  $PY ball-sims/style-kit/get_fonts.py || echo "Poppins download failed: see ball-sims/style-kit/README.md"
  $PY ball-sims/neon-kit/get_fonts.py || echo "DejaVu download failed: see ball-sims/neon-kit/README.md"
fi
echo "setup done"
