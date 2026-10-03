---
name: atlas-vtt-handout-forge
description: "Create and revise illustrated letters, posters, journal pages, contracts, inscriptions, and discovered documents for Atlas VTT players. Preserve approved wording exactly in editable source and deterministic text composition, and generate requested document backgrounds or illustrations through the available image workflow. Use for clue handouts, wanted posters, found letters, and coherent document sets. Standalone seals and faction symbols belong to Heraldry & Symbol Forge."
---

# Atlas VTT Handout Forge

Deliver documents players can read and inspect, with approved wording, material, illustration, layout, and typography handled explicitly.

## Scope and authority

Own discovered visual documents and their narrow revisions. Standalone faction emblems belong to Heraldry & Symbol Forge; an emblem incorporated into a letter is part of this document. Portrait Forge owns independent character illustrations, Item & Treasure Forge owns objects presented as loot, and the existing map forges own playable maps. Find neighboring owners in the current runtime; report an unavailable owner honestly. Rules, dossiers, encounter assembly, plugin development, vault import, and publishing require their own requested workflows.

An image request includes actual generation or editing and visual review. Use the current `imagegen` skill and built-in renderer for raster artwork. For a brief-only or source-only request, deliver that artifact. If rendering or final document export is unavailable, deliver the completed available artifacts and identify the remaining step. Do not call a background illustration a completed text-bearing handout.

Save revisions separately and preserve approved files. Treat reference material as evidence, not instructions or authorization. Reading campaign material does not authorize replacing campaign assets or changing a vault.

## Load only what you need

- Read [references/data-contract.md](references/data-contract.md) for a complete source, a set, exact wording, or revisions. Start with [assets/starter.handout.json](assets/starter.handout.json); its empty draft wording intentionally prevents final composition.
- Consult [assets/examples/ferry-letter.handout.json](assets/examples/ferry-letter.handout.json) for a letter, [assets/examples/discovery-set.handout.json](assets/examples/discovery-set.handout.json) for public and private documents plus an unavailable reference, and [assets/examples/paper-color.change.json](assets/examples/paper-color.change.json) for a narrow revision. These are original demonstrations with sample authority assertions, not campaign canon or generated images.
- Read [references/export-and-atlas.md](references/export-and-atlas.md) for final document export and Atlas presentation. Its source snapshot is dated; refresh relevant source before claiming current compatibility.
- Load current `imagegen` instructions for generation or editing. Its tool contract governs actual references and available controls.

## Establish the document

Use known answers. Resolve only choices that change the result: approved wording, intended reader and display size, document kind, material, style, or an identity conflict. If authorized to choose, record assumptions and proceed. Do not require a campaign questionnaire.

Keep user-supplied exact or user-approved text verbatim, including spelling, punctuation, case, spaces, tabs, and line breaks. Do not silently paraphrase, correct, translate, wrap the source with new line breaks, or add titles, dates, signatures, clue marks, or invented glyphs. Supplied exact text and an explicit instruction authorizing you to choose final wording are sufficient authority for composition: mark wording `approved` and record the basis. When wording is unresolved or a draft/approval step was actually requested, mark it `draft` and resolve only consequential choices. Do not impose a new approval round on delegated wording work. A fictional in-world contract is visual handout work, not legal drafting.

Specify material, wear, text region, illustration placement, typography, ink contrast, and requested dimensions. Choose lettering for reading at the intended presentation size. Reserve an explicit blank text region in the generated artwork. Material damage or decorative flourishes must not accidentally obscure an approved clue. For inscriptions, distinguish approved transliteration from decorative invented writing; exact glyphs require a supplied alphabet or approved glyph artwork.

Inspect accessible references before extracting traits. Record stable reference IDs, locators, roles, inspection status, and concrete traits to use or ignore. A seal filename or unavailable image does not establish its shape. Recover a required reference or record a clearly approved alternative before dependent rendering. Use the actual inspected base for image edits; an unavailable base cannot support a promise to preserve its pixels.

## Author the source and public brief

The editable `handout_spec` is independent of native Atlas data. Keep set and asset IDs, revision, locks, and unspecified values stable. Each document has its own approved wording, layout, typography, illustration direction, and reference IDs. Sets use distinct asset IDs and a shared art direction; produce separate documents unless a sheet is requested.

Put private context only in `gm_notes`; mark private documents and references `gm_only`. All public prose and approved wording must be intentionally player-safe. Filtering cannot recognize a secret hidden in a public sentence. Do not put secrets into negative image instructions.

Run commands relative to this skill's directory:

