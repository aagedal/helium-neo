Helium Neo 0.21.3.1 turns split view into a tiling layout you can rearrange, resize and save as templates, adds a menu item that saves images with the page they came from in their metadata, and updates to Helium 0.21.3.

Download **Helium-Neo-0.21.3.1-macOS-arm64-signed.dmg**, open it, and drag **Helium Neo** to Applications, replacing an existing copy. Requires an Apple Silicon Mac running macOS 13 or later. WebKit streaming tabs require macOS 14 or later. Installations of 0.19.4.1 or later with browser updates enabled receive this release automatically. Users of earlier betas must install it manually once.

**New in Neo**

- **Tiling split view:** a split is now a layout of rows and columns, like a tiling window manager, with up to 16 panes. Closing a pane lets its neighbours fill the space instead of closing the split, and Cmd+W closes only the active pane. The active pane gets an accent outline.
- **Adding panes:** Cmd+Option+N adds a pane next to the active one, and Cmd+Option+Shift+N adds one along the right side of the split. Drop tabs and links on the window edges, or onto a split from another window, to add them as panes. **Add to Current Split** in a tab's menu does the same.
- **Rearranging:** hold Cmd+Shift over a pane to show a drag handle. Drop it on another pane's edge to move it there, near the edge of the split to move it along that whole side, or in the middle of a pane to swap them. The handle also works on pages that aren't in a split: drop it on another window to move the tab there.
- **Resizing:** drag a divider to resize the panes beside it, or hold Option to scale every pane on each side. Double-click a divider to make its panes the same size, or choose **Make All Panes the Same Size** in the split menu.
- **Layouts:** the split's layout menu offers Side by Side, One Left Two Right, 2×2 and 3×2 grids, and **Save Current Layout…** keeps your own, up to 12. Picking a layout adds empty tabs for missing panes and never pulls in your other tabs.
- **Moving between panes:** Ctrl+Cmd+arrow keys go to the pane in that direction.
- **Split tab menus:** **Close** closes only the pane you right-clicked, and **Remove from Split** turns it back into a normal tab. In splits of three or more panes, **Mute sites** lists each site shown in the split.
- **Save Image with Context Metadata:** a new item in an image's menu saves it to your downloads folder right away, recording the page you saved it from, the page title, the image's own address and the time in its metadata. Photo apps such as Adobe Bridge show this as the image's Source and Description, which are only filled in when the image has none. The image's own metadata, such as its creator, copyright and caption, is kept as it is, and the image isn't re-compressed. JPEG, PNG and WebP images hold the metadata in the file. Images with Content Credentials keep their signature, and the metadata goes in an XMP file next to them. **Edit metadata** in the download overlay shows the image's own metadata and lets you edit what was added, choose the folder, and save an XMP file for GIF and SVG images.
- **Tab switcher:** you can now point at a tab in the Ctrl+Tab switcher to highlight it, and click it to switch.
- **Frameless mode:** the loading progress bar shows over the page again.
- **Fixes:** right-clicking a tab in a split of three or more panes no longer crashes the browser.

**From upstream Helium**

- Helium 0.21.3.
- A **Copy download link** item in the downloads menu.
- Fingerprinting protection now applies its noise in workers and every other place a page runs code, not only the page itself.

The installer is Developer ID signed and Apple notarized. `SHA256SUMS` covers the final stapled installer. Release feeds and `update-manifest.json` accompany the download for update delivery and verification.

Neo is an independent fork of Helium. Report Neo issues to this repository; it is not an official imput release. Split layouts, WebKit streaming, image matching and the search overlay remain experimental.
