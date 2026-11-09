#!/usr/bin/env python3
"""Publish verified release bytes over explicit FTPS, then prune old installers.

The FTP login directory must be the public /apps/helium-neo directory, served at
MIRROR_BASE; the account should reach nothing else. Installers and the backup feed
are both published there. Credentials come only from HELIUM_NEO_FTP_* environment
variables; they are never printed or stored in release artifacts.
"""

import argparse
import ftplib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import ssl
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid
import xml.etree.ElementTree as ET

from make_appcast import SPARKLE, sha256_stream

INSTALLER = re.compile(r'Helium-Neo-[0-9.]+-macOS-arm64-signed\.dmg')
MIRROR_BASE = 'https://aagedal.me/apps/helium-neo/'
MIRROR_FEED_NAME = 'helium-neo.xml'
MIRROR_FEED = MIRROR_BASE + MIRROR_FEED_NAME
RELEASE_CONFIG = Path(__file__).with_name('release.json')


def ftp_endpoint(host_setting, port_setting):
    """Accept a hostname or FTP URL without passing URL syntax to DNS lookup."""
    value = host_setting.strip()
    try:
        parsed = urlsplit(value if '://' in value else '//' + value)
        if parsed.scheme not in ('', 'ftp', 'ftps') or not parsed.hostname:
            raise ValueError()
        if parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError()
        if parsed.username or parsed.password:
            raise ValueError()
        port = int(port_setting.strip()) if port_setting.strip() else (parsed.port or 21)
        if not 1 <= port <= 65535 or (parsed.port and parsed.port != port):
            raise ValueError()
        return parsed.hostname, port
    except ValueError:
        raise ValueError('HELIUM_NEO_FTP_HOST must be a hostname or FTP URL without '
                         'credentials or a directory; HELIUM_NEO_FTP_PORT must be its numeric '
                         'port.') from None


def validate_bundle(directory):
    """Validate archive bytes and both feed destinations before any upload."""
    manifest = json.loads((directory / 'update-manifest.json').read_text())
    filename = manifest['installer']
    if not INSTALLER.fullmatch(filename):
        raise ValueError('Unexpected installer filename')
    # The release assets are only as trustworthy as whoever can edit the release;
    # compare them with the reviewed configuration this script was checked out with.
    committed = json.loads(RELEASE_CONFIG.read_text(encoding='utf-8'))
    if manifest.get('sparkle_public_key') != committed['sparkle_public_key']:
        raise ValueError('Release was signed for a different updater key')
    if not re.fullmatch(r'v\d+\.\d+\.\d+\.\d+-neo', manifest.get('tag', '')):
        raise ValueError('Unexpected release tag')
    if manifest['primary_download'] != ('https://github.com/aagedal/helium/releases/download/' +
                                        manifest['tag'] + '/' + filename):
        raise ValueError('Unexpected primary download')
    archive = directory / filename
    with archive.open('rb') as stream:
        digest = sha256_stream(stream)
    if digest != manifest['sha256'] or archive.stat().st_size != manifest['bytes']:
        raise ValueError('Installer does not match the release manifest')
    for feed, url in [('helium-neo.xml', manifest['primary_download']),
                      ('helium-neo-backup.xml', manifest['backup_download'])]:
        root = ET.parse(directory / feed).getroot()
        items = root.findall('./channel/item')
        if root.tag != 'rss' or len(items) != 1:
            raise ValueError('Expected one current stable release in each feed')
        item = items[0]
        enclosure = item.find('enclosure')
        if (enclosure is None or enclosure.get('url') != url
                or enclosure.get('length') != str(manifest['bytes'])
                or enclosure.get(f'{{{SPARKLE}}}edSignature') != manifest['ed_signature']
                or item.findtext(f'{{{SPARKLE}}}version') != manifest['build']):
            raise ValueError('Appcast and release manifest disagree')
    if manifest['backup_download'] != MIRROR_BASE + filename:
        raise ValueError('Unexpected mirror destination')
    # The feed is always published to MIRROR_FEED. Releases before the move
    # name the old /apps/appcast/ location, but their feeds are identical.
    return manifest


