# Atlas VTT classification

Status: initial classification. Evaluation and translation to agent workflows have not begun.

## Method

For each feature, record: name, purpose, inputs, stored objects, user actions, resulting state, visibility, and evidence in the repository. Distinguish documented claims from behavior verified in code or use.

## Initial top-level label

Atlas VTT is a desktop, game-system-agnostic virtual tabletop implemented as an Obsidian plugin. It works with local files in an Obsidian vault. Scenes are saved as `.atlasmap` files.

Source: [Atlas VTT README](https://github.com/ByteMirror/atlas-vtt/blob/main/README.md).

## Documented functional areas

| Area | Documented capability | Verification status |
| --- | --- | --- |
| Scenes and maps | Build scenes from map images; align square or hex grids | README only |
| Tokens and encounters | Import and place characters; save reusable encounters | README only |
| Session controls | Fog of war, dice, initiative, counters, timers | README only |
| Notes | Pin Markdown notes or other Atlas maps to map locations | README only |
| Player visibility | Separate player window with GM information hidden | README only |
| Organization | Collections, folders, and tags for scenes, maps, encounters, characters | README only |

## Next classification work

Inspect repository implementation and documentation to identify the actual object model, persistence format, interaction flows, and visibility rules. Add evidence for each label before evaluating the design.
