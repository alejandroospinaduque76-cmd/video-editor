#!/usr/bin/env python3
"""profile.py: the creator's EDITING STYLE PROFILE — the one place every step reads "how does this person edit".

  python3 workflows/profile.py status                    # new creator? which profile is active?
  python3 workflows/profile.py new <slug> --nombre "Ana"  # create a profile and make it active
  python3 workflows/profile.py use <slug>                 # switch the active profile (one per creator / client)
  python3 workflows/profile.py list
  python3 workflows/profile.py show                       # the style in plain Spanish (also writes ESTILO.md)
  python3 workflows/profile.py get corte.pausa_max_s      # one value (the kit default when no profile)
  python3 workflows/profile.py set subtitulos.palabras 2 --reason "pidió subtítulos más cortos" [--job <job>]
  python3 workflows/profile.py learn creator/perfiles/<slug>/estilo-medido.json   # measured references → values
  python3 workflows/profile.py explain                    # every value, where it came from and when
  python3 workflows/profile.py env                        # KEY=value lines for shell scripts (eval "$(…)")
  python3 workflows/profile.py new <slug> --defaults      # the creator declined onboarding: kit defaults, no more nagging
  python3 workflows/profile.py undo                       # revert the last change
  python3 workflows/profile.py reset subtitulos.palabras  # one value back to the kit default (--all: everything)
  python3 workflows/profile.py export mi-estilo.zip       # every profile (for a new kit version or another computer)
  python3 workflows/profile.py import mi-estilo.zip       # bring them back; the active one stays active

Why (2026-09-28). Until v1.2 the kit's taste was hard-coded: dead air kept up to 0.65 s, captions locked to one
look, a flat −18 dB music bed, "keep the last take"… — tuned to ONE creator. Each buyer edits differently. The
profile holds that person's choices; every script and skill reads them from here, and with no profile the kit
behaves exactly as v1.2 did (the DEFAULTS below are the v1.2 constants).

Where it lives: creator/perfiles/<slug>/perfil.json (+ ESTILO.md, historial.jsonl, estilo-medido.json,
vocabulario in perfil.json) and creator/activo (the active slug). creator/ never ships in a release.
Every value records its source: "default" | "respuesta" (the creator said so) | "medido" (measured on their
reference videos) | "aprendido" (a correction during a review, job named). A later source never silently
overwrites a "respuesta": `learn` only fills values the creator did not answer.
"""
import argparse, copy, datetime, json, os, re, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

KIT = Path(os.environ.get("VIDEO_EDITOR_KIT") or Path(__file__).resolve().parents[1])
CREATOR = KIT / "creator"
PROFILES = CREATOR / "perfiles"
ACTIVE = CREATOR / "activo"
SCHEMA_VERSION = 1

