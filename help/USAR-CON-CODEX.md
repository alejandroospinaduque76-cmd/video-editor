# Usar Video Editor con Codex

## 1. Abre la carpeta completa
Extrae el ZIP. Abre `video-editor` como proyecto local en Codex. Debes ver `AGENTS.md`, `CLAUDE.md`, `SETUP.md` y la carpeta oculta `.claude`. Esta contiene documentos compartidos: no la borres aunque uses Codex.

Si usas la aplicación, selecciona esa carpeta al crear el proyecto. Si ya usas la CLI, abre una terminal en esa carpeta y ejecuta `codex`. Usa las instrucciones oficiales para instalar y autenticar tu entorno: https://developers.openai.com/codex/quickstart

Una conversación normal en ChatGPT web no da acceso automático a estos archivos ni ejecuta el kit. Necesitas un entorno Codex local con permisos para trabajar en la carpeta.

## 2. Comprueba antes de instalar
Copia esta instrucción:

> Lee AGENTS.md y help/USAR-CON-CODEX.md. Confirma que estamos en la carpeta completa del kit. Lee SETUP.md y ejecuta bash setup.sh --check. Explícame qué requisitos faltan, qué descargas se necesitan y qué ruta local podemos probar. No cambies mi configuración global ni conectes servicios de pago sin explicarlo.

El kit conserva scripts y documentos de su ruta original en Claude Code. AGENTS.md explica cómo seguirlos en Codex. Sus hooks, agentes y conexiones no se importan automáticamente.

## 3. Elige una ruta real
Empieza por el procesamiento local `chat-only` si no necesitas controlar una aplicación. El nombre no significa un chat web: el render ocurre en tu computador. Requiere FFmpeg, transcripción y las herramientas gráficas documentadas. Consulta LANES.md para los límites de color y efectos.

Para instalar esta ruta local, después de revisar los requisitos, usa `bash setup.sh --host codex --lane chat-only`. Esta combinación evita registrar servidores de Claude Code.

Para Premiere o Resolve, comprueba que el puente y sus herramientas estén conectados también en Codex. La presencia de `.mcp.json` no basta. No copies claves ni rutas ajenas. Consulta la configuración MCP oficial: https://developers.openai.com/codex/mcp

## 4. Haz una prueba pequeña
Usa un clip propio de 20–60 segundos. Completa el generador de instrucciones de START-HERE.html y pega el resultado en Codex. Revisa transcripción, cortes y borrador antes del archivo final.

## 5. Usa el modo de ayuda

> Actúa en modo de ayuda de Video Editor según AGENTS.md. Lee la guía y la documentación de mi ruta. Estoy en [sistema], usando [ruta]. Esperaba [resultado] y ocurrió [problema]. Este es el error sin datos privados: [mensaje]. Explica qué está confirmado y dame hasta tres pasos. No modifiques archivos todavía.

En Claude Code existe un agente de ayuda registrado en `.claude/agents/`. En Codex la ayuda funciona mediante estas instrucciones del proyecto: no se presenta como un subagente aislado.

## Estado de comprobación
Esta adaptación incluye instrucciones de proyecto y rutas documentadas. Aún no se ha verificado una edición completa desde una instalación limpia en Codex. Las conexiones a aplicaciones deben probarse en el computador del comprador. No presupongas equivalencia automática de todas las integraciones.
