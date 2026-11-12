Helium Neo 0.21.2.2 fixes a crash when opening streaming services in WebKit, adds a tab switcher for Ctrl+Tab, saves screenshots right away with an overlay for opening, dragging and editing them, and updates Chromium to 157.0.8103.78.

Download **Helium-Neo-0.21.2.2-macOS-arm64-signed.dmg**, open it, and drag **Helium Neo** to Applications, replacing an existing copy. Requires an Apple Silicon Mac running macOS 13 or later. WebKit streaming tabs require macOS 14 or later. Installations of 0.19.4.1 or later with browser updates enabled receive this release automatically. Users of earlier betas must install it manually once.

**New in Neo**

- **Tab switcher:** holding Ctrl while pressing Tab shows the tabs in the cycle in the middle of the window, like the macOS app switcher. The current tab is highlighted, with the tab Ctrl+Shift+Tab goes to on its left and the one Ctrl+Tab goes to on its right. It appears after a short pause, so a quick Ctrl+Tab just switches tabs, and closes when you release Ctrl. With most-recently-used cycling on, the tabs keep the order they had when you started. Turn it off under **Settings › Behavior**.
- **Screenshots save right away:** after you select an area, the screenshot is saved with its source metadata to your screenshot folder, or Downloads if you haven't chosen one, using your remembered format. An overlay in the bottom-right corner lets you open it, show it in Finder, drag it into another app, or **Edit metadata**. Editing opens the source documentation form, and **Update file** rewrites the saved file, renaming it if you choose another format. Post details suggested by the site are only added after you review them there.
- **Fixes:** choosing **Open … in WebKit** for a streaming service in the address bar or search overlay no longer crashes the browser. Opening or closing tabs while cycling with Ctrl+Tab in most-recently-used order no longer switches to the wrong tab. With that order on, switching tabs with Cmd+Option+arrows now ends its cycle when you release the keys, instead of waiting for Ctrl.

**From upstream Helium**

- Chromium 157.0.8103.78, including its security fixes.
- Groundwork for translating pages through pluggable translation providers. It is off by default and not yet available in settings.
- Sync uses less memory and never syncs the data of sync provider extensions.

The installer is Developer ID signed and Apple notarized. `SHA256SUMS` covers the final stapled installer. Release feeds and `update-manifest.json` accompany the download for update delivery and verification.

Neo is an independent fork of Helium. Report Neo issues to this repository; it is not an official imput release. Split layouts, WebKit streaming, image matching and the search overlay remain experimental.
