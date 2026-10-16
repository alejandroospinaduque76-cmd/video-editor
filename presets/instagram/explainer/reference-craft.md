# Reference Craft — el lenguaje visual que rompe en IG (research 2026-09-14)

**Qué es esto.** Los 12 posts que más rompieron en una semana en 4 cuentas del nicho
(@soyenriquerocha, @nateherkai, @crece30x, @lucianomusellaa — capturas y texto íntegro en
[`reference/ig-research-2026-09-14/`](reference/ig-research-2026-09-14/)), leídos plano a plano y
traducidos a la mecánica de ESTE motor, más las dos librerías que llegaron con el estudio
([`assets/motion/`](../../../assets/motion/README.md): 34 fondos wireframe, 164 iconos animados y 109 ilustraciones recortadas con alpha en `illustrations/`).

**Es el DEFAULT del explainer corto de este preset.** "Edita este reel" produce este lenguaje sin
pedirlo (cámbialo en tu `brand-kit.md` si tu marca pide otro); `graphics-plan` lo lee en el Step 0 junto a
[`default-overlay-style.md`](default-overlay-style.md) (que sigue siendo el contrato de zonas y el
panel primitivo). Las reglas del brand kit siguen locked y mandan sobre todo lo de abajo: **sin emojis ·
Playfair Display + Public Sans (ambas OFL, incluidas en `assets/fonts/`), nada más · paleta cian `#46D5FF` / azul `#1B35D0` / navy `#1E2A47` /
`#131A2E` / casi-negro `#080A14` / blanco · logos reales · "animación" = algo pasa en la escena ·
transiciones mínimas · subtítulos 2 palabras, abajo, sin caja.** Nada aquí las contradice; todo aquí
las llena de contenido.

---

## 0. LA LEY DE LA CARA — nada la tapa, nunca, y se MIDE (2026-09-14)

Su regla clave, dicha tras ver un chip sobre sus ojos: **ningún gráfico toca la cara: ni
subtítulos, ni chips, ni fichas, ni iconos, ni texturas, ni líneas.** Un número fijo de zona no lo
puede prometer — un clip de WhatsApp 720×1280 escalado a 1080×1920 pone los ojos en y≈1000 y la
barbilla en y≈1250, justo donde un "pecho y 1040 → 1200" caería. Por eso la cara se detecta en el
footage y todo se coloca contra un **keep-out medido**:

```bash
uv run workflows/face-guard.py zones <raw|base> --from 3.7 --to 6.0 [--annotate zones.png]
#  KEEP-OUT (cara + pelo 140 / lados 70 / mandíbula 50):  x 210→870 · y 640→1330
#  free zones:  above  y 200→640 · below  y 1330→1620 · left — · right —
```

- El keep-out es la **unión** de todas las caras del tramo más los márgenes (pelo arriba, orejas a
  los lados, mandíbula abajo); una detección fallida nunca lo encoge.
- **Las zonas libres son las únicas zonas.** Cada pieza de § 2 nombra una preferencia (arriba,
  abajo, lado) pero la coordenada real sale de `zones` para ESE tramo y se escribe en la celda del
  plan. Si la zona preferida no existe (cabeza alta y grande → no hay "arriba"), la pieza baja bajo
  la barbilla, se encoge, o se va a un cutaway (§ 2.16) — nunca se fuerza sobre la cara.
- **Las texturas también obedecen**: un Element sobre el footage lleva un agujero difuminado que
  CONTIENE el keep-out entero (la receta única, con sus números: § 2.7) o se limita a la zona
  `above`; las líneas de una rejilla cruzando la cara cuentan como taparla.
- **Los subtítulos también**: 2 palabras, abajo, y su `y` es `below.y0 + 40` medido, no 1380 de
  memoria (su rango aprobado 1380–1480 salía de tomas con la barbilla en ~1250; en una toma más
  cerrada bajan). Esa franja es SUYA: ningún otro gráfico se planifica en ella.
- **Quién mide y cuándo:** `graphics-plan` en su Step 2, una vez por segmento de V1 (clip raw +
  ventana de `cuts.json`), ANTES del storyboard, con `--zoom 1.09` en los segmentos que llevarán
  punch-in. Escribe el `keepout` de cada celda, y deriva los valores de todo el reel: **zona del
  titular** = la `above` más corta entre segmentos (manda la cabeza más alta); **tope de
  subtítulos** = el `below.y0` más bajo entre segmentos + 40 (manda la barbilla más baja), escritos
  en las celdas `headline` y `captions`. `graphics-build` sólo re-mide celdas sin keep-out; `check`
  corre tras colocar, y los punch-ins los lee de cualquier beat con `push_in: true` que solape el
  gráfico (la cara crece un 9 % en ellos: un chip pegado al borde de la zona los pisa).
- **La puerta (short-form):** `uv run workflows/face-guard.py check projects/<job>` barre cada
  frame de cada overlay colocado (subtítulos y titular incluidos, cada frame contra la cara de SU
  segmento) y falla con tinta dentro del keep-out. `graphics-qa.py` rechaza 9:16 por diseño, así que
  en vertical ESTA es la puerta del paso 5 y corre antes de `edit-review`. Una desviación consciente
  es una línea en `hf-graphics/qa-waivers.json` (`{"g7": {"face": "…"}}`), nunca una frase.

Lo que sí puede ir "sobre él": lo que está DETRÁS (§ 2.6, § 2.11 — el recorte va encima) y los
punch-ins, que mueven el footage entero.

---

## 0b. LA ZONA SEGURA DE INSTAGRAM — regla del usuario, nunca se rompe (2026-09-28)

