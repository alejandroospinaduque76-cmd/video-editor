# Edición del comprador · 2026-09-29 (v1.4)

## Verificación
Pruebas del 29/09/2026 con esta versión:
- Comprador nuevo en un Mac con Apple Silicon, ruta chat-only: `empezar`, perfil de estilo, un clip de iPhone en HDR y en español editado hasta el final verificado, versiones por plataforma y el antes/después (que se niega a mostrar datos privados).
- Edición completa automática, desde el ZIP, de un clip vertical en español con el perfil de estilo (ambos estilos de subtítulos) y de un clip 16:9 para YouTube, en computadores de prueba de GitHub con Mac Apple Silicon, Windows y Linux, y en un Mac con Apple Silicon real.
- Formato largo 16:9 y clipper, revisados por separado. La detección de mirada, en un video de venta real en 16:9.

Sin verificar de principio a fin: Macs Intel (su versión está en prueba final), las rutas Premiere, Resolve, CapCut y Final Cut, Codex, la instalación desde cero de las herramientas base en Windows y Linux (en Linux el instalador muestra el comando `apt` que debes correr), y la primera descarga del motor durante el onboarding.

## Funciona en más computadores
- **Mac Intel:** la transcripción instala sola su versión para Intel (whisperx 3.3.1 con PyTorch 2.2.2, la última de PyTorch para esos Mac). La versión para tu computador está en su prueba final: si algo falla, escríbenos (el contacto está en tu recibo) y te avisamos cuando esté lista o te devolvemos el dinero.
- **Windows:** la edición completa por la ruta chat-only se probó automáticamente de principio a fin (29/09/2026). Premiere, DaVinci Resolve y CapCut para Windows (nuevo) vienen del sistema base (2026.09.28), que los da por probados; nosotros no los hemos probado de principio a fin. La instalación avisa si la carpeta está demasiado honda para Windows.
- **Linux:** la edición completa por la ruta chat-only se probó automáticamente de principio a fin (29/09/2026); DaVinci Resolve viene del sistema base. Para las herramientas base, el instalador muestra el comando `apt` que debes correr.

## Del sistema base (versión 2026.09.28)
- **Nuevo estilo corto: Talking Head Explainer.** Para cuando demuestras una herramienta en pantalla: rota el encuadre por frase (dividido, cerrado, abierto, pantalla completa, tarjeta), con capturas reales y sus propios subtítulos y sonidos. El Explainer de siempre (el de tus subtítulos del perfil) sigue siendo el predeterminado para una persona hablando a cámara con gráficos.
- **Final Cut Pro** como app de edición en Mac: construye la línea de tiempo completa y exporta sin clics (una copia aparte de Final Cut; la tuya no se toca).
- **Cortes exactos al cuadro** con video de iPhone (velocidad de cuadros variable) en todas las rutas, y la imagen sigue sincronizada con el sonido en tomas largas.
- **Exportación a los números de cada formato** (4K para YouTube, 1080×1920 para verticales) también donde la app no llega sola.
- **Revisión más estricta:** cada corte se prueba sobre la forma de onda; un barrido busca en pantalla los datos que le indiques (un teléfono, una clave, un correo) antes de entregar; y un re-corte tardío vuelve a sincronizar gráficos y efectos de sonido. En la ruta chat-only el difuminado de lo que el barrido marque se hace a mano, y el antes/después no se genera si el video tiene datos privados en pantalla.
- **Música:** entra donde la canción arranca de verdad; nivel de fondo −20 dB (antes −18).
- **Muletillas:** una «eh» suelta dentro de una frase que fluye se queda, porque cortarla deja un salto peor; si en tu perfil elegiste quitarlas todas, se quitan igual.
- **`my-rules.md`:** tus reglas fijas para el editor, en tus palabras.
- **Un segundo entregable** (el corte para anuncio, o el archivo 4K para Shorts) se finaliza con `--variant`.

