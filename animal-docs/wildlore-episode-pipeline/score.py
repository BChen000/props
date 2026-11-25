"""The Blue Raspberry score as MIDI: 72 BPM in D, strings pad, harp arpeggios, flute/oboe melody, celesta and
glock sparkles, pizzicato, choir and timpani swells, cued to the shots in timeline.py.

  python score.py                -> $WILDLORE_WORK/audio/score.mid
  ./render_score.sh              -> score_raw.wav through FluidSynth + FluidR3_GM
The cues were written against the first cut (_OLD); warp() moves each one with its shot when shots are lengthened.
"""
import mido, random, math
random.seed(7)
TPB = 480
BPM = 72
SPB = 60.0 / BPM
mid = mido.MidiFile(ticks_per_beat=TPB)
events = {}  # channel -> list of (tick, msg)


import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import S as S_NEW, FPS as _FPS, WORK
# the cues below were written against the original cut; each event keeps its place inside its shot and moves with
# that shot, so notes sounding across a lengthened shot end simply sustain through the added pause
_OLD = [("A", 62, 0), ("B", 168, 0), ("C", 151, 0), ("D", 151, 0), ("E", 190, 0), ("F", 166, 0), ("H1", 104, 12), ("H2", 164, 8),
        ("H3", 94, 8), ("IJ", 341, 10), ("K", 223, 0), ("L1", 124, 0), ("L2", 134, 0), ("M1", 100, 0), ("M2", 130, 0), ("N", 338, 0),
        ("O", 88, 0), ("P", 206, 0), ("Q", 220, 0), ("R", 116, 0), ("S", 384, 12)]
_S_OLD = []
_t = 0
for _n, _f, _x in _OLD:
    _t -= _x
    _S_OLD.append((_t / _FPS, _n))
    _t += _f


def warp(t):
    k = None
    for st, n in _S_OLD:
        if st <= t + 1e-9:
            k = (st, n)
    return t if k is None else t + (S_NEW[k[1]] - k[0])


def tick(t):
    return int(round(warp(t) / SPB * TPB))


def note(ch, t, dur, p, v):
    events.setdefault(ch, []).append((tick(t), mido.Message('note_on', channel=ch, note=int(p), velocity=int(max(1, min(127, v))))))
    events.setdefault(ch, []).append((tick(t + dur), mido.Message('note_off', channel=ch, note=int(p), velocity=0)))


def cc(ch, t, num, val):
    events.setdefault(ch, []).append((tick(t), mido.Message('control_change', channel=ch, control=num, value=int(max(0, min(127, val))))))


def ramp(ch, t0, t1, v0, v1, num=11, step=0.25):
    n = max(1, int((t1 - t0) / step))
    for i in range(n + 1):
        cc(ch, t0 + (t1 - t0) * i / n, num, v0 + (v1 - v0) * i / n)


PROG = {"strings": 48, "slow": 49, "harp": 46, "flute": 73, "oboe": 68, "celesta": 8, "glock": 9, "pizz": 45, "cello": 42,
        "bass": 43, "horn": 60, "choir": 52, "timp": 47, "marimba": 12, "pad": 89, "revcym": 119}
CH = {"strings": 0, "harp": 1, "flute": 2, "oboe": 3, "celesta": 4, "glock": 5, "pizz": 6, "cello": 7, "bass": 8, "horn": 10,
      "choir": 11, "timp": 12, "marimba": 13, "pad": 14, "revcym": 15}
for name, ch in CH.items():
    events.setdefault(ch, []).append((0, mido.Message('program_change', channel=ch, program=PROG[name if name in PROG else "strings"])))
    cc(ch, 0, 7, 100)
    cc(ch, 0, 91, 70)   # reverb send
    cc(ch, 0, 93, 15)
    cc(ch, 0, 10, {"harp": 40, "flute": 75, "oboe": 72, "celesta": 50, "glock": 80, "pizz": 54, "cello": 60, "bass": 64, "horn": 50,
                   "choir": 64, "timp": 64, "marimba": 70, "pad": 64, "strings": 64, "revcym": 64}[name])

