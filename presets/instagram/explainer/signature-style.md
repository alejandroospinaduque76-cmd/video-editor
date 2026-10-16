<!-- ⚠️  BRAND VALUES BELOW ARE PLACEHOLDERS — replace with your own.
     Fill in brand-kit.md and tell Claude "apply my brand kit", or edit the values here directly. -->

# Signature Style — your brand SYSTEM (not a rigid template)

The look for **the short-form explainer** (talking-head) hooks/graphics.
**Philosophy:** the brand CONSTANTS below are locked — apply them verbatim every time. The LAYOUT is not.
Each graphic should be **designed fresh** with discretion: vary alignment, scale, emphasis, word grouping,
and motion so no two feel stamped from the same mold. Dynamic > rigid. Make it genuinely well-designed.
Locked 2026-06-24 (`your-job` hook-v5).

---

## 🔒 CONSTANTS — never change these

### Colors
| Token | Hex | Use |
|-------|-----|-----|
| `--sky`    | `#ddf4ff` | background base (the one constant) |
| `--grid`   | `#74dff6` | grid lines, super-thin (1px) |
| `--royal`  | `#1e48ff` | electric blue — the hero accent |
| `--peri`   | `#879cff` | periwinkle — secondary accent (gradients/decorative; low-contrast, never small text) |
| `--ink`    | `#0a1a4d` | deep navy — primary title text (added 2026-06-24 for two-tone hierarchy) |
| `--slate`  | `#5e687d` | muted subhead text |

### Fonts — Inter
Files at `assets/fonts/Inter-{Black,Bold,Regular}.otf` → copy into each hf project's `assets/fonts/` and `@font-face` them (headless render needs the file embedded).
- **Titles** → Inter Black. **Mixed case / title case — NOT all caps.** `letter-spacing: -2px`, tight `line-height` (~0.95–1.0).
- **Headings / eyebrow labels** → Inter Bold. (Small eyebrow *labels* may stay uppercase — that's a label, not a title.)
- **Subtitles** → Inter Regular, sentence case, color `--slate`.
- Inter Black is WIDE. Re-measure the longest title word (PIL `ImageFont.getlength`) before sizing — on a 1080px frame w/ 72px padding (936px usable), a mixed-case ~9-char word maxes ~200px; stacked titles sit comfortably ~150–170px.

### Signature background — "A · Spotlight"
`#ddf4ff` base + thin `#74dff6` grid + soft white center glow. Reuse for ANY background:
```css
background:
  radial-gradient(120% 78% at 42% 36%, rgba(255,255,255,0.72), rgba(255,255,255,0) 70%),
  linear-gradient(rgba(116,223,246,0.55) 1px, transparent 1px) 0 0 / 100px 100px,
  linear-gradient(90deg, rgba(116,223,246,0.55) 1px, transparent 1px) 0 0 / 100px 100px,
  #ddf4ff;
```
Grid cell `100px` per 1080px width (scale with frame). Move the glow to sit behind the focal text.

### Layout frame (the explainer layout frame)
1080×1920. Top half (0→960) = graphic panel, bottom half (960→1920) = talking head (`object-fit: cover`). The two halves meet at the 960px split with a clean hard edge — **no divider line** (removed 2026-06-24; the old glowing royal→peri seam is retired, don't add it back).

**The face anchor is MEASURED, not eyeballed — this doc owns the number.** The head sits so its median hair top lands **50 px below** the y960 seam; if a shoot defeats the hair-top measurement, fall back to putting the face-box centre at y1385. Both come from the footage, never from a guess: `uv run workflows/face-frame.py <base-cut>` prints the `#head` `object-position` to paste in, and `uv run workflows/face-frame.py <base-cut> --verify <draft>` must **PASS** before the draft goes to review.

---

## 🎨 DESIGN TOOLBOX — mix, don't repeat

Compose each graphic from these motifs; pick what fits the words, vary it piece to piece:
- **Two-tone title** — most words in `--ink` navy, ONE hero word emphasized. Hierarchy beats a wall of one color.
- **Hero-word treatments** (rotate which you use): boxed chip (white text on a `--royal` rounded box, slight `-2.5deg` rotation, soft shadow); or `--royal` fill; or a periwinkle highlighter swipe behind it; or an underline swoosh.
- **Eyebrow as a pill/chip** — translucent white bg, thin royal border, icon + label. Cleaner than loose text.
- **Asymmetry** — left-aligned editorial blocks read more dynamic than dead-center stacks. Vary it.
- **Subhead emphasis** — bold a key phrase in `--royal` to tie back to brand.
- **Motion = entrance, seek-safe, deterministic** (single paused GSAP timeline): chip stamps in (`back.out`), title words rise from a `overflow:hidden` clip mask (stagger), hero word stamps/rotates in, subhead fades up, divider glows in, white `#glow` breathes (yoyo). No `Math.random`. Let GSAP own transforms (CSS transform gets absorbed — see project Lab Notes).

## Reference implementation
No sample project ships — author the hook hf project fresh under `projects/<job>/hf-hook/` from the DESIGN TOOLBOX above: markup + CSS + a single paused GSAP timeline. Re-measure the longest title word, then render.
