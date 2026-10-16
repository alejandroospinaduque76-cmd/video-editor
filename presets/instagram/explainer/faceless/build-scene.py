#!/usr/bin/env python3
"""build-scene.py — the FACELESS scene emitter (presets/instagram/explainer/faceless-mode.md).

A faceless reel is the speaker's own voice with NO face: every beat is a full-frame scene on ONE plate
that ENACTS what is being said (a value counts, icons stack up, a line draws, a ring splits, a timeline
extends, a flow runs), every reveal cued to the spoken word. This emitter turns the plan's scene specs
into HyperFrames comps on the shared plate, using the animation registry (hf-anim.js) and the motion
library (assets/motion/icons, elements) — so a faceless reel is a storyboard, not a hand build.

  uv run presets/instagram/explainer/faceless/build-scene.py projects/<job>              # every scene in hf-graphics/scenes.json
  uv run presets/instagram/explainer/faceless/build-scene.py projects/<job> --ids s2,s3  # a subset
  uv run presets/instagram/explainer/faceless/build-scene.py projects/<job> --render     # + GRAIN=0 render.sh <id> full per scene

hf-graphics/scenes.json:
  { "fps": "30000/1001", "caption_top": 1497,            # the reel's measured caption line (face-guard zones on the face takes, or 1497)
    "scenes": [ { "id": "s1", "pattern": "stack", "start": 0.0, "end": 3.70,
                  "figure": {"text": "TODOS LOS MODELOS", "sub": "de IA", "at": 2.24},   # optional, top third
                  "items": [ {"logo": "ai/openai-white.svg", "at": 1.52}, {"icon": "idea", "at": 2.58} ] }, … ] }
  `at` values are TIMELINE seconds (the transcript's word starts − 0.08); the emitter makes them comp-relative.
  Patterns and their slots: counter · stack · line · donut · timeline · list · flow · type (below, per class).

Output: hf-graphics/gfx/compositions/<id>.html (+ the icon/logo/bed/font assets it needs under gfx/assets/),
one comp per scene, every reveal a registry call, the zero frame pinned, the plate identical in every scene so
scene-to-scene hard cuts read as one continuous world. Render opaque: `GRAIN=0 ./render.sh <id> full` in gfx/.
"""
import argparse, json, os, shutil, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))   # faceless/ → explainer/ → instagram/ → presets/ → repo
ICONS = os.path.join(REPO, "assets", "motion", "icons", "on-dark")
LOGOS = os.path.join(REPO, "assets", "logos")
BED = os.path.join(REPO, "assets", "motion", "elements", "el-02-grid-warp.mp4")
# 2026-09-25: the display serif is Playfair Display (OFL, bundled) — Georgia is a Microsoft font
# whose licence forbids shipping the .ttf inside a sold kit, so it was removed from assets/fonts.
FONTS = {"PublicSans-Black.otf": 900, "PublicSans-SemiBold.otf": 600, "PlayfairDisplay-VF.ttf": 700}
W, H = 1080, 1920
CYAN, BLUE, NAVY, NAVY2, INK, WHITE = "#46D5FF", "#1B35D0", "#1E2A47", "#131A2E", "#080A14", "#ffffff"
SEG_COLORS = [CYAN, BLUE, "#5f6d8a", WHITE]                 # donut segment palette, in order

