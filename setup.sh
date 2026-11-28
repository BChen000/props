#!/usr/bin/env bash
# One-command setup for a session that works from this repo. Safe to re-run: anything already there is skipped.
#
#   ./setup.sh animal-docs              Wildlore: audio/voice Python packages, Cinzel + Cormorant + EB Garamond fonts,
#                                       the Kokoro narrator model (~350 MB), the Whisper checker model (~375 MB),
#                                       the Wildlore asset pack (~56 MB), tool checks
#   ./setup.sh animal-docs --no-models  same without the Kokoro and Whisper downloads
#   ./setup.sh animal-docs --bpy        also Blender 5.3 as a Python module (bpy, scikit-image, fast-simplification)
#                                       for the animal-docs dragons and griffin props and their episodes
#   ./setup.sh ball-sims                Marble Pop: skia, cairo, numba, OpenCV, matplotlib..., Poppins + DejaVu +
#                                       Montserrat fonts
#   ./setup.sh ball-sims --bpy          also Blender 5.3 as a Python module (bpy, OpenEXR, pybullet) for the Blender props
#   ./setup.sh kids-songs               Story Time with Kenji: skia, Kokoro, numpy/scipy audio, DejaVu fonts,
#                                       the int8 Kokoro narrator model (~120 MB), ffmpeg check
#   ./setup.sh cartoon-shorts           the cartoon Shorts engine (shared/cartoon-shorts, shared/stickman-style): the
#                                       kids-songs set above, sherpa-onnx, Poppins + Caveat Brush + Bangers fonts,
#                                       the Whisper checker model (~375 MB) for check_lines.py
#   ./setup.sh all                      every channel
#   ./setup.sh <channel> --check        only report what's missing, install nothing
#
# Packages install with `python3 -m pip` (PYTHON=... to use another interpreter). System tools (Blender, ffmpeg,
# FluidSynth, xvfb, rubberband) are only checked, with an install hint, because they need apt/brew.
set -u
cd "$(dirname "$0")"
CH="${1:-}"
[ $# -gt 0 ] && shift
NO_MODELS=0; BPY=0; CHECK=0
for a in "$@"; do
  case "$a" in
    --no-models) NO_MODELS=1 ;;
    --bpy) BPY=1 ;;
    --check) CHECK=1 ;;
    *) echo "unknown option $a"; exit 2 ;;
  esac
done
PY="${PYTHON:-python3}"
MISSING=()

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; }

has_mod() { "$PY" -c "import $1" >/dev/null 2>&1; }

pkgs() {  # args: pip-spec:module ...  (one pip call per package so one failure doesn't stop the rest)
  for pair in "$@"; do
    spec="${pair%%:*}"; mod="${pair##*:}"
    if has_mod "$mod"; then echo "  ok       $spec"; continue; fi
    if [ "$CHECK" = 1 ]; then echo "  missing  $spec"; MISSING+=("$spec"); continue; fi
    echo "  install  $spec"
    "$PY" -m pip install -q --break-system-packages "$spec" >/dev/null 2>&1 || "$PY" -m pip install -q "$spec" >/dev/null 2>&1
    if has_mod "$mod"; then echo "  ok       $spec"; else echo "  FAILED   $spec"; MISSING+=("$spec"); fi
  done
}

tool() {  # args: command hint
  if command -v "$1" >/dev/null 2>&1; then echo "  ok       $1 ($(command -v "$1"))"; else echo "  missing  $1  -> $2"; MISSING+=("$1"); fi
}

run() {  # a download step, skipped with --check
  if [ "$CHECK" = 1 ]; then echo "  (check only: skipped) $*"; else "$PY" "$@" | sed 's/^/  /'; fi
}

