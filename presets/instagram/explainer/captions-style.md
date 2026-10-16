# Caption Style — your LOCKED preset (talking-head explainer captions)

The standard burn-in caption format for **the short-form explainer** (talking-head, graphics top / face bottom).
Locked 2026-06-24 (`your-job` hook v5). Apply verbatim every time — this replaces any
generic HyperFrames caption treatment for this format.

**Render CLI pinned at 0.8.16; re-validate by PNG-sequence A/B before moving the pin**.

Builder: [`presets/instagram/explainer/build.py`](build.py) · Corrections: [`transcript-corrections.json`](../../../transcript-corrections.json)

## 🎨 Per-creator values (v1.3) — read this first

Per-creator values come from the style profile (`python3 workflows/profile.py show`): palabras,
mayúsculas, posición, tamaño, colores, resaltado. The LOCK now protects the mechanics (face law, safe
zones, timing from the canonical transcript, render path), not the look. The numbers under "THE LOOK"
below are this preset's defaults: they apply only to a value the creator has not set (a value still at
`default` in the profile). Precedence: a knob line edited in the job's copy of `build.py` > env
`ANCHOR_Y` (the face-guard-measured placement) > profile > preset value.

Which builder a short-form job uses comes from the profile, `subtitulos.estilo`:
- `caja` → the explainer builder (`presets/instagram/explainer/build.py`, text on a box)
- `borde` → the tiktok/raw builder (`presets/tiktok/raw/build.py`, outlined text, no box)
- `ninguno` → no caption layer at all

Here (`caja`): `subtitulos.color_resaltado` colours the word being spoken (only with `REVEAL = "word"`,
the default); `""` = no highlight.

---

## 🔒 THE LOOK — locked

