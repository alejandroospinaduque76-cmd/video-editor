#!/usr/bin/env python3
"""Delivery encodes, two modes, one file (ffmpeg, any lane).

MODE 1 — platform delivery master from the approved final (v1.2, customer kit):

  python3 workflows/deliver.py <job> --platform reels                  # dry run: measure and print the plan
  python3 workflows/deliver.py <job> --platform reels --apply          # write outputs/<job>.reels.mp4
  python3 workflows/deliver.py <job> --platform tiktok --source <job>.final.mp4 --apply
  python3 workflows/deliver.py <job> --apply                           # one master per profile platform

Without --platform (v1.3) it makes one master for EACH platform in the creator's style profile
(`plataformas` in workflows/profile.py; no profile → reels, tiktok, shorts). A master that already
exists, or a platform the video does not fit (a horizontal video for a vertical feed), is reported
and skipped; the others still get made.

Runs AFTER finalize.sh (step 8). Reads the approved final, never changes it, and writes one extra
file per platform next to it. Why a separate master: the edit is mixed to the house chain (speech at
-17 LUFS into a -6 dBFS limiter), which lands around -18 LUFS integrated. Phones play Reels, TikTok
and Shorts side by side with content mastered near -14 LUFS, so the house mix sounds quiet in the
feed. This step lifts it with ONE static gain for the whole file (no gain riding, no pumping) and holds
the true peak under the cap with a lookahead limiter run at 4x the sample rate, which touches only the
peaks over the cap, so the platform's own AAC encode does not clip.

Platform targets (sources in research/METODOS-EDICION-2026.md; TikTok and Meta publish no official
loudness number, -14 LUFS is the widely used practical target):
  reels   1080x1920, keep fps (max 60), H.264 High, -14 LUFS, -1.5 dBTP, max 180 s
  tiktok  1080x1920, keep fps (max 60), H.264 High, -14 LUFS, -1.5 dBTP
  shorts  keep size up to 2160x3840, keep fps (max 60), H.264 High, -14 LUFS, -1.5 dBTP, max 180 s
  youtube keep size, keep fps, H.264 High (YouTube's published upload settings), -14 LUFS, -1.5 dBTP
Every master's loudness and true peak are MEASURED after the AAC encode, the way the platform will read them. The
gain and the limiter's ceiling are found on audio-only test encodes (seconds; the video is encoded once), each one
corrected by what the last measured, then the master is encoded with those numbers and measured again: over the
peak cap it is never delivered. Why not loudnorm (v1.2-v1.3): on a final with a hot sound effect its linear mode
could not fit the gain under the cap, fell back to its dynamic mode without saying so (gain riding, the pumping the
house rule forbids), and its TP setting never moved the post-AAC peak: -1.4 and -1.3 dBTP shipped as passed against
-1.5 (6c's re-verify, 2026-09-29). A limiter at the plain sample rate misses the peaks between samples (+0.5 to
+1.9 dB over its ceiling after the AAC on the same finals); at 4x it lands within 0.1 dB.

MODE 2 — the house deliverable encode from a finished master (the 2026.09.28 package):


  uv run workflows/deliver.py <master.mov> <out.mp4> [--shorts]

A lane whose own encoder cannot reach a number encodes its master here instead: Final Cut for every deliverable (its
H.264 choices carry no bitrate control), Premiere for the 4K YouTube Shorts file (its H.264 exporter caps the frame
at 4096x2304, so 2160x3840 comes out 1296x2304; its HEVC exporter answers exportAsMediaDirect with -1). The numbers
(researched and set 2026-09-26; presets/youtube/default/README.md § Export, presets/instagram/talking-head-explainer/
README.md § Export), picked from the master's frame:
  landscape, 1920x1080 or 3840x2160   -> 3840x2160, H.264 High 5.1 CBR 50 (5.2 CBR 80 above 30 fps)
  vertical, 1080x1920 or 2160x3840    -> 1080x1920, H.264 High 4.2 CBR 14 (video <= 2350 / seconds - 0.32 past 2:48)
  vertical 2160x3840 with --shorts    -> 2160x3840 at the landscape 4K numbers (the YouTube Shorts file)
All: closed GOP of half the frame rate, 2 B-frames, CABAC, 4:2:0, bt709 tags on the frames, limited range, the
master's frame rate, AAC-LC 320k 48 kHz, moov first. A frame-size change is a lanczos scale. The master's audio is
PCM, so this AAC encode is the only lossy audio step (never below 256k). Proving the file is the caller's job (each
lane's export.py ffprobes it). Stdlib only.

The mode is picked from the arguments: two positionals where the first is a media file = MODE 2, anything
else = MODE 1. The module API MODE 2 exposes (reels_mbps, target, plan, video_args, TAGS, command, encode) is
what lanes/*/export.py, lanes/capcut and presets/tiktok/raw/build.py --deliver import.
"""

