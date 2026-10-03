# Atlas VTT image forge delivery

Authored on 2026-10-02 by six dedicated GPT-6.1-Sol workers using `xhigh` reasoning, with a lead coordinator responsible for integration and validation. The runtime permitted three concurrent workers alongside the lead, so authoring used two parallel waves. The existing Portrait and Map Forge packages were preserved.

These repository-local skills cover the six previously pending asset families:

| Forge | Package | Behavioral tests |
| --- | --- | --- |
| Token | [atlas-vtt-token-forge](../.agents/skills/atlas-vtt-token-forge/SKILL.md) | 26 |
| Scene Illustration | [atlas-vtt-scene-illustration-forge](../.agents/skills/atlas-vtt-scene-illustration-forge/SKILL.md) | 22 |
| Props & Terrain | [atlas-vtt-props-terrain-forge](../.agents/skills/atlas-vtt-props-terrain-forge/SKILL.md) | 19 |
| Item & Treasure | [atlas-vtt-item-treasure-forge](../.agents/skills/atlas-vtt-item-treasure-forge/SKILL.md) | 21 |
| Heraldry & Symbol | [atlas-vtt-heraldry-symbol-forge](../.agents/skills/atlas-vtt-heraldry-symbol-forge/SKILL.md) | 21 |
| Handout | [atlas-vtt-handout-forge](../.agents/skills/atlas-vtt-handout-forge/SKILL.md) | 28 |

Each package includes a concise entrypoint, normally discoverable UI metadata, an editable starter, representative examples, focused references, a deterministic authoring helper, and behavioral tests. Schemas are included where useful; Handout uses direct source validation and exact-text composition. Invoke `$atlas-vtt-<family>-forge` from an Atlas checkout or worktree. No global copies or plugin installation are required.

The skills support sparse ideas, inspected references, individual assets, coherent sets, and narrow revisions. They preserve stable identities and source locks, filter structured private context from player briefs, and separate requested output properties from actual image measurements. Explicit image requests include generation and inspection through the available `imagegen` workflow. Brief-only requests stop at the authored source and brief.

## Verification

The six packages passed 137 behavioral tests in total, focused Ruff checks, helper type checks, Skill Creator validation, metadata checks, and representative CLI exercises. The lead checked 47 local Markdown links and fresh repository discovery. All six new skills were enabled with repository scope in the Atlas worktree and its `src` subfolder, with no forge entry in the parent Project folder or an unrelated repository.

The behavioral checks cover private variants and references, unavailable edit targets, source readiness, duplicate IDs, narrow revisions, stale versions, locks, output preservation, actual alpha measurements on synthetic fixtures, exact text escaping and whitespace, lettering plans, and coherent carrier dependencies. Token exercises the existing Portrait Forge handoff with a clearly identified synthetic fixture.

Lead validation reproduced and repaired two helpers that accepted `/revision` as a lock and then incremented that value. Validation now rejects locks on the automatically managed revision, with focused regressions. Explicit user choices remain supported, including opaque token bases and borders. A requested seal-and-flag set can use one requested carrier as its consistency anchor without requiring an extra emblem. Supplied wording or delegated final-wording authority does not create a new approval gate.

Cross-author forward testing exercised realistic requests, coherent sets, private variants, unavailable references, exact wording, and narrow revisions across all six forges. The first pass completed 35 workflow calls and 23 consumer assertions. The second completed 38 calls and 26 consumer checks, finding one Heraldry defect: an incomplete flag was blocked in JSON but could still export a plain prompt. The lead repaired that path to reject unresolved text export before creating a file and added a focused regression. An independent rerun confirmed the unresolved flag fails without an output file, the ready seal still exports the same prompt, and the source remains unchanged. No observed defect remains in the exercised workflows. Original failure evidence remains in the bundle alongside the repair verdict.

Package instructions contain their local verification commands. Typical checks from a package directory are:

```sh
uv run --with 'jsonschema>=4.23,<5' --with 'pillow>=11,<13' python -B -m unittest discover -s tests -v
uv run --with 'ruff>=0.15,<1' ruff check scripts tests
uv run --with 'pyyaml>=6,<7' python /Users/farieds/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Handout's helper itself uses the standard library except optional raster checks. Type checking was scoped to the helpers, with their actual dependencies available. An initial lead overlay using legacy Pillow stubs produced annotation errors; the final checks use current Pillow typing and pass.

## Evidence and acceptance boundary

The local evidence bundle is `/Users/farieds/Project/atlas-image-forges-validation/2026-10-02/`. It retains author logs and examples, lead repair evidence, final package hashes, discovery results, and forward-test artifacts. The working tracker is `/Users/farieds/Project/atlas-vtt-image-forges.md`.

Atlas source compatibility findings were inspected at `9b8acc58a40fed29e412f0770c0a13f1f4147dec`. Token artwork has framing and proportional unframed display. Props have no dedicated native asset type, so their placement hints remain authoring data. Scene, Item, Heraldry, and exported Handout images have a source-supported player-window image overlay; this authoring work does not perform that workflow. Handout HTML composition is an exact-text artifact, not a final PNG/PDF/SVG or an Atlas-importable image.

No campaign image generation, real image visual review, final Handout image export, vault import, plugin deployment, or in-app Atlas acceptance was performed. Synthetic image fixtures and deterministic HTML text checks prove only their stated invariants. Source filtering cannot detect a secret embedded in ordinary public prose, and source locks do not lock rendered pixels.

Repository CI remains the plugin build gate and was not replayed locally for this skills-only change. Required checks and any remote results are recorded against the exact integration commit in the external validation record and pull request.
