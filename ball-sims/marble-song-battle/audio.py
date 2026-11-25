"""Soundtrack synthesized from build/plan.json: every marble hit plays its melody note, plus per-song backing.

Melody: piano-ish additive voice with a glockenspiel sparkle an octave up (celesta for 'pizz').
Backing styles (from music.py): trap (808 bass, pad, hats, clap), pop (kick/snare, plucked bass,
e-piano stabs, sleigh bells), pizz (pizzicato bass and chords), dark (kick/clap, pad, hats),
waltz (oom-pah-pah with sleigh bells). Rolling noise on the rails, a send reverb, soft clip.
The tail past the loop point is wrapped onto the start, so the audio loops with the video.
Output: build/audio.wav (44.1 kHz stereo, about -14 dBFS RMS).
"""
import json
import math
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
rng = np.random.default_rng(11)
import settings
import music

D = json.load(open(settings.PLAN_JSON))
OUT = settings.AUDIO
T = D['T']
TAIL = 4.0
NS = int((T + TAIL) * SR)
dry = np.zeros((NS, 2))
send = np.zeros((NS, 2))


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def add(sig, t, pan=0.0, gain=1.0, rev=0.0):
    i0 = int(round(t * SR))
    if i0 >= NS:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    n = min(len(sig), NS - i0)
    l = math.cos((pan + 1) * math.pi / 4) * gain
    r = math.sin((pan + 1) * math.pi / 4) * gain
    dry[i0:i0 + n, 0] += sig[:n] * l
    dry[i0:i0 + n, 1] += sig[:n] * r
    if rev > 0:
        send[i0:i0 + n, 0] += sig[:n] * l * rev
        send[i0:i0 + n, 1] += sig[:n] * r * rev


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return sosfilt(sos, x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, btype='high', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, btype='low', fs=SR, output='sos'), x)


def piano(m, dur, vel=1.0, ring=0.35):
    f0 = hz(m)
    total = min(dur + 1.6, 3.2)
    t = np.arange(int(total * SR)) / SR
    tau0 = 1.5 * (440.0 / f0) ** 0.45
    B = 0.00035
    y = np.zeros_like(t)
    for n in range(1, 9):
        fn = n * f0 * math.sqrt(1 + B * n * n)
        if fn > 16000:
            break
        a = 1.0 / n ** 1.25
        tau = tau0 / (1 + 0.55 * (n - 1))
        y += a * np.exp(-t / tau) * np.sin(2 * math.pi * fn * t + rng.uniform(0, 6.28))
    for ratio, a, tau in ((1.0, 0.55, 1.4), (2.76, 0.22, 0.45), (5.40, 0.10, 0.18), (8.93, 0.04, 0.08)):
        fb = f0 * 2 * ratio
        if fb < 16000:
            y += a * np.exp(-t / (tau * (660.0 / f0) ** 0.3)) * np.sin(2 * math.pi * fb * t)
    att = np.minimum(1.0, t / 0.003)
    rel = np.where(t > dur + ring, np.exp(-(t - dur - ring) / 0.18), 1.0)
    click = rng.standard_normal(len(t)) * np.exp(-t / 0.004) * 0.25
    y = (y * att * rel + hp(click, 2000)) * vel
    return y / 2.2


def celesta(m, dur, vel=1.0):
    f0 = hz(m)
    total = min(dur + 1.4, 2.8)
    t = np.arange(int(total * SR)) / SR
    y = np.zeros_like(t)
    for ratio, a, tau in ((1.0, 1.0, 1.1), (2.0, 0.18, 0.4), (4.0, 0.22, 0.22), (6.9, 0.06, 0.08)):
        y += a * np.exp(-t / tau) * np.sin(2 * math.pi * f0 * ratio * t)
    att = np.minimum(1.0, t / 0.002)
    rel = np.where(t > dur + 0.5, np.exp(-(t - dur - 0.5) / 0.25), 1.0)
    return y * att * rel * vel / 1.6


def bass808(m, dur, vel=1.0):
    f0 = hz(m)
    t = np.arange(int((dur + 0.4) * SR)) / SR
    f = f0 * (1 + 0.6 * np.exp(-t / 0.025))
    ph = 2 * math.pi * np.cumsum(f) / SR
    env = np.minimum(1, t / 0.004) * np.exp(-t / max(0.5, dur * 0.8))
    env *= np.where(t > dur, np.exp(-(t - dur) / 0.08), 1.0)
    y = np.tanh(1.8 * np.sin(ph)) * env
    return y * vel * 0.8


def pluck_bass(m, dur, vel=1.0):
    f0 = hz(m)
    t = np.arange(int(min(dur + 0.3, 1.6) * SR)) / SR
    y = np.zeros_like(t)
    for n, a in ((1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12)):
        y += a * np.exp(-t / (0.5 / n)) * np.sin(2 * math.pi * f0 * n * t)
    y *= np.minimum(1, t / 0.006) * np.where(t > dur, np.exp(-(t - dur) / 0.06), 1.0)
    return y * vel * 0.7