import argparse, importlib.util, json, re, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path

spec = importlib.util.spec_from_file_location('verify_export', Path(__file__).with_name('verify-export.py'))
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

LONG_MBPS, LONG_HFR_MBPS = 50, 80   # 3840x2160 (and the Shorts 2160x3840): CBR 50 at <= 30 fps, CBR 80 at 48-60
REELS_MBPS, AUDIO_MBPS = 14, 0.32   # the vertical 1080x1920 file; AAC 320k


def reels_mbps(secs):
    """The vertical file's video bitrate: CBR 14, or video <= 2350 / seconds - 0.32 (300 MB less 2 % for the
    container, less the AAC) once 14 would break Meta's 300 MB cap, in whole Mbps."""
    return max(1, min(REELS_MBPS, int(2350 / secs - AUDIO_MBPS))) if secs and secs > 0 else REELS_MBPS


def target(W, H, fps, secs, shorts=False):
    """(out W, out H, Mbps, H.264 level, vertical 1080 file?) for a W x H master."""
    hfr = fps > 30.5
    if W > H or shorts:
        return (*((3840, 2160) if W > H else (2160, 3840)), LONG_HFR_MBPS if hfr else LONG_MBPS,
                '5.2' if hfr else '5.1', False)
    return 1080, 1920, reels_mbps(secs), '4.2', True


def plan(master, shorts=False):
    """What the master is and what it becomes: {W, H, rate, fps, frames, secs, OW, OH, mbps, level, vertical, gop}."""
    d = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                                   'stream=width,height,r_frame_rate,nb_read_packets', '-of', 'json', str(master)],
                                  capture_output=True, text=True, check=True).stdout)['streams'][0]
    W, H, rate, frames = int(d['width']), int(d['height']), d['r_frame_rate'], int(d['nb_read_packets'])
    fps = Fraction(*map(int, rate.split('/')))
    secs = float(frames / fps)
    OW, OH, mbps, level, vertical = target(W, H, float(fps), secs, shorts)
    return dict(W=W, H=H, rate=rate, fps=fps, frames=frames, secs=secs, OW=OW, OH=OH, mbps=mbps, level=level,
                vertical=vertical, gop=max(1, round(float(fps) / 2)))


def video_args(mbps, level, gop, rate):
    """The house H.264 video settings as ffmpeg output args (the frame size and the bt709 frame tags are the filter's)."""
    m = f'{mbps}M'
    return ['-c:v', 'libx264', '-profile:v', 'high', '-level:v', level, '-pix_fmt', 'yuv420p', '-preset', 'slow',
            '-b:v', m, '-minrate', m, '-maxrate', m, '-bufsize', m, '-g', str(gop), '-bf', '2', '-flags', '+cgop',
            '-x264-params', 'nal-hrd=cbr:force-cfr=1:open-gop=0', '-r', rate,
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv']


TAGS = 'setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv'


def command(master, out, p):
    """The one ffmpeg command for plan `p`."""
    scale = f'scale={p["OW"]}:{p["OH"]}:flags=lanczos,' if (p['OW'], p['OH']) != (p['W'], p['H']) else ''
    # the tags ride the FRAMES: ffmpeg 8 lets an untagged master's frame properties override -color_primaries & co.
    return ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(master), '-map', '0:v:0', '-map', '0:a:0',
            '-vf', scale + TAGS, *video_args(p['mbps'], p['level'], p['gop'], p['rate']),
            '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-movflags', '+faststart', str(out)]


