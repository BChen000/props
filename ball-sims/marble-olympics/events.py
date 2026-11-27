"""Renders the five events with their own templates and reads back who finished where.

  python events.py            -> build/events/<key>.mp4 for every event, plus build/events/results.json
  python events.py laser-wars -> one event

Each template is copied into build/ball-sims/olympics-<key>/, next to symlinks of every other ball-sims prop, so its
relative imports (../style-kit, ../battle-audio, ...) still work, and only the settings.py lines in the event's `set`
are replaced. The grand final is an episode of marble-funnel-drain and renders in place. Every event's finishing
order is read from the template's own simulation and must match `places` in settings.py, so the cards always agree
with the videos.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import settings as S

PY = sys.executable
SNIPPETS = {
    "ability-battle-template": (
        "import json, sim, settings as S\n"
        "s = sim.run(S.SEED)\n"
        "kos = [e['victim'] for e in s.events if e['type'] == 'ko']\n"
        "tl = json.load(open('out/timeline.json'))\n"
        "print(json.dumps(dict(places=[S.NAMES[s.winner]] + [S.NAMES[v] for v in kos[::-1]], win=tl['tau_win'])))\n"),
    "sword-roulette": (
        "import json, settings as S, timeline as T\n"
        "tl = T.Timeline(S.SEED)\n"
        "print(json.dumps(dict(places=[S.NAMES[tl.winner]] + [S.NAMES[e['j']] for e in tl.kills[::-1]],"
        " win=tl.v_reveal, big=S.NAMES[tl.chosen])))\n"),
    "marble-funnel-drain": (
        "import json, timeline as TL\n"
        "from sim import sim_path\n"
        "p = TL.Episode(sim_path()).places()\n"
        "print(json.dumps(dict(places=[q['colour'] for q in p], win=p[0]['out_video_s'])))\n"),
}
BUILD_CMD = {
    "ability-battle-template": ([PY, "make_video.py", "--jobs", "2"], "out/power_balls.mp4"),
    "sword-roulette": (["bash", "build.sh"], "out/sword_roulette.mp4"),
}


def mirror():
    """build/ball-sims/: a symlink to every prop, so copied templates find their siblings at ../<prop>."""
    root = os.path.join(S.BUILD, "ball-sims")
    os.makedirs(root, exist_ok=True)
    for name in os.listdir(S.BALL_SIMS):
        src, dst = os.path.join(S.BALL_SIMS, name), os.path.join(root, name)
        if os.path.isdir(src) and not name.startswith(".") and name != "marble-olympics" and not os.path.lexists(dst):
            os.symlink(src, dst)
    return root


def copy_template(ev):
    dst = os.path.join(mirror(), "olympics-" + ev["key"])
    if not os.path.exists(dst):
        shutil.copytree(os.path.join(S.BALL_SIMS, ev["template"]), dst,
                        ignore=shutil.ignore_patterns("out", "build", "stills", "__pycache__", "fonts"))
    path = os.path.join(dst, "settings.py")
    src = open(path, encoding="utf-8").read()
    for k, v in ev["set"].items():
        src, n = re.subn(r"^%s = .*$" % k, "%s = %r" % (k, v), src, count=1, flags=re.M)
        if n != 1:
            sys.exit("%s: no line '%s = ...' in %s" % (ev["key"], k, path))
    open(path, "w", encoding="utf-8").write(src)
    return dst


def build(ev):
    out = os.path.join(S.BUILD, "events", ev["key"] + ".mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if ev["template"] == "marble-funnel-drain":
        cwd = os.path.join(S.BALL_SIMS, ev["template"])
        env = dict(os.environ, EPISODE=ev["episode"])
        made = subprocess.run([PY, "-c", "import settings as S; print(S.BUILD + '/' + S.OUT_NAME + '.mp4')"],
                              cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout.strip()
        if not os.path.exists(made):
            subprocess.run([PY, "make_video.py"], cwd=cwd, env=env, check=True)
    else:
        cwd = copy_template(ev)
        env = dict(os.environ)
        cmd, rel = BUILD_CMD[ev["template"]]
        made = os.path.join(cwd, rel)
        if not os.path.exists(made):
            subprocess.run(cmd, cwd=cwd, check=True)
    res = json.loads(subprocess.run([PY, "-c", SNIPPETS[ev["template"]]], cwd=cwd, env=env, capture_output=True,
                                    text=True, check=True).stdout.strip().splitlines()[-1])
    if res["places"] != ev["places"]:
        sys.exit("%s finished %s, but settings.py says %s" % (ev["key"], res["places"], ev["places"]))
    shutil.copyfile(made, out)
    res["video"] = out
    return res


def main(keys):
    path = os.path.join(S.BUILD, "events", "results.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    for ev in S.EVENTS:
        if keys and ev["key"] not in keys:
            continue
        results[ev["key"]] = build(ev)
        print(ev["key"], results[ev["key"]], flush=True)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(results, open(path, "w"), indent=1)
    return results


if __name__ == "__main__":
    main(sys.argv[1:])
