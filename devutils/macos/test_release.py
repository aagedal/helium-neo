#!/usr/bin/env python3
"""Checks release/feed integrity and the mirror's rollback protection."""

# pylint: disable=missing-function-docstring,consider-using-with

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, call
import xml.etree.ElementTree as ET

from deploy_mirror import (check_not_older, ftp_endpoint, read_existing_feed, upload_atomic,
                           validate_bundle)
from make_appcast import make_feed


class ReleaseTests(unittest.TestCase):
    """Deployment must reject corrupted or misdirected release bundles."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = json.loads(
            Path(__file__).with_name('release.json').read_text(encoding='utf-8'))
        self.archive = self.root / ('Helium-Neo-' + self.config['version'] +
                                    '-macOS-arm64-signed.dmg')
        self.archive.write_bytes(b'installer fixture')
        self.manifest = {
            **self.config,
            'installer': self.archive.name,
            'bytes': self.archive.stat().st_size,
            'sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest(),
            'ed_signature': 'signature fixture',
            'primary_download': 'https://github.com/aagedal/helium/releases/download/' +
            self.config['tag'] + '/' + self.archive.name,
            'backup_download': self.config['backup_download_base'] + self.archive.name,
        }
        self.write_bundle()

    def write_bundle(self):
        (self.root / 'update-manifest.json').write_text(json.dumps(self.manifest))
        for name, url in [('helium-neo.xml', self.manifest['primary_download']),
                          ('helium-neo-backup.xml', self.manifest['backup_download'])]:
            (self.root / name).write_bytes(
                make_feed(self.config, self.archive, self.manifest['ed_signature'], url,
                          'Sat, 17 Oct 2026 00:00:00 +0000'))

    def test_same_signed_archive_on_both_hosts(self):
        self.assertEqual(validate_bundle(self.root), self.manifest)

    def test_release_from_before_the_feed_move_is_accepted(self):
        self.manifest['backup_feed'] = 'https://aagedal.me/apps/appcast/helium-neo.xml'
        self.write_bundle()
        self.assertEqual(validate_bundle(self.root), self.manifest)

    def test_unexpected_updater_key_rejected(self):
        self.manifest['sparkle_public_key'] = 'AAAA' + self.config['sparkle_public_key'][4:]
        self.write_bundle()
        with self.assertRaisesRegex(ValueError, 'key'):
            validate_bundle(self.root)

    def test_unexpected_primary_download_rejected(self):
        self.manifest['primary_download'] = 'https://example.com/' + self.archive.name
        self.write_bundle()
        with self.assertRaisesRegex(ValueError, 'primary'):
            validate_bundle(self.root)

    def test_modified_archive_rejected_before_upload(self):
        self.archive.write_bytes(b'corrupted installer')
        with self.assertRaisesRegex(ValueError, 'manifest'):
            validate_bundle(self.root)

    def test_backup_pointing_at_github_rejected(self):
        (self.root / 'helium-neo-backup.xml').write_bytes(
            (self.root / 'helium-neo.xml').read_bytes())
        with self.assertRaisesRegex(ValueError, 'disagree'):
            validate_bundle(self.root)

    def test_changed_signature_rejected(self):
        feed = self.root / 'helium-neo.xml'
        feed.write_text(
            feed.read_text(encoding='utf-8').replace('signature fixture', 'wrong signature'))
        with self.assertRaisesRegex(ValueError, 'disagree'):
            validate_bundle(self.root)

    def test_path_traversal_rejected(self):
        self.manifest['installer'] = '../unrelated.dmg'
        self.write_bundle()
        with self.assertRaisesRegex(ValueError, 'filename'):
            validate_bundle(self.root)

    def test_old_release_cannot_replace_newer_feed(self):
        newer = {**self.config, 'build': '99999999.1'}
        feed = make_feed(newer, self.archive, 'signature', self.manifest['backup_download'], 'now')
        with self.assertRaisesRegex(ValueError, 'newer'):
            check_not_older(self.manifest, feed)

    def test_same_release_can_be_retried(self):
        feed = (self.root / 'helium-neo-backup.xml').read_bytes()
        check_not_older(self.manifest, feed)

    def test_first_deployment_has_no_existing_feed(self):
        ftp = Mock()
        ftp.nlst.return_value = ['Helium-Neo-0.21.1.1-macOS-arm64-signed.dmg']
        self.assertIsNone(read_existing_feed(ftp, '/hosting/www/apps/helium-neo'))
        ftp.retrbinary.assert_not_called()
        check_not_older(self.manifest, None)

    def test_existing_feed_is_read_from_ftp(self):
        ftp = Mock()
        ftp.nlst.return_value = ['helium-neo.xml']
        feed = (self.root / 'helium-neo-backup.xml').read_bytes()
        ftp.retrbinary.side_effect = lambda command, callback: callback(feed)
        self.assertEqual(read_existing_feed(ftp, '/hosting/www/apps/helium-neo'), feed)

    def test_invalid_existing_feed_still_blocks_deployment(self):
        with self.assertRaises(ET.ParseError):
            check_not_older(self.manifest, b'<html>invalid feed')

    def test_upload_uses_login_directory_instead_of_server_root(self):
        ftp = Mock()
        upload_atomic(ftp, self.archive, self.archive.name, '/hosting/www/apps/helium-neo')
        self.assertEqual(ftp.cwd.call_args_list, [call('/hosting/www/apps/helium-neo')])
        ftp.mkd.assert_not_called()

    def test_ftp_host_formats_are_normalized(self):
        for host in [
                'ftp.example.com', ' ftp.example.com\n', 'ftp://ftp.example.com',
                'ftps://ftp.example.com:21/', 'ftp.example.com:21'
        ]:
            with self.subTest(host=host):
                self.assertEqual(ftp_endpoint(host, '21'), ('ftp.example.com', 21))

    def test_ambiguous_ftp_settings_are_rejected(self):
        for host in [
                'ftp://user:password@ftp.example.com', 'ftp://ftp.example.com/apps',
                'ftp.example.com:990'
        ]:
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, 'HELIUM_NEO_FTP_HOST'):
                    ftp_endpoint(host, '21')


if __name__ == '__main__':
    unittest.main()