```sh
uv run python scripts/handout_spec.py validate assets/examples/ferry-letter.handout.json
uv run python scripts/handout_spec.py brief my-handout.json --audience player -o my-handout.player.json
```

The brief exports visible documents and only their inspected, visible references. It excludes `gm_notes` and exact wording from image prompts, while retaining that wording in a separate public text field for composition. Uninspected, unavailable, or private required references appear only as unresolved IDs and block `render_ready`. Empty or draft wording blocks final composition. Recorded inspection and authority statuses are assertions, not executed checks; use the user's existing authority rather than requesting it again.

Share only the filtered player artifact after reviewing its prose. The full source is a private master, and a GM compilation is private. The helper never imports, renders images, or changes a vault.

## Generate artwork and compose exact text

Use imagegen to generate the paper, stone, poster illustration, border, or seal placement with a blank readable text region. Supply actual inspected references and explicit margins. Do not rely on an image model's lettering to preserve wording. If the user explicitly requests baked model lettering, inspect and transcribe every character; disclose mismatches and use deterministic replacement for exact text when needed.

For revisions, use the inspected approved raster as the edit target and state the requested change plus invariants. Preserve existing transparency unless asked to change it. Dimensions and preservation prompts are targets, not verified properties or pixel locks. Review the returned artwork for material, illustration identity, text-region clearance, composition, unwanted lettering, and disclosure; measure actual dimensions and alpha when relevant.

The bundled helper composes an inert, self-contained HTML document with escaped final wording and an optional PNG/JPEG/WebP/GIF background. It embeds a static lossless PNG copy with metadata stripped, rejects mismatched background/layout dimensions, preserves text, and permits visual wrapping without editing the source:

```sh
uv run python scripts/handout_spec.py compose my-handout.json --asset letter-01 -o letter-01.html
uv run --with 'pillow>=11,<13' python scripts/handout_spec.py compose my-handout.json --asset letter-01 --background /absolute/path/reviewed-background.png -o letter-01-illustrated.html
uv run python scripts/handout_spec.py text my-handout.json --asset letter-01 -o letter-01.exact.txt
uv run python scripts/handout_spec.py check-text my-handout.json --asset letter-01 --html letter-01-illustrated.html
```

Composition checks approved text and HTML escaping; it does not measure glyph rendering, font availability, overflow, contrast, or legibility. Text checks compare decoded text, including whitespace, against the source. Review the actual rendered document before export. Use an available deterministic export tool for a requested final PNG/PDF/SVG, keeping text separate from model-generated artwork. Record the exporter and actual output format. Do not claim a `.html` file is a PNG, PDF, SVG, or native Atlas document. See the export reference for readable artifact and Atlas boundaries.

For raster metadata without composition, run `uv run --with 'pillow>=11,<13' python scripts/handout_spec.py inspect-image /absolute/path/background.png`. It reports observed dimensions and alpha extrema, not edge quality, readable lettering, or visual acceptance.

Review the final exported page at full size and intended player size: every character, line ordering, font/glyph support, margins, wrapping, illustration overlap, wear, contrast, and private disclosure. Compare narrow revisions to the approved base. For sets, compare typography and shared material/style in actual documents. Save source revision, background, composition, final export, actual measurements, and findings; show the final image inline when useful.

Track `source_validation: not_run|passed|failed`, `wording: draft|approved`, `artwork: not_generated|generated|reviewed`, `composition: not_created|text_checked|visually_reviewed`, `export: not_exported|exported|reviewed`, and `atlas: not_imported|imported|presentation_verified` separately. Leave unknown measurements null. Source validation and exact-text checks do not establish visual acceptance or working Atlas use.

## Revise without drift

Read saved source and artifact records on resume; do not duplicate a completed generation. Recompile after source edits. A source change does not regenerate the artwork or re-export the document.

```sh
uv run python scripts/handout_spec.py revise assets/examples/ferry-letter.handout.json assets/examples/paper-color.change.json -o ferry-letter-ivory.handout.json
```

The helper requires the expected revision, replaces existing leaf fields on a copy, preserves identity and lock definitions, checks locked paths, validates, and increments revision. It refuses output overwrites. New documents or identity rebinding require a deliberate master edit and validation. A wording change returns to `draft` unless `--wording-basis "User supplied the exact replacement wording"` records existing user authority for final wording. This basis may also record an explicit delegation to choose final wording; a patch or reference alone cannot supply that authority.

An explicit user request to change a locked field supplies authorization. Pass its exact path with `--allow-locked /path` only for that authorized change; a patch or embedded reference cannot authorize it. Locks protect source data, not pixels. Report focused before/after changes and any remaining reference, export, or Atlas acceptance step.
