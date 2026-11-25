"""two-dragons-episode / mix.py: narration, score and effects into $WORK/audio/final_audio.wav (48 kHz, 24-bit).

Voice chain (ffmpeg): high-pass 70 Hz, +2 dB at 160 Hz, +1.5 dB at 3 kHz, gentle 2.5:1 compression. Stems are set to
-16 (voice), -25.5 (music) and -24 LUFS (effects); music ducks 50 % and effects 45 % under speech (80 ms attack,
450 ms release), with extra music ducks under the fire, the roar and the start of the storm. Then 0.25 s fade in,
1.6 s fade out, -14 LUFS integrated and a 5 ms look-ahead limiter to -1.5 dBFS (4x oversampled peaks).
Inputs: $WORK/vo/vo_raw.wav (narrate.py), $WORK/audio/music_raw.wav (music.py), $WORK/audio/sfx.wav (sfx.py).
"""
import os
import numpy as np, soundfile as sf, subprocess, pyloudnorm as pyln, scipy.signal as ss

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("TWO_DRAGONS_WORK") or os.path.join(HERE, "build")
SR = 48000
DUR = 4153 / 24.0
N = int(SR * DUR)
A = os.path.join(WORK, "audio") + os.sep

subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(WORK, "vo", "vo_raw.wav"), "-af",
                "highpass=f=70,equalizer=f=160:t=q:w=0.9:g=2.0,equalizer=f=3000:t=q:w=1.2:g=1.5,"
                "acompressor=threshold=0.12:ratio=2.5:attack=8:release=160:makeup=1.3",
                "-ar", str(SR), "-ac", "1", A + "vo_proc.wav"], check=True)


def load(p, ch=2):
    x, sr = sf.read(p, dtype="float32", always_2d=True)
    assert sr == SR, (p, sr)
    if x.shape[1] == 1 and ch == 2:
        x = np.repeat(x, 2, axis=1)
    if len(x) < N:
        x = np.vstack([x, np.zeros((N - len(x), x.shape[1]), np.float32)])
    return x[:N]


meter = pyln.Meter(SR)
vo = load(A + "vo_proc.wav")
mu = load(A + "music_raw.wav")
fx = load(A + "sfx.wav")


def to_lufs(x, target):
    l = meter.integrated_loudness(x)
    return x * 10 ** ((target - l) / 20), l


vo, l1 = to_lufs(vo, -16.0)
mu, l2 = to_lufs(mu, -25.5)
fx, l3 = to_lufs(fx, -24.0)
print("in loudness vo %.1f mu %.1f fx %.1f" % (l1, l2, l3))

# duck music + beds under voice
env = np.abs(vo[:, 0])
win = int(0.05 * SR)
rms = np.sqrt(np.convolve(env ** 2, np.ones(win) / win, mode="same"))
act = (rms > 10 ** (-38 / 20)).astype(np.float32)
sm = np.zeros_like(act); g = 0.0
att = 1 - np.exp(-1 / (0.08 * SR)); rel = 1 - np.exp(-1 / (0.45 * SR))
for i in range(0, N, 48):
    tgt = act[i]
    k = att if tgt > g else rel
    g += (tgt - g) * (1 - (1 - k) ** 48)
    sm[i:i + 48] = g
duck_mu = 1 - 0.5 * sm
duck_fx = 1 - 0.45 * sm
tt = np.arange(N) / SR
ROAR_T = (2684 + 31.2) / 24.0
S0, S1 = 1849 / 24.0 + 0.45, 1849 / 24.0 + 0.45 + 2.9
extra = 1 - 0.6 * np.clip((tt - (938 / 24.0 - 0.2)) / 0.4, 0, 1) * np.clip((1188 / 24.0 + 0.2 - tt) / 0.4, 0, 1)
extra *= 1 - 0.45 * np.clip((tt - (ROAR_T - 0.5)) / 0.3, 0, 1) * np.clip((ROAR_T + 2.5 - tt) / 0.3, 0, 1)
extra *= 1 - 0.5 * np.clip((tt - S0) / 0.3, 0, 1) * np.clip((S1 - tt) / 0.3, 0, 1)
duck_fx = duck_fx * (1 - 0.5 * np.clip((tt - S0) / 0.3, 0, 1) * np.clip((S1 - tt) / 0.3, 0, 1))
duck_mu = duck_mu * extra
mix = vo + mu * duck_mu[:, None] + fx * duck_fx[:, None]

fade_in = np.minimum(1, np.arange(N) / (0.25 * SR))
fade_out = np.clip((N - np.arange(N)) / (1.6 * SR), 0, 1)
mix *= (fade_in * fade_out)[:, None]

l = meter.integrated_loudness(mix)
mix *= 10 ** ((-14.0 - l) / 20)
# simple lookahead limiter to -1.5 dBFS sample peak (with 4x oversampled check)
ceil = 10 ** (-1.5 / 20)
up = ss.resample_poly(mix, 4, 1, axis=0)
peak = np.abs(up).reshape(-1, 4, 2).max(axis=(1, 2))
peak = peak[:N] if len(peak) >= N else np.pad(peak, (0, N - len(peak)))
need = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
la = int(0.005 * SR)
from scipy.ndimage import minimum_filter1d, uniform_filter1d
gl = minimum_filter1d(need, size=2 * la + 1)
gl = uniform_filter1d(gl, size=la)
gl = np.minimum(gl, need)
mix *= gl[:, None]
print("final lufs %.2f" % meter.integrated_loudness(mix), "peak %.2f dBFS" % (20 * np.log10(np.abs(mix).max())))
sf.write(A + "final_audio.wav", mix.astype(np.float32), SR, subtype="PCM_24")