# The v1.2 behaviour, value for value. Changing a default here changes the kit for every buyer without a profile.
DEFAULTS = {
    "creador": {"nombre": "", "marca": "", "handle": "", "cta": ""},
    "idioma": "auto",
    "plataformas": ["reels", "tiktok", "shorts"],
    "duracion_objetivo_s": 90,
    "corte": {
        "pausa_max_s": 0.65,        # polish-boundaries DEAD_AIR_S: longest silence kept between phrases
        "agresividad": "media",     # suave | media | fuerte — how much good-to-know content the rough cut drops
        "muletillas": "naturales",  # todas | naturales | preguntar
        "tomas": "ultima",          # ultima | preguntar
        "cola_s": 0.07,             # polish-boundaries TAIL_S: air after the last sound of a phrase
    },
    "subtitulos": {
        "estilo": "caja",           # caja (explainer: text on a box) | borde (tiktok/raw: outlined text) | ninguno
        "palabras": 4,              # max words on screen at once
        "mayusculas": False,
        "posicion_y": 0.5,          # centre of the caption, share of frame height from the top
        "tamano_px": 49,            # font size on a 1080x1920 frame
        "color_texto": "#ffffff",
        "color_fondo": "#000000",   # box colour (caja) / outline colour (borde)
        "color_resaltado": "",      # active-word highlight colour ("" = none); explainer builder only
    },
    "graficos": {"densidad": "basica", "zooms": True},   # densidad: ninguna | basica | completa
    "musica": {"activa": False, "volumen_db": -20},   # mix-music.sh BED_DB default (-20 since the 2026.09.28 package)
    "vocabulario": {"auto": {}, "flag": []},             # merged into transcript corrections
}
CHOICES = {
    "corte.agresividad": ["suave", "media", "fuerte"],
    "corte.muletillas": ["todas", "naturales", "preguntar"],
    "corte.tomas": ["ultima", "preguntar"],
    "subtitulos.estilo": ["caja", "borde", "ninguno"],
    "graficos.densidad": ["ninguna", "basica", "completa"],
}
RANGES = {
    "corte.pausa_max_s": (0.10, 1.50), "corte.cola_s": (0.02, 0.25), "subtitulos.palabras": (1, 8),
    "subtitulos.posicion_y": (0.10, 0.85), "subtitulos.tamano_px": (28, 120), "musica.volumen_db": (-36, -8),
    "duracion_objetivo_s": (10, 3600),
}


# ── storage ───────────────────────────────────────────────────────────────────────────────────────────────
def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))).strip("-")
    return s or "creador"


def active_slug():
    try:
        s = ACTIVE.read_text().strip()
    except OSError:
        return None
    return s if (PROFILES / s / "perfil.json").is_file() else None


def pdir(slug=None):
    slug = slug or active_slug()
    return PROFILES / slug if slug else None


def load(slug=None):
    """The active profile merged over DEFAULTS; with no profile, DEFAULTS (source "default")."""
    d = pdir(slug)
    data = json.loads((d / "perfil.json").read_text()) if d and (d / "perfil.json").is_file() else {}
    merged = copy.deepcopy(DEFAULTS)
    _merge(merged, data.get("valores", {}))
    return dict(slug=d.name if d and data else None, valores=merged, fuentes=data.get("fuentes", {}),
                creado=data.get("creado"), version=data.get("version", SCHEMA_VERSION), onboarding=data.get("onboarding"))


def save(p):
    d = PROFILES / p["slug"]
    d.mkdir(parents=True, exist_ok=True)
    out = dict(version=SCHEMA_VERSION, slug=p["slug"], creado=p.get("creado") or now(), valores=p["valores"],
               fuentes=p["fuentes"])
    if p.get("onboarding"):
        out["onboarding"] = p["onboarding"]
    tmp = d / "perfil.json.tmp"
    tmp.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    os.replace(tmp, d / "perfil.json")
    (d / "ESTILO.md").write_text(describe(p, markdown=True))


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict) and k != "vocabulario":
            _merge(base[k], v)
        else:
            base[k] = v


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def getk(vals, key):
    cur = vals
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(key)
        cur = cur[part]
    return cur


def coerce(key, raw):
    default = getk(DEFAULTS, key)
    try:
        return _coerce(key, raw, default)
    except ValueError:
        raise SystemExit(f"✗ {key}: «{raw}» no es un valor válido (ejemplo: {json.dumps(default, ensure_ascii=False)})")


def _coerce(key, raw, default):
    if isinstance(raw, str):
        if isinstance(default, bool):
            v = raw.lower() in ("1", "true", "si", "sí", "yes", "on")
        elif isinstance(default, int) and not isinstance(default, bool):
            v = int(round(float(raw.replace(",", "."))))
        elif isinstance(default, float):
            v = float(raw.replace(",", "."))
        elif isinstance(default, list):
            v = [x.strip() for x in raw.split(",") if x.strip()]
        else:
            v = raw.strip()
    else:
        v = raw
    if key in CHOICES and v not in CHOICES[key]:
        raise SystemExit(f"✗ {key} admite: {', '.join(CHOICES[key])}")
    if key in RANGES:
        lo, hi = RANGES[key]
        if not (lo <= v <= hi):
            raise SystemExit(f"✗ {key}={v} fuera de rango ({lo}–{hi})")
    if key.startswith("subtitulos.color") and not (v == "" and key.endswith("resaltado")) \
            and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(v)):
        raise SystemExit(f"✗ {key} debe ser un color #rrggbb")
    return v