def encode(master, out, shorts=False):
    """Encode `master` to `out`; returns the plan. Raises CalledProcessError on an ffmpeg failure."""
    p = plan(master, shorts)
    print(f'… encoding {master} → {out}: {p["W"]}x{p["H"]}'
          + (f' → {p["OW"]}x{p["OH"]}' if (p['OW'], p['OH']) != (p['W'], p['H']) else '')
          + f' H.264 High {p["level"]} CBR {p["mbps"]} Mbps, GOP {p["gop"]} closed, AAC 320k', flush=True)
    subprocess.run(command(master, out, p), check=True)
    return p


PLATFORMS = {
    'reels':   dict(vertical=True, max_w=1080, max_h=1920, lufs=-14.0, tp=-1.5, max_s=180),
    'tiktok':  dict(vertical=True, max_w=1080, max_h=1920, lufs=-14.0, tp=-1.5, max_s=3600),
    'shorts':  dict(vertical=True, max_w=2160, max_h=3840, lufs=-14.0, tp=-1.5, max_s=180),
    'youtube': dict(vertical=False, max_w=3840, max_h=3840, lufs=-14.0, tp=-1.5, max_s=None),   # -1.5 like the rest (the kit's rule)
}
LRA = 11.0
STANDARD_RATES = [Fraction(24000, 1001), Fraction(24), Fraction(25), Fraction(30000, 1001), Fraction(30),
                  Fraction(50), Fraction(60000, 1001), Fraction(60)]


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                       capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise ValueError('FFprobe no puede leer ' + str(path))
    info = json.loads(r.stdout)
    vs = next(s for s in info['streams'] if s.get('codec_type') == 'video')
    has_audio = any(s.get('codec_type') == 'audio' for s in info['streams'])
    return vs, has_audio, float(info['format']['duration'])


def measure(path, target, tp):
    af = f'loudnorm=I={target}:TP={tp}:LRA={LRA}:print_format=json'
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-map', '0:a:0', '-af', af, '-f', 'null', '-'],
                       capture_output=True, text=True, timeout=1800)
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr)
    if r.returncode or not m:
        raise ValueError('No se pudo medir el volumen (loudnorm).')
    return json.loads(m.group(0))


def loudness_of(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-map', '0:a:0', '-af', 'ebur128=peak=true',
                        '-f', 'null', '-'], capture_output=True, text=True, timeout=1800).stderr
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', r)
    p = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', r)
    return (float(i[-1]) if i else None, float(p[-1]) if p else None)


def audio_args(gain_db, ceiling_db):
    """The one audio chain, identical in the test encodes and the master: a static gain, the lookahead limiter at 4x
    the rate (latency compensated, so the sound keeps its sync; auto level off, so it never turns anything up), then
    48 kHz stereo AAC 320k."""
    af = (f'volume={gain_db:.2f}dB,aresample=192000,alimiter=limit={10 ** (ceiling_db / 20):.5f}:attack=5:release=50:'
          'level=0:latency=1,aresample=48000')
    return ['-map', '0:a:0', '-af', af, '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2']


def start_gain(cfg, m):
    """The gain the source's own measurement asks for (None: a silent track, nothing to lift)."""
    try:
        i = float(m['input_i'])
    except (KeyError, TypeError, ValueError):
        return None
    return round(cfg['lufs'] - i, 2) if -60 < i < 0 else None


