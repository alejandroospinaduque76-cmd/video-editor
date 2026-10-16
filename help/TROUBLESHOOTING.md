# Help index

Use this index with the installed source. Do not apply a fix simply because its title sounds similar; check the actual error and selected editing path.

| Symptom | First check | Documentation / next step |
|---|---|---|
| A shell command is not recognized on Windows | Is Git Bash installed and visible to Claude Code? | `SETUP.md`, Windows setup. Restart after installation. |
| “No such file or directory” while writing on Windows | Is the editor in OneDrive or a protected folder? | `SETUP.md`, Windows location guidance. Move a copy to an appropriate local folder through the user's normal workflow; do not disable system protection. |
| FFmpeg, uv, Node or Pillow is missing | Read the prerequisite report | `check-setup.sh` and `SETUP.md`, Core. Let the main editor run the relevant supported install after normal approval. |
| First transcription takes a long time | Is it downloading a model or creating an environment? Is progress continuing? | `SETUP.md`, first edit. The first edit downloads about 4 GB once (transcription engine and models) and takes about 5 GB of disk. On a fast connection it took about 2–3 minutes; a slow connection takes longer. Do not delete caches or interrupt it while it is progressing. |
| A long red message mentioning `torchcodec` or `libavutil` appears | Did transcription finish and write `words.json`? | It is a dependency warning and does not affect the result. If transcription finished, ignore it. |
| The transcript came out in another language | Does the clip mix languages or is it very short? | Language is detected per clip. To force it, ask the editor to re-transcribe with `--force --lang es` (or your language code). Never cut on a transcript in a language you did not speak. |
| Setup requests a restart | New tools or editor connections may not be loaded | `CLAUDE.md`, First run. Reopen the same project and say “continue setup”. |
| Premiere tools are absent | Was the relevant local connection installed and approved? | `SETUP.md` and `lanes/premiere/`. Do not install a similarly named unofficial package. |
| Resolve reports BRIDGE_UNAVAILABLE | Which Resolve edition and is its bridge running? | `CLAUDE.md`, First run; `LANES.md`, Resolve. Free-edition setup documents starting the bridge from within the app. |
| Captions contain a wrong name ("Clot", "Cloud" instead of Claude) | Confirm the correct spelling against the speech | Add the correction to `projects/<job>/corrections.local.json` (for example `{"auto": {"Clot": "Claude"}}`) or to `transcript-corrections.json` for all your jobs. It is fixed once and reaches captions and graphics. See also `brand-kit.md`, wordlist. |
| Colours of an iPhone clip look washed out, grey or oversaturated | Was it recorded with "HDR Video" on? (on by default) | Since v1.2 the editor converts HDR to SDR when it imports the clip (`workflows/normalize-source.py`). If it warns that a conversion filter is missing, or you are on an earlier version: on the iPhone, Settings → Camera → Record Video → turn off "HDR Video" and record again. |
| The video sounds quieter than others on Reels or TikTok | Did you upload the final or a platform delivery? | Ask "prepare the Reels delivery" (or TikTok, Shorts, YouTube). `workflows/deliver.py` writes `outputs/<job>.reels.mp4` at about −14 LUFS without touching the final. |
| The graphics engine suggests upgrading ("npx hyperframes@latest upgrade") | — | Do not upgrade. The kit is tested with version 0.8.16 and the styles depend on it. |
| Graphic covers a face | Check the documented framing/graphics review step | `CLAUDE.md`, graphics; relevant preset and graphics skill. Ask the main editor to correct the measured layout. |
| Audio effects disappeared after timeline rebuild | Was the app timeline recreated? | `CLAUDE.md`, audio polish and relevant `LANES.md` section. Reapply the documented audio stage through the main editor. |
| A job was interrupted | Find its existing RUN.md | `CLAUDE.md`, pipeline. Resume from the last evidenced stage. |
| The export cannot be found | Check the path the editor reported | The final file is `projects/<job>/outputs/<job>.final.mp4`. `finalize.sh` does not copy it to Downloads (only clips built with the clipper's `make-clips.py --build` get a copy in `~/Downloads/`). |
| "A final already exists" when exporting (`Ya existe un final`) | Did you already export this job? | It is a safeguard: the kit never overwrites a final. Ask for a new version of the job. |
| Help agent is missing | Is the whole package open, including hidden .claude/agents? | `help/QUICK-START.md`, step 9. Restart in the correct folder; inspect agent registration. |
| A feature needs a paid API | Is it optional and which service is it? | Read the specific feature's docs. Do not imply credits are bundled. Buyer decides whether to enable it. |
| The kit does not recognise me (treats me as new or uses someone else's profile) | Which profile is active? Ask for `python3 workflows/profile.py status` and `list` | If your profile is listed: `python3 workflows/profile.py use <your-profile>`. Coming from an older kit version? Type empezar and say where the old folder is (or `profile.py import my-style.zip`). |
| I want to start my style over | Fix one thing, or start from scratch? | To fix one thing, say it in one sentence ("bigger captions"). To start over, say "new profile": it creates a new one and keeps the old one (switch back with "use profile <name>"). |

## Support summary template

- Package version:
- Operating system:
- Claude Code version:
- Editing app and version, or chat-only:
- Project stage:
- Expected result:
- Actual result:
- Exact short error, with secrets and personal information removed:
- Steps already attempted:

Never include credentials, private footage or customer records by default. The help agent must not invent a diagnosis or claim a repair without evidence.
