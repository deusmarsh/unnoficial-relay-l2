"""Developer workflow boundaries: incremental rebuild, stale runtime and private data."""
import contextlib
import hashlib
import io
import json
import plistlib
import runpy
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import dev


class DeveloperChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='relay source with spaces ')
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(dev, 'ROOT', self.root)
        self.root_patch.start()
        for name in dev.NATIVE_INPUTS:
            (self.root / name).write_text('source v1')
        self.compiler = self.root / 'target-clang'
        self.compiler.write_text('compiler')
        self.value = {'mingw_clang': str(self.compiler), 'prefix': str(self.root / 'runtime/prefix')}

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def products(self, *args):
        for name in ('4gameRelay.app/Contents/MacOS/4gameRelay', '.build/NativeLauncherWindow.exe'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('binary')

    def test_changed_source_rebuilds_but_unchanged_source_does_not(self):
        with patch.object(dev, 'script', side_effect=self.products) as build, contextlib.redirect_stdout(io.StringIO()):
            dev.build(self.value)
            dev.build(self.value)
            self.assertEqual(build.call_count, 1)
            (self.root / 'NativeLauncherWindow.c').write_text('source v2')
            dev.build(self.value)
            self.assertEqual(build.call_count, 2)
            (self.root / '.build/NativeLauncherWindow.exe').unlink()
            dev.build(self.value)
            self.assertEqual(build.call_count, 3)

    def test_failed_rebuild_invalidates_success_stamp(self):
        with patch.object(dev, 'script', side_effect=self.products):
            dev.build(self.value)
        (self.root / 'SetupWizard.swift').write_text('changed')
        with patch.object(dev, 'script', side_effect=RuntimeError('compiler failed')):
            with self.assertRaisesRegex(RuntimeError, 'compiler failed'):
                dev.build(self.value)
        self.assertFalse((self.root / '.build/dev-build.sha256').exists())
        with patch.object(dev, 'script', side_effect=self.products) as build:
            dev.build(self.value)
            build.assert_called_once()

    def test_patch_change_or_missing_provenance_requires_new_runtime(self):
        patches = self.root / 'patches'
        patches.mkdir()
        for name in dev.PATCHES:
            (patches / name).write_bytes(name.encode())
        marker = self.root / 'runtime/wine-source/wine-wine-10.0/.relay-patch'
        marker.parent.mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, 'NEW dedicated directory'):
            dev.require_runtime(self.value)
        marker.write_text(hashlib.sha256(b''.join((patches / n).read_bytes() for n in dev.PATCHES)).hexdigest())
        dev.require_runtime(self.value)
        (patches / dev.PATCHES[0]).write_text('changed')
        with self.assertRaisesRegex(RuntimeError, 'NEW dedicated directory'):
            dev.require_runtime(self.value)

    def test_report_excludes_local_config_logs_and_environment(self):
        import package_source
        secret = 'private-account-value-should-never-appear'
        (self.root / 'config.local.json').write_text(secret)
        (self.root / 'private.log').write_text(secret)
        (self.root / 'README.md').write_text('public source')
        with patch.object(package_source, 'FILES', ('README.md',)), contextlib.redirect_stdout(io.StringIO()):
            dev.report()
        text = (self.root / '.build/development-report.json').read_text()
        self.assertNotIn(secret, text)
        self.assertNotIn(str(self.root), text)
        self.assertEqual(set(json.loads(text)['source_sha256']), {'README.md'})

    def test_default_native_build_does_not_generate_icons(self):
        source = Path(__file__).resolve().parent / 'build_native_frame_relay.py'
        builder = self.root / 'build_native_frame_relay.py'
        builder.write_text(source.read_text())
        def fake_tool(arguments, **kwargs):
            if '-o' in arguments:
                Path(arguments[arguments.index('-o') + 1]).write_bytes(b'compiled')
        with patch.object(sys, 'argv', [str(builder), '--relay-only']), patch.object(subprocess, 'run', side_effect=fake_tool) as commands, contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(builder), run_name='__main__')
        self.assertFalse((self.root / '.build/icons').exists())
        plist = plistlib.loads((self.root / '4gameRelay.app/Contents/Info.plist').read_bytes())
        self.assertNotIn('CFBundleIconFile', plist)
        self.assertFalse(any('iconutil' in list(map(str, c.args[0])) for c in commands.call_args_list))
        self.assertFalse(any('build_icons.swift' in str(c.args[0]) for c in commands.call_args_list))

    def test_first_launch_handoff_selects_direct_or_relay_explicitly(self):
        import start_native_frame_relay as starter
        from unittest.mock import Mock
        for name in ('run_stock_launcher.py', 'cef-direct-window.txt', 'cef-switches.txt', 'config.local.json'):
            (self.root / name).touch()
        self.products()
        for relay in (False, True):
            for finish in (False, True):
                with self.subTest(relay=relay, finish=finish):
                    opener = Mock()
                    opener.open.side_effect = lambda *a, **k: io.BytesIO(json.dumps(
                        [{'type': 'page', 'url': 'https://launcher.eu.4game.com/'}]).encode())
                    arguments = ['start_native_frame_relay.py'] + (['--relay'] if relay else []) + (['--finish-setup'] if finish else [])
                    with patch.object(starter, '__file__', str(self.root / 'start_native_frame_relay.py')), patch.object(sys, 'argv', arguments), patch.object(starter, 'build_opener', return_value=opener), patch.object(starter.subprocess, 'run') as runner, contextlib.redirect_stdout(io.StringIO()):
                        starter.main()
                    opened = runner.call_args.args[0]
                    self.assertEqual(opened[0], '/usr/bin/open')
                    self.assertEqual('--relay' in opened, relay)
                    if relay:
                        launch = runner.call_args_list[1].args[0]
                        self.assertEqual('--finish-setup' in launch, finish)
                        self.assertIn('--debug', launch)
                        self.assertIn('relay', launch)
                    else:
                        opener.open.assert_not_called()
                        self.assertEqual('--finish-setup' in opened, finish)
                        self.assertEqual(len(runner.call_args_list), 2)

    @unittest.skipUnless(sys.platform == 'darwin' and dev.os.environ.get('LINEAGE_TEST_SWIFT') == '1', 'Set LINEAGE_TEST_SWIFT=1 for the native Swift argument check')
    def test_swift_setup_preserves_custom_work_directory_with_spaces(self):
        source = Path(__file__).resolve().parent / 'AppPaths.swift'
        main = self.root / 'main.swift'
        main.write_text('''import Foundation
let path = "/tmp/relay runtime with spaces"
assert(AppPaths.sourceWorkDirectoryArguments(["app", "--setup", "--work-dir", path]) == ["--work-dir", path])
assert(AppPaths.sourceWorkDirectoryArguments(["app", "--setup"]).isEmpty)
assert(AppPaths.sourceWorkDirectoryArguments(["app", "--work-dir"]).isEmpty)
''')
        binary = self.root / 'argument-check'
        subprocess.run(['xcrun', 'swiftc', '-module-cache-path', str(self.root / 'module-cache'), str(source), str(main), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

    def test_child_environment_cannot_redirect_to_packaged_installation(self):
        with patch.dict(dev.os.environ, {'LINEAGE_DATA_DIR': '/private/account', 'LINEAGE_PACKAGED': '1'}):
            env = dev.environment()
        self.assertFalse(any(k.startswith('LINEAGE_') for k in env))


if __name__ == '__main__':
    unittest.main()
