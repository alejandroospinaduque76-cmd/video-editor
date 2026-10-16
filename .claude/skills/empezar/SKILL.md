---
name: empezar
description: "Onboarding de estilo (primer uso): revisa el equipo, conoce al creador en 5 preguntas, MIDE su estilo en 1–3 videos terminados, le muestra su perfil en español claro y termina con su primer video exportado. También gestiona perfiles (varios creadores o clientes) e importa el perfil de una versión anterior del kit. First-run style onboarding, English fallback. Triggers: empezar, /empezar, soy nuevo, soy nueva, configúrame, configurar mi estilo, actualizar mi estilo, nuevo perfil, usa el perfil, cambiar de perfil, start, get started, set up my style, new profile, use profile. Also run it when the SessionStart hook says CREADOR NUEVO."
---

# Empezar — el kit aprende cómo editas

**Meta:** de «empezar» a un MP4 exportado con el estilo del creador en **menos de 15 min de trabajo
activo** del creador, con **5 preguntas como máximo**, en **un solo mensaje**. No cites «15 minutos»
al creador: la primera descarga del motor de transcripción (~4,3 GB) depende de su conexión.

**Reglas que no se rompen**
- **Nunca bloquees una edición.** Si en cualquier momento pide editar, guarda lo que ya sabes (o crea
  el perfil por defecto, abajo) y pasa a `edit-video`. El onboarding se retoma con «empezar».
- **Si dice que no** (o «después», «sáltalo», «no quiero») en cualquier paso: crea el perfil por
  defecto y dilo en una línea. Así el aviso de inicio deja de preguntar (revisión G3):
  `python3 workflows/profile.py new "<nombre o mi-estilo>" --defaults [--nombre "<nombre>"]`
  (solo si `profile.py status` sale con código 3; si ya hay perfil, no crees otro).
  → «Listo: edito con el estilo neutro del kit. Cuando quieras que aprenda el tuyo, escribe **empezar**.»
- **Todo el estado vive en `workflows/profile.py`.** Nunca compruebes rutas de `creator/` a mano para
  saber si alguien es nuevo: usa `profile.py status` (código 3 = no hay perfil activo) (revisión G1).
- **Progreso visible:** empieza cada mensaje del flujo con **`Paso n/5 · <nombre del paso>`**.
- **Idioma:** español. Si el creador escribe en inglés, haz el mismo flujo en inglés (las claves del
  perfil siguen en español; tradúcelas al hablar).
- **Windows:** usa `python` en lugar de `python3`. Todo lo demás es igual (Git Bash).
- **Codex:** no hay hooks; AGENTS.md manda comprobar `profile.py status` al inicio y la palabra
  `empezar` abre este archivo. Lanza los procesos en segundo plano con `nohup … &`.

Todos los comandos de perfil se escriben completos, `python3 workflows/profile.py …`, desde la carpeta del kit. No lo guardes en una variable de shell: en zsh `$P set …` no se separa en palabras y falla (c3, 2026-09-29).

---

## Entradas directas (sin recorrer los 5 pasos)

| El creador dice | Haz |
|---|---|
| «usa el perfil X», «cambia a X» | `python3 workflows/profile.py list` → elige el slug que corresponde a X → `python3 workflows/profile.py use <slug>` → `python3 workflows/profile.py show` (3–8 líneas). |
| «nuevo perfil», «otro cliente» | Paso 2 como creador nuevo (siempre `python3 workflows/profile.py new`, nunca pises el perfil activo), luego 3 → 4. |
| «actualizar mi estilo» | Paso 3 (videos nuevos) → Paso 4. Las respuestas anteriores se respetan: `learn` no pisa lo que el creador dijo. |
| «¿cómo edito ahora?», «mi estilo» | `python3 workflows/profile.py show`. |

---

## Paso 1/5 · Tu equipo (antes de gastar su tiempo)

Ejecuta tú, sin pedir permiso, y resume en 2–3 líneas:

