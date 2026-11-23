"""overlays: the POWER BALLS on-arena overlays (skia), drawn in arena coordinates (0..ARENA px).

  draw_intro      PICK YOUR FIGHTER! panel with the four fighters popping in (fades out via a layer)
  draw_fight      big tilted FIGHT! that slams in and fades
  draw_out        "{NAME} IS OUT!" banner at the top of the arena
  draw_final_blow pulsing red FINAL BLOW... (pair with draw_vignette + layout's red frame)
  draw_vignette   dark red edge vignette during the final blow
  draw_flash      white flash (KO hits)
  draw_winner     winner panel: crown, big fighter, "{NAME} WINS!", "with just 1 HP left!"
  Confetti        full-screen confetti burst + rain (screen coordinates)

    python overlays.py --preview preview.png
"""
import math
import random
import sys
from pathlib import Path

import skia

import drawkit as dk
import fighters

# ---------------------------------------------------------------- settings
ARENA = 872.0
NAMES = ['RED', 'BLUE', 'GREEN', 'YELLOW']
COLORS = ['#FE394C', '#2F7EFF', '#21C45D', '#FEC32F']
ABILITIES = ['blaster', 'laser', 'missiles', 'lightning']
ABILITY_NAMES = ['360° BLASTER', 'LASER BEAM', 'MISSILES', 'LIGHTNING']
INTRO_TEXT = 'PICK YOUR FIGHTER!'
FIGHT_TEXT = 'FIGHT!'
OUT_TEXT = '{name} IS OUT!'
FINAL_BLOW_TEXT = 'FINAL BLOW...'
WIN_TEXT = '{name} WINS!'
WIN_SUB_ONE = 'with just {hp} HP left!'
WIN_SUB_MANY = 'with {hp} HP left!'

PANEL_BG, PANEL_RADIUS = '#000000', 36
INTRO = dict(box=(36, 226, 836, 646), box_alpha=215, title_y=320, title_size=62, title_max_w=740, spacing=190,
             ball_y=468, scale=1.3, pop_lead=0.45, pop_stagger=0.09, pop_time=0.4, bob=4, bob_hz=3.2,
             bob_phase=1.3, name_dy=102, name_size=31, ability_dy=138, ability_size=19, ability_color='#D2CDE4',
             ability_max_w=180, fade=0.3)
FIGHT = dict(size=150, color='#FFFFFF', outline='#140A12', ow=16, shadow=8, rotate=-4, grow=1.2, slam=0.18,
             fade_from=0.65, fade_len=0.35, life=1.0)
OUT = dict(y=58, size=44, box='#08080E', box_alpha=225, pad=28, half_h=36, radius=16, pop_from=0.5, pop_time=0.25,
           life=2.0, fade_from=1.6, fade_len=0.4)
FINAL = dict(y=62, size=48, color='#FF4557', outline='#14080E', ow=9, pulse=0.04, pulse_hz=8, ramp=0.2)
VIGNETTE = dict(color='#3C000A', alpha=150, inner=0.55, radius=0.75)
FLASH_COLOR = '#FFFFFF'
WINNER = dict(box=(36, 166, 836, 716), box_alpha=220, box_fade=0.25, pop_time=0.4, crown_y=258, crown_w=110,
              ball_y=392, scale=1.7, name_y=555, name_size=112, name_max_w=740, name_delay=0.15, sub_y=650,
              sub_size=42, sub_color='#FFFFFF', sub_delay=0.35, sub_fade=0.3)
CONFETTI = dict(seed=4242, burst=140, burst_from_center=0.55, center=(540, 900), rain_per_frame=3, rain_until=2.6,
                gravity=700, terminal=330, flutter=40, extra_colors=['#FFCD3C', '#FFFFFF'], width=(9, 14),
                height=(16, 26), canvas=(1080, 1920))


def configure(**kw):
    g = globals()
    for k, v in kw.items():
        if k not in g:
            raise KeyError(k)
        g[k] = v


def _panel(c, box, alpha):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(*box), PANEL_RADIUS, PANEL_RADIUS), dk.fill(PANEL_BG, alpha))


