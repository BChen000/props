"""two-dragons-episode / music.py: the orchestral score, written as MIDI and rendered with FluidSynth (FluidR3_GM).

Eight sections cued to the edit: A intro (Dm), B the West (brass, timpani, low ostinato; the hit on the fire cut),
C the East (pentatonic koto/shakuhachi colours), D storm (taiko, string ostinato), E river (harp ostinato),
F contrasts, G shared ancestry, H finale (D major). 72 BPM as written; the cue times were written against the
first (sped-up) cut and W() maps every note into the final cut, shot by shot, so the score follows the re-pacing
without a rewrite. Anchors where a hit must land on a picture event: the fire cut (sh07b), the roar (u16b_n frame 29)
and the end title. Writes $WORK/audio/music.mid and music_raw.wav. SF2 sets the soundfont path.
"""
import mido, subprocess, math, random, os
random.seed(4)
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("TWO_DRAGONS_WORK") or os.path.join(HERE, "build")
SF2 = os.environ.get("SF2", "/usr/share/sounds/sf2/FluidR3_GM.sf2")
BPM = 72.0
SPB = 60.0 / BPM
TPB = 480
ev = []   # (t, ch, note, vel, dur)
cc = []   # (t, ch, ctrl, val)


def tick(s):
    return int(round(s / SPB * TPB))


def note(t, ch, n, v, d):
    ev.append((t, ch, n, max(1, min(127, int(v))), d))


def chord(t, ch, notes, v, d, spread=0.0):
    for k, n in enumerate(notes):
        note(t + spread * k, ch, n, v, d)


def expr(ch, t0, t1, v0, v1, steps=24):
    for k in range(steps + 1):
        t = t0 + (t1 - t0) * k / steps
        cc.append((t, ch, 11, int(v0 + (v1 - v0) * k / steps)))


PROG = {0: 48, 1: 42, 2: 60, 3: 61, 4: 46, 5: 47, 6: 107, 7: 77, 8: 73, 10: 116, 11: 52, 12: 119, 13: 49}
VOL = {0: 92, 1: 88, 2: 80, 3: 78, 4: 76, 5: 96, 6: 84, 7: 78, 8: 72, 10: 100, 11: 70, 12: 70, 13: 80}

Dm = [50, 57, 62, 65, 69]; Bb = [46, 53, 58, 62, 65]; F = [41, 48, 53, 57, 60, 65]; C = [48, 55, 60, 64, 67]
Gm = [43, 50, 55, 58, 62]; A = [45, 52, 57, 61, 64]; Dm7 = [50, 57, 60, 65, 69]; Fmaj7 = [41, 48, 52, 57, 60]
Dmaj = [50, 57, 62, 66, 69]; Am = [45, 52, 57, 60, 64]; Eb = [51, 58, 63, 67]

# ---------- A: 0-16 intro ----------
prog = [(0.0, Dm), (3.33, Bb), (6.67, F), (10.0, C), (13.33, Dm)]
for t, c in prog:
    chord(t + 0.05, 0, c, 62, 3.45)
expr(0, 0.0, 3.0, 40, 100)
for k in range(48):
    t = 0.2 + k * SPB / 2
    if t > 15.8:
        break
    base = [62, 65, 69, 74, 69, 65][k % 6] if t < 3.3 else ([58, 62, 65, 70, 65, 62][k % 6] if t < 6.7 else ([60, 65, 69, 72, 69, 65][k % 6] if t < 10 else ([60, 64, 67, 72, 67, 64][k % 6] if t < 13.3 else [62, 65, 69, 74, 69, 65][k % 6])))
    note(t, 4, base, 50 + 8 * math.sin(k), 0.9)
horn = [(4.2, 62, 1.6), (5.9, 69, 0.8), (6.7, 67, 0.8), (7.5, 65, 1.6), (9.2, 64, 0.8), (10.0, 62, 0.8), (10.8, 60, 1.6), (12.5, 62, 3.2)]
for t, n, d in horn:
    note(t, 2, n, 72, d)