def pizz(m, vel=1.0):
    f0 = hz(m)
    t = np.arange(int(0.7 * SR)) / SR
    y = np.zeros_like(t)
    for n in range(1, 7):
        y += (1.0 / n) * np.exp(-t / (0.32 / n ** 0.7)) * np.sin(2 * math.pi * f0 * n * t)
    y *= np.minimum(1, t / 0.003)
    return y * vel * 0.6


def epiano(m, dur, vel=1.0):
    f0 = hz(m)
    t = np.arange(int(min(dur + 0.5, 2.0) * SR)) / SR
    y = np.sin(2 * math.pi * f0 * t + 0.8 * np.exp(-t / 0.3) * np.sin(2 * math.pi * f0 * 2 * t))
    y += 0.25 * np.sin(2 * math.pi * f0 * 2 * t) * np.exp(-t / 0.3)
    y *= np.exp(-t / 0.7) * np.minimum(1, t / 0.004) * np.where(t > dur, np.exp(-(t - dur) / 0.1), 1.0)
    return y * vel * 0.5


def pad(ms, dur, vel=1.0):
    t = np.arange(int((dur + 0.6) * SR)) / SR
    y = np.zeros_like(t)
    for m in ms:
        f0 = hz(m)
        for det in (-0.12, 0.0, 0.11):
            f = f0 * 2 ** (det / 12)
            ph = (f * t + rng.uniform(0, 1)) % 1.0
            y += (2 * ph - 1)
    y = lp(y, 1100)
    env = np.minimum(1, t / 0.18) * np.where(t > dur, np.exp(-(t - dur) / 0.25), 1.0)
    return y * env * vel * 0.06


def kick(vel=1.0):
    t = np.arange(int(0.45 * SR)) / SR
    f = 46 + 110 * np.exp(-t / 0.035)
    ph = 2 * math.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.2) + 0.3 * hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.003)
    return np.tanh(1.5 * y) * vel * 0.9


def snare(vel=1.0):
    t = np.arange(int(0.3 * SR)) / SR
    n = bp(rng.standard_normal(len(t)), 1200, 7000) * np.exp(-t / 0.08)
    tone = np.sin(2 * math.pi * 190 * t) * np.exp(-t / 0.05)
    return (0.8 * n + 0.5 * tone) * vel * 0.55


def clap(vel=1.0):
    t = np.arange(int(0.35 * SR)) / SR
    env = np.zeros_like(t)
    for d in (0.0, 0.011, 0.022):
        env += np.where(t >= d, np.exp(-(t - d) / 0.006), 0)
    env += np.where(t >= 0.03, 0.6 * np.exp(-(t - 0.03) / 0.09), 0)
    return bp(rng.standard_normal(len(t)), 900, 5000) * env * vel * 0.5


def hat(vel=1.0, open_=False):
    t = np.arange(int(0.2 * SR)) / SR
    y = hp(rng.standard_normal(len(t)), 7000) * np.exp(-t / (0.09 if open_ else 0.022))
    return y * vel * 0.28


def sleigh(vel=1.0):
    t = np.arange(int(0.25 * SR)) / SR
    y = np.zeros_like(t)
    for _ in range(9):
        d = rng.uniform(0, 0.05)
        f = rng.uniform(5200, 9800)
        y += np.where(t >= d, np.sin(2 * math.pi * f * (t - d)) * np.exp(-(t - d) / rng.uniform(0.03, 0.09)), 0) * rng.uniform(0.3, 1)
    y += 0.5 * hp(rng.standard_normal(len(t)), 6000) * np.exp(-t / 0.03)
    return y * vel * 0.12


def tick(vel=1.0):
    t = np.arange(int(0.08 * SR)) / SR
    y = np.sin(2 * math.pi * 1900 * t) * np.exp(-t / 0.012)
    return y * vel * 0.18


# ---------------- melody (marble hits) ----------------
rounds = {r['k']: r for r in D['rounds']}
for nt in D['notes']:
    r = rounds[nt['k']]
    style = music.SONGS[nt['k']]['style']
    vel = 0.95 if nt['hit'] else 0.55
    pan = max(-0.5, min(0.5, (nt['midi'] - 72) / 24.0))
    if style == 'pizz':
        add(celesta(nt['midi'], nt['dur'], vel), nt['t'], pan, 0.95, rev=0.45)
        add(piano(nt['midi'] - 12, nt['dur'], vel * 0.35), nt['t'], pan, 0.7, rev=0.3)
    else:
        add(piano(nt['midi'], nt['dur'], vel), nt['t'], pan, 1.0, rev=0.35)

