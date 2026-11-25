"""Download the Wildlore asset pack (~58 MB): the third-party HDRIs, textures and models that the Wildlore props
and the episode "The Blue Raspberry" load.

Every file comes straight from a public GitHub repository, pinned to a fixed commit, and is checked against its
SHA-256, so nothing third-party is stored in this repo. Sources and licences are in ASSET_LICENSES.md:
  Babylon.js (Apache 2.0)        forest.hdr -> hdri/babylon_forest.hdr, country.hdr -> hdri/babylon_country.hdr,
                                 rockyGround_basecolor.png, rockyGround_normal.png -> tex/
  BabylonJS/Assets (CC BY 4.0)   Bee.glb -> models/, BroadleafBark.jpg + _Normal.png -> tex/   (needs a credit line)
  google/filament                Moss_01_Color.png + _Normal.png -> tex/ (cgbookcase, CC0),
                                 noon_grass_2k.hdr -> hdri/ (Poly Haven, CC0)
  pmndrs/drei-assets             kiara_1_dawn_1k.hdr -> hdri/ (Poly Haven, CC0)
  three.js (MIT)                 hardwood2_diffuse.jpg -> tex/

  python get_assets.py              -> into WILDLORE_ASSETS (default /home/claude/assets)
  python get_assets.py DIR          -> into DIR (then export WILDLORE_ASSETS=DIR)
  python get_assets.py --check      -> only report what's missing or different
"""
import hashlib
import os
import shutil
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GH = "https://raw.githubusercontent.com/"
PG = "packages/tools/playground/public/textures/"  # Babylon.js playground textures
PINS = {"BabylonJS/Babylon.js": ("0880a7fcc6d772bb428cd5d551fbd8faaa5a919e", "master"),
        "BabylonJS/Assets": ("6946e9be89e0d471d5caba0d2338b4c1ada250d0", "master"),
        "google/filament": ("995bbd17ec545be7e8c6ee2fa74330e8ccc4a554", "main"),
        "pmndrs/drei-assets": ("456060a26bbeb8fdf79326f224b6d99b8bcce736", "master"),
        "mrdoob/three.js": ("084ec06444244980752a420f0e1af5cd8f112aa1", "dev")}
FILES = {  # path in the asset folder: (sha256, repository, path in that repository)
    "hdri/babylon_forest.hdr": ("380fcf11685ce3ea0397757e3ba95fe74198e3897feb8dcd3a4932d706d3c5fa", "BabylonJS/Babylon.js",
                                PG + "forest.hdr"),
    "hdri/babylon_country.hdr": ("d7ab94e8015db2b61c29e6c7317bc32d4672dbfee8c4af19e1b0079de423238e", "BabylonJS/Babylon.js",
                                 PG + "country.hdr"),
    "hdri/noon_grass_2k.hdr": ("d9b8bc2a5d66a2d7165214f825b766cede993285d2e7488747ce828592610de9", "google/filament",
                               "third_party/environments/noon_grass_2k.hdr"),
    "hdri/kiara_1_dawn_1k.hdr": ("ee70fb8c8fb3e34566802191d83b299e179ecc392b97639e6c750f66e161c8e2", "pmndrs/drei-assets",
                                 "hdri/kiara_1_dawn_1k.hdr"),
    "tex/rockyGround_basecolor.png": ("e0f9375b366c3bd3375581a329af36fe70ded07ffee8e1156aa6a210c16f486b", "BabylonJS/Babylon.js",
                                      PG + "rockyGround_basecolor.png"),
    "tex/rockyGround_normal.png": ("66fccd4db45e00fcc713907208b42aa9b64f4f26db35e9b5251b36756558b7a1", "BabylonJS/Babylon.js",
                                   PG + "rockyGround_normal.png"),
    "tex/BroadleafBark.jpg": ("abd3c66e776fbf37b8d74265fb65bdc936f3a549a2ca0af8548d4129cb5f9c6f", "BabylonJS/Assets",
                              "meshes/Trees/BroadleafBark.jpg"),
    "tex/BroadleafBark_Normal.png": ("b7c482ee77418f0fcc07ff2eb60461512df65eea667fa1ffece52dcc41272b62", "BabylonJS/Assets",
                                     "meshes/Trees/BroadleafBark_Normal.png"),
    "tex/Moss_01_Color.png": ("e3b8db0ee0b3351e2777885018793422a5088ae7b6765bf3ff4471462c7271ca", "google/filament",
                              "third_party/textures/Moss_01/Moss_01_Color.png"),
    "tex/Moss_01_Normal.png": ("ae3329bee1b1282c71bd5728922b0bc2440d2c4465f1d92167b1a572ddcea22d", "google/filament",
                               "third_party/textures/Moss_01/Moss_01_Normal.png"),
    "tex/hardwood2_diffuse.jpg": ("3986fe3bd7d3c24b18e7da17ae72bbef9385dbc355c931c52a04dbfe1412c802", "mrdoob/three.js",
                                  "examples/textures/hardwood2_diffuse.jpg"),
    "models/Bee.glb": ("e7f57e9818d89bd68717e961bbfe9f38ecbbea2a4b99eab23fef3f77613dfb45", "BabylonJS/Assets", "meshes/Bee.glb"),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def status(dest):
    bad = {}
    for rel, (digest, _, _) in FILES.items():
        p = os.path.join(dest, rel)
        if not os.path.exists(p):
            bad[rel] = "missing"
        elif sha256(p) != digest:
            bad[rel] = "different"
    return bad


def fetch(dest, rel):
    digest, repo, path = FILES[rel]
    out = os.path.join(dest, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for ref in PINS[repo]:  # the pinned commit first, the branch as a fallback
        try:
            urllib.request.urlretrieve(GH + f"{repo}/{ref}/{path}", out + ".part")
            if sha256(out + ".part") == digest:
                os.replace(out + ".part", out)
                return True
            print(f"  {rel}: {repo}@{ref} has a different file, skipped")
        except Exception as e:
            print(f"  {rel}: {repo}@{ref} failed: {e}")
        if os.path.exists(out + ".part"):
            os.remove(out + ".part")
    return False


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dest = args[0] if args else os.environ.get("WILDLORE_ASSETS", "/home/claude/assets")
    bad = status(dest)
    if "--check" not in sys.argv:
        for rel in list(bad):
            print("fetching", rel, flush=True)
            fetch(dest, rel)
        bad = status(dest)
        os.makedirs(dest, exist_ok=True)
        shutil.copy(os.path.join(HERE, "ASSET_LICENSES.md"), os.path.join(dest, "ASSET_LICENSES.md"))
    for rel in FILES:
        print(f"  {bad.get(rel, 'ok'):9s} {rel}")
    print(("all present in " if not bad else f"{len(bad)} missing in ") + dest)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
