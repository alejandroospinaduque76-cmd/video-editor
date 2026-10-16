# Modo FACELESS — el reel que retrata lo que dices, sin tu cara (2026-09-17)

**Qué es.** Tu voz grabada (el talking-head de siempre, cortado por `rough-cut`) y, encima, en vez de
tu cara, **una escena por beat que ENACTA lo que estás diciendo**: una cifra que cuenta, iconos que se
apilan uno a uno, una línea que se dibuja, un anillo que se reparte, una línea de tiempo que se
extiende, un flujo que corre — cada revelado en la palabra que lo nombra. Es el reel de @lukedavis
(`reference/ig-research-2026-09-14/ld-*.jpg`): 38 s sin cara, un gráfico cada ~4 s, la frase
completándose palabra a palabra. Aquí la frase la llevan tus subtítulos de 2 palabras; la escena lleva
el gráfico y UNA cosa escrita.

**Cómo se pide.** "hazlo faceless" · "sin mi cara" · "estilo lukedavis" · "solo animaciones" → tier
`faceless` del explainer. Con matiz: "cara en el gancho y el cierre" → `bookends` (la cara abre y
cierra, todo lo demás es escena); "cara solo donde no haya nada que mostrar" → `auto`. Sin matiz =
`never` (la cara no aparece).

**Qué NO cambia.** Los pasos 1–3 (intake, corte, audio) son los de siempre: la voz es la del corte y
manda los tiempos. Los subtítulos corren todo el reel (2 palabras, abajo, en el `y` del reel). La
paleta, las fuentes, el registro de animación (`hf-anim.js`) y el tamaño mínimo de texto (54 px) son los
locks de siempre. Cambia el paso 5: casi todo son cutaways en V2, y por eso el 25 % de § 3 de
[`reference-craft.md`](reference-craft.md) no aplica (`validate-plan.py` lo sabe por el tier).

---

## 1. La placa — una por reel

Navy `#131A2E` + `el-02-grid-warp` al 0.12 + viñeta (la misma placa de § 2.16). **Idéntica en todas
las escenas**: así los cortes duros entre escenas leen como un solo mundo por el que pasan las cosas, no
como diapositivas. Lo que cambia entre escenas es lo que hay encima. Sin grano (`GRAIN=0`), sin cara,
nada bajo la línea de subtítulos (`caption_top − 40`; con cara en ningún tramo, `caption_top` = 1497 por
defecto; con `bookends`, el medido en las tomas con cara).

## 2. La gramática — de lo que dice a lo que se ve

Lee cada beat del guion y pregúntate **qué VERBO visual tiene**. Esta tabla es el mapa; el patrón es el
molde que `build-scene.py` rellena.

| Lo que dice (ejemplos) | Verbo visual | Patrón | Qué pasa en pantalla |
|---|---|---|---|
| una cifra, un precio, un %, "cada uno cuesta…", "perdió el 95 %" | **cuenta** | `counter` | la cifra cuenta de A a B entre dos palabras; el icono del sustantivo sostiene el frame; un chip remata (×4, −95 %) |
| "un montón de", "todos los", "cuatro herramientas", una lista de marcas | **se apila** | `stack` | 1–6 iconos o logos reales aparecen uno a uno en sus palabras; la figura arriba |
| "cada vez más", "cayó", "creció", "desde 2020" | **se dibuja** | `line` | una línea se traza de izquierda a derecha entre dos palabras; el valor final salta al llegar |
| "una parte", "el 40 %", "A frente a B", "se reparte" | **se reparte** | `donut` | un anillo se llena por segmentos, cada uno en su palabra, con su icono dentro |
| fechas, "hace 50 años", "primero… luego…", un proceso | **se extiende** | `timeline` | un corchete se dibuja y los hitos saltan sobre él en sus palabras |
| "tres cosas", "los pasos", "lo que necesitas" | **se enumera** | `list` | filas icono + 2–4 palabras que entran en sus palabras |
| "le venden X a Y", "de aquí a allá", causa → efecto | **fluye** | `flow` | icono origen → puntos de datos → icono destino; la figura arriba |
| una pregunta, una afirmación fuerte sin sustantivo, el gancho | **se dice** | `type` | palabras grandes (Playfair Display) que entran y salen en sus tiempos |
| un producto, una empresa, una herramienta | **se nombra** | `stack` de 1 con logo real, o `flow` | la marca en su ficha con su color muestreado |

**Reglas que hacen que sea b-roll y no un stamp** (las de § 2.16, aquí sin excepción):

- **Nada se adelanta a la voz.** En t=0 solo está lo que ya se dijo; cada pieza entra en SU palabra
  (`at` = inicio de la palabra − 0.08 del transcript canónico). Una escena de 4 s con todo puesto en el
  primer segundo es una diapositiva.
- **Un hold de más de 3 s cambia de estado a mitad**, en la palabra que lo motiva: la cifra sigue
  contando, entra el siguiente icono, se dibuja el tramo siguiente. La única quietud legítima es la del
  final (el "held read").
- **Una cosa escrita por escena** (la figura: la cifra, el nombre, la palabra de poder), Public Sans
  Black 110–190 px con su sub-etiqueta cian de 44 px. La frase hablada NUNCA se escribe en la escena:
  ya está en los subtítulos.
