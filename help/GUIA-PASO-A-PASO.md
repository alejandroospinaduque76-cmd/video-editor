# Tu primer video

Open START-HERE.html for the visual guide, route selector, prompt builder and examples. / Abre START-HERE.html para ver imágenes y usar las herramientas.

## 1. Conoce tu kit

Entiende qué hace cada pieza antes de instalar.

1. El editor reúne instrucciones y herramientas que ejecutas en tu computador con Claude Code o Codex. Tú aportas el material, das dirección y revisas las decisiones de edición.

2. Esta guía te acompaña paso a paso. El agente de ayuda consulta la documentación del kit para explicar dudas y diagnosticar errores.

3. Necesitas acceso propio a Claude Code o Codex, internet para la instalación y espacio para material y descargas. El uso de IA, las aplicaciones de pago y los servicios opcionales se pagan por separado.

Señal de éxito: Puedes distinguir el editor, la guía y el agente de ayuda. Tienes un clip propio de 20–60 segundos para practicar.

Si falla: Este kit se abre como proyecto local en Claude Code o Codex. El chat web básico de Claude o ChatGPT no ejecuta estas herramientas por sí solo.

## 2. Abre la carpeta correcta

Abre el kit en el asistente que elegiste.

1. Extrae todo el ZIP. Abre la carpeta video-editor que contiene SETUP.md, CLAUDE.md y AGENTS.md. Conserva también la carpeta oculta .claude.

2. Elige Claude Code o Codex e inicia sesión con tu propia cuenta. Si eliges Codex, sigue help/USAR-CON-CODEX.md. En Windows, los scripts del kit requieren Git Bash.

3. Abre la carpeta completa como proyecto local en el entorno que elegiste y escribe empezar. El asistente confirma la carpeta, revisa tu equipo y las herramientas y después aprende tu estilo de edición.

> empezar

Señal de éxito: Tu asistente puede leer SETUP.md y reconoce la carpeta completa. En Codex también ha leído AGENTS.md.

Si falla: Si no encuentra SETUP.md, probablemente abriste la carpeta superior o una copia incompleta. Comprueba la ubicación antes de instalar nada.

## Tu estilo

La primera vez escribe **empezar**. El editor revisa tu equipo, te hace hasta 5 preguntas en un solo mensaje (nombre y @, plataformas, subtítulos A/B/C, muletillas, palabras que se transcriben mal), mide 1–3 videos terminados que te gusten (se analizan en tu computador y no se suben a ningún lado) y edita tu primer clip con ese estilo.

- Tu estilo queda escrito en `creator/perfiles/<tu-perfil>/ESTILO.md`. Corrige cualquier línea con una frase («pausas más cortas»). En cada revisión te pregunta «¿siempre así?» y lo aprende.
- Varios creadores o clientes: di «nuevo perfil» y «usa el perfil <nombre>».
- ¿No quieres configurarlo? Di que no: edita con el estilo neutro del kit y no vuelve a preguntar. Puedes escribir empezar cuando quieras.
- Al pasar a una versión nueva del kit, escribe empezar en la carpeta nueva y di dónde estaba la anterior: trae tu perfil. También puedes usar `python3 workflows/profile.py export mi-estilo.zip` y `import`.

## 3. Prepara las herramientas

Instala una vez y comprueba lo que quedó listo.

1. Primero pide el diagnóstico con bash setup.sh --check. No instala herramientas ni cambia conexiones.

2. Selecciona arriba Claude Code o Codex. Para Codex sin app de edición, la instalación es bash setup.sh --host codex --lane chat-only. Los puentes de otras apps requieren una configuración específica.

3. Revisa los requisitos y las descargas antes de instalar. Reinicia el entorno elegido solo si se necesita. Comprueba un clip corto después; los requisitos correctos no prueban una edición completa.

> Lee las instrucciones de mi entorno y ejecuta bash setup.sh --check. Explica qué falta, qué se descargará y qué ruta está disponible. En Codex usa únicamente la instalación local documentada con --host codex --lane chat-only; comprueba por separado los puentes de aplicaciones. No configures servidores de Claude para Codex.

