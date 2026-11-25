"""Shared steps of the marble music templates: split the render over worker processes, join the parts, and mux the
soundtrack at a fixed loudness.

    parts = run_workers([sys.executable, __file__, song], n_frames, workers, outdir, costs=None)
        runs `<cmd> --worker F0 F1 outdir/partN.mp4` per worker (the template renders frames [F0, F1) there).
        With per-frame cost estimates the cuts give each worker about the same work; without them (or with
        SPLIT=even) the frames are split evenly, which is how the shipped videos were cut.
    mux(parts, wav, out_mp4)
        concat (stream copy) + AAC 192k, gain set so the music measures LOUDNESS LUFS integrated
"""
import os
import subprocess
import sys

# ===================================================================== SETTINGS (shipped values)
LOUDNESS = -13.0        # LUFS, integrated (every shipped video measures -13.0)
AUDIO_BITRATE = "192k"
PEAK_CEILING = -0.5     # dBFS; a limiter is added only if the gain would push the peak above this
# ================================================================= END SETTINGS


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def frame_costs(pos, vis, base=1.4):
    """Rough render cost per frame: `base` + 1 per visible marble (fitted to the timing logs of all four videos;
    resting marbles cost about as much as moving ones, because their shadows and AO are redrawn every frame)."""
    import numpy as np
    return base + np.asarray(vis).sum(1)


def run_workers(cmd, n_frames, workers, outdir, costs=None):
    if costs is None or os.environ.get("SPLIT", "balanced") == "even":
        cuts = [round(n_frames * i / workers) for i in range(workers + 1)]
    else:
        import numpy as np
        cum = np.concatenate([[0.0], np.cumsum(costs)])
        cuts = [0] + [int(np.searchsorted(cum, cum[-1] * i / workers)) for i in range(1, workers)] + [n_frames]
    parts = [os.path.join(outdir, f"part{i + 1}.mp4") for i in range(workers)]
    log(f"rendering {n_frames} frames in {workers} workers...")
    procs = [subprocess.Popen([*cmd, "--worker", str(cuts[i]), str(cuts[i + 1]), parts[i]]) for i in range(workers)]
    if any(p.wait() for p in procs):
        sys.exit("a render worker failed")
    return parts


def loudness(wav):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", wav, "-af", "ebur128=peak=true", "-f", "null",
                          "-"], capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    return float(summary.split("I:")[1].split("LUFS")[0]), float(summary.split("Peak:")[1].split("dBFS")[0])


def mux(parts, wav, out):
    lst = out[:-4] + "_parts.txt"
    with open(lst, "w") as fh:
        fh.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    integ, peak = loudness(wav)
    gain = LOUDNESS - integ
    af = f"volume={gain:.2f}dB"
    if peak + gain > PEAK_CEILING:
        af += f",alimiter=limit={10 ** (PEAK_CEILING / 20):.3f}:level=false"
    tmp = out[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v",
                    "-map", "1:a", "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-movflags",
                    "+faststart", tmp], check=True)
    os.replace(tmp, out)
    os.remove(lst)
    log(f"music {integ:.1f} LUFS -> {LOUDNESS:.0f} LUFS ({gain:+.2f} dB)")
