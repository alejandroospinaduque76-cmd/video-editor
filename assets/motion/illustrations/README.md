# assets/motion/illustrations/ — the cut-out illustration library (109 PNGs)

One hundred and nine **flat-vector illustrations with alpha**, teal/cyan on black silhouettes:
business people (confident, thinking, multitasking, signing, at the desk), hands (holding,
pointing, pitching), money (bag, bills, dollar sign, weight), metaphors (two roads, cliff, chains,
mask, puppet, hourglass, wings), audiences, and a few empty scenes/plates. Supplied by the user
on 2026-09-21 (`PNGs` pack). Usage rights are the user's; they ship here so a job never has to
look outside the repo. Each file was downscaled to **≤ 2400 px on the long side** from the
originals (up to 11,777 px, which trip PIL's decompression-bomb guard) — plenty for a 2160×3840
frame; the originals stay in the user's pack, never in a job.

Catalog: [`catalog.json`](catalog.json) — one row per file: `slug` (the file name), `name_es`,
`size`, `source` (the pack's original name) and bilingual `keywords`. **Find by concept:**
`python3 assets/motion/find.py dinero` / `--illustrations decisión`.

## How they are used (the WHAT — `presets/instagram/explainer/reference-craft.md`)

| Use | Mechanics | When |
|---|---|---|
| **Cut-out on a card** | `<img>` inside the comp, scaled to the panel, GSAP `pop`/`riseIn` on the wrapper | a noun event that has no icon: "two roads", "the weight of money", "multitasking" |
| **Scene plate (faceless beats)** | an `*-empty` / `escena-sin-personaje` / `fondo-degradado` plate under the words, a character in front | `faceless-mode.md` § 2 scenes: counter · list · flow beats |
| **Punch-cut field** | the illustration large, low opacity, behind a full-screen card | long-form punch-cuts, one per section at most |

Rules: never on the face (`workflows/face-guard.py check` judges every overlay); the palette is the
comp's, so tint via CSS `filter` on the wrapper if a look needs another hue; a `*-vacio` /
`*-empty` file is the same scene without its character, for type-behind and stacking.
