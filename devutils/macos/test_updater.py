#!/usr/bin/env python3
"""Exercise the real browser updater against isolated localhost feeds.

Use a disposable signed app with a lower CFBundleVersion for download tests.
All browser profiles and update endpoints are isolated from production.
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import plistlib
import socket
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from make_appcast import SPARKLE


def free_port():
    """Choose an available loopback port for an isolated test service."""
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def webdriver(base, method, path, payload=None):
    """Make a WebDriver request and fail on protocol errors."""
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(base + path,
                      data=data,
                      method=method,
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=120) as response:
        result = json.load(response)['value']
    if isinstance(result, dict) and 'error' in result:
        raise RuntimeError(result)
    return result


def stop_test_processes(directory):
    """Stop only processes launched from this test's unique disposable directory."""
    if directory is None:
        return
    processes = subprocess.check_output(['ps', '-axo', 'pid=,command='], text=True)
    prefixes = (str(directory) + '/', str(directory.resolve()) + '/')
    for line in processes.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) == 2 and any(prefix in fields[1] for prefix in prefixes):
            try:
                os.kill(int(fields[0]), signal.SIGTERM)
            except ProcessLookupError:
                pass


def main(): # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Drive a disposable signed app through a real Sparkle update scenario."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--chromedriver', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--identity', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--scenario',
                        choices=[
                            'current', 'feed-fallback', 'download-fallback', 'slow-primary',
                            'both-down', 'bad-signature', 'disabled', 'no-consent'
                        ],
                        required=True)
    args = parser.parse_args()
    manifest = json.loads((args.release / 'update-manifest.json').read_text())
    archive = args.release / manifest['installer']
    installer_paths = ('/primary/' + archive.name, '/backup/' + archive.name)
    requests = []
    http_port = free_port()
    origin = 'http://127.0.0.1:' + str(http_port)

    class Handler(BaseHTTPRequestHandler):
        """Serve the selected failure scenario and record updater traffic."""

        def log_message(self, *unused):
            pass

        def send_installer(self, primary):
            """Serve the installer or a byte range of it, throttling a slow primary."""
            size = archive.stat().st_size
            start, end = 0, size - 1
            ranged = self.headers.get('Range', '')
            if ranged.startswith('bytes='):
                first, _, last = ranged[len('bytes='):].partition('-')
                start = int(first or 0)
                end = min(int(last), size - 1) if last else size - 1
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            else:
                self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(end - start + 1))
            self.end_headers()
            slow = primary and args.scenario == 'slow-primary'
            block_size = 16 * 1024 if slow else 1024 * 1024
            try:
                with archive.open('rb') as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining > 0 and (block := stream.read(min(block_size, remaining))):
                        self.wfile.write(block)
                        remaining -= len(block)
                        if slow:
                            time.sleep(.25)  # About 64 KB/s.
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self): # pylint: disable=invalid-name
            """Serve an appcast or signed installer, injecting the requested failure."""
            path = self.path.split('?')[0]
            # Mark the updater's short speed measurements apart from downloads.
            requests.append(path + (' (range)' if 'Range' in self.headers else ''))
            print('Updater request:', requests[-1], flush=True)
            primary = path.startswith('/primary/')
            if args.scenario == 'both-down' or (primary and args.scenario == 'feed-fallback'):
                self.send_error(503)
                return
            if path.endswith('/helium-neo.xml'):
                root = ET.parse(args.release / 'helium-neo.xml').getroot()
                item = root.find('./channel/item')
                enclosure = item.find('enclosure')
                # Like production, both hosts serve the installer under the same name.
                enclosure.set(
                    'url', origin + ('/primary/' if primary else '/backup/') +
                    ('missing.dmg' if primary and args.scenario == 'download-fallback' else
                     archive.name))
                if args.scenario == 'bad-signature':
                    enclosure.set(f'{{{SPARKLE}}}edSignature', 'A' * 86 + '==')
                data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                self.send_response(200)
                self.send_header('Content-Type', 'application/rss+xml')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path in installer_paths:
                self.send_installer(primary)
            else:
                self.send_error(404)

    server = ThreadingHTTPServer(('127.0.0.1', http_port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = {}
    succeeded = False
    root = None
    defaults_domain = 'no.aagedal.helium-neo.update-test.' + uuid.uuid4().hex
    try:
        with tempfile.TemporaryDirectory(prefix='neo-updater-test-') as temporary:
            root = Path(temporary)
            test_app = root / args.app.name
            subprocess.run(['ditto', str(args.app), str(test_app)], check=True)
            needs_update = args.scenario in ('feed-fallback', 'download-fallback', 'slow-primary',
                                             'bad-signature')
            info_path = test_app / 'Contents/Info.plist'
            with info_path.open('rb') as stream:
                info = plistlib.load(stream)
            info['SUDefaultsDomain'] = defaults_domain
            if needs_update:
                parts = manifest['build'].split('.')
                parts[-1] = str(int(parts[-1]) - 1)
                info['CFBundleVersion'] = '.'.join(parts)
            with info_path.open('wb') as stream:
                plistlib.dump(info, stream)
            subprocess.run([
                'codesign', '--force', '--timestamp', '--sign', args.identity, '--options',
                'restrict,kill,library,runtime', '--entitlements',
                str(args.source / 'chrome/app/app-entitlements.plist'),
                str(test_app)
            ],
                           check=True)
            profile = root / 'profile'
            (profile / 'Default').mkdir(parents=True)
            (profile / 'Default/Preferences').write_text(
                json.dumps({
                    'helium': {
                        'completed_onboarding': True,
                        'services': {
                            'enabled': True,
                            'user_consented': args.scenario != 'no-consent',
                            'schema_version': 999,
                            'browser_updates': args.scenario != 'disabled',
                            'ext_proxy': False,
                            'bangs': False,
                            'spellcheck_files': False,
                            'ublock_assets': False,
                        }
                    },
                }))
            port = free_port()
            base = 'http://127.0.0.1:' + str(port)
            with (args.report.with_suffix('.driver.log')).open('w') as log:
                driver = subprocess.Popen( # pylint: disable=consider-using-with
                    [str(args.chromedriver), '--port=' + str(port)],
                    stdout=log,
                    stderr=log)
                session = None
                try:
                    for _ in range(100):
                        try:
                            webdriver(base, 'GET', '/status')
                            break
                        except OSError:
                            time.sleep(.1)
                    session = webdriver(
                        base, 'POST', '/session', {
                            'capabilities': {
                                'alwaysMatch': {
                                    'browserName': 'chrome',
                                    'goog:chromeOptions': {
                                        'binary': str(test_app / 'Contents/MacOS/Helium Neo'),
                                        'args': [
                                            '--enable-logging=stderr', '--no-first-run',
                                            '--no-default-browser-check', '--use-mock-keychain',
                                            '--user-data-dir=' + str(profile),
                                            '--custom-update-server-url=' + origin + '/primary/',
                                            '--custom-update-fallback-url=' + origin + '/backup/'
                                        ],
                                    },
                                }
                            }
                        })['sessionId']
                    route = '/session/' + session
                    webdriver(base, 'POST', route + '/url', {'url': 'chrome://settings/help'})
                    webdriver(
                        base, 'POST', route + '/execute/async', {
                            'script': '''
                        const done = arguments[arguments.length - 1];
                        import('chrome://resources/js/cr.js').then(({addWebUiListener}) => {
                          window.neoUpdateStatuses = [];
                          addWebUiListener('update-status-changed', e => window.neoUpdateStatuses.push(e));
                          chrome.send('refreshUpdateStatus'); done(true);
                        }).catch(e => done(String(e)));
                    ''',
                            'args': []
                        })
                    expected = {
                        'current': 'updated',
                        'feed-fallback': 'nearly_updated',
                        'download-fallback': 'nearly_updated',
                        'slow-primary': 'nearly_updated',
                        'both-down': 'failed',
                        'bad-signature': 'failed',
                        'disabled': 'disabled',
                        'no-consent': 'disabled'
                    }[args.scenario]
                    deadline = time.monotonic() + 150
                    while time.monotonic() < deadline:
                        statuses = webdriver(base, 'POST', route + '/execute/sync', {
                            'script': 'return window.neoUpdateStatuses || []',
                            'args': []
                        })
                        if any(s.get('status') == expected for s in statuses):
                            break
                        time.sleep(.5)
                    else:
                        raise AssertionError('Expected ' + expected + '; got ' + repr(statuses) +
                                             '; requests ' + repr(requests))
                    if args.scenario in ('feed-fallback', 'download-fallback', 'both-down'):
                        assert 1 <= requests.count('/backup/helium-neo.xml') <= requests.count(
                            '/primary/helium-neo.xml'), requests
                    else:
                        assert '/backup/helium-neo.xml' not in requests, requests
                    if args.scenario == 'slow-primary':
                        # Measured both hosts, then downloaded only from the faster mirror.
                        assert installer_paths[0] + ' (range)' in requests, requests
                        assert installer_paths[1] + ' (range)' in requests, requests
                        assert installer_paths[1] in requests, requests
                        assert installer_paths[0] not in requests, requests
                    if args.scenario in ('disabled', 'no-consent'):
                        assert not requests, requests
                    else:
                        assert '/primary/helium-neo.xml' in requests, requests
                    results = {
                        'scenario': args.scenario,
                        'passed': True,
                        'requests': list(requests),
                        'statuses': statuses
                    }
                finally:
                    if session:
                        try:
                            webdriver(base, 'DELETE', '/session/' + session)
                        except OSError:
                            pass
                    driver.terminate()
                    driver.wait(timeout=20)
                if args.scenario in ('feed-fallback', 'download-fallback', 'slow-primary'):
                    deadline = time.monotonic() + 60
                    while time.monotonic() < deadline:
                        try:
                            with (test_app / 'Contents/Info.plist').open('rb') as stream:
                                installed = plistlib.load(stream)['CFBundleVersion']
                            if installed == manifest['build']:
                                break
                        except FileNotFoundError:
                            pass
                        time.sleep(.5)
                    else:
                        raise AssertionError('Downloaded update was not installed on quit')
                    subprocess.run(['codesign', '--verify', '--deep', '--strict',
                                    str(test_app)],
                                   check=True)
                    results['installed_build'] = installed
                    results['installed_signature_valid'] = True
                succeeded = True
    finally:
        server.shutdown()
        stop_test_processes(root)
        subprocess.run(['defaults', 'delete', defaults_domain],
                       check=False,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        if not results:
            results = {'scenario': args.scenario, 'requests': requests}
        results['passed'] = succeeded
        args.report.write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
