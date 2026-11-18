#!/usr/bin/env python3
"""Launch a separately installed official runner using local runtime configuration."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from app_paths import DATA, CONFIG, HELPERS
import subprocess
import shutil
from prepare_game_fonts import prepare_game_fonts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restart', action='store_true',
                        help='Stop only the lab prefix before starting the comparison.')
    parser.add_argument('--check-layout', action='store_true')
    parser.add_argument('--finish-setup', action='store_true', help='Restart the installer-opened launcher with the relay connection enabled.')
    parser.add_argument('--debug', action='store_true', help='Enable the official /d diagnostic endpoint (port 8088).')
    parser.add_argument('--switch-file', type=Path, help='Optional official /sw file for a separate rendering experiment.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    config_path = CONFIG
    if not config_path.is_file():
        parser.error('Create config.local.json using config.example.json first.')
    config = json.loads(config_path.read_text())
    prefix = Path(config['prefix']).expanduser().resolve()
    install = prefix / 'drive_c/Program Files (x86)/Innova/4game_global'
    host = Path(config['wine']).expanduser().resolve()
    server = Path(config['wineserver']).expanduser().resolve()
    # Inn.games.exe is the installed single-file official runner. It adds /4.
    command = [str(host), str(install / 'Inn.games.exe'), '/e', 'prod', '/l', 'en-US']
    if args.debug:
        command.append('/d')
    switch = None
    if args.switch_file:
        switch = args.switch_file.resolve(strict=True)
        # The official single-file runner reassembles arguments without quoting.
        # Keep /sw inside the prefix at a Windows path with no spaces.
        command += ['/sw', r'C:\lineage-relay\cef-switches.txt']
    for file in (host, server, install / 'Inn.games.exe', install / 'bin/Launcher.exe'):
        if not file.is_file():
            parser.error(f'Missing file: {file}')
    if args.check_layout:
        print(json.dumps({'command': command, 'cwd': str(install), 'prefix': str(prefix)}, indent=2))
        return
    prepare_game_fonts(prefix)
    if switch:
        destination = prefix / 'drive_c/lineage-relay/cef-switches.txt'
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(switch, destination)
    env = os.environ.copy()
    env.update(WINEPREFIX=str(prefix),
               DYLD_FALLBACK_LIBRARY_PATH=':'.join(str(Path(item).expanduser().resolve()) for item in config['library_paths']) + ':/usr/local/lib:/usr/lib',
               WINEDLLOVERRIDES='winemenubuilder.exe=d;winedbg.exe=d',
               DOTNET_MULTILEVEL_LOOKUP='0',
               WINEDEBUG='-all,err+all')
    if args.restart:
        stopped = subprocess.run([str(server), '-k'], env=env, timeout=15)
        # wineserver -k returns 1 when this prefix has no running server.
        if stopped.returncode not in (0, 1):
            stopped.check_returncode()
        subprocess.run([str(server), '-w'], env=env, check=True, timeout=15)
    logs = DATA / 'logs'
    logs.mkdir(exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log = logs / f'stock-runner-{stamp}.log'
    with log.open('x') as output:
        output.write('Official installed runner; debug=' + str(args.debug) + '; custom switches=' + str(bool(args.switch_file)) + '\n')
        os.chmod(log, 0o600)
        output.flush()
        helper = HELPERS / 'NativeLauncherWindow.exe'
        if helper.is_file():
            subprocess.run([str(host),str(helper),'--background-setup'],env=env,stdout=output,stderr=output,timeout=30,check=True)
        # Retire a crash debugger left by an earlier failed launcher in this prefix.
        debugger = subprocess.run([str(host), 'taskkill', '/F', '/IM', 'winedbg.exe'], env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        if debugger.returncode == 0:
            output.write('Closed a leftover Wine crash debugger.\n')
        elif debugger.returncode != 128:
            output.write('Crash-debugger cleanup returned ' + str(debugger.returncode) + '.\n')
            if isinstance(debugger.stdout, bytes): output.write(debugger.stdout.decode(errors='replace'))
        output.flush()
        if args.finish_setup:
            # Only launcher executables in this prefix; never kill the prefix or game.
            for name in ('Inn.games.exe', 'Launcher.exe', 'explorer.exe'):
                result = subprocess.run([str(host), 'taskkill', '/F', '/IM', name], env=env,
                                        stdout=output, stderr=output, timeout=30)
                if result.returncode not in (0, 128):
                    raise RuntimeError('Could not restart the installer-opened launcher. See the launcher log.')
        process = subprocess.Popen(command, cwd=install, env=env,
                                   stdout=output, stderr=output, start_new_session=True)
    print(json.dumps({'pid': process.pid, 'log': str(log)}, indent=2))


if __name__ == '__main__':
    main()
