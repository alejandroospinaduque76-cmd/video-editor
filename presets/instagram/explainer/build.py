#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///
"""
Caption-style preset builder (talking-head explainer).

Run it from the copy inside the job's hf-graphics/captions project after setting the
per-job block below:  uv run build.py

TIMING SOURCE OF TRUTH: the canonical transcribe-once transcript
(projects/<job>/outputs/<job>.transcript.json) — WhisperX large-v3 word timings
remapped through cuts.json. It is guaranteed to match the rendered audio, so
captions stay on-beat with zero manual adjusting. NEVER time captions off an
ad-hoc subset; that is what caused the back-half drift.

Emits a HyperFrames composition: a black Inter Bold box centered on the
graphics/face seam, pre-sized to each full phrase, words popping in on their own
word-level timestamps. Re-runnable — tweak the STYLE block and re-render.
"""
import json, html, re, math, pathlib, os
import sys
# Windows consoles/pipes default to cp1252, which can't encode the ⚠/→ glyphs in this
# script's status lines: a cosmetic print must never kill a pipeline step (it did once,
# 2026-08-13, mid-splice on a real Windows job). Force UTF-8; no-op on macOS/Linux.
for _s in (sys.stdout, sys.stderr):
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

HERE = pathlib.Path(__file__).parent


def _repo_root():
    """The repo root: the nearest ancestor holding transcript-corrections.json. This file runs from a
    COPY inside the job (projects/<job>/hf-graphics/captions/build.py) as often as from presets/, so a
    fixed parent depth is wrong half the time. Override with VIDEO_EDITOR_REPO."""
    env = os.environ.get("VIDEO_EDITOR_REPO")
    if env:
        return env
    for p in pathlib.Path(__file__).resolve().parents:
        if (p / "transcript-corrections.json").exists() or (p / "presets" / "caption-corrections.json").exists():
            return str(p)
    return str(pathlib.Path(__file__).resolve().parents[3])


REPO = _repo_root()
CORRECTIONS = f"{REPO}/transcript-corrections.json"
if not os.path.exists(CORRECTIONS):   # pre-2026-08-31 location
    CORRECTIONS = f"{REPO}/presets/caption-corrections.json"

# ===== SET PER JOB (the only lines you touch) ==============================
JOB        = f"{REPO}/projects/CHANGE-ME"                                 # the job folder
TRANSCRIPT = f"{JOB}/outputs/{pathlib.Path(JOB).name}.transcript.json"    # canonical source of truth
ALPHA      = True          # True = the step-5 overlay: transparent comp, rendered to renders/captions-alpha.mov
                           #        and placed on the top graphics track like any graphic (2026-09-04)
                           # False = burn onto BG for a flat look-check (the preview path, not the deliverable)
BG         = "assets/captions-bg.mp4"   # ALPHA=False only: the render to preview over, copied into this project
HOOK_END_T = None          # None = caption the WHOLE video; or set seconds to preview just the hook
# ===========================================================================

# ----- the creator's style profile (v1.3) ----------------------------------
# workflows/profile.py holds how THIS creator likes captions. A value feeds a knob below only when the
# creator actually set it (answered, measured on their videos or learned in a review); anything left
# at "default" keeps this preset's own look, so with no profile the output is byte-identical to v1.2.
# Precedence: a knob line edited in the job copy (it no longer calls _pv) > env ANCHOR_Y (the
# face-guard measured placement) > the profile > the preset value. Load failures → preset values.
def _load_profile_captions():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ve_profile", os.path.join(REPO, "workflows", "profile.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        p = mod.load()
        if not p.get("slug"):
            return None, {}
        subs = p["valores"].get("subtitulos", {})
        return p["slug"], {k: v for k, v in subs.items() if f"subtitulos.{k}" in p.get("fuentes", {})}
    except Exception:
        return None, {}


PROFILE_SLUG, PROFILE_CAPS = _load_profile_captions()


def _pv(key, preset, conv=lambda v: v):
    """The profile's subtitulos.<key> when the creator set it, else the preset value."""
    return conv(PROFILE_CAPS[key]) if key in PROFILE_CAPS else preset