# ---------------------------------------------------------------- intro / fight
def draw_intro(c, tau, layer_alpha=1.0, frame=0):
    """PICK YOUR FIGHTER! at video time tau (s). layer_alpha < 1 fades the whole panel."""
    g = INTRO
    ia = 1.0
    layer = layer_alpha < 1.0
    if layer:
        c.saveLayerAlpha(skia.Rect(0, 0, ARENA, ARENA), int(255 * layer_alpha))
    _panel(c, g['box'], g['box_alpha'] * ia)
    dk.text(c, INTRO_TEXT, ARENA / 2, g['title_y'], g['title_size'], 'Black', (255, 255, 255), 255 * ia,
            max_w=g['title_max_w'])
    for i in range(4):
        cx = ARENA / 2 + (i - 1.5) * g['spacing']
        cy = g['ball_y']
        pop = dk.ease_out_back((tau + g['pop_lead'] - g['pop_stagger'] * i) / g['pop_time'])
        if pop <= 0:
            continue
        bob = g['bob'] * math.sin(tau * g['bob_hz'] + i * g['bob_phase'])
        c.save()
        c.translate(cx, cy + bob)
        c.scale(pop, pop)
        fighters.draw_weapon(c, ABILITIES[i], 0, 0, scale=g['scale'], rng=random.Random(frame * 13 + i))
        fighters.draw_ball(c, i, 0, 0, 7, scale=g['scale'], alpha=255 * ia)
        c.restore()
        dk.text(c, NAMES[i], cx, cy + g['name_dy'], g['name_size'], 'Black', COLORS[i], 255 * ia * dk.clamp01(pop))
        dk.text(c, ABILITY_NAMES[i], cx, cy + g['ability_dy'], g['ability_size'], 'Bold', g['ability_color'],
                255 * ia * dk.clamp01(pop), max_w=g['ability_max_w'])
    if layer:
        c.restore()


def draw_fight(c, age):
    g = FIGHT
    if not (0 <= age < g['life']):
        return
    sc = 1.0 + g['grow'] * (1 - dk.ease_out(age / g['slam']))
    al = 255 * (1 - dk.clamp01((age - g['fade_from']) / g['fade_len']))
    c.save()
    c.translate(ARENA / 2, ARENA / 2)
    c.scale(sc, sc)
    c.rotate(g['rotate'])
    dk.text(c, FIGHT_TEXT, 0, 0, g['size'], 'Black', g['color'], al, outline=g['outline'], ow=g['ow'],
            shadow=g['shadow'])
    c.restore()


# ---------------------------------------------------------------- knockouts / final blow
def draw_out(c, i, age):
    """'{NAME} IS OUT!' banner, age s after the knockout (shows for OUT['life'] s)."""
    g = OUT
    if not (0 <= age < g['life']):
        return
    sc = g['pop_from'] + (1 - g['pop_from']) * dk.ease_out_back(age / g['pop_time'])
    al = 255 * (1 - dk.clamp01((age - g['fade_from']) / g['fade_len']))
    c.save()
    c.translate(ARENA / 2, g['y'])
    c.scale(sc, sc)
    msg = OUT_TEXT.format(name=NAMES[i])
    f = dk.font('Black', g['size'])
    w = f.measureText(msg)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-w / 2 - g['pad'], -g['half_h'], w / 2 + g['pad'], g['half_h']),
                                      g['radius'], g['radius']), dk.fill(g['box'], g['box_alpha'] * al / 255))
    dk.text(c, msg, 0, 0, g['size'], 'Black', COLORS[i], al)
    c.restore()


def draw_final_blow(c, strength, tau):
    """Pulsing FINAL BLOW... text; strength 0..1 fades it."""
    g = FINAL
    if strength <= 0:
        return
    pulse = 1.0 + g['pulse'] * math.sin(tau * g['pulse_hz'])
    c.save()
    c.translate(ARENA / 2, g['y'])
    c.scale(pulse, pulse)
    dk.text(c, FINAL_BLOW_TEXT, 0, 0, g['size'], 'Black', g['color'], 255 * strength, outline=g['outline'],
            ow=g['ow'])
    c.restore()


def draw_vignette(c, strength):
    g = VIGNETTE
    if strength <= 0:
        return
    sh = skia.GradientShader.MakeRadial((ARENA / 2, ARENA / 2), ARENA * g['radius'],
                                        [dk.C((0, 0, 0), 0), dk.C(g['color'], g['alpha'] * strength)],
                                        [g['inner'], 1.0])
    c.drawRect(skia.Rect(0, 0, ARENA, ARENA), skia.Paint(Shader=sh))