Señal de éxito: El informe no muestra requisitos obligatorios pendientes. Conoces la ruta de edición elegida; la confirmarás en el paso 4.

Si falla: Una descarga puede tardar. Pide que compruebe si hay progreso o un error; no borres cachés ni repitas instalaciones a ciegas.

## 4. Elige dónde editar

Selecciona la ruta que corresponde a tu aplicación.

1. Una “ruta de edición” indica dónde se arma y exporta el video. Puedes usar una aplicación compatible o el procesamiento local llamado chat-only.

2. Selecciona abajo la ruta que realmente usarás. Las funciones automatizadas varían entre aplicaciones; revisa la limitación indicada antes de empezar.

3. Pide al editor que confirme la conexión y las funciones disponibles. Tener la aplicación instalada no demuestra que esté conectada.

Señal de éxito: El editor identifica tu ruta y confirma su conexión, o explica qué falta para activarla.

Si falla: Si falla la conexión, ve a Ayuda. No cambies de aplicación a mitad de un trabajo sin que el editor revise el proyecto existente.

## 5. Haz tu primer video

Empieza pequeño: un clip, un objetivo, una prueba.

1. Elige un clip propio de 20–60 segundos, con una persona hablando claramente. Ábrelo primero para comprobar que se ve y se oye. Los videos de celular en vertical se detectan como vertical aunque el archivo diga 3840×2160; el idioma se detecta solo. Si el clip es de iPhone en HDR, el editor lo convierte a SDR al importarlo (workflows/normalize-source.py) y guarda tu original intacto en raw/_source/.

2. Completa el formulario de abajo. La ruta es la dirección del archivo en tu computador. El formulario prepara una instrucción; no sube ni procesa el video.

3. Pega la instrucción en Claude Code o Codex. Revisa el texto transcrito y los cortes propuestos. Pide una vista previa antes de aprobar la exportación final.

Señal de éxito: Hay un borrador reproducible, entiendes los cortes y el mensaje mantiene su sentido. Si el flujo se detiene, sabes en qué etapa está.

Si falla: Si dice que el archivo no existe, verifica su nombre, extensión y ruta. En Windows puedes usar “Copiar como ruta”; en Mac, Option + clic derecho permite copiar la ruta del archivo.

## 6. Revisa con criterio

Da indicaciones que el editor pueda ejecutar.

1. Mira el borrador completo con sonido. Revisa que los cortes no cambien el significado y que nombres y cifras sean correctos.

2. Comprueba que el rostro siga visible, que los subtítulos se lean y que la voz no quede tapada. Usa la comparación visual de abajo para practicar.

3. Pide cambios concretos: momento, problema y resultado esperado. Conserva lo que ya aprobaste y revisa de nuevo el fragmento modificado.

> En 00:12, conserva completa la frase sobre [tema]. Cambia el subtítulo [texto incorrecto] por [texto correcto]. Mantén el resto aprobado y muéstrame ese fragmento revisado antes de exportar.

Señal de éxito: Aprobaste el mensaje, la ortografía, el encuadre y el audio. Ya puedes pedir el archivo final.

Si falla: “Hazlo mejor” no indica qué cambiar. Sustitúyelo por una petición como “en 00:12, baja el subtítulo para que no cubra mi cara”.

## 7. Exporta y comprueba

Encuentra el archivo que vas a compartir.

1. Cuando apruebes el borrador, pide la exportación. El lugar documentado es projects/<trabajo>/outputs/<trabajo>.final.mp4; el nombre real depende de tu proyecto.

2. Pide comprobar el archivo completo con workflows/verify-export.py: duración, dimensiones y decodificación. Confirma también que tiene audio si el video lo requiere.

3. Abre el MP4 final: revisa principio, mitad y final, sincronía de voz e imagen y dimensiones. Exportar no publica automáticamente en redes. Para subirlo, pide "prepara la entrega para Reels" (o TikTok, Shorts, YouTube): workflows/deliver.py crea outputs/<trabajo>.reels.mp4 con el volumen de la plataforma, sin tocar el final.

> Exporta el borrador exacto que aprobé. Verifica duración, dimensiones, audio y decodificación completa con workflows/verify-export.py. Usa finalize.sh con --source, --approved y --apply. Conserva originales y borradores; no sobrescribas un final existente ni ejecutes limpieza. Dame la ruta exacta y no publiques en redes.

