# The design skills — what they add to a comp, and what our locks override (2026-09-15)

Three third-party design skills are installed (`npx skills add Leonxlnx/taste-skill`, `npx skills add
pbakaus/impeccable`, `npx claude-code-templates --skill creative-design/ui-ux-pro-max`; the user asked
for them "para mejorar los diseños y animaciones en los videos"). They were written for **web
interfaces**, and our graphics are HTML/CSS/GSAP comps rendered to video — so their craft transfers,
their product mechanics do not. This sheet is the bridge: read it at **`graphics-build` Stage 3**
before authoring a comp, and at **`edit-review`** as a critique lens.

## What to read, when

| Moment | Read | For |
|---|---|---|
| before authoring ANY comp | [`.agents/skills/impeccable/reference/craft-floor.md`](../../../.agents/skills/impeccable/reference/craft-floor.md) (50 lines) | the quality floor and the bans — the single most useful file |
| a comp with motion beyond the registry's entrance (a reveal, a scene, a cutaway) | [`.agents/skills/impeccable/reference/animate.md`](../../../.agents/skills/impeccable/reference/animate.md) | the motion thesis: ONE focal moment, material by meaning, timing by consequence |
| a comp whose type carries the beat (headline, stamp, figure) | `.agents/skills/design-taste-frontend/SKILL.md` § 4.1 Typography, § 4.2 Color, § 4.4 Materiality, § 4.7 (eyebrow restraint, hero stack) | the bias corrections |
| a graphic that lays out several elements (list, row of tiles, set) | `impeccable/reference/layout.md` | spacing rhythm and hierarchy |
| reviewing a placed draft (edit-review) | `impeccable/reference/critique.md` (heuristics) + craft-floor § Refuse | a defect list, never taste |

Do NOT run `impeccable context`, `init`, `document`, the detector hook or `live`: they expect a web
project (PRODUCT.md / DESIGN.md / a running app) and a downloaded binary. Our "DESIGN.md" is the preset
(`presets/<platform>/<preset>/*.md`) and `brand-kit.md`. `ui-ux-pro-max`'s search CLI
(`python3 .claude/skills/ui-ux-pro-max/scripts/search.py`) is for choosing palettes/fonts/styles — ours
are locked, so it is a reference for *reasoning* (its `ux-guidelines.csv`, `ui-reasoning.csv`), not a
picker.

## What transfers to a comp (apply)

- **Contrast is measured**: text ≥ 4.5:1 against what is UNDER it — on footage that means the ink
  shadow / stacked-duplicate glow, never bare type; secondary text tinted from the accent, never gray.
- **Depth = offset + soft blur** (`0 22px 50px` is right; a zero-offset colored halo is decoration).
  **Declare elevation once** — a panel is a border OR a shadow; a 1px border under a wide shadow is
  the "ghost card". Our `.panel` keeps its 2px rim as a deliberate rim, not a ghost.
- **One radius scale per job** (shape-consistency lock): pick 16 / 24 / 32 and stick to it across
  chips, tiles, panels. Mixed radii on one reel read as assembled, not designed.
- **Tracking floor −0.04em; −0.02 to −0.03 usually reads better.** Display type is decisive contrast
  in size and weight, not a wall of one size.
- **Emphasis = the SAME family in bold/italic or the accent colour** — never a random serif word inside
  a sans line (our two families are a SYSTEM: Playfair Display carries titles, Public Sans carries labels,
  chips, captions; they do not mix inside one line).
- **Eyebrow restraint**: a small uppercase label above a heading is the #1 AI tell. A spoken word
  above a title ("Existe" over `arena.ai`) is copy, and it is set at copy size (≥ 54 px, § tamaño
  mínimo); a decorative eyebrow is dropped — the heading speaks.
- **Hero stack discipline, scaled to a graphic**: ≤ 2 text elements per graphic (the title and ONE
  figure/label). The third thing is a second graphic or nothing.
- **One authored motion moment per graphic**: the entrance is the registry's (`hf-anim.js` — the
  numbers are locked), so the authored moment is what the graphic DOES while it holds: a count-up,
  a state change on the word, a draw-on, a flow. Not one identical entrance on every element, not
  scattered effects. **Exit faster than entrance** (registry: riseOut 0.35 < riseIn 0.55 ✓). No
  bounce or elastic by reflex.
- **Material by meaning**: reveal = mask / clip-path; focus and depth = bounded blur, shadow, light;
  continuity = shared movement. Blur/filter tweens stay numeric (opacity on a scrim, never a CSS
  `filter` string tween — the render gotcha in `graphics-build`).
- **Real illustration or none**: our icons are the drawn line library (`assets/motion/icons/`), our
  props are solid vector fills; no sketch-style SVG scenes, no emoji, no unicode glyphs as icons.
- **Backgrounds are surfaces**: a two-axis grid needs a canvas under it (the cutaway PLATE, a set)
  — over live footage it is the default the floor refuses, which is why `texture` (§ 2.7) is 0–1 per
  reel and always masked off the face.
- **Anti-default discipline**: no AI-purple gradients, no gradient text, no glass-blur decoration, no
  colored `border-left` bars, no hard offset block shadows, no monospace as a "tech" costume.

## What our locks override (ignore in the skills)

- **Palette and fonts**: the user's (cyan `#46D5FF` / blue `#1B35D0` / navy `#1E2A47` / `#131A2E` /
  `#080A14` / white; Playfair Display + Public Sans). The skills' palette/pairing pickers, "Inter discouraged",
  "serif discouraged", "rotate the serif pool" do not apply — the brief wins, and impeccable says so
  itself ("Honor pinned aesthetics… even when they conflict").
- **Motion numbers**: `presets/youtube/default/animations.md` (the registry) and `creative-moves.md`
  own durations and eases; the skills' 150–300 ms micro-interaction table is for UI state changes,
  not entrances on a timeline.
- **The face law and the safe bands** (`reference-craft.md` § 0): geometry is measured on the footage;
  no skill's layout rule moves an element onto the face or into y < 200 / y > 1620.
- **Web-only sections**: accessibility/focus/touch targets, responsive collapse, dark-mode protocol,
  reduced motion, scroll-driven motion, CTAs/forms/nav/bento, loading/empty/error states, browser
  surfaces, DOM cost, i18n. A comp has none of these.
- **Anti-center bias**: a 9:16 reel graphic is centred on the head axis by default (the message IS
  the design — the skill's own override); asymmetry is a choice inside the `above` zone, not a rule.

## The bundle

`Leonxlnx/taste-skill` installs 13 skills, not one. Useful here: `design-taste-frontend`,
`high-end-visual-design`, `gpt-taste` (GSAP motion), `minimalist-ui`. Web/image-only and inert for
video: `brandkit`, `image-to-code`, `imagegen-frontend-*`, `stitch-design-taste`,
`industrial-brutalist-ui`, `redesign-existing-projects`, `full-output-enforcement`,
`design-taste-frontend-v1`. They live in `.agents/skills/` (symlinked into `.claude/skills/`);
remove one with `npx skills remove <name>`. `ui-ux-pro-max` lives in `.claude/skills/` directly
(its installer is `claude-code-templates`, not the skills CLI, so `skills-lock.json` does not track it).