def draw_flash(c, strength):
    if strength > 0:
        c.drawRect(skia.Rect(0, 0, ARENA, ARENA), dk.fill(FLASH_COLOR, 255 * min(1.0, strength)))


# ---------------------------------------------------------------- winner
def draw_winner(c, age, i, hp, frame=0, weapon=None):
    """Winner panel age s after it appears. weapon: draw_weapon kwargs for the live weapon state."""
    g = WINNER
    pop = dk.ease_out_back(age / g['pop_time'])
    ba = dk.clamp01(age / g['box_fade'])
    _panel(c, g['box'], g['box_alpha'] * ba)
    c.save()
    c.translate(ARENA / 2, 0)
    c.scale(max(0.01, pop), max(0.01, pop))
    dk.crown(c, 0, g['crown_y'], g['crown_w'])
    kw = dict(weapon or {})
    kw.setdefault('rng', random.Random(frame * 17))
    fighters.draw_weapon(c, ABILITIES[i], 0, g['ball_y'], scale=g['scale'], **kw)
    fighters.draw_ball(c, i, 0, g['ball_y'], hp, scale=g['scale'])
    c.restore()
    pop2 = dk.ease_out_back((age - g['name_delay']) / g['pop_time'])
    if pop2 > 0:
        c.save()
        c.translate(ARENA / 2, g['name_y'])
        c.scale(pop2, pop2)
        dk.text(c, WIN_TEXT.format(name=NAMES[i]), 0, 0, g['name_size'], 'Black', COLORS[i], max_w=g['name_max_w'])
        c.restore()
    pop3 = dk.clamp01((age - g['sub_delay']) / g['sub_fade'])
    if pop3 > 0:
        sub = (WIN_SUB_ONE if hp == 1 else WIN_SUB_MANY).format(hp=hp)
        dk.text(c, sub, ARENA / 2, g['sub_y'], g['sub_size'], 'ExtraBold', g['sub_color'], 255 * pop3, caps=False)


class Confetti:
    """Advance once per video frame with update(tau, tau_win, winner_color); draw in screen coordinates."""

    def __init__(self, fps=30):
        self.rng = random.Random(CONFETTI['seed'])
        self.parts = []
        self.fps = fps

    def update(self, tau, tau_win, color):
        g = CONFETTI
        rng = self.rng
        dt = 1.0 / self.fps
        W, H = g['canvas']
        if tau_win is not None and tau >= tau_win:
            age = tau - tau_win
            n = 0
            if age < dt * 1.5:
                n = g['burst']
            elif age < g['rain_until']:
                n = g['rain_per_frame']
            for _ in range(n):
                burst = age < dt * 1.5
                if burst and rng.random() < g['burst_from_center']:
                    x, y = g['center'][0] + rng.uniform(-60, 60), g['center'][1] + rng.uniform(-40, 40)
                    a = rng.uniform(-math.pi, 0)
                    sp = rng.uniform(500, 1500)
                    vx, vy = math.cos(a) * sp, math.sin(a) * sp - 200
                else:
                    x, y = rng.uniform(0, W), rng.uniform(-260, -20)
                    vx, vy = rng.uniform(-60, 60), rng.uniform(120, 300)
                cols = [dk.rgb(color)] + [dk.rgb(x_) for x_ in g['extra_colors']]
                self.parts.append([x, y, vx, vy, rng.uniform(0, 6.28), rng.uniform(-9, 9), rng.uniform(0, 6.28),
                                   rng.uniform(4, 9), rng.choice(cols), rng.uniform(*g['width']),
                                   rng.uniform(*g['height'])])
        keep = []
        for p in self.parts:
            p[3] += g['gravity'] * dt
            p[2] *= 0.985
            p[3] = min(p[3], g['terminal'] + 40 * math.sin(p[6]))
            p[3] *= 0.995 if p[3] > 0 else 1
            p[6] += p[7] * dt
            p[0] += (p[2] + g['flutter'] * math.sin(p[6] * 1.3)) * dt
            p[1] += p[3] * dt
            p[4] += p[5] * dt
            if p[1] < H + 60:
                keep.append(p)
        self.parts = keep

    def draw(self, c):
        for p in self.parts:
            c.save()
            c.translate(p[0], p[1])
            c.rotate(math.degrees(p[4]))
            c.scale(max(0.15, abs(math.cos(p[6]))), 1.0)
            c.drawRect(skia.Rect(-p[9] / 2, -p[10] / 2, p[9] / 2, p[10] / 2), dk.fill(p[8]))
            c.restore()


