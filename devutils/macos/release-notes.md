Helium Neo 0.22.1.1 updates to Helium 0.22.1 and Chromium 158.

Download **Helium-Neo-0.22.1.1-macOS-arm64-signed.dmg**, open it, and drag **Helium Neo** to Applications, replacing an existing copy. Requires an Apple Silicon Mac running macOS 13 or later. WebKit streaming tabs require macOS 14 or later. Installations of 0.19.4.1 or later with browser updates enabled receive this release automatically. Users of earlier betas must install it manually once.

**New in Neo**

- All Neo features carried over to Chromium 158, including tiling split view, WebKit streaming tabs, the command bar, page archiving, screenshots and Save Image with Context Metadata.

**From upstream Helium**

- Chromium 158.0.8127.36 and Helium 0.22.1.
- **Interface density:** a new setting on the Accessibility page. **Spacious** makes the location bar, tabs, toolbar buttons and vertical tabs larger, with more room between them.
- Simpler side panel position settings.
- Certificate trust data, such as the Certificate Transparency log list and the root store, now updates between releases. Certificate errors caused by a captive portal or by security software that intercepts connections show a specific explanation instead of a generic warning.
- Chromium 158's history sync prompt and reading mode chip in the address bar are turned off.
- uBlock Origin 1.76.4.

The installer is Developer ID signed and Apple notarized. `SHA256SUMS` covers the final stapled installer. Release feeds and `update-manifest.json` accompany the download for update delivery and verification.

Neo is an independent fork of Helium. Report Neo issues to this repository; it is not an official imput release. Split layouts, WebKit streaming, image matching and the search overlay remain experimental.
