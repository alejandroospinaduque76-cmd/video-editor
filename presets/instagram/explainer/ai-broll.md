# B-roll generado — Higgsfield (MCP `hsff`) en el reel (2026-09-17)

**Qué es.** El usuario tiene el MCP de Higgsfield conectado en claude.ai (aparece como `hsff`). Es el
"AI-video tool" que `graphics-plan` ya nombraba para las celdas `b-roll` sin footage real: genera
clips (texto → video, imagen → video con movimiento de cámara) que entran al reel como cutaways en V2.
Este doc dice **cuándo sí, cuándo no, y cómo se pide**, para que un clip generado sume y no huela a
stock.

**Estado (2026-09-17).** Autorizado y probado end-to-end desde Claude Code (primer clip: la captura de arena.ai
de example-reel, Seedance 2.5, 45 créditos, ~4.5 min). Si en una sesión `hsff` no aparece, se autoriza una vez en
**claude.ai → Ajustes → Conectores → Higgsfield** y se reinicia Claude Code; hasta entonces las celdas
`generate: "higgsfield"` quedan como `⚠️ pendiente de generar` y el reel se construye igual con el resto.

**Mecánica desde Claude Code (sin widget).** `media_upload {filename}` → `curl -X PUT --data-binary` del
archivo al `upload_url` (200) → `media_confirm {media_id, type:"image"}` → `generate_video` con
`get_cost:true` primero (Seedance 2.5 1080p 5 s = 45 cr; MiniMax H3 Max 768p = 12.5 cr pero hay que escalar)
→ `generate_video` real (`model: seedance_2_5`, `mode: omni_reference`, `medias:[{value, role:"start_image"}]`,
`aspect_ratio: "9:16"`, `resolution: "1080p"`, `generate_audio: false`) → `jobs_wait` en bucle (15 s por
llamada, ~4–5 min) → `curl` del `result_url` a `broll/<gid>-raw.mp4` → conformar (`fps=30000/1001`, H.264
CRF 16). Sale HEVC 24 fps 1080×1920. **Saldo** con `balance`.

**Lección del primer clip.** El bloque de paleta del prompt RE-ILUMINA la escena (la pared beige quedó
navy/cian). Eso es lo que se quiere para atmósfera y para el set, pero en imagen → video de una captura que
convive con la toma real del mismo monitor produce un salto de luz al corte. Para continuidad con la toma
real, cambiar el bloque por *"keep the original room lighting and colours exactly, only the camera moves"*
y dejar el navy/cian para los clips que viven solos (apertura de sección, payoff).

---

## 1. Cuándo SÍ (los beats que hoy quedan flojos)

| Beat | Hoy | Con Higgsfield |
|---|---|---|
| **Abstracto con atmósfera** — "la inflación", "una ciudad que no duerme", "un equipo trabajando de noche" | icono en placa (§ 2.16) — correcto pero plano | un clip cinematográfico de 3–5 s en la paleta, como cutaway |
| **Un artefacto real que existe como FOTO** — su producto, una captura, un logo grande | captura estática con zoom (§ 2.5) | imagen → video: push-in lento, parallax, luz que se mueve; la captura cobra vida sin inventar nada |
| **El "set" (§ 2.12)** — el fondo del escenario para una sección larga | Element wireframe | un fondo generado con la iluminación de la marca, en bucle, DETRÁS del dispositivo |
| **Metáfora visual del payoff** — "abrir una puerta", "una llave", "cruzar una línea" | `type` / icono | un plano metafórico de 2–3 s (luz, objeto, cámara), sin personas reconocibles |

## 2. Cuándo NO (lo que rompe la autenticidad)

- **Nunca como prueba.** Una demo, un resultado, una pantalla, un cliente: si es real se graba o se
  captura (§ 2.5); si no existe, se dice que no existe. Un clip generado que *simula* la prueba es
  fabricar (CLAUDE.md: *Document, don't manufacture*).
- **Nunca personas reconocibles ni "gente genérica de stock"** (oficinas con gente sonriendo,
  manos tecleando). Son el stock que el research identificó como lo que NO copiamos.
- **Nunca sobre la cara** (ley de la cara, § 0) y nunca más del 25 % del runtime junto con las demás
  pruebas/cutaways (§ 3) — salvo en el tier faceless, donde compite con las escenas: máximo 1 de cada 3
  escenas generadas, el resto enactadas (el ritmo de un faceless vive en las escenas que cuentan,
  apilan y dibujan; un reel de puros clips generados es un montaje de stock).
- **Nunca texto dentro del clip generado** (la IA lo deletrea mal): el texto lo pone la comp encima.

## 3. Cómo se pide (el prompt en la paleta)

Todo prompt lleva el bloque de estilo fijo + el sujeto del beat. Sin marcas, sin texto, sin caras.

```
<sujeto del beat, una frase concreta>, cinematic, 9:16 vertical, slow <push-in | dolly | parallax>,
shallow depth of field, dark navy environment (#131A2E) with a single cyan (#46D5FF) key light,
no text, no logos, no people's faces, clean, high contrast, 24fps
```

- **Duración:** 3–5 s (la voz decide; el clip se corta a la palabra). **Aspecto:** 9:16 · 1080×1920.
- **Imagen → video** (el caso más valioso): la captura o foto REAL del job (`raw/`, `assets/`) como
  imagen de entrada, y el prompt describe solo el MOVIMIENTO ("slow push-in, subtle parallax, light
  drifting across the screen"); nada que cambie el contenido de la imagen.
- **Variantes:** pedir 2, elegir la que no tenga artefactos (manos, texto fantasma, warping), y
  escribir en el plan cuál se usó.
- **Guardar** en `projects/<job>/broll/<gid>.mp4` con el prompt en `projects/<job>/broll/<gid>.txt`
  (proveniencia: el reviewer y el usuario deben poder ver qué se pidió).

## 4. Cómo entra al reel

- **Plan:** la celda es `"kind": "b-roll"`, `"cutaway": true`, `"generate": "higgsfield"`, con el
  prompt en `content` y el `file` esperado (`broll/<gid>.mp4`). `validate-plan.py` la trata como
  cutaway (bordes al frame en los cortes de V1, cuenta en el 25 %).
- **Build:** `graphics-build` Stage 2 genera (o marca `⚠️ pendiente` si el MCP no está autorizado),
  conforma a la secuencia (`scale=1080:1920` con `crop` centrado si hace falta, sin grano, ≥ 256k de
  audio no aplica: son mudos) y pasa por la **corrección de paleta**: `colorbalance`/`curves` hacia
  navy-cian si el clip vino tibio, y la viñeta de la placa (el clip debe sentarse en el mismo mundo
  que las escenas).
- **Placement:** V2 como cualquier cutaway (`place-graphics.py` deriva la fila desde `file`); los
  subtítulos siguen encima; SFX: un whoosh de corte, nada más (un clip generado no "hace pop").
- **Gates:** `face-guard` (no aplica: no hay cara); `place-graphics --verify`; y a ojo, en el
  program monitor: **cero artefactos** (una mano de seis dedos o un texto fantasma es un defecto
  objetivo, no gusto).

## 5. Lo que Higgsfield NO sustituye

Las escenas que **enactan** (contar, apilar, dibujar, repartir, extender, fluir) siguen siendo
comps: son deterministas, en la paleta, sincronizadas a la palabra al frame y editables. Un clip
generado no sabe cuándo dices "cuatro"; una comp sí. Higgsfield es atmósfera y vida sobre lo real —
no es el motor de la animación.