def find_audio(src, cfg, m):
    """(gain dB, limiter ceiling dB, LUFS, dBTP) found on audio-only test encodes, measured after the AAC like the
    master will be. Each round moves the gain by the loudness still missing and, over the cap, the ceiling by the
    overshoot; four rounds at most. Returns the round nearest the loudness target among those under the peak cap,
    or the last round when none got under it (the caller then refuses to deliver)."""
    aim = cfg['tp'] - 0.1          # ebur128 prints one decimal: a tenth of margin keeps the printed peak at the cap
    g, c = start_gain(cfg, m), aim - 0.2
    best = last = None
    with tempfile.TemporaryDirectory() as d:
        test = str(Path(d) / 'audio.m4a')
        for _ in range(4):
            r = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src),
                                *audio_args(g, c), '-vn', test], capture_output=True, text=True)
            if r.returncode:
                raise ValueError('ffmpeg falló al probar el audio: ' + r.stderr.strip()[-800:])
            i, p = loudness_of(test)
            if i is None or p is None:
                raise ValueError('No se pudo medir el audio de prueba (ebur128).')
            last = (g, c, i, p)
            if p <= cfg['tp'] and (best is None or abs(cfg['lufs'] - i) < abs(cfg['lufs'] - best[2])):
                best = last
            if p <= cfg['tp'] and abs(cfg['lufs'] - i) <= 0.2:
                break
            if p > cfg['tp']:
                c = round(c + aim - p, 2)
            if abs(cfg['lufs'] - i) > 0.2:
                g = round(g + cfg['lufs'] - i, 2)
    return best or last


def rate_of(value):
    # "0/0", empty or missing (screen recordings, odd MP4s) mean unknown, never a ZeroDivisionError
    try:
        r = Fraction(value or '')
    except (ValueError, ZeroDivisionError):
        return None
    return r if r > 0 else None


def even(x):
    return int(x) // 2 * 2


class PlatformError(ValueError):
    """This platform cannot be delivered (exists already / wrong orientation / HDR)."""


ALIASES = {'instagram': 'reels', 'ig': 'reels', 'reel': 'reels', 'youtube-shorts': 'shorts',
           'youtube_shorts': 'shorts', 'short': 'shorts', 'yt': 'youtube'}


def profile_platforms():
    """The creator's platforms from workflows/profile.py (sibling file); v1.2 set when it cannot be read."""
    try:
        spec = importlib.util.spec_from_file_location('ve_profile', Path(__file__).with_name('profile.py'))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        raw = mod.load()['valores'].get('plataformas') or []
    except Exception:
        raw = ['reels', 'tiktok', 'shorts']
    out = []
    for x in raw:
        k = ALIASES.get(str(x).strip().lower(), str(x).strip().lower())
        if k not in PLATFORMS:
            print(f'⚠ Plataforma del perfil desconocida: {x!r} (válidas: {", ".join(sorted(PLATFORMS))}); se omite.',
                  file=sys.stderr)
        elif k not in out:
            out.append(k)
    return out


def platform_main(argv=None):
    ap = argparse.ArgumentParser(description='Platform delivery master from the approved final (MODE 1).')
    ap.add_argument('job')
    ap.add_argument('--platform', choices=sorted(PLATFORMS),
                    help='Una plataforma. Sin esta opción: una por cada plataforma del perfil de estilo.')
    ap.add_argument('--source', help='Nombre del MP4 dentro de outputs/ (por defecto <job>.final.mp4)')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args(argv)
    # accept "projects/<job>" too, the form normalize-source.py and transcribe.sh take (2026-09-25)
    a.job = a.job.rstrip('/\\')
    if a.job.replace('\\', '/').startswith('projects/'):
        a.job = a.job.replace('\\', '/').split('/', 1)[1]

    if not a.job or a.job in ('.', '..') or any(c in a.job for c in '/\\\0'):
        ap.error('Nombre de proyecto inválido: usa el nombre de la carpeta dentro de projects/, p. ej. mi-video.')
    root = Path(__file__).resolve().parents[1]
    out = root / 'projects' / a.job / 'outputs'
    if not out.is_dir():
        ap.error('No existe projects/<job>/outputs.')
    name = a.source or (a.job + '.final.mp4')
    if Path(name).name != name:
        ap.error('--source debe ser un nombre de archivo, sin carpetas.')
    src = out / name
    if not src.is_file():
        ap.error(f'No existe outputs/{name}. Primero ejecuta finalize.sh con el borrador aprobado.')

    if a.platform:
        try:
            deliver(a.job, a.platform, src, out, a.apply, {})
        except PlatformError as e:
            ap.error(str(e))
        return
    plats = profile_platforms()
    if not plats:
        ap.error('El perfil no tiene plataformas válidas: usa --platform.')
    print('Plataformas (perfil de estilo): ' + ', '.join(plats))
    cache, failed, skipped = {}, [], []
    for plat in plats:
        try:
            deliver(a.job, plat, src, out, a.apply, cache)
        except PlatformError as e:
            print(f'· {plat}: {e}', file=sys.stderr); skipped.append(plat)
        except (ValueError, OSError, subprocess.SubprocessError) as e:
            print(f'✗ {plat}: {e}', file=sys.stderr); failed.append(plat)
    if failed:
        raise ValueError('Falló la entrega para: ' + ', '.join(failed))
    if len(skipped) == len(plats):
        # reviewer R2: every platform skipped must not look like success
        raise ValueError('No se creó ninguna entrega: todas las plataformas se omitieron (ver avisos arriba).')