- **Font:** Inter Bold (`assets/fonts/Inter-Bold.otf`, OFL, @font-face'd into the hf project). *(2026-09-25: replaced Coolvetica, whose Typodermic desktop licence does not allow redistributing the font file inside a kit.)*
- **Box:** solid black `#000`, radius `14px`, padding `14px 24px`. The box **never animates** — hard cut on/off.
- **Text:** white `#fff`, `49px`, letter-spacing `0.5px`, natural case.
- **Position:** dead-centered both axes — vertical center `y960` (exact frame middle / graphics-face seam), horizontally centered.
  **On a job whose brand rules put the captions LOW instead (under the chin, no box — a common
  brand-kit rule), the y is MEASURED, never a remembered number (2026-09-14):** `uv run workflows/face-guard.py
  zones <raw> --from --to` per V1 segment → the caption TOP sits at the lowest `below.y0` + 40 across
  the takes (with `--zoom 1.09` on punch-in beats). The builder anchors the box CENTRE
  (`translate(-50%,-50%)`), so the knob is **`ANCHOR_Y = top + box_h / 2`** (a 2-word 64 px line with
  its padding is ~100 px tall → `ANCHOR_Y = below.y0 + 90`), with `MAX_WORDS = 2` and
  `BOX_COLOR = "transparent"`; `face-guard.py check` then sweeps the rendered caption layer frame by
  frame against the jaw. Even on the split-frame layout the y960 lock and the measured face can
  disagree (hair 50 px under the seam puts the keep-out top ~y910): the gate wins, move the box.
- **Box sizing:** **pre-sized to the full phrase** and held that size — it does NOT grow word-by-word.
- **Animation = words only:** each word pops in (opacity + 6px rise, 0.13s) on its **own word-level timestamp**. On-beat karaoke; the box just sits there and the words appear onto it.
- **Phrasing:** 2–4 words per box, broken on clause/sentence punctuation.

## 🔒 THE TIMING RULE — this is the lock

**Always build captions from the canonical transcribe-once transcript:**
`projects/<job>/outputs/<job>.transcript.json`

That file is WhisperX large-v3 word timings remapped through `cuts.json` — it is the SAME timeline as the
audio that ships, so captions are on-beat **with zero manual nudging**.

- **NEVER** time captions off an ad-hoc/subset transcript (e.g. a `hook.transcript.json`). That is exactly
  what caused the back-half drift on v1–v4: a stale subset had dropped "it works." and compressed the tail,
  so later captions slid in early. The canonical transcript has every word at its true time.
- **Caption over the render that SHIPS** (the final cut or the graphics render of it). Same audio → same
  timeline → guaranteed sync. Verify once with `ffmpeg silencedetect` if you ever suspect drift: the audio's
  silences must line up with the transcript's word gaps.

## 🔧 AUTO-FIX mis-transcribed words

The builder runs every word through [`transcript-corrections.json`](../../../transcript-corrections.json) before captioning
(caption display text only — the source transcript is never touched):
- **`auto`** — silent whole-word fixes: `clod/claud/clawed → Claude`, casing like `anthropic → Anthropic`,
  `chatgpt → ChatGPT`, `ai → AI`, `mcp → MCP`, etc.
- **`flag`** — ambiguous words (`cloud`, `school`) the builder PRINTS so you eyeball them in context that run.
  When a flagged word IS a fix for that video (e.g. "my **school** community" = your **YourBrand**), drop a
  `corrections.local.json` next to `build.py` (`{"auto": {"school": "YourBrand"}}`) — job-local, so the shared map stays conservative.
- **Grow the file** whenever a new mistake shows up. The build log lists every fix it made + every flag to check.

---

## ▶️ Per-job workflow (step 5: the caption layer, on by default)

**Captions are a step-5 graphic (2026-09-04), not a pass.** The builder emits an ALPHA overlay
that the lane's placer lays on the top graphics track like any other graphic; the plan carries the
`captions` cell (`graphics-plan` § The captions cell).

1. Scaffold the comp project: `cd projects/<job>/hf-graphics && HYPERFRAMES_SKIP_SKILLS=1 npx -y hyperframes@0.8.16 init captions --example blank --non-interactive --skip-transcribe`
   (writes `package.json` + `hyperframes.json`; delete the generated `index.html`, `AGENTS.md`, `CLAUDE.md` — `build.py` writes the real `index.html`). A job with an existing comp project (`hf-graphics/gfx/`) can copy those two files instead. Then `mkdir -p assets/fonts renders`, copy in `assets/fonts/Inter-Bold.otf` and
   `presets/instagram/explainer/build.py`. (Durable under the job folder, never `/tmp`.)
2. In `build.py` set the per-job lines: `JOB` (TRANSCRIPT auto-derives) and `HOOK_END_T`
   (`None` = whole video; a number previews just the hook). `ALPHA = True` is the default.
3. `uv run build.py` → writes `index.html`. Read the log: confirm the chunk list, apply any `⚠ REVIEW` flags,
   note the printed `COMP_DUR`.
4. `npx hyperframes@0.8.16 lint` → the render command the build prints:
   `npx hyperframes@0.8.16 render . -c index.html --fps 30 --quality standard --video-frame-format png --format mov --output renders/captions-alpha.mov`.
   Placing the layer is a lane mechanic: [`LANES.md`](../../../LANES.md) § step 5 (Premiere:
   `lanes/premiere/place-graphics.py --plan --write`; chat-only: one more overlay in the assemble).

Preview / burn path (`ALPHA = False`): copy the shipping render into `assets/captions-bg.mp4`, set
`BG`, and render to a flat mp4 — a look check, not the deliverable. The caption box lives on the seam
(y960), inside the short-form safe box (y200→1620).

## Knobs (only if asked to tweak)

`FONT_SIZE` · `UPPERCASE` (→ ALL CAPS) · `BOX_COLOR`/`BOX_RADIUS`/`BOX_PAD` (`"transparent"` = the no-box brand
rule) · `MAX_WORDS` (phrase length) · `ANCHOR_Y` (the box CENTRE; the measured low placement above) ·
`WORD_FADE`/`WORD_RISE` (pop feel) · `REVEAL` (`word` = on-beat karaoke, `phrase` = whole phrase at once).
