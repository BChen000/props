"""Render the whole Ring Escape Short into out/ring_escape.mp4.

1. Frames in CHUNKS chunks, 2 at a time (render.py range), each an H.264 file
2. Concat with -c copy
3. Soundtrack (audio.py), then battle_audio.loudnorm_filter(): two-pass loudnorm to -14 LUFS / -1 dBTP
4. Mux with -c:v copy, AAC 192k

  python build.py          (about 1 min on 2 CPU cores)
Do not commit out/.
"""
import os
import subprocess
import sys

import settings as S
from timeline import Race

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "..", "battle-audio"))
import battle_audio as ba  # noqa: E402


def sh(cmd):
    subprocess.run(cmd, check=True)


def main():
    out = S.OUT_DIR
    os.makedirs(out, exist_ok=True)
    n = Race().n_frames
    k = S.CHUNKS
    bounds = [round(n * i / k) for i in range(k + 1)]
    segs = [os.path.join(out, f"seg{i}.mp4") for i in range(k)]
    print("frames:", n)
    for i in range(0, k, 2):
        procs = [subprocess.Popen([sys.executable, os.path.join(HERE, "render.py"), "range",
                                   str(bounds[j]), str(bounds[j + 1]), segs[j]]) for j in range(i, min(i + 2, k))]
        for p in procs:
            if p.wait() != 0:
                raise SystemExit("render failed")
    lst = os.path.join(out, "segs.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.basename(s)}'\n" for s in segs)
    video = os.path.join(out, "video_only.mp4")
    sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])
    wav = os.path.join(out, "audio.wav")
    sh([sys.executable, os.path.join(HERE, "audio.py"), wav])
    L = S.LOUDNESS
    af = ba.loudnorm_filter(wav, I=L["I"], TP=L["TP"], LRA=L["LRA"])
    final = os.path.join(out, S.OUT_NAME)
    tmp = final[:-4] + ".part.mp4"
    sh(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", tmp])
    os.replace(tmp, final)
    print("wrote", os.path.relpath(final, HERE))


if __name__ == "__main__":
    main()
