#!/usr/bin/env python3
"""POWER BALLS renderer: replays the deterministic sim against the video clock and draws 1080x1920 frames.

    python render.py timeline                 -> out/timeline.json (events with video times, for audio.py)
    python render.py preview preview.png --frame 633
    python render.py frames 0,633,1450 out/frames
    python render.py chunk 0 775 out/chunk_0.mp4
    python render.py style style.json         -> every exact style value
Add --seed N to any mode to render another fight. make_video.py runs the whole pipeline.
"""
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import skia

import settings as S
import sim
import drawkit as dk
import layout
import cards
import fighters
import fx
import overlays
from sim import AS, R, DT

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
W, H, FPS = S.W, S.H, S.FPS
COL = [dk.rgb(c) for c in S.COLORS]
ABIL = S.ABILITIES

layout.configure(W=S.W, H=S.H, TITLE=S.TITLE, SUBTITLE=S.SUBTITLE, WIN_TITLE=S.WIN_TITLE, ARENA_SIZE=S.ARENA,
                 CAPTION=S.CAPTION, DUEL_CAPTION=S.DUEL_CAPTION, END_CAPTION=S.END_CAPTION)
cards.configure(NAMES=S.NAMES, COLORS=S.COLORS, LABELS=S.ABILITY_LABELS, MAX_HP=S.HP, MAX_LEVEL=S.MAX_LEVEL)
fighters.configure(COLORS=S.COLORS, ABILITIES=S.ABILITIES, BALL_R=S.BALL_R)
fx.configure(BALL_R=S.BALL_R)
overlays.configure(ARENA=S.ARENA, NAMES=S.NAMES, COLORS=S.COLORS, ABILITIES=S.ABILITIES,
                   ABILITY_NAMES=S.ABILITY_NAMES, INTRO_TEXT=S.INTRO_TEXT, FIGHT_TEXT=S.FIGHT_TEXT,
                   OUT_TEXT=S.OUT_TEXT, FINAL_BLOW_TEXT=S.FINAL_BLOW_TEXT, WIN_TEXT=S.WIN_TEXT,
                   WIN_SUB_ONE=S.WIN_SUB_ONE, WIN_SUB_MANY=S.WIN_SUB_MANY,
                   CONFETTI=dict(overlays.CONFETTI, canvas=(S.W, S.H)))


# ---------------------------------------------------------------- director / timing
class Director:
    """Finds the final blow and stages slow motion, zoom and the winner screen around it."""

    def __init__(self, seed):
        self.seed = seed
        s = sim.run(seed)
        if s.winner is None:
            raise SystemExit(f'seed {seed} ends in a draw; pick another with search.py')
        self.t_end = s.t_end
        self.winner = s.winner
        hits = [e for e in s.events if e['type'] == 'hit']
        prev = hits[-2]['t'] if len(hits) >= 2 else 0.0
        if self.t_end - prev < 1.3:
            self.t_s = max(self.t_end - S.SLOW_LEAD, prev + 0.04)
        else:
            self.t_s = self.t_end - 0.8
        self.t_e = self.t_end + S.SLOW_TAIL
        self.t_win = self.t_end + S.WIN_DELAY
        self.final_loser = hits[-1]['victim']

    def speed(self, t):
        return S.SLOW if self.t_s <= t < self.t_e else 1.0


