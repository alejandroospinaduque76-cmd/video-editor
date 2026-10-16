#!/usr/bin/env python3
"""assemble.py: the chat-only lane's composite (LANES.md steps 5' and 5): the base cut, its footage laid out per the
plan's layout map, every placed graphic over it, the caption layer last. One ffmpeg pass; the base is never
re-rendered by graphics and its audio rides through untouched.

  uv run lanes/chat-only/assemble.py projects/<job>               -> hf-graphics/renders/final.mp4
  uv run lanes/chat-only/assemble.py projects/<job> --out <mp4>
  uv run lanes/chat-only/assemble.py projects/<job> --draft       -> also outputs/<job>.draft-vN.mp4 (review/finalize)

Reads outputs/<job>.mp4 (the base cut), hf-graphics/placement.json (the placed rows: id, kind, start, end, file) and,
on a layout-rotation preset (the Talking Head Explainer), graphics-plan.json `layout` + face-frame.json `modes`
through the preset's layout.py: the base is cut at the layout edges and each span gets its footage transform (a row's
own `frame` over its mode's; S slides the frame, T punches in about the face, W is untouched; F and O keep W's
footage under their graphic; hard cuts, no ramps: layout.md § 2). A plan without `layout` keeps the footage as it is.

The mechanics below were each forced by a flash-scan FAIL on the Windows test job (2026-09-27) and stay exactly so:
  · layout edges cut FRAME-exact (trim=start_frame/end_frame): a float-second trim (14.8148 = frame 443.998) rounded
    a frame early, and every layout switch landed a frame before its graphic;
  · each overlay is placed FRAME-exact with setpts=(N+f0)/fps: a float -itsoffset ran it a frame early;
  · each overlay carries a one-frame tpad: with eof_action=pass ffmpeg never shows an overlay's LAST frame;
  · each overlay's enable window sits half a frame inside the frame grid: between(t, start, end) on float seconds
    missed the first frame whenever t and start differed in the last digit.
The caption layer goes on last. Built by captions.py --straight-alpha (hf-graphics/captions/renders/
captions-alpha-sa*.mov) it composites as approved: ffmpeg's overlay blends straight alpha in gamma space
(incremental-graphics.md). The stutter guardrail runs after every composite: 8 % or more frames identical to the
previous (signalstats YDIF == 0) exits 1.

Kept from the product's own chat-only assembler (merged into the 2026.09.28 one, 2026-09-29): --draft writes the next
free outputs/<job>.draft-vN.mp4 (never overwrites; finalize.sh promotes it); a job with no placement.json (a captions-
only short) composites the caption layer alone; graphics-plan.json is optional (no layout → footage untouched); a
layer rendered at another size than the base (1080 graphics on a 2160x3840 iPhone base) is scaled to the base frame;
the output is labelled BT.709 on the frames (setparams) when the base is untagged or BT.709 — ffmpeg 9.0.1 drops
the encoder colour flags on untagged frames; and the composite must last as long as the base. Also kept: --base <file>
and --placement <json> override the defaults; a row's "hold": true keeps its last frame to its end (eof_action=repeat);
a row's relative "file" is found in the job folder, then its hf-graphics/, then the kit root (graphics-qa.py and
face-guard.py read rows the same way); layers stack by "track" (the placers' 1-5, "top" above all, none = by kind:
"full" / the older "segment" under the graphics, "captions" over them).
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[2]
BT709 = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"
LAYOUT = REPO / "presets" / "instagram" / "talking-head-explainer" / "layout.py"
DUP_LIMIT = 0.08


def probe(path):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate", "-of", "json", str(path)],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    return int(d["width"]), int(d["height"]), d["r_frame_rate"]


def colour_matrix(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_space",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return (out.strip().splitlines() or ["unknown"])[0].strip(",") or "unknown"


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def layout_module():
    spec = importlib.util.spec_from_file_location("thx_layout", LAYOUT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def footage_chain(job, plan, W, H, fps, FPS):
    """(filter pieces, label) laying the base's footage out per the layout map; None when the plan has no layout."""
    if not plan.get("layout"):
        return None
    L = layout_module()
    md = L.modes(json.loads((job / "face-frame.json").read_text(encoding="utf-8")))
    fc, labels = [], []
    for k, (a, b, _key, m) in enumerate(L.footage_spans(plan, md)):
        s, (cx, cy) = float(m["scale"]), m["centre"]
        sw, sh = round(W * s / 2) * 2, round(H * s / 2) * 2
        x, y = round(cx * W - sw / 2), round(cy * H - sh / 2)
        f0, f1 = round(a * FPS), round(b * FPS)
        fc.append(f"[0:v]trim=start_frame={f0}:end_frame={f1},setpts=PTS-STARTPTS,scale={sw}:{sh}:flags=lanczos[s{k}];"
                  f"color=c=black:s={W}x{H}:r={fps}[bg{k}];[bg{k}][s{k}]overlay=x={x}:y={y}:shortest=1,setsar=1[v{k}]")
        labels.append(f"[v{k}]")
    fc.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[foot]")
    return fc, "foot"