1. **Máquina.** `uname -s -m`.
   - `Darwin arm64` → bien. `Darwin x86_64` → comprueba `sysctl -n sysctl.proc_translated` (1 =
     Apple Silicon bajo Rosetta → bien). Si da 0 o falla, es un **Mac Intel**: sigue, y dilo en una
     línea: «La versión para tu computador está en su prueba final. Si algo falla, escríbenos (el
     contacto está en tu recibo): te avisamos cuando esté lista o te devolvemos el dinero.» La
     transcripción instala sola su versión para Intel. Nunca digas que el kit no se puede usar en ese equipo.
   - Windows (`MINGW…`/`MSYS…`) o Linux → sigue. La edición completa por la ruta chat-only está probada en
     los dos (29/09/2026); no hace falta ningún aviso. En Linux, el instalador pide correr el comando `apt`
     que muestra: pásaselo tal cual. (CLAUDE.md § Windows tiene los detalles de Windows.)
2. **Espacio.** `df -Pk . | awk 'NR==2{printf "%d\n", $4/1048576}'` (GB libres). **< 10 GB** → dilo y
   pide liberar espacio antes de seguir (el motor de transcripción ocupa ~5 GB y cada trabajo guarda
   copias del material). No lances la descarga.
3. **Herramientas.** `bash setup.sh --check`. Si falta `.setup-complete` o dice `lane=pending`, corre
   el flujo **FIRST RUN de CLAUDE.md** tal cual (`./setup.sh` y sus códigos de salida). Si pide
   reiniciar, di: «Reinicia, abre esta misma carpeta y escribe **empezar**»; al volver, este paso ya
   pasa y sigues en el Paso 2.
4. **Descarga en segundo plano, ya.** Apenas las herramientas estén (antes de la entrevista):
   `mkdir -p creator && bash .claude/skills/rough-cut/scripts/transcribe.sh --prefetch > creator/prefetch.log 2>&1`
   en **segundo plano** (Claude Code: `run_in_background`; Codex: `nohup … &`). Descarga el motor y
   el modelo (~4,3 GB) mientras el creador responde; si el creador escribe en inglés añade `--lang en`
   (sin idioma baja el alineador de español). Log completo:
   `${VIDEO_EDITOR_WORK:-/tmp/video-editor}/_prefetch/prefetch.log`. Es idempotente; si falla, sigue:
   la primera edición lo descarga (y una transcripción espera a un prefetch en curso). No esperes.

## Paso 2/5 · ¿Quién eres?

**a) ¿Lo conozco?** `python3 workflows/profile.py status`.
- **Código 0 (ACTIVO)** → saluda por su nombre, muestra `python3 workflows/profile.py show` y ofrece en una línea:
  **editar ya** · **actualizar mi estilo** (Paso 3) · **nuevo perfil** (otro creador o cliente) ·
  **cambiar de perfil** (`python3 workflows/profile.py list` / `python3 workflows/profile.py use`). Si su `creator/perfiles/<slug>/perfil.json` tiene
  `"onboarding": "rechazado"`, dile que ahora sí puede enseñarte su estilo y sigue con b) sobre ESE
  perfil (usa `python3 workflows/profile.py set`, no `python3 workflows/profile.py new`).
- **Código 3 con «perfil(es) guardado(s)»** → hay perfiles pero ninguno activo: `python3 workflows/profile.py list`, pregunta
  cuál es el suyo, `python3 workflows/profile.py use <slug>`.
- **Código 3 sin perfiles** → primero c) (¿viene de otra versión?), luego b).

**c) ¿Actualizó el kit? (revisión G2)** Cada versión es una carpeta nueva y `creator/` no viene en el
ZIP. Busca una versión anterior (funciona en bash y zsh):
`find .. -maxdepth 3 -type d -ipath '../*video*editor*/creator/perfiles' 2>/dev/null | grep -vF "../$(basename "$PWD")/"`. Si encuentras una, o el creador te da la ruta de su kit anterior o un `.zip` exportado:
- carpeta anterior → `mkdir -p creator && VIDEO_EDITOR_KIT="<ruta del kit anterior>" python3 workflows/profile.py export "$PWD/creator/perfil-anterior.zip"`
  (usa el `profile.py` de ESTA versión y solo lee la carpeta anterior; nunca la modifiques), luego
  `python3 workflows/profile.py import creator/perfil-anterior.zip`;