## Arreglos
- **Mirada fuera de cámara, también en horizontal:** el detector encuentra la cara en videos 16:9 (antes no la veía) y marca cuándo miras a un lado, arriba o abajo (como al leer un guion), con las palabras que decías en ese momento. Con `--write` solo recorta el silencio en que miras fuera al empezar o terminar un tramo, y nunca borra una palabra: si mirabas fuera mientras hablabas, te muestra esa frase para que decidas si se corta. Probado con un video de venta real: ninguna palabra borrada, y su recorte cayó a 7 milésimas del que se hizo a mano.
- Subtítulos con contorno: la frase aparece completa y centrada, y la palabra que se dice toma tu color de resaltado.
- Versiones por plataforma: el volumen sube con una sola ganancia fija y un limitador que solo toca los picos, y el nivel y el pico real se miden después de codificar el audio, como los lee la plataforma: −14 LUFS y pico de −1,5 dBTP o menos (antes, en YouTube, el pico quedaba en −0,9 y luego en −1,4). Un master que pase el tope no se entrega. Si el limitador tuvo que bajar mucho los picos, te avisa para que lo escuches.
- `finalize.sh --source` acepta también la ruta del archivo aprobado, no solo su nombre, si está dentro de `outputs/`.
- Subtítulos con tamaño grande en tu perfil (por ejemplo 72 px): las líneas se parten por su ancho medido, así ningún subtítulo se sale de la zona segura de Instagram (antes, con estilo contorno, la frase quedaba recostada a la izquierda y fuera de la zona).
- La auditoría de cortes ya no recorta el final de la última palabra cuando el sonido es suave (una «s» final), y nunca propone un corte antes del inicio del clip.
- Formato largo 16:9: los gráficos caen en el cuadro exacto del corte y a la velocidad de la línea de tiempo, colores BT.709 en todo el ensamblado.
- Clipper: los subtítulos de cada clip se generan en cualquier sistema, y ya no copia nada a Descargas salvo que lo pidas (`--export-dir`).
- Perfil con «sin subtítulos»: el clipper igual entrega cada clip (con la tarjeta de gancho).
- La medición de volumen omite los clips sin audio (grabaciones de pantalla) en vez de detener el corte.
- Formato largo: una captura real (b-roll o captura de pantalla) sin tarjeta renderizada ya no se descarta; entra a pantalla completa en su tramo, sin estirarse.
- Premiere en español: la capa de color (Lumetri) y el difuminado de privacidad encuentran sus efectos también por su nombre en español, y si un efecto no queda puesto se detienen y lo dicen en vez de reportar éxito. El difuminado ya no puede borrar la pista de música.

## Si tienes un trabajo a medio hacer de la v1.3
El plan de gráficos de la v1.4 pide datos nuevos (de dónde sale cada gráfico, sus fases, su imagen, el cuadro del creador), así que un plan hecho en la v1.3 no pasa el validador nuevo. La colocación de gráficos igual funciona y solo avisa. Termina ese video en la carpeta de la v1.3, o vuelve a planear sus gráficos en la v1.4. En Premiere, el kit no escribe en el proyecto que quedó en la carpeta de la v1.3 aunque se llame igual que el trabajo: abre el proyecto de la carpeta nueva.

# Edición del comprador · 2026-09-28 (v1.3)

## Verificación
Prueba de comprador nuevo el 29/09/2026, desde el ZIP de prueba de esta versión extraído en una carpeta limpia, en un Mac con Apple Silicon, ruta chat-only, con el motor de transcripción ya descargado:
- El kit detectó al creador nuevo, hizo las 5 preguntas, midió 2 videos de referencia (1 min 11 s) y mostró el perfil en español.
- Primer video (clip de iPhone en HDR, en español) editado con ese perfil: subtítulos elegidos (C: mayúsculas, contorno, palabra hablada en amarillo), pausas y vocabulario del perfil, final verificado, versiones para Reels y TikTok, antes/después.
- Aprendizaje: «subtítulos más grandes» → «¿siempre así?» → guardado en el perfil y aplicado al volver a renderizar.
- Mismo clip sin perfil: igual que la v1.2.
- Unos 7 minutos de reloj de principio a fin con respuestas instantáneas de prueba; el tiempo que tarde una persona en leer y responder no está medido.