expr(2, 4.0, 15.0, 70, 105)
note(11.75, 12, 72, 60, 0.1)

# ---------- B: 16-34 West ----------
west = [(16.0, Dm), (19.33, Gm), (22.67, Bb), (26.0, A), (29.0, A)]
for t, c in west:
    chord(t, 0, [x - 12 if x > 60 else x for x in c], 70, 3.3)
for k in range(int((34.0 - 16.0) / (SPB / 2))):
    t = 16.0 + k * SPB / 2
    n = [38, 38, 38, 41, 38, 38, 43, 41][k % 8]
    if t > 29.9:
        n = 33 if k % 2 == 0 else 45
    note(t, 1, n, 64 + 18 * (t - 16) / 14, SPB / 2 * 0.9)
expr(1, 16.0, 29.9, 70, 100)
brass = [(17.2, [50, 57, 62], 2.4), (20.5, [43, 50, 58], 2.4), (23.8, [46, 53, 58], 2.4), (26.4, [45, 52, 57, 61], 3.3)]
for t, c, d in brass:
    chord(t, 3, c, 70, d)
expr(3, 16.0, 29.8, 60, 95)
for k in range(64):
    t = 27.2 + k * 0.045
    if t >= 29.95:
        break
    note(t, 5, 38 if k % 2 else 45, 30 + 35 * (t - 27.2) / 2.8, 0.05)
note(29.85, 12, 60, 90, 0.3)
# hit at fire
chord(30.0, 3, [38, 45, 50, 57], 78, 3.5)
chord(30.0, 0, [38, 50, 57, 62, 65], 70, 3.8)
note(30.0, 5, 38, 92, 1.0); note(30.0, 13, 57, 62, 2.0)
for k in range(30):
    t = 30.6 + k * 0.11
    note(t, 5, 38, 48 - k, 0.08)
expr(0, 30.0, 34.5, 120, 60)
expr(3, 30.0, 34.5, 120, 40)