Del reel de referencia que mandó el usuario (jun_yuh, "text placement": ojos / subtítulo / título / zona segura /
zona de peligro / punch-in con la misma línea de ojos / borde en fondos cargados), medido sobre un iPhone alto,
donde Instagram llena la ALTURA y recorta los lados del reel. En píxeles de 1080x1920:

- **Zona segura (verde): x 180 → 905 · y 200 → 1507.** Todo lo que se lee o se reconoce vive dentro: texto,
  iconos, logos, fichas, filas de lista, también dentro de un cutaway (la placa de fondo sí puede llenar el frame).
- **Zona de peligro, "evítala a toda costa":** la columna de botones de la derecha (**x > 845 para y > 826**:
  like, comentario, compartir) y la franja de abajo (**y > 1507**: usuario, caption, audio).
- **Título / gancho arriba**; **ojos en la línea del tercio superior** (≈ y 672, 0.35 de la altura): si la
  toma los deja más abajo se reencuadra el footage (Movimiento: escala + posición, nunca un recorte ciego);
  **subtítulo justo bajo la cara**, a la altura del pecho.
- **Punch-in con la línea de ojos fija:** el zoom pivota en los ojos (Transform: punto de anclaje = posición =
  los ojos), nunca en el centro del frame.
- **Texto sobre fondo cargado lleva borde (stroke).**

Consecuencia de layout: con la cara al centro, las columnas laterales (x < 260 o x > 850) quedan fuera de la
zona o bajo los botones, así que **no hay gráficos laterales**. Los gráficos van arriba de la cabeza, en la
banda bajo los subtítulos (hasta y 1507) o en cutaways. La puerta: `workflows/face-guard.py check` mide la
tinta de cada overlay contra este rectángulo además de contra la cara.

---

## 1. Lo que hacen los que rompen (la lectura)

