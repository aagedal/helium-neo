# Developer utilities for ungoogled-chromium

This is a collection of scripts written for developing on ungoogled-chromium. See the descriptions at the top of each script for more information.

## Page change monitoring

`helium/ui/page-change-monitor.patch` extends `PaneSettings` with explicit refresh
presets, optional uniform ±5% jitter, a shared FIFO reload queue and error backoff.
The queue allows two active automatic reloads, spaces starts by 250 ms, and
sleeps while both slots are occupied. Requests are cancelled when settings change
or tabs close, and newly due tabs cannot jump ahead of tabs already waiting.
Legacy 15-second-multiple intervals through 180 seconds remain accepted when
restoring old sessions, but are not offered as new menu choices. Monitoring is an
opt-in `WebContentsObserver`; its isolated-world text read runs once after loading
settles, without a MutationObserver, interval scan, hidden-tab wakeup, or pixel diff.
The scan stops at 4,000 nodes, 65,536 UTF-16 text units or 12 ms, with a two-second
browser-side reply timeout. These are best-effort work limits, not a hard bound on
one expensive browser DOM/style operation. Empty, missing and incomplete results
never replace a valid baseline. The line diff runs only when reviewing changes.

**Monitor a section of the page…** opens an overlay in the page, in the same
isolated world and inside a closed shadow root with constructed stylesheets, so
page CSP and Trusted Types do not block it. A click picks the block under the
pointer; a drag picks the blocks the rectangle touches, or their shared block if
it covers all of them. The choice is checked with the production scan before it
is accepted, and stored as a comma-separated list of ID or positional selectors.
If any listed block is missing on a later check, the check fails closed. The
browser polls the overlay every 250 ms because isolated-world execution cannot
wait for a promise; polling stops on choice, Escape, navigation or after three
minutes, and automatic refresh is held while the overlay is open.

**Review page changes…** shows the page title and address, the watched scope,
local check and change times, then each detected change, newest first, under
its own local timestamp. Changes appear as tinted removed and added lines with
two lines of context, and longer unchanged runs are summarized. The text being
watched now follows (the first 40 lines), so a new selection can be verified
before anything changes. **Show on page** activates the tab, scrolls to the
watched blocks and outlines them for three seconds without taking pointer input.
The last 20 detections are kept in memory only, each limited to 80 rows of up
to 1,000 bytes; the export record still holds both full text versions. The
whole-line LCS table is limited to one million cells; larger edits fall back
to showing the changed block as removed and added.

Run `python3 devutils/test_tab_preview.py` for sanitizer-backed viewport, interval
and jitter checks. Run `python3 devutils/test_page_change_diff.py` for line diff,
context, gap, fallback and UTF-8 checks. Run
`python3 devutils/test_page_change_picker.py --chromedriver <chromedriver> --binary <browser>`
to drive the shipped picker with real pointer and keyboard input on a page with a
strict CSP. Native `PaneSettingsTest.*`
covers timer deadlines, blocking, restoration and tab lifecycle; it requires an unpruned Chromium test build.
Run `python3 devutils/page_change_monitor_server.py`, open
`http://127.0.0.1:8240/`, and choose **Run production-script checks** for DOM fixtures.
The server extracts the exact production script from the fork patch. The same page
has a statement-change button for native change indicator, review and export QA.

Automatic PNG exports reuse the existing screenshot metadata encoder. PNG and PDF
exports include JSON sidecars with both text versions, capture limitations and a
SHA-256 digest of the finished file. Filenames use frozen source details and a UUID.
Files are written atomically on background workers. A single monitored tab may
export at a time; there is no unbounded export queue. Each tab's exports time out
after 30 seconds, disabling its export opt-ins and releasing refresh blocking.
Hidden tabs cannot export compositor screenshots, because their surface may be
stale. Printing and screenshot policy preferences are honored. Exports remain
opt-in each session; text baselines and differences are never session-serialized.

Validation on the persistent Apple Silicon development build: all 17 production
DOM fixtures passed, along with 132 viewport cases, 7,501 interval checks, 1,414
jitter samples and 209 changed-line excerpt cases under sanitizers. The final app
rebuilt and was restarted through the persistent launcher. Native QA verified
the full interval menu, five-second reloads with optional jitter, unchanged pages
not creating duplicate exports, change review with complete changed sentences,
automatic PNG and one-page PDF exports, matching JSON SHA-256 digests, and PNG
Creator Tool metadata. A second capture preserved the observed URL fragment in
its source record. Native content was controlled local test content, not a live
news site. A 200-paragraph DOM fixture took roughly 0.2 ms median per extraction
(100 checks); this is not a multi-site browser performance benchmark.

The scheduler and tab menu GN header dependency checks passed. The broad `:ui`
check still reports existing dependencies for `autofill_ml_internals_ui.h` and
`async_check_tracker.h`; it reports no new monitoring include errors. Native
`PaneSettingsTest.*` regression cases were added but have not been executed in
the pruned development tree. Broader live-site and multi-tab load testing remains
useful before a release.

## Screenshots with source documentation

Export filenames use the frozen capture timestamp, hostname (without `www.`),
and page title for both Save As suggestions and direct folder saves. The common
`ScreenshotFilenameStem` helper replaces filesystem-unsafe characters, including
Unicode formatting controls, collapses whitespace and bounds the hostname/title
to 48/80 UTF-8 bytes without splitting code points. Missing hosts use `page`;
empty titles are omitted. URL credentials, paths, queries and fragments are not
used as filename components. Direct saves retain their full random UUID suffix
to prevent overwriting previous exports. Archive members retain their fixed
`screenshot.*`, `metadata.json` and `source.txt` names for compatibility.

Filename validation: all 20 native screenshot documentation/export tests passed,
including four filename cases covering source components, unsafe characters,
long Unicode titles and missing details. Both GN header dependency checks,
patch lint, patch-file checks and a no-fuzz reverse/apply round trip of the
changed hunks passed. The capture dialog compiled and the persistent macOS
development app rebuilt successfully. Save As and direct-folder downloads have
not been exercised through the native UI for this change.

`helium/ui/screenshot-source-documentation.patch` extends Chromium's existing
manual region selector and screenshot review dialog. The context-menu command
uses the clicked pane's `WebContents`, including an inactive pane in a split.
It is available on HTTP(S) pages when screenshots are permitted by policy.
The default shortcut is Command-Shift-S on macOS and Ctrl-Shift-S on other
desktop platforms. macOS owns this binding through the File menu and Cocoa
accelerator map so the existing Keyboard shortcuts settings can remap or remove
it; other desktop platforms use the browser accelerator table.
Selection remains available with accessibility clients connected. Enter captures
the visible pane explicitly, and Escape cancels without changing the clipboard.

The renderer surface is copied at its native pixel density. Browser chrome,
the selection overlay and other windows are excluded; macOS desktop capture
permission is not required. Source URL/title, view bounds, selection coordinates
in device-independent pixels, and snapshot request/completion times are frozen
with the capture. A document or URL change before completion discards the
result. Later navigation does not rewrite the source details in the review.

The optional permalink, posting account, publication date text, post text,
accessibility alt text and notes remain separate from automatically observed
fields. Unknown dates are not inferred or
converted to a fabricated exact timestamp. A read-only isolated-world DOM query
runs alongside the snapshot to find post permalinks for Twitter/X, Instagram,
Facebook, Threads and Truth Social. It associates visible links with the crop or an
overlapping post container, converts view DIPs to CSS viewport coordinates, normalizes tracking
URLs, and retains meaningful Facebook comment IDs. No API calls, extra network
fetches or click actions are performed. DOM inspection remains read-only.
Supported social timestamp links without a full date can receive a browser-delivered
mouse hover after the pixel copy completes. The system cursor stays in place.
Scoped profile links and time
attributes provide optional posting-account and publication-date suggestions.
Truth Social's observed `data-testid="status"` feed wrappers and
`.detailed-actualStatus` detail wrappers are supported, including detail-page
footer dates and both `/@account/posts/id` and legacy `/@account/id` links.
Threads supports both `threads.com` and legacy `threads.net` post links,
including pressable post containers without article semantics. Instagram's
account-prefixed post footer supplies the post date; caption/comment timestamps
and comment permalinks are excluded. Facebook timeline wrappers, plain
accessible timestamp links and compound numeric post IDs are supported.
Valid `data-utime` values are recorded as epoch seconds and exact UTC values.
Other site text is retained verbatim, without guessing missing timezones.
Fragment-only controls are excluded from post links.