CSS = f"""
@font-face{{font-family:"Public Sans";src:url("assets/fonts/PublicSans-Black.otf") format("opentype");font-weight:900;}}
@font-face{{font-family:"Public Sans";src:url("assets/fonts/PublicSans-SemiBold.otf") format("opentype");font-weight:600;}}
@font-face{{font-family:"Playfair Display";src:url("assets/fonts/PlayfairDisplay-VF.ttf") format("truetype");font-weight:400 900;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
:root{{--cyan:{CYAN};--blue:{BLUE};--navy:{NAVY};--navy2:{NAVY2};--ink:{INK};--w:{WHITE};}}
#root{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:var(--navy2);}}
#grid{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover;opacity:0.12;}}
#vig{{position:absolute;inset:0;background:radial-gradient(ellipse 78% 60% at 50% 48%, rgba(19,26,46,0) 40%, rgba(8,10,20,0.85) 100%);}}
#float{{position:absolute;inset:0;will-change:transform;}}
.fig{{position:absolute;left:60px;top:300px;width:960px;text-align:center;font-family:"Public Sans",sans-serif;font-weight:900;font-size:136px;line-height:1;color:var(--w);text-shadow:0 4px 0 var(--ink),0 12px 30px rgba(8,10,20,.7);opacity:0;will-change:transform,opacity;letter-spacing:-2px;}}
.fig small{{display:block;font-size:44px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:var(--cyan);margin-top:16px;}}
.fig .cy{{color:var(--cyan);}}
.ic{{position:absolute;opacity:0;will-change:transform,opacity;display:flex;align-items:center;justify-content:center;}}
.ic video{{width:100%;height:100%;}}
.tile{{position:absolute;border-radius:32px;background:linear-gradient(165deg,var(--navy),var(--navy2));border:2px solid rgba(70,213,255,.55);box-shadow:0 22px 50px rgba(8,10,20,.7);display:flex;align-items:center;justify-content:center;opacity:0;will-change:transform,opacity;}}
.tile img{{width:52%;height:52%;object-fit:contain;}}
.tile.brand{{border:0;}}
.lbl{{position:absolute;text-align:center;font-family:"Public Sans",sans-serif;font-weight:600;font-size:40px;color:var(--w);opacity:0;will-change:transform,opacity;text-shadow:0 3px 0 var(--ink),0 10px 24px rgba(8,10,20,.6);}}
.chip{{position:absolute;left:50%;transform:translateX(-50%);padding:14px 30px;border-radius:16px;background:var(--cyan);color:var(--ink);font-family:"Public Sans",sans-serif;font-weight:900;font-size:60px;line-height:1.1;white-space:nowrap;opacity:0;box-shadow:0 0 34px rgba(70,213,255,.55);will-change:transform,opacity;}}
.dot{{position:absolute;width:14px;height:14px;border-radius:50%;background:var(--cyan);opacity:0;box-shadow:0 0 14px rgba(70,213,255,0.9);}}
.row{{position:absolute;left:120px;width:840px;height:118px;display:flex;align-items:center;gap:28px;opacity:0;will-change:transform,opacity;}}
.row .ri{{width:96px;height:96px;flex:0 0 96px;}} .row .ri video{{width:96px;height:96px;}}
.row .rt{{font-family:"Public Sans",sans-serif;font-weight:900;font-size:56px;color:var(--w);line-height:1.05;text-shadow:0 3px 0 var(--ink),0 10px 24px rgba(8,10,20,.6);}}
.word{{position:absolute;left:60px;width:960px;top:0;text-align:center;font-family:"Playfair Display",Georgia,serif;font-weight:700;font-size:150px;line-height:1.02;color:var(--w);text-shadow:0 4px 0 var(--ink),0 14px 34px rgba(8,10,20,.75);opacity:0;will-change:transform,opacity;}}
svg .axis{{stroke:rgba(255,255,255,.35);stroke-width:3;}}
svg .line{{fill:none;stroke:var(--cyan);stroke-width:12;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 14px rgba(70,213,255,.7));}}
svg .seg{{fill:none;stroke-width:110;}}
svg .brk{{stroke:var(--w);stroke-width:6;stroke-linecap:round;}}
"""


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fig_html(fig, top=300):
    if not fig: return ""
    txt = esc(fig["text"])
    if fig.get("hero"): txt = txt.replace(esc(fig["hero"]), f'<span class="cy">{esc(fig["hero"])}</span>', 1)
    sub = f'<small>{esc(fig["sub"])}</small>' if fig.get("sub") else ""
    size = fig.get("size", 136)
    return f'<div class="fig" id="fig" style="top:{top}px;font-size:{size}px;">{txt}{sub}</div>'