- **El icono es el sustantivo, y es de la librería** (`python3 assets/motion/find.py <palabra>`); la
  marca es el logo real con su color muestreado (`assets/logos/`). Nunca emoji, nunca un chip de texto
  en vez de un logo.
- **Un patrón nunca dos veces seguidas, y ≥ 3 patrones distintos por reel.** `stack` seguido de
  `stack` es la excepción cuando el segundo es un logo único ("se nombra").
- **Ritmo:** una escena cada 2–6 s (las de 1–1.5 s son `type`); ≤ 2 escenas sobre un mismo take de V1
  cortando en mitad del take (el corte de escena no tiene por qué caer en un corte de V1: V1 está
  debajo, invisible).
- **Frame 0 del reel nunca vacío:** la primera escena entra en el primer frame (`type` con la pregunta
  del gancho, o el primer icono).
- **Salidas:** cada elemento sale con `riseOut` dos frames antes del fin de su escena (la placa queda);
  la siguiente escena entra con `pop`/`riseIn` en su primera palabra. Sin fundidos entre escenas.

## 3. Cómo se escribe (el plan)

`graphics-plan` en tier `faceless` escribe **`hf-graphics/scenes.json`** además del plan: una entrada
por escena con `pattern`, `start`/`end` (tiempos de timeline) y los slots del patrón con sus `at` en
palabras del transcript. El ejemplo que renderiza (los 8.4 s del gancho de Arena AI, 4 escenas):
[`faceless/example-scenes.json`](faceless/example-scenes.json) → `reference/faceless-demo.jpg`.

```json
{ "fps": "30000/1001", "caption_top": 1497,
  "scenes": [
    { "id": "s2", "pattern": "counter", "start": 3.70, "end": 6.006, "icon": "money", "icon_at": 3.70,
      "counter": { "from": 0, "to": 80, "prefix": "$", "sub": "al mes, uno por uno",
                   "at_start": 4.36, "at_end": 5.73, "size": 190, "chip": "×4 suscripciones", "chip_at": 5.42 } } ] }
```

Slots por patrón (todos los `at` en segundos de timeline; `figure` = `{text, hero?, sub?, at, size?}`):

- `counter` — `icon`, `icon_at`, `counter{from, to, prefix?, suffix?, sub?, at_start, at_end, size?, chip?, chip_at?}`
- `stack` — `figure?`, `items[{icon | logo, brand?, label?, at}]` (1–6)
- `line` — `figure?`, `line{points[[x,y]…] en 0–1, at_start, at_end, x0?, x1?, end_label?}`
- `donut` — `figure?`, `segments[{pct, color?, icon?, at}]`
- `timeline` — `figure?`, `timeline{start_label?, end_label?, at_draw, markers[{pos 0–1, label, at}]}`
- `list` — `figure?`, `rows[{icon, text, at}]` (las que quepan sobre la línea de subtítulos)
- `flow` — `figure?`, `flow{from_icon, to_icon, at_from, at_to, at_dots?}`
- `type` — `words[{text, at, size?, top?}]`

En `graphics-plan.json` cada escena es una celda `graphic:true` con `"kind": "<patrón>"`,
`"cutaway": true`, `region: "cutaway"` y el mismo `start`/`end`; la celda `captions` sigue. Con
`bookends`/`auto`, los beats con cara se planifican como en `reference-craft.md` (titular, chips,
fichas, con la ley de la cara).

## 4. Cómo se construye y se coloca

```bash
uv run presets/instagram/explainer/faceless/build-scene.py projects/<job> --render   # comps + GRAIN=0 renders
uv run lanes/premiere/place-graphics.py projects/<job> --plan --write && … --apply   # V2, una fila por escena
```

El emisor escribe `hf-graphics/gfx/compositions/<id>.html` (placa + registro + librería, el frame 0
fijado, salidas en registro) y renderiza opaco. Premiere: **V2**, corte seco, cada escena termina donde
empieza la siguiente; chat-only: los mismos mp4 en el assemble. Luego SFX (`sfx-plan.py` lee los
`pop`/`riseIn`/`countUp` de cada escena) y export como siempre.

**Puertas.** `face-guard.py check` (sólo importa en `bookends`/`auto`: las escenas no tienen cara),
`place-graphics.py --verify`, y una que es propia de este modo: **ver el reel entero de un tirón** —
un faceless se cae por ritmo (dos `type` seguidos, un `stack` que entra tarde, un hold muerto), y eso
sólo se ve corriendo.

## 5. Lo que aprendimos del reel de referencia (y lo que no copiamos)

- Copiamos: una placa, un gráfico por beat, la cifra que cuenta, los billetes que se apilan, la línea
  que se dibuja, el donut con iconos dentro, la frase completándose con la voz, el hold final.
- No copiamos: su tipografía (la nuestra: Public Sans + Playfair Display), su verde/amarillo (nuestra paleta),
  la frase escrita en la escena (nuestros subtítulos ya la llevan), el CTA card del final.
- Una mejora sobre él: nuestros iconos son animados (la librería), no vectores fijos — el icono
  reproduce su animación al entrar y se queda en su pose de reposo.