def setv(p, key, value, source, reason="", job=None, overwrite_answer=True):
    """Set one value; returns False when a creator's own answer would be overwritten by a weaker source."""
    prev = p["fuentes"].get(key, {})
    if not overwrite_answer and prev.get("source") == "respuesta":
        return False
    value = coerce(key, value)
    cur = p["valores"]
    parts = key.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    old = cur.get(parts[-1])
    cur[parts[-1]] = value
    p["fuentes"][key] = dict(source=source, reason=reason, job=job, fecha=now())
    if p.get("slug"):
        with open(PROFILES / p["slug"] / "historial.jsonl", "a") as f:
            f.write(json.dumps(dict(fecha=now(), key=key, de=old, a=value, source=source, reason=reason, job=job,
                                    fuente_previa=prev or None),
                               ensure_ascii=False) + "\n")
    return True


# ── plain-Spanish description (what the creator SEES) ─────────────────────────────────────────────────────
def describe(p, markdown=False):
    v = p["valores"]; c = v["corte"]; s = v["subtitulos"]; m = v["musica"]; g = v["graficos"]
    f = p.get("fuentes", {})

    names = {"respuesta": "tú lo dijiste", "medido": "medido en tus videos", "aprendido": "aprendido editando",
             "default": "valor inicial del kit"}

    def src(k):
        # a line built from several values names every origin it mixes (c3 2026-09-29: "tú lo dijiste" was shown
        # for a caption line whose position and size came from the measurement)
        keys = k if isinstance(k, (list, tuple)) else [k]
        seen = []
        for key in keys:
            x = names.get(f.get(key, {}).get("source", "default"), "?")
            if x not in seen:
                seen.append(x)
        return " + ".join(seen)

    ritmo = {"suave": "tranquilo: se conserva el contexto", "media": "equilibrado",
             "fuerte": "ágil: solo lo necesario"}[c["agresividad"]]
    subs = ("sin subtítulos" if s["estilo"] == "ninguno" else
            f"{s['palabras']} palabra{'s' if s['palabras'] != 1 else ''} a la vez, "
            f"{'MAYÚSCULAS, ' if s['mayusculas'] else ''}{'en caja' if s['estilo'] == 'caja' else 'con borde'}, "
            f"texto {s['color_texto']}{', la palabra que dices se pinta ' + s['color_resaltado'] if s.get('color_resaltado') else ''}, "
            f"a {round(s['posicion_y'] * 100)}% de alto, {s['tamano_px']} px")
    sub_keys = ["subtitulos." + x for x in ("estilo", "palabras", "mayusculas", "color_texto", "color_resaltado",
                                            "posicion_y", "tamano_px")]
    mul = {"todas": "se quitan todas", "naturales": "se quitan los titubeos, se conservan las que suenan naturales",
           "preguntar": "se listan y tú decides"}[c["muletillas"]]
    lines = [
        ("Ritmo", f"{ritmo}; pausas de hasta {c['pausa_max_s']:.2f} s", ["corte.agresividad", "corte.pausa_max_s"]),
        ("Muletillas", mul, "corte.muletillas"),
        ("Tomas repetidas", "se queda la última" if c["tomas"] == "ultima" else "te pregunto cuál", "corte.tomas"),
        ("Subtítulos", subs, sub_keys if s["estilo"] != "ninguno" else "subtitulos.estilo"),
        ("Gráficos", {"ninguna": "ninguno", "basica": "pocos y limpios", "completa": "muchos, estilo explicativo"}[g["densidad"]]
         + ("; con zooms de énfasis" if g["zooms"] else "; sin zooms"),
         "graficos.zooms" if "graficos.zooms" in f and "graficos.densidad" not in f else "graficos.densidad"),
        ("Música", f"sí, {m['volumen_db']} dB bajo la voz" if m["activa"] else "no",
         ["musica.activa", "musica.volumen_db"] if m["activa"] else "musica.activa"),
        ("Plataformas", ", ".join(v["plataformas"]) + f"; duración objetivo {v['duracion_objetivo_s']} s",
         ["plataformas", "duracion_objetivo_s"]),
    ]
    name = v["creador"].get("nombre") or p.get("slug") or "sin perfil"
    learned = sum(1 for x in f.values() if x.get("source") == "aprendido")
    if markdown:
        out = [f"# Tu estilo de edición — {name}", "", "| | | origen |", "|---|---|---|"]
        out += [f"| **{a}** | {b} | {src(k)} |" for a, b, k in lines]
        voc = v["vocabulario"]
        if voc.get("auto"):
            out += ["", "**Palabras que siempre se escriben bien:** " + ", ".join(sorted(set(voc["auto"].values())))]
        out += ["", f"Aprendido editando contigo: {learned} ajuste(s). Para cambiar algo, dilo en una frase "
                "(\"subtítulos más grandes\", \"deja más pausas\") y responde **sí** a \"¿siempre así?\"."]
        return "\n".join(out) + "\n"
    out = [f"Estilo de {name}:"] + [f"  • {a}: {b}  ({src(k)})" for a, b, k in lines]
    if learned:
        out.append(f"  Aprendido editando contigo: {learned} ajuste(s).")
    return "\n".join(out)