One unambiguous post link fills the editable permalink field with a review
notice. Multiple candidates, multiple selected posts or an incomplete scan
require choosing a candidate or entering a link. Hidden/occluded content and
profile links are excluded. Candidate collection is capped at eight links and
10,000 anchors / 1,000 post containers; reaching a limit disables autofill.
Initial inspection times out after one second. Optional timestamp tooltip reads
use bounded retries and a shared five-second budget for starting further reads;
an in-flight renderer read also has a short timeout. No hover runs before the
captured pixels are frozen. Timestamp mouse-leave events clean up the hover.
Navigation or view resizing invalidates a pending result. Main-document DOM
inspection cannot read cross-origin embedded posts or inaccessible shadow DOM.
The embedded/ZIP source record stores `automatic.permalink_suggestions`, its
observation time and unverified status; `user_provided.post_permalink_origin`
distinguishes a reviewed suggestion from a manually entered/edited link.
Candidate `site_details` preserves observed profile links/display names, visible
date text, date tooltips, and original `datetime` / `data-utime` attributes.
The machine-readable timestamp is used verbatim when present; relative dates
and unspecified timezones are never parsed into an invented exact time.
`selected_post_details` can preserve account/date observations for one selected
post on a supported site even when its permalink is unavailable. Nested quote
metadata is scoped to its own post. Conflicting observations suppress autofill.
Account/date fields remain editable; changing link candidates replaces only
untouched suggestions. The record stores `posting_account_origin` and
`publication_date_text_origin`, alongside the unchanged site observations.
The browser's screenshot capture time remains separate from publication time.
For X's public portal tooltip, extraction requires exactly one open timestamp
trigger matching the candidate permalink and one visible timestamp tooltip.
Quoted posts, unrelated/closing portals and ambiguous triggers cannot provide
its date. Other platforms validate the original timestamp element, enclosing
href and unchanged displayed text before accepting a full title or explicitly
ARIA-associated date. A fallback requires one newly exposed nearby tooltip on
the hovered timestamp. Hidden, stale, unrelated and ambiguous tooltips are
rejected. Transient DOM selectors/hover targets are removed before export. `publication_date_tooltip`, `date_evidence` and
`tooltip_observed_at_utc` identify a later hover observation; the original
`publication_date_displayed` remains unchanged. Missing tooltips retain the
original relative/date text, with no ID-based or relative-time calculation.
Twitter/X and Threads nested quote posts can return `status: preferred` with multiple
documented candidates. A crop confined to a nested post prefers that post;
otherwise the enclosing post is preferred when it contains the selection or
its own selected header/comment. Separate sibling posts and structurally
unresolved links remain ambiguous. An unlinked enclosing post with selected
own content prevents its quote from being treated as the sole source.
`selection_reason` and candidate `relationship`, `quoted_by` or
`contains_selected_post` fields retain the heuristic decision. Each post's
account/date stays scoped to its own container. The preferred post is first
for bounded hover inspection, and a preselected source chooser allows an
override while preserving manual field edits.
Facebook posts with attached photos can also return `status: preferred`.
Exactly one timestamped post source must enclose every detected photo source;
photo candidates require an actual image link in that post. The enclosing
post stays primary for image-only crops. Photo URLs remain in the chooser and
record with `relationship: attached_media` and `attached_to`; account/date
observations from a shared container belong only to the post. Independent
nested media details remain separate. Sibling posts, comment permalinks,
plain text links to other photos and incomplete scans remain ambiguous.
Cocoa mouse capture accepts descendant content views, uses the release position
for the crop, and consumes scrolling without implicitly committing selection.

Encoding, metadata embedding, SHA-256 calculation and optional ZIP creation run
on a blocking worker. The remembered per-profile choices are PNG, JPEG (quality
95, 4:4:4) or lossless JPEG XL, and standalone image or documentation ZIP.
Standalone image is the default; all formats retain embedded IPTC/XMP metadata.
Direct saving is enabled by default and asks for a screenshot folder on first
save. The review panel shows the remembered folder and provides a folder picker
to change it. Disabling direct saving restores Save As for each capture.
Screenshot-specific folder and direct-save preferences do not change the general
download directory. Each direct save uses a fresh UUID in its filename to avoid
overwrites, including repeated saves of the same capture.
JPEG uses Chromium's existing encoder. JPEG XL statically links the standalone
fast lossless encoder from libjxl 0.12.0, downloaded with a pinned SHA-256 in
`deps.ini`; it does not require a system library, Homebrew or a subprocess.
Fresh builds unpack this dependency through the normal dependency step. For an
existing prepared cache, retrieve/unpack only this new dependency without running
`prepare_sources` or replacing unrelated source/build outputs.

The default-on per-profile preference `helium.screenshot_preserve_hdr` appears as
**Automatically preserve HDR** in capture review. Turning it on for an HDR
selection selects JPEG XL immediately; a subsequent explicit format choice is
honored. The preference persists when toggled, even if review is cancelled.
Every capture requests an F16 master so changing this export setting can apply
to the current frozen snapshot without recapturing a later page state. The
separate N32 sRGB preview/clipboard never replaces the export master.

The opt-in `CopyFromSurfaceWithHDR` API uses a main-renderer-surface copy on
macOS and Aura. GPU readback converts the source render pass into half-float
linear Rec.2020, preserving values beyond reference white. F16 bitmap type,
color space and odd dimensions survive Viz/Mojo transport. Existing capture
APIs keep their behavior. Unsupported platforms/backends may return ordinary
SDR; failed high-precision copies retry the normal copy path with its own
bounded timeout. This captures rendered pixels, not original HDR media, and
cannot undo earlier tone mapping. Native popup surfaces are excluded.

Selected pixels above linear reference white (with half-float rounding tolerance)
trigger HDR output when preservation and JPEG XL are selected. The exporter
maps linear Rec.2020 to 16-bit integer Rec.2100 PQ at 203 cd/m² reference white.
The standalone encoder has a narrow local extension for explicit D65/Rec.2020,
ST 2084 and absolute luminance metadata; the pinned upstream compression code
is retained. Out-of-gamut/nonfinite or >10000 cd/m² samples fail HDR export
rather than claiming successful preservation. PQ quantization precedes lossless
compression. SDR conversion clips extended values and is explicitly documented.

Schema-2 records now include automatic preservation preference, high-precision
readback availability, selected HDR detection and peak relative signal. The
`screenshot` object records output bits per channel, HDR preservation, color
encoding, reference white and range conversion. The readable report and embedded
XMP carry the same information. Capture precision never implies original-media
precision or verified source authenticity.

All three image formats embed the same XMP packet: IPTC Core Title
(`dc:title`) and Headline (`photoshop:Headline`), both using the page title;
Description (`dc:description`, source report without the capture
limitations, copyright notice, language setting or browser/version), optional
Alt Text (`Iptc4xmpCore:AltTextAccessibility`, the user-entered image description),
Source (`photoshop:Source`, the reviewed posting account and permalink joined
with ` / `, or either value alone when only one is supplied), and Date Created
(`photoshop:DateCreated`, screenshot capture time). `dc:source` records the page
URL; XMP CreatorTool/CreateDate record the browser and capture time. A custom
`helium:SourceRecord` property preserves the complete schema-2 JSON, including
selection/viewport geometry and separately identified automatic/user fields.
Publication date text remains reviewed source text with its origin recorded;
no creator or copyright ownership is inferred. Copyright Notice (`dc:rights`)
contains the requested source credit: `Screenshot / [account] / [platform]` or
`Skjermbilde / [account] / [platform]`. The remembered English/Norwegian selector
updates a live preview. The notice uses the reviewed account and recognized
permalink platform, falling back to the captured page's platform or hostname;
an empty or missing account uses `Screenshot / [hostname]` or
`Skjermbilde / [hostname]` from the captured HTTP(S) page instead. This works
on any website, omits a leading `www.` and excludes ports, paths, queries and
fragments. Invalid, non-HTTP(S) or credential-bearing URLs leave the fallback
absent. Twitter/X is labeled Twitter. XMP
stores the selected text as both `x-default` and `en`/`nb`; the complete source
record identifies the formatted-source-credit method without recording the
language preference. The ZIP text report retains the capture limitations.
The optional remembered `Captured by (username)` field is explicitly entered
by the user and stored in IPTC Creator (`dc:creator`, an RDF sequence), the
readable description and `user_provided.captured_by` in the complete record.
It identifies the screenshot capturer separately from the posting account.
Creator stays absent when this field is empty; no rights-holder flag is set. XML is escaped, and JPEG uses Adobe
Extended XMP for long records.
PNG uses the standard XMP iTXt keyword; JPEG XL uses an uncompressed `xml ` box.