Sin verificar: la primera descarga (~4,3 GB) durante el onboarding, Macs Intel (en prueba final), Windows/Linux, rutas Premiere/Resolve/CapCut, Codex de principio a fin, formato largo 16:9.

## El kit aprende cómo editas tú
- **Primer uso: escribe `empezar`.** El kit detecta que eres nuevo, revisa tu equipo, te hace 5 preguntas y mide 1–3 videos terminados que te gusten (tuyos o de otro creador): ritmo de cortes (al menos N por minuto), zooms, pausas que dejas, velocidad al hablar, volumen, música de fondo y cómo son tus subtítulos (posición, tamaño, caja o borde, color de resaltado). Qué hacer con tus muletillas lo decides tú en las preguntas.
- **Tu perfil de estilo** (`creator/perfiles/<nombre>/ESTILO.md`, en español claro) guía cada edición: pausas máximas, cuánto se recorta, muletillas, tomas repetidas, subtítulos, gráficos, zooms, música, plataformas de entrega y las palabras que siempre deben escribirse bien.
- **Sigue aprendiendo:** cuando pides un cambio en la revisión, el editor pregunta «¿siempre así?» y lo guarda; al final te dice qué aprendió. `profile.py undo` / `reset` lo deshacen.
- **Varios perfiles** (un creador o cliente por perfil): «nuevo perfil», «usa el perfil <nombre>». Se exportan e importan al actualizar el kit.
- Sin perfil, el kit edita exactamente como la v1.2.

## Otros
- Subtítulos: palabra activa resaltada en color (opcional, ambos estilos).
- Antes/después de 10 s del primer video (`workflows/before-after.py`).
- La descarga del motor de transcripción empieza en segundo plano mientras respondes las preguntas.
- ZIP más liviano: sin los renders de fondos regenerables; imágenes de la guía comprimidas.

# Edición del comprador · 2026-09-25 (v1.2)

## Verificación
Edición completa real el 25/09/2026, desde este ZIP extraído en una carpeta limpia, en un Mac con Apple Silicon, ruta chat-only:
- Clip vertical de iPhone grabado en HDR (HLG/Dolby Vision, girado) en español → conversión a SDR, transcripción, corte, subtítulos, composición, exportación verificada y master para Reels (−13,6 LUFS).
- Primera transcripción con cachés vacías: unos 4,3 GB de descarga, 2 min 21 s.
- Regresión: el clip del 21/09 conserva la palabra final completa ("segundos").

Sin verificar: instalación de las herramientas base desde cero (Homebrew, ffmpeg, uv, node), Macs Intel (en prueba final), Windows/Linux, rutas Premiere/Resolve/CapCut y Codex de principio a fin.
- Arreglado después de esa prueba: el ensamblado chat-only ya funciona sin placement.json cuando solo hay subtítulos.

## Video del iPhone
- **HDR (activado de fábrica en iPhone 12 y posteriores):** al importar, `workflows/normalize-source.py` convierte HLG/Dolby Vision a SDR BT.709, gira los clips verticales y pasa la velocidad de cuadros variable a constante. El original queda en `raw/_source/`. Antes, un clip HDR salía con colores grises o saturados.
- **Varios clips distintos** en un mismo trabajo (4K + grabación de pantalla, 60 y 30 fps, clips sin audio) ya no rompen el corte: se igualan tamaño y velocidad, y los clips sin audio reciben silencio.
- **Calidad del corte:** el bitrate intermedio sube con la resolución (4K60 ≈ 60 Mb/s en vez de 8) y el video lleva etiquetas de color BT.709.

## Audio y entrega
- **Entrega por plataforma:** `workflows/deliver.py` crea `outputs/<trabajo>.reels.mp4` (o tiktok, shorts, youtube) a −14 LUFS y pico −1,5 dBTP, en 1080×1920 para Reels/TikTok, sin tocar el final aprobado. El final del 21/09 medía −18 LUFS: sonaba más bajo que el resto del feed.
- **Última palabra:** el pulido de cortes ya no recorta la consonante final ("segundo**s**").