- archivo `.zip` → `python3 workflows/profile.py import "<archivo.zip>"` (si choca con un perfil existente, pregunta antes de
  usar `--replace`).
Después `python3 workflows/profile.py status` → si quedó activo, salta a Paso 4 (muestra su estilo) y luego Paso 5. Si la
carpeta anterior no tiene `creator/` (kits v1.0–v1.2), no hay nada que traer: sigue con b).

**b) Las 5 preguntas, en UN mensaje.** Antes, abre las muestras de subtítulos para que las vea:
macOS `open assets/onboarding/subtitulos-ABC.png` · Windows `cmd //c start "" assets/onboarding/subtitulos-ABC.png`
· Linux `xdg-open …`. (Si el cliente muestra imágenes en el chat, muéstrala también.) Luego envía:

> **Paso 2/5 · ¿Quién eres?** Responde lo que quieras en un solo mensaje; lo que dejes en blanco
> queda con el valor entre [corchetes]. Escribe **ok** para aceptar todo.
> 1. **Tu nombre o marca**, tu **@** y la **frase final** de tus videos (tu llamada a la acción). [sin @ ni frase]
> 2. **Dónde publicas** y **cuánto duran** tus videos. [Reels, TikTok y Shorts · ~90 s]
> 3. **Subtítulos:** A (caja), B (borde) o C (grandes, una palabra en amarillo) — te abrí la imagen —, o **ninguno**. [A]
> 4. **Muletillas** («eh», «este», «o sea»): **quitar todas**, **dejar las naturales** o **preguntarme**. [dejar las naturales]
> 5. **Palabras que se escriben mal** al transcribir: nombres, marcas, jerga (ej. «Klaud → Claude»). [ninguna]
>
> ¿Ya usabas una versión anterior del kit? Dime en qué carpeta está y traigo tu estilo en lugar de preguntarte todo.

**Guardar las respuestas.** Solo lo que el creador DIJO va con `--source respuesta` (lo que aceptó
con «ok» se queda como valor inicial, así sus videos de referencia pueden afinarlo en el Paso 3).
1. Perfil: si no hay activo → `python3 workflows/profile.py new "<marca o nombre>" --nombre "<nombre>"` (sin nombre → `python3 workflows/profile.py new mi-estilo`).
2. `python3 workflows/profile.py set creador.marca "<marca>" --source respuesta`, igual `creador.handle "@<usuario>"`, `creador.cta "<frase>"`.
3. `python3 workflows/profile.py set plataformas "reels,tiktok" --source respuesta` (minúsculas: reels, tiktok, shorts, youtube,
   linkedin…) y `python3 workflows/profile.py set duracion_objetivo_s 60 --source respuesta`.
4. Subtítulos — valores exactos por opción (la vista previa `assets/onboarding/subtitulos-*.png` está
   dibujada con estos mismos valores):

   | opción | estilo | palabras | mayusculas | color_texto | color_fondo | posicion_y | tamano_px |
   |---|---|---|---|---|---|---|---|
   | **A · caja** (= valores iniciales del kit; «ok» elige A) | `caja` | `4` | `false` | `#ffffff` | `#000000` | `0.50` | `49` |
   | **B · borde** | `borde` | `4` | `false` | `#ffffff` | `#000000` | `0.78` | `52` |
   | **C · grande** | `borde` | `2` | `true` | `#ffffff` | `#000000` | `0.70` | `84` |
   | **ninguno** | `ninguno` | — | — | — | — | — | — |

   - **Eligió A, B o C de forma explícita** → guarda TODA la fila con `--source respuesta`, incluidos
     `posicion_y` y `tamano_px`: el tamaño y el lugar son parte del look que eligió en la imagen (C sin sus
     84 px deja de ser «grande», c3 2026-09-29). **C** además: `python3 workflows/profile.py set subtitulos.color_resaltado "#ffd400"
     --source respuesta` (la palabra que se está diciendo se pinta amarilla; ambos constructores lo hacen).
     Si luego el Paso 3 mide otra posición o tamaño en sus videos, `learn` no pisa la respuesta: díselo en una
     línea («En tus videos los subtítulos van a 76% y 49 px; dejé los de la opción C. ¿Prefieres los tuyos?»)
     y cambia solo si dice que sí.
   - **Respondió «ok» o no eligió** → no guardes nada de subtítulos todavía: el Paso 3 mide sus videos y
     gana la medida; lo que quede sin medir se queda en A (los valores iniciales del kit).
   - El estilo decide el constructor: `caja` → explainer (caja), `borde` → cualquiera de los dos dibuja
     texto con contorno y sin caja, `ninguno` → no hay capa de subtítulos.
