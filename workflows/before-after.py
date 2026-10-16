#!/usr/bin/env python3
"""before-after.py: a short ANTES / DESPUÉS clip of a finished job — the raw take next to the edited final.

  python3 workflows/before-after.py projects/<job>                  # first 10 s of each → outputs/<job>.antes-despues.mp4
  python3 workflows/before-after.py projects/<job> --seconds 8
  python3 workflows/before-after.py projects/<job> --final outputs/<job>.draft-v2.mp4 --audio antes

Why (2026-09-28, v1.3 onboarding). The first edit a new creator sees is the moment they decide whether the kit
"gets" them. Watching their own raw take beside the finished cut says it faster than any summary. Optional:
`empezar` offers it after the first export; it never replaces the final and never touches it.

What it does.
  ANTES   the first N s of the NORMALIZED raw (raw/<clip>, SDR, upright; the camera copy in raw/_source/ is only a
          fallback and is flagged, because an HDR original shows grey/neon colours without tone-mapping).
  DESPUÉS the first N s of outputs/<job>.final.mp4 (or --final).
  Layout  vertical final (9:16) → two 540x960 halves side by side, 1080x960.
          horizontal/square final → two 1080x960 halves stacked, 1080x1920 (a 9:16 post).
          Each half keeps its own aspect (fit + dark padding), so a horizontal raw next to a vertical final is not
          stretched.
  Labels  rendered with PIL from the kit's bundled Inter font into one transparent PNG and overlaid — no ffmpeg
          drawtext (many ffmpeg builds ship without libfreetype).
  Audio   the final's by default (--audio antes | despues | ninguno).
  Privacy the ANTES half is the raw, never blurred: a job that lists what must not reach the screen (pii.json) or
          whose sweep found it (review/pii-scan*.json with hits) is REFUSED, because the comparison would show again
          what the final hides (c3, v1.4 QA 2026-09-29: an e-mail blurred in the final was readable in the ANTES).
          --allow-raw overrides it, only after a look at the first N s of the raw.
"""
import argparse, json, shutil, subprocess, sys, tempfile
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mts"}


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    if v is None:
        raise SystemExit(f"✗ {path}: no se puede leer el video")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        rot = int(round(float(sd.get("rotation", 0) or 0)))
    if abs(rot) % 180 == 90:
        w, h = h, w
    return dict(w=w, h=h, dur=float(d.get("format", {}).get("duration") or 0),
                audio=any(s.get("codec_type") == "audio" for s in d.get("streams", [])),
                hdr=v.get("color_transfer") in ("arib-std-b67", "smpte2084"))


def find_raw(job):
    raw = job / "raw"
    clips = sorted(p for p in raw.glob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXT) if raw.is_dir() else []
    if clips:
        return clips[0], False
    src = sorted(p for p in (raw / "_source").glob("*") if p.suffix.lower() in VIDEO_EXT) if (raw / "_source").is_dir() else []
    return (src[0], True) if src else (None, False)


def font(px):
    from PIL import ImageFont
    for name in ("Inter-Black.otf", "Inter-Bold.otf"):
        f = KIT / "assets" / "fonts" / name
        if f.is_file():
            return ImageFont.truetype(str(f), px)
    return ImageFont.load_default()


