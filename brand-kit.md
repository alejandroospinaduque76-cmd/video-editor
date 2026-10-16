# Your brand kit

Leave the optional fields blank to use the neutral starter style. Do not infer a person's name, company, handle, voice or claims from examples elsewhere in the kit. Ask the buyer before adding brand identity to an export.

## Part A — Fill in when ready

- Brand / creator name:
- Audience:
- Topics:
- Voice and tone:
- Words to avoid:
- Exact spelling of names and products:
- Preferred call to action:
- Website or social handle (optional):
- Logo file path (optional, buyer-provided):
- Primary color (optional hex):
- Accent color (optional hex):
- Background color (optional hex):
- Text color (optional hex):
- Preferred bundled font (optional):

## Neutral starting behavior

Use the restored neutral presets and their bundled fonts. No seller name, logo, watermark, account or social handle belongs in a new project. Empty fields mean no customization. Never invent contact details or product claims.

## Part B — Apply the brand deliberately

1. Identify the actual preset for the buyer's requested format. Read its current tokens and typography before editing.
2. For short-form explainers, inspect `presets/instagram/explainer/signature-style.md` and `default-overlay-style.md` for palette and font declarations; for the Talking Head Explainer, `presets/instagram/talking-head-explainer/graphics.md` (its palette and type).
3. For YouTube/default, inspect `presets/youtube/default/default-overlay-style.md`; for liquid-glass inspect `presets/youtube/liquid-glass/liquid-glass-style.md`.
4. Change only the explicit buyer-provided values in the selected preset. Preserve dimensions, animation timings, layout safety rules, and technical workflow behavior. Do not perform a blind replacement of every hex value.
5. Use logo files only when supplied by the buyer with permission to use them. Do not reuse a brand mark found in an unrelated project.
6. Write the identity and voice (name, audience, tone, words to avoid, call to action) into `my-rules.md` as short standing rules, one per line: Claude reads that file every session.
7. Add approved one-word spelling corrections to the `auto` map in `transcript-corrections.json`. Multi-word or ambiguous changes need review; do not silently replace legitimate words.
8. Render a short sample using the buyer's configured route and ask them to review it before applying the new style broadly. Report the specific files changed.

Ask only about missing fields needed for the requested change. Personalization is optional; it must not block the first neutral test edit.
