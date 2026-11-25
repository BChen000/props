"""Render the Ring Escape rounds for the ring stream: one ../ring-escape Short per seed, into build/rounds/.

  python3 rounds.py               all of SEEDS (about 1.5 min a round on 2 cores; finished rounds are skipped)
  python3 rounds.py 7372 1885     just these seeds, numbered in the order given

The races of SEEDS ship in assets/ (8450's in ../ring-escape/assets/), so every machine replays the same rounds.
A seed with no recorded race is simulated first and saved to assets/. Find more seeds with ../ring-escape/search.py.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RING = os.path.join(os.path.dirname(HERE), "ring-escape")

# ---- settings (shipped values) ----
BUILD = os.environ.get("STREAMS_BUILD", os.path.join(HERE, "build"))
ROUNDS = os.environ.get("STREAMS_ROUNDS", os.path.join(BUILD, "rounds"))
SEEDS = [7372, 1885, 2973, 8450, 6735, 1415, 4268, 8201]
WINNERS = ["ORANGE", "BLUE", "GREEN", "CYAN", "PINK", "RED", "YELLOW", "PURPLE"]   # of SEEDS, for the README


def race_dir(seed):
    mine = os.path.join(HERE, "assets")
    if os.path.exists(os.path.join(RING, "assets", f"race_{seed}.npz")):
        return os.path.join(RING, "assets")
    return mine


def main():
    seeds = [int(a) for a in sys.argv[1:]] or SEEDS
    os.makedirs(ROUNDS, exist_ok=True)
    out_dir = os.path.join(BUILD, "ring-out")
    for k, seed in enumerate(seeds, 1):
        dst = os.path.join(ROUNDS, f"round_{k:02d}_{seed}.mp4")
        if os.path.exists(dst):
            print(f"round {k}: seed {seed} already rendered")
            continue
        env = dict(os.environ, RING_SEED=str(seed), RING_RACE_DIR=race_dir(seed), RING_OUT_DIR=out_dir)
        if not os.path.exists(os.path.join(env["RING_RACE_DIR"], f"race_{seed}.npz")):
            print(f"round {k}: simulating seed {seed}")
            subprocess.run([sys.executable, "sim.py", "record"], cwd=RING, env=env, check=True)
        print(f"round {k}: rendering seed {seed}", flush=True)
        subprocess.run([sys.executable, "build.py"], cwd=RING, env=env, check=True)
        shutil.copy2(os.path.join(out_dir, "ring_escape.mp4"), dst)
        print("  ->", os.path.relpath(dst, HERE))


if __name__ == "__main__":
    main()
