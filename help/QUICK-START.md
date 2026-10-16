# Your first video

Open START-HERE.html for the visual guide, route selector, prompt builder and examples. / Abre START-HERE.html para ver imágenes y usar las herramientas.

## 1. Meet your kit

Know what each part does before you install.

1. The editor is a collection of instructions and tools that Claude Code or Codex runs on your computer. You supply footage and review its editing decisions.

2. This guide walks you through the workflow. The help agent reads the kit documentation to explain questions and investigate errors.

3. You need your own Claude Code or Codex access, internet for setup and room for footage and downloads. AI usage, paid editing apps and optional services are separate.

Success: You can identify the editor, guide and help agent. You have a 20–60 second clip of your own to practice with.

If stuck: Expected a standalone app? This kit runs inside Claude Code. Step 2 prepares that environment.

## 2. Open the right folder

Get the kit ready for your first conversation.

1. Extract the entire ZIP, including .claude, into a local folder. Check SETUP.md, CLAUDE.md and AGENTS.md.

2. Open the folder in your chosen local environment: Claude Code or Codex. Windows scripts require Git Bash.

3. Type empezar (Spanish for "start"). The editor confirms the folder, checks your computer and tools, then learns your editing style. In Codex it follows AGENTS.md and help/USAR-CON-CODEX.md; Claude hooks and MCP connections are not imported.

> empezar

Success: Claude Code is open in video-editor and can read SETUP.md. The hidden .claude folder is still included.

If stuck: If SETUP.md is missing, you may have opened the parent folder or an incomplete copy. Check the location before installing tools.

## Your style

The first time, type **empezar** (or "start"). The editor checks your computer, asks up to 5 questions in one message (name and handle, platforms, captions A/B/C, filler words, words the transcript gets wrong), measures 1–3 finished videos you like (analysed on your computer, never uploaded) and edits your first clip in that style.

- Your style is written to `creator/perfiles/<your-profile>/ESTILO.md`. Correct any line in one sentence ("shorter pauses"). During each review it asks "always like this?" and learns.
- Several creators or clients: say "new profile" and "use profile <name>".
- Rather not set it up? Say no: it edits with the kit's neutral style and stops asking. Type empezar any time later.
- When you move to a new kit version, type empezar in the new folder and say where the old one is: it brings your profile along. Or use `python3 workflows/profile.py export my-style.zip` and `import`.

## 3. Set up the tools

Install once, then check what is ready.

1. Run bash setup.sh --check first. It diagnoses prerequisites without installing or wiring services.

2. For Codex local processing use bash setup.sh --host codex --lane chat-only after reviewing downloads. Other app bridges need host-specific verification.

3. Restart the selected environment only when needed. Complete a short test clip; a prerequisite check is not proof of a complete edit.

> Read my host instructions and run bash setup.sh --check. Explain missing prerequisites and downloads. For Codex use the documented local setup with --host codex --lane chat-only; verify app bridges separately. Do not configure Claude servers for Codex.

Success: The report has no outstanding required prerequisites. You know which editing route was selected; confirm it in step 4.

If stuck: A download can take time. Ask whether it is progressing or has reported an error before deleting caches or repeating installations.

## 4. Choose your editing route

Match the workflow to your application.

1. An editing route means where your video is assembled and exported. Use a supported editing app or the local rendering route called chat-only.

2. Select the route you will actually use below. Automated features vary between applications; read the limitation shown before starting.

3. Ask the editor to confirm its connection and available features. Having the app installed does not prove it is connected.

Success: The editor identifies your route and confirms its connection, or explains what is still needed.

If stuck: If the connection fails, open Help. Do not switch apps midway through a job without reviewing the existing project first.

## 5. Make your first video

Start small: one clip, one goal, one test.

1. Choose a 20–60 second clip you own, with one person speaking clearly. Play it first to check its picture and sound. Vertical phone clips are detected as vertical even when the file reports 3840×2160; the spoken language is detected automatically. An iPhone HDR clip is converted to SDR on import (workflows/normalize-source.py); your untouched original is kept in raw/_source/.

2. Fill in the form below. A file path is the address of the clip on your computer. This form creates an instruction; it does not upload or process footage.

3. Paste the instruction into Claude Code or Codex. Review the transcript and proposed cuts. Ask for a preview before approving the final export.

Success: You have a playable draft, understand the cuts and the message still makes sense. If work pauses, you know its current stage.

If stuck: If the file cannot be found, check its name, extension and location. Windows offers “Copy as path”; on Mac, Option + right-click offers a pathname copy action.

## 6. Review with a clear brief

Give feedback the editor can act on.

1. Watch the entire draft with sound. Check that cuts preserve meaning and that names and numbers are correct.

2. Check the face remains visible, captions are readable and the voice is clear. Use the visual comparison below to practice.

3. Ask for specific changes: timestamp, problem and desired result. Keep approved sections and review the changed portion again.

> At 00:12, keep the entire sentence about [topic]. Correct the caption [wrong text] to [correct text]. Preserve the rest of the approved edit and show me the revised section before exporting.

Success: You have approved meaning, spelling, framing and audio. You can request the final file.

If stuck: “Make it better” gives no clear target. Try “at 00:12, move the caption lower so it does not cover my face”.

## 7. Export and verify

Find the file you are going to share.

1. After approving the draft, request an export. The documented location is projects/<job>/outputs/<job>.final.mp4; the actual name depends on your project.

2. Check the full file with workflows/verify-export.py: duration, dimensions, full decoding and audio where required.

3. Open the final MP4: check its start, middle and end, audio sync and dimensions. Exporting does not automatically post it to social media. To upload, ask "prepare the Reels delivery" (or TikTok, Shorts, YouTube): workflows/deliver.py writes outputs/<job>.reels.mp4 at the platform's loudness without touching the final.

