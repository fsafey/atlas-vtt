# Exact document export and Atlas presentation

The HTML composition is editable document output with exact escaped text. It is not a raster export and is not accepted by Atlas's image display command. Keep the generated background and approved text as separate source artifacts.

For a requested final image, use an available deterministic HTML/PDF/SVG export workflow. Locate bundled document or rendering dependencies with the desktop workspace dependency tool when useful. Do not install an image provider client. Honor existing browser selection and approval instructions when a workflow requires browser actions. An unavailable exporter leaves a clearly identified HTML composition plus reviewed background, not a completed PNG handout.

At export, verify:

- All approved wording remains present and in order. Check the HTML with the helper before export, then inspect final lettering visually or compare trusted text extraction when the format supports it. OCR alone does not prove exact wording.
- Fonts cover the requested alphabet. Ligatures and visual wrapping can differ from source bytes without changing the wording; missing glyphs, clipped text, or reordered columns are failures.
- The full text fits, including long words, blank lines, trailing signatures, and any illustration reservation. Do not change approved wording or insert new source line breaks to fix fit without authorization; adjust layout or typography.
- Final dimensions, margins, contrast, and text size work at intended player zoom. A high-resolution page can still be unreadable when fitted to a small screen.
- Background images contain no hidden clue or accidental lettering. No private metadata, annotations, or GM notes enter the deliverable.

For a PDF request, provide the actual PDF and record whether text is searchable/embedded. For a raster request, provide the actual PNG/WebP/JPEG and measured dimensions. For SVG, prefer static text paths or supported text plus embedded images; verify the actual renderer and font behavior. Do not rename a file to change its format. The helper decodes a static common raster and embeds a lossless PNG copy with metadata removed; it does not embed active SVG/HTML markup or silently flatten animation. It rejects background dimensions that differ from the layout. Review the actual background and deliberately resolve its layout before composition rather than stretching or cropping it silently.

## Atlas source snapshot

Inspected 2026-10-02 in `fsafey/atlas-vtt` at commit `9b8acc58a40fed29e412f0770c0a13f1f4147dec`. These are source findings, not an Obsidian acceptance run. Refresh the same paths for a later compatibility claim:

- `src/app/services/ImageDisplayService.ts:55` adds image-file menu actions. `:250` reads a vault image and requires an already-open player window; `:289` inserts an `<img>` overlay. `:326` accepts PNG, JPG/JPEG, GIF, BMP, SVG, and WebP. `:410` maps their MIME types. HTML and PDF are absent from that list.
- `src/app/plugin/registerCommands.ts:39` registers `Display image on player view` for the active image file. The corresponding dismiss command is at `:50`; the ribbon checks for an active image at `:64`.
- `src/app/services/imageOverlayControls.ts` supplies player-overlay panning and zooming. Verify readability at the actual zoom and display size, rather than assuming fit-to-window proves it.
- `src/app/services/AssetService.ts:137` defines the asset union with token, map, note, statblock, character, scene, encounter, and player assets; there is no standalone handout asset type.

When the user requests Atlas use, the supported source path is a final image placed in the authorized vault, opened as an image, with the player window open, then displayed through the image command/menu. Vault copying, player display, dismiss/reopen behavior, and readable player presentation are separate steps. Do not create a token/map registration solely to make a handout display, guess `.atlasmap` data, or edit `.atlas-data` indexes. Record actual file, import/copy action, and in-app findings. A file extension on the allowlist does not establish that a particular generated SVG or raster was successfully displayed.