# ── measured references → values ──────────────────────────────────────────────────────────────────────────
def from_measured(m, H=1920):
    """Map style-learn.py's summary to profile values. Returns {key: (value, why)}; only what the data supports."""
    s = m.get("summary", m)
    out = {}
    if "pause_p90_s" in s:
        pm = round(min(0.9, max(0.15, s["pause_p90_s"])) * 20) / 20
        out["corte.pausa_max_s"] = (pm, f"en tus videos el 90% de las pausas dura unos {pm:.2f} s o menos")
    if "cuts_per_min" in s:
        cpm = s["cuts_per_min"]
        lvl = "fuerte" if cpm >= 22 else "suave" if cpm < 8 else "media"
        # the cut detector never invents cuts but misses ~1 in 5 (reviewer S1): say "at least"
        out["corte.agresividad"] = (lvl, f"al menos {cpm:.0f} cortes por minuto (toma mediana {s.get('median_shot_s', 0):.1f} s)")
    if "punch_ins_per_min" in s:
        out["graficos.zooms"] = (s["punch_ins_per_min"] >= 0.8, f"{s['punch_ins_per_min']:.1f} zooms por minuto")
    if s.get("music_bed") is not None:
        out["musica.activa"] = (bool(s["music_bed"]), "música de fondo detectada" if s["music_bed"] else "sin música de fondo")
        if s["music_bed"] and s.get("music_vs_voice_db") is not None:
            out["musica.volumen_db"] = (int(max(-30, min(-10, round(s["music_vs_voice_db"])))),
                                        f"la música va {abs(s['music_vs_voice_db']):.0f} dB bajo la voz")
    if s.get("captions") is True:
        if "caption_center_y" in s:
            out["subtitulos.posicion_y"] = (round(min(0.85, max(0.10, s["caption_center_y"])), 2),
                                            f"tus subtítulos están a {s['caption_center_y'] * 100:.0f}% de alto")
        if s.get("caption_line_height"):
            # the measured box is one line of glyphs incl. outline ≈ 0.95 × the font size
            px = int(round(min(120, max(28, s["caption_line_height"] * H * 0.95))))
            out["subtitulos.tamano_px"] = (px, f"línea de subtítulo de {s['caption_line_height'] * 100:.1f}% del alto")
        if s.get("caption_box") is not None:
            out["subtitulos.estilo"] = ("caja" if s["caption_box"] else "borde",
                                        "tus subtítulos van sobre una caja" if s["caption_box"] else "tus subtítulos van con borde, sin caja")
        if s.get("caption_color") == "yellow":
            out["subtitulos.color_texto"] = ("#ffd400", "tus subtítulos son amarillos")
        hl = {"yellow": "#ffd400", "cyan": "#22d3ee", "green": "#22c55e", "orange": "#fb923c", "red": "#ef4444",
              "blue": "#3b82f6", "magenta": "#e879f9"}.get(s.get("caption_highlight") or "")
        if hl:
            out["subtitulos.color_resaltado"] = (hl, f"resaltas la palabra clave en {s['caption_highlight']}")
        wps = s.get("words_per_s")
        if wps and s.get("caption_changes_per_s"):
            n = int(max(1, min(5, round(wps / s["caption_changes_per_s"]))))
            out["subtitulos.palabras"] = (n, f"hablas {wps:.1f} palabras/s y el subtítulo cambia {s['caption_changes_per_s']:.1f} veces/s")
    elif s.get("captions") is False:
        out["subtitulos.estilo"] = ("ninguno", "tus videos de referencia no llevan subtítulos quemados")
    # corte.muletillas is NOT learned (c3, 2026-09-29): Whisper leaves "eh/mmm" out of its text, so a finished
    # video always reads ~0 fillers/min and every buyer would be switched to "remove all". It is asked instead.
    # idioma is NEVER learned (reviewer P1): a reference may be another creator in another language, and a
    # learned "en" would force English transcription on a Spanish buyer — the v1.1 defect D1 again.
    if s.get("duration_s"):
        out["duracion_objetivo_s"] = (int(round(s["duration_s"] / 5) * 5) or 10, f"tus videos duran ~{s['duration_s']:.0f} s")
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status"); sub.add_parser("list"); sub.add_parser("show"); sub.add_parser("explain")
    sub.add_parser("env"); sub.add_parser("json")
    n = sub.add_parser("new"); n.add_argument("slug"); n.add_argument("--nombre", default="")
    n.add_argument("--defaults", action="store_true", help="declined onboarding: keep kit defaults, stop asking")
    ex = sub.add_parser("export"); ex.add_argument("file")
    im = sub.add_parser("import"); im.add_argument("file"); im.add_argument("--replace", action="store_true")
    u = sub.add_parser("use"); u.add_argument("slug")
    g = sub.add_parser("get"); g.add_argument("key")
    s = sub.add_parser("set"); s.add_argument("key"); s.add_argument("value")
    s.add_argument("--reason", default=""); s.add_argument("--job"); s.add_argument("--source", default="respuesta",
                                                                                  choices=["respuesta", "aprendido", "medido"])
    le = sub.add_parser("learn"); le.add_argument("measured")
    sub.add_parser("undo")
    rs = sub.add_parser("reset"); rs.add_argument("key", nargs="?"); rs.add_argument("--all", action="store_true")
    w = sub.add_parser("word"); w.add_argument("wrong"); w.add_argument("right", nargs="?")
    a = ap.parse_args()

    if a.cmd == "status":
        slug = active_slug()
        if not slug:
            n_prof = len(list(PROFILES.glob("*/perfil.json"))) if PROFILES.is_dir() else 0
            print("NUEVO: no hay perfil activo" + (f" ({n_prof} perfil(es) guardado(s): usa `profile.py use <slug>`)" if n_prof else "")
                  + " → correr la skill `empezar` (onboarding de estilo)")
            sys.exit(3)
        p = load()
        print(f"ACTIVO: {slug} ({p['valores']['creador'].get('nombre') or slug})")
        return
    if a.cmd == "list":
        act = active_slug()
        for d in sorted(PROFILES.glob("*/perfil.json")) if PROFILES.is_dir() else []:
            print(("* " if d.parent.name == act else "  ") + d.parent.name)
        return
    if a.cmd == "new":
        slug = slugify(a.slug)
        if (PROFILES / slug / "perfil.json").exists():
            raise SystemExit(f"✗ ya existe el perfil {slug}: `profile.py use {slug}`")
        p = dict(slug=slug, valores=copy.deepcopy(DEFAULTS), fuentes={}, creado=now())
        (PROFILES / slug / "referencias").mkdir(parents=True, exist_ok=True)
        if a.nombre:
            setv(p, "creador.nombre", a.nombre, "respuesta")
        if a.defaults:
            p["onboarding"] = "rechazado"   # reviewer G3: a "no" still creates a profile, so the hook stops asking
        save(p)
        CREATOR.mkdir(exist_ok=True); ACTIVE.write_text(slug + "\n")
        print(f"✓ perfil {slug} creado y activo → {PROFILES / slug}")
        return
    if a.cmd == "export":
        # reviewer G2: a new kit version is a new folder, and creator/ must travel with the creator
        import zipfile
        if not PROFILES.is_dir():
            raise SystemExit("✗ no hay perfiles que exportar")
        with zipfile.ZipFile(a.file, "w", zipfile.ZIP_DEFLATED) as z:
            for f in CREATOR.rglob("*"):
                if f.is_file() and "referencias" not in f.relative_to(CREATOR).parts:
                    z.write(f, f.relative_to(CREATOR))
        print(f"✓ perfiles exportados → {a.file} (sin los videos de referencia; sus medidas sí van)")
        return
    if a.cmd == "import":
        import zipfile
        if not Path(a.file).is_file() or not zipfile.is_zipfile(a.file):
            raise SystemExit(f"✗ {a.file} no existe o no es un .zip exportado con `profile.py export`")
        with zipfile.ZipFile(a.file) as z:
            names = [n for n in z.namelist() if not n.startswith("/") and ".." not in Path(n).parts]
            slugs = sorted({Path(n).parts[1] for n in names if n.startswith("perfiles/") and len(Path(n).parts) > 2})
            clash = [s_ for s_ in slugs if (PROFILES / s_).exists()]
            if clash and not a.replace:
                raise SystemExit(f"✗ ya existen: {', '.join(clash)} — usa --replace para sobrescribirlos")
            for n in names:
                if n.startswith("perfiles/") or (n == "activo" and not active_slug()):
                    z.extract(n, CREATOR)
        print(f"✓ importado(s): {', '.join(slugs) or 'nada'} · activo: {active_slug() or 'ninguno (usa `profile.py use <slug>`)'}")
        return
    if a.cmd == "use":
        slug = slugify(a.slug)
        if not (PROFILES / slug / "perfil.json").is_file():
            raise SystemExit(f"✗ no existe el perfil {slug} (perfiles: `profile.py list`)")
        ACTIVE.write_text(slug + "\n"); print(f"✓ perfil activo: {slug}")
        return

    p = load()
    if a.cmd == "get":
        try:
            val = getk(p["valores"], a.key)
        except KeyError:
            raise SystemExit(f"✗ clave desconocida: {a.key}")
        print(json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list, bool)) else val)
        return
    if a.cmd == "json":
        print(json.dumps(p, indent=1, ensure_ascii=False)); return
    if a.cmd == "env":
        # flat KEY=value for shell scripts: VE_CORTE_PAUSA_MAX_S=0.65 …
        def walk(d, pre):
            for k, x in d.items():
                if k == "vocabulario":
                    continue
                if isinstance(x, dict):
                    walk(x, pre + [k])
                else:
                    val = ",".join(x) if isinstance(x, list) else ("1" if x is True else "0" if x is False else x)
                    print(f"VE_{'_'.join(pre + [k]).upper()}={val}")
        walk(p["valores"], []); print(f"VE_PERFIL={p['slug'] or ''}"); return
    if a.cmd == "show":
        print(describe(p))
        if p["slug"]:
            (PROFILES / p["slug"] / "ESTILO.md").write_text(describe(p, markdown=True))
        return
    if a.cmd == "explain":
        def walk(d, pre):
            for k, x in d.items():
                key = ".".join(pre + [k])
                if isinstance(x, dict) and k != "vocabulario":
                    walk(x, pre + [k]); continue
                fs = p["fuentes"].get(key, {})
                print(f"{key:28} = {json.dumps(x, ensure_ascii=False):22} {fs.get('source', 'default'):10} "
                      f"{fs.get('reason', '')}{' (job ' + fs['job'] + ')' if fs.get('job') else ''}")
        walk(p["valores"], []); return
    if not p["slug"]:
        raise SystemExit("✗ no hay perfil activo: crea uno con `profile.py new <nombre>` (o corre `empezar`)")
    if a.cmd == "set":
        try:
            getk(DEFAULTS, a.key)
        except KeyError:
            raise SystemExit(f"✗ clave desconocida: {a.key} (ver `profile.py explain`)")
        setv(p, a.key, a.value, a.source, a.reason, a.job)
        save(p); print(f"✓ {a.key} = {getk(p['valores'], a.key)}  ({a.source}{': ' + a.reason if a.reason else ''})")
        return
    if a.cmd == "word":
        voc = p["valores"].setdefault("vocabulario", {"auto": {}, "flag": []})
        if a.right:
            voc.setdefault("auto", {})[a.wrong.lower()] = a.right
            msg = f"✓ «{a.wrong}» se escribirá siempre «{a.right}»"
        else:
            voc.setdefault("flag", []).append(a.wrong.lower()); msg = f"✓ «{a.wrong}» se marcará para revisar"
        p["fuentes"]["vocabulario"] = dict(source="respuesta", fecha=now())
        save(p); print(msg); return
    if a.cmd in ("undo", "reset"):
        # reviewer G6: every change is reversible — undo the last one, or put a value (or all) back to the kit default
        hist = PROFILES / p["slug"] / "historial.jsonl"
        if a.cmd == "undo":
            lines = hist.read_text().splitlines() if hist.is_file() else []
            if not lines:
                raise SystemExit("✗ no hay cambios que deshacer")
            last = json.loads(lines[-1])
            cur = p["valores"]
            parts = last["key"].split(".")
            for part in parts[:-1]:
                cur = cur[part]
            cur[parts[-1]] = last["de"] if last["de"] is not None else getk(DEFAULTS, last["key"])
            if last.get("fuente_previa"):
                p["fuentes"][last["key"]] = last["fuente_previa"]
            else:
                p["fuentes"].pop(last["key"], None)
            hist.write_text("\n".join(lines[:-1]) + ("\n" if len(lines) > 1 else ""))
            save(p); print(f"✓ deshecho: {last['key']} vuelve a {json.dumps(getk(p['valores'], last['key']), ensure_ascii=False)}")
            return
        keys = [k for k in list(p["fuentes"]) if k != "vocabulario"] if a.all else [a.key] if a.key else []
        if not keys:
            raise SystemExit("✗ indica una clave (`reset subtitulos.palabras`) o --all")
        for k in keys:
            try:
                setv(p, k, getk(DEFAULTS, k), "default", "reset")
            except KeyError:
                raise SystemExit(f"✗ clave desconocida: {k}")
            p["fuentes"].pop(k, None)
        save(p); print(f"✓ {len(keys)} valor(es) vuelven al valor inicial del kit")
        return
    if a.cmd == "learn":
        m = json.loads(Path(a.measured).read_text())
        changed, kept = [], []
        for key, (val, why) in from_measured(m).items():
            if setv(p, key, val, "medido", why, overwrite_answer=False):
                changed.append(f"  • {key} = {val}  — {why}")
            else:
                kept.append(key)
        save(p)
        print("Aprendido de tus videos:\n" + ("\n".join(changed) or "  (nada nuevo)"))
        if kept:
            print("Se respetó lo que tú respondiste en: " + ", ".join(kept))
        return


if __name__ == "__main__":
    main()
