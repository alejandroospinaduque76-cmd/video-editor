# Solución de problemas

Usa esta tabla junto con los documentos del kit. No apliques un arreglo solo porque el título se parece a tu caso: revisa el error exacto y la ruta de edición que elegiste.

| Qué pasa | Qué revisar primero | Dónde seguir |
|---|---|---|
| Windows no reconoce un comando | ¿Está instalado Git Bash y lo ve Claude Code? | `SETUP.md`, sección Windows. Reinicia después de instalar. |
| "No such file or directory" al guardar en Windows | ¿La carpeta del kit está en OneDrive o en una carpeta protegida? | `SETUP.md`, ubicación en Windows. Copia el kit a una carpeta local normal. No desactives protecciones del sistema. |
| Falta FFmpeg, uv, Node o Pillow | Lee el informe de requisitos | `./check-setup.sh` y `SETUP.md`, sección Core. Deja que el editor haga la instalación indicada, con tu aprobación. |
| La primera transcripción tarda mucho | ¿Está descargando o creando el entorno? ¿Avanza? | La primera edición descarga una sola vez unos 4 GB (motor de transcripción y modelos) y ocupa unos 5 GB en disco. Con conexión rápida tomó unos 2–3 minutos; con conexión lenta tarda más. No borres cachés ni la interrumpas si hay progreso. |
| Aparece un texto largo en rojo que menciona `torchcodec` o `libavutil` | ¿La transcripción terminó y escribió `words.json`? | Es un aviso de una dependencia y no afecta el resultado. Si la transcripción terminó, ignóralo. |
| La transcripción salió en otro idioma | ¿El clip mezcla idiomas o es muy corto? | El idioma se detecta en cada clip. Para forzarlo, pide al editor que vuelva a transcribir con `--force --lang es`. No cortes sobre una transcripción en un idioma que no hablaste. |
| Un nombre sale mal en los subtítulos ("Clot", "Cloud" en vez de Claude) | Compara con lo que dijiste | Agrega la corrección en `projects/<trabajo>/corrections.local.json` (por ejemplo `{"auto": {"Clot": "Claude"}}`) o en `transcript-corrections.json` para todos tus trabajos. Se corrige una vez y llega a subtítulos y gráficos. |
| Los colores de un clip de iPhone se ven lavados, grises o saturados | ¿Grabaste con "Vídeo HDR" activado? (viene activado de fábrica) | Desde la v1.2 el editor convierte HDR a SDR al importar el clip (`workflows/normalize-source.py`). Si avisa que falta un filtro de conversión, o usas una versión anterior: en el iPhone, Ajustes → Cámara → Grabar vídeo → desactiva "Vídeo HDR" y vuelve a grabar. |
| El video suena más bajo que otros en Reels o TikTok | ¿Subiste el final o una entrega por plataforma? | Pide "prepara la entrega para Reels" (o TikTok, Shorts, YouTube). `workflows/deliver.py` crea `outputs/<trabajo>.reels.mp4` a unos −14 LUFS sin tocar el final. |
| El motor de gráficos sugiere actualizarse ("npx hyperframes@latest upgrade") | — | No actualices. El kit está probado con la versión 0.8.16 y los estilos dependen de ella. |
| La configuración pide reiniciar | Hay herramientas o conexiones nuevas sin cargar | `CLAUDE.md`, primer uso. Abre el mismo proyecto y di "continúa la configuración". |
| No aparecen las herramientas de Premiere | ¿Se instaló y aprobó la conexión local? | `SETUP.md` y `lanes/premiere/`. No instales paquetes no oficiales con nombre parecido. |
| Resolve dice BRIDGE_UNAVAILABLE | ¿Qué edición de Resolve tienes? ¿Está corriendo el puente? | `CLAUDE.md`, primer uso; `LANES.md`, Resolve. En la edición gratuita, el puente se inicia desde la aplicación. |
| Un gráfico o subtítulo tapa la cara | Revisa el paso de encuadre y gráficos | Pide al editor que mida de nuevo las zonas libres de la cara y mueva el elemento. |
| Se perdieron los efectos de audio al rehacer la línea de tiempo | ¿Se recreó la línea de tiempo en la aplicación? | `CLAUDE.md`, pulido de audio, y la sección de tu ruta en `LANES.md`. Pide al editor que vuelva a aplicar la etapa de audio. |
| Se interrumpió un trabajo | Busca su `RUN.md` | Retoma desde la última etapa con evidencia. |
| No encuentras el video exportado | Revisa la ruta que informó el editor | El archivo final queda en `projects/<trabajo>/outputs/<trabajo>.final.mp4`. `finalize.sh` no lo copia a Descargas (solo los clips que arma el clipper con `make-clips.py --build` dejan una copia en `~/Downloads/`). |
| "Ya existe un final" al exportar | ¿Ya exportaste este trabajo? | Es una protección: el kit nunca sobrescribe un final. Pide una versión nueva del trabajo. |
| No aparece el agente de ayuda | ¿Abriste la carpeta completa, incluida la oculta `.claude/agents`? | `help/GUIA-PASO-A-PASO.md`. Abre de nuevo la carpeta correcta. |
| Una función necesita una API de pago | ¿Es opcional? ¿Qué servicio usa? | Lee la documentación de esa función. Los créditos no vienen incluidos; tú decides si la activas. |
| El kit no me reconoce (me trata como nuevo o usa el perfil de otra persona) | ¿Qué perfil está activo? Pide `python3 workflows/profile.py status` y `list` | Si tu perfil aparece en la lista: `python3 workflows/profile.py use <tu-perfil>`. Si venías de otra versión del kit, escribe empezar y di dónde está la carpeta anterior (o `profile.py import mi-estilo.zip`). |
| Quiero volver a empezar mi estilo | ¿Quieres corregir algo o empezar de cero? | Para corregir, dilo en una frase («subtítulos más grandes»). Para empezar de cero, di «nuevo perfil»: crea uno nuevo y deja el anterior guardado (vuelves con «usa el perfil <nombre>»). |

## Si necesitas ayuda, copia esta ficha

- Versión del kit (archivo `VERSION`):
- Sistema operativo:
- Claude Code o Codex, y su versión:
- Aplicación de edición y versión, o chat-only:
- Etapa del trabajo:
- Qué esperabas:
- Qué pasó:
- Error exacto, corto, sin claves ni datos personales:
- Qué ya intentaste:

No incluyas contraseñas, material privado ni datos de clientes. El agente de ayuda no debe inventar un diagnóstico ni decir que algo quedó arreglado sin evidencia.
