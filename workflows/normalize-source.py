#!/usr/bin/env python3
"""normalize-source.py: step-1 intake guard for phone footage (HDR, variable frame rate, rotation).

  uv run workflows/normalize-source.py projects/<job>            # dry run: probe every raw clip, say what it would do
  uv run workflows/normalize-source.py projects/<job> --apply    # write normalized clips, keep the originals
  uv run workflows/normalize-source.py projects/<job> --json     # machine-readable probe

Why it exists. A phone clip straight off an iPhone (default camera settings since the iPhone 12) is
10-bit HEVC in HLG with Dolby Vision metadata, recorded at a VARIABLE frame rate, with a rotation
flag instead of rotated pixels. Every step downstream assumes the opposite:

- HDR: splice.sh and the caption composite encode 8-bit H.264 without converting the transfer
  curve. The export then carries HLG pixels tagged or displayed as SDR: washed-out, grey faces on
  Instagram/TikTok, or neon colours, depending on the player. It has to be tone-mapped ONCE, here.
- VFR: trim and concat work on timestamps while the frame-grid snap assumes a constant rate. On a
  VFR source the snapped cuts drift by frames and captions slip against the voice.
- Rotation: handled by the Step-0 probe already; normalizing bakes it into the pixels so no later
  tool has to remember it.

What it does. For each clip in raw/ that is HDR, VFR or rotated, it writes an SDR (BT.709),
constant-frame-rate, upright copy under the SAME stem in raw/, and moves the untouched copy to
raw/_source/ (the camera original outside the project is never touched, per step 1). transcribe.sh
only globs raw/ itself, so the pipeline sees exactly one clip per take. Audio is kept bit-exact as
PCM (decoded once, resampled only when it is not already 48 kHz) so the loudness measurement in
step 3 is not taken on a second lossy encode.

Tone-mapping backends, first available wins:
  macOS  VideoToolbox (scale_vt): Apple's own HLG/PQ/Dolby Vision -> SDR conversion, the same one
         Photos and QuickTime use. Needs no extra ffmpeg libraries.
  any    zscale + tonemap (hable): needs an ffmpeg built with libzimg (most static builds have it).
  any    libplacebo: needs an ffmpeg built with libplacebo + Vulkan.
If none is present on an HDR clip it stops and says so, never ships an unconverted clip silently.
"""
import argparse, json, os, platform, shutil, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from fractions import Fraction
from pathlib import Path

VIDEO_EXT = {".mov", ".mp4", ".m4v", ".mkv"}
HDR_TRC = {"arib-std-b67", "smpte2084"}      # HLG, PQ
STANDARD_RATES = [Fraction(24000, 1001), Fraction(24), Fraction(25), Fraction(30000, 1001), Fraction(30),
                  Fraction(50), Fraction(60000, 1001), Fraction(60)]
VFR_SAMPLE = 300                              # packets inspected for frame-duration jitter
VFR_SHARE = 0.01                              # >1% of frames off the median duration = variable rate


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"ffprobe failed on {path}: {out.stderr.strip()}")
    data = json.loads(out.stdout)
    v = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    if v is None:
        return None
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(round(float(sd["rotation"])))
    if not rot and "rotate" in (v.get("tags") or {}):
        rot = -int(v["tags"]["rotate"])
    dovi = any("DOVI" in (sd.get("side_data_type") or "") or "Dolby Vision" in (sd.get("side_data_type") or "")
               for sd in v.get("side_data_list", []) or [])
    trc = v.get("color_transfer") or ""
    r = rate_of(v.get("r_frame_rate")) or Fraction(0)
    avg = rate_of(v.get("avg_frame_rate")) or Fraction(0)
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    vfr = is_vfr(path)
    return dict(path=str(path), codec=v.get("codec_name"), pix_fmt=v.get("pix_fmt"), width=w, height=h,
                rotation=rot, transfer=trc, primaries=v.get("color_primaries") or "", matrix=v.get("color_space") or "",
                dolby_vision=dovi,
                hdr=trc in HDR_TRC or dovi, r_frame_rate=str(r), avg_frame_rate=str(avg), vfr=vfr,
                # VFR drags avg below the camera's rate (53.7 on a 60 fps take); the nominal rate is the one to keep
                target_rate=str(nearest_rate(r if r and float(r) <= 61 else (avg or Fraction(30)))),
                duration=float(data["format"].get("duration") or 0),
                audio=bool(a), audio_rate=int(a["sample_rate"]) if a else None)


