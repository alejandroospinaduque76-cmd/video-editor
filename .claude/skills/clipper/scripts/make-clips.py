#!/usr/bin/env python3
"""make-clips.py: scaffold and build clip sub-jobs from a clips-plan.json.

Part of the clipper skill. Reads projects/<parent>/clips-plan.json (authored by
the skill's selection pass) and turns each approved clip into a standard job
folder under projects/<parent>/clips/<name>/, then (with --build) runs the full
lane per clip: rough-cut splice, 9:16 face-centered reframe, locked tiktok-raw
captions, deliverable (+ an export copy only when asked for). A plan with "parent_job" (the job the
long-form was edited in) is cut from that job's RAW footage: each published-timeline
segment is mapped through its cuts.json, so no burned-in graphic reaches the crop.

Usage:
  uv run .claude/skills/clipper/scripts/make-clips.py <parent_job_dir>              # scaffold only
  uv run .claude/skills/clipper/scripts/make-clips.py <parent_job_dir> --build      # scaffold + build all
  uv run .claude/skills/clipper/scripts/make-clips.py <parent_job_dir> --build --only <name> [<name> ...]
  uv run .claude/skills/clipper/scripts/make-clips.py <parent_job_dir> --build --export-dir <folder>

Env:
  AMPLIFY_DB   the creator's manual override of the measured gain, passed through to splice.sh (a deviation,
               recorded in RUN.md); never set it to quiet an audio-qa warning on your own.
  VE_EXPORT_DIR  opt-in export-copy folder, same as --export-dir (the flag wins)

Per clip, --build does:
  1. splice.sh on the clip folder  -> outputs/<name>.mp4 (16:9) + canonical transcript
  2. face-frame.py measures the face -> face-centered crop to 1080x1920
     (center crop when no face is detectable, e.g. screencast-heavy clips);
     the 16:9 original is kept as outputs/<name>-169.mp4
  3. presets/tiktok/raw/build.py  -> outputs/<name>.final.mp4 (captions always on,
     hook card only when the plan gives hook_text)
  4. ONLY with --export-dir / VE_EXPORT_DIR: a copy of the deliverable into that folder, never over
     an existing file. Off by default since 2026-09-29: it used to copy into ~/Downloads, overwriting
     a same-named file there, while finalize.sh promises to copy nothing into Downloads.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
# Windows consoles/pipes default to cp1252, which can't encode the {glyphs} glyphs in this
# script's status lines: a cosmetic print must never kill a pipeline step (it did once,
# 2026-08-13, mid-splice on a real Windows job). Force UTF-8; no-op on macOS/Linux.
for _s in (sys.stdout, sys.stderr):
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

REPO = Path(__file__).resolve().parents[4]
SPLICE = REPO / ".claude/skills/rough-cut/scripts/splice.sh"
FACE_FRAME = REPO / "workflows/face-frame.py"
TIKTOK_BUILD = REPO / "presets/tiktok/raw/build.py"


def die(msg):
    sys.exit(f"make-clips: {msg}")


def work_root():
    """The scratch root splice.sh, transcribe.sh and polish-boundaries.py share (2026-09-25),
    same logic as polish-boundaries.work_root. A literal "/tmp/video-editor" is fine on
    macOS/Linux, but native Windows Python resolves it to C:\\tmp\\video-editor while Git Bash's
    /tmp (what splice.sh reads) is %TEMP%, so the two sides used different folders."""
    env = os.environ.get("VIDEO_EDITOR_WORK", "").strip()
    if env:
        return env
    if os.name == "nt":
        return os.path.join(tempfile.gettempdir(), "video-editor")
    return "/tmp/video-editor"


# Exported so the splice.sh children read exactly the folder this script writes cuts.json into.
os.environ["VIDEO_EDITOR_WORK"] = work_root()


def run(cmd, **kw):
    """Run a child streaming its output (audio-qa warnings must stay visible)."""
    print(f"  $ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run([str(c) for c in cmd], **kw).returncode


def probe_wh(video):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", str(video)])
    # iPhone footage carries stream side data that the csv writer emits as extra
    # elements/rows ("1920,1080," or an extra line): keep the first two real tokens.
    tok = [t for t in out.decode().strip().splitlines()[0].split(",") if t.strip()]
    return int(tok[0]), int(tok[1])


def videotoolbox_ok():
    """Apple's hardware H.264 encoder can refuse to open: a Mac VM with no media engine answers "Cannot create
    compression session: -12908" (the Intel CI Mac, 2026-09-30, where every render of the edit failed on it), and a
    busy encoder can too. A 0.2 s test encode decides; libx264 takes over when it fails. VE_NO_VIDEOTOOLBOX=1 forces
    the software encoder (tests, or a Mac where the hardware encoder misbehaves)."""
    if platform.system() != "Darwin" or os.environ.get("VE_NO_VIDEOTOOLBOX") == "1":
        return False
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:r=30:d=0.2",
                        "-c:v", "h264_videotoolbox", "-b:v", "2M", "-f", "null", "-"], capture_output=True)
    return r.returncode == 0


_VT = None


def encoder_args():
    global _VT
    if _VT is None:
        _VT = videotoolbox_ok()
    if _VT:
        return ["-c:v", "h264_videotoolbox", "-b:v", "10M"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]


def scratch_root():
    """Where splice.sh reads a clip's working EDL (the package's name for work_root, which also honours
    VIDEO_EDITOR_WORK): /tmp/video-editor on macOS/Linux, %TEMP%\\video-editor on Windows."""
    return work_root()


def link_into(dst_dir, src):
    link = dst_dir / src.name
    if not link.exists():
        try:
            os.link(src, link)             # same volume: zero bytes copied
        except OSError:
            shutil.copy2(src, link)        # cross-volume fallback


def parent_timeline(pjob):
    """The parent job's EDL laid on its PUBLISHED timeline: [(timeline start, timeline end, raw clip, raw in)], from
    each segment's `_timeline` readback when the EDL carries one (a hand-edited or mixed-rate timeline), else the
    running sum of segment lengths (the splice's own arithmetic)."""
    segs = json.loads((pjob / "transcript" / "cuts.json").read_text(encoding="utf-8"))["segments"]
    out, t = [], 0.0
    for s in segs:
        a, b = float(s["start"]), float(s["end"])
        t0, t1 = (float(s["_timeline"][0]), float(s["_timeline"][1])) if s.get("_timeline") else (t, t + b - a)
        out.append((t0, t1, os.path.basename(s["clip"]), a))
        t += b - a
    return out


def words_in(words, clip, a, b):
    """The parent's words (raw clock) whose midpoint falls in [a, b) of `clip`, as one line of text."""
    for c in words.get("clips", []):
        if os.path.basename(c.get("clip", "")) == clip:
            return " ".join(w.get("w") or w.get("word") or "" for w in c.get("words", [])
                            if "start" in w and "end" in w and a <= (w["start"] + w["end"]) / 2 < b).strip()
    return ""


def to_raw(seg, tl, words):
    """One clip segment on the PUBLISHED timeline -> the parent's raw segments that play it, split at the parent's
    cuts. An edge on a parent cut is pinned on its own (pin_in / pin_out): that boundary was refined and polished in
    the parent job already, and re-refining it could pull a word the parent killed back in. The clip's own start and end
    are refined like any cut (a whole-piece no_refine froze them too, review 2026-09-27)."""
    a, b = float(seg["start"]), float(seg["end"])
    pieces = []
    for t0, t1, clip, r0 in tl:
        x, y = max(a, t0), min(b, t1)
        if y - x <= 1e-3:
            continue
        s0, s1 = r0 + x - t0, r0 + y - t0
        piece = {k: v for k, v in seg.items() if k not in ("start", "end", "transcript", "clip")}
        piece.update(clip=clip, start=round(s0, 6), end=round(s1, 6), transcript=words_in(words, clip, s0, s1))
        if x > a + 1e-3:
            piece["pin_in"] = True                      # starts on a parent cut
        if y < b - 1e-3:
            piece["pin_out"] = True                     # ends on a parent cut
        pieces.append(piece)
    if not pieces:
        die(f"segment {a:.3f}-{b:.3f} of the published timeline is outside the parent job's EDL")
    covered = sum(p["end"] - p["start"] for p in pieces)
    if abs(covered - (b - a)) > 0.05:
        die(f"segment {a:.3f}-{b:.3f}: the parent's EDL covers {covered:.3f} s of its {b - a:.3f} s (a gap in the parent)")
    return pieces


def scaffold(parent, clip, source, words, pjob=None):
    """Create the clip's standard job folder + authored cuts (durable and /tmp). With `pjob` (the plan's parent_job)
    the clip is cut from the parent's RAW footage instead of the published file: a published long-form made here
    carries its graphics burned in, and the 9:16 face-centred reframe cut them to fragments ("ling", "ally important"
    on the Windows test clip, 2026-09-27)."""
    name = clip["name"]
    cdir = parent / "clips" / name
    for sub in ("raw", "transcript", "outputs"):
        (cdir / sub).mkdir(parents=True, exist_ok=True)

    wcopy = cdir / "transcript" / "words.json"
    if pjob is None:
        link_into(cdir / "raw", source)
        if not wcopy.exists():
            shutil.copy2(words, wcopy)
        segments = []
        for seg in clip["segments"]:
            s = dict(seg)
            s.setdefault("clip", source.name)
            segments.append(s)
    else:
        pwords = json.loads((pjob / "transcript" / "words.json").read_text(encoding="utf-8"))
        tl = parent_timeline(pjob)
        segments = [p for seg in clip["segments"] for p in to_raw(seg, tl, pwords)]
        for c in sorted({s["clip"] for s in segments}):
            if not (pjob / "raw" / c).exists():
                die(f"the parent's raw {pjob / 'raw' / c} is missing")
            link_into(cdir / "raw", pjob / "raw" / c)
        shutil.copy2(pjob / "transcript" / "words.json", wcopy)     # the raw clock the segments now run on
    cuts = {"segments": segments}

    # Durable authored copy (macOS wipes /tmp) + the scratch copy splice.sh reads.
    (cdir / "transcript" / "cuts.authored.json").write_text(
        json.dumps(cuts, indent=1) + "\n", encoding="utf-8")
    work = Path(work_root()) / name
    work.mkdir(parents=True, exist_ok=True)
    (work / "cuts.json").write_text(json.dumps(cuts, indent=1) + "\n", encoding="utf-8")

    dur = sum(s["end"] - s["start"] for s in segments)
    print(f"  scaffolded clips/{name}  ({len(segments)} segment(s), {dur:.1f}s)")
    return cdir


def reframe(cdir, name):
    """Face-centered crop of the spliced 16:9 base to the 1080x1920 clean base."""
    base = cdir / "outputs" / f"{name}.mp4"
    if not base.exists():
        die(f"{name}: splice produced no {base}")
    w, h = probe_wh(base)
    if (w, h) == (1080, 1920):
        print(f"  {name}: already 1080x1920, no reframe needed")
        return

    vf = None
    rc = run(["uv", "run", FACE_FRAME, base])
    ff_json = cdir / "face-frame.json"
    if rc == 0 and ff_json.exists():
        data = json.loads(ff_json.read_text(encoding="utf-8"))
        vf = data.get("reframe", {}).get("ffmpeg")
    if vf is None:
        crop_w = round(h * 9 / 16 / 2) * 2
        crop_x = max(0, (w - crop_w) // 2 // 2 * 2)
        vf = f"crop={crop_w}:{h}:{crop_x}:0,scale=1080:1920"
        print(f"  {name}: no measurable face, using center crop")

    wide = cdir / "outputs" / f"{name}-169.mp4"
    shutil.move(base, wide)
    rc = run(["ffmpeg", "-y", "-v", "error", "-i", wide, "-vf", vf,
              *encoder_args(), "-c:a", "copy", "-movflags", "+faststart", base])
    if rc != 0:
        shutil.move(wide, base)   # restore the base so a re-run starts clean
        die(f"{name}: reframe ffmpeg failed")
    print(f"  {name}: reframed to 1080x1920 ({vf})")


def captions(cdir, name, clip):
    final = cdir / "outputs" / f"{name}.final.mp4"
    # `uv run`, like face-frame.py above (2026-09-29): the builder declares Pillow in its own script
    # header (PEP 723), and uv resolves it on every OS. sys.executable was uv's throw-away interpreter for
    # THIS script, which has no Pillow ("No module named PIL" at the caption step); never "python3" either
    # (Windows ships a fake stub).
    # --deliver: this burn IS the clip's deliverable, so it takes the vertical file's numbers (workflows/deliver.py)
    cmd = ["uv", "run", TIKTOK_BUILD, cdir, "--hook-text", clip.get("hook_text", ""), "--out", final, "--deliver"]
    if clip.get("hook_end") is not None:
        cmd += ["--hook-end", str(clip["hook_end"])]
    if run(cmd) != 0:
        die(f"{name}: caption build failed")
    return final


def export_copy(final, name, export_dir):
    """The opt-in copy (2026-09-29): only into a folder the creator named, and never over a file that is
    already there (finalize.sh's rule: a same-named clip in that folder is someone's work)."""
    if not export_dir:
        return
    dl = Path(export_dir).expanduser()
    dest = dl / final.name
    if not dl.is_dir():
        print(f"  {name}: export dir {dl} missing, skipped copy")
    elif dest.exists():
        print(f"  {name}: {dest} already exists, not overwritten (the clip is in {final})")
    else:
        shutil.copy2(final, dest)
        print(f"  {name}: export copy -> {dest}")


def main():
    args = sys.argv[1:]
    if not args:
        die("usage: make-clips.py <parent_job_dir> [--build] [--export-dir <folder>] [--only <name> ...]")
    export_dir = os.environ.get("VE_EXPORT_DIR") or None
    if "--export-dir" in args:
        i = args.index("--export-dir")
        if i + 1 >= len(args):
            die("--export-dir needs a folder")
        export_dir = args[i + 1]
        del args[i:i + 2]        # before --only, which takes every argument after it
    parent = Path(args[0]).resolve()
    build = "--build" in args
    only = args[args.index("--only") + 1:] if "--only" in args else None

    plan_path = parent / "clips-plan.json"
    if not plan_path.exists():
        die(f"missing {plan_path} (run the clipper selection pass first)")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    source = parent / plan["source"]
    if not source.exists():
        die(f"plan source not found: {source}")
    words = parent / "transcript" / "words.json"
    if not words.exists():
        die(f"missing {words} (transcribe the parent first)")
    # parent_job: the long-form was edited HERE, so the clip is cut from that job's raw (its segments are still
    # authored on the published timeline, from the published transcript)
    pjob = None
    if plan.get("parent_job"):
        pjob = Path(plan["parent_job"])
        pjob = (pjob if pjob.is_absolute() else REPO / pjob).resolve()
        for need in ("transcript/cuts.json", "transcript/words.json"):
            if not (pjob / need).exists():
                die(f"parent_job {pjob}: no {need}")
        print(f"cutting from the parent job's raw footage: {pjob}")

    clips = [c for c in plan["clips"] if only is None or c["name"] in only]
    if not clips:
        die("no clips matched")

    failed = []
    for clip in clips:
        name = clip["name"]
        print(f"\n=== {name} ===")
        cdir = scaffold(parent, clip, source, words, pjob)
        if not build:
            continue
        try:
            if run(["bash", SPLICE, cdir]) != 0:
                raise RuntimeError("splice failed (see output above)")
            reframe(cdir, name)
            final = captions(cdir, name, clip)
            export_copy(final, name, export_dir)
            print(f"  ✓ {name}: {final}")
        except (RuntimeError, SystemExit) as e:
            print(f"  ✗ {name}: {e}")
            failed.append(name)

    if not build:
        print("\nScaffold done. Build with:  make-clips.py <parent> --build")
    elif failed:
        die(f"failed clips: {', '.join(failed)}")
    else:
        print(f"\nAll {len(clips)} clip(s) built.")


if __name__ == "__main__":
    main()
