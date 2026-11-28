"""Fire or Ice? (Marble Pop, Nov 2026): three wild classical pieces against three calm ones. Run any step with
EPISODE=fire-or-ice (make_video.sh passes it through), which builds in build_fire-or-ice/.

FIRE: In the Hall of the Mountain King, Turkish March, Flight of the Bumblebee (orange and red glows, ember-dark
moods, coal and dark slabs). ICE: Swan Lake, Für Elise, Brahms' Lullaby (cyan and ice-blue glows, cold blue moods,
slabs, ornaments and discs). All six melodies are public domain (published before 1929).
"""
TITLE = 'Fire or Ice?'
TEAMS = {'FIRE': (255, 118, 36), 'ICE': (96, 208, 255)}

ROUNDS = [
    dict(song='mountain_king', team='FIRE', style='helix', obst='coal', R=2.1, R1=1.15, turns=2, sgn=+1,
         drift=(0.0, 0.0), glow=(1.0, 0.32, 0.03), e=0.24),
    dict(song='swan_lake', team='ICE', style='stairs', obst='slab', vf=2.4, A=0.55, Tsw=3.2,
         glow=(0.12, 0.72, 1.0), e=0.30),
    dict(song='turkish_march', team='FIRE', style='zigzag', obst='slab', vf=2.1, k=1.9, Lmin=0.22, Lmax=0.95,
         glow=(1.0, 0.10, 0.02), e=0.34),
    dict(song='fur_elise', team='ICE', style='helix', obst='ornament', R=2.0, R1=1.3, turns=2, sgn=-1,
         drift=(0.0, 0.0), glow=(0.40, 0.62, 1.0), e=0.26),
    dict(song='bumblebee', team='FIRE', style='stairs', obst='coal', vf=2.5, A=0.45, Tsw=2.6,
         glow=(1.0, 0.58, 0.04), e=0.30),
    dict(song='brahms_lullaby', team='ICE', style='zigzag', obst='mint', vf=2.1, k=1.9, Lmin=0.22, Lmax=0.95,
         glow=(0.55, 0.92, 1.0), e=0.34),
]

MOODS = [
    dict(fog=(0.11, 0.035, 0.012), sun=(1.0, 0.70, 0.48), sun_e=2.7, amb=1.3),
    dict(fog=(0.10, 0.20, 0.33), sun=(0.90, 0.96, 1.0), sun_e=3.4, amb=1.0),
    dict(fog=(0.12, 0.025, 0.02), sun=(1.0, 0.62, 0.45), sun_e=2.6, amb=1.3),
    dict(fog=(0.07, 0.13, 0.30), sun=(0.88, 0.94, 1.0), sun_e=3.3, amb=1.0),
    dict(fog=(0.12, 0.06, 0.012), sun=(1.0, 0.78, 0.50), sun_e=2.6, amb=1.3),
    dict(fog=(0.12, 0.22, 0.34), sun=(0.92, 0.97, 1.0), sun_e=3.4, amb=1.0),
]
INTRO_MOOD = len(MOODS) - 1
