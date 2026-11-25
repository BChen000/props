"""creature-sfx / demo.py: render every sound to out/<name>.wav (48 kHz stereo) and draw out/sheet.png.

  python demo.py                 all sounds, with the episode's settings (same gains and lengths as in the film)
  python demo.py roar fire_roar  only those
  python demo.py --sheet         also draw the waveform + spectrogram sheet (needs matplotlib)

Each file is normalised to a -1 dBFS peak so they can be auditioned side by side; the film's relative levels are in
style.json and ../two-dragons-episode/sfx.py.
"""
import os, sys
import numpy as np
import soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sfx_lib import *

OUT = os.path.join(HERE, "out")


def bed(fn, seconds=6.0, **kw):
    def make():
        rng = np.random.default_rng(11)
        n = int(seconds * SR)
        x = fn(rng, n, **kw)
        e = np.ones(n, np.float32); k = int(0.4 * SR)
        e[:k] = np.linspace(0, 1, k); e[-k:] = np.linspace(1, 0, k)
        return x * e[:, None]
    return make


def two_flaps():
    rng = np.random.default_rng(11)
    out = np.zeros((int(2.8 * SR), 2), np.float32)
    for k in range(3):                                   # 28-frame wingbeat at 24 fps = 1.167 s apart
        a = int(k * 28 / 24.0 * SR)
        f = flap(rng, 0.8)
        out[a:a + len(f)] += f[:len(out) - a]
    return out


SOUNDS = {
    "wind": bed(wind_bed),
    "volcano": bed(volcano_bed),
    "river": bed(river_bed),
    "rain": bed(rain_bed),
    "gust": bed(gust_bed),
    "thunder": lambda: thunder(np.random.default_rng(11), seed=48),
    "thunder_distant": lambda: thunder(np.random.default_rng(11), 3.5, crack=False, seed=9),
    "whoosh": lambda: whoosh(np.random.default_rng(11), 2.4, 120, 1200, 0.45),
    "flaps": two_flaps,
    "growl": lambda: growl(3.2, 46, 1, 0.8),
    "roar": lambda: roar(2.1, 92, 3, 0.34),
    "fire_roar": lambda: fire_roar(np.random.default_rng(11), 5.9, 1, 0.34),
    "fire_ignite": lambda: fire_roar(np.random.default_rng(11), 1.3, 2, 0.35, attack=0.5),
}


def sheet(names):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(names), 2, figsize=(7.2, 12.8), dpi=100, gridspec_kw={"width_ratios": [1, 1.4]})
    fig.patch.set_facecolor("#16181d")
    for ax_row, nm in zip(axes, names):
        x, _ = sf.read(os.path.join(OUT, nm + ".wav"), dtype="float32")
        m = x.mean(axis=1); t = np.arange(len(m)) / SR
        a, b = ax_row
        a.plot(t, m, lw=0.4, color="#e8b15a"); a.set_xlim(0, t[-1]); a.set_ylim(-1, 1)
        b.specgram(m, NFFT=1024, Fs=SR, noverlap=768, cmap="magma", vmin=-140, vmax=-30)
        b.set_ylim(0, 8000)
        a.set_ylabel(nm, color="#ddd", fontsize=8, rotation=0, ha="right", va="center")
        for ax in (a, b):
            ax.set_facecolor("#16181d"); ax.tick_params(colors="#888", labelsize=6)
            for sp in ax.spines.values():
                sp.set_color("#444")
        a.set_yticks([]); b.set_yticks([])
    axes[0][0].set_title("waveform (s)", color="#ccc", fontsize=8); axes[0][1].set_title("spectrogram, 0-8 kHz", color="#ccc", fontsize=8)
    fig.subplots_adjust(left=0.2, right=0.98, top=0.97, bottom=0.03, hspace=0.35, wspace=0.08)
    fig.savefig(os.path.join(OUT, "sheet.png"), facecolor=fig.get_facecolor())
    print("wrote", os.path.join(OUT, "sheet.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = args or list(SOUNDS)
    for nm in names:
        x = np.asarray(SOUNDS[nm](), np.float32)
        x *= 10 ** (-1 / 20) / max(np.abs(x).max(), 1e-9)
        sf.write(os.path.join(OUT, nm + ".wav"), x, SR)
        print("wrote", os.path.join(OUT, nm + ".wav"), "%.2f s" % (len(x) / SR))
    if "--sheet" in sys.argv:
        sheet(names)
