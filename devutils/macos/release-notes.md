Helium Neo 0.21.1.1 adds a search overlay for new tabs and the address bar, one-step page archiving, suggested post text for screenshot sources and a new icon, and updates Chromium to 157.0.8103.38 and upstream Helium to 0.21.1.

Download **Helium-Neo-0.21.1.1-macOS-arm64-signed.dmg**, open it, and drag **Helium Neo** to Applications, replacing an existing copy. Requires an Apple Silicon Mac running macOS 13 or later. WebKit streaming tabs require macOS 14 or later. Installations of 0.19.4.1 or later with browser updates enabled receive this release automatically. Users of earlier betas must install it manually once.

**New in Neo**

- **Search overlay:** an optional Arc-style overlay for Command-T and Command-L shows autocomplete results together with open tabs. Type `>` for browser commands or `!` for bangs. A button shows a QR code for the current page. Turn it on under Settings › Appearance; it is off by default.
- **Archive page:** Command-Option-S, **File › Archive Page** or **Save and share › Archive page** saves the current tab to an archive folder in one step, as `.mhtml` or optionally as PDF. Content that loads on scroll is loaded first. Choose the folder under Settings › Downloads; the default is `~/Documents/Helium_Archive`.
- **Screenshot sources:** the screenshot tool suggests post text from the selected post on X, Bluesky, Mastodon, Reddit, YouTube and other platforms, and falls back to the page's own metadata for permalink, author and date. The description starts with a readable summary and recognises more platforms.
- **New icon:** a helium atom with its emission spectrum replaces the orbital mark.

**From upstream Helium 0.21.1**

- Chromium 157.0.8103.38.
- uBlock Origin 1.75.4.
- Sparkle 2.10.1.

The installer is Developer ID signed and Apple notarized. `SHA256SUMS` covers the final stapled installer. Release feeds and `update-manifest.json` accompany the download for update delivery and verification.

Neo is an independent fork of Helium. Report Neo issues to this repository; it is not an official imput release. Split layouts, WebKit streaming, image matching and the search overlay remain experimental.
