# Worldbuilding and map scales

Use the current campaign's conventions and location notes. Give the immediate situation enough detail for a meaningful choice; develop more as the player investigates. Preserve established geography, character identity, clues, terms and history.

## Establish a place

Read its existing note and relevant parent location. Reuse known landmarks, architecture, inhabitants and connections. Add compatible observable detail, useful routes, people with motives, and consequences that fit what the player does. Distinguish a confirmed fact, an NPC claim, a tentative design, and an event that actually happened. Clarify an outcome-changing contradiction before resolving the action.

Keep a location note small: parent place, public description, important people/features, established connections, and actual map/illustration locators with their readiness. Record durable additions there; record actual choices, time, costs, discoveries and pending actions in Session State. Keep unrevealed motives and future possibilities in private GM notes. A public location hub must not link to GM-only notes or expose secrets in previews.

## Choose the scale that helps the decision

| Surface | Question it answers | Representation |
| --- | --- | --- |
| Regional map | Where are we travelling? | Party/subgroup location and distances in the region. |
| City or settlement map | Which streets and places can we visit? | Districts, routes and destinations. |
| Building/interior map | Where are entrances, people and obstacles? | Local positions at a separately chosen scale. |
| Description or scene illustration | What is this place like? | Atmosphere and visible information; no measured movement implied. |

More detailed maps are separately authored assets. Zooming a regional raster enlarges its existing artwork; it does not reveal streets or rooms. Use a description for conversation; introduce a city map when route choices matter, or an interior map when entrances, cover, searches or precise positions change decisions. Do not generate every level before playing.

Regional token portraits are identifying markers. Several people can occupy one hex; token size, snapping and overlap do not set occupancy rules or establish room-scale separation. Retain linked individual hero cards and live resources even if one marker represents their group. When a party genuinely splits, record subgroup membership and real destinations before using separate markers. A regrouping or display adjustment does not spend time/resources by itself.

Preserve the campaign's designated resource-owner scene/tokens when opening a child scene. Copied cards/defaults and new scene counters are not automatically synchronized. Apply costs once at the designated owner; keep presentation copies from implying a fresh resource pool. Any explicit ownership transfer needs confirmed values, a verified new owner and a recorded handoff that retires the old owner.

## Route a needed asset

Reuse an appropriate existing asset first. When creating an asset is within the current request, load its owning skill from the active Atlas repository's `.agents/skills/<name>/SKILL.md`; these paths locate instructions, not newly granted tools or permissions.

| Need | Owner |
| --- | --- |
| Region, city or playable interior | `atlas-vtt-map-forge` |
| Atmospheric place or moment | `atlas-vtt-scene-illustration-forge` |
| Character appearance / tabletop marker | `atlas-vtt-portrait-forge` / `atlas-vtt-token-forge` |
| Document or discoverable writing | `atlas-vtt-handout-forge` |
| Map object / emblem | `atlas-vtt-props-terrain-forge` / `atlas-vtt-heraldry-symbol-forge` |

Carry forward the location's identity, parent geography, known entrances/routes, approved appearance and player-safe information. Map Forge creates an editable spec and setup plan; pass its player-safe brief to the available image workflow for requested rendering. Image forges own their rendering/review steps. Reuse approved portraits for recurring characters. Do not silently replace an approved map or broaden an illustration into a playable map.

A skill does not supply a renderer or native tool. If an owner/tool is unavailable, report that dependency and continue play through description when spatial accuracy is not required. Keep a needed exact layout pending rather than inventing measured geometry.

## Connect and present

Keep each native scene's scale explicit and calibrated against its own asset. Use public location notes as hubs linking existing parent/child scenes and illustrations; mark missing assets as not created, without fabricated links. Opening a closer scene is presentation, not automatic fictional travel or elapsed time. Explain what its grid and markers mean before relying on positions.

The source-backed hex-link route is Note Pin tool > Shift-click a hex > choose its public location note. A hex holds one linked note, so use that note as a hub for multiple buildings/scenes; this link limit is unrelated to character occupancy. Scene links must respect Atlas collection boundaries. This route still needs native verification in the current installation.

For authorized Atlas setup, follow native operations: import the reviewed player-safe asset, create/calibrate the scene, link notes through native controls and check the player view. Source supports note/hex links; check current routes and collection constraints before using scene links. Writing a location note does not install a map link. A drafted spec, rendered image, imported scene and verified player presentation are separate stages. Do not write guessed native JSON or claim seamless zoom navigation without evidence.