5. Muletillas: quitar todas → `todas` · dejar las naturales → `naturales` · preguntarme → `preguntar`
   (`python3 workflows/profile.py set corte.muletillas <valor> --source respuesta`).
6. Cada palabra: `python3 workflows/profile.py word "<como sale mal>" "<como se escribe>"` (una sola palabra a cada
   lado). **Si lo que sale mal es una palabra real** (p. ej. «cloud» o «groove» lo son; «clot» no), una corrección
   automática la cambiaría también cuando la diga de verdad: pregúntale en una línea («¿dices "cloud" alguna vez
   en tus videos?») y, si sí, márcala para revisar con `python3 workflows/profile.py word "<palabra>"` (sin
   corrección). Varias palabras → también solo marcar.
7. **brand-kit.md, parte A** — rellena con lo MISMO (no preguntes dos veces), solo los campos vacíos:
   `Brand / creator name`, `Exact spelling of names and products` (las palabras del punto 5),
   `Preferred call to action`, `Website or social handle`. No toques los demás ni la parte B. Di una
   línea: «Tu brand-kit ya tiene tu nombre, @ y frase; cuando quieras tus colores y fuentes en los
   gráficos, di **aplica mi brand kit**.» No lo apliques ahora.

## Paso 3/5 · Aprender de tus videos

> **Paso 3/5 · Aprender de tus videos.** Pásame 1 a 3 videos **terminados** que te gusten: tuyos, o de
> alguien cuyo estilo quieras seguir. Arrastra los archivos aquí (necesito el archivo, no el enlace).
> Se analizan en tu computador, no se suben a ningún lado ni se usan dentro de tus videos. ¿No tienes?
> Escribe **sin videos**.

- **Copia, nunca muevas:** `cp "<archivo>" creator/perfiles/<slug>/referencias/` (el slug de `python3 workflows/profile.py status`).
- **Mide:** `uv run workflows/style-learn.py creator/perfiles/<slug>/referencias --out creator/perfiles/<slug>/estilo-medido.json`
  Tarda: medido en un Mac M, ~1–1,5 min para dos referencias de ~1 min (la transcripción corre en paralelo
  con el análisis de imagen; si la descarga del Paso 1 sigue en curso, mide sin transcripción y afina en el Paso 5).
  Lánzalo en segundo plano y, mientras, adelanta el punto 7 del Paso 2 o pide el clip del Paso 5.
  Si mandan videos largos, pide los 1–2 más representativos de menos de 90 s.
- **Aprende:** `python3 workflows/profile.py learn creator/perfiles/<slug>/estilo-medido.json`. Respeta lo que el creador respondió.
- **El momento «me conoce»: dile lo medido en 3 líneas, con sus números**, por ejemplo:
  «En tus videos hay 14 cortes por minuto (una toma cada 2,1 s) · el 90% de tus pausas dura menos de
  0,35 s · tus subtítulos van a 72% de alto, 2 palabras a la vez; tus videos duran ~45 s.»
  Lo que no se pudo medir (subtítulos no detectados, música dudosa) se queda con el valor inicial; no
  lo inventes (revisión G4).
- Luego guarda `posicion_y`/`tamano_px` de su opción de subtítulos si siguen en `default` (Paso 2, punto 4).
- **Sin videos:** «Me quedo con los valores iniciales del kit; en tu ESTILO.md dicen *valor inicial
  del kit*. Cuando tengas videos, di **actualizar mi estilo**.» Aplica igual el punto de `posicion_y`/`tamano_px`.
