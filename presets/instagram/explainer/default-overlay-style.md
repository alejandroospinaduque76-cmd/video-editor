<!-- ⚠️  BRAND VALUES BELOW ARE PLACEHOLDERS — replace with your own.
     Fill in brand-kit.md and tell Claude "apply my brand kit", or edit the values here directly. -->

# Default Overlay Style — THE default graphics pass (short-form explainer)

**This is what "do a graphics pass" means on a short-form explainer unless you name something
else.** Modern, blue, clean UI cards that pop up **over** the footage. Nothing full-frame. Nothing
bespoke. A ~30-minute pass, not a production.

This preset's own copy of the default overlay language (forked from the long-form one in
`presets/youtube/default/` 2026-08-27 — presets are fully independent, so edits here never touch
long-form). Locked 2026-08-05 after a full-tier job overran (1h40m of full-frame illustrated
collage scenes when the ask was "a couple of overlays, maybe some text").

- Build mechanics + render gotchas: the `graphics-build` skill.
- This doc is the **visual language + the scope contract**. The scope half is the important half.

---

## 🔒 SCOPE — the part that was missing

| | Default (this doc) | Only when you say so |
|---|---|---|
| **Coverage** | overlay cards in the top half, face bottom | full-frame takeovers, background replacement |
| **Count** | **4–7 graphics** for a reel | 15+ |
| **Art** | composed from the 6 templates below | bespoke SVG illustration, characters, props, scenes |
| **Motion** | one in/out per card | per-graphic custom motion systems, tracked/baked paths |
| **Look** | this doc | [`signature-style.md`](signature-style.md) split-frame full plan |
| **Budget** | **~30 min** end to end | as long as it takes |

**Your face is never hidden.** Cards live in the top half above you — if a graphic would cover your
face, it's the wrong graphic. **Zero seconds of full-frame** is the default; any full-frame beat is
a question to ask at plan time (state the total second-count and get a yes), never an assumption.

**If a beat seems to want more than a card can carry, say so in one line and keep it a card.**
Overrunning the scope to make one beat better is the exact failure this doc exists to stop.

---

## 🔒 CONSTANTS