## Español
- La transcripción guarda el idioma real (antes el archivo final decía "en").
- Las cifras que el alineador no ubica ya no se pierden: reciben tiempo interpolado.
- Muletillas en español en la guía de corte (siempre: eh, em, mmm; solo aisladas: este, o sea, bueno, pues…) y retomas: se conserva la última y se listan las cortadas.
- Nuevo `find-fillers.py`: lista titubeos que Whisper no escribe (candidatos para confirmar; no corta solo).
- Subtítulos: "¿" y "¡" nunca quedan sueltos al final de línea; las líneas largas en español ya no se salen del cuadro.
- Correcciones incluidas para "Claude" (Clot, Clod, Claud); "Cloud" y "Groove" se marcan para revisar.
- Nueva `help/SOLUCION-DE-PROBLEMAS.md` en español, enlazada desde START-HERE.

## Ruta chat-only
- Nuevo `lanes/chat-only/assemble.py`: une corte, gráficos y subtítulos en una pasada con la protección contra cuadros duplicados, y deja el borrador en `outputs/` listo para `finalize.sh`.

## Instalación
- Versiones fijas: whisperx 3.8.6, torch 2.8.0. HyperFrames sigue en 0.8.16: ignora el aviso de actualización.
- Se oculta un aviso falso de `torchcodec` en la primera transcripción.
- Licencias: se retiraron Georgia (Microsoft) y Coolvetica (no redistribuible). Subtítulos del explainer en Inter Bold; títulos serif en Playfair Display. Licencias OFL incluidas.

# Edición del comprador · 2026-09-21 (v1.1)

## Verificado hoy con un clip real
Edición completa desde el ZIP publicado, extraído en una carpeta limpia (macOS, ruta chat-only): clip vertical de iPhone de 22 s en español → transcripción, cortes, audio, subtítulos en español, verificación y export final de 9,3 s. Evidencia y defectos corregidos en el informe del vendedor (qa/e2e-2026-09-21). Sigue sin verificarse: máquina limpia sin descargas previas, Windows/Linux, rutas Premiere/Resolve/CapCut, Codex de principio a fin.

## Correcciones a partir de esa prueba
- Transcripción: el idioma se detecta automáticamente por clip (antes forzaba inglés y traducía el español con tiempos falsos). `--lang es` o `WHISPERX_LANG=es` lo fuerzan.
- Límites de corte: una palabra final suave ya no se recorta cuando el ruido de fondo sube el umbral (suelo en el fin de palabra + aviso).
- Formato: los clips verticales de celular (rotation ±90) se reconocen como verticales.
- Subtítulos: el proyecto HyperFrames se crea con `hyperframes init` (ya no exige copiar archivos de un proyecto previo).
- Export chat-only: documentado copiar el borrador aprobado a `outputs/` antes de `finalize.sh`.
- Guía y ayuda: nueva entrada "La transcripción salió en otro idioma"; la instrucción del generador declara el idioma del audio.
- Assets: 109 ilustraciones recortadas con alpha en `assets/motion/illustrations/` (catálogo bilingüe; `python3 assets/motion/find.py <palabra>`).

## Edición anterior (2026-09-21 v1)
- Diagnóstico sin instalación: bash setup.sh --check.
- Instalación local explícita para Codex: --host codex --lane chat-only; otras rutas requieren verificar sus conexiones.
- No se asume Premiere ni se elige arbitrariamente entre proyectos.
- Un fallo obligatorio detiene las etapas que dependen de él.
- Exportación desde el archivo aprobado: validación completa, borradores conservados, finales existentes protegidos.
- Guía 03 con selector de asistente e instrucciones revisadas.

Pruebas: 11 comprobaciones de medios y protección de archivos con un video sintético de 2 segundos, más la edición real descrita arriba.