KIND = {"segment": "full", "alpha": "overlay"}   # the product's older chat-only row names (incremental-graphics.md)


def row_file(job, f):
    """A placement row's file: absolute as written; a relative one is looked up in the job folder, its hf-graphics/,
    then the kit root. graphics-qa.py and face-guard.py read a row the same way (c3, v1.4 QA 2026-09-29: this
    script resolved it from the job and the two gates from the kit root, so only absolute paths worked everywhere)."""
    p = Path(f)
    if p.is_absolute():
        return p
    for c in (job / p, job / "hf-graphics" / p, REPO / p, Path.cwd() / p):
        if c.exists():
            return c.resolve()
    return job / p


def track_of(r):
    """The layer's stacking number: the placers' 1-5 (V2 cutaways … V6 headline); "top" (a hand-written caption row)
    above everything; a row with no track by its kind (a full-frame part under the graphics, captions over them).
    An unreadable value stacks as a graphic instead of crashing (c3: int("top") raised ValueError, 2026-09-29)."""
    t = r.get("track")
    if t is None:
        return {"full": 1, "captions": 4}.get(r.get("kind"), 2)
    if str(t).strip().lower() == "top":
        return 99
    try:
        return int(t)
    except (TypeError, ValueError):
        return 2


def overlay_rows(job, base_dur, pj=None):
    """The placed overlays in track order, the caption layer on its own track (its straight-alpha build when one exists)."""
    pj = pj or job / "hf-graphics" / "placement.json"
    if pj.exists():
        pl = json.loads(pj.read_text(encoding="utf-8"))
        rows = pl["rows"] if isinstance(pl, dict) else pl
    else:
        # a captions-only job never writes placement.json (the caption presets don't ask for it): lay the caption
        # layer alone over the whole base instead of refusing (c3's buyer test, 2026-09-25)
        rd = job / "hf-graphics" / "captions" / "renders"
        cands = sorted(rd.glob("captions-alpha-sa*.mov"), key=lambda p: p.stat().st_mtime) or \
            sorted(rd.glob("captions-alpha*.mov"), key=lambda p: p.stat().st_mtime)
        if not cands:
            sys.exit(f"✗ nothing to composite: no {pj} and no caption layer in {rd}")
        print(f"· no placement.json — compositing the caption layer alone (0 → {base_dur:.3f}s)")
        rows = [{"id": "captions", "kind": "captions", "file": str(cands[-1]), "start": 0.0, "end": base_dur}]
    orphans = [f"{r.get('id', '?')} at {float(r.get('start') or 0):.3f}s" for r in rows if r.get("ripple") == "orphaned"]
    if orphans:                     # a re-cut deleted their anchor (ripple-cut.py): laid, they sit at pre-recut times
        sys.exit(f"✗ placement row(s) orphaned by a re-cut: {', '.join(orphans)}. Re-anchor or delete each row, re-run "
                 "workflows/placement.py --write, then assemble (every placer refuses them, never lays them)")
    out, caps = [], []
    for r in rows:
        r["kind"] = KIND.get(r.get("kind", "overlay"), r.get("kind", "overlay"))
        f = row_file(job, r["file"])
        if not f.exists():
            sys.exit(f"✗ {r.get('id')}: {f} is not rendered")
        (caps if r.get("kind") == "captions" else out).append({**r, "file": str(f)})
    for c in caps:
        if Path(c["file"]).name.startswith("captions-alpha-sa"):
            continue
        sa = sorted((job / "hf-graphics" / "captions" / "renders").glob("captions-alpha-sa*.mov"),
                    key=lambda p: p.stat().st_mtime)
        if sa:
            c["file"] = str(sa[-1])
        else:
            print(f"⚠ no straight-alpha caption build: {Path(c['file']).name} composites heavier than approved over "
                  "ffmpeg's gamma-space blend; build it with captions.py projects/<job> --straight-alpha",
                  file=sys.stderr)
    # stacked in TRACK order, the way the app lanes lay them (placement.py): V2 cutaways under every overlay, V3/V4
    # graphics and person cut-outs, V5 captions, V6 the house headline above them; file order within one track
    return sorted(out + caps, key=track_of)