# ---------------------------------------------------------------- game effects (events -> fx presets)
class GameFX(fx.FX):
    def __init__(self, seed, director):
        super().__init__(rng=random.Random(seed * 7919 + 17))
        self.card_hit = [0.0] * 4
        self.heart_pop = [None] * 4
        self.ev_i = 0
        self.kos = []
        self.director = director
        self.trail = {}

    def upgrade_label(self, i, level, s):
        lab = S.UPGRADE_LABELS[ABIL[i]]
        if isinstance(lab, tuple):
            return lab[0] if level % s.p['MS_EVERY'] == 0 else lab[1]
        return lab

    def on_event(self, e, s):
        t = e['type']
        if t == 'blaster':
            b = s.balls[e['owner']]
            self.ring(b.x, b.y, R, R + 46, 0.2, dk.rgb(fx.RING_COLORS['blaster']), 6)
        elif t == 'bullet_wall':
            self.burst(e['x'], e['y'], 4, [dk.rgb(x) for x in fx.SPARK_COLORS['bullet_wall']], 80, 260, 0.25, 3,
                       kind='spark', drag=4)
        elif t == 'absorb':
            self.burst(e['x'], e['y'], 6, dk.rgb(fx.SPARK_COLORS['absorb']), 80, 240, 0.22, 3, kind='spark', drag=4)
        elif t == 'laser_fire':
            self.shake = max(self.shake, 7.0)
        elif t == 'missile_launch':
            b = s.balls[e['owner']]
            tipx, tipy = b.x + math.cos(b.aim) * (R + 20), b.y + math.sin(b.aim) * (R + 20)
            self.puff(tipx, tipy, 4, 60, 0.55, 7, dk.rgb(fx.SMOKE_COLORS['launch']), 3)
        elif t == 'missile_explode':
            self.explosion(e['x'], e['y'], e['hit'])
        elif t == 'lightning':
            self.add_bolt(owner=e['owner'], targets=list(e['targets']), pts=[tuple(p) for p in e['pts']])
            self.shake = max(self.shake, 3.5)
            gc, gs, gl = fx.LIGHTNING_GLOW
            for (px, py) in e['pts'][1:]:
                self.glow(px, py, gs, gl, dk.rgb(gc))
        elif t == 'hit':
            v = e['victim']
            self.hit(e['x'], e['y'], e['sx'], e['sy'], COL[v])
            self.card_hit[v] = 0.4
            self.heart_pop[v] = [e['hp'], 0.0]
            if e['upgraded'] and not s.over:
                a = s.balls[e['attacker']]
                self.label(self.upgrade_label(e['attacker'], e['level'], s), a.x, a.y, COL[e['attacker']])
        elif t == 'ko':
            v = e['victim']
            self.ko(e['x'], e['y'], COL[v], final=(s.over and self.director is not None))
            self.kos.append((v, s.t))
        elif t == 'bump':
            if e['v'] > 160:
                self.burst(e['x'], e['y'], 5, dk.rgb(fx.SPARK_COLORS['bump']), 60, 200, 0.18, 2.5, kind='spark',
                           drag=5)
        elif t == 'fizzle':
            self.puff(e['x'], e['y'], 3, 40, 0.4, 6, dk.rgb(fx.SMOKE_COLORS['fizzle']), 3)

    def step(self, s, speed=1.0):
        rng = self.rng
        while self.ev_i < len(s.events):
            e = s.events[self.ev_i]
            self.ev_i += 1
            self.on_event(e, s)
        for b in s.balls:
            if b.alive:
                h = self.trail.setdefault(b.i, [])
                h.append((b.x, b.y))
                if len(h) > 40:
                    del h[0]
            else:
                self.trail.pop(b.i, None)
        smoke = dk.rgb(fx.SMOKE_COLORS['trail'])
        for m in s.missiles:
            if rng.random() < 0.55:
                tx, ty = m.x - math.cos(m.ang) * 18, m.y - math.sin(m.ang) * 18
                self.puff(tx, ty, 1, 20, 0.55, 5, smoke, 1.5)
        for b in s.balls:
            if ABIL[b.i] == 'laser' and b.alive and b.lz_state == 'fire' and rng.random() < 0.6:
                ex, ey = s.beam_end(b.x, b.y, b.aim)
                back = b.aim + math.pi
                self.burst(ex, ey, 1, [dk.rgb(x) for x in fx.SPARK_COLORS['laser_wall']], 150, 420, 0.25, 3,
                           kind='spark', drag=4, ang=back, spread=1.2)
        self.update(DT, speed)
        for i in range(4):
            self.card_hit[i] = max(0.0, self.card_hit[i] - DT)
            if self.heart_pop[i] is not None:
                self.heart_pop[i][1] += DT
                if self.heart_pop[i][1] > 0.5:
                    self.heart_pop[i] = None