# ---------- C: 34-53.3 East ----------
penta = [62, 65, 67, 69, 72, 69, 67, 65]
for k in range(int((53.3 - 34.3) / (SPB / 2))):
    t = 34.3 + k * SPB / 2
    n = penta[k % 8] + (12 if (k // 16) % 2 == 1 and k % 8 in (3, 4) else 0)
    note(t, 6, n, 58 + 10 * math.sin(k * 0.7), SPB * 0.8)
eastp = [(34.3, Dm7), (37.6, Fmaj7), (41.0, [43, 50, 57, 62, 65]), (44.3, Dm7), (47.6, [48, 55, 62, 65, 69]), (50.9, Dm7)]
for t, c in eastp:
    chord(t, 0, c, 55, 3.4)
expr(0, 34.3, 36.0, 50, 85)
shaku = [(40.2, 69, 2.4), (42.7, 67, 0.8), (43.5, 65, 1.6), (45.2, 62, 2.4), (48.0, 72, 1.6), (49.7, 69, 0.8), (50.5, 67, 2.4)]
for t, n, d in shaku:
    note(t, 7, n, 70, d)

# ---------- D: 53.3-61.1 storm ----------
for t, c in [(53.3, [38, 50, 57, 63]), (56.6, [36, 48, 55, 63]), (59.0, [38, 50, 57, 62])]:
    chord(t, 0, c, 72, 3.2)
for k in range(int((61.0 - 53.3) / (SPB / 4))):
    t = 53.3 + k * SPB / 4
    note(t, 1, 38 if (k // 8) % 2 == 0 else 39, 60 + 20 * ((k % 4) == 0), SPB / 4 * 0.9)
for bar in range(3):
    b0 = 53.3 + bar * 4 * SPB * 0.6
    for off, v in [(0, 110), (0.5, 70), (1.5, 90), (2.0, 110), (2.75, 80), (3.0, 100), (3.5, 85)]:
        t = b0 + off * SPB * 0.6
        if t < 61.0:
            note(t, 10, 50, v, 0.4)
expr(0, 53.3, 61.0, 90, 60)

# ---------- E: 61.1-70.6 river ----------
for k in range(int((70.5 - 61.2) / (SPB / 2))):
    t = 61.2 + k * SPB / 2
    note(t, 6, [62, 67, 69, 72, 74, 72, 69, 67][k % 8], 52, SPB * 0.7)
for t, c in [(61.2, Dm7), (64.5, [43, 50, 57, 62, 65]), (67.8, Fmaj7)]:
    chord(t, 0, c, 50, 3.3)
chord(63.5, 3, [50, 57, 62], 62, 1.6)
for k in range(10):
    note(65.6 + k * 0.06, 4, [62, 65, 67, 69, 72, 74, 77, 79, 81, 84][k], 60, 0.8)
note(67.0, 8, 74, 60, 2.0); note(69.0, 8, 72, 55, 1.5)

# ---------- F: 70.6-89.4 contrasts ----------
chord(70.7, 3, [38, 45, 50, 57], 85, 1.3); note(70.7, 5, 38, 100, 0.8)
for k in range(8):
    note(72.15 + k * 0.19, 6, penta[k], 62, 0.6)
for t, c in [(73.75, Dm), (77.0, Gm)]:
    chord(t, 0, [x - 12 if x > 60 else x for x in c], 75, 3.2)
for k in range(int((80.6 - 73.75) / (SPB / 2))):
    t = 73.75 + k * SPB / 2
    note(t, 1, [38, 38, 41, 38, 43, 41, 38, 36][k % 8], 72, SPB / 2 * 0.9)
for t, n, d in [(74.0, 62, 1.6), (75.7, 69, 1.6), (77.4, 67, 0.8), (78.2, 70, 2.4)]:
    note(t, 2, n, 85, d)
chord(78.2, 3, [43, 50, 55, 58, 62], 80, 2.4); note(78.2, 5, 43, 95, 0.6); note(78.2, 13, 57, 60, 2.0)
for k in range(int((89.3 - 80.8) / (SPB / 2))):
    t = 80.8 + k * SPB / 2
    note(t, 6, penta[k % 8], 56, SPB * 0.8)
for t, c in [(80.8, Dm7), (84.1, Fmaj7), (87.4, Dm7)]:
    chord(t, 0, c, 52, 3.3)
for t, n, d in [(81.5, 69, 2.4), (84.0, 72, 1.6), (85.7, 69, 0.8), (86.5, 67, 2.4)]:
    note(t, 8, n, 66, d)

# ---------- G: 89.4-112.1 shared ----------
shared = [(89.4, Dm), (92.7, Bb), (96.0, F), (99.3, C), (100.6, Dm), (103.9, Bb), (107.2, [41, 48, 53, 57, 60]), (109.0, C)]
for t, c in shared:
    chord(t, 0, c, 62, 3.4 if t != 99.3 else 1.3)
expr(0, 89.4, 112.0, 70, 110)
for t, n, d in [(90.0, 62, 1.6), (91.7, 69, 0.8), (92.5, 67, 0.8), (93.3, 65, 1.6), (95.0, 64, 0.8), (95.8, 62, 2.4)]:
    note(t, 2, n, 72, d)
for t, n, d in [(96.5, 69, 1.6), (98.2, 72, 0.8), (99.0, 69, 0.8), (99.8, 67, 2.4)]:
    note(t, 8, n, 66, d)
chord(100.6, 11, [62, 65, 69], 50, 8.0)
chord(105.2, 3, [38, 45, 50, 57, 62], 92, 1.6); note(105.2, 5, 38, 105, 0.6)
for k in range(12):
    note(106.85 + k * 0.05, 4, [62, 65, 67, 69, 72, 74, 77, 79, 81, 84, 86, 89][k], 62, 1.0)
note(107.0, 7, 74, 70, 1.8)
for t, n, d in [(109.2, 62, 0.8), (110.0, 65, 0.8), (110.8, 69, 1.4)]:
    note(t, 2, n, 80, d)
    note(t, 8, n + 12, 60, d)

# ---------- H: 112.1-120 finale ----------
for t, c in [(112.1, Bb), (114.0, C), (115.9, [45, 52, 57, 61, 64])]:
    chord(t, 0, c, 80, 1.95)
    chord(t, 3, c[:3], 70, 1.9)
chord(117.6, 0, [38, 50, 57, 62, 66, 69, 74], 92, 2.4)
chord(117.6, 3, [38, 50, 57, 62, 66], 80, 2.3)
chord(117.6, 11, [62, 66, 69], 60, 2.3)
note(117.6, 2, 74, 85, 2.3); note(117.6, 5, 38, 90, 1.0)
for t, n, d in [(112.4, 69, 1.6), (114.1, 72, 1.6), (115.8, 74, 1.6)]:
    note(t, 2, n, 82, d)
expr(0, 117.6, 120.0, 110, 30); expr(3, 117.6, 120.0, 100, 20); expr(11, 117.6, 120.0, 90, 20); expr(2, 117.6, 120.0, 100, 30)

# ---------- warp to the normal-speed edit ----------
import numpy as np
_A = [(0.0, 0.0), (282, 404), (384, 557), (720, 1042), (816, 1188), (1279, 1849), (1466, 2125),
      (1694, 2452), (1730, 2508), (1769, 2555), (78.2 * 24, 2713), (1936, 2798), (2146, 3060), (2414, 3462), (2524, 3618),
      (2563, 3675), (2616, 3753), (2690, 3865), (117.6 * 24, 170.6 * 24), (2880, 4153)]
_XO = np.array([a for a, b in _A]) / 24.0
_XN = np.array([b for a, b in _A]) / 24.0


def W(t):
    return float(np.interp(t, _XO, _XN))


ev = [(W(t), ch, n, v, W(t + d) - W(t)) for t, ch, n, v, d in ev]
cc = [(W(t), ch, c, v) for t, ch, c, v in cc]

# ---------- write ----------
mid = mido.MidiFile(ticks_per_beat=TPB)
tr = mido.MidiTrack(); mid.tracks.append(tr)
tr.append(mido.MetaMessage('set_tempo', tempo=int(SPB * 1e6), time=0))
msgs = []
for ch, p in PROG.items():
    if ch == 9:
        continue
    msgs.append((0, 0, mido.Message('program_change', channel=ch, program=p)))
    msgs.append((0, 0, mido.Message('control_change', channel=ch, control=7, value=VOL[ch])))
    msgs.append((0, 0, mido.Message('control_change', channel=ch, control=91, value=70)))
    msgs.append((0, 0, mido.Message('control_change', channel=ch, control=11, value=100)))
for t, ch, n, v, d in ev:
    msgs.append((tick(t), 1, mido.Message('note_on', channel=ch, note=n, velocity=v)))
    msgs.append((tick(t + d), 0, mido.Message('note_off', channel=ch, note=n, velocity=0)))
for t, ch, c, v in cc:
    msgs.append((tick(t), 0, mido.Message('control_change', channel=ch, control=c, value=max(0, min(127, v)))))
msgs.sort(key=lambda x: (x[0], x[1]))
last = 0
for tk, _, m in msgs:
    m.time = tk - last; last = tk
    tr.append(m)
AUD = os.path.join(WORK, "audio"); os.makedirs(AUD, exist_ok=True)
mid.save(os.path.join(AUD, "music.mid"))
if "--midi-only" not in __import__("sys").argv:
    subprocess.run(["fluidsynth", "-ni", "-g", "0.55", "-r", "48000", "-F", os.path.join(AUD, "music_raw.wav"),
                    SF2, os.path.join(AUD, "music.mid")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("music done", AUD)
