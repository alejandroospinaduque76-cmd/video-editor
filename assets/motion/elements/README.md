# assets/motion/elements/ — the wireframe motion beds (34 loops)

Thirty-four **white-on-black tech loops** at 1920×1080 · 29.97 fps · 3.3–7 s · h264, audio
stripped (the pack shipped a −91 dB silent track). They are the visual **texture layer** of the
short-form look: grids, contour lines, wireframe objects, waveforms, code typing, glitch. All
monochrome by design — colour comes from the comp (tint) or from what they sit behind.

Catalog: [`catalog.json`](catalog.json) — one row per file with `desc_es`, `keywords`,
`seamless_loop`, `black_lead_frames` / `black_tail_frames` (most files end on 1–2 black frames:
**trim those off** or the loop pops), and `coverage` (`sparse` = a thin figure on black, `full` =
bright texture across the whole frame).

## The three ways they are used (the WHAT — `presets/instagram/explainer/reference-craft.md`)

| Use | Mechanics | When |
|---|---|---|
| **Bed behind the cut-out person** | opaque mp4 on V3, the MediaPipe cut-out of the speaker on V4 (the `example-reel` recipe: `hf-graphics/cutout/`) | the "algo pasa detrás de él" beat: the room is replaced by the wireframe world for 2–4 s |
| **Screen overlay on the footage** | luma-keyed alpha version over V1 (below) — white lines on the room, the room stays | a texture beat, a "tech" accent, a transition bridge; opacity 0.35–0.7, never on the face |
| **Field of a full-screen graphic** | `<video>` inside the comp under the panel, opacity 0.25–0.5 | a punch-cut / listicle / logo-wall background instead of a flat navy field |

A bed **tinted to the palette** is one `colorchannelmixer` away: white → cyan `#46D5FF` is
`-vf "colorchannelmixer=rr=0.275:gg=0.835:bb=1"`, white → blue `#1B35D0` is
`rr=0.106:gg=0.208:bb=0.816`. Tint sparingly — the white-on-navy contrast IS the look; tint one
layer when two beds stack.

## Alpha versions are derived on demand, never shipped (34 × ~60 MB of ProRes is 2 GB)

```bash
# Premiere-ready overlay (ProRes 4444, straight alpha = luma, white lines) into the job:
./assets/motion/elements/make-alpha.sh el-28 projects/<job>/hf-graphics/beds            # white
./assets/motion/elements/make-alpha.sh el-28 projects/<job>/hf-graphics/beds 46D5FF     # tinted
# Comp-side (<video> inside an HTML comp): the same script with FORMAT=webm writes a VP9 alpha webm
FORMAT=webm ./assets/motion/elements/make-alpha.sh el-28 projects/<job>/hf-graphics/gfx/assets
```

The script trims the catalogued black tail frames, so the file loops cleanly when the timeline
clip is longer than the source (loop it by laying the clip twice; `seamless_loop:false` files
are the build-in kind — ripple, hand, code typing — and are played ONCE from their first frame).

## Pairing rules (learned on the competitor set, 2026-09-14)

- **One bed per beat, never two textures fighting.** `full` coverage beds (contour rings, topo
  flow, glitch bars, mountain band) carry a whole beat on their own; `sparse` ones (a globe, a
  torus, a waveform line) sit behind a panel or a cut-out as a single prop.
- **Match the noun.** Code typing under "programar / agente / Claude Code"; globe under "el
  mundo / global"; waveform under "voz / audio / podcast"; number ticker under "datos / cálculo";
  wireframe human under "cliente / persona / avatar"; glitch bars ONLY on a break or a "no".
- **Motion is continuous; the entrance is the registry's.** The bed itself never fades in over
  more than 4 frames — cut in with the beat, `riseOut`/cut out with it. What animates IN is the
  panel or cut-out on top, from `hf-anim.js`.
- **Never over the face.** As a screen overlay the mask is the top half (y 200 → 960) or a
  feathered vignette that keeps the face clear; as a bed behind the cut-out, the face is by
  definition in front.
