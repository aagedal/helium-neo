Helium Neo 0.22.4.1 updates to Helium 0.22.4 (including 0.22.3) and Chromium 158.0.8127.88.

Download **Helium-Neo-0.22.4.1-macOS-arm64-signed.dmg**, open it, and drag **Helium Neo** to Applications, replacing an existing copy. Requires an Apple Silicon Mac running macOS 13 or later. WebKit streaming tabs require macOS 14 or later. Installations of 0.19.4.1 or later with browser updates enabled receive this release automatically. Users of earlier betas must install it manually once.

**New in Neo**

- Turning **Keep pinned tabs across windows and sessions** off and back on preserves Neo's per-pane settings (mobile preview, auto-refresh, page monitoring) alongside pinned splits.
- Updated Neo's mirror speed-probing and fallback updater integration for upstream's refactored macOS Sparkle updater.
- Reserved Neo's internal command IDs in their own range so upstream's new **Update Helium** approval menu item does not conflict with Neo actions.

**From upstream Helium**

- Helium 0.22.3 and 0.22.4, updated to Chromium 158.0.8127.88.
- **Per-window pinned tabs option:** added a **Keep pinned tabs across windows and sessions** toggle in Appearance & Behavior so each window can keep its own pins when disabled.
- **Drag to pin/unpin:** in the vertical tab strip, dragging tabs into or out of the pinned area pins or unpins them, and canceling a drag restores their original state.
- **Pinned tab fixes:** unpinning or removing a pin keeps loaded copies open as regular tabs in other windows instead of closing them, and dragging a pin out and dropping it back among regular tabs unpins it cleanly.
- Updated bundled uBlock Origin to 1.77.0.
- Added an experimental **HTTP cache encryption** flag in `chrome://flags`.
- macOS updater improvements, including an app menu approval item when an update cannot be installed silently.

The installer is Developer ID signed and Apple notarized. `SHA256SUMS` covers the final stapled installer. Release feeds and `update-manifest.json` accompany the download for update delivery and verification.

Neo is an independent fork of Helium. Report Neo issues to this repository; it is not an official imput release. Split layouts, WebKit streaming, image matching and the search overlay remain experimental.