- **Estructura: gancho → prueba en pantalla → recurso.** 9 de 12 abren con una herramienta
  nombrada + una afirmación que pica ("Claude acaba de matar a los diseñadores web", "Astra le
  gana a Fable pero no en lo que tú crees"), lo PRUEBAN con grabación de pantalla real y cierran con
  el recurso. El cierre de comentarios es suyo, no nuestro (aquí no vive CTA); el ORDEN sí se copia.
- **La tipografía grande y bold es la protagonista.** O un titular fijo arriba de principio a fin
  (Enrique: "La solución siempre fue GPT6 Astra + Fable5.1"), o el subtítulo en mayúsculas con la
  palabra de poder en otro color / otra fuente (Nate: NOW BUILD *websites*). Nunca las dos cosas
  compitiendo en el mismo frame.
- **Cada sustantivo tiene su imagen** — logo real en ficha, chip con la frase, icono. La cámara
  sola no dura más de ~3 s. Los logos son fichas redondeadas al pecho, en el color de la marca.
- **La prueba es real y va a pantalla completa**, con titular y subtítulos encima: el README del
  repo, la terminal, los docs, el chat. Zoom con lupa sobre la línea exacta.
- **Profundidad.** La persona recortada con algo detrás (Elon Musk detrás de Luciano), o la
  pantalla arriba y la cara abajo (Nate). La cara nunca se tapa.
- **Lista pre-mostrada** (#1–#5 borrosos con flecha "THESE 5") para retener en un listicle.
- **De los carruseles de @crece30x** (no son video) se copia sólo la jerarquía: un número grande,
  una idea, UNA palabra en bold.
- **Lo que NO copiamos:** memes de stock (Document, don't manufacture — un cutaway de meme sólo si
  se pide por nombre), amarillo y verde (fuera de paleta), emojis, CTAs de comentarios.

### 1b. El reel de referencia #2 — Jack Mason × Greg LaV (añadido por él el 2026-09-14)

[instagram.com/reel/Db55l3zx7wS](https://www.instagram.com/reel/Db55l3zx7wS/) · 92 s · 16:9
publicado como reel · 14,3 K likes · frames `jm-*.jpg` en `reference/`. **Es el listón de "nivel
cinematográfico"**: producción alta, pero cada truco es reproducible aquí. Lo que hace, plano a plano:

- **Tipografía gigante DETRÁS de la persona** recortada sobre fondo blanco seamless ("WHY?",
  "investors", "dealflow", "personal brand", "authority"): la palabra de poder es un objeto de la
  escena, no un rótulo. Es nuestro `cutout.py` + el tipo en V3 bajo el recorte en V4 (§ 2.11).
- **Un SET para una sección larga**: la habitación naranja con un monitor retro que reproduce su
  footage, y las palabras habladas apareciendo en el espacio negativo a izquierda y derecha del
  monitor, 2–3 palabras, sincronizadas (10 s seguidos). El campo lo da la escena; los eventos son el
  tipo (§ 2.12).
- **Tarjetas de capítulo numeradas** ("1. ACCESS", "2. AUDIENCE", "3. AUTHORITY") en un marco de
  televisor/CRT con footage vintage suyo y un light-leak de entrada: la estructura se ve (§ 2.13).
- **La cifra rueda** ("$ 0M" → "$600M a year in revenue") al lado del producto: `countUp`.
- **Todo artefacto es real**: la tarjeta de perfil de IG, el contador "87.7K", el muro de reels
  desplazándose, el botón Boost en macro con un dedo. Ninguna pantalla dibujada.
- **Lista carrusel**: los tres ítems en vertical, el activo centrado y oscuro, los otros en gris
  claro arriba y abajo, desplazándose con la voz (§ 2.14).
- **B-roll del sujeto en ~40 % del runtime** (podcast, cafetería, feria, escalera), con UNA palabra
  por corte flotando en el espacio libre del plano, no siempre abajo (§ 2.15).
- **Dos fondos que alternan**: blanco seamless (presentador) y la habitación naranja (set) — la
  misma ley de rotación bg-light / bg-dark del preset long-form.
- **Transiciones con motivo**: whip con motion blur al entrar a un mockup, light-leak a una tarjeta
  de capítulo; el resto, corte seco.
- Es 16:9: el mismo lenguaje vale para un long-form de YouTube; en vertical se comprime a los
  tercios (set arriba, cara abajo).

---

## 2. El vocabulario — diez piezas

Cada pieza: qué es · dónde se vio · cómo se hace AQUÍ (zonas de 1080×1920, registro de
[`animations.md`](../../youtube/default/animations.md) vía `hf-anim.js`, paleta y fuentes suyas).
**Toda coordenada de abajo es una PREFERENCIA de zona (`above` / `below` / `left` / `right`); el
rectángulo real lo imprime `face-guard.py zones` para ese tramo (§ 0), dentro de las bandas seguras
(nada clave en y < 200 ni y > 1620).** Los "y ≈" que aparecen son el caso típico (barbilla ≈ 1250)
para que se entienda la escala, nunca un número que se copie.

### 2.1 Titular fijo (headline)

- **Qué:** 1–2 líneas arriba, desde el frame 0 hasta el final (o hasta el payoff, si el titular es
  la pregunta). Es la AFIRMACIÓN escrita, no la frase hablada: nombra la herramienta + lo que pica.
- **Visto en:** los tres reels de @soyenriquerocha (01–04, 11–17 en `reference/`).
- **Aquí:** el TOPE de la zona `above`: y 230 → 430 en el caso típico, ancho 940 centrado. Playfair Display
  Bold 64–74 px blanco con sombra ink (`text-shadow: 0 4px 0 #080A14, 0 14px 34px rgba(8,10,20,.75)`),
  UNA palabra en cian. Sin caja. `riseIn` en 0.00 (es el primer evento del video), `float('subtle')`
  toda su vida, sin salida (corta con el video) o `riseOut` 0.35 s antes del payoff. Una comp que
  dura todo el reel: > 20 s → partes (SOP de split del `graphics-build`). Como cubre TODAS las tomas,
  su keep-out es la unión de las tomas (`zones` sobre cada clip; manda la cabeza más alta): si la
  zona `above` de la toma más cerrada no aguanta dos líneas a 64 px, el titular pasa a UNA línea, y
  si ni eso cabe, el plan lo flagea (`⚠️ sin banda libre sobre la cabeza`) y propone titular lateral o
  en cutaway — nunca sobre el pelo.
- **Lock:** ≤ 7 palabras por línea, la más larga medida con PIL antes de fijar el cuerpo; las
  tarjetas de la zona `above` empiezan 40 px bajo el titular para no chocar con él; el titular y el
  subtítulo nunca dicen lo mismo al mismo tiempo.

**Tamaño mínimo de CUALQUIER texto en un reel: 54 px (Public Sans) / 60 px (Playfair Display) sobre
1080×1920.** Un label de 26 px ("Existe" sobre arena.ai, example-reel v2) no se lee en el teléfono —
él lo dijo el 2026-09-15. Los eyebrows de 23–26 px del preset long-form no existen aquí: lo que
no merece 54 px no merece estar en pantalla.

### 2.2 Chip de frase (keyword chip)

- **Qué:** la frase clave del beat en una píldora: blanca con texto casi-negro sobre fondos
  oscuros/cálidos, o navy con texto blanco y borde cian sobre fondos claros.
- **Visto en:** "A media semana" (03), "KILLED" (05), "AND INTERACTIONS" (31).
- **Aquí:** Public Sans Black 54–64 px, padding 18/34, radio 18, sombra `0 22px 50px
  rgba(8,10,20,.7)`. Zona **`above`**, 40 px bajo el titular (o bajo las fichas si las hay), o una
  zona lateral de ≥ 300 px de ancho. **Nunca `below`: esa franja es de los subtítulos, que corren
  siempre** (keep-out bottom + 40 es exactamente donde arranca el subtítulo, así que ahí no queda
  sitio). Cuando `above` no cabe (cabeza alta y grande) el chip NO se fuerza: la frase va al
  subtítulo como palabra de poder (§ 2.9) o el beat se corta a un cutaway (§ 2.16). `pop` en la
  palabra (−0.08 s), hold 1.2–2.0 s, `riseOut`. Uno por beat; nunca dos chips vivos.
- **Cuándo:** una frase corta que vale leer — una condición, un "gratis", un "en 3 líneas", una cifra
  con contexto.

### 2.3 Ficha de logo (logo tile)

- **Qué:** el logo REAL sobre una ficha redondeada; el color de la ficha es el de la marca,
  **muestreado** del archivo real (Claude `#d97757`, OpenAI negro, Gemini blanco…) o navy con borde
  cian cuando la marca no tiene color de ficha.
- **Visto en:** GPT-6 Astra badge (11), Fable 5.1 (13), Claude (15).
- **Aquí:** ficha 260–320 px, radio 32, sombra profunda, logo al 55 % de la ficha; nombre debajo en
  Public Sans SemiBold 26 px sólo si el logo es un símbolo sin nombre. Zona **`above`** (bajo el
  titular) o **`below`** si `above` no la aguanta; **la ficha se ENCOGE ENTERA a la zona** (200 px
  cuando la zona da 250, como en `reference/reference-craft-demo.jpg`), nunca se recorta ni se monta
  sobre el keep-out; una zona lateral sólo si mide ≥ 300 px de ancho. 2–4 marcas seguidas → fila en
  `above` con `pop` escalonado 4 f, encogidas hasta que la fila quepa. `pop` en el nombre, hold
  mientras se habla de ella, `riseOut`.
- **Fuentes:** `assets/logos/` (los nuevos van ahí: SVG de Simple Icons / Wikimedia, color
  muestreado del original, nunca de memoria — `default-overlay-style.md` § BORROWED PALETTES).

### 2.4 Icono animado (la librería)

- **Qué:** [`assets/motion/icons/`](../../../assets/motion/icons/README.md) — 164 iconos de línea
  animados (negocio, finanzas, inmobiliaria, tech, personas), en dos variantes con alfa:
  **`on-dark/`** (trazo blanco + cian de marca) para paneles navy y sobre el footage;
  **`on-light/`** (trazo casi-negro + cian) para fichas blancas. Sustituye para siempre al emoji.
- **Aquí:** `python3 assets/motion/find.py <palabra>` → slug. En la comp:
  `<video src="assets/icons/<slug>.webm" data-start="T" muted playsinline>` dentro de un wrapper
  `div` que recibe el `pop` (GSAP transforma el WRAPPER, nunca el `<video>`; el timing va en el
  `<video>` o en el wrapper, nunca en ambos). El icono reproduce su animación UNA vez desde la
  palabra (1–3 s, su último frame es la pose de reposo → hold), después `riseOut` del wrapper.
  Tamaño 220–360 px suelto; en ficha, panel navy 300×300 radio 32 con el icono a 200 px.
- **Lock:** el trazo no se recolorea a otra cosa que blanco/casi-negro + cian de marca; nunca dos
  iconos vivos salvo en una lista; el hold del icono cuenta como gráfico (nada de "no había nada").

### 2.5 Prueba en pantalla (proof)

- **Qué:** la grabación de pantalla o el artefacto real (repo, terminal, docs, DM, post, resultado)
  a pantalla completa 2–5 s, con titular y subtítulos encima. Es el acto 2 del reel.
- **Visto en:** 04 (docs de Codex), 18 (README de Humanizer), 34/35 (OmniRoute, chat), 49 (Grok CLI).
- **Aquí:** es b-roll → **V2**, corte seco EN la palabra (−30 ms), sin fundidos, extendido ~7 f si
  sale en un corte de V1 (regla suya). Escalado a 1080 de ancho o recortado a la región que importa.
  **Zoom con lupa** (`annotation`): círculo de 420 px con la región a 1.6×, borde cian 4 px, sombra,
  `pop`, hold 1.5–2.5 s sobre la línea exacta (el comando, la cifra). Alternativa: caja de resaltado
  cian que se dibuja con `drawOn`. Cuando la grabación sólo tiene sentido con la cara visible, va
  recortada a la zona **`above`** (Nate, 28/29/31) — su alto es el de la zona, no 760 px fijos: si la
  zona da menos de ~500 px la grabación no se lee, y entonces la prueba es a pantalla completa (sin
  cara, contada en el 25 %) o se pide un plano más abierto.
- **Lock:** si no hay grabación ni captura del artefacto en `raw/` o `assets/`, el plan lo **flagea y
  lo pide** (`⚠️ falta la prueba de X`) — nunca se dibuja una pantalla falsa (real artifacts beat
  drawn ones). Un proof es un `readable`: la captura completa se ve quieta ≥ 2 s.

### 2.6 Escena detrás de él (bed behind the cutout)

- **Qué:** la persona recortada y algo VIVO detrás: un fondo wireframe de
  [`assets/motion/elements/`](../../../assets/motion/elements/README.md), la captura/foto de la
  persona o el artefacto nombrado, una lluvia de props dibujados (los billetes de example-reel). Es el
  "dinero cayendo detrás de mí" de sus reglas.
- **Visto en:** Elon Musk detrás de Luciano (46/47).
- **Aquí:** `uv run workflows/cutout.py <raw-o-base> --from T0 --to T1 --out
  projects/<job>/hf-graphics/cutout/renders/cutout-<beat>.mov` → ProRes 4444 de la persona
  (MediaPipe, suavizado temporal + blur de máscara). Premiere: el fondo en **V3**, el recorte en
  **V4**; V1 sigue debajo y rellena los bordes de la máscara. 2–4 s por beat; entra y sale con
  corte o disolución 5 f. Elemento por sustantivo (catálogo): `full` coverage reemplaza la
  habitación, `sparse` es un prop grande detrás del hombro; tinte cian/azul con
  `colorchannelmixer` cuando el blanco pese demasiado.
- **Lock:** el recorte se verifica en el program monitor (pelo, manos, hombros) antes de seguir;
  si la máscara respira, la escena va al top-half como panel, no detrás. `face-guard.py check` lo
  mide: con una fila `cutout` en la timeline juzga cada frame contra la silueta (la silueta debe
  cubrir ≥ 85 % de la cara detectada en ese instante; si la máscara falla, el frame se juzga como
  cualquier otro). **Y una advertencia de gusto (2026-09-15):** él quitó la lluvia de billetes detrás
  de sí mismo en example-reel ("no está siendo bueno") — la escena detrás funciona con UN elemento grande
  y legible (una foto, una palabra, una pantalla), no con partículas pequeñas cayendo alrededor de la cabeza.

### 2.7 Textura de pantalla (screen texture)

- **Qué:** un Element con alfa (blanco → alfa por luma) sobre el footage, opacidad 0.35–0.6, con un
  AGUJERO difuminado alrededor del keep-out o limitado a la zona `above`. Un beat "tech", el puente
  hacia una prueba, el respiro de un titular largo.
- **Aquí — LA receta del agujero (la única; § 0 apunta aquí):** dentro de una comp, `<video>` de la
  versión webm (`FORMAT=webm make-alpha.sh`) en un wrapper con
  `mask-image: radial-gradient(ellipse <0.71·kw>px <0.71·kh>px at <cx>px <cy>px, transparent 100%, #000 125%)`
  — semiejes = **0.71 × el ancho/alto del keep-out** (√2/2: así la parada transparente contiene las
  cuatro ESQUINAS del rectángulo; con kw/2 × kh/2 la elipse queda inscrita y las esquinas del
  keep-out, ~20 % de su área, siguen entintadas — el gate lo falla) —, o con
  `clip-path: inset(0 0 <1920 − above.y1>px 0)` para dejarla sólo arriba. **El wrapper de la textura
  va FUERA de `#float`**: el agujero se queda sobre la cara, que no flota. Colocada directa en Premiere
  (`make-alpha.sh` → ProRes) sólo cuando la cara no está en el plano. Recortada a la duración del
  beat, nunca > 4 s seguidos. El modelo que renderiza: `reference/reference-craft-demo.html`.
- **Lock:** las líneas de una rejilla cruzando la cara cuentan como taparla (el gate mide alfa > 40,
  y una textura al 0.35 da ~90): sin agujero o recorte no pasa; probar el agujero con un Element
  `full` (`el-02`), no sólo con uno `medium`; nunca dos texturas a la vez; `full` coverage al 0.35,
  `sparse` al 0.6.

### 2.8 Lista pre-mostrada (list pre-show)

- **Qué:** en un listicle (3–5 cosas) TODAS las filas aparecen en el "hay N" como fichas atenuadas y
  borrosas con su número, y cada una se enciende (nitidez + cian + icono) en su palabra.
- **Visto en:** 33 (#1–#5 borrosos, "THESE 5").
- **Aquí:** panel primitivo en la zona **`above`** (bajo el titular): filas de 118 px, número Playfair Display
  Bold 54 px, texto Public Sans Bold 40 px, icono `on-dark` 90 px — **caben `floor((alto de la zona −
  padding) / 118)` filas**; si son menos que los ítems, filas de 96 px con tipo más pequeño, y si
  tampoco, la lista pasa a carrusel (§ 2.14) o a cutaways (§ 2.16), nunca baja sobre el pelo.
  Estado "off" = `opacity:.35;
  filter:blur(3px)` **declarado en CSS** y encendido con un tween a `blur(0px)` (declararlo en CSS es
  lo que deja a GSAP interpolar desde un número; nunca un tween de `filter` sobre un valor no
  declarado — `graphics-build` § gotchas). `riseIn` del panel, `pop` por fila al encenderse. > 8 s →
  partes (split SOP).

### 2.9 Subtítulo con palabra de poder

- **Locked (sus reglas):** 2 palabras, abajo — `y = below.y0 + 40` medido en la toma con la barbilla
  más baja (§ 0; `ANCHOR_Y` del builder = ese tope + la mitad del alto del bloque, porque el builder
  ancla el CENTRO) —, sin caja (`BOX_COLOR = "transparent"`), blanco + sombra ink, revelado por
  frase, Public Sans Black; la activa del karaoke en cian (example-reel v2).
- **Lo nuevo del research:** UNA palabra de la frase puede cambiar de voz — cian, o **Playfair Display
  Italic** para la palabra emocional / de marca (Nate: "websites" en script, "entire design").
  Máximo una palabra estilizada por frase; nunca amarillo ni verde; el titular y el subtítulo no
  repiten la misma palabra a la vez.

### 2.10 Corte, ritmo, sonido

- **Punch-in** (Transform 100 → 108/109, cúbico, el comando `zoom` del bridge) en las 2–4 frases
  fuertes; nunca en cada frase. Va en el plan como `push_in: true` en el beat hablado (también en
  short-form), porque la cara crece un 9 % y todo gráfico vivo en ese tramo se mide y se juzga contra
  la cara agrandada (§ 0).
- **Transiciones:** corte seco por defecto; disolución 5 f sólo cuando cambia el tipo de plano; cero
  zooms cruzados (sus palabras: "agresivas o innecesarias").
- **Cada aparición tiene su sonido** (paso 6, `sfx-plan.py` lee las llamadas del registro): pop →
  pop, chip → click, logo → whoosh corto, prueba → whoosh, escena detrás → riser suave 0.5 s. Los
  iconos animados no suenan por dentro; suena su `pop` de entrada.
- **B-roll y prueba EN la palabra**, nunca en el inicio de la frase; cutaways pegados al `end` real
  del anterior, sin huecos de 1 frame (sus reglas).

### 2.11 Tipo gigante detrás (type behind the cutout)

- **Qué:** la palabra de poder del beat como OBJETO de la escena: Playfair Display Bold 260–420 px en cian o
  azul de marca, detrás de la persona recortada, sobre un fondo liso (blanco `#FFFFFF` o navy
  `#131A2E`) o sobre el propio footage.
- **Visto en:** jm-16s "WHY?", jm-42s "investors", jm-86s "personal brand".
- **Aquí:** `cutout.py` para el tramo (2–4 s) → V4; la comp del tipo (y del fondo liso si lo hay)
  → V3. La palabra entra con `slam` (es un stamp) o `riseIn` si es una frase; `float('medium')` en
  la palabra, `subtle` en el resto. En vertical la palabra arranca en la zona `above` y puede bajar
  hasta asomar detrás de los HOMBROS (bajo el keep-out, donde el recorte la cubre de verdad); lo que
  quedaría detrás de la CARA sólo se ve donde la máscara respira (pelo, mandíbula) y por eso el gate
  la juzga restando el alfa del recorte (`cutout` row en `placement.json`): si aun así hay tinta en el
  keep-out, la palabra sube o se encoge.
- **Lock:** una palabra (dos como máximo) por beat; en cian sobre blanco medir el contraste — si no
  lee, azul `#1B35D0`; la palabra hablada y la escrita coinciden al frame; el recorte se verifica en
  el program monitor antes de dar la pieza por buena.

### 2.12 El set (a stage for a long section)

- **Qué:** para una sección de 8–15 s, la habitación deja de ser la habitación: un campo navy con
  un Element de suelo en perspectiva (`el-01`) o rejilla (`el-02`), un DISPOSITIVO (monitor,
  portátil, teléfono: marco dibujado con el panel primitivo, radio 28, bisel cian 2 px, sombra
  profunda) reproduciendo el footage o la prueba, y las palabras habladas apareciendo en el
  espacio negativo a los lados, 2–3 palabras, `riseIn`/`riseOut` sincronizadas.
- **Visto en:** jm-30s / jm-34s / jm-75s (la habitación naranja + monitor).
- **Aquí:** es una comp de partes (split SOP), fondo estático, el footage entra en el dispositivo
  como `<video>` recortado del base cut (o el clip vive en V1 escalado y la comp deja el hueco en
  alfa — más barato de iterar en Premiere: la comp es el marco + el campo con un agujero
  transparente y V1 se escala/posiciona con Movimiento para caer dentro). En vertical el set vive
  en la zona `above` con el dispositivo encogido a su alto (el footage dentro del dispositivo es
  otra copia de V1, no la cara del plano); si la zona da menos de ~450 px, el set se hace a pantalla
  completa como cutaway con el footage dentro del marco (sin cara fuera del marco) y cuenta en el 25 %.
- **Lock:** un set por video, en la sección que explica el PROCESO; nunca en el hook.

### 2.13 Tarjeta de capítulo (numbered chapter card)

- **Qué:** cuando el guion tiene estructura ("tres cosas", "paso 1/2/3"), cada cabecera es una
  tarjeta de 1.2–1.8 s: número + palabra en Playfair Display Bold 120–160 px sobre un marco de dispositivo
  (CRT/monitor dibujado) con un fragmento del footage dentro y un Element `sparse` detrás; entra
  con corte + un flash de luz cian 6 f (opacidad 0.6 → 0 sobre un `div` blanco/cian), sale con corte.
- **Visto en:** jm-24s "1. ACCESS", jm-67s "3. AUTHORITY".
- **Aquí:** una comp por capítulo, a pantalla completa como cutaway (V2, sin cara, 1.2–1.8 s; si
  empieza en un corte de V1 el validador exige el frame exacto) o, con la cara en plano, encogida a
  la zona `above` (el numeral baja a 90–110 px si hace falta). El SFX del capítulo es el whoosh + un
  impacto suave (paso 6).

### 2.14 Lista carrusel (list carousel)

- **Qué:** 3–5 ítems en vertical; el activo centrado, Public Sans Black 64 px blanco (o casi-negro
  sobre blanco); el anterior y el siguiente a ±150 px en `--muted` al 40 %; al cambiar, toda la
  columna se desplaza 150 px con `power2.out` 0.45 s y el nuevo activo sube de 40 % a 100 %.
- **Visto en:** jm-80s (More Status / More leverage / More Reputation).
- **Aquí:** una sola comp (partes si > 8 s) en la zona `above` (tres filas de 150 px = 450 px: si
  la zona da menos, el paso baja a 110 px y el tipo a 48 px, o la lista se va a cutaway);
  alternativa a la lista pre-mostrada cuando los ítems son frases y no sustantivos con icono. El
  desplazamiento es un tween de `y` en el wrapper de la columna, nunca tres comps.

### 2.16 Icono como B-roll (el cutaway) — reel de referencia #3, @lukedavis

- **Qué:** el icono o el Element ES el plano: un cutaway sin cara de 2–6 s en el que la voz sigue
  y el gráfico ocupa el frame — campo navy `#131A2E` con una rejilla tenue (`el-02` al 0.12 o la
  rejilla CSS de 100 px), el icono `on-dark` centrado con **600–700 px de tinta visible** (los webm de
  la librería llevan aire dentro: el contenedor sale a ~800 px; medir el bbox en el render, no el
  contenedor), y en el tercio superior UNA cosa escrita: la cifra, el dato o la palabra de poder
  (Public Sans Black 90–120 px, cian la palabra clave) — **nunca la frase hablada**: la frase la
  llevan los subtítulos de V5, que siguen corriendo (en lukedavis la frase palabra a palabra ES su
  subtítulo; aquí ya existe). Lo que lo hace b-roll y no un stamp: **el gráfico enacta la
  afirmación** — un % que baja, billetes que se apilan uno a uno, una línea que se dibuja, un donut
  que se reparte — mientras el subtítulo completa la frase.
- **Visto en:** `ld-*.jpg` — 38 s seguidos sin cara, un gráfico por beat cada ~4 s.
- **Aquí:** es un full-frame → **V2 como b-roll** (corte seco en la palabra, corte de vuelta a la
  cara antes del siguiente beat hablado; en el plan la celda lleva `"cutaway": true` y el placer la
  deriva a V2), renderizado opaco `GRAIN=0 render.sh <id> full` (el knob existe en
  `fullscreen-render.sh` desde 2026-09-15; sin él la placa lleva el grano que en vertical se vuelve ruido). **La placa es UNA por reel** (el mismo campo + rejilla en todos los cutaways;
  sólo cambia lo que hay encima, como en lukedavis). El icono entra con `flash` (el strobe del
  registro, 7 f, sólo a la tasa de la timeline — el cutaway no lleva `STEP_FPS`) o `pop`, y se queda;
  **un hold de más de 3 s cambia de estado a mitad, en la palabra que lo motiva** (la cifra baja
  con `countUp`, los billetes se apilan uno a uno, la línea se dibuja con `drawOn`, el icono se
  atenúa al 55 % en "vale menos") — lo que en el reel de referencia dura 0.8–1.0 s por cambio; sale
  con `riseOut` o `flash` invertido y 1–3 frames de placa vacía antes del siguiente elemento, nunca
  placa contra placa. Dos o tres iconos de la librería se pueden combinar en un cutaway (el billete +
  la flecha abajo) si cuentan UNA cosa. Los subtítulos siguen corriendo abajo en el `y` del reel (el
  medido en las tomas con cara, § 0: en un segmento sin cara `zones` no devuelve `below`, y el
  subtítulo NO se mueve), así que **todo elemento del cutaway termina 40 px por encima de ese `y`**
  y el chip del payoff vive justo ahí (caso típico: termina ≤ y 1450). El texto del cutaway es el
  gráfico, no un segundo subtítulo. Modelo que renderiza: `reference/reference-craft-cutaway-demo.html`
  (+ `.jpg`).
- **Cuándo:** el beat que describe algo abstracto sin artefacto real (inflación, tiempo, un
  proceso, "cada vez que…"), o cuando el keep-out de la cara no deja zona libre para una ficha —
  en vez de forzarla sobre él, se corta al icono.
- **Lock:** 2–6 s por cutaway, ≤ 3 seguidos, y cuentan dentro del 25 % de "prueba/cutaway" de § 3;
  la cara vuelve siempre antes de una frase fuerte hablada a cámara (un punch-in nunca cae en un
  cutaway).

**B-roll GENERADO (Higgsfield):** atmósfera, una foto o captura real que cobra vida, el fondo de un
set — nunca la prueba, nunca gente de stock. Reglas, prompt en la paleta y cómo entra:
[`ai-broll.md`](ai-broll.md).

**Cuando TODO el reel es cutaway** — "sin mi cara", "estilo lukedavis" — el modo es otro documento:
[`faceless-mode.md`](faceless-mode.md), con su gramática (qué verbo visual tiene cada frase) y su
emisor de escenas (`faceless/build-scene.py`), que genera estas escenas desde un `scenes.json`.

### 2.17 Element como cutaway (la textura a pantalla completa)

- **Qué:** un Element opaco (`elements/*.mp4`, no la versión alfa) como plano completo de 1–2 s en
  un beat "tech" o de transición — el globo en "el mundo", el código escribiéndose en "programa",
  la calavera wireframe en "riesgo", el ticker de cifras en "calcula" — tintado a la paleta con
  `colorchannelmixer` cuando el blanco pese, con la frase hablada debajo como en § 2.16.
- **Aquí:** V2 como b-roll (celda `texture` o `b-roll` con `"cutaway": true` y el archivo en `file`),
  corte seco, sin escala (ya es 1920×1080 → recortado al centro a 1080×1920 con `crop=1080:1080` +
  `pad` o a 9:16 con `scale=-2:1920,crop=1080:1920`); los `seamless_loop` se pueden alargar en bucle,
  los `build-in` se cortan en su parte buena.
- **Lock:** ≤ 2 s, nunca dos seguidos, y nunca como fondo de un texto largo (para eso está el set,
  § 2.12).

### 2.15 Palabra en el espacio negativo (sólo sobre b-roll)

- **Qué:** en cortes de b-roll SIN cara, la palabra clave del momento flota en el espacio libre del
  plano (el cielo, la pared, la mesa), Public Sans Black 90–120 px blanco con sombra ink, UNA
  palabra, `riseIn`/`riseOut` en la palabra.
- **Visto en:** jm todo el b-roll ("lifestyle", "opportunities", "sells").
- **Aquí:** es una excepción declarada a su lock de subtítulos (2 palabras, abajo): aplica SÓLO
  cuando no hay cara en el plano, y el subtítulo normal sigue corriendo abajo (los dos conviven:
  el subtítulo dice la frase, la palabra flotante es el gráfico). ⚠️ Proponer en el plan la
  primera vez; es su llamada.

---

## 3. La cadencia — por 30 s de reel

| | objetivo |
|---|---|
| titular fijo | 1, permanente |
| eventos de sustantivo (chip · logo · icono) | **6–10** |
| pruebas en pantalla + cutaways de icono / element (§ 2.5, § 2.16, § 2.17) | 2–4, de 2–6 s, **≤ 25 % del runtime** juntos |
| escena detrás | 0–1, de 2–4 s |
| textura | 0–1 |
| punch-ins en V1 | 2–4 |
| tramo desnudo más largo (sin evento gráfico vivo, titular aparte) | **≤ 3 s** |
| cara tapada (§ 0, medido por `face-guard.py check`) | **0 s** |

Esto sustituye el "4–7 gráficos por reel" del basic tier **para este preset** (pedido el
2026-09-14: "que edite sustancialmente mejor"). Lo que no cambia: la cara nunca se tapa, nada a
pantalla completa salvo la prueba y los cutaways del 25 %, y todo se mide antes de que él lo vea —
en vertical la puerta es `face-guard.py check` + `place-graphics.py --verify` (los cortes al frame);
`graphics-qa.py` es la de 16:9 y rechaza este formato.

---

## 4. La escalera de decisión por beat (para `graphics-plan`)

1. **Hook** → titular fijo desde 0.00 + el gráfico más fuerte del video en los primeros 2 s.
2. ¿Nombra una marca / producto con logo? → **ficha de logo**.
3. ¿Sustantivo concreto sin logo? → **icono** (`find.py`).
4. ¿Usa, muestra o cita una herramienta, un resultado, un artefacto? → **prueba en pantalla** (o
   `⚠️` pedirla).
5. ¿Nombra a una persona, una empresa, "el mundo", "detrás de mí"? → **escena detrás**.
6. ¿Cifra? → stat card con `countUp`. ¿Condición o frase que vale leer? → **chip**.
7. ¿Lista? → **pre-show** (sustantivos con icono) o **carrusel** (frases).
8. ¿La palabra de poder del payoff? → **tipo gigante detrás**. ¿Una sección de proceso de 8–15 s?
   → **el set**. ¿"Tres cosas / paso N"? → **tarjeta de capítulo** por cabecera.
9. ¿Algo abstracto sin artefacto real (inflación, tiempo, un proceso), o un sustantivo cuya ficha no
   cabe en ninguna zona libre? → **cutaway de icono** (§ 2.16) o **de element** (§ 2.17), dentro del
   25 %.
10. ¿Nada de lo anterior y > 3 s desde el último evento? → **textura** o palabra de poder en el
   subtítulo.

**Cómo se escriben en el plan** (`graphics-plan.json`, campo `kind`): `headline` · `chip` ·
`logo-tile` · `icon` · `b-roll` + `"proof": true` (la prueba: no se renderiza, se coloca como b-roll
en V2, con la ruta en `file`) · `bed-behind` (el fondo; el placer deriva la fila `<id>-cutout` del
recorte en V4) · `texture` · `list-preshow` · `type-behind` · `set` · `chapter-card` ·
`list-carousel` · `neg-space-word`. **Un cutaway (§ 2.16 / § 2.17) es `icon` o `texture` /
`b-roll` con `"cutaway": true`**: el validador le exige los bordes al frame en los cortes de V1 y lo
cuenta en el 25 %, y el placer lo lleva a V2 (`chapter-card` es cutaway por definición). Los de
siempre (`stat-callout`, `annotation`, `quote`, `captions`…) no cambian. `headline` va a su propia
pista (V6 en Premiere) y queda fuera de la densidad, como `captions`. `push_in: true` va en el beat
hablado que hace zoom, también en vertical.

**Errores que el research deja claros:** texto que repite lo que ya se ve en pantalla; dos
palabras estilizadas en una frase; una tarjeta sobre la cara; colores fuera de paleta; un emoji
horneado como PNG; una pantalla "dibujada" donde existía la real.

---

## 5. Acabado de cine (lo que hace que se vea película y no plantilla)

- **Capas con profundidad:** fondo (bed) / persona / gráficos / subtítulos — cada capa con su
  sombra y su `float`; nada plano pegado a la imagen.
- **Todo eased del registro**, nada lineal, nada instantáneo salvo los cortes; `float('subtle')`
  en toda comp, `medium` sólo en un héroe.
- **Una paleta, dos fuentes, un panel primitivo, UNA escala de radios.** La consistencia es lo que
  lee como producción. El suelo de calidad de cada comp (contraste medido, sombra con offset + blur,
  tracking, un solo momento de animación autoral por gráfico, sin eyebrows decorativos, sin
  gradient text) viene de las design skills instaladas el 2026-09-15 — el puente y lo que nuestros
  locks anulan: [`.claude/skills/graphics-build/design-skills.md`](../../../.claude/skills/graphics-build/design-skills.md).
- **Grado, opt-in en short-form:** "con grado" → el paso 4 corre en el reel con el look de casa
  (Autumn-Rec709 70/115) bajo los gráficos, como en long-form; por defecto sigue "skipped:
  short-form". Sin grano ni viñeta en vertical: la compresión de IG los convierte en ruido.
- **Verificar midiendo, no mirando:** `face-guard.py` (zonas antes, `check` después), el
  program monitor de Premiere, `place-graphics.py --verify` para los cortes; `graphics-qa.py` sólo en
  16:9. Lo que el sistema puede encontrar, el sistema lo arregla antes de que él lo vea.

---

## 6. Mecánica por lane (punteros, no recetas)

- **Comps:** `hf-anim.js` + `<video>` con alfa — webm VP9 (`yuva420p`) y ProRes 4444 probados en
  el render headless de `hyperframes@0.8.16` el 2026-09-14: el alfa sobrevive. Timing en el
  `<video>` o en el wrapper, nunca en ambos; GSAP sobre el wrapper.
- **Premiere (short-form):** V1 footage · V2 b-roll / prueba · V3 gráficos y beds · V4 recorte y
  solapes · V5 subtítulos. `place-graphics.py` coloca todo overlay; los punch-ins van al bridge
  `zoom`; el b-roll de V2 se coloca como en `premiere-pro` § generated b-roll.
- **Chat-only:** los mismos archivos entran como overlays en el assemble
  ([`lanes/chat-only/incremental-graphics.md`](../../../lanes/chat-only/incremental-graphics.md)).

Provenance: `reference/ig-research-2026-09-14/` — 16 frames del estudio de 4 cuentas + 16 frames
`jm-*` del reel de Jack Mason, nombrados por lo que enseñan, y el texto íntegro de ambos. Lo que se
copia es el lenguaje, nunca el contenido.
