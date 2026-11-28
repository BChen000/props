"""lowpoly-gl: a small OpenGL 3.3 renderer (moderngl, headless EGL; llvmpipe on a CPU) for flat-shaded low-poly scenes.

Forward shading with up to 8 point/spot/directional lights, one soft (PCF) spot-light shadow map, hemisphere ambient,
textures (albedo or emissive), procedural modes (lit windows, cork), exponential fog, and an additive pass for light
beams, glows and dust. Colour is rendered to RGBA16F with 4x MSAA; alpha carries view depth for the post pass.
"""
import math
import numpy as np
import moderngl

MAXL = 8


# ------------------------------------------------------------------ matrices
def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2)
    m = np.zeros((4, 4), np.float32)
    m[0, 0] = f / aspect; m[1, 1] = f
    m[2, 2] = (far + near) / (near - far); m[2, 3] = 2 * far * near / (near - far); m[3, 2] = -1
    return m


def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = (np.asarray(a, np.float64) for a in (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f)
    if abs(np.dot(f, up / np.linalg.norm(up))) > 0.999:
        up = np.array([0, 1.0, 0])
    s = np.cross(f, up); s /= np.linalg.norm(s); u = np.cross(s, f)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m.astype(np.float32)


def T(t):
    m = np.eye(4); m[:3, 3] = t; return m


def R3(R):
    m = np.eye(4); m[:3, :3] = R; return m


def S(s):
    m = np.eye(4); m[0, 0], m[1, 1], m[2, 2] = np.broadcast_to(np.asarray(s, float), (3,)); return m


def euler(x=0.0, y=0.0, z=0.0):
    """Rotation matrix for XYZ Euler angles in radians (applied X, then Y, then Z)."""
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


# ------------------------------------------------------------------ shaders
VS = """
#version 330
uniform mat4 M; uniform mat4 VP; uniform mat3 NM; uniform vec4 uvx;
in vec3 in_pos; in vec3 in_nrm; in vec2 in_uv; in vec3 in_col;
out vec3 v_w; out vec3 v_n; out vec2 v_uv; out vec3 v_c; out vec3 v_l;
void main(){ vec4 w = M*vec4(in_pos,1.0); v_w=w.xyz; v_n=normalize(NM*in_nrm); v_uv=in_uv*uvx.zw+uvx.xy; v_c=in_col; v_l=in_pos;
 gl_Position = VP*w; }
"""

FS = """
#version 330
#define MAXL %d
uniform vec3 cam; uniform mat4 V;
uniform int nl; uniform vec4 Lp[MAXL]; uniform vec4 Lc[MAXL]; uniform vec4 Ld[MAXL]; uniform vec4 Lx[MAXL];
uniform sampler2DShadow shmap; uniform mat4 SVP; uniform float sh_soft; uniform int has_sh;
uniform vec3 amb_top; uniform vec3 amb_bot;
uniform sampler2D tex; uniform int tmode; uniform vec3 emit; uniform float temit; uniform float spec; uniform float shin;
uniform vec2 wsc; uniform vec3 wcol;
uniform vec3 tint; uniform int mode; uniform float seed; uniform float t; uniform float cellf; uniform float tt; uniform float rate;
uniform vec3 fog_col; uniform float fog_d; uniform float fog_h;
in vec3 v_w; in vec3 v_n; in vec2 v_uv; in vec3 v_c; in vec3 v_l;
out vec4 frag;
const vec2 PD[12] = vec2[](vec2(-0.326,-0.406),vec2(-0.840,-0.074),vec2(-0.696,0.457),vec2(-0.203,0.621),
 vec2(0.962,-0.195),vec2(0.473,-0.480),vec2(0.519,0.767),vec2(0.185,-0.893),vec2(0.507,0.064),vec2(0.896,0.412),
 vec2(-0.322,-0.933),vec2(-0.792,-0.598));
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
float shadow(vec3 w, vec3 n, vec3 l){
  vec4 p = SVP*vec4(w + n*0.004, 1.0); p.xyz /= p.w; p.xyz = p.xyz*0.5+0.5;
  if (p.x<0.0||p.x>1.0||p.y<0.0||p.y>1.0||p.z>1.0) return 1.0;
  float b = 0.0006 + 0.0015*(1.0-max(dot(n,l),0.0));
  float s = 0.0; vec2 ts = vec2(sh_soft/2048.0);
  float r = hash(gl_FragCoord.xy)*6.2831; mat2 rot = mat2(cos(r),-sin(r),sin(r),cos(r));
  for (int i=0;i<12;i++) s += texture(shmap, vec3(p.xy + rot*PD[i]*ts, p.z - b));
  return s/12.0;
}
void main(){
  vec3 N = normalize(v_n); if (!gl_FrontFacing) N = -N;
  vec3 Vv = normalize(cam - v_w);
  vec3 alb = v_c*tint; vec3 E = emit;
  if (tmode==1){ vec4 tx = texture(tex, v_uv); alb *= pow(tx.rgb, vec3(2.2)); }
  if (tmode==2){ vec4 tx = texture(tex, v_uv); E += pow(tx.rgb, vec3(2.2))*temit; alb *= 0.02; }
  if (tmode==3){ vec4 tx = texture(tex, v_uv); if (tx.a < 0.5) discard; alb *= pow(tx.rgb, vec3(2.2)); }
  if (mode==1){ // building windows from world position
    vec3 an = abs(N); vec2 q = an.x>an.y ? v_w.yz : v_w.xz; if (an.z>0.7) q = vec2(-1.0);
    vec2 cs = vec2(0.9,1.1)*wsc; vec2 cell = floor(q/cs); vec2 f = fract(q/cs);
    float win = step(0.18,f.x)*step(f.x,0.82)*step(0.22,f.y)*step(f.y,0.78)*step(0.0,q.y);
    float h = hash(cell + seed*vec2(13.1, 7.7) + floor(v_w.xy*0.01));
    float lit = step(0.88, h);
    alb = wcol.x >= 0.0 ? mix(alb, wcol, win) : mix(alb, alb*0.5, win);
    E += win*lit*vec3(1.0,0.62,0.28)*(1.2+1.5*hash(cell*1.7))*temit;
  }
  if (mode==3){ // phone-farm screen: in_col.r = atlas cell / 8, in_col.g = random phase
    float c0 = floor(v_c.r*8.0); float ph = v_c.g;
    float c = cellf >= 0.0 ? cellf : mod(c0 + floor(tt*rate + ph*8.0), 8.0);
    vec2 uv = vec2((clamp(v_uv.x,0.0,1.0) + c)/8.0, v_uv.y);
    float fl = 0.85 + 0.15*step(0.5, fract(sin(c0*91.7 + floor(tt*7.0 + ph*13.0))*437.5));
    E += pow(texture(tex, uv).rgb, vec3(2.2))*temit*fl; alb = vec3(0.01);
  }
  if (mode==4){ // glowing floor grid
    vec2 q = v_w.xy*2.0; vec2 gg = abs(fract(q - 0.5) - 0.5)/max(fwidth(q), vec2(1e-4));
    float line = 1.0 - min(min(gg.x, gg.y), 1.0);
    E += line*vec3(0.04, 0.20, 0.30)*seed;
  }
  if (mode==5){ // unlit vertex colour (sky dome, sun, signs that glow)
    E += v_c*temit; alb = vec3(0.0);
  }
  if (mode==2){ // cork
    float n1 = hash(floor(v_l.xz*420.0)); float n2 = hash(floor(v_l.xz*90.0)+3.1);
    alb *= 0.78 + 0.28*n1 + 0.12*n2;
  }
  vec3 col = alb*mix(amb_bot, amb_top, N.z*0.5+0.5) + E;
  for (int i=0;i<MAXL;i++){
    if (i>=nl) break;
    vec3 L; float att = 1.0;
    if (Lp[i].w > 1.5){ L = -Ld[i].xyz; }
    else {
      vec3 d = Lp[i].xyz - v_w; float dist = length(d); L = d/dist;
      float rr = dist/max(Lc[i].w,0.001); float win = clamp(1.0-rr*rr*rr*rr,0.0,1.0);
      att = win*win/(dist*dist+0.02);
      if (Lp[i].w > 0.5){ float cd = dot(-L, Ld[i].xyz); att *= smoothstep(Ld[i].w, Lx[i].x, cd); }
    }
    float ndl = dot(N,L);
    float wrap = Lx[i].w; float dif = max((ndl+wrap)/(1.0+wrap), 0.0);
    if (att*dif <= 0.0) continue;
    float sh = 1.0; if (has_sh==1 && Lx[i].y > 0.5) sh = shadow(v_w, N, L);
    vec3 H = normalize(L+Vv); float sp = spec*pow(max(dot(N,H),0.0), shin)*step(0.0,ndl);
    col += Lc[i].rgb*att*sh*(alb*dif + sp*Lx[i].z);
  }
  float vd = -(V*vec4(v_w,1.0)).z;
  float fh = exp(-max(v_w.z - fog_h, 0.0)*0.6);
  float f = 1.0 - exp(-fog_d*vd*fh);
  col = mix(col, fog_col, f);
  frag = vec4(col, vd);
}
""" % MAXL

SVS = """
#version 330
uniform mat4 M; uniform mat4 SVP; in vec3 in_pos;
void main(){ gl_Position = SVP*M*vec4(in_pos,1.0); }
"""
SFS = """
#version 330
void main(){}
"""

# additive: light beams, glows, dust (alpha untouched so the depth in alpha survives)
AVS = """
#version 330
uniform mat4 M; uniform mat4 VP; in vec3 in_pos; in vec3 in_nrm; in vec2 in_uv; in vec3 in_col;
out vec3 v_l; out vec2 v_uv; out vec3 v_w; out vec3 v_n; out vec3 v_c;
void main(){ vec4 w = M*vec4(in_pos,1.0); v_w=w.xyz; v_l=in_pos; v_uv=in_uv; v_n=mat3(M)*in_nrm; v_c=in_col; gl_Position=VP*w; }
"""
AFS = """
#version 330
uniform int amode; uniform vec3 acol; uniform float aint; uniform vec3 cam; uniform float t;
in vec3 v_l; in vec2 v_uv; in vec3 v_w; in vec3 v_n; in vec3 v_c;
out vec4 frag;
void main(){
  float a = 0.0;
  if (amode==0){ // beam: local cone along -Z from apex at origin; v_uv.y = 0 apex .. 1 base
    float h = clamp(-v_l.z, 0.0, 10.0); float y = v_uv.y;
    vec3 N = normalize(v_n); vec3 Vv = normalize(cam - v_w);
    float edge = pow(abs(dot(N, Vv)), 1.6);
    a = edge*(1.0-y)*(1.0-y)*smoothstep(0.0,0.12,y);
  } else if (amode==1){ // radial glow quad
    float r = length(v_uv*2.0-1.0); a = exp(-r*r*5.0)*0.7 + exp(-r*r*40.0)*0.6;
  } else { // dust mote
    float r = length(v_uv*2.0-1.0); a = smoothstep(1.0, 0.0, r);
  }
  frag = vec4(acol*aint*a*v_c, 0.0);
}
"""



def _set(prog, name, val):
    if name in prog:
        prog[name].value = val


def _write(prog, name, data):
    if name in prog:
        prog[name].write(data)


class Mesh:
    def __init__(self, ctx, prog, sprog, aprog, d):
        data = np.hstack([d['pos'], d['nrm'], d['uv'], d['col']]).astype('f4')
        self.vbo = ctx.buffer(data.tobytes())
        self.n = len(d['pos'])
        self.cap = self.n
        fmt = '3f 3f 2f 3f'
        self.vao = ctx.vertex_array(prog, [(self.vbo, fmt, 'in_pos', 'in_nrm', 'in_uv', 'in_col')])
        self.svao = ctx.vertex_array(sprog, [(self.vbo, '3f 32x', 'in_pos')])
        self.avao = ctx.vertex_array(aprog, [(self.vbo, fmt, 'in_pos', 'in_nrm', 'in_uv', 'in_col')])
        self.data = d

    def update(self, d):
        data = np.hstack([d['pos'], d['nrm'], d['uv'], d['col']]).astype('f4')
        self.vbo.write(data.tobytes())


class Renderer:
    def __init__(self, w=1080, h=1920, msaa=4, shadow=2048):
        self.w, self.h = w, h
        self.ctx = moderngl.create_standalone_context(backend='egl')
        c = self.ctx
        self.prog = c.program(vertex_shader=VS, fragment_shader=FS)
        self.sprog = c.program(vertex_shader=SVS, fragment_shader=SFS)
        self.aprog = c.program(vertex_shader=AVS, fragment_shader=AFS)
        self.msfbo = c.framebuffer(c.renderbuffer((w, h), 4, samples=msaa, dtype='f2'),
                                   c.depth_renderbuffer((w, h), samples=msaa))
        self.outtex = c.texture((w, h), 4, dtype='f2')
        self.outfbo = c.framebuffer(self.outtex)
        self.shtex = c.depth_texture((shadow, shadow))
        self.shtex.compare_func = '<='
        self.shtex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.shtex.repeat_x = self.shtex.repeat_y = False
        self.shfbo = c.framebuffer(depth_attachment=self.shtex)
        self.shadow_size = shadow
        self.meshes, self.textures = {}, {}
        self.white = c.texture((1, 1), 4, bytes([255, 255, 255, 255]))
        _set(self.prog, 'shmap', 1)
        _set(self.prog, 'tex', 0)

    def add_meshes(self, parts):
        for k, d in parts.items():
            self.meshes[k] = Mesh(self.ctx, self.prog, self.sprog, self.aprog, d)

    def set_dynamic(self, name, d):
        n = len(d['pos'])
        m = self.meshes.get(name)
        if m is None or m.cap < n:
            pad = max(n, 3)
            dd = {k: np.concatenate([v, np.zeros((pad - n,) + v.shape[1:], v.dtype)]) if pad > n else v for k, v in d.items()}
            m = Mesh(self.ctx, self.prog, self.sprog, self.aprog, dd)
            m.cap = pad
            self.meshes[name] = m
        else:
            m.update(d)
        m.n = n

    def add_texture(self, name, img, mip=True):
        img = np.ascontiguousarray(np.asarray(img)[::-1])
        if img.shape[2] == 3:
            img = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
        t = self.ctx.texture((img.shape[1], img.shape[0]), 4, img.astype(np.uint8).tobytes())
        if mip:
            t.build_mipmaps(); t.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            try:
                t.anisotropy = 8.0
            except Exception:
                pass
        self.textures[name] = t

    def render(self, items, cam, lights, env, adds=()):
        """items: list of (mesh, M 4x4, mat dict); cam: dict(eye, target, fov, near, far, up);
        lights: list of dicts; env: dict(amb_top, amb_bot, fog_col, fog_d, fog_h, shadow=dict(light index));
        adds: additive items (mesh, M, dict(amode, col, int))."""
        c = self.ctx
        V = look_at(cam['eye'], cam['target'], cam.get('up', (0, 0, 1)))
        P = perspective(cam['fov'], self.w / self.h, cam.get('near', 0.02), cam.get('far', 200.0))
        VP = (P @ V).astype('f4')
        has_sh = 0
        si = next((i for i, l in enumerate(lights) if l.get('shadow')), None)
        if si is not None:
            l = lights[si]
            pos = np.asarray(l['pos'], float); d = np.asarray(l['dir'], float); d /= np.linalg.norm(d)
            up = (0, 1, 0) if abs(d[2]) > 0.9 else (0, 0, 1)
            SV = look_at(pos, pos + d, up)
            SP = perspective(l.get('sh_fov', 2 * l.get('outer', 45) + 6), 1.0, l.get('sh_near', 0.1), l.get('sh_far', 30))
            SVP = (SP @ SV).astype('f4')
            self.shfbo.use(); self.shfbo.clear(depth=1.0)
            c.enable(moderngl.DEPTH_TEST); c.disable(moderngl.BLEND); c.disable(moderngl.CULL_FACE)
            _write(self.sprog, 'SVP', SVP.T.tobytes())
            for mesh, M, mat in items:
                if mat.get('cast', True):
                    _write(self.sprog, 'M', np.asarray(M, 'f4').T.tobytes())
                    self.meshes[mesh].svao.render(vertices=self.meshes[mesh].n)
            has_sh = 1
            _write(self.prog, 'SVP', SVP.T.tobytes())
            _set(self.prog, 'sh_soft', float(l.get('soft', 2.5)))
        _set(self.prog, 'has_sh', has_sh)
        self.shtex.use(1)
        self.msfbo.use()
        bg = env.get('bg', (0, 0, 0))
        self.msfbo.clear(bg[0], bg[1], bg[2], 1000.0, depth=1.0)
        c.enable(moderngl.DEPTH_TEST); c.disable(moderngl.BLEND); c.disable(moderngl.CULL_FACE)
        pr = self.prog
        _write(pr, 'VP', VP.T.tobytes()); _write(pr, 'V', V.T.tobytes())
        _set(pr, 'cam', tuple(map(float, cam['eye'])))
        Lp = np.zeros((MAXL, 4), 'f4'); Lc = np.zeros((MAXL, 4), 'f4'); Ld = np.zeros((MAXL, 4), 'f4'); Lx = np.zeros((MAXL, 4), 'f4')
        for i, l in enumerate(lights[:MAXL]):
            typ = {'point': 0, 'spot': 1, 'dir': 2}[l['type']]
            Lp[i, :3] = l.get('pos', (0, 0, 0)); Lp[i, 3] = typ
            Lc[i, :3] = np.asarray(l['col'], float) * l.get('energy', 1.0); Lc[i, 3] = l.get('range', 30)
            d = np.asarray(l.get('dir', (0, 0, -1)), float); d /= np.linalg.norm(d)
            Ld[i, :3] = d; Ld[i, 3] = math.cos(math.radians(l.get('outer', 45)))
            Lx[i] = (math.cos(math.radians(l.get('inner', l.get('outer', 45) * 0.7))), 1.0 if i == si else 0.0,
                     l.get('spec', 1.0), l.get('wrap', 0.0))
        _set(pr, 'nl', min(len(lights), MAXL))
        _write(pr, 'Lp', Lp.tobytes()); _write(pr, 'Lc', Lc.tobytes()); _write(pr, 'Ld', Ld.tobytes()); _write(pr, 'Lx', Lx.tobytes())
        _set(pr, 'amb_top', tuple(env.get('amb_top', (0.02, 0.02, 0.025))))
        _set(pr, 'amb_bot', tuple(env.get('amb_bot', (0.01, 0.01, 0.01))))
        _set(pr, 'fog_col', tuple(env.get('fog_col', (0, 0, 0))))
        _set(pr, 'fog_d', float(env.get('fog_d', 0.0))); _set(pr, 'fog_h', float(env.get('fog_h', 100.0)))
        for mesh, M, mat in items:
            M = np.asarray(M, 'f4')
            if abs(np.linalg.det(M[:3, :3].astype(np.float64))) < 1e-12:
                continue                                  # zero-scale item (e.g. text popping in): nothing to draw
            _write(pr, 'M', M.T.tobytes())
            NM = np.linalg.inv(M[:3, :3]).T.astype('f4')
            _write(pr, 'NM', NM.T.tobytes())
            tx = mat.get('tex')
            (self.textures[tx] if tx else self.white).use(0)
            _set(pr, 'tmode', int(mat.get('tmode', 1 if tx else 0)))
            _set(pr, 'temit', float(mat.get('temit', 1.0)))
            _set(pr, 'emit', tuple(map(float, mat.get('emit', (0, 0, 0)))))
            _set(pr, 'tint', tuple(map(float, mat.get('tint', (1, 1, 1)))))
            _set(pr, 'spec', float(mat.get('spec', 0.08))); _set(pr, 'shin', float(mat.get('shin', 24.0)))
            _set(pr, 'mode', int(mat.get('mode', 0))); _set(pr, 'seed', float(mat.get('seed', 0.0)))
            _set(pr, 'wsc', tuple(map(float, mat.get('wsc', (1.0, 1.0))))); _set(pr, 'wcol', tuple(map(float, mat.get('wcol', (-1.0, -1.0, -1.0)))))
            _set(pr, 'cellf', float(mat.get('cellf', -1.0))); _set(pr, 'tt', float(mat.get('tt', 0.0))); _set(pr, 'rate', float(mat.get('rate', 2.0)))
            uvx = mat.get('uvx', (0, 0, 1, 1)); _set(pr, 'uvx', tuple(map(float, uvx)))
            self.meshes[mesh].vao.render(vertices=self.meshes[mesh].n)
        if adds:
            c.enable(moderngl.BLEND)
            c.blend_func = (moderngl.ONE, moderngl.ONE, moderngl.ZERO, moderngl.ONE)
            self.msfbo.depth_mask = False
            ap = self.aprog
            _write(ap, 'VP', VP.T.tobytes()); _set(ap, 'cam', tuple(map(float, cam['eye'])))
            for mesh, M, a in adds:
                _write(ap, 'M', np.asarray(M, 'f4').T.tobytes())
                _set(ap, 'amode', int(a.get('amode', 0))); _set(ap, 'acol', tuple(map(float, a.get('col', (1, 1, 1)))))
                _set(ap, 'aint', float(a.get('int', 1.0)))
                self.meshes[mesh].avao.render(vertices=self.meshes[mesh].n)
            self.msfbo.depth_mask = True
            c.disable(moderngl.BLEND)
        c.copy_framebuffer(self.outfbo, self.msfbo)
        raw = self.outfbo.read(components=4, dtype='f2')
        img = np.frombuffer(raw, np.float16).reshape(self.h, self.w, 4)[::-1].astype(np.float32)
        return img
