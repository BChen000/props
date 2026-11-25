# props

The code, settings and styles behind GJ's animated YouTube Shorts, kept so a new video starts from parts that already work and match each channel's look:
- `ball-sims/`: Marble Pop
- `animal-docs/`: Wildlore
- `kids-songs/`: Story Time with Kenji

Start with [`CLAUDE.md`](CLAUDE.md). It has the workflow, the index of every prop and the rules for adding new ones.

```bash
git clone --depth 1 https://github.com/BChen000/props && cd props
./setup.sh ball-sims          # or animal-docs, kids-songs; add --check to only report what's missing
```
Each prop's README covers how to run it, its gotchas and what it can't do. Finished videos, fonts and model weights aren't stored here.
