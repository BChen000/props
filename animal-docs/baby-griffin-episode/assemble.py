import sys, os, json, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ep_paths
import comp

OUT = ep_paths.OUT
os.makedirs(OUT, exist_ok=True)
SHOTS = [('s01', 209), ('s02', 51), ('s03', 110), ('s04', 140), ('s05', 102), ('s06', 154), ('s07a', 50), ('s08', 92), ('s07b', 127), ('s09', 85), ('s10', 140), ('s11', 147), ('s12', 106), ('s13', 85), ('s14', 149), ('s15', 121), ('s16', 139), ('s17', 87), ('s18', 266), ('s19', 165), ('s20', 199), ('s21', 79), ('s22', 123), ('s23', 71), ('s24', 111), ('s25', 154), ('s26', 95), ('s27', 56), ('s28', 114)]
NFR = dict(SHOTS)
P = {
    's01': dict(zoom=(1.0, 1.04)), 's02': dict(zoom=(1.02, 1.05)), 's03': dict(zoom=(1.0, 1.05)), 's04': dict(),
    's05': dict(zoom=(1.0, 1.03)), 's06': dict(bg_blur=2.0, zoom=(1.0, 1.06)), 's07': dict(bg_blur=6.0, zoom=(1.0, 1.04)),
    's08': dict(bg_blur=3.0, zoom=(1.0, 1.03)), 's09': dict(bg_blur=3.0), 's10': dict(), 's11': dict(bg_blur=5.0),
    's12': dict(bg_blur=5.0), 's13': dict(zoom=(1.0, 1.10)), 's14': dict(bg_blur=2.0), 's15': dict(bg_blur=2.0),
    's16': dict(bg_blur=1.0), 's17': dict(bg_blur=1.0), 's18': dict(), 's19': dict(bg_blur=8.0, zoom=(1.0, 1.05)),
    's20': dict(bg_blur=4.0), 's21': dict(zoom=(1.0, 1.04)), 's22': dict(), 's23': dict(), 's24': dict(), 's25': dict(),
    's26': dict(zoom=(1.0, 1.03)), 's27': dict(bg_blur=2.0, zoom=(1.02, 1.08)), 's28': dict(zoom=(1.0, 1.04), fade_out=30),
}


def last_frame_of(name):
    p = OUT + name + '.mp4'
    cmd = ['ffmpeg', '-loglevel', 'error', '-sseof', '-0.05', '-i', p, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(comp.OUT_H, comp.OUT_W, 3).astype(np.float32) / 255.0


def build(name):
    kw = dict(P.get(name, {}))
    n = NFR[name]
    if name in ('s07a', 's07b'):
        a = NFR['s07a']
        f0, f1 = (1, a) if name == 's07a' else (a + 1, a + NFR['s07b'])
        comp.compose_shot('s07', f0, f1, OUT + name + '.mp4', **dict(P['s07']))
        return
    if name == 's18' and os.path.exists(OUT + 's17.mp4'):
        lf = last_frame_of('s17')
        kw['prepend'] = [lf] * 14
        kw['prepend_dissolve'] = 14
    comp.compose_shot(name, 1, n, OUT + name + '.mp4', **kw)
    return


def concat(final=ep_paths.BUILD + 'griffin_final.mp4'):
    lst = OUT + 'list.txt'
    with open(lst, 'w') as fh:
        for n, _ in SHOTS:
            fh.write(f"file '{OUT}{n}.mp4'\n")
    tmpv = OUT + 'video_only.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', tmpv], check=True)
    tmp = final[:-4] + '.part.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmpv, '-i', ep_paths.AUDIO + 'final_mix.wav', '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, final)
    print('FINAL', final)


def upload(src=None, dst=None):
    """The file that was uploaded: BT.601 -> BT.709 matrix conversion with BT.709 tags (YouTube assumes 709 for HD;
    comp.py's ffmpeg pipe writes untagged BT.601), x264 slow CRF 23, AAC 256k straight from the WAV master."""
    src = src or ep_paths.BUILD + 'griffin_final.mp4'
    dst = dst or ep_paths.BUILD + 'Baby_Griffin_Wildlore.mp4'
    tmp = dst[:-4] + '.part.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', ep_paths.AUDIO + 'final_mix.wav', '-map', '0:v', '-map', '1:a',
                    '-vf', 'scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,format=yuv420p',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-profile:v', 'high', '-level', '4.2',
                    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
                    '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, dst)
    print('UPLOAD', dst)


if __name__ == '__main__':
    # python3 assemble.py s01 s07a ...   composite single shots (build/out/<shot>.mp4)
    # python3 assemble.py all            every shot in cut order (s17 before s18, whose dissolve needs s17), then concat
    # python3 assemble.py concat         join the shots + the mix -> build/griffin_final.mp4
    # python3 assemble.py upload         the BT.709 upload file -> build/Baby_Griffin_Wildlore.mp4
    for a in sys.argv[1:]:
        if a == 'concat':
            concat()
        elif a == 'upload':
            upload()
        elif a == 'all':
            for n, _ in SHOTS:
                build(n)
            concat()
        else:
            build(a)