def verify_public(url, expected_hash):
    """Download public bytes and compare them to the expected SHA-256."""
    request = Request(url, headers={'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=120) as response:
        digest = sha256_stream(response)
    if digest != expected_hash:
        raise RuntimeError('Public mirror verification failed: ' + url)


def read_existing_feed(ftp, login_directory):
    """Read the actual FTP file, avoiding websites that return HTML for missing URLs."""
    ftp.cwd(login_directory)
    names = {name.rsplit('/', 1)[-1] for name in ftp.nlst()}
    if MIRROR_FEED_NAME not in names:
        return None
    with io.BytesIO() as existing:
        ftp.retrbinary('RETR ' + MIRROR_FEED_NAME, existing.write)
        return existing.getvalue()


def check_not_older(manifest, existing_feed):
    """A rerun of an older release must never roll the mirror feed backwards."""
    if existing_feed is None:
        return
    current = ET.fromstring(existing_feed)

    def version(value):
        if not value or not re.fullmatch(r'\d+(?:\.\d+)*', value):
            raise ValueError('Mirror contains an unexpected updater version')
        return tuple(map(int, value.split('.')))

    builds = [
        version(item.findtext(f'{{{SPARKLE}}}version'))
        for item in current.findall('./channel/item')
    ]
    if builds and max(builds) > version(manifest['build']):
        raise ValueError('Refusing to overwrite a newer mirror release')


def upload_atomic(ftp, source, filename, login_directory):
    """Upload to a unique temporary name and rename only after transfer succeeds."""
    ftp.cwd(login_directory)
    temporary = filename + '.' + uuid.uuid4().hex + '.tmp'
    with source.open('rb') as stream:
        ftp.storbinary('STOR ' + temporary, stream)
    ftp.rename(temporary, filename)


def main():
    """Deploy one validated release and clean up eligible older downloads."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--retain', type=int, default=5)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if args.retain < 3:
        parser.error('Keep at least three installers')
    manifest = validate_bundle(args.directory)
    if args.validate_only:
        print('Release bundle and both feeds agree.')
        return
    ftp = ftplib.FTP_TLS(context=ssl.create_default_context(), timeout=120)
    host, port = ftp_endpoint(os.environ['HELIUM_NEO_FTP_HOST'],
                              os.environ.get('HELIUM_NEO_FTP_PORT', ''))
    ftp.connect(host, port)
    try:
        ftp.login(os.environ['HELIUM_NEO_FTP_USERNAME'], os.environ['HELIUM_NEO_FTP_PASSWORD'])
        login_directory = ftp.pwd()
        ftp.prot_p()
        check_not_older(manifest, read_existing_feed(ftp, login_directory))
        filename = manifest['installer']
        # The public check also confirms that the login directory is MIRROR_BASE
        # before the feed is replaced.
        upload_atomic(ftp, args.directory / filename, filename, login_directory)
        verify_public(manifest['backup_download'], manifest['sha256'])
        feed = args.directory / 'helium-neo-backup.xml'
        upload_atomic(ftp, feed, MIRROR_FEED_NAME, login_directory)
        verify_public(MIRROR_FEED + '?revision=' + uuid.uuid4().hex,
                      hashlib.sha256(feed.read_bytes()).hexdigest())
        # Each feed contains only the current release. Never remove that release;
        # retain at least seven days of older downloads for in-flight clients.
        ftp.cwd(login_directory)
        entries = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for listed in ftp.nlst():
            name = listed.rsplit('/', 1)[-1]
            if INSTALLER.fullmatch(name):
                timestamp = ftp.sendcmd('MDTM ' + name).split()[1]
                modified = datetime.strptime(timestamp.split('.')[0],
                                             '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
                entries.append((modified, name))
        entries.sort(reverse=True)
        for modified, name in entries[args.retain:]:
            if name != filename and modified < cutoff:
                ftp.delete(name)
                print('Removed old mirrored installer:', name)
        print('Verified backup installer and appcast published.')
    finally:
        ftp.close()


if __name__ == '__main__':
    main()
