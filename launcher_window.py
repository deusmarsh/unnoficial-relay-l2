#!/usr/bin/env python3
"""Minimize or restore the original WPF launcher, without touching game windows."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from app_paths import DATA, CONFIG, HELPERS, RESOURCES, PACKAGED

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--frame', action='store_true', help='Add standard controls and a runtime-window title.')
    parser.add_argument('--hide', action='store_true', help='Hide the original launcher surface while keeping its process running.')
    args = parser.parse_args()
    helper = HELPERS / 'NativeLauncherWindow.exe'
    if not helper.is_file():
        raise SystemExit('Window helper not built. Set mingw_clang in config.local.json and rebuild.')
    c = json.loads(CONFIG.read_text())
    env = os.environ.copy()
    env.update(WINEPREFIX=str(Path(c['prefix']).expanduser().resolve()), WINEDEBUG='-all',
               DYLD_FALLBACK_LIBRARY_PATH=':'.join(c['library_paths']) + ':/usr/local/lib:/usr/lib')
    action = '--inspect' if args.inspect else '--restore' if args.restore else '--hide' if args.hide else '--frame' if args.frame else '--minimize'
    command = [c['wine'], str(helper), action]
    icon = RESOURCES / 'Payload/helpers/Runtime.ico' if PACKAGED else ROOT / '.build/icons/Runtime.ico'
    if PACKAGED and icon.is_file():
        command.append('Z:' + str(icon).replace('/', '\\'))
    subprocess.run(command, env=env, check=True, timeout=20)

if __name__ == '__main__':
    main()
