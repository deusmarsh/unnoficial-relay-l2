"""Offline regression checks for updater extraction and pinned CA repair."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import prepare_updater_ca as repair


class UpdaterCAChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name) / 'app'
        self.app.mkdir()

    def assembly(self, extra=None):
        content = {name: ('publisher-' + name).encode() for name in repair.UPDATER_FILES}
        content['rootcert.ca'] = b'original CA content\n'
        content.update(extra or {})
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
            for name, data in content.items():
                output.writestr(name, data)
        (self.app / 'Launcher.Updater.Core.dll').write_bytes(b'assembly-prefix' + archive.getvalue() + b'other-resource')
        return content

    def test_fresh_lazy_extraction_prepared_before_publisher_runs(self):
        payload = self.assembly()
        ca = repair.prepare_updater_ca(self.app)
        self.assertTrue(ca.read_bytes().startswith(payload['rootcert.ca']))
        self.assertIn(repair.ROOT_CA.read_bytes(), ca.read_bytes())
        for name in ('4updater.exe', '4updater.properties'):
            self.assertEqual((ca.parent / name).read_bytes(), payload[name])

    def test_existing_updater_preserved_and_repeat_does_not_rewrite(self):
        self.assembly()
        ca = repair.prepare_updater_ca(self.app)
        executable = ca.parent / '4updater.exe'
        executable.write_bytes(b'existing updated executable')
        ca.write_bytes(ca.read_bytes() + b'\nlocal extra CA content\n')
        before = ca.read_bytes()
        with patch.object(repair, 'atomic_write', side_effect=AssertionError('No rewrite expected')):
            repair.prepare_updater_ca(self.app)
        self.assertEqual(ca.read_bytes(), before)
        self.assertEqual(executable.read_bytes(), b'existing updated executable')

    def test_existing_ca_extended_without_extracting_binaries(self):
        updater = self.app / 'forgameUpdater'
        updater.mkdir()
        (updater / '4updater.exe').write_bytes(b'keep')
        (updater / 'rootcert.ca').write_bytes(b'keep original roots\n')
        ca = repair.prepare_updater_ca(self.app)
        self.assertTrue(ca.read_bytes().startswith(b'keep original roots\n'))
        self.assertEqual((updater / '4updater.exe').read_bytes(), b'keep')

    def test_changed_bundled_certificate_fails_before_extraction(self):
        self.assembly()
        fake = self.app / 'changed.pem'
        fake.write_bytes(b'not the pinned certificate')
        with patch.object(repair, 'ROOT_CA', fake), self.assertRaisesRegex(RuntimeError, 'fingerprint'):
            repair.prepare_updater_ca(self.app)
        self.assertFalse((self.app / 'forgameUpdater').exists())

    def test_unexpected_archive_paths_rejected_before_writes(self):
        self.assembly({'../escape': b'bad'})
        with self.assertRaisesRegex(RuntimeError, 'Unexpected'):
            repair.prepare_updater_ca(self.app)
        self.assertFalse((self.app / 'forgameUpdater').exists())

    def test_linked_directory_and_ca_are_refused(self):
        self.assembly()
        outside = self.app.parent / 'outside'
        outside.mkdir()
        updater = self.app / 'forgameUpdater'
        updater.symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, 'linked updater directory'):
            repair.prepare_updater_ca(self.app)
        self.assertEqual(list(outside.iterdir()), [])
        updater.unlink()
        updater.mkdir()
        (updater / '4updater.exe').write_bytes(b'existing')
        target = outside / 'keep.ca'
        target.write_bytes(b'keep')
        (updater / 'rootcert.ca').symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, 'linked updater CA'):
            repair.prepare_updater_ca(self.app)
        self.assertEqual(target.read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