def labels_png(path, W, H, boxes):
    """One transparent W x H PNG with a pill label at the top of each half. boxes = [(x, y, w, h, text), …]."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(34)
    for x, y, w, h, text in boxes:
        tw = d.textlength(text, font=f)
        cx, top = x + w / 2, y + 22
        d.rounded_rectangle([cx - tw / 2 - 20, top, cx + tw / 2 + 20, top + 54], radius=27,
                            fill=(255, 255, 255, 235) if text == "DESPUÉS" else (0, 0, 0, 200))
        d.text((cx, top + 27), text, font=f, anchor="mm", fill=(15, 15, 18) if text == "DESPUÉS" else "white")
    im.save(path)


def private_marks(job):
    """What says this job's raw shows something that must not reach the screen: pii.json, or a sweep with hits."""
    why = []
    if (job / "pii.json").is_file():
        why.append("pii.json")
    for m in sorted((job / "review").glob("pii-scan*.json")) if (job / "review").is_dir() else []:
        if m.name.endswith(".meta.json"):
            continue
        try:
            hits = sum(1 for v in json.loads(m.read_text(encoding="utf-8")).values() if v)
        except Exception:
            continue
        if hits:
            why.append(f"review/{m.name} ({hits} fotogramas con coincidencias)")
    return why


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("job", help="projects/<job>")
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--final", help="the edited file (default outputs/<job>.final.mp4)")
    ap.add_argument("--raw", help="the raw clip (default: the first clip in raw/)")
    ap.add_argument("--audio", choices=["despues", "antes", "ninguno"], default="despues")
    ap.add_argument("--allow-raw", action="store_true",
                    help="build it even when the job has private data on screen (only after checking the raw)")
    a = ap.parse_args()

    job = Path(a.job).resolve()
    name = job.name
    if not job.is_dir():
        raise SystemExit(f"✗ no existe {job}")
    marks = private_marks(job)
    if marks and not a.allow_raw:
        raise SystemExit("✗ No hago el antes/después de este trabajo: el ANTES usa el video crudo sin difuminar y "
                         "mostraría otra vez lo que el final oculta (" + ", ".join(marks) + "). Si revisaste que los "
                         f"primeros {a.seconds:g} s del crudo no muestran nada privado, repite con --allow-raw.")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"✗ falta {tool} (bash setup.sh --check)")
    try:
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit("✗ falta Pillow (bash setup.sh --check lo instala)")

    final = Path(a.final) if a.final else job / "outputs" / f"{name}.final.mp4"
    if not final.is_absolute() and not final.exists():
        final = job / final
    if not final.is_file():
        drafts = sorted((job / "outputs").glob(f"{name}.draft-v*.mp4")) if (job / "outputs").is_dir() else []
        hint = f" Borradores: {', '.join(p.name for p in drafts)} (usa --final)." if drafts else ""
        raise SystemExit(f"✗ no hay final en {final}.{hint}")
    raw, from_source = (Path(a.raw), False) if a.raw else find_raw(job)
    if not raw or not raw.is_file():
        raise SystemExit(f"✗ no encuentro el clip crudo en {job / 'raw'} (usa --raw)")

    pf, pr = probe(final), probe(raw)
    if from_source or pr["hdr"]:
        print(f"⚠ ANTES usa {raw.name}, que no está normalizado"
              + (" y es HDR: sus colores se verán grises o saturados" if pr["hdr"] else "")
              + ". Corre workflows/normalize-source.py para una comparación justa.")
    n = max(1.0, min(a.seconds, pf["dur"] or a.seconds, pr["dur"] or a.seconds))

    vertical = pf["h"] > pf["w"]
    if vertical:
        W, H, hw, hh = 1080, 960, 540, 960
        pos = [(0, 0), (540, 0)]
    else:
        W, H, hw, hh = 1080, 1920, 1080, 960
        pos = [(0, 0), (0, 960)]
    out = job / "outputs" / f"{name}.antes-despues.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "labels.png"
        labels_png(png, W, H, [(pos[0][0], pos[0][1], hw, hh, "ANTES"), (pos[1][0], pos[1][1], hw, hh, "DESPUÉS")])
        fit = (f"scale={hw}:{hh}:force_original_aspect_ratio=decrease:flags=lanczos,"
               f"pad={hw}:{hh}:(ow-iw)/2:(oh-ih)/2:color=0x111114,setsar=1,fps=30,format=yuv420p")
        stack = "hstack=inputs=2" if vertical else "vstack=inputs=2"
        fc = (f"[0:v]{fit}[a];[1:v]{fit}[b];[a][b]{stack}[s];"
              f"[s][2:v]overlay=0:0:format=auto,format=yuv420p[v]")
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y",
               "-t", f"{n:.3f}", "-i", str(raw), "-t", f"{n:.3f}", "-i", str(final), "-loop", "1", "-t", f"{n:.3f}",
               "-i", str(png), "-filter_complex", fc, "-map", "[v]"]
        src_audio = {"despues": (1, pf["audio"]), "antes": (0, pr["audio"])}.get(a.audio)
        if src_audio and src_audio[1]:
            cmd += ["-map", f"{src_audio[0]}:a:0", "-c:a", "aac", "-b:a", "160k", "-ar", "48000"]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", "-t", f"{n:.3f}", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"✗ ffmpeg falló:\n{r.stderr[-1500:]}")
    po = probe(out)
    print(f"✓ {out}  ({po['w']}x{po['h']}, {po['dur']:.1f} s) — ANTES: {raw.name} · DESPUÉS: {final.name}")


if __name__ == "__main__":
    main()
