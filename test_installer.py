"""Checks for installer boundaries; no network, Wine or account access."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('relay_installer', Path(__file__).with_name('install.py'))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

class InstallerChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def archive(self, items):
        path = self.root / 'input.tar'
        with tarfile.open(path, 'w') as archive:
            for name, link in items:
                entry = tarfile.TarInfo(name)
                if link is not None:
                    entry.type = tarfile.SYMTYPE; entry.linkname = link
                    archive.addfile(entry)
                else:
                    data = b'verified payload'; entry.size = len(data)
                    archive.addfile(entry, io.BytesIO(data))
        return path
    def test_checksum_rejects_tampered_download(self):
        path = self.root / 'asset'; path.write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'Checksum mismatch'):
            setup.verify(path, {'sha256': hashlib.sha256(b'expected').hexdigest()})
    def test_existing_verified_cache_does_not_download(self):
        path = self.root / 'asset'; path.write_bytes(b'expected')
        with patch.object(setup, 'run', side_effect=AssertionError('No download allowed')):
            self.assertEqual(setup.fetch({'file':'asset','sha256':hashlib.sha256(b'expected').hexdigest()}, self.root), path)
    def test_extract_rejects_parent_traversal(self):
        path = self.archive([('../escape',None)])
        with self.assertRaisesRegex(RuntimeError, 'Unsafe archive'):
            setup.unpack(path,self.root/'out')
        self.assertFalse((self.root/'escape').exists())
    def test_extract_rejects_escaping_symlink(self):
        path = self.archive([('link','../outside')])
        with self.assertRaisesRegex(RuntimeError, 'Unsafe archive'):
            setup.unpack(path,self.root/'out')
    def test_extract_rejects_file_under_symlink(self):
        path = self.archive([('link','inside'),('link/file',None)])
        with self.assertRaisesRegex(RuntimeError, 'nested under a symlink'):
            setup.unpack(path,self.root/'out')
    def test_extract_keeps_safe_internal_symlink(self):
        path = self.archive([('inside',None),('link','inside')])
        setup.unpack(path,self.root/'out')
        self.assertEqual((self.root/'out/link').read_bytes(),b'verified payload')
    def test_extract_refuses_unowned_nonempty_directory(self):
        path = self.archive([('file',None)])
        output = self.root/'out';output.mkdir();(output/'mine').write_text('keep')
        with self.assertRaisesRegex(RuntimeError, 'Incomplete extraction'):
            setup.unpack(path,output)
        self.assertEqual((output/'mine').read_text(),'keep')
    def test_confirmation_cannot_be_silently_accepted_without_terminal(self):
        with patch.object(setup.sys.stdin,'isatty',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'Interactive confirmation'):
                setup.confirm('Install?')
    def test_gui_confirmation_uses_button_response_without_a_terminal(self):
        with patch.object(setup,'GUI',True), patch.object(setup.sys,'stdin',io.StringIO('y\n')), contextlib.redirect_stdout(io.StringIO()) as output:
            setup.confirm('Download runtime?')
        self.assertIn('@@LINEAGE_SETUP@@',output.getvalue())
        self.assertIn('"kind": "prompt"',output.getvalue())
    def test_gui_decline_stops_setup(self):
        with patch.object(setup,'GUI',True), patch.object(setup.sys,'stdin',io.StringIO('n\n')), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError,'Cancelled'):
                setup.confirm('Download runtime?')
    def test_gui_closed_pipe_is_not_approval(self):
        with patch.object(setup,'GUI',True), patch.object(setup.sys,'stdin',io.StringIO('')), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError,'window closed'):
                setup.confirm('Download runtime?')
    def test_plan_never_changes_files_or_runs_commands(self):
        with patch.object(setup.sys,'argv',['install.py','--plan']), patch.object(setup,'run',side_effect=AssertionError('No execution allowed')), contextlib.redirect_stdout(io.StringIO()) as output:
            setup.main()
        self.assertIn('official installer',output.getvalue())

if __name__ == '__main__':
    unittest.main()