CH_ = {
    "D": ([50, 57, 62, 66, 69, 64], 38), "Bm": ([47, 54, 57, 62, 66], 35), "G": ([43, 50, 59, 62, 66], 31), "Asus": ([45, 52, 57, 62, 64], 33),
    "A": ([45, 52, 57, 61, 64], 33), "Em": ([40, 47, 55, 62, 64], 28), "F#m": ([42, 49, 57, 61, 66], 30), "Bbmaj7#11": ([46, 53, 57, 62, 64], 34),
    "Gm9": ([43, 50, 58, 57, 65], 31), "Ebmaj7": ([39, 46, 55, 62, 67], 27), "F": ([41, 48, 57, 60, 65], 29), "C": ([48, 55, 60, 64, 67], 36),
    "D/F#": ([42, 50, 57, 62, 66], 30), "G/D": ([50, 55, 59, 62, 67], 38), "Dbig": ([50, 57, 62, 66, 69, 74, 78], 26),
}


def pad(t, dur, chord, v=58, ch="strings", bass=True, octave=0):
    notes, b = CH_[chord]
    for p in notes:
        note(CH[ch], t, dur, p + octave, v + random.randint(-4, 4))
    if bass:
        note(CH["cello"], t, dur, notes[0], v - 6)
        note(CH["bass"], t, dur, b + 12 if b < 36 else b, v - 10)


def arp(t, dur, chord, step=SPB / 2, v=50, ch="harp", up=True, octave=12):
    notes, _ = CH_[chord]
    seq = sorted(set(notes))[1:]
    seq = seq + [p + 12 for p in seq[:2]]
    i = 0
    tt = t
    while tt < t + dur - 0.05:
        p = seq[i % len(seq)] + octave - 12
        note(CH[ch], tt, step * 1.8, p, v + random.randint(-6, 6))
        i += 1
        tt += step


def melody(t, notes, ch="flute", v=62):
    tt = t
    for p, d in notes:
        if p is not None:
            note(CH[ch], tt, d * SPB * 0.98, p, v + random.randint(-5, 3))
        tt += d * SPB


# ---------------- S1: forest wonder (0 - 30.1)
c = 6.67
for i, ch_ in enumerate(["D", "Bm", "G", "Asus", "D"]):
    t0 = 0.2 + i * c
    pad(t0, c + 0.2, ch_ if not (ch_ == "Asus" and False) else ch_, v=50 if i == 0 else 56)
    if i >= 1:
        arp(t0, c, ch_, v=44)
ramp(CH["strings"], 0, 4, 40, 100)
ramp(CH["cello"], 0, 4, 40, 100)
ramp(CH["bass"], 0, 4, 40, 100)
# flute motif from the flowers (9.6s)
melody(9.8, [(69, 1), (74, 1), (76, 1), (78, 3), (76, 1), (74, 1), (71, 2), (69, 2), (None, 1), (66, 1), (69, 1), (71, 1), (74, 4)])
# celesta twinkles for bee landing (~15s)
for k, p in enumerate([86, 90, 93, 98]):
    note(CH["celesta"], 14.6 + k * 0.18, 1.2, p, 48)
# pizzicato bird hops (16 - 22)
for k in range(14):
    note(CH["pizz"], 16.2 + k * 0.42, 0.3, [62, 66, 69, 74, 69, 66][k % 6], 50)
# seeds falling (22-30): harp descending glissando dots
for k in range(10):
    note(CH["harp"], 22.4 + k * 0.33, 1.5, [93, 90, 86, 83, 81, 78, 74, 71, 69, 66][k], 46)
# ---------------- S2: into the cell (30.1 - 51)
t = 30.1
for i, ch_ in enumerate(["Bbmaj7#11", "Gm9", "Ebmaj7", "F"]):
    pad(t + i * 4.3, 4.5, ch_, v=46, ch="choir", bass=True)
    pad(t + i * 4.3, 4.5, ch_, v=40, ch="pad", bass=False, octave=12)
    arp(t + i * 4.3, 4.3, ch_, step=SPB / 3, v=40, ch="celesta", octave=24)
# cobalt reveal: D major glow at ~47.5s
pad(47.4, 4.0, "D", v=56, ch="strings")
pad(47.4, 4.0, "D", v=44, ch="choir", bass=False, octave=12)
for k, p in enumerate([74, 78, 81, 86, 90]):
    note(CH["glock"], 47.4 + k * 0.22, 2.0, p, 52)
note(CH["revcym"], 45.0, 2.4, 60, 50)
# ---------------- S3: drupelets & roots (51 - 75)
t = 51.0
for i, ch_ in enumerate(["Bm", "G", "D", "A"]):
    pad(t + i * 6.0, 6.1, ch_, v=46)
    for k in range(int(6.0 / (SPB / 2))):
        notes, _ = CH_[ch_]
        p = sorted(notes)[1 + (k % 3)] + 12
        note(CH["marimba"] if i < 2 else CH["pizz"], t + i * 6.0 + k * SPB / 2, 0.25, p, 44 + (8 if k % 4 == 0 else 0))
