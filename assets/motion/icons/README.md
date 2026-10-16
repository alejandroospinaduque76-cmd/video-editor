# assets/motion/icons/ — 165 animated line icons, recoloured to the palette, with alpha

The user's icon pack (Flaticon-style animated line icons, 512×512, 1–4 s, 25/30/60 fps; business,
finance, real estate, tech, people; Spanish file names). **These replace emojis for good** — every
concrete noun in a reel that has no real logo gets one of these (the WHAT:
[`reference-craft.md`](../../../presets/instagram/explainer/reference-craft.md) § 2.4).

| Folder | What | Use it |
|---|---|---|
| `on-dark/<slug>.webm` | **white** strokes + brand cyan `#46D5FF` accents, VP9 alpha (`yuva420p`) | inside comps on navy panels or straight over footage — the default |
| `on-light/<slug>.webm` | **near-black `#080A14`** strokes + brand cyan, VP9 alpha | inside comps on white / light cards |
| `original/<slug>.mp4` | the pack as delivered: black + `#33cbca` on white, no alpha | reference only; never on a timeline as-is |
| `catalog.json` | slug · original name · duration · fps · keywords (es + en) | `python3 assets/motion/find.py <palabra>` |

Recolour is exact, not approximate: the source is three flat colours (white bg, `#000` stroke,
`#33cbca` accent), so alpha = distance-to-white, accent pixels → the brand cyan, everything else →
the stroke colour (`geq`, straight alpha, anti-aliased edges kept). `crecimiento.gif` in the pack is
a duplicate of `crecimiento.mp4` and was skipped.

## In an HTML comp (the normal path)

```html
<div class="w" id="ic1"><video src="assets/icons/dinero.webm" data-start="0.42" data-duration="2.4" muted playsinline></video></div>
<script> pop('#ic1', 0.42); /* the WRAPPER pops; the <video> itself is never GSAP-transformed */ </script>
```

Copy the needed `.webm` into the job's `hf-graphics/gfx/assets/icons/` (comps resolve assets
under the gfx root). Proven on `hyperframes@0.8.16` (2026-09-14): the alpha survives the headless
render, a `data-start` later than 0 seeks correctly, and a scale tween on the wrapper composes with
it. Two rules from the engine's own lint: timing (`data-start`/`data-duration`) goes on the
`<video>` **or** on a wrapper, never both; GSAP animates the wrapper, never the `<video>`.

The icon plays ONCE from its `data-start` (its last frame is the rest pose, so a clip longer than
the source simply holds it). Size 220–360 px free-standing; 200 px inside a 300 px navy tile.

## Hand placement on an app timeline

```bash
./assets/motion/icons/make-prores.sh dinero projects/<job>/hf-graphics/gfx/renders [on-dark|on-light] [fps]
```
→ `icon-dinero-on-dark.mov`, ProRes 4444 straight alpha at the timeline rate, placed like any
overlay (`place-graphics.py` on Premiere; premultiply first on CapCut).

## ⚠ ffmpeg gotcha — decode these webms with `-c:v libvpx-vp9` on the INPUT

ffmpeg's native `vp9` decoder ignores the alpha plane (`alpha_mode=1` is only a tag to it), and an
input-side `-ss` on a VP9-alpha file returns frames with no alpha at all. Every ffmpeg command that
reads one of these must put `-c:v libvpx-vp9` before `-i`, and seek with `-ss` **after** `-i` (or
`select=`). Both scripts here do; a contact sheet that shows blank tiles is this bug, not a broken file.