Señal de éxito: Puedes localizar y reproducir el MP4 final fuera del editor. Guarda también el material original y el proyecto.

Si falla: Si no aparece, pide comprobar el archivo en outputs y el estado de exportación. No des por terminado el trabajo solo porque se cerró una ventana.

## 8. Hazlo tuyo

Personaliza la marca después de la primera prueba.

1. Abre brand-kit.md. Rellena tu nombre o marca, público, tono, colores y palabras que se suelen transcribir mal.

2. Usa fuentes, imágenes, música y logos que tengas derecho a utilizar. Si una función requiere un servicio externo de pago, decide si quieres activarlo.

3. Pide que aplique la marca según el mapa del archivo y haga una muestra corta. Aprueba esa muestra antes de usar el estilo en un proyecto largo.

> Lee brand-kit.md y ayúdame a completar los campos que faltan, sin inventar datos de mi marca. Después aplica el mapa documentado y crea una muestra corta para revisar colores, fuentes y nombres. No actives servicios de pago sin mi autorización.

Señal de éxito: La muestra usa tus colores y tu vocabulario. Confirmaste que el texto sigue siendo legible.

Si falla: Si un cambio no aparece, pide comparar el valor de brand-kit.md con el preset usado. Un preset es una receta de estilo.

## 9. Pide ayuda útil

Lleva el problema al agente incluido, con contexto.

1. En Claude Code, usa el agente video-editor-help. En Codex, pide el modo de ayuda descrito en AGENTS.md y help/USAR-CON-CODEX.md.

2. Incluye sistema, ruta, etapa y el mensaje exacto del error, sin claves ni información privada. El asistente consulta la documentación antes de responder.

3. Pide primero un diagnóstico sin modificar archivos. En Codex es una instrucción de trabajo; no es un subagente con herramientas de lectura restringidas. Para aplicar una solución, indícalo expresamente al editor.

> Actúa en modo de ayuda del kit. En Claude Code utiliza video-editor-help; en Codex sigue AGENTS.md. Lee la documentación antes de responder. Estoy en [sistema], usando [ruta], en [etapa]. Esperaba [resultado] y ocurrió [problema]. Error sin datos privados: [mensaje]. Dime qué está confirmado, qué falta y hasta tres pasos. No modifiques archivos todavía.

Señal de éxito: Recibes una explicación vinculada a la documentación y un siguiente paso concreto; si falta evidencia, el agente la pide.

Si falla: En Claude Code, comprueba .claude/agents/video-editor-help.md. En Codex, comprueba AGENTS.md y pide modo de ayuda. Ambos requieren la carpeta completa.

## 10. Retoma sin empezar de cero

Continúa desde lo que realmente quedó hecho.

1. Vuelve a abrir la misma carpeta y localiza el proyecto. Su archivo RUN.md registra el avance del trabajo.

2. Pide al editor revisar el registro y los archivos que existen. Que determine el último paso completado antes de continuar.

3. Guarda una copia de tus originales y del resultado aprobado. Para problemas con la compra o descarga, usa el contacto del vendedor que aparece en tu recibo.

> Lee el RUN.md de mi proyecto [nombre] y comprueba sus archivos. Dime cuál fue la última etapa completada y qué queda pendiente. Continúa desde ahí sin sobrescribir el trabajo aprobado ni modificar mis originales.

Señal de éxito: El editor retoma el proyecto correcto y respeta las decisiones ya aprobadas.

Si falla: Si hay varios proyectos, identifica el correcto por su nombre y material. No dejes que seleccione uno al azar.

## Official setup / Instalación oficial

https://code.claude.com/docs/en/quickstart

## Editing-route limits / Límites de las rutas

See SETUP.md and LANES.md. CapCut automation: macOS only. Premiere: macOS / Windows. Resolve: edition-specific bridge; some grading/SFX tasks manual or unvalidated. chat-only: local rendering; long-form grading and automatic SFX mixing not implemented.

## Export location

projects/<job>/outputs/<job>.final.mp4

## Help / Ayuda