# ----- STYLE KNOBS (the locked preset) --------------------------------------
# FONT (2026-09-25): Inter Bold (OFL, bundled). Was Coolvetica — Typodermic's desktop licence
# forbids handing the font file to anyone else or embedding it in software/templates, so it
# cannot ship inside a sold kit. Inter covers every Spanish glyph (á é í ó ú ñ ü ¿ ¡).
FONT_SIZE  = _pv("tamano_px", 49, int)              # px  (profile: subtitulos.tamano_px)
TEXT_COLOR = _pv("color_texto", "#ffffff")           # (profile: subtitulos.color_texto)
BOX_COLOR  = _pv("color_fondo", "#000000")           # (profile: subtitulos.color_fondo)
HIGHLIGHT  = _pv("color_resaltado", None)            # optional: the word being spoken turns this colour
BOX_RADIUS = 14            # px
BOX_PAD    = "14px 24px"
# subtitulos.estilo (v1.3, c3 E2E 2026-09-29): "caja" = this preset's box; "borde" = the same captions with NO box
# and an outline in color_fondo, so a creator who picked the outlined look (onboarding B/C) gets it whichever
# builder the job runs; "ninguno" = no caption layer at all (the builder refuses to write one).
CAPTION_STYLE = _pv("estilo", "caja")
if CAPTION_STYLE == "borde":
    import math as _m
    _r = max(2, round(FONT_SIZE * 0.07))                 # outline ≈ 7% of the font size (3–6 px)
    OUTLINE_CSS = ("\n        text-shadow: " + ", ".join(
        f"{round(_r * _m.cos(a * _m.pi / 8), 1)}px {round(_r * _m.sin(a * _m.pi / 8), 1)}px 0 {BOX_COLOR}"
        for a in range(16)) + ";")
    BOX_BG = "transparent"
else:
    OUTLINE_CSS, BOX_BG = "", BOX_COLOR
ANCHOR_Y   = int(round(float(os.environ.get("ANCHOR_Y") or _pv("posicion_y", 960, lambda f: round(float(f) * 1920)))))
                           # box vertical CENTER (px) = exact frame middle (1920/2). seam=960
                           # (profile: subtitulos.posicion_y × 1920; env ANCHOR_Y = the measured face-guard value wins)
UPPERCASE  = _pv("mayusculas", False, bool)          # natural case for v1 (profile: subtitulos.mayusculas)

TAIL       = 0.50          # s to hold the final phrase after the last word ends

# chunking
MAX_WORDS  = _pv("palabras", 4, int)                 # (profile: subtitulos.palabras)
MAX_CHARS  = 24
# Hard cap checked BEFORE a word is appended (2026-09-25): MAX_CHARS is only tested after the append,
# so a 21-char chunk plus "independientemente" jumped to 40 chars — 1135 px in Inter Bold 49 px, wider
# than the 1080 frame, and the nowrap box cannot wrap. 30 chars ≈ 850 px including padding.
MAX_CHARS_HARD = 30
GAP_BREAK  = 0.45          # pause (s) after a word forces a new chunk

# THE INSTAGRAM SAFE ZONE (reference-craft.md § 0b, the owner's unbreakable rule): every caption line, box included,
# stays inside x 180 → 905, and left of the like / comment column (x 845) once any of it sits below y 826. The line is
# centred on x 540, so the nearer edge caps its half width. MAX_CHARS was tuned on Inter Bold 49 px: at a profile size
# of 72 px the same 24 characters ran past both edges and face-guard failed every caption frame (c3, v1.4 QA,
# 2026-09-29), so a chunk now also breaks on its MEASURED width.
IG_X0, IG_X1, IG_COL_X, IG_COL_Y = 180, 905, 845, 826
_PAD_X = int(BOX_PAD.split()[1].rstrip("px")) if len(BOX_PAD.split()) > 1 else 24
_EDGE = (max(2, round(FONT_SIZE * 0.07)) + 1) if CAPTION_STYLE == "borde" else _PAD_X   # the outline's reach, or the box padding
_HALF_H = FONT_SIZE * 0.52 + (2 if CAPTION_STYLE == "borde" else 14)
_RIGHT = IG_COL_X if ANCHOR_Y + _HALF_H > IG_COL_Y else IG_X1
MAX_LINE_PX = 2 * min(540 - IG_X0, _RIGHT - 540) - 2 * _EDGE