- Si `style-learn` falla (sin `uv`, video ilegible), dilo en una línea y sigue con los valores iniciales.

## Paso 4/5 · Tu estilo

`python3 workflows/profile.py show` y pega su salida tal cual (es el resumen en español claro; también escribe
`creator/perfiles/<slug>/ESTILO.md`). Luego:

> ¿Algo no es como editas? Corrígelo en una frase («pausas más cortas», «subtítulos más arriba», «sin música»).

Cada corrección → `python3 workflows/profile.py set <clave> <valor> --source respuesta --reason "<sus palabras>"`, y vuelve a
mostrar solo la línea cambiada. Guía rápida:

| dice | clave → valor |
|---|---|
| más ágil / más cortes · más tranquilo | `corte.agresividad` → `fuerte` · `suave` |
| pausas más cortas · más largas | `corte.pausa_max_s` → baja/sube 0,1 (rango 0,10–1,50) |
| subtítulos más grandes · más pequeños | `subtitulos.tamano_px` → ±10 (28–120) |
| subtítulos más arriba · más abajo | `subtitulos.posicion_y` → ∓0,08 (0,10–0,85) |
| menos/más palabras en pantalla | `subtitulos.palabras` (1–8) |
| en mayúsculas | `subtitulos.mayusculas` → `true` |
| sin/con zooms · sin gráficos · muchos gráficos | `graficos.zooms` · `graficos.densidad` → `ninguna`/`basica`/`completa` |
| con música / música más baja | `musica.activa` → `true` · `musica.volumen_db` (−36 a −8) |
| elegir la toma yo | `corte.tomas` → `preguntar` |

Si no reconoces la clave, `python3 workflows/profile.py explain` lista todas. Nunca edites `perfil.json` a mano.

## Paso 5/5 · Tu primer video

> **Paso 5/5 · Tu primer video.** Pásame un clip corto sin editar (hasta 60 s) y lo edito con tu estilo.

- Mide la duración (`ffprobe -v error -show_entries format=duration -of csv=p=0 "<clip>"`). Si pasa de
  60 s, dile que la primera edición será más larga y ofrece usar solo el primer minuto; no lo bloquees.
- Si la descarga del Paso 1 sigue en curso (`tail -2 creator/prefetch.log`), dilo: la transcripción
  espera a que termine.
- Corre la skill **`edit-video`** completa (ella lee el perfil activo en su paso 0 y lo anota en RUN.md).
  Respeta todas sus puertas: revisión del borrador y exportación aprobada.
- **Afinar la medición (en segundo plano, sin preguntar):** si en el Paso 3 la descarga seguía en curso,
  `style-learn.py` midió las pausas solo por energía (dice «sin transcripción»). Ahora que el motor está
  instalado, relánzalo con las mismas referencias y `python3 workflows/profile.py learn` otra vez: solo afina valores `medido`, nunca
  lo que el creador respondió. Dile en una línea qué cambió («Ya medí tus pausas con palabras: …»).
- Tras el MP4 final, ofrece (opcional): «¿Te hago un ANTES/DESPUÉS de 10 s para ver la diferencia?» →
  `python3 workflows/before-after.py projects/<job> --seconds 10` → `projects/<job>/outputs/<job>.antes-despues.mp4`.

**Cierre (3–4 líneas):**
- Tu estilo está en `creator/perfiles/<slug>/ESTILO.md` (ábrelo cuando quieras).
- Sigue aprendiendo: cuando pidas un cambio en una revisión, te preguntaré **«¿siempre así?»**; si dices
  que sí, queda en tu perfil y te digo qué aprendí.
- Varios creadores o clientes: **«nuevo perfil»** y **«usa el perfil <nombre>»**.
- Al instalar una versión nueva del kit: escribe **empezar** en la carpeta nueva y dime dónde estaba la
  anterior (o `python3 workflows/profile.py export mi-estilo.zip` y luego `import` en la nueva).
