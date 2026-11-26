"""Check reproducible profile selection, stale provenance and prefix boundaries."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import dev
import install
import metal_runtime
import material_fix
import x87_audio
from runtime_environment import wine_environment, METAL_PROFILE


class MetalRuntimeChecks(unittest.TestCase):
    def config(self):
        return dict(prefix='/tmp/isolated prefix', library_paths=['/tmp/runtime/lib'],
                    framework_path='/tmp/runtime/frameworks', runtime_profile=METAL_PROFILE)

    def test_inherited_graphics_and_audio_settings_cannot_override_profile(self):
        with patch.dict(os.environ, {'WINEDLLOVERRIDES': 'winecoreaudio.drv=b;d3d9=b',
                                     'MTLD3D_CONFIG': 'shader.asyncCompile=true',
                                     'DYLD_FRAMEWORK_PATH': '/foreign', 'MTL_HUD_ENABLED': '1',
                                     'FEX_TEST': '1'}):
            env = wine_environment(self.config())
        self.assertIn('winecoreaudio.drv=d', env['WINEDLLOVERRIDES'])
        self.assertNotIn('d3d9=b', env['WINEDLLOVERRIDES'])
        self.assertEqual(env['DYLD_FRAMEWORK_PATH'], str(Path('/tmp/runtime/frameworks').resolve()))
        self.assertEqual(env['MTLD3D_CONFIG'], 'color.hdr.enable=false;shader.asyncCompile=false')
        self.assertNotIn('MTL_HUD_ENABLED', env)
        self.assertNotIn('FEX_TEST', env)

    def test_existing_legacy_configuration_keeps_audio_and_renderer(self):
        config = self.config(); config.pop('runtime_profile')
        env = wine_environment(config)
        self.assertNotIn('winecoreaudio', env['WINEDLLOVERRIDES'])
        self.assertNotIn('MTLD3D_CONFIG', env)
        config['runtime_profile'] = 'unsupported'
        with self.assertRaisesRegex(RuntimeError, 'Unknown runtime'):
            wine_environment(config)

    def test_changed_dependency_or_patch_invalidates_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root/'patches').mkdir()
            for name in metal_runtime.PATCHES: (root/'patches'/name).write_text(name)
            manifest = {name: {'sha256': name} for name in metal_runtime.DEPENDENCIES}
            (root/'dependencies.json').write_text(json.dumps(manifest))
            (root/'runtime').mkdir()
            value = self.config(); value['prefix'] = str(root/'runtime/prefix')
            value['runtime_identity'] = metal_runtime.identity(root, manifest)
            stamp = root/'runtime/.metal-runtime-identity'
            stamp.write_text(value['runtime_identity'])
            with patch.object(dev, 'ROOT', root):
                self.assertTrue(dev.runtime_matches(value))
                manifest['metal_renderer']['sha256'] = 'changed'
                (root/'dependencies.json').write_text(json.dumps(manifest))
                self.assertFalse(dev.runtime_matches(value))

    def test_default_build_selects_both_fixes_and_verifies_cached_renderer(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder).resolve()
            config = dict(self.config(), wine=str(work/'stock/bin/wine'),
                          wineserver=str(work/'stock/bin/wineserver'), runtime_identity='baseline')
            archive = work / 'rustup-init'
            archive.touch()
            archives = dict(rustup_init=archive, x87_sidecar=work/'sidecar.tar',
                            metal_renderer_source=work/'source.tar')
            def install_copy(config, runtime, library):
                dest = runtime/'lib/wine/x86_64-unix/mtld3d.so'
                dest.parent.mkdir(parents=True)
                dest.write_bytes(b'patched shader')
                return dest
            with patch.object(x87_audio, 'unpack_sidecar'), patch.object(x87_audio, 'verified_sidecar'), \
                 patch.object(install, 'run'), patch.object(material_fix, 'build_library') as build, \
                 patch.object(material_fix, 'install_library', side_effect=install_copy):
                result = metal_runtime.source_defaults(work, config, archives, install)
                self.assertEqual(result['prefix'], config['prefix'])
                self.assertEqual(result['material_fix']['previous_runtime']['wine'], config['wine'])
                self.assertIn('x87_audio', result)
                self.assertEqual(metal_runtime.source_defaults(work, config, archives, install), result)
                build.assert_called_once()
                native = Path(result['wine']).parents[1]/'lib/wine/x86_64-unix/mtld3d.so'
                native.write_bytes(b'unexpected renderer')
                with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                    metal_runtime.source_defaults(work, config, archives, install)

    def test_metal_preparation_refuses_legacy_prefix_before_any_change(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder); (work / 'prefix').mkdir()
            with patch.object(metal_runtime, 'identity', return_value='expected'), patch.object(install, 'unpack') as unpack:
                with self.assertRaisesRegex(RuntimeError, 'older prefix'):
                    metal_runtime.prepare(work, {}, 1, install)
            unpack.assert_not_called()
            self.assertFalse((work / '.metal-runtime-identity').exists())

    def test_renderer_refuses_unowned_prefix_without_running_wine(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self.config(); config['prefix'] = folder
            with patch.object(install, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'unowned'):
                    metal_runtime.install_prefix(config, install)
            run.assert_not_called()

    def test_prefix_renderer_is_scoped_to_both_game_executables(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prefix = root/'prefix'; prefix.mkdir()
            (prefix/install.MARKER).touch()
            renderer = root/'renderer'
            for arch, system in [('i386-windows','syswow64'),('x86_64-windows','system32')]:
                (renderer/'native'/arch).mkdir(parents=True)
                (renderer/'native'/arch/'d3d9.dll').write_bytes(arch.encode())
                (renderer/'prefix-markers'/system).mkdir(parents=True)
                (renderer/'prefix-markers'/system/'mtld3d.dll').write_bytes(b'marker')
                (prefix/'drive_c/windows'/system).mkdir(parents=True)
            config = self.config(); config.update(prefix=str(prefix), metal_renderer_dir=str(renderer), wine='wine')
            with patch.object(install, 'run') as run:
                metal_runtime.install_prefix(config, install)
            self.assertEqual(run.call_count, 2)
            for call, exe in zip(run.call_args_list, ('L2.exe','L2.bin')):
                self.assertIn('AppDefaults\\'+exe+'\\DllOverrides', call.args[0][3])
                self.assertEqual(call.kwargs['env']['WINEPREFIX'], str(prefix.resolve()))
                self.assertIn('native,builtin', call.args[0])
            self.assertEqual((prefix/'drive_c/windows/syswow64/d3d9.dll').read_bytes(), b'i386-windows')


if __name__ == '__main__':
    unittest.main()