### No encuentra el archivo · ruta · file not found

Comprueba que extraíste el kit y que la ruta del clip apunta a un archivo existente. Si la ruta tiene espacios, consérvala completa entre comillas al escribir comandos. Pide al editor verificar la existencia antes de editar. Comprueba que el archivo esté descargado en el equipo, no solo disponible en la nube.

Reference: Paso 2 y paso 5 · SETUP.md

### Windows: no reconoce un comando · Bash · FFmpeg

Comprueba Git Bash y pide ejecutar check-setup.sh. Si instalaste herramientas, abre de nuevo el entorno que elegiste para que detecte sus ubicaciones. Resuelve el requisito que el informe identifica.

Reference: SETUP.md · Core / Windows

### Windows: no puede escribir · OneDrive · permisos

Usa una copia completa en una carpeta local que controles, fuera de OneDrive y de carpetas protegidas. No desactives la protección del sistema para completar el tutorial.

Reference: SETUP.md · Windows

### La transcripción salió en otro idioma · inglés · traducción

El kit detecta el idioma de cada clip automáticamente. Si el texto aparece en un idioma que no hablaste o con muchas palabras dudosas, pide repetir la transcripción forzando el idioma: transcribe.sh projects/<proyecto> --force --lang es. No apruebes cortes sobre una transcripción equivocada.

Reference: Paso 5 · SETUP.md · Language

### La primera transcripción tarda mucho · WhisperX

El modelo inicial ocupa unos 3–5 GB; el entorno y componentes GPU pueden añadir más. Pide comprobar descargas, espacio disponible y el último mensaje. El tiempo depende del equipo y la conexión.

Reference: SETUP.md · First edit

### Premiere no se conecta · MCP

Comprueba que el instalador de Premiere terminó. Reinicia Premiere y Claude Code según SETUP.md y revisa la conexión del proyecto. Pide el diagnóstico del puente antes de reinstalar.

Reference: SETUP.md · Premiere lane

### Resolve · BRIDGE_UNAVAILABLE

Indica si usas Free o Studio. La ruta documentada para Free requiere abrir un proyecto y ejecutar Workspace → Scripts → resolve_bridge cada vez que inicias Resolve. Sigue las instrucciones de tu edición.

Reference: SETUP.md · DaVinci Resolve lane

### El subtítulo tapa la cara o tiene errores

Da el segundo exacto y la palabra correcta. Pide corregir la transcripción de origen cuando corresponda y verificar el encuadre con una vista previa.

Reference: Paso 6 · CLAUDE.md / graphics

### No aparece el agente de ayuda

En Claude Code comprueba .claude/agents/video-editor-help.md. En Codex pide el modo de ayuda de AGENTS.md. Los agentes de .claude no se registran automáticamente en Codex.

Reference: help/USAR-CON-CODEX.md

### No aparece el agente de ayuda

Comprueba que existe .claude/agents/video-editor-help.md dentro de la carpeta abierta. Reinicia Claude Code e intenta de nuevo. El agente de ayuda lee y explica; las reparaciones las aplica el editor principal.

Reference: Paso 9 · help/QUICK-START.md

### ¿Puedo usar ChatGPT o Claude desde el navegador?

La guía se puede leer en el navegador, pero el editor necesita Claude Code o Codex con acceso a la carpeta local y sus herramientas. El uso de IA y las aplicaciones opcionales no están incluidos.

Reference: help/USAR-CON-CODEX.md

### ¿Qué cambia al usar Codex?

Codex lee AGENTS.md. Las etapas del editor siguen en .claude/skills como documentación. Los hooks, agentes y conexiones de Claude Code no se importan automáticamente. Revisa la guía de Codex antes de elegir una integración.

Reference: help/USAR-CON-CODEX.md

### La exportación se detuvo · ya existe un final

El kit conserva el final anterior. Elige un nuevo proyecto o versiona la entrega; no borres el archivo aprobado para forzar el proceso. Indica el nombre exacto del borrador que revisaste.

Reference: finalize.sh · workflows/verify-export.py

## Más problemas frecuentes

Tabla completa en español: `help/SOLUCION-DE-PROBLEMAS.md`.
