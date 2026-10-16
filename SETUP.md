# Inicio para esta edición del kit

Abre START-HERE.html. Usa Claude Code o Codex local, con la carpeta completa.

1. Diagnóstico sin instalar: `bash setup.sh --check`.
2. Para Codex local sin aplicación de edición: `bash setup.sh --host codex --lane chat-only`. Revisa primero requisitos y descargas. No registra conexiones de Claude.
3. Para Claude Code, sigue la instalación y la ruta documentadas abajo.
4. En Codex con Premiere o Resolve, sigue `help/USAR-CON-CODEX.md`; el instalador de Claude no valida conexiones de Codex.
5. Prueba un clip de 20–60 segundos. Un diagnóstico correcto no demuestra una edición completa.

La documentación histórica de abajo explica las herramientas y rutas de Claude Code. Las reglas de esta edición en CLAUDE.md y AGENTS.md prevalecen para instalación, fallos y exportación.

---

# 🛠️ Setup — read this first

This is a **video editing system you run with [Claude Code](https://claude.com/claude-code).** You
drop in raw footage, and Claude takes it from **raw → fully edited → exported.** It does short-form
explainers, TikTok/raw-style verticals, and long-form YouTube intros, with locked, on-brand captions,
graphics, colour and sound design.

**Verified end to end on macOS (chat-only route).** Windows and Linux are **supported by the scripts,
not yet verified end to end**: the installer and every pipeline script have Windows/Linux paths, but
no complete raw → export run has been confirmed on them yet. On a Mac it uses Apple's hardware video
encoder; on Windows/Linux the scripts use software encoding (slower). If you are on Windows or Linux,
run one short test clip first and report anything that breaks.

The fastest path: unzip, open this folder in Claude Code (the one named `video-editor`, with `setup.sh`
and `CLAUDE.md` in it; Windows' Extract All puts it one level down), and say **"Set this up on my
machine"**. Claude detects your OS, runs the one-command auto-installer (**`./setup.sh`**: installs every
tool via Homebrew on macOS / winget on Windows, bootstraps the render engine, verifies itself,
**auto-detects your editing app** (Premiere Pro / DaVinci Resolve / CapCut / Final Cut Pro) and wires its lane, and
is safe to re-run), and walks you through the one or two restarts along the way. If you have several
editing apps installed it asks one question: which one you edit in. That's the whole setup.
Personalizing the look/voice (your brand kit) is **optional** and can happen any time later, or
never. Everything below is the same setup by hand, if you prefer to see each step.

### 🍎 Mac requirements

**Apple Silicon (M1 or later)** is the route verified end to end (chat-only). An **Intel Mac** gets its own
transcription stack (whisperx 3.3.1 on PyTorch 2.2.2, the last PyTorch built for Intel Macs), installed on its
own; that version is in its final test. If anything fails on an Intel Mac, write to us (the contact is on your
receipt): we tell you when it is ready, or refund you. Homebrew is installed by `./setup.sh` when missing.

### 🪟 On Windows — one install first

Use native Windows, not WSL or a virtual machine (`check-setup.sh` detects WSL2 and may run there, but it is not the supported path). Its scripts run through **Git Bash**, the
Unix shell that ships with **Git for Windows** (it's also the shell Claude Code itself uses on
Windows), so that's the one thing to install first:

1. Install **Git for Windows**: `winget install Git.Git` (in PowerShell), then restart Claude Code
   so it finds Git Bash.
2. Unzip the project **outside Documents, Desktop, Pictures, Videos, Music and OneDrive**, e.g.
   `C:\Users\<you>\video-editor` (Windows Explorer's Extract All is fine), and open that folder in
   Claude Code. Those folders are guarded by Windows Security's Controlled Folder Access on many
   machines, which silently blocks Git Bash, node and python from writing there, and the error
   reads "No such file or directory", not "permission denied". `./setup.sh` checks for this first
   and says what to do.
3. That's it. Everything below runs unchanged; wherever a command says `brew`, use the
   **Windows (winget)** version below. After any `winget install`, open a **new** terminal
   (and restart Claude Code once) so PATH picks the tool up.

---

## 1. Install the prerequisites

**The automatic way** (recommended; auto-installs on macOS + Windows, prints the exact apt
commands on Linux and finishes the rest there too):

```bash
./setup.sh
```

It detects your OS, installs everything missing, bootstraps the render engine, verifies, then
auto-detects your editing app and wires its lane (one app: wired automatically; several: it asks
which you edit in). Re-run it after any restart: it skips what's done and finishes the rest. (The
one manual step it can ask of you: installing Homebrew itself on a fresh Mac, which needs your
password; after that it finds Homebrew and puts it on your PATH itself.) It tells you exactly when a
Claude Code restart is needed; at most two once setup starts (once when just-installed tools or
Homebrew's PATH need a fresh session, once after an editing-app MCP is wired), plus the one-off
Git for Windows restart above if you needed that. Setup pre-approves the editing app's connection, so
after the MCP restart there should be nothing to click; if Claude Code does ask whether to enable this
project's `.mcp.json` servers, answer yes. (Clicked no? Claude clears it with `claude mcp
reset-project-choices`, then one more restart.)

**The manual way** — run the report-only checker and follow what it prints:

```bash
./check-setup.sh
```

### Core (required — the raw → exported pipeline)

`./check-setup.sh` prints the right command for whichever OS you're on — run it and follow what it shows.

**macOS:**

```bash
# Homebrew (skip if you already have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install ffmpeg          # every audio/video pass (cut, captions, music, render)
brew install uv              # builds the WhisperX transcription engine on first run
brew install node            # the graphics render engine (npx hyperframes)
brew install python          # caption text overlays + the pipeline scripts
brew install pillow          # PIL — text overlays (this ffmpeg has no built-in text)
brew install yt-dlp          # optional: downloading reference clips + YouTube research
```

**Windows (winget — built into Windows 11 / App Installer):**

```bash
winget install Gyan.FFmpeg           # every audio/video pass (cut, captions, music, render)
winget install OpenJS.NodeJS.LTS     # the graphics render engine (npx hyperframes)
winget install Python.Python.3.12    # caption text overlays + the pipeline scripts
winget install astral-sh.uv          # builds the WhisperX transcription engine on first run
python -m pip install pillow         # PIL — text overlays (run AFTER the Python install, new terminal)
winget install yt-dlp.yt-dlp         # optional: downloading reference clips + YouTube research
```

> Open a **new terminal** after the winget installs (and restart Claude Code once) so PATH updates.
> Note: on Windows, Python is `python`, not `python3` — the `python3` name there is a fake
> Microsoft Store stub. The pipeline scripts handle this automatically.

**Linux (Ubuntu / Debian):**

```bash
sudo apt update
sudo apt install -y ffmpeg python3 python3-pip python3-pil fonts-dejavu-core   # video passes + caption text (PIL) + the caption mono

# Node ≥22 (the render engine) — Ubuntu's apt node is too old, so use NodeSource:
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs

# uv (builds the WhisperX transcription engine on first run):
curl -LsSf https://astral.sh/uv/install.sh | sh

sudo apt install -y wamerican   # optional: enables the transcript-QA word scan
uv tool install yt-dlp          # optional: reference clips + YouTube research (apt's build is too old for YouTube)
```

Then bootstrap the render engine **once**:

```bash
npx hyperframes@0.8.16 browser ensure   # one time, about 270 MB: the render engine and its headless browser
```

> Pinned to `@0.8.16` — the version the locked caption/graphics presets were validated against.
> Using the same version for the one-time bootstrap means it's cached once and every render uses it.
> Its npm and telemetry notices are noise; ignore any "newer version available" line and never run
> `hyperframes upgrade`.
>
> **On Linux,** if the bootstrap (or a render) reports a missing shared library, install the headless-Chrome
> deps it names, e.g. `sudo apt install -y libnss3 libatk-bridge2.0-0 libgtk-3-0 libgbm1 libasound2t64`.

**Language.** Transcription auto-detects the spoken language of each clip (Spanish, English, Portuguese, … — the WhisperX large-v3 list) and loads the matching word aligner, one download per language. To force it: `bash .claude/skills/rough-cut/scripts/transcribe.sh projects/<job> --force --lang es` or `WHISPERX_LANG=es`. A transcript in a language you did not speak means the detection missed: re-run with `--lang`, never cut on it.

**First edit is slow, once.** The first time you run a job, the rough-cut step downloads the WhisperX
`large-v3` speech model and builds its environment: about 4.3 GB of downloads and 5.2 GB on disk (measured on a Mac
with empty caches, 2026-09-25; keep at least 10 GB free). That takes a few minutes on a fast connection and needs
internet — but only the first time. Every job after is fast. **Your hardware is auto-detected:** an
NVIDIA GPU (Windows/Linux) transcribes on CUDA, several times faster than CPU (the first build adds
the ~3 GB CUDA stack), and if the GPU path ever fails it falls back to CPU automatically, so
transcription always works. The GPU build is verified, not assumed: the transcriber probes CUDA
after installing it and records what actually works, and if it ever has to fall back it prints a
loud SLOW PATH banner rather than quietly taking several times longer. Macs and GPU-less machines
run the reliable CPU path. **If that first build
is interrupted** (a closed laptop, a dropped connection), nothing is left half-broken: the transcriber
records a `.deps-ok` sentinel only once the environment is complete, so on the next run it sees the
incomplete state, wipes `~/.cache/video-editor/whisperx-venv` and rebuilds cleanly. (Same idea, much smaller: the face-framing
tool `workflows/face-frame.py` auto-installs its OpenCV dependency via `uv` on first use, ~50 MB.)

### Fonts — bundled, plus one system font

- **Inter** — bundled in `assets/fonts/` (free, Open Font License). The display font for the Talking Head
  Explainer graphics and liquid-glass. Nothing to install — and it's the cross-platform default. *(macOS only:
  prefer Apple's SF Pro?* Install the free "San Francisco Pro" pack from <https://developer.apple.com/fonts>
  and set it in `brand-kit.md`. On Windows/Linux, stay on the bundled Inter.)
- **Playfair Display** — bundled in `assets/fonts/` (free, Open Font License): the display serif for titles and big words. Nothing to do.
- Explainer captions use the bundled **Inter Bold**. Every bundled font ships with its licence file (`OFL-*.txt`) next to it.
- **The caption mono** (the Talking Head Explainer's captions) is the one system font, and one of these
  must exist: SF Mono or Menlo (macOS, both already there), Consolas Bold (Windows, already there) or
  DejaVu Sans Mono Bold (Linux: `sudo apt install -y fonts-dejavu-core`, in the apt line above).
  `captions.py` names the font it used. With none of them, `./check-setup.sh` counts it missing and
  prints that fix, since the captions step cannot run without one.
- **SF Pro (system)** — *optional.* The TikTok/raw overlays render from bundled **Inter** by default; SF Pro is not required.

### Optional (only if you use the feature)

- **Premiere lane** (the recommended finish if you edit in Premiere — the rough cut
  lands on your timeline as **separate, trimmable clips**, and Claude can build graphics, apply
  effects, recolor sections, and run the final export in there too): one command,
  ```bash
  ./setup-premiere.sh
  ```
  It installs the pinned Premiere MCP engine (`vendor/premiere-mcp`, built from source at a verified
  commit), installs the **MCP Bridge (CEP)** panel into Premiere, and writes `.mcp.json`. Safe to
  re-run; it skips what's already done. Requires **Adobe Premiere Pro** (validated on Premiere Pro 2026, 26.x) on
  **macOS or Windows** — plain Linux has no Premiere, use the default chat-only pipeline.
  Afterward: restart Premiere (setup patches the panel to start the bridge itself, so there is
  nothing to click) → restart Claude Code once (through `./setup.sh --lane premiere` the connection is
  pre-approved; run directly, answer yes when Claude Code asks) → verify with `node lanes/premiere/premiere-bridge.mjs ping`.
- **DaVinci Resolve lane** (the same finish, in Resolve on macOS, Windows, or Linux; Studio and
  the free edition both work): one command,
  ```bash
  ./setup-resolve.sh
  ```
  It installs the pinned Resolve MCP server (`vendor/davinci-resolve-mcp`, built from source at a
  verified commit), detects your edition, and writes the `davinci-resolve` entry into `.mcp.json`
  (other servers are left untouched). Safe to re-run. **Studio:** the MCP talks to Resolve's
  scripting API directly (on Windows with Studio 21.1 or newer, setup wires Blackmagic's own
  `ResolveMCP.exe` instead and keeps the pinned server as the fallback: `./setup-resolve.sh
  --community` switches to it); Resolve just has to be running (Claude can launch it), and there's
  nothing to change inside it: **External scripting = Local is its default** (only if the
  connection fails, check **Preferences → System → General → External scripting = Local**).
  **Free edition:** Blackmagic gates external scripting to Studio, so setup installs the MCP's
  in-app bridge into Resolve's Scripts menu and enables it. One recurring step, every time you
  start Resolve: open a project, then **Workspace → Scripts → resolve_bridge**, and leave it
  running. (Detected the wrong edition? `./setup-resolve.sh --studio` or `--free`.) Afterward:
  restart Claude Code once (through `./setup.sh --lane resolve` the connection is pre-approved; run
  directly, answer yes when Claude Code asks) → verify by asking Claude to get the Resolve version. The `davinci-resolve` skill documents
  everything the lane can do, plus the API calls to avoid.
- **CapCut lane** (the same, in the CapCut desktop app — macOS and Windows): nothing to
  install beyond CapCut itself. `uv run lanes/capcut/capcut-bridge.py replay <job>` writes the rough cut
  as a native CapCut draft, one trimmable clip per cut. **Quit CapCut fully before running it** (it
  clobbers new drafts on exit otherwise). Full lane rules + live-editing commands: the CapCut section
  in `CLAUDE.md`.
- **Final Cut Pro lane** (the same finish, in Final Cut Pro on macOS; the App Store's one-time purchase or
  Apple Creator Studio): one command,
  ```bash
  ./setup-finalcut.sh
  ```
  It installs **SpliceKit** (an open-source tool, MIT; the pinned release, checked against its published
  checksum), which makes a **separate, patched copy** of Final Cut in `~/Applications/SpliceKit/` with a bridge
  inside that Claude drives. Your App Store Final Cut is never changed, and libraries work in both. **One click
  from you:** SpliceKit opens, you quit Final Cut and click **Continue**, and it tells you when it's done (the
  same click again after every Final Cut update). Setup also puts the house look into Final Cut's Custom LUTs
  and writes the `splicekit` entry into `.mcp.json`. Safe to re-run. Afterward: restart Claude Code once, and
  always open the PATCHED copy (in `~/Applications/SpliceKit/`) when Claude edits for you. Claude builds each
  timeline from your job's files, brings it in through Final Cut's own importer, and exports with no clicks;
  the `final-cut-pro` skill documents the lane.
- **Speaker labels** (`rough-cut --diarize`): needs a free Hugging Face account and token — set
  `HUGGINGFACE_TOKEN` (see `.env.example`) and accept the pyannote/speaker-diarization-community-1 model terms (the default of the pinned whisperx 3.8)
  on Hugging Face. **Not verified end to end yet** — treat it as experimental. The normal
  single-speaker flow does **not** need this.
- **On-screen secret sweep** (`workflows/pii-scan.py`, for screen-recording or live-call footage):
  macOS reads the frames with the system's own OCR through a small Swift shim (needs the Xcode command
  line tools, `xcode-select --install`); Windows and Linux use `workflows/ocr_shim.py` (RapidOCR, which
  `uv run` installs on first use, offline after its models download; on Windows it runs on the GPU through
  DirectML, about 0.12 s a frame, any DirectX 12 GPU, with the CPU, about 1 s a frame, as its fallback). The slice-ASR checks, `cut-audit.py`'s content gate (with `--say` and
  `--spans-out`) and the Premiere lane's `cut-proof.py`, run mlx-whisper on macOS and the WhisperX venv's
  faster-whisper everywhere else (`workflows/asr_cli.py`; CUDA when the venv has it), so they need one
  transcription first to build that venv.
- **yt-dlp** (downloading reference clips and YouTube research for graphics): nothing in the pipeline
  calls it, it's a hand tool. `./setup.sh` installs it for you on macOS and Windows; on Linux run
  `uv tool install yt-dlp` (apt's build is too old for YouTube). Clips headed into Premiere must be
  H.264 (the format string is in `lanes/premiere/lab-notes.md`).

---

## 2. Make it yours (optional: any time, or never)

The editor works out of the box with a neutral bundled look (Inter fonts, a generic starter
palette). Personalization only makes captions and graphics sound and look like *you*.
Whenever you want that:

1. **Fill in `brand-kit.md`** — your name, niche, handles, voice/tone, brand colors, fonts, hook style,
   and brand wordlist. This is the one file that drives how every caption and graphic sounds and looks.
   (Part A is the fill-in form; **Part B** spells out exactly which file and token each value changes, if
   you want to do it by hand or verify Claude's work.)
2. *(Optional)* **Add your logos** to `assets/logos/` — any brand marks you want available for graphics.

Then tell Claude **"apply my brand kit"** and it writes those values into the presets and `my-rules.md`
(your own file) for you (the exact map is Part B of `brand-kit.md`), and renders a quick test so you can see the look
took.

---

## 3. Edit your first video

1. Put a raw clip somewhere handy (e.g. `~/Downloads`).
2. In Claude Code, say: **"edit this video: ~/Downloads/yourclip.mp4"**.
3. Claude copies it into `projects/<job>/raw/`, runs the rough cut, plans graphics, and walks the rest
   of the pipeline with you. It auto-detects the format from the footage (vertical = short-form,
   horizontal = long-form YouTube) and states the hook + takeaway it read from your transcript;
   correct it in a word if it read wrong.
   Before anything reads the clip, `workflows/normalize-source.py` converts iPhone HDR to SDR, variable
   to constant frame rate and bakes the rotation; your untouched copy stays in `raw/_source/`.
4. The finished deliverable is `projects/<job>/outputs/<job>.final.mp4`. Once you approve a draft,
   Claude runs `bash finalize.sh <job> --source <approved-file.mp4> --approved --apply`: it verifies that
   exact file and copies it to the `.final.mp4`. It never picks a draft by date, never deletes drafts,
   never overwrites an existing final and does **not** copy anything to `~/Downloads/`.
5. For upload, ask for a platform master ("prepare the Reels delivery"; also TikTok, Shorts, YouTube):
   `python3 workflows/deliver.py <job> --platform reels --apply` writes `outputs/<job>.reels.mp4`
   (about -14 LUFS, platform size) and leaves the final untouched.

That's it. The whole pipeline and how each step works is documented in `CLAUDE.md`.

---

## 4. Update to a new version

A new version arrives as a new ZIP (`CHANGELOG-CUSTOMER.md` says what changed). Never unzip it over the
folder you already use. Unzip it into a NEW folder, open that folder in Claude Code and say **"run the
setup"**, then move your own work across from the old folder: `projects/` (your jobs), `creator/` (your
style profile), `my-rules.md`, `brand-kit.md` if you filled it in, and `.env` if it holds your keys. Keep
the old folder until the new one has edited a video.

---

## What's in the box

| Path | What it is |
|------|-----------|
| `CLAUDE.md` | The editor's brain — the pipeline, the rules, the format variants. |
| `brand-kit.md` | Optional personalization: fill it in whenever you want the output to carry your brand. |
| `setup.sh` | One-command auto-setup: detects macOS/Windows, installs everything, bootstraps the renderer, wires your editing app's lane. |
| `check-setup.sh` | Prerequisite checker (report-only). |
| `.claude/skills/` | The editing skills + the HyperFrames render toolkit. The rough cut includes `rough-cut/scripts/find-fillers.py`, which lists the hesitations Whisper leaves out of the transcript ("eh", "mmm", "este…") as cut candidates for review — it never cuts on its own. |
| `presets/` | The locked looks, one folder per preset — **`youtube/default/` (THE long-form default: the overlay cards + the creative-moves vocabulary)**, the house short-form Explainer (signature style, reference craft, captions), the Talking Head Explainer (short-form: layout rotation, graphics, captures, captions, sound), TikTok/raw, liquid-glass, the vox print-collage long-form look (which carries `motion-craft.md`, its own craft rules — vox-only, never the default). |
| `workflows/` | Universal utilities: `normalize-source.py` (intake: iPhone HDR → SDR, variable → constant frame rate, rotation baked), `voice-gain.py` for step 3, `sfx-plan.py` for step 6, face framing, chin line, the face guard, the graphics QA gate, hand tracking, cut-outs, window capture, window capture and recording, the on-screen secret sweep, the second-camera lip-sync measurement, the re-cut ripple, plus the export tools `verify-export.py`, `finalize-safe.py` (what `finalize.sh` runs) and `deliver.py` (the house export encode from a master, and the platform delivery masters). Nothing app-specific. |
| `lanes/` | Everything app-specific, one folder per editing app: `premiere/` (bridge, launch, grade, placement scripts + templates), `resolve/` (`resolve-templates/` fps-matched project templates, `resolve-grading/` the color playbook, `resolve-export.md` delivery-render settings, `resolve-audio-polish/` the final audio pass), `capcut/` (the bridge + schema templates), `chat-only/` (`assemble.py`, which composites the placed graphics and captions over the cut and writes `outputs/<job>.draft-vN.mp4` — `python3 lanes/chat-only/assemble.py projects/<job> --draft` — plus the incremental re-render sheet), `finalcut/` (the Final Cut Pro lane through SpliceKit). Each carries a `lab-notes.md` with that app's own gotchas. `LANES.md` at the root says, per pipeline step, which app has a scripted recipe and where it lives. |
| `assets/` | Fonts (bundled, OFL/licence files included: Inter — `Inter-Bold.otf` is the caption font —, Playfair Display, Public Sans, Montserrat, Outfit) + the face-detection model + `luts/` (30 cubes, with the house **Autumn-Rec709** look captured and ready so step 4 grades itself) + `sfx/` (the full SFX library the presets were tuned on, 150 clips, so step 6 runs with nothing else to download) + `logos/` for your own brand marks (you supply). |
| `projects/` | Your job folders land here (one per video). A finished job you no longer need moves off whole: to an external drive when one is connected, otherwise to the Trash (Recycle Bin on Windows). Ask Claude to clear it out. |
| `finalize.sh` | The export step — `bash finalize.sh <job> --source <approved-file.mp4> --approved --apply` verifies the draft you approved and copies it to `outputs/<job>.final.mp4` (`--variant NAME` for a second deliverable in `outputs/NAME/`). Without `--apply` it only verifies. Never auto-picks, never deletes drafts, never overwrites a final, never copies to `~/Downloads/`. |
| `my-rules.md` | Your own standing instructions for Claude; the kit never writes it, and it moves whole to a new version. |