animal_docs() {
  echo "== animal-docs (Wildlore)"
  echo "-- Python packages"
  pkgs numpy:numpy scipy:scipy pillow:PIL soundfile:soundfile librosa:librosa pedalboard:pedalboard mido:mido \
       kokoro-onnx:kokoro_onnx fonttools:fontTools opencv-python-headless:cv2 pyloudnorm:pyloudnorm sherpa-onnx:sherpa_onnx \
       zstandard:zstandard matplotlib:matplotlib
  if [ "$BPY" = 1 ]; then pkgs bpy==5.3.0:bpy scikit-image:skimage fast-simplification:fast_simplification; fi
  echo "-- fonts (Cinzel, Cormorant Garamond Italic + its static weight-560 instance)"
  run animal-docs/wildlore-title/get_fonts.py
  echo "-- fonts (EB Garamond 12 Regular + Italic, for wildlore-2d-comp)"
  run animal-docs/wildlore-2d-comp/get_fonts.py
  echo "-- narrator model (Kokoro v1.0)"
  if [ -n "${KOKORO_DIR:-}" ] && [ -f "$KOKORO_DIR/kokoro-v1.0.onnx" ]; then echo "  ok       $KOKORO_DIR"
  elif [ -f /home/claude/models/kokoro/kokoro-v1.0.onnx ]; then echo "  ok       /home/claude/models/kokoro"
  elif [ "$NO_MODELS" = 1 ]; then echo "  skipped (--no-models)"
  else run animal-docs/wildlore-narrator/get_models.py; fi
  echo "-- narration checker model (Whisper small.en int8, shared/narration-check)"
  if [ -n "${WHISPER_DIR:-}" ] && [ -f "$WHISPER_DIR/small.en-encoder.int8.onnx" ]; then echo "  ok       $WHISPER_DIR"
  elif [ "$NO_MODELS" = 1 ]; then echo "  skipped (--no-models)"
  else run shared/narration-check/get_models.py; fi
  echo "-- tools"
  if command -v blender >/dev/null 2>&1; then
    v="$(blender --version 2>/dev/null | head -1)"
    case "$v" in
      "Blender 4.0"*|"Blender 4.1"*) echo "  ok       $v (EEVEE Legacy)" ;;
      *) echo "  WARN     $v: the Wildlore kit needs Blender 4.0 or 4.1 (EEVEE Legacy)"; MISSING+=("blender-4.0/4.1") ;;
    esac
  else echo "  missing  blender  -> apt-get install -y blender (Ubuntu 24.04 ships 4.0.2) or download 4.1"; MISSING+=("blender"); fi
  tool ffmpeg "apt-get install -y ffmpeg / brew install ffmpeg"
  tool fluidsynth "apt-get install -y fluidsynth fluid-soundfont-gm / brew install fluid-synth"
  tool rubberband "apt-get install -y rubberband-cli / brew install rubberband (the baby griffin narration's pitch shift)"
  if [ "$(uname)" = "Linux" ]; then tool xvfb-run "apt-get install -y xvfb (EEVEE needs a display)"; fi
  if [ "$BPY" = 1 ]; then echo "  info     the dragons and griffin props render with bpy 5.3 (Cycles), not the Blender binary above"; fi
  sf2="${SF2:-/usr/share/sounds/sf2/FluidR3_GM.sf2}"
  if [ -f "$sf2" ]; then echo "  ok       $sf2"; else echo "  missing  FluidR3_GM.sf2 -> apt-get install -y fluid-soundfont-gm, or set SF2="; MISSING+=("FluidR3_GM.sf2"); fi
  echo "-- third-party assets (downloaded from their original repos; see animal-docs/wildlore-blender-kit/ASSET_LICENSES.md)"
  if [ "$CHECK" = 1 ]; then out="$("$PY" animal-docs/wildlore-blender-kit/get_assets.py --check)"; rc=$?
  else out="$("$PY" animal-docs/wildlore-blender-kit/get_assets.py)"; rc=$?; fi
  echo "$out" | sed 's/^/  /'
  [ $rc -eq 0 ] || MISSING+=("wildlore-assets")
  A="${WILDLORE_ASSETS:-/home/claude/assets}"
  if [ ! -f "$A/tex/BroadleafBark.jpg" ]; then echo "  info     no bark/moss textures: trunks and moss fall back to procedural materials"; fi
}