class Scene:
    def __init__(self, spec, meta, gfx):
        self.s, self.meta, self.gfx = spec, meta, gfx
        self.t0 = float(spec["start"]); self.dur = round(float(spec["end"]) - self.t0, 4)
        self.assets = set(); self.html = []; self.js = []
        self.cap = int(meta.get("caption_top", 1497)) - 40          # nothing below this line (the captions run there)

    def rel(self, t):                                                 # timeline seconds → comp seconds, never negative
        return round(max(0.0, float(t) - self.t0), 3)

    def icon(self, slug, x, y, size, id_):
        src = os.path.join(ICONS, f"{slug}.webm")
        if not os.path.exists(src): sys.exit(f"no such icon: {slug} (assets/motion/icons/on-dark/) — python3 assets/motion/find.py <palabra>")
        self.assets.add(("icons", src))
        self.html.append(f'<div class="ic" id="{id_}" style="left:{x}px;top:{y}px;width:{size}px;height:{size}px;"><video src="assets/icons/{slug}.webm" data-start="0" data-duration="{self.dur}" muted playsinline></video></div>')

    def logo(self, rel, x, y, size, id_, brand=None):
        src = os.path.join(LOGOS, rel)
        if not os.path.exists(src): sys.exit(f"no such logo: {rel} (assets/logos/)")
        self.assets.add(("logos", src))
        style = f"left:{x}px;top:{y}px;width:{size}px;height:{size}px;" + (f"background:{brand};" if brand else "")
        self.html.append(f'<div class="tile{" brand" if brand else ""}" id="{id_}" style="{style}"><img src="assets/logos/{os.path.basename(rel)}"/></div>')

    # ── patterns ────────────────────────────────────────────────────────────
    def counter(self):
        """A figure counts from → to while its icon holds the frame (the bill draining 100 % → 5 %)."""
        s = self.s; c = s["counter"]
        self.html.append(fig_html({"text": c.get("from_text", "0"), "sub": c.get("sub"), "size": c.get("size", 170)}))
        # the icon holds the frame between the figure (top third) and the chip (above the caption line): 640 px, y 700→1340
        if s.get("icon"): self.icon(s["icon"], 220, 700, 640, "ico")
        if c.get("chip"): self.html.append(f'<div class="chip" id="chip" style="top:{min(1366, self.cap - 100)}px;">{esc(c["chip"])}</div>')
        pre, suf = c.get("prefix", ""), c.get("suffix", "")
        self.js.append(f"riseIn('#fig',{self.rel(c['at_start'])});")
        if s.get("icon"): self.js.append(f"pop('#ico',{self.rel(s.get('icon_at', self.t0))});")
        self.js.append(f"countUp('#fig',{self.rel(c['at_start'])},{max(0.2, self.rel(c['at_end']) - self.rel(c['at_start']))},{int(c['to'])},v=>'{pre}'+v.toLocaleString('es-CO')+'{suf}',{int(c.get('from', 0))});")
        if c.get("sub"):   # countUp rewrites innerText, so the sub label is a sibling
            self.html[0] = fig_html({"text": c.get("from_text", "0"), "size": c.get("size", 170)})
            self.html.append(f'<div class="lbl" id="sub" style="left:60px;width:960px;top:{300 + c.get("size", 170) + 20}px;font-size:44px;letter-spacing:3px;text-transform:uppercase;color:var(--cyan);">{esc(c["sub"])}</div>')
            self.js.append(f"riseIn('#sub',{self.rel(c['at_start'])});")
        if c.get("chip"): self.js.append(f"pop('#chip',{self.rel(c['chip_at'])});")

    def stack(self):
        """N things appear one by one on their words — icons or real logos, a grid that fits N."""
        s = self.s; items = s["items"]; n = len(items)
        self.html.append(fig_html(s.get("figure")))
        top = 600 if s.get("figure") else 520
        layouts = {1: [(230, 780, 620)], 2: [(80, 800, 440), (560, 800, 440)],
                   3: [(60, 860, 300), (390, 860, 300), (720, 860, 300)],
                   4: [(140, top, 360), (580, top, 360), (140, top + 440, 360), (580, top + 440, 360)],
                   5: [(60, top, 300), (390, top, 300), (720, top, 300), (225, top + 360, 300), (555, top + 360, 300)],
                   6: [(60, top, 300), (390, top, 300), (720, top, 300), (60, top + 360, 300), (390, top + 360, 300), (720, top + 360, 300)]}
        if n not in layouts: sys.exit(f"stack: {n} items (1–6)")
        for i, (it, (x, y, size)) in enumerate(zip(items, layouts[n])):
            id_ = f"it{i}"
            if it.get("logo"): self.logo(it["logo"], x, y, size, id_, it.get("brand"))
            else: self.icon(it["icon"], x, y, size, id_)
            if it.get("label"): self.html.append(f'<div class="lbl" id="lb{i}" style="left:{x - 40}px;width:{size + 80}px;top:{y + size + 14}px;">{esc(it["label"])}</div>')
            self.js.append(f"pop('#{id_}',{self.rel(it['at'])});" + (f"riseIn('#lb{i}',{self.rel(it['at']) + 0.1});" if it.get("label") else ""))
        if s.get("figure"): self.js.append(f"riseIn('#fig',{self.rel(s['figure']['at'])});")

    def line(self):
        """A line draws left → right between two words; the end value pops when it lands."""
        s = self.s; c = s["line"]; pts = c["points"]
        x0, x1, y0, y1 = 140, 940, 720, 1320
        P = [(x0 + p[0] * (x1 - x0), y1 - p[1] * (y1 - y0)) for p in pts]
        d = "M " + " L ".join(f"{x:.0f} {y:.0f}" for x, y in P)
        self.html.append(fig_html(s.get("figure"), 260))
        self.html.append(f'''<svg id="chart" style="position:absolute;left:0;top:0;opacity:0;" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <line class="axis" x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}"/><line class="axis" x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}"/>
  <path id="ln" class="line" d="{d}"/></svg>''')
        for k, lab in (("x0", c.get("x0")), ("x1", c.get("x1"))):
            if lab: self.html.append(f'<div class="lbl" id="{k}" style="left:{x0 - 60 if k == "x0" else x1 - 140}px;width:200px;top:{y1 + 20}px;font-size:34px;">{esc(lab)}</div>')
        if c.get("end_label"): self.html.append(f'<div class="chip" id="end" style="left:{P[-1][0]:.0f}px;top:{P[-1][1] - 110:.0f}px;">{esc(c["end_label"])}</div>')
        a, b = self.rel(c["at_start"]), self.rel(c["at_end"])
        self.js.append(f"tl.set('#chart',{{opacity:1}},{a});const L=document.getElementById('ln').getTotalLength();tl.set('#ln',{{strokeDasharray:L,strokeDashoffset:L}},0);")
        self.js.append(f"tl.to('#ln',{{strokeDashoffset:0,duration:{max(0.3, b - a):.3f},ease:'power2.inOut'}},{a});")
        for k in ("x0", "x1"):
            if c.get(k): self.js.append(f"riseIn('#{k}',{a});")
        if c.get("end_label"): self.js.append(f"pop('#end',{b});")
        if s.get("figure"): self.js.append(f"riseIn('#fig',{self.rel(s['figure']['at'])});")

    def donut(self):
        """A ring splits into segments, each sweeping in on its word, its icon inside the arc."""
        s = self.s; segs = s["segments"]; cx, cy, r = 540, 1040, 280
        C = 2 * 3.141592653589793 * r
        self.html.append(fig_html(s.get("figure"), 280))
        import math
        circles = []; icons = []; start = -90.0
        for i, sg in enumerate(segs):
            frac = float(sg["pct"]) / 100.0
            circles.append(f'<circle id="sg{i}" class="seg" cx="{cx}" cy="{cy}" r="{r}" stroke="{sg.get("color", SEG_COLORS[i % 4])}" transform="rotate({start:.2f} {cx} {cy})" stroke-dasharray="0 {C:.1f}"/>')
            if sg.get("icon"):
                mid = math.radians(start + 360 * frac / 2); icons.append((i, sg["icon"], int(cx + math.cos(mid) * r - 60), int(cy + math.sin(mid) * r - 60)))
            start += 360 * frac
        self.html.append(f'<svg id="ring" style="position:absolute;left:0;top:0;opacity:0;" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><circle class="seg" cx="{cx}" cy="{cy}" r="{r}" stroke="rgba(255,255,255,.08)"/>{"".join(circles)}</svg>')
        for i, slug, ix, iy in icons: self.icon(slug, ix - 15, iy - 15, 150, f"si{i}")   # after the ring: the icons sit ON the arcs
        self.js.append(f"tl.set('#ring',{{opacity:1}},{self.rel(segs[0]['at'])});")
        for i, sg in enumerate(segs):
            length = C * float(sg["pct"]) / 100.0
            self.js.append(f"tl.to('#sg{i}',{{attr:{{'stroke-dasharray':'{length:.1f} {C:.1f}'}},duration:0.6,ease:'power2.out'}},{self.rel(sg['at'])});")
            if sg.get("icon"): self.js.append(f"pop('#si{i}',{self.rel(sg['at']) + 0.3});")
        if s.get("figure"): self.js.append(f"riseIn('#fig',{self.rel(s['figure']['at'])});")

    def timeline(self):
        """A bracket draws across, then markers pop along it on their words."""
        s = self.s; c = s["timeline"]; x0, x1, y = 140, 940, 1040
        self.html.append(fig_html(s.get("figure"), 280))
        self.html.append(f'''<svg id="tlx" style="position:absolute;left:0;top:0;opacity:0;" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <line id="br" class="brk" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/><line class="brk" x1="{x0}" y1="{y - 24}" x2="{x0}" y2="{y + 24}"/><line class="brk" x1="{x1}" y1="{y - 24}" x2="{x1}" y2="{y + 24}"/></svg>''')
        for k, lab, x in (("l0", c.get("start_label"), x0 - 100), ("l1", c.get("end_label"), x1 - 100)):
            if lab: self.html.append(f'<div class="lbl" id="{k}" style="left:{x}px;width:200px;top:{y + 44}px;font-size:36px;">{esc(lab)}</div>')
        for i, m in enumerate(c.get("markers", [])):
            mx = x0 + float(m["pos"]) * (x1 - x0)
            self.html.append(f'<div class="ic" id="mk{i}" style="left:{mx - 16:.0f}px;top:{y - 16}px;width:32px;height:32px;border-radius:50%;background:var(--cyan);box-shadow:0 0 24px rgba(70,213,255,.8);"></div>')
            # marker labels live ABOVE the bracket (the start/end years sit below it), on two alternating heights so neighbours never touch
            self.html.append(f'<div class="lbl" id="ml{i}" style="left:{mx - 220:.0f}px;width:440px;top:{y - 110 if i % 2 == 0 else y - 200}px;font-size:44px;font-weight:900;">{esc(m["label"])}</div>')
        a = self.rel(c["at_draw"])
        self.js.append(f"tl.set('#tlx',{{opacity:1}},{a});tl.fromTo('#br',{{attr:{{x2:{x0}}}}},{{attr:{{x2:{x1}}},duration:0.6,ease:'power2.out'}},{a});")
        for k in ("l0", "l1"):
            if c.get("start_label" if k == "l0" else "end_label"): self.js.append(f"riseIn('#{k}',{a + 0.3});")
        for i, m in enumerate(c.get("markers", [])):
            self.js.append(f"pop('#mk{i}',{self.rel(m['at'])});riseIn('#ml{i}',{self.rel(m['at']) + 0.06});")
        if s.get("figure"): self.js.append(f"riseIn('#fig',{self.rel(s['figure']['at'])});")

    def list(self):
        """Rows reveal on their words: icon + a 2–4 word label each."""
        s = self.s; rows = s["rows"]
        self.html.append(fig_html(s.get("figure"), 260))
        top = 640 if s.get("figure") else 520
        for i, r in enumerate(rows):
            y = top + i * 150
            if y + 118 > self.cap: sys.exit(f"list: row {i + 1} would sit on the caption line; ≤ {(self.cap - top) // 150} rows fit")
            self.icon(r["icon"], 0, 0, 96, f"tmp{i}")   # registers the asset; the markup below embeds it in the row
            self.html.pop()
            self.html.append(f'<div class="row" id="r{i}" style="top:{y}px;"><div class="ri"><video src="assets/icons/{r["icon"]}.webm" data-start="0" data-duration="{self.dur}" muted playsinline></video></div><div class="rt">{esc(r["text"])}</div></div>')
            self.js.append(f"riseIn('#r{i}',{self.rel(r['at'])});")
        if s.get("figure"): self.js.append(f"riseIn('#fig',{self.rel(s['figure']['at'])});")

    def flow(self):
        """From → to: two icons, the figure, and cyan data dots flowing between them (a sale, a transfer, a cause)."""
        s = self.s; c = s["flow"]
        self.html.append(fig_html(s.get("figure"), 330))
        for i in range(30): self.html.append(f'<div class="dot" id="d{i}"></div>')
        self.icon(c["from_icon"], 40, 760, 460, "from"); self.icon(c["to_icon"], 580, 760, 460, "to")
        self.js.append(f"pop('#from',{self.rel(c['at_from'])});pop('#to',{self.rel(c['at_to'])});")
        if s.get("figure"): self.js.append(f"riseIn('#fig',{self.rel(s['figure']['at'])});")
        a = self.rel(c.get("at_dots", c["at_to"]))
        self.js.append("var Y=[930,960,990,1020,1050,945,975,1005,1035,1065,920,950,980,1010,1040,1070,935,965,995,1025,1055,925,955,985,1015,1045,1075,940,970,1000];"
                       "var S=[0,0.15,0.3,0.05,0.5,0.2,0.65,0.1,0.8,0.35,0.95,0.25,1.1,0.4,1.25,0.55,1.4,0.7,1.55,0.85,1.7,1.0,1.85,1.15,2.0,1.3,2.15,1.45,2.3,1.6];"
                       "var V=[0.9,1.1,1.0,1.2,0.95,1.05,1.15,0.9,1.0,1.1,0.95,1.2,1.05,0.9,1.1,1.0,1.15,0.95,1.05,1.2,0.9,1.0,1.1,0.95,1.05,1.15,1.0,0.9,1.2,1.1];"
                       f"for(var i=0;i<30;i++){{var t0={a}+S[i]; if(t0>DUR-0.5) continue; var du=Math.min(V[i],DUR-t0-0.05);"
                       "tl.set('#d'+i,{opacity:0.95,x:300,y:Y[i],scale:0.6+(i%3)*0.3},t0); tl.to('#d'+i,{x:790,duration:du,ease:'none'},t0); tl.set('#d'+i,{opacity:0},t0+du); }")

    def type(self):
        """Kinetic word beats: each line rises on its word and leaves before the next (registry-sequenced)."""
        s = self.s; words = s["words"]
        for i, w in enumerate(words):
            size = w.get("size", 150)
            self.html.append(f'<div class="word" id="w{i}" style="top:{w.get("top", 760)}px;font-size:{size}px;">{esc(w["text"])}</div>')
        for i, w in enumerate(words):
            a = self.rel(w["at"]); self.js.append(f"riseIn('#w{i}',{a});")
            if i + 1 < len(words):
                nxt = self.rel(words[i + 1]["at"]); self.js.append(f"riseOut('#w{i}',{max(a + 0.4, nxt - 0.35):.3f});")

    def build(self):
        pat = self.s["pattern"]
        if not hasattr(self, pat) or pat in ("build", "rel", "icon", "logo"): sys.exit(f"{self.s['id']}: unknown pattern {pat!r}")
        getattr(self, pat)()
        # exits: every named element riseOut two frames before DUR, so the next scene's plate is clean (the plate itself stays)
        ids = [h.split('id="')[1].split('"')[0] for h in self.html if 'id="' in h and not h.startswith("<svg")] + [h.split('id="')[1].split('"')[0] for h in self.html if h.startswith("<svg")]
        exits = "".join(f"exit('#{i}');" for i in ids if not i.startswith("d") or i == "d")   # the flow dots kill themselves
        fps = self.meta.get("fps", "30000/1001")
        js = (f"const DUR={self.dur};const H=HF.init({{fps:{fps},dur:DUR}});const {{tl,F,pop,slam,riseIn,riseOut,exit,float,countUp}}=H;\n"
              f"float('#float',0,DUR,'subtle');\n" + "\n".join(self.js) + f"\n{exits}\nH.finish();")
        note = self.s.get("note", "")
        html = f"""<!doctype html><html lang="es"><head><meta charset="UTF-8"/><meta name="viewport" content="width={W}, height={H}"/>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><script src="hf-anim.js"></script>
<title>{self.s['id']} · faceless scene · {pat}</title><style>
/* {self.s['id']} · {pat} · timeline {self.t0:.3f}→{self.t0 + self.dur:.3f} (DUR {self.dur}) · generated by presets/instagram/explainer/faceless/build-scene.py from hf-graphics/scenes.json
   {esc(note)}
   plate = navy + el-02 grid 0.12 + vignette (identical in every scene) · captions run at y ≥ {self.cap + 40}: nothing below y {self.cap} */
{CSS}</style></head><body style="margin:0;background:transparent;">
<div id="root" data-composition-id="main" data-width="{W}" data-height="{H}" data-start="0" data-duration="{self.dur:.4f}">
  <video id="grid" src="assets/beds/el-02-grid-warp.mp4" data-start="0" data-duration="{self.dur}" muted playsinline></video><div id="vig"></div>
  <div id="float">
    {chr(10).join('    ' + h for h in self.html)}
  </div>
</div>
<script>
{js}
</script></body></html>
"""
        return html


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job"); ap.add_argument("--ids"); ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    job = os.path.abspath(a.job); hf = os.path.join(job, "hf-graphics"); gfx = os.path.join(hf, "gfx")
    spec = json.load(open(os.path.join(hf, "scenes.json")))
    for d in ("compositions", "renders", "assets/icons", "assets/logos", "assets/beds", "assets/fonts"): os.makedirs(os.path.join(gfx, d), exist_ok=True)
    ref = os.path.join(REPO, "presets", "youtube", "default", "reference")
    for f, dst in (("hf-anim.js", "hf-anim.js"), ("fullscreen-render.sh", "render.sh")):
        if not os.path.exists(os.path.join(gfx, dst)): shutil.copy(os.path.join(ref, f), os.path.join(gfx, dst)); os.chmod(os.path.join(gfx, dst), 0o755)
    if not os.path.exists(os.path.join(gfx, "assets/beds", os.path.basename(BED))): shutil.copy(BED, os.path.join(gfx, "assets/beds"))
    for f in FONTS:
        src = os.path.join(REPO, "assets", "fonts", f)
        if os.path.exists(src) and not os.path.exists(os.path.join(gfx, "assets/fonts", f)): shutil.copy(src, os.path.join(gfx, "assets/fonts", f))
    want = set(a.ids.split(",")) if a.ids else None
    built = []
    for s in spec["scenes"]:
        if want and s["id"] not in want: continue
        sc = Scene(s, spec, gfx); html = sc.build()
        for kind, src in sc.assets:
            dst = os.path.join(gfx, "assets", kind, os.path.basename(src))
            if not os.path.exists(dst): shutil.copy(src, dst)
        out = os.path.join(gfx, "compositions", f"{s['id']}.html"); open(out, "w").write(html); built.append(s["id"])
        print(f"{s['id']:5s} {s['pattern']:9s} {sc.t0:7.3f}→{sc.t0 + sc.dur:7.3f} ({sc.dur:.3f}s)  → compositions/{s['id']}.html")
    print(f"{len(built)} scene(s). Render: cd {os.path.relpath(gfx)} && " + " && ".join(f"GRAIN=0 ./render.sh {i} full" for i in built))
    if a.render:
        for i in built:
            r = subprocess.run(["./render.sh", i, "full"], cwd=gfx, env={**os.environ, "GRAIN": "0"}, capture_output=True, text=True)
            print((r.stdout.strip().splitlines() or [""])[-1] if r.returncode == 0 else f"✗ {i}: {r.stderr[-400:]}")


if __name__ == "__main__":
    main()