# ---------------- accompaniment ----------------
for k, song in enumerate(music.SONGS):
    r = rounds[k]
    spb = r['spb']
    b0 = r['beat0_t']
    style = song['style']
    meter = song['meter']
    db = song['downbeat']
    chords = song['chords']
    end_beat = song['end_beat']

    def chord_at(b):
        cur = None
        for cb, cd, ms, bass in chords:
            if cb <= b + 1e-6:
                cur = (cb, cd, ms, bass)
        return cur

    for cb, cd, ms, bass in chords:
        t = b0 + cb * spb
        dur = cd * spb
        if style == 'trap':
            add(bass808(bass, dur * 0.98, 0.85), t, 0, 0.9)
            add(pad(ms, dur, 1.0), t, 0, 1.0, rev=0.5)
        elif style == 'dark':
            add(pad([m - 12 for m in ms], dur, 0.9), t, 0, 1.0, rev=0.5)
        elif style == 'pizz':
            pass
        else:
            add(pad(ms, dur, 0.55), t, 0, 1.0, rev=0.5)

    nb = int(math.ceil(end_beat))
    for b in range(db, nb):
        t = b0 + b * spb
        if t > T + 2:
            break
        ch = chord_at(b)
        if ch is None:
            continue
        cb, cd, ms, bass = ch
        last_bar = b >= nb - meter
        if style == 'trap':
            pos = (b - db) % 3
            if pos == 0:
                add(kick(0.9), t)
            if pos == 2:
                add(clap(0.6), t, 0.1, rev=0.3)
            for sub in (0, 0.5):
                add(hat(0.7 if sub == 0 else 0.45), t + sub * spb, 0.3)
            if (b - db) % 6 == 5:
                for sub in (0.5, 0.667, 0.833):
                    add(hat(0.35), t + sub * spb, 0.3)
        elif style in ('pop', 'dark'):
            pos = (b - db) % 4
            if pos in (0, 2):
                add(kick(0.85 if style == 'pop' else 0.95), t)
                add(pluck_bass(bass, spb * 1.8, 0.9), t, 0, 0.9)
            if pos in (1, 3):
                add(snare(0.55) if style == 'pop' else clap(0.65), t, -0.05, rev=0.25)
                if style == 'pop':
                    for m in ms:
                        add(epiano(m + 12, spb * 0.8, 0.35), t, 0.15, rev=0.4)
            if style == 'pop':
                add(sleigh(1.0 if pos in (1, 3) else 0.7), t, -0.35, rev=0.3)
                add(sleigh(0.45), t + 0.5 * spb, -0.35, rev=0.3)
            else:
                add(hat(0.6), t, 0.3)
                add(hat(0.4), t + 0.5 * spb, 0.3)
                if pos == 2:
                    add(kick(0.6), t + 0.75 * spb)
        elif style == 'pizz':
            if b % 4 == 0:
                pb = bass if (b // 4) % 2 == 0 else bass + 7
                add(pizz(pb, 0.9), t, -0.15, rev=0.35)
                add(tick(0.6), t, 0.2, rev=0.2)
            if b % 4 == 2:
                for m in ms[:3]:
                    add(pizz(m + 12, 0.35), t, 0.2, rev=0.4)
            if b % 8 == 4:
                add(sleigh(0.45), t, -0.3, rev=0.3)
        elif style == 'waltz':
            pos = (b - db) % 3
            if pos == 0:
                add(kick(0.6), t)
                add(pluck_bass(bass, spb * 0.95, 0.95), t, 0, 0.9)
            else:
                for m in ms:
                    add(epiano(m + 12, spb * 0.7, 0.32), t, 0.15, rev=0.4)
                add(sleigh(0.9), t, -0.35, rev=0.3)

# ---------------- rails (rolling) ----------------
for a, b in D['rail_times']:
    for off in (0.0, T):
        t0, t1 = a + off, b + off
        if t0 > T + TAIL:
            continue
        n = int((t1 - t0) * SR)
        if n <= 0:
            continue
        x = lp(rng.standard_normal(n), 380)
        tt = np.arange(n) / n
        env = np.minimum(1, tt / 0.15) * np.minimum(1, (1 - tt) / 0.15)
        wob = 1 + 0.25 * np.sin(2 * math.pi * 23 * np.arange(n) / SR)
        add(x * env * wob * 0.5, t0, 0, 0.9)
        land = bp(rng.standard_normal(int(0.06 * SR)), 1500, 6000) * np.exp(-np.arange(int(0.06 * SR)) / SR / 0.01)
        add(land * 0.35, t0, 0.1)

# ---------------- reverb & master ----------------
irn = int(1.9 * SR)
ti = np.arange(irn) / SR
ir = np.zeros((irn, 2))
for c in range(2):
    ir[:, c] = lp(rng.standard_normal(irn), 6000) * np.exp(-ti / 0.42)
    ir[:, c] /= np.sqrt((ir[:, c] ** 2).sum())
wet = np.zeros_like(send)
for c in range(2):
    wet[:, c] = fftconvolve(send[:, c], ir[:, c])[:NS]
mix = dry + 0.55 * wet
mix = hp(mix.T, 30).T
nT = int(round(T * SR))
tail = mix[nT:]
out = mix[:nT].copy()
out[:len(tail)] += tail
pk = np.abs(out).max()
rms = np.sqrt((out ** 2).mean())
gain = 0.2 / rms
out = np.tanh(out * gain * 1.1) / 1.1
out *= 0.89 / np.abs(out).max()
print('pre peak', pk, 'rms', rms, 'final rms dBFS', 20 * np.log10(np.sqrt((out ** 2).mean())))
import wave
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print('wrote', OUT, len(out) / SR)
