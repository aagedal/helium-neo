Helium Neo 0.21.2.1 adds a download overlay, makes WebKit streaming opt-in and adds more services to it, and updates Chromium to 157.0.8103.50 and upstream Helium to 0.21.2.

Download **Helium-Neo-0.21.2.1-macOS-arm64-signed.dmg**, open it, and drag **Helium Neo** to Applications, replacing an existing copy. Requires an Apple Silicon Mac running macOS 13 or later. WebKit streaming tabs require macOS 14 or later. Installations of 0.19.4.1 or later with browser updates enabled receive this release automatically. Users of earlier betas must install it manually once.

**New in Neo**

- **Download overlay:** finished downloads appear as a card in the bottom-right corner of the window, with buttons to open the file, show it in Finder, or drag it into another app. It closes after six seconds unless the pointer is over it. The toolbar download button still opens the full list, and downloads with warnings still use the regular popup. Frameless mode stays hidden.
- **WebKit streaming is opt-in:** streaming services no longer open in WebKit automatically. Typing one into the address bar or search overlay offers to open it in WebKit, and afterwards you can choose to always open that service there. Prime Video, Apple TV+, Viaplay, SkyShowtime, discovery+, Telia Play, NRK TV, Hulu, Paramount+, Peacock and Spotify join the list; Spotify keeps playing when its tab is in the background. WebKit tabs show their site icons.
- **Safer WebKit tabs:** links to other sites leave WebKit and continue in Chromium, popups stay blocked, camera and microphone requests are denied, and the address bar shows "Not secure" for pages without full HTTPS. Each profile gets a new WebKit data store, so you need to sign in to streaming services once more.
- **Archive page:** archives are always PDFs, which record the page's title, address and archive time in their document properties and in Finder's "Where from". Bars fixed to the top of the page print once instead of on every page, and cookie notices are left out. Archives now appear in the download list, so the download button opens them.
- **Screenshots:** in frameless mode, the screenshot panel opens over the page instead of revealing the toolbar. Post details are suggested only when the screenshot is taken on the platform's own site, so other pages can't attribute text to a post.
- **Faster updates:** the updater downloads from whichever of GitHub and the aagedal.me mirror is clearly faster, and gives up on a stalled download after 30 seconds.
- **Removed:** finding an image in other tabs, which scrolled through every tab in the window. Image search on the current page remains.

**From upstream Helium 0.21.2**

- Chromium 157.0.8103.50, including its security fixes.
- Settings › Search has address bar options to leave browsing history or bookmarks out of suggestions.

The installer is Developer ID signed and Apple notarized. `SHA256SUMS` covers the final stapled installer. Release feeds and `update-manifest.json` accompany the download for update delivery and verification.

Neo is an independent fork of Helium. Report Neo issues to this repository; it is not an official imput release. Split layouts, WebKit streaming, image matching and the search overlay remain experimental.