The review panel places editable source fields beside a read-only IPTC/XMP
preview, stacking the preview below the form in narrow browser windows. Export
settings, image description/notes, capture facts and the complete embedded JSON
record have keyboard-accessible disclosure buttons. XMP property names can be
hidden, and focusing a source field highlights the relevant standard metadata
headings. Save/Copy actions stay outside the scrolling review area.

The preview and encoder share `BuildScreenshotMetadata`, including the complete
Description and source record. Color analysis is cached for the frozen capture;
editing text does not encode images or repeat pixel analysis. Post text is
manually entered in this version and remains separate from notes and alt text.
Their origins are recorded as user-entered or not supplied. Empty alt text is
omitted from XMP; notes and post text are never silently used as alt text.
Capture limitations remain in `helium:SourceRecord` and the ZIP's `source.txt`,
rather than occupying an accessibility-description field.

Panel validation: the persistent macOS development app rebuilt successfully;
13 native export tests, both GN header checks, patch lint, patch-file checks,
12 utility tests and a strict no-fuzz apply/reverse round trip passed. Native
checks covered two-column and stacked layouts, source suggestions, section
disclosures, field-name visibility, live text/alt-text updates and saving a PNG.
ExifTool and XML/JSON inspection verified exact multiline Unicode post text,
separate notes/alt text and their user-entered origins, Norwegian credit, separate
capture/publication dates and capture limitations in the embedded source record.
The native export used the controlled local Telegram fixture, not a live post.

Copyright-language validation passed the persistent macOS browser build, all
nine export tests, GN dependency checks, patch lint and strict patch apply/reverse.
ExifTool independently read the exact English/Norwegian Copyright Notice and
language alternatives from all six PNG/JPEG/JPEG XL fixtures. Native UI checks
verified live account edits, remembered language on the next capture, and a
saved PNG containing `Skjermbilde / @brukernavn / Twitter`.

A ZIP contains exactly `screenshot.png`, `.jpg` or `.jxl`, `metadata.json`
(schema version 2) and `source.txt`. Its SHA-256 hashes the final image including
embedded metadata. The embedded record omits that hash: a file cannot include
its own final hash. Page/user strings are file contents, never paths or commands.
Temporary files are removed after archive creation. A browser-created blob
hands the complete image or ZIP to Chromium's download manager, using the
remembered screenshot folder for direct saving or a save-location prompt, avoiding data-URL size limits. The archive excludes cookies and browser
storage, but the selected pixels, page URL/title and user notes may themselves
contain private information. The user explicitly chooses when and where to save.

Build with the persistent command from `AGENTS.md`. The patch also adds a small
standalone Chromium test target, independent of the pruned full browser suite:

```sh
autoninja -C out/Default screenshot_documentation_tests screenshot_color_tests
out/Default/screenshot_documentation_tests
out/Default/screenshot_color_tests
```

Tests unpack the production archive and check lossless PNG pixels, final-file
hashes, dimensions, distinct automatic/user fields, UTF-8/multiline values,
XML escaping, absent metadata, JPEG decoding, extended JPEG metadata, JPEG XL
container structure, default-on HDR/disabled/SDR-format exports, metadata, and
empty-image rejection. Copyright tests cover English/Norwegian, reviewed accounts,
platform selection, empty accounts, XML escaping and all three export formats.
Color tests cover selected-area detection, PQ highlights,
out-of-range failure and exact half-float IPC round trips with odd dimensions.
Optional independent validation
fixtures can be generated by running the test executable with
the following flags:

```sh
--gtest_filter=ScreenshotDocumentationTest.ExportsExactImageAndDistinctSourceFields \
--screenshot-fixture-dir=/absolute/output/directory
```

This writes PNG/JPEG/JPEG XL images, their documentation ZIPs, and a JPEG with
a long metadata record for inspection with ExifTool and `djxl` (development
tools only).
 UI validation should cover manual selection, reverse dragging, Escape,
copying, invalid permalink correction, save cancellation/retry, large captures,
inactive split panes, mobile previews, navigation during/after capture and a
closed source tab. A hash is an integrity aid relative to the saved manifest,
not independent proof of authenticity or of the computer's clock.

Local Apple Silicon validation passed the persistent browser build, GN header
dependency checks, patch lint, a no-fuzz patch apply/reverse check and the
initial three archive tests. Native UI checks covered forward/reverse rectangle dragging,
Escape cancellation, Enter capture, permalink validation and source-field entry.
Saved 950 × 380 and 2170 × 1200 crops retained their native 2× pixel density;
the latter produced a 7.5 MB ZIP. The exported PNG dimensions and SHA-256 values
matched their manifests, including Unicode/multiline notes and empty optional
fields. Split/mobile combinations and navigation races still need broader
browser QA before release.
The default screenshot shortcut was also verified in the native macOS app:
Command-Shift-S opens selection, the File menu exposes the command, and Keyboard
shortcuts settings show the binding with editable Add/Remove controls.

Format export validation on Apple Silicon passed the rebuilt browser, all six
export tests, GN dependency checks, patch lint and strict patch application.
ExifTool read IPTC/XMP fields and the complete source JSON from PNG, JPEG and
JPEG XL without warnings, including a JPEG with 150 KB notes. XML parsing
verified that escaped control/noncharacter input survives in the JSON record.
The independent libjxl decoder produced pixels identical to the PNG gradient,
and all three ZIP manifests hashed the final embedded-metadata images correctly.
Native review exposed all three format choices and the ZIP checkbox, and the
save path produced a complete documented PNG ZIP. Standalone JPEG/JPEG XL
encoding was independently verified; their native save-dialog paths and other
desktop platforms still need broader UI QA before release.

Permalink validation passed four standalone C++ tests and 21 real-DOM fixtures
covering all three platforms, quoted/multiple posts, partial post crops, hidden
and occluded links, URL normalization, preserved Facebook comment IDs, zoom
coordinate conversion and conservative scan limits. The pinch-offset fixture
simulates visual viewport geometry; physical pinch/mobile behavior still needs
broader device QA. Run the production script fixtures with:

```sh
python3 devutils/screenshot_source_server.py
# Open http://127.0.0.1:8232/ and click Run permalink checks.
# The browser console can also call runScreenshotSourceTests().
```

The standalone C++ target is `screenshot_source_tests`. The existing export
tests additionally cover preserved suggestion records and a distinct reviewed
permalink. The macOS browser build and GN checks passed. Native checks verified
Command-Shift-S selection, a 1580 × 366 manual crop with its timestamp outside
the crop, automatic permalink fill, scrolling without capture, Escape, Enter,
an ambiguous-link chooser and editable candidate selection. ExifTool read the
saved PNG's complete source JSON and confirmed the original/normalized candidate
URLs, reviewed-suggestion origin, native 2× geometry and user notes. Tests use
controlled local markup; authenticated live layouts for Twitter/X, Instagram
and Facebook still need field testing as those sites change.

