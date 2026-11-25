"""Regenerates the prop index in CLAUDE.md from each prop's README.md.

Every <channel>/<prop>/README.md contributes one line: the summary after "# name:" in its heading if there is one,
otherwise the first sentence of its first paragraph. Run it after adding or renaming a prop:
  python update_index.py           -> rewrites the block between the index markers in CLAUDE.md
  python update_index.py --print   -> prints the index instead
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
START, END = "<!-- index:start -->", "<!-- index:end -->"
MAX = 190


def summary(readme):
    lines = open(readme, encoding="utf-8").read().splitlines()
    head = next((l for l in lines if l.startswith("# ")), "")
    if ": " in head:
        return head.split(": ", 1)[1].strip()
    para = []
    for l in lines[lines.index(head) + 1 if head in lines else 0:]:
        s = l.strip()
        if not s:
            if para:
                break
            continue
        if s.startswith(("!", "#", "|", "```", "- ", "* ")) or re.match(r"\d+\. ", s):
            if para:
                break
            continue
        para.append(s)
    text = " ".join(para)
    text = re.sub(r"\*\*|`", "", text)
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    first = (m.group(1) if m else text).rstrip(":").strip()
    if len(first) > MAX:
        first = first[:MAX].rsplit(" ", 1)[0].rstrip(",;:") + " …"
    return first


def build():
    out = []
    for ch in sorted(d for d in os.listdir(HERE) if os.path.isdir(os.path.join(HERE, d)) and not d.startswith(".")):
        props = sorted(glob.glob(os.path.join(HERE, ch, "*", "README.md")))
        if not props:
            continue
        out.append(f"### {ch}/ ({len(props)})")
        for r in props:
            name = os.path.basename(os.path.dirname(r))
            out.append(f"- `{name}`: {summary(r)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    idx = build()
    if "--print" in sys.argv:
        print(idx)
        sys.exit(0)
    p = os.path.join(HERE, "CLAUDE.md")
    s = open(p, encoding="utf-8").read()
    a, b = s.index(START) + len(START), s.index(END)
    open(p, "w", encoding="utf-8").write(s[:a] + "\n" + idx + s[b:])
    print("index updated:", idx.count("\n- "), "props")
