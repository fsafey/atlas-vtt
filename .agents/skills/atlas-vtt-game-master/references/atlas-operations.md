# Native Atlas operations during play

Use for an immediate Atlas action, not a feature-tour checklist. These notes reflect observed local behavior on 2026-10-03; refresh observations if the installation changes.

## Acquire the intended surface

Use the available native computer-use tool, currently `mcp__cua_repl.js`. Follow its first-invocation and post-compaction/reset documentation rules. Do not substitute shell, AppleScript, UI scripting, or data-file edits for native interaction. A skill does not itself supply tools or permissions.

Inspect Obsidian's current window titles and select the campaign vault. Obtain fresh accessibility state and a screenshot for visual/spatial work. Observe after actions and derive new element indices; do not reuse stale targets. Keep one native UI operator.

## Useful observed routes

| Task | Native route | Limit |
| --- | --- | --- |
| Reopen scene | Atlas dashboard > Continue your adventure, or Asset Manager identified scene | Preserve existing scene rather than recreating it. |
| GM notes/cards | Tab with canvas focus opens DM Dashboard | Focus matters; Locate actor also closes dashboard. |
| Actor context | DM Dashboard > Locate named actor, then right-click at that actor | AX canvas-container right-click worked at its center when XY failed. Confirm actor identity after layout changes or overlaps. |
| Resources | Placed actor's DM card | Do not infer changes to other actors or note defaults. |
| Party Delay | Scene counter labeled Delay | Party-wide cost; verify the counter and checkpoint the confirmed value. |
| Hide/show/edit | Identified actor's context menu | Check intended actor; verify player visibility when material. |
| Fit map | Shift+1 with canvas focus | Camera change is not travel or token movement. |
| Player map | Atlas palette > Send Current Map to Player View | An old held frame does not prove a live connection. |
| Handout | Open exact image > Display image on player view | Dismiss overlay when returning to map; no GM notes on player display. |
| Dice | Roll Dice / DiceLog | Report only observed rolls; preserve actual-play history. |
| Snapshot | Scene Snapshots in Atlas palette | Record actual name/ID; create, restore and reopen are different evidence. |

Use current controls if shortcuts differ. Entering a palette query then Return was more reliable than clicking filtered commands. Editable fields accepted `setValue`; paste could append. These are local workarounds, not universal behavior.

## Identify actors before mutating

Canvas objects may not have their own AX nodes. Locate centers the actor but a changed sidebar/layout can shift the click point; overlapping actors can target the wrong one. Inspect the visible actor and context/Edit Token identity before a name, resource, visibility, size, or position change. If identity is ambiguous, refresh and locate again, rather than treating the menu's existence as identity proof.

Native success needs observed evidence. When necessary, read saved scene data to corroborate the affected actor; that is read-only evidence, not a license to edit Atlas JSON.

## Recover without replaying play

AX controls and fresh screenshots worked on a dedicated display; coordinate input still failed with `windowNotFoundAtPosition`. Do not infer freehand dragging or measurement from a working menu. Locate changes camera, not position.

After failure, refresh and try one relevant supported alternative. If it also fails, state the blocked operation and impact, save the pending/unapplied change, continue unaffected fiction, and request only the needed environment fix. Inspect dice history/resources before retrying an action whose outcome may already exist; do not roll or spend twice.

Movement needs native placement evidence. If blocked, record the real fictional location and map discrepancy in Session State, without claiming the token moved or editing coordinates on disk.

Scene snapshots omit diceLog and other state and do not restore notes, collection settings, or the entire session. Older restores can erase cards/resources/party visibility. Recover the intended point and reconcile against actual story events.

Audio/lighting were build-disabled, Loot lacked a Base, and folder rename durability failed. Defer these until needed; do not enable flags, invent loot, or audit unrelated features during play. Plugin development is a separate authorized task.

Filesystem tools may read saved Atlas data and write ordinary campaign Markdown/checkpoints. Never mutate `.atlasmap`, `.atlas-data`, or plugin configuration to manufacture a native result.