Truth Social and account/date validation passed the development browser build,
GN dependency checks, all ten C++ source/export tests and 38 browser fixtures.
The production inspector was also exercised on public Truth Social feed/detail
pages and X's public profile view. It kept re-shared/quoted accounts and dates
separate, read Truth Social's relative label plus full tooltip/footer date,
and preserved X's plain relative timestamp links without fabricating an exact
time. Authenticated layouts and other languages still need broader site QA.
Native macOS checks confirmed account/date autofill, distinct UTC capture time,
updated untouched fields when choosing another source, and preservation of a
manual account edit and deliberately cleared date. ExifTool recovered both
saved PNGs' site observations and reviewed field origins correctly.

Twitter hover validation passed five C++ source tests, all nine export tests,
48 real-DOM fixtures, the persistent browser build, GN checks and patch lint.
A native selection of the reported public X post filled
`11:57 PM · Oct 15, 2026` automatically. ExifTool recovered the same reviewed
date and tooltip, the original `25m` label, and a distinct tooltip observation
time after pixel capture. The saved crop retained the site's relative label.

Quote-post validation passed six C++ source tests, nine export tests, 57 DOM
fixtures, the browser build, GN checks and strict patch apply/reverse. Live X
inspection covered full enclosing posts and crops confined to quoted cards.
Native macOS review selected Elon's permalink, account and full hover timestamp
for the reported full quote post; switching the source chooser selected Arash's
account and distinct date. ExifTool confirmed the saved PNG's primary source,
matching Copyright Notice, and the quoted post's separate link/account/date and
`quoted_by` relationship.

Expanded social timestamp validation passed eight C++ source tests, nine export
tests and 79 production-script browser fixtures, the persistent macOS build,
GN dependency checks, patch lint and strict no-fuzz patch apply/reverse. Public
examples supplied for Instagram, Threads and Truth Social were inspected with
the production script. Instagram used the post footer datetime rather than the
caption's later datetime or comment dates. Threads kept the enclosing post and
quoted post separate. Truth Social used the main detail footer rather than the
quoted post's earlier timestamp.
Native Facebook selection automatically read `Saturday, October 3, 2026 at
3:33 PM` from hover while preserving the original `October 3 at 3:33 PM` label.
Facebook's deeply nested markup uses a bounded 64-level selector so its date
link remains an exact hover target. Native Threads capture selected the main
post's account and ISO timestamp, with the quoted source retained separately.
ExifTool verified both saved PNGs, reviewed date/account origins, matching
Norwegian Copyright Notice and removal of transient hover selectors. Missing
years are not inferred; unavailable hover dates retain the site's original
label. Authenticated layouts, additional locales and other desktop platforms
still require broader field testing.

Facebook photo-source validation passed nine C++ source tests, nine export tests
and 88 production-script DOM fixtures, including full/photo-only crops, multiple
attachments, sibling posts and comment/text-link exclusions. Native macOS
capture of the reported profile-picture post selected its `/posts/` URL and
filled `Truls Aagedal` and `Sunday, August 9, 2026 at 12:27 AM` automatically.
A native photo-only crop filled the same post source, account and full date.
ExifTool confirmed the reviewed source and date, matching Copyright Notice and
separate attached photo URL, without assigning the post's account/date to that
photo. The browser build, GN dependency check, patch lint and strict no-fuzz
patch apply/reverse also passed.

## Experimental multi-pane split view

`helium/ui/multi-pane-split-view.patch` extends the base split implementation;
the actions and layout-options patches are applied after it in `patches/series`.
It extends the existing split collection to three or four tabs. Select three or
four ordinary tabs with Command-click (macOS) or Control-click, right-click a
selected tab, and use the existing split command. Choose either orientation
when that submenu is available. Four tabs form a 2×2 grid; three tabs form two
small panes beside one larger pane. Changing orientation changes the order in
which the grid is partitioned.

This remains an experimental feature with a six-pane limit. Geometry checks
cover all layout presets; full browser integration testing remains required
before shipping. Local macOS builds reuse the prepared cache documented in
`AGENTS.md`.

Every divider is resizable, including subdivisions inside each half. Drag a
boundary or focus its handle and use the arrow keys. Pane sizes stay with the
split when switching tabs and are restored with the last session. Exit split preserves the active tab. Closing or detaching one
pane exits the entire split, following the existing model behavior. Pair-only
reverse, close-half, and replace/swap commands are disabled for grids.
Last-session restore accepts up to six panes; recently closed windows and
Groups restore their tabs without reconstructing a grid. Grid corner styling
and animation clipping use the fallback behavior rather than the pair-specific
window corner/animation rules.

Right-click a tab and open **Split Layout** to create or rearrange a split:

- **Three Columns / Three Rows**: a 1×3 or 3×1 strip.
- **Four Columns / Four Rows**: a 1×4 or 4×1 strip.
- **2 × 2 Grid**: the original four-pane grid.
- Mixed layouts: one pane beside two or three stacked panes, or one pane above
  two or three side-by-side panes, with mirrored variants for each.

The action retains existing pages and fills spare panes with new-tab pages.
It acts on the right-clicked tab, even when other tabs are selected. Changing
an existing layout keeps the split and its pages. Choices with fewer panes than
the current split are disabled. Every boundary has a native resize handle. Choosing a layout resets the main
divider to its default ratio and the subdivisions to equal sizes. Layout choices persist in last-session restore;
older session files default to the original grid arrangement.

These choices are implemented by `helium/ui/split-layout-options.patch`.
It adds browser coverage for in-place rearrangement and a session round-trip
regression for every arrangement. Full browser/session test execution still
requires an unpruned Chromium test tree.

`helium/ui/four-pane-split-actions.patch` also fixes grid accessibility labels:
it avoids passing indices 2 and 3 to the pair-only label formatter, which
aborted the browser when creating a grid. The layout-options patch uses
indexed pane labels that work across all shapes.
Browser regressions cover creation, expansion, and both label orientations.

### Checks available in this repository

```sh
python3 devutils/lint.py
python3 devutils/test_multi_pane_split.py
```

The second command compiles the actual grid partition helper extracted from the
patch with C++20 and address/undefined-behavior sanitizers. It checks coverage,
non-overlap, containment, unused panes, pair compatibility, invalid pane counts,
and odd/zero/tiny dimensions across 11,200 cases. An additional 400 resize cases
check both orientations, all presets, minimum sizes, gutter placement, and
adjacent-pane resizing that leaves the other panes unchanged. It does not compile the browser
or prove that tab activation and session integration work.

To test the complete production header in an already patched source tree:

```sh
python3 devutils/test_multi_pane_split.py --source-tree /path/to/build/src
```

### Browser validation still required

