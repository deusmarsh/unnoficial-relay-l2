"""Verify the renderer boundary, rollback and source provenance checks."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import material_fix
from runtime_environment import METAL_PROFILE


class MaterialFixChecks(unittest.TestCase):
    def test_candidate_preserves_audio_prefix_and_original_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); old = root / 'old'; new = root / 'new'
            native = new / 'lib/wine/x86_64-unix/mtld3d.so'
            native.parent.mkdir(parents=True); native.write_bytes(b'fixed')
            config = dict(wine=str(old / 'bin/wine'), wineserver=str(old / 'bin/wineserver'),
                          library_paths=[str(old / 'lib'), str(root / 'support')],
                          prefix=str(root / 'prefix'), x87_audio={'sidecar': 'kept'})
            result = material_fix.candidate(config, new, native)
            self.assertEqual(result['prefix'], config['prefix'])
            self.assertEqual(result['x87_audio'], config['x87_audio'])
            self.assertEqual(result['library_paths'], [str(new / 'lib'), str(root / 'support')])
            self.assertNotIn('material_fix', config)
            material_fix.verify_renderer(result)
            native.write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError, 'missing or changed'):
                material_fix.verify_renderer(result)

    def test_patch_drift_is_rejected_before_renderer_use(self):
        with self.assertRaisesRegex(RuntimeError, 'provenance changed'):
            material_fix.verify_renderer({'material_fix': {'patch_sha256': 'old'}})

    def test_legacy_runtime_is_refused_before_any_process_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'; path.write_text('{}')
            with patch('x87_audio.stopped') as stopped:
                with self.assertRaisesRegex(RuntimeError, 'existing Metal'):
                    material_fix.activate(path, Path(folder) / 'work', None)
            stopped.assert_not_called()

    def test_disable_can_restore_missing_renderer_and_preserves_x87(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'
            previous = {'wine': '/old/bin/wine', 'wineserver': '/old/bin/wineserver',
                        'library_paths': ['/old/lib']}
            config = dict(runtime_profile=METAL_PROFILE, wine='/missing/bin/wine',
                          prefix='/same/prefix', x87_audio={'sidecar': 'kept'},
                          material_fix={'previous_runtime': previous})
            path.write_text(json.dumps(config))
            with patch('x87_audio.stopped') as stopped:
                material_fix.activate(path, Path(folder) / 'work', None, disable=True)
                self.assertNotIn('material_fix', stopped.call_args.args[0])
            result = json.loads(path.read_text())
            self.assertEqual(result['wine'], previous['wine'])
            self.assertEqual(result['x87_audio'], config['x87_audio'])
            self.assertNotIn('material_fix', result)


if __name__ == '__main__':
    unittest.main()