### Colors — DARK blue tech UI
Locked 2026-08-05 on your call ("modern tech UI look, dark blue palette, our dark blue grid
background"). This is the brand's signature grid **inverted to navy** — not the bright frosted
panels of the full-tier signature look.

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#060d24` | deep navy field (full-frame comps only) |
| `--line` | `rgba(74,124,255,0.16)` | grid lines, 100px cells |
| `--royal` | `#1e48ff` | hero accent, meter fills |
| `--sky` | `#57c9f0` | secondary accent, status furniture |
| `--txt` | `#e8f0ff` | primary text — **off-white, never pure `#fff`** |
| `--muted` | `#8fa6d4` | eyebrows, labels, subs |
| `--green` | `#2ff58a` | **reserved** — a genuine "free"/unlocked payoff, nothing else |
| `--red` | `#ff4d5e` | the strike-through / negation accent |

One accent per card. Green is not decoration: it marks the single beat where something is free or
unlocked, the same way yellow is rationed elsewhere in the brand.

### Font — Inter
`assets/fonts/Inter-{Black,Bold,Regular}.otf` → copy into the job's `assets/fonts/` and
`@font-face` (the headless render needs the file embedded, a system name silently falls back).
Headline = Black, mixed case, `letter-spacing:-1.5px`. Eyebrow label = Bold, uppercase, 23px tracking
`+3.4px`, `--muted` (the `.eyebrow` CSS below is the lock). Body = Regular, `--muted`.

### THE panel — one primitive, everything is built from it
A **solid UI surface**, not translucent glass: opaque enough to read over bright studio footage,
with a royal rim + drop shadow so it sits *on* the frame instead of floating in it.
```css
.panel{position:absolute;background:linear-gradient(160deg,#12224e 0%,#0a1435 100%);
  border:2px solid rgba(96,146,255,0.42);border-radius:22px;
  box-shadow:0 26px 60px rgba(2,7,24,0.72), 0 0 0 1px rgba(6,13,36,0.85),
             inset 0 2px 0 rgba(140,180,255,0.22);}
.panel.hi{border-color:rgba(47,245,138,0.55);      /* the payoff state */
  box-shadow:0 26px 60px rgba(2,7,24,0.72), 0 0 44px rgba(47,245,138,0.30);}
.eyebrow{font-weight:700;font-size:23px;letter-spacing:3.4px;text-transform:uppercase;color:var(--muted);}
.head{font-weight:900;letter-spacing:-1.6px;color:var(--txt);line-height:1;}
```
Plus the small furniture that sells "tech panel" rather than "text box": a glowing status `.dot`,
a hairline `.rule`, segmented meters, bar charts. Use one or two, never all of them.

⚠️ **The panel must read on its OWN fill — `backdrop-filter` does nothing here.** These render as
isolated alpha `.mov`s with no backdrop behind them, so a blur-the-background panel comes out
transparent and reads as a floating text ghost over the footage. Opacity in the gradient, never
`backdrop-filter`.

⚠️ **Glow = stacked blurred duplicates, never `text-shadow`.** Four copies of the same text at
falling blur/opacity (56px → 22px → 7px → sharp) is what spills real light onto the frame;
`text-shadow` at any strength stays a flat sticker halo.

### Placement — 9:16, 1080×1920

Cards sit in the **top half** (y 200 → 960), the face stays in the bottom half. The short-form safe
bands are absolute: **nothing key in the top 200 px or bottom 300 px** — face, captions, and every
card stay inside y 200 → 1620 (platform UI + device chrome own those bands). Captions keep their
locked centered zone; a card never collides with them.

Check one frame of the beat before placing — don't guess where your head sits.

---

## 🎨 THE SIX TEMPLATES — compose, never invent

Every graphic is one of these. If a beat doesn't fit one, it probably doesn't need a graphic.

1. **Label card** — eyebrow + 2–5 word headline, one word in `--royal`. The workhorse.
2. **Stat card** — big number (Black, 96px, `--royal`) + a `--muted` label under it.
3. **List card** — eyebrow + **max 3** rows, each a small royal chip/check + 2–4 words. Rows stamp in
   sequence, 4 frames apart.
4. **Compare pair** — two stacked mini-cards, the second with a `--royal` border = the winner.
5. **Label bar** — a name/label bar low in the card zone, slides in from the left edge.
6. **Annotation** — a royal arrow/underline/circle drawn onto something already on screen.

No mascots, no characters, no illustrated scenes, no props, no paper/halftone/collage texture, no
gloss, no 3D, and no glow on a card's TYPE beyond the stacked-duplicate recipe above — type glow is
for a graphic whose SUBJECT emits light (a neon sign, an LED readout, a terminal accent), not for a
card headline. Those are other presets.

## Motion — stepped, one move in, one move out

**Posterized, not smooth** (your call — keep it): every move quantizes onto a 3-frame grid via
`ease: steps(n)` where `n = frames/3`. At ~30fps that reads as ~10fps stepped motion, which is what
stops it looking like a default template fade.

- **In:** fade `0 → 1` + slide 20–28 px, 5–7 frames, stepped.
- **Hold:** static. Sequenced elements stamp 2–6 frames apart, entrance only.
- **Out:** fade `1 → 0` + drift, 6–8 frames, stepped.
- Hard-kill every element at its end (`tl.set('#id',{opacity:0}, end)`) or it pops / lints red.
- One paused GSAP timeline, absolute times, no `Math.random` — deterministic so seeks are frame-exact.
- **Author in frames** (e.g. `F(n) = n*1001/30000` at 29.97), so stamps land on the real frame grid.

⚠️ **Never drive text from a tween's `onUpdate`.** It does not fire on `seek()` of a paused
timeline (measured 2026-08-05: the value interpolates correctly, the callback never runs), and the
renderer advances by seeking frame to frame — so an onUpdate counter renders **frozen on its first
value** while looking perfect in a scrub. Emit counts as discrete `tl.set(sel,{innerText:...})`
calls on the step grid instead, which is the posterized look anyway.

That's the whole motion vocabulary. No tracked paths, no baked per-frame motion, no physics — a
basic pass is *not* where that effort goes.

---

## Build

Same generated-composition mechanics as every other look — a per-job `build.py` under
`projects/<job>/hf-graphics/` emitting one comp per card, rendered to alpha ProRes 4444 and
composited over the reframed 9:16 base. At 4–7 short overlay cards there are **no shared-timeline
chains and no part-splitting**: each card is its own independent comp, so a tweak re-renders one
~2s comp. **Probe the comp in the browser before spending a render** — recipe in the `graphics-build` skill.
