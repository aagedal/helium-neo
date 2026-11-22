Helium Neo 0.22.2.1 updates to Helium 0.22.2, which brings persistent pinned tabs.

Download **Helium-Neo-0.22.2.1-macOS-arm64-signed.dmg**, open it, and drag **Helium Neo** to Applications, replacing an existing copy. Requires an Apple Silicon Mac running macOS 13 or later. WebKit streaming tabs require macOS 14 or later. Installations of 0.19.4.1 or later with browser updates enabled receive this release automatically. Users of earlier betas must install it manually once.

**New in Neo**

- Pinned splits work with upstream's persistent pins. A pinned split keeps all of its panes (up to 16) and its layout, and each pinned pane keeps its settings, such as mobile preview, auto-refresh and page monitoring. Changes to a pinned pane's settings carry over to its copies in other windows.
- Pinned splits from earlier Neo versions are kept when your pins move to the new shared set.

**From upstream Helium**

- Helium 0.22.2, still on Chromium 158.0.8127.36.
- **Persistent pinned tabs:** pins are shared by all windows of a profile and kept across restarts. Closing a pin puts it to sleep instead of removing it, and it returns to the address it was pinned at when you open it again. Links and searches to other sites open from a pin in a new tab. The tab menu adds **Return to pinned URL** and **Use current URL as pinned URL**. Pins from earlier versions are merged into one shared set on first launch.
- Redesigned pinned tabs in vertical tabs, with outlined pins in balanced rows.
- In Zen mode, the floating sidebar shows tabs at full width instead of staying collapsed.
- Canvas fingerprinting protection gives partial canvas reads the same noise as full reads.
- The page zoom indicator stays visible with long addresses.
- Left clicks are no longer ignored when the flag that disables link dragging is on.

The installer is Developer ID signed and Apple notarized. `SHA256SUMS` covers the final stapled installer. Release feeds and `update-manifest.json` accompany the download for update delivery and verification.

Neo is an independent fork of Helium. Report Neo issues to this repository; it is not an official imput release. Split layouts, WebKit streaming, image matching and the search overlay remain experimental.
