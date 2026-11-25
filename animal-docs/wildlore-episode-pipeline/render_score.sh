#!/bin/bash
# Renders the score MIDI to audio with FluidSynth (2.3.4) and the FluidR3_GM General MIDI soundfont, 48 kHz stereo.
# SF2 defaults to the Debian/Ubuntu fluid-soundfont-gm path; set SF2=... elsewhere.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WILDLORE_WORK:-$HERE/build}"
SF2="${SF2:-/usr/share/sounds/sf2/FluidR3_GM.sf2}"
fluidsynth -ni -q -r 48000 -g "${GAIN:-0.5}" -F "$WORK/audio/score_raw.wav" "$SF2" "$WORK/audio/score.mid"
echo "wrote $WORK/audio/score_raw.wav"
