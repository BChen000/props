# Wildlore asset pack: sources and licences

`get_assets.py` downloads these files from public GitHub repositories, pinned to the commits below, and checks each against the SHA-256 in `get_assets.py`. Nothing here is stored in BChen000/props.

These are byte-for-byte the files the episode "The Blue Raspberry" was rendered with. They were matched by SHA-256 in Nov 2026.

| file in WILDLORE_ASSETS | original | repository @ commit | licence |
|---|---|---|---|
| `hdri/babylon_forest.hdr` | `packages/tools/playground/public/textures/forest.hdr` | BabylonJS/Babylon.js @ 0880a7f | Apache 2.0 (NOTICE: "Babylon.js, Copyright 2023 The Babylon.js team") |
| `hdri/babylon_country.hdr` | `.../textures/country.hdr` | BabylonJS/Babylon.js @ 0880a7f | Apache 2.0 |
| `tex/rockyGround_basecolor.png` | `.../textures/rockyGround_basecolor.png` | BabylonJS/Babylon.js @ 0880a7f | Apache 2.0 |
| `tex/rockyGround_normal.png` | `.../textures/rockyGround_normal.png` | BabylonJS/Babylon.js @ 0880a7f | Apache 2.0 |
| `models/Bee.glb` | `meshes/Bee.glb` | BabylonJS/Assets @ 6946e9b | CC BY 4.0 |
| `tex/BroadleafBark.jpg` | `meshes/Trees/BroadleafBark.jpg` | BabylonJS/Assets @ 6946e9b | CC BY 4.0 |
| `tex/BroadleafBark_Normal.png` | `meshes/Trees/BroadleafBark_Normal.png` | BabylonJS/Assets @ 6946e9b | CC BY 4.0 |
| `tex/Moss_01_Color.png` | `third_party/textures/Moss_01/Moss_01_Color.png` | google/filament @ 995bbd1 | CC0 1.0 (from cgbookcase.com) |
| `tex/Moss_01_Normal.png` | `third_party/textures/Moss_01/Moss_01_Normal.png` | google/filament @ 995bbd1 | CC0 1.0 (from cgbookcase.com) |
| `hdri/noon_grass_2k.hdr` | `third_party/environments/noon_grass_2k.hdr` | google/filament @ 995bbd1 | CC0 1.0 (Poly Haven) |
| `hdri/kiara_1_dawn_1k.hdr` | `hdri/kiara_1_dawn_1k.hdr` | pmndrs/drei-assets @ 456060a | CC0 1.0 (Poly Haven) |
| `tex/hardwood2_diffuse.jpg` | `examples/textures/hardwood2_diffuse.jpg` | mrdoob/three.js @ 084ec06 | MIT (Copyright © 2010-2026 three.js authors) |

Where the licences come from:
- **BabylonJS/Assets:** the repository is CC BY 4.0 "unless specified otherwise in the asset folder". `meshes/` and `meshes/Trees/` have no licence file of their own.
- **google/filament:** `third_party/textures/` and `third_party/environments/` each hold `CC0.html` and a `URL.txt` naming the source (cgbookcase.com and hdrihaven.com, now Poly Haven).
- **pmndrs/drei-assets:** this is a mirror of Poly Haven HDRIs. The CC0 dedication comes from Poly Haven.

The files are unmodified. The two Babylon.js HDRIs are only renamed: `forest.hdr` became `babylon_forest.hdr`, and `country.hdr` became `babylon_country.hdr`.

## Credit in videos
End the description of every video made with this pack with this line:

`Credits: bee model and bark texture by the Babylon.js team (BabylonJS/Assets), CC BY 4.0, modified; HDRIs and ground texture from Babylon.js (Apache 2.0).`

- **The bee and the bark (CC BY 4.0)** require credit. "Modified" covers `load_bee` re-shading the wings and the bark's tint.
- **The Babylon.js HDRIs and ground texture (Apache 2.0)** show in the picture. Apache 2.0 asks that its NOTICE travel with derived work, so the same line names them.
- **The CC0 and MIT files** need no credit in a video. The MIT terms apply only to copies of the file itself.

## Fallbacks
If the bark or moss files are missing, `bblib.make_trunk` and `bblib.mat_moss` fall back to procedural bark and moss (`mat_bark_procedural`, `mat_moss_procedural`). These read fine at forest-shot distance but look plainer in close-ups.

## Not in the pack
The episode's picking hand is `models/xr_right_hand.glb`, the generic right hand from immersive-web/webxr-input-profiles (`packages/assets/profiles/generic-hand/right.glb`, MIT, Copyright (c) 2019 Amazon). No prop uses it, so it isn't downloaded.