def _measurer():
    try:
        from PIL import ImageFont
        f = ImageFont.truetype(os.path.join(REPO, "assets", "fonts", "Inter-Bold.otf"), FONT_SIZE)
        return f.getlength
    except Exception:   # no Pillow or no font file: Inter Bold's average advance, a little generous
        return lambda s: len(s) * FONT_SIZE * (0.68 if UPPERCASE else 0.60)


_text_w = _measurer()


def line_px(ws):
    """The rendered width of these words on one line: each word's advance plus the 0.5 px letter-spacing per glyph,
    and the 0.30 em gap between words, the way .box and .w + .w lay them out."""
    texts = [(w["text"].upper() if UPPERCASE else w["text"]) for w in ws]
    return sum(_text_w(x) + 0.5 * len(x) for x in texts) + 0.30 * FONT_SIZE * (len(texts) - 1)

# reveal
REVEAL        = "word"     # "word"   = each word pops in on its OWN word-level timestamp (on-beat),
                           #            inside a box PRE-SIZED to the full phrase (box never resizes)
                           # "phrase" = whole phrase pops in together at chunk start (no per-word sync)
if CAPTION_STYLE == "borde":
    # With no box, the line reserved at full width showed its first word left of centre until the rest arrived (c3,
    # v1.4 QA, 2026-09-29): an outlined caption shows its whole phrase at once, centred, like the tiktok/raw builder,
    # and the profile's highlight colour follows the spoken word.
    REVEAL = "phrase"
PHRASE_STAGGER = 0.05      # s between words in "phrase" mode
WORD_FADE  = 0.13          # s per-word fade-in
WORD_RISE  = 6             # px rise
# box itself never animates — hard cut on/off, pre-sized to the full phrase
# ---------------------------------------------------------------------------

# ----- transcription fixes (display text only; source transcript untouched) -
cfg = json.load(open(CORRECTIONS))
AUTO = {k.lower(): v for k, v in cfg.get("auto", {}).items()}
FLAG = {w.lower() for w in cfg.get("flag", [])}
# optional per-job overrides — corrections.local.json next to this build.py, for
# context-specific calls (e.g. "school"→"YourBrand" in THIS video). Keeps the shared map conservative.
_local = HERE / "corrections.local.json"
if _local.exists():
    lc = json.load(open(_local))
    AUTO.update({k.lower(): v for k, v in lc.get("auto", {}).items()})
    FLAG = (FLAG | {w.lower() for w in lc.get("flag", [])}) - set(AUTO)
_split = re.compile(r"^(\W*)(.*?)(\W*)$")  # leading punct / core / trailing punct

def fix_word(text):
    pre, core, post = _split.match(text).groups()
    low = core.lower()
    if low in AUTO:
        return pre + AUTO[low] + post, ("auto", core, AUTO[low])
    if low in FLAG:
        return text, ("flag", core, None)
    return text, None

# Spanish opening marks. 2026-09-25: if the transcriber ever emits "¿"/"¡" (or «) as its
# OWN token, the chunker could end a phrase on it — a lone "¿" at the end of one caption and
# the question in the next. Glue any opener-only token onto the word after it.
OPENERS = "¿¡«“‘(["


def attach_openers(words):
    """Merge tokens made only of opening punctuation into the following word (keeps that
    word's end, takes the opener's start). Pure: returns a new list, input untouched."""
    out, pending = [], None
    for w in words:
        t = w["text"].strip()
        if t and all(c in OPENERS for c in t):
            pending = dict(w) if pending is None else {**pending, "text": pending["text"] + t}
            continue
        if pending is not None:
            w = {**w, "text": pending["text"].strip() + t, "start": pending["start"]}
            pending = None
        out.append(w)
    return out                               # a trailing opener with nothing after is dropped


def caption_lang(transcript):
    """<html lang> for the caption page = the transcript's language (set by export-transcript.py
    from what WhisperX detected). 2026-09-25: was hard-coded "en"; the lang attribute drives
    hyphenation and text-transform casing rules in the browser, so a Spanish video must say es."""
    code = str(transcript.get("language_code") or "en").strip().lower()
    return re.sub(r"[^a-z0-9-]", "", code) or "en"