def style():
    return {
        'arena_px': ARENA, 'coordinates': 'arena-local (0..arena_px); confetti uses 1080x1920 screen coordinates',
        'fighters': [{'name': n, 'color': col, 'ability': ab, 'ability_name': an}
                     for n, col, ab, an in zip(NAMES, COLORS, ABILITIES, ABILITY_NAMES)],
        'texts': {'intro': INTRO_TEXT, 'fight': FIGHT_TEXT, 'out': OUT_TEXT, 'final_blow': FINAL_BLOW_TEXT,
                  'win': WIN_TEXT, 'win_sub_one': WIN_SUB_ONE, 'win_sub_many': WIN_SUB_MANY},
        'font': 'Poppins (Black for headlines, Bold/ExtraBold for small lines)',
        'panel': {'color': PANEL_BG, 'radius': PANEL_RADIUS},
        'intro': dict(INTRO, pop_easing='easeOutBack, starts (pop_lead - stagger*i) s early'),
        'fight': dict(FIGHT, slam_easing='easeOutCubic'),
        'out_banner': dict(OUT, pop_easing='easeOutBack'),
        'final_blow': FINAL, 'vignette': VIGNETTE, 'flash_color': FLASH_COLOR,
        'winner': dict(WINNER, pop_easing='easeOutBack'),
        'confetti': CONFETTI,
    }


# ---------------------------------------------------------------- preview
def _arena_backdrop(c):
    c.clear(dk.C('#0D0D17'))
    gp = dk.stroke('#AFAFBE', 1.6, 120, cap=skia.Paint.kButt_Cap)
    for k in range(11):
        v = 76 + 80 * k
        if v < ARENA:
            c.drawLine(v, 0, v, ARENA, gp)
            c.drawLine(0, v, ARENA, v, gp)


def preview(path):
    """2x2 sheet: intro panel, OUT banner + FIGHT!, final blow, winner panel (each the 872 px arena)."""
    n = int(ARENA)
    sheet = dk.new_surface(2 * n + 24, 2 * n + 24)
    sc = sheet.getCanvas()
    sc.clear(dk.C('#130D22'))
    cells = []
    for k in range(4):
        surf = dk.new_surface(n, n)
        c = surf.getCanvas()
        _arena_backdrop(c)
        if k == 0:
            draw_intro(c, 1.2, 1.0, frame=36)
        elif k == 1:
            fighters.draw_ball(c, 0, 300, 520, 4)
            fighters.draw_ball(c, 3, 600, 300, 5)
            draw_out(c, 2, 0.6)
            draw_fight(c, 0.3)
        elif k == 2:
            fighters.draw_ball(c, 0, 360, 470, 1)
            fighters.draw_ball(c, 3, 470, 400, 1)
            draw_vignette(c, 1.0)
            draw_final_blow(c, 1.0, 0.4)
            c.drawRect(skia.Rect(0, 0, ARENA, ARENA), dk.stroke('#FF3B4E', 10))
        else:
            draw_winner(c, 1.5, 0, 1, frame=45, weapon=dict(n=15, rot=1.0))
        cells.append(surf.makeImageSnapshot())
    for k, img in enumerate(cells):
        sc.drawImage(img, 8 + (k % 2) * (n + 8), 8 + (k // 2) * (n + 8))
    dk.save_png(sheet, path)


if __name__ == '__main__':
    if '--preview' in sys.argv:
        out = sys.argv[sys.argv.index('--preview') + 1]
        preview(out)
        print('wrote', out)
    elif '--style' in sys.argv:
        import json
        out = sys.argv[sys.argv.index('--style') + 1]
        Path(out).write_text(json.dumps(dict(style(), **dk.style()), indent=2, ensure_ascii=False))
        print('wrote', out)
    else:
        print(__doc__)
