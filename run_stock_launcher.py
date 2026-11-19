#!/usr/bin/env python3
"""Open the official launcher directly in Wine, with an optional frame relay."""
import argparse
import csv
import fcntl
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

from app_paths import DATA, CONFIG, HELPERS
from launcher_startup import finish_loading
from prepare_game_fonts import prepare_game_fonts
from prepare_updater_ca import prepare_updater_ca

BACKGROUND_KEY = r'HKCU\Software\Wine\AppDefaults\Launcher.exe\Mac Driver'


def running_images(host, env):
    result = subprocess.run([str(host), 'tasklist', '/FO', 'CSV', '/NH'], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
    return {row[0].lstrip('\ufeff').lower() for row in
            csv.reader(result.stdout.decode(errors='replace').splitlines()) if row}


def endpoint_free():
    """Do not connect recovery or the relay to another prefix's authenticated page."""
    try:
        with socket.create_connection(('127.0.0.1', 8088), timeout=1):
            return False
    except ConnectionRefusedError:
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--display', choices=('direct', 'relay'), default='direct')
    parser.add_argument('--restart', action='store_true', help='Restart only this prefix launcher; refuses while a game or updater runs.')
    parser.add_argument('--check-layout', action='store_true')
    parser.add_argument('--finish-setup', action='store_true', help='Reconnect the installer-opened launcher using the selected display mode.')
    parser.add_argument('--debug', action='store_true', help='Enable the local diagnostic endpoint in relay mode (always enabled for direct startup recovery).')
    parser.add_argument('--switch-file', type=Path, help='Optional official /sw file for a rendering experiment.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if not CONFIG.is_file():
        parser.error('Create config.local.json using config.example.json first.')
    config = json.loads(CONFIG.read_text())
    prefix = Path(config['prefix']).expanduser().resolve()
    install = prefix / 'drive_c/Program Files (x86)/Innova/4game_global'
    host = Path(config['wine']).expanduser().resolve()
    server = Path(config['wineserver']).expanduser().resolve()
    direct = args.display == 'direct'
    switch = (args.switch_file or root / ('cef-direct-window.txt' if direct else 'cef-switches.txt')).resolve(strict=True)
    # The single-file runner reassembles arguments without quoting. Use a Windows
    # path with no spaces, even when the configured prefix has spaces in its path.
    switch_name = 'cef-direct-window.txt' if direct else 'cef-switches.txt'
    command = [str(host), str(install / 'Inn.games.exe'), '/e', 'prod', '/l', 'en-US']
    if direct or args.debug:
        command.append('/d')
    command += ['/sw', 'C:\\lineage-relay\\' + switch_name]
    for file in (host, server, install / 'Inn.games.exe', install / 'bin/Launcher.exe'):
        if not file.is_file():
            parser.error(f'Missing file: {file}')
    if args.check_layout:
        print(json.dumps({'display': args.display, 'command': command, 'cwd': str(install), 'prefix': str(prefix)}, indent=2))
        return
    logs = DATA / 'logs'
    logs.mkdir(exist_ok=True, mode=0o700)
    with (logs / '.launcher-start.lock').open('a') as lock:
        os.chmod(lock.name, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Launcher startup is already in progress. Its window will open when ready.', flush=True)
            return
        launch(args, config, prefix, install, host, command, switch, switch_name, logs)


def launch(args, config, prefix, install, host, command, switch, switch_name, logs):
    direct = args.display == 'direct'
    prepare_game_fonts(prefix)
    prepare_updater_ca(install / 'bin')
    env = os.environ.copy()
    # A launch must use the configured environment, not an inherited graphics test.
    for key in list(env):
        if key.startswith(('WINE', 'DXVK_', 'MVK_', 'VK_', 'DYLD_')):
            env.pop(key)
    env.update(WINEPREFIX=str(prefix),
               DYLD_FALLBACK_LIBRARY_PATH=':'.join(str(Path(item).expanduser().resolve()) for item in config['library_paths']) + ':/usr/local/lib:/usr/lib',
               WINEDLLOVERRIDES='winemenubuilder.exe=d;winedbg.exe=d',
               DOTNET_MULTILEVEL_LOOKUP='0', WINEDEBUG='-all,err+all')
    tasks = running_images(host, env)
    restarting = args.restart or args.finish_setup
    if restarting and tasks.intersection({'l2.exe', '4updater.exe'}):
        raise RuntimeError('Close the game and let the update finish before restarting the launcher.')
    helper = HELPERS / 'NativeLauncherWindow.exe'
    if 'launcher.exe' in tasks and not restarting:
        setting = subprocess.run([str(host), 'reg', 'query', BACKGROUND_KEY, '/v', 'LineageBackgroundApp'],
                                 env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        expected = 'N' if direct else 'Y'
        values = [line.split('REG_SZ', 1)[1].strip() for line in
                  setting.stdout.decode(errors='replace').splitlines() if 'REG_SZ' in line]
        if setting.returncode or expected not in values:
            raise RuntimeError('A different launcher display mode is already running. Close it before switching modes.')
        if direct and helper.is_file():
            subprocess.run([str(host), str(helper), '--show'], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=20)
        # In particular, do not reload a page that may be downloading an update.
        print('Reusing the running launcher; game and update work are preserved.', flush=True)
        return
    if tasks.intersection({'l2.exe', '4updater.exe', 'inn.games.exe'}) and not restarting:
        raise RuntimeError('A game, update or launcher startup is already running. Wait for it before opening another launcher.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log = logs / f'stock-runner-{stamp}.log'
    with log.open('x') as output:
        log.chmod(0o600)
        output.write('Official installed runner; display=' + args.display + '\n')
        output.flush()
        if restarting:
            # No /T, wineserver -k, explorer kill, or game process termination.
            for name in ('Inn.games.exe', 'Launcher.exe', 'CefSharp.BrowserSubprocess.exe'):
                result = subprocess.run([str(host), 'taskkill', '/F', '/IM', name], env=env,
                                        stdout=output, stderr=output, timeout=30)
                if result.returncode not in (0, 128):
                    raise RuntimeError('Could not restart the launcher. See the launcher log.')
        deadline = time.monotonic() + 5
        while not endpoint_free():
            if not restarting or time.monotonic() >= deadline:
                raise RuntimeError('Local launcher port 8088 is already in use. Close the other launcher before retrying.')
            time.sleep(0.25)
        if helper.is_file():
            subprocess.run([str(host), str(helper), '--background-setup'], env=env,
                           stdout=output, stderr=output, timeout=30, check=True)
        # Only the official launcher needs a foreground Mac application in direct
        # mode. Browser helpers and the Wine desktop shell stay in the background.
        subprocess.run([str(host), 'reg', 'add', BACKGROUND_KEY, '/v', 'LineageBackgroundApp',
                        '/t', 'REG_SZ', '/d', 'N' if direct else 'Y', '/f'], env=env,
                       stdout=output, stderr=output, check=True, timeout=30)
        destination = prefix / 'drive_c/lineage-relay' / switch_name
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(switch, destination)
        subprocess.run([str(host), 'taskkill', '/F', '/IM', 'winedbg.exe'], env=env,
                       stdout=output, stderr=output, timeout=30)
        output.flush()
        process = subprocess.Popen(command, cwd=install, env=env,
                                   stdout=output, stderr=output, start_new_session=True)
    print(json.dumps({'pid': process.pid, 'log': str(log), 'display': args.display}), flush=True)
    if direct:
        # Finite, startup-only checks; no screenshot capture or ongoing CDP polling.
        with log.open('a') as output:
            import contextlib
            with contextlib.redirect_stdout(output):
                finish_loading()


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit('Launcher could not open: ' + str(error))
