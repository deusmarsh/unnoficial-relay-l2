"""Regression checks for direct startup, existing downloads and splash recovery."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import launcher_connection
import launcher_startup
import run_stock_launcher as runner


class LaunchChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='direct launcher with spaces ')
        self.addCleanup(self.directory.cleanup)
        self.data = Path(self.directory.name).resolve()
        self.prefix = self.data / 'prefix'
        self.install = self.prefix / 'drive_c/Program Files (x86)/Innova/4game_global'
        (self.install / 'bin').mkdir(parents=True)
        self.wine = self.data / 'wine'
        self.server = self.data / 'wineserver'
        for file in (self.wine, self.server, self.install / 'Inn.games.exe', self.install / 'bin/Launcher.exe'):
            file.touch()
        ca = patch.object(runner, 'prepare_updater_ca')
        self.ca_preparation = ca.start()
        self.addCleanup(ca.stop)
        fonts = patch.object(runner, 'prepare_game_fonts')
        self.font_preparation = fonts.start()
        self.addCleanup(fonts.stop)
        self.config = self.data / 'config.local.json'
        self.config.write_text(json.dumps(dict(prefix=str(self.prefix), wine=str(self.wine),
                                               wineserver=str(self.server), library_paths=[])))
        for name, value in [('CONFIG', self.config), ('DATA', self.data), ('HELPERS', self.data / 'no-helpers')]:
            handle = patch.object(runner, name, value)
            handle.start()
            self.addCleanup(handle.stop)

    def invoke(self, args=(), images=(), background='N', free=True):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            output = (f'LineageBackgroundApp    REG_SZ    {background}\r\n'.encode()
                      if command[1:3] == ['reg', 'query'] else b'')
            return subprocess.CompletedProcess(command, 0, output)
        with patch.object(sys, 'argv', ['runner', *args]), \
             patch.object(runner, 'running_images', return_value=set(images)), \
             patch.object(runner, 'endpoint_free', return_value=free), \
             patch.object(runner.subprocess, 'run', side_effect=run), \
             patch.object(runner.subprocess, 'Popen', return_value=SimpleNamespace(pid=123)) as launch, \
             patch.object(runner, 'finish_loading', return_value=True) as recovery, \
             contextlib.redirect_stdout(io.StringIO()):
            runner.main()
            return calls, launch, recovery

    def test_direct_default_uses_tested_switches_and_foreground_launcher(self):
        calls, launch, recovery = self.invoke()
        command = launch.call_args.args[0]
        self.assertIn('/d', command)
        self.assertEqual(command[-2:], ['/sw', r'C:\lineage-relay\cef-direct-window.txt'])
        switches = (self.prefix / 'drive_c/lineage-relay/cef-direct-window.txt').read_text().splitlines()
        self.assertEqual(switches, ['disable-gpu', 'disable-gpu-compositing',
                                  'disable-accelerated-video-decode', 'force-device-scale-factor 1', 'in-process-gpu'])
        self.assertTrue(any(cmd[1:3] == ['reg', 'add'] and cmd[-2:] == ['N', '/f'] for cmd in calls))
        self.assertFalse(any('-k' in cmd or '/T' in cmd for cmd in calls))
        self.assertEqual(launch.call_args.kwargs['env']['WINEPREFIX'], str(self.prefix))
        recovery.assert_called_once()
        self.font_preparation.assert_called_once_with(self.prefix)
        self.ca_preparation.assert_called_once_with(self.install / 'bin')

    def test_metal_setup_profile_reaches_official_launcher_environment(self):
        value = json.loads(self.config.read_text())
        value.update(runtime_profile='metal-no-audio-v1', framework_path=str(self.data / 'frameworks'))
        self.config.write_text(json.dumps(value))
        _, launch, _ = self.invoke()
        env = launch.call_args.kwargs['env']
        self.assertIn('winecoreaudio.drv=d', env['WINEDLLOVERRIDES'])
        self.assertEqual(env['MTLD3D_CONFIG'], 'color.hdr.enable=false;shader.asyncCompile=false')
        self.assertEqual(env['DYLD_FRAMEWORK_PATH'], str(self.data / 'frameworks'))

    def test_reopen_preserves_active_game_download_and_page(self):
        calls, launch, recovery = self.invoke(images=('launcher.exe', '4updater.exe', 'l2.exe'))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1:3], ['reg', 'query'])
        launch.assert_not_called()
        recovery.assert_not_called()
        self.assertFalse((self.prefix / 'drive_c/lineage-relay').exists())

    def test_restart_and_setup_handoff_refuse_live_game_or_update(self):
        for flag in ('--restart', '--finish-setup'):
            for image in ('l2.exe', '4updater.exe'):
                with self.subTest(flag=flag, image=image), self.assertRaisesRegex(RuntimeError, 'Close the game'):
                    self.invoke((flag,), images=('launcher.exe', image))

    def test_other_display_mode_requires_explicit_close(self):
        with self.assertRaisesRegex(RuntimeError, 'different launcher display'):
            self.invoke(images=('launcher.exe',), background='Y')

    def test_foreign_endpoint_is_never_used_for_recovery(self):
        with self.assertRaisesRegex(RuntimeError, '8088 is already in use'):
            self.invoke(free=False)
        self.assertFalse((self.prefix / 'drive_c/lineage-relay').exists())

    def test_relay_fallback_keeps_legacy_switches_without_direct_recovery(self):
        calls, launch, recovery = self.invoke(('--display', 'relay', '--debug'))
        self.assertEqual(launch.call_args.args[0][-2:], ['/sw', r'C:\lineage-relay\cef-switches.txt'])
        self.assertTrue(any(cmd[1:3] == ['reg', 'add'] and cmd[-2:] == ['Y', '/f'] for cmd in calls))
        self.assertNotIn('in-process-gpu', (self.prefix / 'drive_c/lineage-relay/cef-switches.txt').read_text())
        recovery.assert_not_called()

    def test_check_layout_never_runs_wine_or_writes_prefix(self):
        with patch.object(sys, 'argv', ['runner', '--check-layout']), \
             patch.object(runner.subprocess, 'run') as run, \
             patch.object(runner.subprocess, 'Popen') as launch, \
             contextlib.redirect_stdout(io.StringIO()):
            runner.main()
        run.assert_not_called()
        launch.assert_not_called()
        self.font_preparation.assert_not_called()
        self.ca_preparation.assert_not_called()
        self.assertFalse((self.data / 'logs').exists())

    def test_inherited_experiments_do_not_change_selected_runtime(self):
        with patch.dict('os.environ', {'WINEDLLOVERRIDES': 'd3d9=n', 'DXVK_HUD': 'full',
                                      'MVK_CONFIG_TRACE_VULKAN_CALLS': '1', 'VK_ICD_FILENAMES': 'foreign.json'}):
            _, launch, _ = self.invoke()
        env = launch.call_args.kwargs['env']
        self.assertNotIn('d3d9=n', env['WINEDLLOVERRIDES'])
        for key in ('DXVK_HUD', 'MVK_CONFIG_TRACE_VULKAN_CALLS', 'VK_ICD_FILENAMES'):
            self.assertNotIn(key, env)

    def test_tasklist_is_csv_parsed_and_scoped_to_configured_prefix(self):
        env = {'WINEPREFIX': str(self.prefix)}
        with patch.object(runner.subprocess, 'run', return_value=SimpleNamespace(stdout=b'"L2.exe","123","Console","1","1,024 K"\r\n')) as run:
            self.assertEqual(runner.running_images(self.wine, env), {'l2.exe'})
        self.assertEqual(run.call_args.kwargs['env'], env)


class SplashRecovery(unittest.TestCase):
    def simulate(self, path='/splash', bridge_at=10, recover=False):
        clock = SimpleNamespace(now=0)
        reloads = []
        state = SimpleNamespace(ready=False)
        def sleep(seconds): clock.now += seconds
        class Socket:
            def __init__(self, url): self.socket = SimpleNamespace(settimeout=lambda value: None)
            def call(self, method, params):
                if method == 'Page.reload':
                    reloads.append(clock.now)
                    state.ready = recover
                    return {}
                return {'result': {'value': json.dumps({'path': '/game/l2-eu/play' if state.ready else path,
                    'state': 'complete', 'bridge': 'object' if clock.now >= bridge_at else 'undefined'})}}
            def close(self): pass
        class Opener:
            def open(self, *args, **kwargs):
                return io.BytesIO(json.dumps([{'type': 'page', 'url': 'https://launcher.eu.4game.com' + path,
                    'webSocketDebuggerUrl': 'ws://127.0.0.1:8088/devtools/page/test'}]).encode())
        with patch.object(launcher_startup, 'build_opener', return_value=Opener()), \
             patch.object(launcher_startup, 'LocalWebSocket', Socket), \
             patch.object(launcher_startup.time, 'monotonic', side_effect=lambda: clock.now), \
             patch.object(launcher_startup.time, 'sleep', side_effect=sleep), \
             contextlib.redirect_stdout(io.StringIO()):
            result = launcher_startup.finish_loading()
        return result, reloads, clock.now

    def test_splash_reload_waits_for_native_bridge(self):
        result, reloads, _ = self.simulate(bridge_at=30, recover=True)
        self.assertTrue(result)
        self.assertEqual(len(reloads), 1)
        self.assertGreaterEqual(reloads[0], 38)

    def test_unresolved_splash_has_one_reload_and_a_deadline(self):
        result, reloads, elapsed = self.simulate()
        self.assertFalse(result)
        self.assertEqual(len(reloads), 1)
        self.assertLessEqual(elapsed, 90)

    def test_no_reload_without_bridge(self):
        self.assertEqual(self.simulate(bridge_at=1000)[1], [])

    def test_active_game_page_is_never_reloaded(self):
        result, reloads, _ = self.simulate(path='/game/l2-eu/play', bridge_at=0)
        self.assertTrue(result)
        self.assertEqual(reloads, [])

    def test_debug_connection_rejects_remote_or_injected_addresses(self):
        for url in ('ws://example.com:8088/page', 'ws://127.0.0.1:9999/page',
                    'wss://127.0.0.1:8088/page', 'ws://user@127.0.0.1:8088/page'):
            with self.subTest(url=url), patch.object(launcher_connection.socket, 'create_connection') as connect:
                with self.assertRaises(ValueError): launcher_connection.LocalWebSocket(url)
                connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
