# Atlas image presentation boundary

Source inspected on 2026-10-02 in `/Users/farieds/Project/atlas-vtt-image-forges` at `9b8acc58a40fed29e412f0770c0a13f1f4147dec`. This is a code snapshot, not an Obsidian acceptance run. Find the active checkout and refresh these paths before giving current compatibility instructions:

| Concern | Source |
| --- | --- |
| Vault image context menus | `src/app/services/ImageDisplayService.ts`, `registerContextMenu`, `addImageDisplayMenuItem`, `isImageFile` |
| Player image overlay | `ImageDisplayService.ts`, `displayImageOnPlayerView`, `createImageDisplay` |
| Image containment | `src/app/services/image-display.scss`, `.atlas-image-display__image` |
| Player-window availability | `src/app/services/PlayerWindowService.ts`, used by the image display service |

At that snapshot, image files have a `Display on player view` context-menu action. The service handles vault image files and resolved image links/embeds. It recognizes PNG, JPG/JPEG, GIF, BMP, SVG, and WebP extensions. `displayImageOnPlayerView` first requires an open player window, reads the vault file as binary, creates a blob URL, and displays an image overlay in that window. The image starts contained at a maximum of 90 percent of the overlay's width and height; the service uses overlay controls for pan/zoom and a close action.

This supports ordinary illustration presentation from a vault image. It does not make the illustration a playable map or prove a native illustration-scene persistence contract. Scene Illustration Forge delivers ordinary image files and authoring sources. It does not export `.atlasmap`, calibrate a grid, create walls/lights/fog, register a guessed scene subtype, or write `.atlas-data` indexes.

For requested use, preserve the reviewed master image, establish the intended vault destination, follow the current vault-image placement workflow, open the player window, and use the current image context menu. Source compatibility, actual vault placement, and successful player presentation are separate outcomes. Claim `presentation_verified` only after seeing the intended player-safe artwork in the player window and observing its needed framing/controls. No map-grid or token-distance checks are required for a reveal overlay.

Reading this reference does not authorize vault writes or browser use. Follow the user's current browser-selection instructions if browser interaction becomes necessary. Authoring and rendering can proceed without opening a vault or player window.
