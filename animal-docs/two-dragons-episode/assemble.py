"""two-dragons-episode / assemble.py: join the shots and add the mix.

  python assemble.py           -> $WORK/The_Two_Dragons.mp4 (stream copy of the shots + AAC 256k) and
                                  $WORK/The_Two_Dragons_upload.mp4 (x264 medium CRF 19, max 16 Mb/s, faststart)
  python assemble.py --master  only the master

The shots are concatenated without re-encoding, so a changed shot only needs its own file re-rendered.
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shots2d import CUTS, OUTD, WORK

lst = os.path.join(WORK, "concat.txt")
with open(lst, "w") as f:
    for name, _ in CUTS:
        p = os.path.join(OUTD, name + ".mp4")
        assert os.path.exists(p), p
        f.write("file '%s'\n" % p)
vid = os.path.join(WORK, "video_only.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid], check=True)
final = os.path.join(WORK, "The_Two_Dragons.mp4")
tmp = final.replace(".mp4", ".tmp.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", os.path.join(WORK, "audio", "final_audio.wav"), "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", tmp], check=True)
os.replace(tmp, final)
print("wrote", final)
if "--master" not in sys.argv:
    up = os.path.join(WORK, "The_Two_Dragons_upload.mp4")
    tmp = up.replace(".mp4", ".tmp.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", final, "-map", "0:v", "-map", "0:a", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "19", "-maxrate", "16M", "-bufsize", "32M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", tmp],
                   check=True)
    os.replace(tmp, up)
    print("wrote", up)
