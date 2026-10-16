# Video Editor — instrucciones para Codex

Trabaja con el kit local completo. El objetivo es editar material del usuario y entregar un archivo verificado; publicar en redes queda fuera del flujo.

## Inicio
Lee `help/USAR-CON-CODEX.md`, `CLAUDE.md`, `SETUP.md` y `LANES.md`. CLAUDE.md documenta el proceso compartido; adapta sus referencias específicas a Claude según las reglas siguientes. No afirmes que una conexión está activa sin comprobar sus herramientas.

## Perfil de estilo (v1.3)
- Al inicio de cada sesión, después de `bash setup.sh --check`, ejecuta `python3 workflows/profile.py status` (en Windows `python`). Código 3 = creador nuevo sin perfil de estilo: ofrece `empezar` (onboarding de estilo, ~10 min) antes de editar. Si dice que no, crea un perfil con valores por defecto (`python3 workflows/profile.py new <slug> --defaults`) para no volver a preguntar. Nunca bloquees una edición por esto.
- Cuando el usuario escriba `empezar` (o «soy nuevo», «configurar mi estilo», «actualizar mi estilo», «nuevo perfil», «usa el perfil …»), lee y sigue `.claude/skills/empezar/SKILL.md`.

## Adaptación del entorno
- Las instrucciones por etapa están en `.claude/skills/`. Lee el SKILL.md de la etapa requerida y sus referencias como documentación local. No supongas que Codex registra esas carpetas como skills o comandos automáticamente.
- Empieza una edición por `.claude/skills/edit-video/SKILL.md`. Conserva el proceso de ingestión, revisión y exportación y su registro RUN.md.
- Los hooks y agentes de `.claude` son específicos de Claude Code. Realiza explícitamente la comprobación de requisitos con `bash setup.sh --check`; no dependas de un hook de inicio.
- No ejecutes comandos `claude mcp` para configurar Codex. `.mcp.json` no demuestra una conexión en Codex. Revisa las herramientas realmente disponibles y la configuración MCP oficial del entorno antes de elegir una ruta que las requiera.
- Si una etapa exige una herramienta ausente, explica qué falta. No inventes llamadas, renders ni validaciones. La ruta chat-only usa procesamiento local y tampoco funciona sin sus dependencias.
- Los nombres de modelos de Claude y sus mecanismos de subagentes no son instrucciones de configuración para Codex. Mantén el modelo seleccionado por el usuario; no inventes equivalencias. Si no hay delegación disponible, realiza las etapas secuencialmente.
- Respeta los permisos del entorno. No desactives protecciones ni apruebes servidores en nombre del usuario. Explica las instalaciones y servicios de pago antes de activarlos.

## Modo de ayuda
Cuando el usuario pida ayuda con el kit, consulta `help/GUIA-PASO-A-PASO.md`, `help/SOLUCION-DE-PROBLEMAS.md` (español; `help/TROUBLESHOOTING.md` en inglés) y el documento correspondiente al problema. Opera en modo de lectura: explica lo confirmado, lo pendiente y hasta tres pasos concretos. No cambies archivos durante un diagnóstico salvo que el usuario pida aplicar la solución. Esto es un modo de trabajo del asistente, no un subagente aislado ni una restricción técnica de herramientas.

## Entrega
Conserva originales; trabaja en un proyecto nuevo. Comprueba archivos, duración, dimensiones y reproducción. Pide revisión del borrador antes del final. Marca cualquier parte no probada. No prometas automatización total si hubo pasos manuales.

## Instalación y cierre en esta edición
Para configurar el procesamiento local en Codex usa `bash setup.sh --host codex --lane chat-only`, después del diagnóstico. El instalador rechaza otras rutas en Codex antes de modificar el equipo; comprueba los puentes por separado según la guía. Una ruta ausente no significa Premiere. Un fallo obligatorio bloquea sus etapas dependientes. Exporta la fuente exacta aprobada con finalize.sh; nunca elijas por fecha ni limpies borradores automáticamente.