# roots: low cellos glow (65 - 75)
for i, ch_ in enumerate(["Em", "Bm"]):
    pad(65.3 + i * 4.9, 5.0, ch_, v=50, ch="strings", octave=-12)
    pad(65.3 + i * 4.9, 5.0, ch_, v=38, ch="choir", bass=False)
for k in range(8):
    note(CH["celesta"], 66.5 + k * 1.05, 1.5, [81, 86, 88, 93, 86, 81, 88, 93][k], 38)
# ---------------- S4: cultivation and the two-year cycle (75 - 110)
t = 74.6
prog = ["G", "D/F#", "Em", "C", "G", "D", "Bm", "A"]
seg = 35.4 / len(prog)
for i, ch_ in enumerate(prog):
    pad(t + i * seg, seg + 0.1, ch_, v=50 + i * 2)
    notes, _ = CH_[ch_]
    k = 0
    tt = t + i * seg
    while tt < t + (i + 1) * seg - 0.05:
        p = sorted(notes)[2 + (k % 3)]
        note(CH["pizz"], tt, 0.2, p + 12, 46 + (10 if k % 4 == 0 else 0))
        k += 1
        tt += SPB / 2
    if i >= 2:
        note(CH["horn"], t + i * seg, seg * 0.95, sorted(notes)[2], 40 + i * 3)
        note(CH["horn"], t + i * seg, seg * 0.95, sorted(notes)[3], 38 + i * 3)
melody(86.0, [(67, 2), (69, 1), (71, 1), (74, 3), (72, 1), (71, 2), (69, 2), (67, 4)], ch="flute", v=54)
for k in range(6):
    note(CH["timp"], 104.0 + k * 0.6, 0.5, 38, 50 + k * 6)
# ---------------- S5: maturity & harvest (110 - 131)
t = 108.7
for i, ch_ in enumerate(["D", "G/D", "Bm", "G", "A"]):
    pad(t + i * 4.4, 4.5, ch_, v=50)
    arp(t + i * 4.4, 4.4, ch_, v=42)
melody(110.5, [(74, 2), (76, 1), (78, 1), (81, 3), (78, 1), (76, 2), (74, 2), (None, 1), (71, 1), (74, 1), (76, 1), (78, 2), (76, 2), (74, 4)], ch="oboe", v=56)
# ---------------- S6: finale (131 - 151)
t = 130.0
for i, ch_ in enumerate(["G", "A", "Bm", "G"]):
    pad(t + i * 4.0, 4.1, ch_, v=58 + i * 5)
    pad(t + i * 4.0, 4.1, ch_, v=46 + i * 4, ch="choir", bass=False)
    notes, _ = CH_[ch_]
    note(CH["horn"], t + i * 4.0, 3.9, sorted(notes)[2] + 12, 48 + i * 6)
    note(CH["horn"], t + i * 4.0, 3.9, sorted(notes)[3] + 12, 46 + i * 6)
    arp(t + i * 4.0, 4.0, ch_, v=46 + i * 3)
melody(131.0, [(74, 3), (76, 1), (78, 2), (81, 2), (83, 3), (81, 1), (78, 4)], ch="flute", v=60)
note(CH["revcym"], 143.2, 2.9, 60, 70)
for k in range(10):
    note(CH["timp"], 144.2 + k * 0.18, 0.3, 38, 40 + k * 5)
pad(146.0, 7.5, "Dbig", v=70)
pad(146.0, 7.5, "D", v=56, ch="choir", bass=False, octave=12)
note(CH["horn"], 146.0, 7.0, 62, 66); note(CH["horn"], 146.0, 7.0, 66, 62); note(CH["horn"], 146.0, 7.0, 69, 60)
note(CH["timp"], 146.0, 1.5, 38, 90)
for k, p in enumerate([86, 90, 93, 98, 102]):
    note(CH["glock"], 146.2 + k * 0.25, 3.0, p, 46)
for chn in list(CH.values()):
    ramp(chn, 149.0, 153.4, 100, 0)
for ch, evs in events.items():
    tr = mido.MidiTrack(); mid.tracks.append(tr)
    if ch == 0:
        tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
    evs.sort(key=lambda e: (e[0], 0 if e[1].type == 'note_off' else 1))
    last = 0
    for tk, msg in evs:
        tr.append(msg.copy(time=tk - last)); last = tk
os.makedirs(os.path.join(WORK, "audio"), exist_ok=True)
mid.save(os.path.join(WORK, "audio", "score.mid"))
print("saved", mid.length)