def deliver(job, platform, src, out, apply, cache):
    """One platform master. cache: loudness measurements shared across platforms of one run."""
    dst = out / f'{job}.{platform}.mp4'
    if dst.exists():
        raise PlatformError(f'Ya existe outputs/{dst.name}. Se conserva; bórralo tú si quieres regenerarlo.')

    cfg = PLATFORMS[platform]
    vs, has_audio, dur = probe(src)
    w, h = int(vs['width']), int(vs['height'])
    for sd in vs.get('side_data_list', []) or []:
        if abs(int(round(float(sd.get('rotation', 0))))) % 180 == 90:
            w, h = h, w
    if cfg['vertical'] and w > h:
        raise PlatformError(f'{platform} es vertical y este video es horizontal ({w}x{h}). Reencuádralo a 9:16 primero.')
    if (vs.get('color_transfer') or '') in ('arib-std-b67', 'smpte2084'):
        raise PlatformError('El final está en HDR. Normaliza las fuentes con workflows/normalize-source.py y vuelve a renderizar.')
    if cfg['max_s'] and dur > cfg['max_s'] + 0.5:
        print(f'⚠ Dura {dur:.0f} s; {platform} admite hasta {cfg["max_s"]} s en este formato.', file=sys.stderr)

    scale = min(1.0, cfg['max_w'] / w, cfg['max_h'] / h)
    ow, oh = even(w * scale), even(h * scale)
    # snap to the nearest broadcast rate: a phone's variable rate otherwise leaks through as 59.832 fps
    rate = rate_of(vs.get('avg_frame_rate')) or rate_of(vs.get('r_frame_rate')) or Fraction(30)
    rate = min(STANDARD_RATES, key=lambda s: abs(float(s) - float(rate)))
    gop = max(1, round(float(rate) / 2))                      # YouTube: closed GOP of half the frame rate
    mbps = 12 if oh * ow <= 1080 * 1920 else 35               # 1080p60 12 Mb/s; 4K ~35-45 Mb/s

    summary = f'{platform}: {w}x{h} → {ow}x{oh} · {float(rate):.3f} fps · H.264 High · {mbps} Mb/s máx'
    g0 = None
    if has_audio:
        key = (cfg['lufs'], cfg['tp'])
        m = cache[key] if key in cache else cache.setdefault(key, measure(src, cfg['lufs'], cfg['tp']))
        g0 = start_gain(cfg, m)
        if g0 is None:
            summary += ' · audio en silencio: se copia sin subir el volumen'
        else:
            squeeze = float(m['input_tp']) + g0 - (cfg['tp'] - 0.3)
            summary += (f' · audio {float(m["input_i"]):.1f} LUFS / {float(m["input_tp"]):.1f} dBTP → '
                        f'{cfg["lufs"]:.0f} LUFS / {cfg["tp"]} dBTP ({g0:+.1f} dB'
                        + (f'; el limitador baja ~{squeeze:.1f} dB los picos más fuertes)' if squeeze > 0.05 else ')'))
    print(summary)
    if not apply:
        print('SIMULACIÓN: no se escribió nada. Añade --apply para crear ' + dst.name)
        return

    vf = f'scale={ow}:{oh}:flags=lanczos,format=yuv420p' if (ow, oh) != (w, h) else 'format=yuv420p'
    # 2026-09-29: Homebrew ffmpeg 9.0.1 ignores -color_primaries/-color_trc below when the final's frames carry
    # no colour tags (the chat-only final shipped them "unknown", so did its master) and, on a fully untagged
    # file, reads the matrix as BT.601 and converts it. setparams writes BT.709 on the frames of an untagged or
    # BT.709 final (no conversion); a final tagged with another matrix keeps ffmpeg's matrix conversion.
    if (vs.get('color_space') or 'unknown') in ('unknown', 'bt709'):
        vf += ',setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709'
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', str(src),
           '-map', '0:v:0', '-vf', vf, '-fps_mode', 'cfr', '-r', str(rate),
           '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '18',
           '-maxrate', f'{mbps}M', '-bufsize', f'{mbps * 2}M', '-g', str(gop), '-bf', '2', '-flags', '+cgop',
           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv']
    found = None
    if has_audio and g0 is not None:
        gkey = key + ('found',)
        if gkey not in cache:
            print('… probando el audio (solo audio, medido después del AAC)', flush=True)
            cache[gkey] = find_audio(src, cfg, m)
        found = cache[gkey]
        g, c, ti, tpk = found
        print(f'· audio: ganancia {g:+.2f} dB, techo del limitador {c:.2f} dBTP → prueba {ti:.1f} LUFS / {tpk:.1f} dBTP')
    tmp = dst.with_suffix('.tmp.mp4')
    aud = (audio_args(found[0], found[1]) if found else
           ['-map', '0:a:0', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2']) if has_audio else []
    r = subprocess.run(cmd + aud + ['-movflags', '+faststart', '-metadata:s:v:0', 'rotate=0', str(tmp)],
                       capture_output=True, text=True)
    if r.returncode:
        tmp.unlink(missing_ok=True)
        raise ValueError('ffmpeg falló: ' + r.stderr.strip()[-800:])
    # verify and measure BEFORE the rename: a master that fails must never sit in outputs/ under the deliverable's name
    try:
        res = v.verify(tmp, expected_duration=dur, width=ow, height=oh, require_audio=has_audio)
        if found:
            i, p = loudness_of(tmp)
            if p is None or p > cfg['tp']:
                raise ValueError(f'el master mide {p} dBTP de pico real, sobre el tope de {cfg["tp"]} dBTP (la prueba de '
                                 f'audio medía {found[3]:.1f}): no se entrega. Vuelve a correrlo; si se repite, avísanos.')
            res.update(loudness_lufs=i, true_peak_dbfs=p, gain_db=found[0], limiter_ceiling_dbtp=found[1])
            squeeze = float(m['input_tp']) + found[0] - found[1]
            res['limiter_max_db'] = round(max(0.0, squeeze), 1)
            if squeeze > 6:
                res['limiter_warning'] = (f'el limitador bajó hasta {squeeze:.1f} dB los picos más fuertes: escúchalo antes '
                                          'de subirlo; si suena aplastado, falta el pulido de audio del paso 3 o un efecto '
                                          'de sonido está muy alto.')
            if i is not None and abs(i - cfg['lufs']) > 1.0:
                res['loudness_warning'] = (f'{i:.1f} LUFS, lejos de {cfg["lufs"]:.0f}: el audio no llegó a la meta '
                                           'sin pasar el tope de pico.')
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.rename(dst)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print('Entrega lista: ' + str(dst))


def master_main(argv):
    """MODE 2: `deliver.py <master> <out.mp4> [--shorts]`, the 2026.09.28 package's CLI, unchanged."""
    ap = argparse.ArgumentParser(description='The house deliverable encode from a finished master (MODE 2).')
    ap.add_argument('master')
    ap.add_argument('out')
    ap.add_argument('--shorts', action='store_true', help='a 2160x3840 master: the 4K YouTube Shorts file')
    a = ap.parse_args(argv)
    encode(a.master, a.out, a.shorts)
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    pos = [x for x in argv if not x.startswith('-')]
    if not pos and any(x in ('-h', '--help') for x in argv):
        print(__doc__)          # both modes (c3: -h showed only the platform mode)
        return 0
    if len(pos) == 2 and Path(pos[0]).is_file() and pos[1].lower().endswith(('.mp4', '.mov', '.m4v')):
        return master_main(argv)
    return platform_main(argv)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as e:
        print('ERROR: ' + str(e), file=sys.stderr); sys.exit(1)
