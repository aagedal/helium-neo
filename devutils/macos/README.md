# Helium Neo stable releases

The updater uses the public GitHub release asset `helium-neo.xml` as its primary
feed. Its backup is `https://aagedal.me/apps/helium-neo/helium-neo.xml`; that
feed downloads independently mirrored installers from the same directory.
Releases up to 0.21.1.1 look for the backup at the old
`https://aagedal.me/apps/appcast/helium-neo.xml`, which is no longer updated; they
pick up the new location with their next update from GitHub.

Neo retains Helium's service consent and browser-update preference. An enabled
installation checks on startup and daily, downloads in the background, and uses
the existing relaunch/update-on-quit integration. Before downloading an update
from GitHub, it measures GitHub and the mirror by fetching up to 2 MB of the same
installer from each for at most 8 seconds, then downloads from the mirror only if
it is at least 1.5 times faster (or GitHub failed the measurement). Sparkle
verifies the signature whichever host served the file. A download that receives
nothing for 30 seconds fails. A failed primary feed or archive download retries
once through the mirror, and a failed mirror download chosen for speed retries
once from GitHub. Both hosts failing ends the attempt; the next check starts
with GitHub. Signature, validation and installation errors do not trigger
retries. Development component builds keep Sparkle disabled.

## Build and package

Read the repository's AGENTS.md before modifying the shared cache. Confirm no
other build is using it. Reuse the prepared source and optimized `out/Beta3`
output; never run `prepare_sources` or reset the cache.

Update `release.json` for each release. The display version matches the four-part
Helium version in `chrome/VERSION`; `build` is a separate increasing Sparkle
version (`YYYYMMDD.sequence`). Increment it even when Chromium is unchanged.
The packaging script writes it into the staged app's CFBundleVersion before
signing, preserving the Chromium framework's own version and paths.

The Ed25519 private key is in macOS Keychain under Sparkle's service and account
`no.aagedal.helium-neo`. Only its public key is committed. Back up this key securely
using Sparkle's `generate_keys --account no.aagedal.helium-neo -x <private-file>`;
never commit or upload the exported private file.

Download the official Sparkle distribution matching the prepared framework
(currently 2.10.1) for its command-line tools, then:

```sh
neo_cache="$HOME/Developer/helium/build"
neo_source="$neo_cache/macos/build/src"
python3 devutils/macos/prepare_release_source.py \
  --source "$neo_source" --build-output "$neo_source/out/Beta3"
```

The common feed patch is part of `patches/series`. The Sparkle glue patch must be
applied after the platform's Sparkle integration, which is why it lives here.
The preparation command handles both patches idempotently and preserves all
other source changes and GN arguments. Then use the cache's Python environment:

```sh
export PATH="$neo_cache/venv/bin:/opt/homebrew/bin:$PATH"
export SISO_PATH="$neo_source/third_party/siso/cipd/siso"
cd "$neo_source"
./buildtools/mac/gn gen out/Beta3 --fail-on-unused-args
python3 third_party/depot_tools/autoninja.py -C out/Beta3 \
  chrome chromedriver screenshot_documentation_tests screenshot_color_tests screenshot_source_tests
```

From this repository, package into a new release directory:

```sh
python3 devutils/macos/package_release.py \
  --source "$neo_source" --build-output "$neo_source/out/Beta3" \
  --output "$neo_cache/releases/neo-stable-0.21.1.1" \
  --identity '<Developer ID identity>' --notary-profile notary \
  --sparkle-tools '<extracted official Sparkle distribution>'
```

This stages the app, checks the updater key, sets the build number, signs nested
code including Sparkle's installer, creates a DMG, waits for notarization, staples
the ticket, checks Gatekeeper, and generates both feeds using the Keychain key.
The backup installer is byte-for-byte identical, so its signature is identical.

## Validation and publication

Run `python3 devutils/macos/test_release.py`, repository patch/config checks,
the native screenshot tests, standalone dependency/signature and browser smoke
checks, and the real-browser updater scenarios in `test_updater.py` before
publishing. That harness uses disposable apps/profiles and localhost feeds; it
never modifies an installed app or personal profile. Download scenarios test
installation on quit from a lower signed build. It requires the packaged release,
built chromedriver, source path and Developer ID identity.

For example, run each of `current`, `feed-fallback`, `download-fallback`,
`slow-primary`, `both-down`, `bad-signature`, `disabled`, and `no-consent` with
(`slow-primary` throttles GitHub's installer to about 64 KB/s and expects the
download to come from the mirror):

```sh
python3 devutils/macos/test_updater.py \
  --scenario current --app '<release>/standalone/Helium Neo.app' \
  --chromedriver "$neo_source/out/Beta3/chromedriver" --release '<release>' \
  --source "$neo_source" --identity '<Developer ID identity>' \
  --report '<release>/updater-current.json'
```

Publish a stable GitHub release under the configured tag with the signed DMG,
`SHA256SUMS`, `helium-neo.xml`, `helium-neo-backup.xml`, and
`update-manifest.json`. Publish only after all assets have been uploaded to a
draft and verified. Set it as the latest release so the primary feed URL resolves.
Existing betas need one manual installation to acquire the updater.

The `Publish Neo update mirror` workflow runs when a stable release is published
and can be rerun manually with a tag, from the default branch only. It always
runs the deploy script from the default branch, not from the release's commit.
Its `Helium_Neo_App` environment needs:

- `HELIUM_NEO_FTP_HOST` (hostname; a pasted FTP URL without credentials or a path is also accepted)
- `HELIUM_NEO_FTP_PORT` (defaults to 21 when empty)
- `HELIUM_NEO_FTP_USERNAME`
- `HELIUM_NEO_PASSWORD`

Limit the environment's deployment branches and tags to `main` and `v*-neo`.

The FTP account is Neo's own and its login directory is the public
`/apps/helium-neo` directory; it should not reach other apps' files. Uploads and
cleanup stay relative to that directory, even when the server's filesystem root
is different. The installer's public SHA-256 check confirms the directory before
the feed is replaced.
Deployment uses explicit FTPS with certificate verification and protected data
connections. It validates the assets, uploads under a temporary name, renames,
downloads the public installer to verify SHA-256, then publishes/verifies the
backup feed. It keeps the latest five installers plus anything newer than seven
days, removes only matching Neo DMGs in its own directory, and refuses to replace
a newer feed with an older release. Neither source trees nor keys are uploaded.
The existing-feed check reads the authenticated FTP file directly, so a website's
HTML fallback for missing URLs does not block first-time deployment.

For manual deployment, the same script reads `HELIUM_NEO_FTP_HOST`,
`HELIUM_NEO_FTP_PORT`, `HELIUM_NEO_FTP_USERNAME` and `HELIUM_NEO_FTP_PASSWORD` from
its environment: `python3 devutils/macos/deploy_mirror.py '<release>'`.

For isolated updater testing, `--custom-update-server-url` replaces the feed base
and disables production fallback. An explicit `--custom-update-fallback-url`
sets its test mirror base. Both resolve `helium-neo.xml`, accept HTTPS or localhost,
and remain subject to user consent and signature validation.