_transcript = json.load(open(TRANSCRIPT))
LANG = caption_lang(_transcript)
words = _transcript["words"]
words = [w for w in words if w.get("type", "word") == "word" and w["text"].strip()]
words = attach_openers(words)
if HOOK_END_T is not None:
    words = [w for w in words if w["start"] < HOOK_END_T]

fixes, flags = [], []
for w in words:
    new, note = fix_word(w["text"])
    if note and note[0] == "auto":
        if new != w["text"]:            # 2026-09-25: a no-op (AI→AI) is not a fix — don't report it
            fixes.append((note[1], note[2])); w["text"] = new
    elif note and note[0] == "flag":
        flags.append(note[1])

COMP_DUR = round(words[-1]["end"] + TAIL, 2)

# group into chunks — respect clause/sentence punctuation so phrases read naturally
wide = []   # single words wider than the safe line on their own: said, since no break can fix them


def chunk_words(words):
    chunks, cur = [], []
    for i, w in enumerate(words):
        if cur and (sum(len(x["text"]) for x in cur) + len(cur) + len(w["text"]) > MAX_CHARS_HARD
                    or line_px(cur + [w]) > MAX_LINE_PX):
            chunks.append(cur); cur = []
        if line_px([w]) > MAX_LINE_PX:
            wide.append(w["text"])
        cur.append(w)
        t = w["text"].rstrip()
        chars = sum(len(x["text"]) for x in cur) + (len(cur) - 1)
        gap_next = (words[i + 1]["start"] - w["end"]) if i + 1 < len(words) else 99
        ends_sentence = t.endswith((".", "!", "?", "…"))
        ends_clause = t.endswith((",", ":", ";"))
        brk = (
            ends_sentence
            or (ends_clause and len(cur) >= 2)
            or len(cur) >= MAX_WORDS
            or chars >= MAX_CHARS
            or gap_next > GAP_BREAK
        )
        if brk:
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    return chunks


chunks = chunk_words(words)

# build markup + timeline
caps_html, tl_js = [], []
for ci, ch in enumerate(chunks):
    start = ch[0]["start"]
    nxt = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else COMP_DUR
    wspans = "".join(
        f'<span class="w" id="c{ci}w{wi}">{html.escape(w["text"])}</span>'
        for wi, w in enumerate(ch)
    )
    caps_html.append(f'<div class="cap" id="c{ci}"><div class="box">{wspans}</div></div>')
    # box: NO animation — hard ON at chunk start, hard OFF at next chunk (seek-safe)
    tl_js.append(f'tl.set("#c{ci}",{{opacity:1}},{start:.3f});')
    for wi, w in enumerate(ch):
        at = (start + wi * PHRASE_STAGGER) if REVEAL == "phrase" else w["start"]
        # words always occupy layout, so the box is pre-sized to the FULL phrase and
        # never resizes; each word just pops in (opacity + rise) on its own timestamp
        tl_js.append(
            f'tl.fromTo("#c{ci}w{wi} ",{{opacity:0,y:{WORD_RISE}}},'
            f'{{opacity:1,y:0,duration:{WORD_FADE},ease:"power2.out"}},{at:.3f});'
        )
    if HIGHLIGHT:
        # profile subtitulos.color_resaltado: the spoken word takes the colour until the next word starts
        for wi, w in enumerate(ch):
            off = ch[wi + 1]["start"] if wi + 1 < len(ch) else nxt
            tl_js.append(f'tl.set("#c{ci}w{wi}",{{color:"{HIGHLIGHT}"}},{w["start"]:.3f});')
            tl_js.append(f'tl.set("#c{ci}w{wi}",{{color:"{TEXT_COLOR}"}},{off:.3f});')
    tl_js.append(f'tl.set("#c{ci}",{{opacity:0}},{nxt:.3f});')  # hard-kill, seek-safe