def dup_share(path):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YDIF",
                        "-f", "null", "-"], capture_output=True, text=True)
    ydif = [float(l.split("=")[1]) for l in (r.stderr + r.stdout).splitlines() if "YDIF=" in l]
    return len(ydif), sum(1 for v in ydif[1:] if v == 0.0) / max(1, len(ydif) - 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Composite a chat-only job: footage layout, overlays, captions.")
    ap.add_argument("job")
    ap.add_argument("--out", help="default: hf-graphics/renders/final.mp4")
    ap.add_argument("--base", help="the base cut (default outputs/<job>.mp4)")
    ap.add_argument("--placement", help="the placement rows (default hf-graphics/placement.json)")
    ap.add_argument("--draft", action="store_true", help="also copy the composite to outputs/<job>.draft-vN.mp4")
    a = ap.parse_args(argv)
    job = Path(a.job).resolve()
    base = Path(a.base).resolve() if a.base else job / "outputs" / f"{job.name}.mp4"
    if not base.exists():
        sys.exit(f"✗ no base cut at {base}: splice it first (rough-cut, RENDER=1)")
    gp = job / "graphics-plan.json"
    plan = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else {}   # captions-only: no plan, no layout
    W, H, rate = probe(base)
    base_dur = duration(base)
    fps = str(plan.get("fps") or rate)
    FPS = float(Fraction(fps))
    out = Path(a.out) if a.out else job / "hf-graphics" / "renders" / "final.mp4"

    inputs, fc = ["-i", str(base)], []
    lay = footage_chain(job, plan, W, H, fps, FPS)
    if lay:
        fc += lay[0]
        last = lay[1]
    else:
        fc.append("[0:v]null[foot]")
        last = "foot"
    rows = overlay_rows(job, base_dur, Path(a.placement).resolve() if a.placement else None)
    for i, r in enumerate(rows, start=1):
        inputs += ["-i", r["file"]]
        f0 = round(float(r["start"]) * FPS)
        h = 0.5 / FPS
        a_, b_ = f0 / FPS - h, round(float(r["end"]) * FPS) / FPS - h
        ow, oh, _ = probe(r["file"])
        fit = f",scale={W}:{H}:flags=lanczos" if (ow, oh) != (W, H) else ""   # 1080 layers on a 4K base
        if fit and r.get("kind") == "full" and abs(ow * H - oh * W) > 0.01 * W * H:
            # a real capture of another shape (a long-form screenshot or b-roll row, 2026-09-29) is fitted whole and
            # letterboxed, never stretched to the frame
            fit = (f",scale={W}:{H}:flags=lanczos:force_original_aspect_ratio=decrease,"
                   f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black")
        fc.append(f"[{i}:v]tpad=stop=1:stop_mode=clone,setpts=(N+{f0})/({fps})/TB{fit}[g{i}]")
        # "hold": true keeps a layer's last frame up to its end (eof_action=repeat), and so does a still image (one
        # frame, gone after it otherwise); every other layer passes
        still = str(r["file"]).lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        eof = "repeat" if r.get("hold") or still else "pass"
        fc.append(f"[{last}][g{i}]overlay=eof_action={eof}:enable='between(t,{a_:.6f},{b_:.6f})'[o{i}]")
        last = f"o{i}"
    tag = "," + BT709 if colour_matrix(base) in ("unknown", "bt709", "") else ""
    fc.append(f"[{last}]format=yuv420p{tag}[vout]")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]",
                    "-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-r", fps,
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    n, dups = dup_share(out)
    print(f"-> {out}  ({len(rows)} overlay(s){', layout keyed' if lay else ''}; {n} frames, "
          f"{100 * dups:.1f}% identical to the previous)")
    if dups >= DUP_LIMIT:
        sys.exit(f"✗ {100 * dups:.1f}% duplicated frames (the stutter trap, incremental-graphics.md): an overlay without "
                 "eof_action=pass, or a slow input")
    od = duration(out)
    if abs(od - base_dur) > 0.1:
        sys.exit(f"✗ composite is {od:.3f}s but the base is {base_dur:.3f}s — a layer extended the timeline")
    if a.draft:
        n = 1
        while (job / "outputs" / f"{job.name}.draft-v{n}.mp4").exists():
            n += 1
        draft = job / "outputs" / f"{job.name}.draft-v{n}.mp4"
        import shutil
        shutil.copy2(out, draft)
        print(f"-> draft for review {draft}  (export: bash finalize.sh {job.name} --source {draft.name} --approved --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
