"""Assembles a Wildlore episode with ffmpeg: concatenates the shot renders in timeline order (crossfades where SEGS
asks), upscales any 720p shot with lanczos + light unsharp, pads short ones by holding the last frame, then adds a
vignette, fine grain, a 0.25 s fade in, the title card (Cinzel "THE  BLUE  RASPBERRY" at 64.5 % height with the
italic species name under it, 0.35-3.8 s), top-left chapter captions, a fade to black and a 2.5 s WILDLORE end card.
Audio is two-pass loudness-normalised to -14 LUFS / -1.5 dBTP. x264 CRF 18, capped at 16 Mb/s.

  python assemble.py                 -> $WILDLORE_WORK/final/episode.mp4
  python assemble.py out.mp4 --dry   -> only writes audio/filter.txt (check the graph without encoding)
  PRESET=veryfast python assemble.py -> quick check encode
"""
import subprocess, sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "wildlore-title"))
from timeline import SEGS, S, FPS, TOTAL, WORK
from wildlore_title import find_font

OUT = os.path.join(WORK, "out")
DRY = "--dry" in sys.argv
args = [a for a in sys.argv[1:] if a != "--dry"]
FINAL = args[0] if args else os.path.join(WORK, "final", "episode.mp4")
AUDIO = os.path.join(WORK, "audio", "mix.wav")
FONT_T = find_font(["Cinzel[wght].ttf", "Cinzel.ttf"])                         # drawtext uses the default instance, weight 400
FONT_I = find_font(["CormorantGaramond-Italic-560.ttf", "CormorantGaramond-MediumItalic-static.ttf"])  # static weight 560
os.makedirs(os.path.dirname(FINAL), exist_ok=True)

PRESET = os.environ.get("PRESET", "slow")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,nb_frames", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    w, nf = r.stdout.strip().split(",")[:2]
    return int(w), int(nf)


inputs = []
fc = []
for i, (name, f, n, xf) in enumerate(SEGS):
    inputs += ["-i", f"{OUT}/{f}"]
    w, nf = probe(f"{OUT}/{f}")
    up = "" if w == 1080 else ",scale=1080:1920:flags=lanczos,unsharp=5:5:0.45:5:5:0.0"
    pad = f"tpad=stop_mode=clone:stop={n - nf}," if nf < n else ""
    print("SEG", name, f, w, nf, "native" if not up else "upscaled", f"PADDED {n - nf} frames" if pad else "")
    fc.append(f"[{i}:v]{pad}trim=end_frame={n},setpts=PTS-STARTPTS,fps={FPS},format=yuv420p{up},settb=1/{FPS}[s{i}]")
cur = "s0"
length = SEGS[0][2]
for i, (name, f, n, xf) in enumerate(SEGS[1:], start=1):
    nxt = f"c{i}"
    if xf > 0:
        off = (length - xf) / FPS
        fc.append(f"[{cur}][s{i}]xfade=transition=fade:duration={xf / FPS:.4f}:offset={off:.4f}[{nxt}]")
        length = length - xf + n
    else:
        fc.append(f"[{cur}][s{i}]concat=n=2:v=1:a=0,settb=1/{FPS}[{nxt}]")
        length = length + n
    cur = nxt
dur = length / FPS


def esc(t):
    return t.replace(":", "\\:").replace("'", "’")


def text(label, txt, font, size, y, t0, t1, fade=0.5, color="white", spacing=0, alpha_max=1.0, border=0, x="(w-text_w)/2", shadow=0.55):
    a = f"if(lt(t,{t0}),0,if(lt(t,{t0 + fade}),(t-{t0})/{fade},if(lt(t,{t1 - fade}),1,if(lt(t,{t1}),({t1}-t)/{fade},0))))*{alpha_max}"
    return (f"drawtext=fontfile={font}:text='{esc(txt)}':fontsize={size}:fontcolor={color}:x={x}:y={y}:"
            f"alpha='{a}':shadowcolor=black@{shadow}:shadowx=0:shadowy=2" + (f":borderw={border}:bordercolor=black@0.3" if border else ""))


# grade + upscale + texture
END_PAD = 1.25  # black tail so the WILDLORE card stays up for ~2.5 s
pic_end = dur
dur = dur + END_PAD
post = [f"[{cur}]tpad=stop_mode=add:stop_duration={END_PAD}:color=black", "vignette=angle=0.55:mode=forward", "noise=alls=2:allf=t+u",
        f"fade=t=in:st=0:d=0.25",
        f"fade=t=out:st={pic_end - 2.6:.3f}:d=1.3"]
N0 = S["N"]
# title sits above the area that YouTube's Shorts overlay covers, and stays up across the first cut
post.append(text("title", "THE  BLUE  RASPBERRY", FONT_T, 66, "h*0.645", 0.35, 3.8, fade=0.45))
post.append(text("sci", "Rubus cyanocarpus", FONT_I, 60, "h*0.645+92", 0.7, 3.8, fade=0.45, color="0xDCE4FF"))
# growth-cycle captions top-left, clear of the plant in the middle of the frame
post.append(text("yr1", "YEAR ONE", FONT_T, 50, "h*0.11", N0 + 3.5, N0 + 6.9, fade=0.35, alpha_max=0.95, x="w*0.075", shadow=0.75, border=1))
post.append(text("yr2", "YEAR TWO", FONT_T, 50, "h*0.11", N0 + 7.2, N0 + 13.8, fade=0.35, alpha_max=0.95, x="w*0.075", shadow=0.75, border=1))
post.append(text("end", "WILDLORE", FONT_T, 84, "(h-text_h)/2", pic_end - 1.25, dur + 5, fade=0.5, alpha_max=1.0))
fc.append(",".join(post) + "[vout]")
filt = ";".join(fc)
FILTER = os.path.join(WORK, "audio", "filter.txt")
os.makedirs(os.path.dirname(FILTER), exist_ok=True)
open(FILTER, "w").write(filt)
if DRY:
    print("DRY RUN: wrote", FILTER, "| picture", round(pic_end, 3), "s + end pad", END_PAD); sys.exit(0)
# two-pass loudness normalisation of the mix
p1 = subprocess.run(["ffmpeg", "-hide_banner", "-i", AUDIO, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
js = json.loads(p1[p1.rindex("{"):p1.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
      f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
tmp = FINAL.replace(".mp4", "_tmp.mp4")
cmd = ["ffmpeg", "-hide_banner", "-y"] + inputs + ["-i", AUDIO, "-filter_complex_script", FILTER,
       "-map", "[vout]", "-map", f"{len(SEGS)}:a", "-af", ln + f",afade=t=out:st={dur - 2.0:.3f}:d=2.0,aresample=48000",
       "-c:v", "libx264", "-preset", PRESET, "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart",
       "-c:a", "aac", "-b:a", "256k", "-t", f"{dur:.3f}", tmp]
print("DURATION", dur)
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-3000:]); sys.exit(1)
os.replace(tmp, FINAL)
print("WROTE", FINAL)