def rate_of(value):
    # "0/0", empty or missing (screen recordings, odd MP4s) mean unknown, never a ZeroDivisionError
    try:
        r = Fraction(value or "")
    except (ValueError, ZeroDivisionError):
        return None
    return r if r > 0 else None


def is_vfr(path):
    # An iPhone's avg rate sits only 0.03-0.05% under nominal (59.97 vs 60), so comparing rates misses it,
    # and packet durations are written constant even when frames are dropped. The gaps between presentation
    # timestamps show it: a low-light iPhone take that falls to 30 fps inside a 60 fps file doubles them
    # (review R3, 2026-09-25). One-tick rounding jitter (59.94 in a 1/600 timebase) is not VFR.
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-read_intervals", f"%+#{VFR_SAMPLE}",
                          "-show_entries", "packet=pts", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout
    pts = sorted(int(x.split(",")[0]) for x in out.split() if x.split(",")[0].lstrip("-").isdigit())
    durs = sorted(b - a for a, b in zip(pts, pts[1:]))
    if len(durs) < 10:
        return False
    med = durs[len(durs) // 2]
    off = sum(1 for d in durs if abs(d - med) > max(1, med // 2))
    return off / len(durs) > VFR_SHARE


def transpose_for(rot):
    # the same mapping ffmpeg's autorotate uses (theta = -rotation)
    return {-90: "transpose=clock", 270: "transpose=clock", 90: "transpose=cclock", -270: "transpose=cclock",
            180: "hflip,vflip", -180: "hflip,vflip"}.get(rot, "")


def nearest_rate(rate):
    rate = Fraction(rate)
    return min(STANDARD_RATES, key=lambda s: abs(float(s) - float(rate)))


def filters():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return {line.split()[1] for line in out.splitlines() if len(line.split()) > 2 and line.startswith(" ")}


def tonemap_backend(avail):
    if platform.system() == "Darwin" and "scale_vt" in avail:
        return "videotoolbox"
    if {"zscale", "tonemap"} <= avail:
        return "zscale"
    if "libplacebo" in avail:
        return "libplacebo"
    return None


def video_bitrate(w, h, rate):
    # ~0.12 bits per pixel per frame for an intermediate that will be cut and re-encoded again: visually
    # transparent for talking heads, far smaller than ProRes. 4K60 -> ~60 Mb/s, 1080p30 -> ~8 Mb/s.
    return max(8, int(w * h * float(rate) * 0.12 / 1e6))


def build_cmd(info, dst, backend, sw=False):
    rate = info["target_rate"]
    w, h = info["width"], info["height"]
    mbps = video_bitrate(w, h, Fraction(rate))
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    vf = []
    if info["hdr"] and backend == "videotoolbox":
        # Decode on the GPU and tone-map there. Autorotate does NOT apply to hardware frames on ffmpeg 9
        # (a portrait iPhone HDR clip came out 1920x1080 on its side, review R1), so the source matrix is
        # dropped with -display_rotation 0 and the rotation is done in software after the download.
        # scale_vt keeps the 10-bit surface: download it as p010, then let swscale drop to 8-bit 4:2:0.
        cmd += ["-hwaccel", "videotoolbox", "-hwaccel_output_format", "videotoolbox_vld", "-display_rotation", "0"]
        dl = "p010le" if "10" in (info["pix_fmt"] or "") else "nv12"
        tr = transpose_for(info["rotation"])
        vf.append("scale_vt=color_matrix=bt709:color_primaries=bt709:color_transfer=bt709,"
                  f"hwdownload,format={dl}" + (f",{tr}" if tr else "") + ",format=yuv420p")
    cmd += ["-i", info["path"]]
    if info["hdr"] and backend == "zscale":
        vf.append("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
                  "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    elif info["hdr"] and backend == "libplacebo":
        vf.append("libplacebo=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv:"
                  "tonemapping=bt.2390:format=yuv420p")
    elif not info["hdr"]:
        # 2026-09-29: on an UNTAGGED SDR clip (a screen recording, some Android phones) Homebrew ffmpeg 9.0.1
        # ignores the -color_primaries/-color_trc flags below and, asked for -colorspace bt709, its auto-scaler
        # reads the untagged matrix as BT.601 and converts it: the copy came out primaries/transfer "unknown" and
        # colour-shifted. setparams labels an untagged or BT.709 clip as BT.709 (no conversion, all three tags);
        # a clip tagged with another matrix (BT.601) keeps ffmpeg's matrix conversion, which is right for it.
        vf.append("format=yuv420p" + (",setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"
                                      if info.get("matrix") in ("", "unknown", "bt709") else ""))
    if vf:
        cmd += ["-vf", ",".join(vf)]
    # iPhone files carry timed-metadata tracks next to the audio; map the first real audio stream only
    cmd += ["-map", "0:v:0", "-map", "0:a:0?", "-fps_mode", "cfr", "-r", rate]
    if platform.system() == "Darwin" and not sw:
        cmd += ["-c:v", "h264_videotoolbox", "-b:v", f"{mbps}M", "-maxrate", f"{int(mbps * 1.5)}M",
                "-profile:v", "high"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "14", "-profile:v", "high", "-pix_fmt", "yuv420p"]
    cmd += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
            "-metadata:s:v:0", "rotate=0"]
    if info["audio"]:
        # PCM keeps the voice bit-exact for the step-3 measurement; 48 kHz is the rate every later step uses
        cmd += ["-c:a", "pcm_s16le"] + (["-ar", "48000"] if info["audio_rate"] != 48000 else [])
    cmd += ["-map_metadata", "0", "-movflags", "+faststart", str(dst)]
    return cmd


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("job")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    job = Path(args.job).resolve()
    raw = job / "raw" if (job / "raw").is_dir() else job
    keep = raw / "_source"
    # an interrupted --apply leaves the original in _source/ and a partial .normalizing file: put it back first
    for leftover in raw.glob("*.normalizing.*"):
        leftover.unlink()
        print(f"· removed partial file from an interrupted run: {leftover.name}")
    if keep.is_dir():
        for orig in keep.iterdir():
            if orig.suffix.lower() in VIDEO_EXT and not (raw / (orig.stem + ".mov")).exists():
                shutil.move(str(orig), raw / orig.name)
                print(f"· restored {orig.name} from raw/_source/ (its normalized copy was missing)")
    clips = sorted(p for p in raw.iterdir() if p.suffix.lower() in VIDEO_EXT and not p.name.startswith("."))
    if not clips:
        raise SystemExit(f"no clips in {raw}")
    avail = filters()
    backend = tonemap_backend(avail)
    report = []
    for clip in clips:
        info = probe(clip)
        if info is None:
            continue
        reasons = [r for r, on in (("HDR " + (info["transfer"] or "Dolby Vision"), info["hdr"]),
                                   (f"VFR avg {float(Fraction(info['avg_frame_rate'])):.3f} fps", info["vfr"]),
                                   (f"rotation {info['rotation']}", bool(info["rotation"]))) if on]
        info["reasons"] = reasons
        info["action"] = "normalize" if reasons else "keep"
        report.append(info)

    if args.json:
        print(json.dumps(dict(backend=backend, clips=report), indent=1))
        return
    for info in report:
        name = Path(info["path"]).name
        if info["action"] == "keep":
            print(f"✓ {name}: SDR, constant {info['r_frame_rate']} fps, upright — kept as is")
        else:
            print(f"→ {name}: {', '.join(info['reasons'])} → SDR BT.709 · {info['width']}x{info['height']} · "
                  f"CFR {info['target_rate']} fps")

    todo = [i for i in report if i["action"] == "normalize"]
    if not todo:
        return
    if any(i["hdr"] for i in todo) and backend is None:
        raise SystemExit("✗ HDR footage but this ffmpeg has no tone-mapping filter (scale_vt, zscale or libplacebo).\n"
                         "  Install a full ffmpeg build (setup.sh prints how) or, on the phone, turn off\n"
                         "  Settings > Camera > Formats > HDR Video and re-record. Nothing was changed.")
    if not args.apply:
        print(f"dry run — {len(todo)} clip(s) need normalizing (tone-map backend: {backend or 'n/a'}). Re-run with --apply.")
        return

    stems = [Path(i["path"]).stem.lower() for i in report]
    clash = sorted({Path(i["path"]).name for i in todo if stems.count(Path(i["path"]).stem.lower()) > 1})
    if clash:
        raise SystemExit(f"✗ two clips share a name stem ({', '.join(clash)}); normalizing would overwrite one. "
                         "Rename one of them first. Nothing was changed.")
    keep.mkdir(exist_ok=True)
    for info in todo:
        src = Path(info["path"])
        moved = keep / src.name
        if moved.exists():
            raise SystemExit(f"✗ {moved} already exists — this clip was normalized before; not overwriting the original")
        shutil.move(str(src), moved)
        info["path"] = str(moved)
        dst = raw / (src.stem + ".mov")
        tmp = raw / (src.stem + ".normalizing.mov")
        # The Mac's hardware encoder can refuse to open ("Cannot create compression session: -12908" on a macOS VM
        # with no media engine, the Intel CI Mac 2026-09-29; "may be busy" on a loaded machine): the same clip is then
        # encoded in software, and an HDR clip whose GPU tone-map fails goes through the next tone-map filter.
        tries = [(backend, False)]
        if platform.system() == "Darwin":
            tries.append((backend, True))
            alt = tonemap_backend(avail - {"scale_vt"}) if info["hdr"] and backend == "videotoolbox" else None
            if alt:
                tries.append((alt, True))
        for n, (be, sw) in enumerate(tries):
            try:
                r = subprocess.run(build_cmd(info, tmp, be, sw), capture_output=True, text=True)
            except BaseException:              # Ctrl-C or a closed terminal mid-encode: leave raw/ as it was
                tmp.unlink(missing_ok=True)
                shutil.move(str(moved), src)
                raise
            if r.returncode == 0:
                break
            tmp.unlink(missing_ok=True)
            if n + 1 < len(tries):
                nb, nsw = tries[n + 1]
                print(f"· {src.name}: {'the hardware encoder' if not sw else be + ' tone-mapping'} failed "
                      f"({(r.stderr.strip().splitlines() or ['?'])[0][:120]}); retrying with "
                      + ("the software encoder" if nb == be else f"{nb} tone-mapping"))
        if r.returncode != 0:
            shutil.move(str(moved), src)   # put the clip back exactly as it was
            tmp.unlink(missing_ok=True)
            raise SystemExit(f"✗ {src.name}: ffmpeg failed, original restored\n{r.stderr.strip()[-1500:]}")
        os.replace(tmp, dst)
        after = probe(dst)
        ok = (after["transfer"] in ("bt709", "") and not after["hdr"] and not after["vfr"] and not after["rotation"]
              and (after["width"], after["height"]) == (info["width"], info["height"])
              and abs(after["duration"] - info["duration"]) < 0.1)
        mark = "✓" if ok else "⚠"
        print(f"{mark} {dst.name}: {after['width']}x{after['height']} · {after['transfer'] or 'untagged'} · "
              f"{after['avg_frame_rate']} fps · {after['duration']:.2f}s (source {info['duration']:.2f}s) · "
              f"original kept in raw/_source/")
        if not ok:
            print("  ⚠ the normalized clip did not verify — inspect it before cutting", file=sys.stderr)


if __name__ == "__main__":
    main()