def weapon_state(s, b, t):
    """Live draw_weapon kwargs for ball b."""
    a = ABIL[b.i]
    if a == 'blaster':
        return dict(n=s.bl_count(b), rot=s.blaster_rot(t), since_fire=t - b.fire_t)
    if a == 'laser':
        charge = 0.0
        if b.lz_state == 'charge':
            charge = 1 - b.lz_timer / s.p['LZ_CHARGE']
        if b.lz_state == 'fire':
            charge = 1.0
        return dict(aim=b.aim, sight=(b.lz_state == 'idle'), charge=charge)
    if a == 'missiles':
        return dict(aim=b.aim, ready=fighters.missile_ready(b.cd))
    return {}


# ---------------------------------------------------------------- frame
class Renderer:
    def __init__(self, D):
        self.D = D
        self.surf = dk.new_surface(W, H)
        self.confetti = overlays.Confetti(FPS)

    def update_confetti(self, tau, tau_win):
        self.confetti.update(tau, tau_win, S.COLORS[self.D.winner])

    def draw(self, s, gfx, tau, k, phase):
        c = self.surf.getCanvas()
        layout.draw_background(c)
        frng = random.Random(k * 1000003 + 7)
        t = s.t
        if phase.get('win_age') is not None:
            layout.draw_win_header(c, phase['win_age'])
        else:
            layout.draw_header(c)
        self.draw_cards(c, s, gfx, t, phase)
        sh = gfx.shake
        ox = frng.uniform(-sh, sh) if sh > 0 else 0.0
        oy = frng.uniform(-sh, sh) if sh > 0 else 0.0
        final_mode = phase.get('final_blow', 0.0)
        layout.draw_arena_frame(c, ox, oy, final_mode)
        layout.begin_arena(c, ox, oy, phase.get('zoom', 1.0), phase.get('focus', (AS / 2, AS / 2)))
        self.draw_arena_content(c, s, gfx, t, k, frng, phase)
        c.restore()
        layout.begin_overlay(c, ox, oy)
        overlays.draw_flash(c, gfx.flash)
        overlays.draw_vignette(c, final_mode)
        self.draw_banners(c, s, gfx, t, phase)
        self.draw_overlays(c, s, k, phase)
        c.restore()
        alive = [b for b in s.balls if b.alive]
        if phase.get('win_age') is not None:
            layout.draw_caption(c, 'end')
        elif (len(alive) == 2 or s.over) and not phase.get('intro'):
            layout.draw_caption(c, 'duel', tau)
        else:
            layout.draw_caption(c, 'normal')
        self.confetti.draw(c)
        return self.surf

    def draw_cards(self, c, s, gfx, t, phase):
        alive = [b.alive for b in s.balls]
        hp = [b.hp for b in s.balls]
        leader = None if phase.get('intro') else cards.auto_leader([b.hp if b.alive else 0 for b in s.balls], alive)
        if phase.get('win_age') is not None:
            leader = self.D.winner
        ko_age = [(t - b.ko_t) if (not b.alive and b.ko_t is not None) else None for b in s.balls]
        cards.draw_cards(c, hp, [b.level for b in s.balls], alive, leader, ko_age, gfx.card_hit, gfx.heart_pop)

    def draw_arena_content(self, c, s, gfx, t, k, frng, phase):
        alive = [b for b in s.balls if b.alive]
        for b in alive:
            if ABIL[b.i] == 'lightning':
                fighters.draw_range_ring(c, b.x, b.y, s.lt_range(b), t, ready=b.cd <= 0)
        gfx.draw_smoke(c)
        gfx.draw_rings(c)
        for b in alive:
            if ABIL[b.i] != 'laser':
                continue
            tipx, tipy = b.x + math.cos(b.aim) * (R + 36), b.y + math.sin(b.aim) * (R + 36)
            ex, ey = s.beam_end(b.x, b.y, b.aim)
            if b.lz_state == 'charge':
                u = 1 - b.lz_timer / s.p['LZ_CHARGE']
                fighters.draw_laser_aim(c, tipx, tipy, ex, ey, t, u, b.lz_timer <= s.p['LZ_LOCK'])
            elif b.lz_state == 'fire':
                fighters.draw_laser_beam(c, b.x, b.y, ex, ey, s.lz_width(b), s.p['LZ_FIRE'] - b.lz_timer,
                                         s.p['LZ_FIRE'], t)
        for bl in s.bullets:
            fighters.draw_bullet(c, bl.x, bl.y, bl.vx, bl.vy)
        for m in s.missiles:
            fighters.draw_missile(c, m.x, m.y, m.ang, frng)
        for b in alive:
            fighters.draw_trail(c, b.i, gfx.trail.get(b.i, []))
        for b in alive:
            kw = weapon_state(s, b, t)
            kw['rng'] = random.Random(k * 31 + b.i)
            fighters.draw_weapon(c, ABIL[b.i], b.x, b.y, **kw)
        for b in alive:
            inv = b.inv
            fl = 0.0
            if inv > s.p['INVULN'] - 0.12:
                fl = 0.75
            shield = inv / s.p['INVULN'] if inv > 0 else 0.0
            fighters.draw_ball(c, b.i, b.x, b.y, b.hp, flash=fl, shield=shield)
        for bo in gfx.bolts:
            u = bo['age'] / bo['life']
            al = 255 * (1 - u) ** 0.7
            rngb = random.Random(bo['seed'] + (k // 2) * 7)
            owner = s.balls[bo['owner']]
            prev = (owner.x, owner.y) if owner.alive else bo['pts'][0]
            for j, ti in enumerate(bo['targets']):
                tb = s.balls[ti]
                p1 = (tb.x, tb.y) if tb.alive else bo['pts'][j + 1]
                fighters.draw_bolt(c, prev, p1, al, rngb)
                prev = p1
        gfx.draw_particles(c)
        gfx.draw_texts(c, hide_labels=phase.get('final_blow', 0) > 0)

    def draw_banners(self, c, s, gfx, t, phase):
        if phase.get('intro') or phase.get('win_age') is not None:
            return
        for (v, kt) in gfx.kos:
            if s.over and v == self.D.final_loser:
                continue
            overlays.draw_out(c, v, t - kt)
        overlays.draw_final_blow(c, phase.get('final_blow', 0.0), phase.get('tau', 0))

    def draw_overlays(self, c, s, k, phase):
        if phase.get('intro_alpha', 0) > 0:
            overlays.draw_intro(c, phase['tau'], phase['intro_alpha'], frame=k)
        fa = phase.get('fight_age')
        if fa is not None:
            overlays.draw_fight(c, fa)
        wa = phase.get('win_age')
        if wa is not None:
            b = s.balls[self.D.winner]
            overlays.draw_winner(c, wa, self.D.winner, b.hp, frame=k, weapon=weapon_state(s, b, s.t))


# ---------------------------------------------------------------- driver
def iterate(D, draw_cb=None, frame_range=None, collect_events=None, want=None):
    """Step the sim against the video clock; call draw_cb(surface, k) for the frames asked for."""
    s = sim.Sim(D.seed)
    gfx = GameFX(D.seed, D)
    rnd = Renderer(D) if draw_cb is not None else None
    tau_sim = S.T_INTRO
    tau_win = None
    total = None
    k = 0
    ev_seen = 0
    zoom = 1.0
    focus = (AS / 2, AS / 2)
    slow_tau0 = None
    while True:
        tau = k / FPS
        if tau >= S.T_INTRO:
            while True:
                nxt = tau_sim + DT / D.speed(s.t)
                if nxt > tau + 1e-9:
                    break
                s.step()
                gfx.step(s, D.speed(s.t))
                tau_sim = nxt
                if collect_events is not None:
                    while ev_seen < len(s.events):
                        e = s.events[ev_seen]
                        ev_seen += 1
                        e2 = {kk: vv for kk, vv in e.items() if kk != 'pts'}
                        e2['tau'] = tau_sim
                        collect_events.append(e2)
                if tau_win is None and s.over and s.t >= D.t_win:
                    tau_win = tau_sim
                    total = int(math.ceil((tau_win + S.WIN_HOLD) * FPS))
        if total is not None and k >= total:
            break
        phase = {'tau': tau}
        if tau < S.T_INTRO + 0.3:
            phase['intro_alpha'] = 1.0 if tau < S.T_INTRO else 1 - (tau - S.T_INTRO) / 0.3
        if tau < S.T_INTRO:
            phase['intro'] = True
        if tau >= S.T_INTRO:
            phase['fight_age'] = tau - S.T_INTRO
        if D.t_s <= s.t and tau_win is None:
            if slow_tau0 is None:
                slow_tau0 = tau
            fb = dk.clamp01((tau - slow_tau0) / overlays.FINAL['ramp'])
            if s.t > D.t_e:
                fb = dk.clamp01(1 - (s.t - D.t_e) / 0.4)
            phase['final_blow'] = fb
        if D.t_s - 0.05 <= s.t < D.t_win:
            alive_b = [b for b in s.balls if b.alive or b.i == D.final_loser]
            if s.t < D.t_end and len(alive_b) >= 2:
                fxp = sum(b.x for b in alive_b) / len(alive_b)
                fyp = sum(b.y for b in alive_b) / len(alive_b)
            else:
                lb = s.balls[D.final_loser]
                fxp, fyp = (lb.x + s.balls[D.winner].x) / 2, (lb.y + s.balls[D.winner].y) / 2
            target_z = S.ZOOM_FINAL if s.t < D.t_e else 1.0
        else:
            fxp, fyp = AS / 2, AS / 2
            target_z = 1.0
        zoom += (target_z - zoom) * 0.16
        half = AS / (2 * zoom)
        fxp = min(max(fxp, half), AS - half)
        fyp = min(max(fyp, half), AS - half)
        focus = (focus[0] + (fxp - focus[0]) * 0.2, focus[1] + (fyp - focus[1]) * 0.2)
        phase['zoom'] = zoom
        phase['focus'] = (min(max(focus[0], half), AS - half), min(max(focus[1], half), AS - half))
        if tau_win is not None:
            phase['win_age'] = tau - tau_win
        if rnd is not None:
            rnd.update_confetti(tau, tau_win)
            if want is not None:
                if k in want:
                    draw_cb(rnd.draw(s, gfx, tau, k, phase), k)
                if k >= max(want):
                    break
            elif frame_range is None or frame_range[0] <= k < frame_range[1]:
                draw_cb(rnd.draw(s, gfx, tau, k, phase), k)
            elif frame_range is not None and k >= frame_range[1]:
                break
        k += 1
        if k > 200 * FPS:
            raise RuntimeError('runaway')
    return dict(total=total, tau_win=tau_win)


def timeline(D, path):
    evs = []
    info = iterate(D, collect_events=evs)
    out = dict(info, seed=D.seed, t_end=D.t_end, t_s=D.t_s, t_e=D.t_e, t_win=D.t_win, winner=D.winner,
               T_INTRO=S.T_INTRO, SLOW=S.SLOW, fps=FPS, events=evs)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(out))
    return out


def style_json():
    """Every exact value the template uses (also written to style.json)."""
    import music
    import sfx
    return {
        'video': {'width': S.W, 'height': S.H, 'fps': S.FPS, 'encode': 'H.264 (libx264 veryfast, CRF 18, yuv420p)',
                  'audio': f'AAC 192k, {S.SR} Hz, loudnorm {S.LOUDNESS} LUFS / {S.TRUE_PEAK} dBTP'},
        'seed': S.SEED,
        'fighters': [{'name': n, 'color': c, 'ability': a, 'card_label': lab, 'intro_name': an,
                      'upgrade_label': S.UPGRADE_LABELS[a]}
                     for n, c, a, lab, an in zip(S.NAMES, S.COLORS, S.ABILITIES, S.ABILITY_LABELS, S.ABILITY_NAMES)],
        'texts': {k: getattr(S, k) for k in ['TITLE', 'SUBTITLE', 'WIN_TITLE', 'INTRO_TEXT', 'FIGHT_TEXT', 'CAPTION',
                                              'DUEL_CAPTION', 'END_CAPTION', 'OUT_TEXT', 'FINAL_BLOW_TEXT', 'WIN_TEXT',
                                              'WIN_SUB_ONE', 'WIN_SUB_MANY']},
        'timing_s': {'intro': S.T_INTRO, 'intro_fade': 0.3, 'fight_text': overlays.FIGHT['life'],
                     'out_banner': overlays.OUT['life'], 'slow_motion_speed': S.SLOW,
                     'slow_motion_lead': S.SLOW_LEAD, 'slow_motion_tail': S.SLOW_TAIL,
                     'final_blow_ramp': overlays.FINAL['ramp'], 'winner_delay_sim': S.WIN_DELAY,
                     'winner_hold': S.WIN_HOLD, 'hit_shake': cards.SHAKE['time'], 'heart_pop': 0.5,
                     'iframes': S.ABILITY['INVULN'], 'physics_step': S.DT},
        'camera': {'final_zoom': S.ZOOM_FINAL, 'zoom_smoothing_per_frame': 0.16, 'focus_smoothing_per_frame': 0.2,
                   'shake': 'random offset +-shake px per frame; laser 7, lightning 3.5, missile hit 4, KO 14'},
        'simulation': {'arena_px': S.ARENA, 'ball_radius': S.BALL_R, 'base_speed': S.BASE_SPEED, 'relax': S.RELAX,
                       'knockback': S.KNOCK, 'hp': S.HP, 'max_level': S.MAX_LEVEL,
                       'first_cooldown': S.FIRST_COOLDOWN, 'abilities': S.ABILITY},
        'fonts': dk.style(),
        'layout': layout.style(), 'cards': cards.style(), 'fighters_look': fighters.style(), 'fx': fx.style(),
        'overlays': overlays.style(), 'music': music.style(), 'sfx': sfx.style(),
        'mix': {'music_gain': S.MUSIC_GAIN, 'sfx_gain': S.SFX_GAIN, 'pregain': S.PREGAIN, 'limiter_ceiling': S.LIMIT,
                'music_highpass_hz': 35, 'limiter': '4x oversampled peak, 5 ms look-ahead, 90 ms release, 16 kHz LP',
                'end_fade_s': 0.6},
    }


def _pop_arg(args, name, default=None, cast=str):
    if name in args:
        i = args.index(name)
        v = cast(args[i + 1])
        del args[i:i + 2]
        return v
    return default


def main():
    args = sys.argv[1:]
    seed = _pop_arg(args, '--seed', S.SEED, int)
    D = Director(seed)
    mode = args[0] if args else 'help'
    if mode == 'timeline':
        path = args[1] if len(args) > 1 else OUT / 'timeline.json'
        out = timeline(D, path)
        print('timeline', path, 'frames', out['total'], 'duration', round(out['total'] / FPS, 2), 'winner',
              S.NAMES[D.winner])
    elif mode in ('frames', 'preview'):
        if mode == 'preview':
            frame = _pop_arg(args, '--frame', 633, int)
            want = {frame}
            target = Path(args[1] if len(args) > 1 else HERE / 'preview.png')
        else:
            want = set(int(x) for x in args[1].split(','))
            target = Path(args[2] if len(args) > 2 else OUT / 'frames')
            target.mkdir(parents=True, exist_ok=True)

        def cb(surf, k):
            path = target if mode == 'preview' else target / f'f{k:05d}.png'
            dk.save_png(surf, path)

        iterate(D, draw_cb=cb, want=want)
        print('wrote', target)
    elif mode == 'chunk':
        k0, k1, out = int(args[1]), int(args[2]), Path(args[3])
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.stem + '.part.mp4')
        cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS),
               '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
               '-threads', '1', '-movflags', '+faststart', str(tmp)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        t0 = time.time()
        cnt = [0]

        def cb(surf, k):
            proc.stdin.write(surf.toarray().tobytes())
            cnt[0] += 1

        iterate(D, draw_cb=cb, frame_range=(k0, k1))
        proc.stdin.close()
        if proc.wait() != 0:
            sys.exit('ffmpeg failed')
        os.replace(tmp, out)
        print(f'chunk {out.name}: {cnt[0]} frames in {time.time() - t0:.0f}s')
    elif mode == 'style':
        path = Path(args[1] if len(args) > 1 else HERE / 'style.json')
        path.write_text(json.dumps(style_json(), indent=2, ensure_ascii=False))
        print('wrote', path)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