transform = "uppercase" if UPPERCASE else "none"
word_default_display = "inline-block"  # words always reserve space → box = full phrase width
caps_block = "\n        ".join(caps_html)
tl_block = "\n      ".join(tl_js)
body_bg = "transparent" if ALPHA else "#000"
bg_layers = "" if ALPHA else (
    f'<video id="bg" class="clip" src="{BG}" data-start="0" data-duration="{COMP_DUR}" data-track-index="0" muted playsinline></video>\n'
    f'      <audio id="bg-audio" src="{BG}" data-start="0" data-duration="{COMP_DUR}" data-track-index="10" data-volume="1"></audio>')

HTML = f"""<!doctype html>
<html lang="{LANG}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Inter"; src: url("assets/fonts/Inter-Bold.otf") format("opentype"); font-weight: 700; font-display: block; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: {body_bg}; }}

      /* caption rail — dead-centered (h + v) on the frame middle / graphics-face seam */
      .cap {{
        position: absolute; left: 540px; top: {ANCHOR_Y}px;
        transform: translate(-50%, -50%);
        opacity: 0; width: 1000px; text-align: center; pointer-events: none;
      }}
      .box {{
        display: inline-block; max-width: 1000px;
        background: {BOX_BG}; border-radius: {BOX_RADIUS}px;
        padding: {BOX_PAD};
        font-family: "Inter", sans-serif; font-weight: 700;
        font-size: {FONT_SIZE}px; line-height: 1.04; letter-spacing: 0.5px;
        color: {TEXT_COLOR}; text-transform: {transform};
        white-space: nowrap;{OUTLINE_CSS}
      }}
      .w {{ display: {word_default_display}; opacity: 0; }}
      .w + .w {{ margin-left: 0.30em; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{COMP_DUR}" data-width="1080" data-height="1920" style="position: relative; width: 1080px; height: 1920px; overflow: hidden;">
      {bg_layers}

      <section id="captions" class="clip" data-start="0" data-duration="{COMP_DUR}" data-track-index="1">
        {caps_block}
      </section>
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {tl_block}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""

if CAPTION_STYLE == "ninguno":
    # a creator's choice, not a failure: exit 0 so nothing reports "build failed" (reviewer C2, 2026-09-29)
    print("[captions] the creator's style profile says no captions (subtitulos.estilo = ninguno): "
          "no caption layer written. Leave the captions cell out of the plan.")
    sys.exit(0)
(HERE / "index.html").write_text(HTML)

# report
print(f"source: {pathlib.Path(TRANSCRIPT).name}  |  COMP_DUR={COMP_DUR}s  (bg must be >= this)")
if PROFILE_SLUG:
    print(f"profile {PROFILE_SLUG}: {', '.join(f'{k}={v}' for k, v in sorted(PROFILE_CAPS.items())) or '(no caption values set)'}"
          f"  →  FONT_SIZE={FONT_SIZE} MAX_WORDS={MAX_WORDS} UPPERCASE={UPPERCASE} ANCHOR_Y={ANCHOR_Y} "
          f"STYLE={CAPTION_STYLE} TEXT={TEXT_COLOR} BOX={BOX_COLOR}{' HIGHLIGHT=' + HIGHLIGHT if HIGHLIGHT else ''}")
if fixes:
    print("auto-fixed:", ", ".join(f"{a}→{b}" for a, b in fixes))
else:
    print("auto-fixed: (none)")
if flags:
    print("⚠ REVIEW these in context:", ", ".join(sorted(set(flags))))
print(f"chunks: {len(chunks)}  (lines ≤ {MAX_LINE_PX} px wide: the Instagram safe zone at y {ANCHOR_Y})")
if wide:
    print(f"⚠ wider than the safe line on their own at {FONT_SIZE} px: {', '.join(sorted(set(wide)))} "
          "— lower subtitulos.tamano_px, or check face-guard's zone verdict on those frames")
for ci, ch in enumerate(chunks):
    print(f"  {ci:2d} [{ch[0]['start']:5.2f}] " + " ".join(w["text"] for w in ch))
print("wrote index.html")
if ALPHA:
    print("render (the step-5 overlay, straight alpha):\n  npx hyperframes@0.8.16 render . -c index.html --fps 30 --quality standard "
          "--video-frame-format png --format mov --output renders/captions-alpha.mov")
else:
    print(f"render (flat preview over {BG}):\n  npx hyperframes@0.8.16 render . -c index.html --fps 30 --quality standard --output renders/captions-preview.mp4")