Use the [Helium macOS development build workflow](https://github.com/imputnet/helium-macos/blob/main/docs/building.md#development-build-and-environment).
The packaging repository supplies `dev.sh`, Chromium downloads and the build
toolchain; this core repository alone does not build a browser. Its
`helium-chromium` submodule must contain this private fork's changes and match
the packaging version. After installing that workflow's dependencies, use
`source dev.sh`, `he setup`, `he build`, and `he run`. Use the development
profile provided by `he run` when testing.

The grid patch adds these tests to Chromium's existing `TabStripModelTest` suite:

- `FourPaneSplitSelectionAndFocus`
- `MoveWithinFourPaneSplit`
- `RestoreFourPaneSplit`

The follow-up actions patch adds these `TabMenuModelBrowserTest` regressions:

- `FourPaneSplitAccessibleLabels`
- `CreateAndExpandFourPaneSplit`
- `ChangePaneArrangementInPlace`
- `SplitLayoutSubmenu`

Run those tests and the existing split model tests in a Chromium build. Before
shipping, also check two/three/four panes in both orientations; click and
keyboard activation in every pane; the toolbar's URL; switching between grids,
pairs and ordinary tabs; resizing; devtools and modal dialogs in each pane;
exit/close/detach; pinned/grouped tabs; vertical/horizontal tab strips;
fullscreen; right-to-left layout; and restart/recently-closed restore.
All contributions and any future PR must stay within the private fork.

## Mobile preview workspaces and per-tab auto-refresh

`helium/ui/tab-preview-workspaces.patch` extends the four-pane prototype.
Right-click an individual tab and open **Tab view**:

- **Mobile preview (402 × 874)** toggles a fixed portrait viewport with 3×
  device density and mobile viewport/touch emulation. The page is centered and
  scaled down to fit its pane, keeping its CSS viewport unchanged when the
  window or divider is resized. It uses Chromium's emulation API without
  opening a DevTools window, device toolbar, or console.
- **Create desktop/mobile workspace** creates two copies of the page in a
  named **Desktop + mobile** saved tab group, pins that group, and splits the
  copies side by side with more space for desktop. The original tab is retained.
  Rename the group using the normal group menu. This action requires a regular
  profile with saved groups enabled.
- **Auto-refresh** offers **Off** and every 15 seconds through 180 seconds
  (15, 30, 45, …, 180). It applies only to the right-clicked tab, even if several
  tabs are selected or belong to one split. Off is the default.

The preset matches the 402 × 874 CSS-pixel dimensions corresponding to the
[standard iPhone 17's 1206 × 2622 display](https://support.apple.com/en-us/125089)
at 3× density. This is a Chromium responsive preview: it does not emulate
Safari/WebKit, an iPhone user agent, browser bars, or a screen cutout.
`helium/ui/mobile-preview-device-identity.patch` adds an Android mobile Chromium
user agent and matching Client Hints to both mobile modes. HTTP requests and
JavaScript device detection see a mobile device, while other panes retain their
desktop identity. Switching between desktop and mobile reloads eligible HTTP(S)
GET pages; POST pages are not automatically resubmitted. Changing only the mobile
height does not reload. Restored panes receive their identity before loading.

Tab settings are included in session snapshots and recently closed tab data
and copied when a tab is discarded. Refresh skips loading, crashed, discarded,
non-HTTP(S), and POST pages. Closing a tab destroys its timer. Mobile preview
does not take over an already attached inspector; attachment/protocol failures
clear the toggle. Normal developer tools remain available when explicitly
opened.

Saved groups store tab settings locally using stable saved-tab IDs. Reopening
a preview workspace reconstructs its desktop/mobile pair when both saved tabs
still exist, including after reordering or renaming. These extra settings and
the pair layout are local to the profile and are not synced to other devices.
Reopened workspaces use the default side-by-side orientation and 65/35 divider;
last-session restore retains the normal split layout/ratio. Creation during
saved-group service initialization still needs browser validation.

### Validation

```sh
python3 devutils/lint.py
python3 devutils/test_multi_pane_split.py
python3 devutils/test_tab_preview.py
```

The preview check compiles the production fit/interval helper with C++20 and
address/undefined-behavior sanitizers, exercising 132 viewport cases and
601 interval values. It does not compile the browser or exercise a timer.
The patch adds `PaneSettingsTest.*` to Chromium's existing unit-test target,
covering timer deadlines, interval replacement, Off, independent tabs, tab
destruction, loading/POST/discard skips, and valid/invalid restoration.
Run those tests in the build environment described above.

The Apple Silicon development build compiles these features, but full Chromium
browser and timer test execution still requires an unpruned test tree. Before
shipping, verify a
responsive page with `innerWidth`, `innerHeight`, `devicePixelRatio`, viewport
metadata and touch media queries; every interval in ordinary tabs and split
panes; foreground/background refresh; POST and beforeunload handling;
disable/re-enable; switching between mobile and desktop panes; resizing;
navigation and renderer crashes; tab hibernation; closing/reopening the saved
workspace; tab reordering and group renaming; restart; inspector attachment;
and unavailable saved groups/incognito. Use a development profile.

## Stability review (October 2026)

`helium/ui/pane-stability.patch` is applied after the layout-options patch. It
keeps tab-specific split menus attached to the original tab and split identities
when indices change, and disables actions, labels, and icons after that split
disappears. Toolbar/divider menus still resolve the active tab lazily because
they are created before tabs exist and reused across splits. Browser regressions
cover index changes, split removal, menu reuse, and an empty tab-strip model.

Selecting an unchanged auto-refresh interval preserves its deadline and avoids
redundant session writes and view invalidation. Refresh also skips pending
navigations. Mobile preview resizing updates device metrics without resending
unchanged touch settings; attachment and page changes still configure both.
Two additional `PaneSettingsTest` regressions cover timer deadlines and pending
navigation.

The upstream archive-layer merge and build-dependency pruning changes have
regression coverage in `utils/tests/test_prepared_sources.py`. Run the utility
checks with pytest installed:

```sh
PYTHONPATH=utils python3 -m pytest -o addopts='' utils/tests
python3 -m pytest -o addopts='' devutils/tests
```

Review validation: all 12 utility/developer tests passed, patch lint passed,
the five feature patches and upstream Web Store patch reversed and reapplied
without fuzz against the cached source, and both sanitizer helper checks passed
against the production headers. The persistent macOS component build passed,
including the merged upstream Web Store resources, and a fresh-profile headless
startup/rendering smoke test passed. Both the pane-settings unit-test source and
tab-menu browser-test source compiled independently using their generated
Chromium commands; this also fixed existing `NavigationSimulator::CreateFromPending`
and `chrome::NewTab` test API mismatches. A Chromium regression-test build stopped
at missing pruned test data (`chrome/test/data/extensions/extension_api_unittest/
api_features.json`); the new browser and timer regressions remain unexecuted.

## Helium Neo branding

The private fork builds as `Helium Neo.app`. Its macOS bundle identifier and
normal profile directory name are `no.aagedal.helium-neo`; its Keychain entry is
`Helium Neo Storage Key` (account `Helium Neo`). Existing Helium profiles and keys
are not migrated. The local launcher retains the existing `build/dev-profile`.

`utils/name_substitution.py` applies the display name and macOS identities after
platform patches. For the existing prepared cache, run it from this worktree:

```sh
python3 utils/name_substitution.py --sub -t "$HOME/Developer/helium/build/macos/build/src"
```

Then use the persistent `build-local.sh` described in `AGENTS.md`. Do not run
`prepare_sources` against the cache. The persistent launcher must target
`out/Default/Helium Neo.app/Contents/MacOS/Helium Neo` after rebuilding.

## Resizable multi-pane dividers

`helium/ui/resizable-multi-pane-splits.patch` adds the missing native resize
handles for the inner boundaries of three/four-pane layouts, reserves gutters
between those panes, and gives multi-pane rows usable minimum sizes. It keeps
pane weights in split visual data and appends them to session commands; old
sessions retain equal subdivisions. Selecting another preset resets the weights.
The ordinary two-pane divider keeps its existing behavior.

The patch also extends `SplitPaneArrangementSaved` to round-trip custom weights
and adds `SplitPaneSizesSurviveTabActivation` and
`CustomSplitPaneSizesRestored`. Those Chromium tests require an
unpruned test build; the standalone geometry harness runs in this repository.

Local validation: the component browser compiled successfully; all geometry,
resize, viewport and refresh harness checks passed. Native keyboard resizing
was checked in three columns, three rows and both halves of a grid. A clean
browser restart preserved a diagnostic pane at 556 × 457, including its custom
main ratio and inner weights. Pointer-drag automation was inconclusive, so a
hands-on drag check remains recommended before making a standalone release.

## Helium Neo atom icon

The private fork uses a helium atom instead of Helium's blue asterisk: two
protons and two neutrons, an orbit that tapers and fades toward the main
electron, a second electron, and helium's emission spectrum below on a dark
indigo tile. The ring stops short of each electron along a circle around it.

`devutils/generate_neo_icons.py` holds the geometry and writes every format from
it: the full-color `resources/branding/product_logo.svg` master, the layers in
`resources/branding/macos/AppIcon.icon` (glass electrons and nucleus, glass
orbit, spectrum, glow; Icon Composer allows at most four groups), the mono and
color Chromium vector icons, and the rasters. Edit the script, not the SVGs.
Both the classic `app.icns` and modern `Assets.car` are checked in; the common
resource list overrides the platform repository's icons after platform resources
are copied.

On macOS, regenerate the PNGs, wordmarks, Chromium vector paths, ICNS, and asset
catalog using Pillow, librsvg and Xcode:

```sh
~/Developer/helium/build/venv/bin/python3 devutils/generate_neo_icons.py
```

Then run `utils/generate_resources.py` and `utils/replace_resources.py` against
the prepared source before the incremental build. Do not recreate the cache.

## Five- and six-pane layouts

`helium/ui/extended-pane-layouts.patch` raises the split capacity to six and adds
these **Split Layout** choices:

- **3 × 2 Grid**: three columns in each of two rows (six pages).
- **Two Stacked Left + Three Columns**: two stacked pages in the leftmost
  column and three full-height pages beside it (five pages).

Every boundary uses the existing native resize behavior. The mixed layout starts
with one quarter of the width for the stacked column; its right side is divided
into three columns. Changing presets retains existing pages and fills new panes
with new tabs. A preset with fewer panes remains disabled for a larger split.

Sizes and arrangements persist in the session. The extra two pane weights are
an optional tail in the session data, so older four-pane sessions still restore
with equal defaults for unused panes. Regression coverage includes exact layout
geometry, every divider in every arrangement, six-pane focus/activation, and
browser restore tests for both new presets. Full Chromium browser test execution
requires an unpruned test build.

Local verification of the expanded presets: the component browser built, both
menu choices created their expected five/six panes, native keyboard resizing
worked in both mixed axes and on the final sixth-pane boundary, and a clean
restart reproduced all saved split visual data exactly. The older four-pane
session restored its original 556 × 457 diagnostic pane; the new five-pane
session retained its 291 × 457 diagnostic pane. No normal browser profile was
used for these checks.

## Pinned split and mobile view persistence

`helium/ui/pinned-split-pane-state.patch` fixes reload selection for every split
size (two through six panes). Command-R and bypass-cache reload affect the active
pane when a single split is selected. Explicitly selecting additional tab-strip
tabs retains Chromium's multiple-tab reload behavior.

Pinned-tab startup now saves and restores split membership, orientation,
arrangement, main ratio, all inner divider weights, and each tab's mobile mode
and auto-refresh interval. This also works when startup opens a new-tab page
rather than restoring the last session. Legacy URL-only pinned entries still
open as ordinary pinned tabs. These settings remain local to the profile.

**Tab view → Mobile preview (402 wide, full height)** is an additional mobile
mode. It keeps a 402 CSS-pixel width and 3× device density, uses the entire pane
height, and scales down only when the pane is narrower than 402 pixels. Its CSS
height follows the available height without the portrait preset's 874-pixel cap.
The fixed **Mobile preview (402 × 874)** remains available. Selecting either mode
replaces the other; selecting the checked mode returns to desktop rendering.

The preview harness checks both modes, including tall and narrow panes. Chromium
regressions cover normal/bypass reload for every active pane and split capacity,
mobile/refresh setting round trips, and pinned split startup reconstruction with
custom sizes and per-tab settings. Full regression execution still requires the
unpruned Chromium test dependencies described above.

The modern macOS icon uses 1024-pixel transparent rasters of each layer inside
Icon Composer. Apple's SVG importer fills stroked shapes and reduces their size,
so the generator supplies `AppIcon.icon/Assets/*.png` from the matching SVGs. To
verify the actual modern rendering, use Icon Composer's bundled
`ictool --export-image` for the Default, Dark, TintedLight and ClearDark
renditions, rather than inspecting only the fallback PNG or ICNS.

Validation for these changes: the persistent Apple Silicon component build
passed, patch lint and reverse-application checks passed, and both standalone
sanitizer harnesses passed against the repository patches and prepared source.
The reload browser test, pinned-startup browser test, and pane-settings unit-test
sources compiled independently with Chromium's generated commands. Full browser
regressions were not executed. Native UI automation failed with
`Sky Computer Use native pipe closed before response`, so keyboard/restart UI
checks remain unverified. A seeded-profile smoke attempt was inconclusive because
Chromium's protected preferences discarded the injected pinned-tab entries.
Apple's Icon Composer renderer reproduced the old filled oval and verified the
corrected orbital foreground; the built app's asset catalog matches the new
checked-in catalog.

HDR export fixtures are generated by including
`ScreenshotDocumentationTest.HDRExports16BitPQAndDocumentsSDRConversions` in the
filter (or running all tests with `--screenshot-fixture-dir`). Decode
`hdr-auto.jxl` using upstream `djxl --bits_per_sample=16`; its PNG color profile
must report Rec.2100 PQ and BT.2020. Compare decoded integer samples against the
ST 2084 calculation, and check `hdr-disabled.jxl`/PNG/JPEG are documented SDR.

HDR validation: all four color/transport tests, seven export tests and four
source validation tests pass. An independent libjxl decoder reads the HDR
fixture as 16-bit Rec.2100 PQ / BT.2020 and reproduces the expected PQ codes
for linear values 4, 2 and 1 exactly. A separate 321×179 gradient including
varying 16-bit alpha also round-tripped sample-for-sample.

Native macOS verification used an HDR-capable display with a PQ PNG fixture.
The default-on preference selected JPEG XL automatically; full-pane and manual
HDR captures exported genuine 16-bit PQ with embedded source records. A
separate SDR crop on the same page exported at 8-bit. Disabling preservation
persisted into the next capture and exported documented SDR; re-enabling it
updated the same frozen capture. With `--disable-gpu`, rendering was SDR and
the PNG export correctly recorded no HDR preservation. Normal GPU rendering
and the previous page were restored after testing.

The final persistent application build passed after the complete Skia/Viz F16
serialization integration. All 15 screenshot regressions were rerun successfully
against that completed output. Header dependency checks, repository lint and
strict no-fuzz patch apply/reverse checks also passed.

## Mobile device identity and active split indication

`mobile-preview-device-identity.patch` supplements both mobile viewport modes
with per-pane Android Chromium identification in HTTP headers, Client Hints,
and navigator properties. Enabling/disabling mobile mode reloads eligible GET
pages; restoring settings and changing mobile height do not start another load.
The browser regression in `TabMenuModelBrowserTest.MobilePreviewDeviceIdentity`
checks echoed request headers, JavaScript identity, desktop-pane isolation,
height changes, and returning to desktop.

`split-active-pane-indicator.patch` uses the normal theme-aware active-tab
background for the actual active sub-tab and inactive backgrounds for its
siblings. The highlight remains visible while the toolbar or a context menu has focus. Clicking another
sub-tab within the current split explicitly selects that pane; returning from
another tab still restores the split's last focused pane.

Validation: both changes compiled in the persistent Apple Silicon component
build; the browser regression source compiled using its generated Chromium
command. The full browser-test executable was not built/run in this pruned
cache. Native app checks confirmed mobile HTTP/JavaScript identity, TV 2's
latest-news strip, desktop/mobile isolation, and selection indication in
two-pane and compact pinned three-pane splits. Clicking a pinned sub-tab selected its corresponding pane after restart. A restored inactive
saved split showed blank contents during the additional session-restore check;
that restore path remains unverified.

The split indicator uses existing theme background states rather than a custom
underline or thicker pane outline. The revised component app built successfully,
and native checks confirmed the highlight follows compact pinned sub-tab selection.
The old downloaded installer contained the malformed modern macOS icon catalog;
macOS resolved the current running build to the correct orbital icon.

## Vertical pinned split tabs

`vertical-pinned-split-tabs.patch` applies active-pane background highlighting
and direct sub-tab selection to the vertical tab implementation. Each pinned
sub-tab paints its own theme background rather than sharing the first pane's
background. In an expanded sidebar, pinned split icons share a row and wrap
when the sidebar cannot fit all panes; the collapsed sidebar keeps its vertical
icon stack. Expanding/collapsing invalidates the split layout.

`PinnedSplitTabViewTest.ExpandedTilesAndSelection` covers two through six panes,
multiple sidebar widths, non-overlapping bounds, direct selection and style
state, and the collapsed stack.

Validation: the persistent Apple Silicon app build and independent Chromium
browser-test source compilation passed. Native UI checks verified the expanded
three-pane pinned icon row, per-pane selection, the collapsed icon stack, and
expanding back to a row. Full browser-test execution remains unavailable in the
pruned cache.


Bluesky source extraction adds matching profile/permalink attribution, feed and
reply timestamp accessibility labels, and the expanded thread item's scoped date
footer. DID paths remain as observed; they are not resolved to guessed handles.
Reposter links and body mentions cannot establish the posting account. An
unlinked quote gets separate DOM ownership; a crop confined to it cannot autofill
the enclosing source. The expanded page URL is never assigned to a lone reply.
Linked quotes use the existing enclosing/quoted source relationships.

Validation for this addition: 105 production-script browser fixtures, nine native
source tests and nine native export tests, plus patch parsing, lint and a strict no-fuzz patch reverse/apply round trip
for all four changed Chromium files. The complete patch round trip against the
shared cache still encounters existing differences in screenshot_captured_bubble.h
and the JPEG XL encoder, outside these changes. Public
Bluesky pages were checked for an original feed post, a repost, an expanded quote
post, a crop inside its unlinked quote, and a thread reply with its own date.
The focused native targets were rebuilt in the persistent macOS cache. The full
app rebuild was stopped after it scheduled a broad dependency rebuild; native
capture-dialog and saved-image QA for Bluesky remain to be completed. No external
API requests or identity resolution were added to the capture flow.


TikTok source extraction recognizes explicit `/@account/video/id` and
`/@account/photo/id` links. Current `recommend-list-item-container` articles can
use page address/canonical/Open Graph metadata only when their scoped
`more-menu-icon` item IDs agree with the URL. Adjacent preloaded articles are
matched independently. Missing, conflicting or stale IDs leave page-derived
sources unset, and a crop containing multiple posts cannot silently autofill
its only discoverable source. Native validation accepts only normalized TikTok
video/photo post paths.

Creator profile links must match the permalink's account. The adjacent creator
row supplies the displayed date, without decoding dates from IDs or inventing
years/timezones. A visible avatar can support a date next to a rendered zero-width
creator name; hidden links cannot. Caption/header links to a different post are
references, retained only when directly selected and requiring review. Known
comment containers have separate ownership, and captures including unsupported
comments require review, including crops with margins. No short-link resolution
or external API was added. An observed photo URL can retain `image_index` in the
source record while the suggested permalink identifies the post.

Validation passed 141 production-script browser fixtures, ten native source
tests, nine native export tests, two GN header dependency checks, patch lint and
a strict no-fuzz reverse/apply round trip for the four changed Chromium files.
The full development app and the final incremental revision were rebuilt using
the persistent macOS cache. Native review filled the video/photo permalink,
account and date; a full-pane capture including a comment required review with
blank fields. Stale item IDs and an obscuring overlay left all source fields
blank. ExifTool verified a saved PNG's reviewed values and origins, original photo
URL with `image_index=3`, creator-row date evidence and distinct capture timestamp.

Current public video and photo markup was inspected directly for item IDs,
creator/date rows and preloaded articles. Unobscured authenticated live capture
checks remain limited by TikTok's login/signup and verification prompts; the
live overlay correctly returned no source for its obscured post.

For reproducible native capture/export checks, run the fixture server and open
`http://127.0.0.1:8232/tiktok-capture`. Video and photo media crops should suggest
`@reporter` with the displayed date. Comment crops require source review. The
stale-metadata and overlay variants should leave the source blank. This is
controlled local content, not an authenticated live TikTok capture.


Reddit source extraction supports the observed current `shreddit-post` and
`shreddit-comment` layouts. Post permalinks must agree with `t3_` IDs; comment
permalinks must agree with both their `t1_` comment ID and `t3_` parent post ID.
Current and legacy explicit comment paths normalize to a distinct comment URL;
title slugs and tracking parameters are removed while the original URL remains
in provenance. Native validation accepts only these normalized post/comment
paths. Share-code links and `redd.it` links are not resolved.

Author links must be visible in the item's own credit row and agree with its
reported author. Subreddit links, body mentions, deleted authors and nested
reply authors do not supply the selected item's account. Publication times must
be visible in its own credit row and agree with its reported creation time;
missing evidence or duplicate matching timestamps leave the date blank. Edited
timestamps cannot substitute for creation times. The observed datetime, tooltip
and displayed relative label remain separate; no hover or external API is used.
A crop confined to a nested reply excludes its ancestors. Captures spanning
multiple items, unsupported items, directly selected references or crossposts
require review. Current crossposts embed the original's media inside the
reposter's container without a separate author/ID scope, so they never autofill
as a unique source. Page address/canonical/Open Graph URLs cannot establish
Reddit item ownership.

Validation: 178 production-script browser fixtures, 11 native source tests and
nine native export tests passed. Both GN header dependency checks, patch lint,
patch-file checks and the strict no-fuzz reverse/apply round trip for the four
changed Chromium files passed. The persistent macOS development app rebuilt
successfully. Live public Reddit checks covered a feed post, expanded post,
comment, nested reply with its own date and a crosspost media crop requiring
review. Old Reddit redirected to login and its layout is not supported by this
addition; authenticated and additional locale layouts remain unverified.

Native capture-dialog QA used `http://127.0.0.1:8234/reddit-capture` (or the port
given to `screenshot_source_server.py`). Post and comment crops showed distinct
permalinks, accounts and dates; a full-page capture left all three fields blank
and offered a source chooser. A saved post PNG was inspected with ExifTool and
its embedded source record verified the reviewed fields, original tracked URL,
relative date, Reddit credit and separate capture time. This page is controlled
local test content, not a live Reddit capture.


YouTube extraction normalizes explicit watch, Shorts, live and `youtu.be` video
links to `https://www.youtube.com/watch?v=VIDEO_ID`; an observed comment's full
`lc` parameter remains distinct, including reply IDs containing dots. Playback
time, playlists and tracking are omitted from the suggestion and retained in the
original observed URL. Native validation accepts only the normalized video and
comment forms. Embed, clip, playlist-only and channel URLs are not video sources.

A watch video needs a matching `ytd-watch-flexy[video-id]` and agreement between
observed page address/canonical/Open Graph video IDs. The crop must overlap the
player or watch metadata; comments, sidebar recommendations, chat and unrelated
panels cannot borrow that source. Shorts use their own scoped
`#shorts-player a.ytp-title-link` rather than the current page address, so adjacent
preloads stay independent. Uploader links come only from the video owner or the
Short's channel bar. Observed handles, including Unicode, remain handles;
channel-ID/legacy profile links retain their observed display name and profile
URL without identity resolution. Conflicting owners leave the account blank.

Watch dates come from the observed two-label watch-info row (view count and
publication label). Expanded descriptions expose a calendar date in that same
row; collapsed relative labels remain relative. Body text, generic time elements
and hidden tooltip contents are excluded. Shorts dates remain absent. Current
watch-page comments use their own `#published-time-text` link and scoped author
row; nested replies retain their complete `lc` identity. Date text, including an
edited marker, is preserved without parsing it into a guessed publication time.
Shorts comment panels and live-chat messages are not attributed by this addition.
References from any YouTube item are kept only when directly selected and require
review. Known selected ads suppress uploader/date details; recommendation and
end-screen tiles, unsupported selected items and multiple sources prevent silent
autofill. No external API or timestamp hover was added.

Validation: 230 production-script browser fixtures, 12 native source tests and
nine native export tests passed. Both GN dependency checks, seven patch lint
checks, patch-file checks, existing devutils tests and the strict no-fuzz
reverse/apply round trip for all four changed Chromium files passed. The
persistent macOS development app rebuilt successfully. Live public checks covered
a watch-player crop, expanded watch date, comment with its own author and `lc`,
a Short with its own handle, and end-screen recommendations requiring review.
Authenticated, mobile and additional locale layouts, live broadcasts and actual
advertisements still need broader live QA; the ad guard was verified in fixtures.

Native QA at `http://127.0.0.1:8235/youtube-capture` verified separate video and
comment fields, plus a full-page chooser with blank permalink/account/date.
ExifTool inspection of the saved comment PNG verified its full `lc` URL,
`@reader`, the unchanged relative edited label, reviewed-field origins, original
tracking URL, YouTube credit and separate capture timestamp. This is controlled
local test content, not a live YouTube capture.


LinkedIn source extraction targets the observed public
`article[data-activity-urn]` activity cards. Explicit `/posts/...-activity-ID-code`
and `/feed/update/urn:li:activity:ID/` permalinks, including encoded URN colons and
localized two-letter LinkedIn hosts, normalize to the activity URL. The original
observed URL retains tracking. Comment/reply query parameters, fragments,
profiles, articles, shortened `lnkd.in` links and share/UGC-post URNs are not
normalized into an activity. Native validation accepts only the normalized HTTPS
activity path with a numeric ID and no query/fragment.

Page address/canonical/Open Graph sources must match the card's own activity URN.
A different featured activity prevents attribution; the separate attributed share
URN is never treated as an activity ID. Container IDs alone do not manufacture
permalinks, and IDs are never decoded into dates. Public actor-name links must
belong to the card's own entity-lockup header. The linked display name and cleaned
member/company/school profile URL are retained without guessing an @handle from
a slug. Body mentions, comment authors, hidden names and conflicting author
observations do not provide an account. One visible scoped header `time` supplies
the observed datetime attribute or displayed date label, preserving relative
labels and edited markers. Missing/duplicate times stay blank; generic body times
and hidden tooltips do not supply publication dates. No timestamp hover, identity
resolution, short-link expansion or external API was added.

Public `section.comment` elements have separate ownership. The inspected layout
exposes only author links and relative labels, so comment-only crops leave source,
account and date blank. Crops with comments and post content, including margins,
require review. Unlinked nested articles cannot inherit the enclosing source;
references to other posts or platforms are kept only when directly selected and
require review. Authenticated feed layouts, LinkedIn articles and comment
permalinks are not supported by this addition.

Validation: 280 production-script browser fixtures, 13 native source tests and
nine native export tests passed. Both GN header checks, seven patch lint checks,
patch-file checks, existing devutils tests and the strict no-fuzz reverse/apply
round trip for the four changed Chromium files passed. The persistent macOS app
rebuilt successfully. Public company/person posts were inspected for activity vs
share URNs, localized author URLs, relative/edited date labels and separate
comment sections. Live sign-in overlays correctly yielded no suggestions.
Unobscured live capture and authenticated layout QA remain unverified because
LinkedIn presented sign-in overlays; no account or CAPTCHA flow was used.

Native QA at `http://127.0.0.1:8236/linkedin-capture` verified the post's activity
URL, Example Company name and unchanged `11mo Edited` label. A comment-only crop
left all attribution fields blank; the full page offered a chooser with blank
permalink/account/date. ExifTool inspection of a saved post PNG verified its
reviewed-field origins, original tracked `/posts/` URL, normalized company profile,
LinkedIn credit, site-date evidence and separate capture timestamp. This fixture
is controlled local content, not an unobscured live LinkedIn capture.


### Mastodon instance and status ownership

Mastodon uses a scoped `#mastodon` web-app fingerprint and standard `.status` /
`.detailed-status` headers and timestamp links. One own visible author profile,
observed `.display-name__account` and matching timestamp permalink must agree
before a URL is accepted. Arbitrary `/@account/id` links on other pages are not
platform evidence. Native validation checks a bounded ownership record; URL-only
candidates on arbitrary domains remain unsupported. This is heuristic DOM
attribution, not server or account authentication.

Instance hostnames, including `www`, `m` and `mobile`, remain intact. A remote
`/@user@home.example/id` route keeps the viewing instance's observed ID and URL.
Qualified handles remain exactly as displayed; account domains may differ from
profile web domains. No WebFinger, API request, data-id conversion or inferred
origin URL is used. The timestamp's own datetime/display text/title is recorded;
separate edited markers are excluded. Boost actors, mentions and preview cards
cannot supply the author. Linked nested quotes have separate ownership; missing
quote evidence and selected references require review. Multiple selected posts
cannot autofill a single source.

The current standard web app was inspected on mastodon.social and fosstodon.org.
Production-script checks on a local profile timeline, detailed status and remote
Fosstodon status returned the observed account, permalink and publication time.
A detailed reply containing a remote quoted status informed the quote fixtures.
Alternative frontends, older layouts, ActivityPub `/users/.../statuses/...` URI-only
links and inaccessible or virtualized placeholders are not supported.

The controlled native capture fixture is `/mastodon-capture`; it deliberately
uses a remote proxy handle, a `www` instance, a mismatched local data-id and a
separate edited label. It is local test content, not a live Mastodon post.

Validation: 306 production-script browser fixtures, 17 native source tests and
10 native export tests passed. The persistent macOS app rebuilt successfully;
both GN header checks, patch lint, patch-file checks, devutils tests and a strict
no-fuzz reverse/apply round trip for the four changed added Chromium files passed.
The separate copyright-preview change matches its compiled source block.

Native QA at `http://127.0.0.1:8237/mastodon-capture` confirmed the proxy permalink,
qualified account and original publication timestamp for a crop excluding the
header. The credit preview shows Mastodon. ExifTool inspection of a saved PNG
confirmed Mastodon credit, reviewed-field origins, observed tracked URL, ownership
record, exact instance hostname and separate capture timestamp. The edited label
was excluded. This remains a controlled local export test.


### Telegram public channel messages

The standard public `t.me/s/<channel>` timeline and standalone `?embed=1` message
widget expose `.tgme_widget_message[data-post]`, an own footer
`a.tgme_widget_message_date` and an own channel header link. The observed footer
permalink must match data-post before a body crop can inherit it. The matching
visible `.tgme_widget_message_owner_name` supplies the handle and display name;
missing or conflicting headers leave the account blank. No URL is synthesized
from data-post alone, page canonical metadata or a channel sidebar.

Explicit `https://t.me/<channel>/<positive-message-id>` links and `/s/` equivalents
normalize to the public message permalink. Original query parameters remain in
`original_url`; comment/thread/reply parameters and fragments are rejected so
separate identities are not collapsed. Native validation accepts only canonical
public message URLs, with a bounded ASCII username, no reserved service routes,
credentials, ports, query or fragment. Subdomains, private `/c/` links, invites,
`tg:` links and `telegram.me` aliases remain unsupported.

The footer time's datetime attribute and displayed text are preserved separately.
Absent machine dates remain observed text, without invented dates or zones.
Video duration, views, edited labels, forwarded-source names and reply previews
cannot supply the hosting message's author or publication time. A forwarded
message is attributed to its publishing channel and message timestamp, not its
original author. Forwarded-banner-only, reply-only and link-preview-only crops
require review; selected references and full reply context remain ambiguous.
Media albums with distinct selected message links also require review.

Live inspection of https://t.me/s/V_Zelenskiy_official and the standalone
https://t.me/V_Zelenskiy_official/21387?embed=1&mode=tme confirmed these selectors.
The production detector returned the exact message permalink, observed
`@V_Zelenskiy_official` header, displayed time and datetime for body-only crops in
both layouts. This tests public message content; private chats and Telegram Web's
authenticated UI are not supported. Standalone widgets are supported when loaded
as the captured top-level document; iframe-contained embeds are not traversed.

The `/telegram-capture` route serves controlled local content for native export
QA, including a tracked permalink, original timestamp, edited label and separate
reply preview. It is not a live Telegram message.

Validation: 344 production-script browser fixtures, 18 native source tests and
11 native export tests passed. The persistent macOS build, both GN header checks,
patch lint, patch-file checks, existing devutils tests and the strict no-fuzz
reverse/apply round trip for all four changed Chromium files passed.

Native QA at `http://127.0.0.1:8238/telegram-capture` verified body-only account,
permalink, original publication timestamp and Telegram credit preview. Reply-only
and full-page mixed captures offered review with blank permalink/account/date.
ExifTool inspection of a saved body PNG verified Telegram credit, tracked original
URL, normalized permalink, exact datetime offset and displayed time, reviewed-field
origins and separate capture timestamps. This is controlled local export QA.