ball_sims() {
  echo "== ball-sims (Marble Pop)"
  echo "-- Python packages"
  pkgs numpy:numpy scipy:scipy pillow:PIL matplotlib:matplotlib skia-python==144.1:skia pycairo:cairo numba:numba \
       opencv-python:cv2 fonttools:fontTools brotli:brotli scikit-image:skimage
  if [ "$BPY" = 1 ]; then pkgs bpy==5.3.0:bpy OpenEXR:OpenEXR pybullet==3.2.7:pybullet; fi
  echo "-- fonts (Poppins, DejaVu Sans Bold, Montserrat)"
  run ball-sims/style-kit/get_fonts.py
  run ball-sims/neon-kit/get_fonts.py
  run ball-sims/marble-raytrace-kit/get_fonts.py
  echo "-- tools"
  tool ffmpeg "apt-get install -y ffmpeg / brew install ffmpeg"
  tool gcc "apt-get install -y gcc (marble-raytrace-kit compiles its C path tracers with OpenMP)"
  if command -v blender >/dev/null 2>&1; then echo "  info     $(blender --version 2>/dev/null | head -1) (marble-song-battle needs 4.0 or 4.1)"
  else echo "  info     no blender: only marble-song-battle needs it -> apt-get install -y blender (Ubuntu 24.04 ships 4.0.2)"; fi
  if ! has_mod cairo; then echo "  hint     pycairo builds from source on Linux: apt-get install -y libcairo2-dev pkg-config python3-dev"; fi
}

kids_songs() {
  echo "== kids-songs (Story Time with Kenji)"
  echo "-- Python packages"
  pkgs numpy:numpy scipy:scipy pillow:PIL soundfile:soundfile skia-python==144.1:skia kokoro-onnx:kokoro_onnx \
       matplotlib:matplotlib
  echo "-- fonts (DejaVu 2.37: Sans, Sans Bold, Serif, Serif Bold, Serif Italic, Sans Mono Bold, Sans Condensed Bold)"
  run kids-songs/storytime-kit/get_fonts.py
  echo "-- narrator model (Kokoro v1.0 int8)"
  if [ -n "${KOKORO_DIR:-}" ] && [ -f "$KOKORO_DIR/kokoro-v1.0.int8.onnx" ]; then echo "  ok       $KOKORO_DIR"
  elif [ -f kids-songs/storytime-narrator/models/kokoro-v1.0.int8.onnx ]; then echo "  ok       kids-songs/storytime-narrator/models"
  elif [ -f /home/claude/models/kokoro/kokoro-v1.0.int8.onnx ]; then echo "  ok       /home/claude/models/kokoro"
  elif [ "$NO_MODELS" = 1 ]; then echo "  skipped (--no-models)"
  else run kids-songs/storytime-narrator/get_models.py; fi
  echo "-- tools"
  tool ffmpeg "apt-get install -y ffmpeg / brew install ffmpeg"
}

cartoon_shorts() {
  kids_songs
  echo "== cartoon-shorts (shared/cartoon-shorts, shared/stickman-style)"
  echo "-- Python packages"
  pkgs sherpa-onnx:sherpa_onnx
  echo "-- fonts (Poppins ExtraBold, Caveat Brush, Bangers)"
  run shared/cartoon-shorts/get_fonts.py
  echo "-- narration checker model (Whisper small.en int8, shared/narration-check)"
  if [ -n "${WHISPER_DIR:-}" ] && [ -f "$WHISPER_DIR/small.en-encoder.int8.onnx" ]; then echo "  ok       $WHISPER_DIR"
  elif [ -f shared/narration-check/models/whisper-small.en/small.en-encoder.int8.onnx ]; then echo "  ok       shared/narration-check/models"
  elif [ "$NO_MODELS" = 1 ]; then echo "  skipped (--no-models)"
  else run shared/narration-check/get_models.py; fi
}

case "$CH" in
  animal-docs) animal_docs ;;
  ball-sims) ball_sims ;;
  kids-songs) kids_songs ;;
  cartoon-shorts) cartoon_shorts ;;
  all) animal_docs; ball_sims; cartoon_shorts ;;
  -h|--help|"") usage; exit 0 ;;
  *) echo "unknown channel '$CH'"; usage; exit 2 ;;
esac

echo
if [ ${#MISSING[@]} -eq 0 ]; then echo "READY: nothing missing"; else echo "NOT READY: ${MISSING[*]}"; exit 1; fi
