"""Checks for explicit activation, verified downloads and reversible configuration."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import x87_audio
from runtime_environment import METAL_PROFILE, wine_environment


class X87AudioChecks(unittest.TestCase):
    def config(self):
        return dict(prefix='/tmp/isolated', library_paths=['/tmp/lib'],
                    framework_path='/tmp/frameworks', runtime_profile=METAL_PROFILE)

    def test_opt_in_enables_audio_and_only_verified_sidecar(self):
        with tempfile.TemporaryDirectory() as folder:
            sidecar = Path(folder) / 'sidecar'; sidecar.write_bytes(b'verified'); sidecar.chmod(0o755)
            item = {'binary_sha256': hashlib.sha256(b'verified').hexdigest()}
            config = self.config(); config['x87_audio'] = {'sidecar': str(sidecar)}
            with patch.object(x87_audio, 'dependency', return_value=item), patch.dict(os.environ, {
                'ROSETTA_X87_PATH': '/foreign', 'X87_DISABLE_HOOK': '1', 'X87_ENABLE_FMA_CONTRACT': '1'}):
                env = wine_environment(config)
                self.assertEqual(env['ROSETTA_X87_PATH'], str(sidecar.resolve()))
                self.assertNotIn('winecoreaudio.drv=d', env['WINEDLLOVERRIDES'])
                self.assertNotIn('X87_DISABLE_HOOK', env)
                self.assertNotIn('X87_ENABLE_FMA_CONTRACT', env)
                sidecar.write_bytes(b'tampered')
                with self.assertRaisesRegex(RuntimeError, 'missing or changed'):
                    wine_environment(config)

    def test_legacy_default_and_unknown_modes_do_not_silently_enable_x87(self):
        config = self.config()
        self.assertIn('winecoreaudio.drv=d', wine_environment(config)['WINEDLLOVERRIDES'])
        config['x87_audio'] = False
        with self.assertRaisesRegex(RuntimeError, 'Invalid'):
            wine_environment(config)
        config.pop('runtime_profile')
        with self.assertRaisesRegex(RuntimeError, 'requires'):
            wine_environment(config)

    def test_archive_links_cannot_replace_sidecar(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); archive = root / 'sidecar.tar.xz'
            with tarfile.open(archive, 'w:xz') as bundle:
                item = tarfile.TarInfo('x87sidecar'); item.type = tarfile.SYMTYPE; item.linkname = '/foreign'
                bundle.addfile(item)
            dep = {'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
            with patch.object(x87_audio, 'dependency', return_value=dep):
                with self.assertRaisesRegex(RuntimeError, 'archive layout'):
                    x87_audio.unpack_sidecar(archive, root / 'binary')
            self.assertFalse((root / 'binary').exists())

    def test_configuration_backup_and_concurrent_edit_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); config = root / 'config.local.json'
            before = b'{"original":true}'; config.write_bytes(before)
            x87_audio.save(config, before, {'updated': True})
            backups = list((root / '.build/x87-audio-backups').glob('*.json'))
            self.assertEqual(backups[0].read_bytes(), before)
            self.assertEqual(json.loads(config.read_text()), {'updated': True})
            with self.assertRaisesRegex(RuntimeError, 'changed during'):
                x87_audio.save(config, before, {'unexpected': True})

    def test_failed_hardware_check_never_activates_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); config = self.config()
            config.update(prefix=str(root / 'prefix'), wine=str(root / 'engine/bin/wine'))
            path = root / 'config.local.json'; path.write_text(json.dumps(config))
            before = path.read_bytes()
            ntdll = root / 'engine/lib/wine/x86_64-unix/ntdll.so'
            ntdll.parent.mkdir(parents=True); ntdll.write_bytes(b'ROSETTA_X87_PATH')
            with patch.object(x87_audio, 'stopped'), patch('dev.require_runtime'), \
                 patch.object(x87_audio, 'unpack_sidecar'), \
                 patch.object(x87_audio, 'validate', side_effect=RuntimeError('unsupported Rosetta')):
                with self.assertRaisesRegex(RuntimeError, 'unsupported Rosetta'):
                    x87_audio.activate(path, archive=root / 'cached.tar.xz')
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
