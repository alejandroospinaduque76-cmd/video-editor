# assets/motion/ — the motion library (icons + wireframe beds + illustrations)

Three libraries the short-form look draws from, supplied by the user (icons and beds on 2026-09-14, illustrations on 2026-09-21) (WeTransfer
pack `element-01-mp4`, Flaticon-style animated icons + a white-on-black wireframe loop set). Usage
rights are the user's; they ship here so a job never has to look outside the repo.

| Folder | What | Read |
|---|---|---|
| [`icons/`](icons/README.md) | 164 animated line icons (business, finance, real estate, tech, people), recoloured to the palette with alpha: `on-dark/` (white + cyan) and `on-light/` (near-black + cyan), originals kept | its README + `catalog.json` |
| [`elements/`](elements/README.md) | 34 white-on-black wireframe loops 1920×1080 (grids, contours, waveforms, wireframe objects, code, glitch), audio stripped, plus `make-alpha.sh` for luma-keyed overlays | its README + `catalog.json` |
| [`illustrations/`](illustrations/README.md) | 109 flat-vector cut-outs with alpha (business people, hands, money, metaphors, audiences, empty scene plates), ≤ 2400 px, PNG | its README + `catalog.json` |

**Find by concept:** `python3 assets/motion/find.py <palabras>` searches all three catalogs (Spanish
and English keywords, accent-insensitive) and prints the ready-to-use paths.

**WHAT decides when they appear:** [`presets/instagram/explainer/reference-craft.md`](../../presets/instagram/explainer/reference-craft.md)
(§ 2.4 icons, § 2.6 beds behind the cut-out, § 2.7 screen textures). Long-form may borrow an
element as a punch-cut field, but the default long-form vocabulary is unchanged.

**HOW they enter a comp:** as `<video>` elements with alpha — VP9 webm and ProRes 4444 both
proven to keep their alpha through the `hyperframes@0.8.16` headless render (2026-09-14). Put the
timing (`data-start`/`data-duration`) on the `<video>` OR on a wrapper, never both; GSAP-animate the
wrapper, never the `<video>` itself (`graphics-build` § render gotchas).