> Export the exact draft I approved. Verify duration, dimensions, audio and full decoding with workflows/verify-export.py. Use finalize.sh with --source, --approved and --apply. Preserve originals and drafts; never overwrite an existing final or run cleanup. Give me the exact path without publishing.

Success: You can find and play the final MP4 outside the editor. Keep the original footage and project too.

If stuck: If it is missing, ask the editor to check the outputs folder and export status. A closed window alone does not prove completion.

## 8. Make it yours

Add your brand after the first successful test.

1. Open brand-kit.md. Fill in your name or brand, audience, tone, colors and words that are often transcribed incorrectly.

2. Use fonts, images, music and logos you have permission to use. If a feature requires an external paid service, decide whether to enable it.

3. Ask the editor to apply the documented brand map and make a short sample. Approve the sample before applying the style to a long project.

> Read brand-kit.md and help me fill in missing fields without inventing brand information. Apply its documented map and create a short sample to review colors, fonts and names. Do not enable paid services without my approval.

Success: The sample uses your colors and vocabulary. You have checked that text is still readable.

If stuck: If a change is missing, ask the editor to compare brand-kit.md with the active preset. A preset is a style recipe.

## 9. Get useful help

Give the included agent enough context.

1. In Claude Code use video-editor-help. In Codex request help mode according to AGENTS.md.

2. Include OS, host, route, stage and redacted error. The assistant consults local documentation.

3. Request diagnosis first, without changes. Codex help mode is an instruction, not an isolated read-only subagent. Ask the main assistant to apply a repair when ready.

> Use documented help mode: video-editor-help in Claude Code, AGENTS.md in Codex. Read the docs. My OS is [OS], route [route], stage [stage]. Expected [result], got [problem]. Redacted error: [message]. State what is confirmed and at most three next steps. Do not modify files.

Success: You receive a documented explanation and a concrete next step. If evidence is missing, the agent asks for it.

If stuck: If the agent is absent, restart Claude Code in the correct folder and check .claude/agents/video-editor-help.md. You can also ask the main editor to read this guide directly.

## 10. Pick up where you left off

Continue from work that actually completed.

1. Reopen the same folder and identify your project. Its RUN.md file records the job’s progress.

2. Ask the editor to check both the record and existing files. It should identify the last completed stage before continuing.

3. Keep backups of the source footage and approved output. For purchase or download issues, use the seller contact on your receipt.

> Read RUN.md for my project [name] and inspect its files. Tell me the last completed stage and what remains. Continue from there without overwriting approved work or changing my original footage.

Success: The editor resumes the right project and preserves approved decisions.

If stuck: If several projects exist, identify yours by its name and footage. Do not let the editor choose one at random.

## Official setup / Instalación oficial

https://code.claude.com/docs/en/quickstart

## Editing-route limits / Límites de las rutas

See SETUP.md and LANES.md. CapCut automation: macOS only. Premiere: macOS / Windows. Resolve: edition-specific bridge; some grading/SFX tasks manual or unvalidated. chat-only: local rendering; long-form grading and automatic SFX mixing not implemented.

## Export location

projects/<job>/outputs/<job>.final.mp4

## Help / Ayuda

### File not found · path

Confirm the kit is extracted and the clip path points to an existing file. Keep paths with spaces fully quoted when entering commands. Ask the editor to check the file before editing.

Reference: Steps 2 and 5 · SETUP.md

### Windows: command not recognized · Bash · FFmpeg

Check Git Bash and request check-setup.sh. Reopen Claude Code after installing tools so it can find them. Resolve the specific requirement the report identifies.

Reference: SETUP.md · Core / Windows

### Windows: cannot write · OneDrive · permissions

Use a complete copy in a local folder you control, outside OneDrive and protected folders. Do not disable system protection to finish this tutorial.

Reference: SETUP.md · Windows

### Transcript came out in another language · translation

The kit detects each clip’s language automatically. If the text is in a language you did not speak, or has many doubtful words, ask to re-run transcription forcing the language: transcribe.sh projects/<job> --force --lang en. Never approve cuts on a wrong transcript.

Reference: Step 5 · SETUP.md · Language

### First transcription is slow · WhisperX

The initial model is roughly 3–5 GB; its environment and GPU components can add more. Ask for download progress, free disk space and the latest message. Timing depends on hardware and connection.

Reference: SETUP.md · First edit

### Premiere does not connect · MCP

Check whether the Premiere installer completed. Restart Premiere and Claude Code as directed in SETUP.md and review the project connection. Ask for bridge diagnostics before reinstalling.

Reference: SETUP.md · Premiere lane

### Resolve · BRIDGE_UNAVAILABLE

Specify Free or Studio. The documented Free route requires opening a project and running Workspace → Scripts → resolve_bridge each time you start Resolve. Follow your edition’s instructions.

Reference: SETUP.md · DaVinci Resolve lane

### Caption covers a face or has a typo

Give the exact time and correct wording. Ask to correct the source transcript where applicable and check the framing in a preview.

Reference: Step 6 · CLAUDE.md / graphics

### Cannot find the MP4 · export

In Claude Code check .claude/agents/video-editor-help.md. In Codex request help mode in AGENTS.md; Claude agents are not automatically registered.

Reference: Step 7 · finalize.sh

### Help agent is missing

The guide opens in a browser. Editing requires local Claude Code or Codex with tools. AI usage and paid applications are separate.

Reference: Step 9 · help/QUICK-START.md

### Can I use a phone? Are credits included?

You can read this guide on a phone. Editing runs on a computer with Claude Code and its tools. Your Claude usage, paid apps and optional services are separate.

Reference: Step 1 · SETUP.md
