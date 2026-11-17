#!/usr/bin/env python3
"""Start the official launcher and the native macOS display relay."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-layout', action='store_true')
    parser.add_argument('--finish-setup', action='store_true', help='Reconnect the installer-opened launcher using its diagnostic endpoint.')
    parser.add_argument('--new-instance', action='store_true', help='Open a relay instance separate from the setup window.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    app = root / '4gameRelay.app'
    required = [app / 'Contents/MacOS/4gameRelay', root / 'run_stock_launcher.py', root / 'cef-switches.txt', root / 'config.local.json']
    for path in required:
        if not path.is_file():
            raise SystemExit('Missing file: ' + str(path))
    subprocess.run([sys.executable, str(root / 'run_stock_launcher.py'), '--check-layout'], check=True)
    if args.check_layout:
        print('Launcher, runtime and relay files verified.')
        return
    opener = build_opener(ProxyHandler({}))

    def ready():
        try:
            with opener.open('http://127.0.0.1:8088/json/list', timeout=1) as response:
                pages = json.load(response)
            official = [p for p in pages if p.get('type') == 'page' and urlsplit(p.get('url', '')).hostname == 'launcher.eu.4game.com']
            return len(official) >= 1
        except (OSError, ValueError):
            return False

    if not ready():
        print('Starting official launcher…', flush=True)
        subprocess.run([sys.executable, str(root / 'run_stock_launcher.py'), '--debug',
                        '--switch-file', str(root / 'cef-switches.txt')] + (['--finish-setup'] if args.finish_setup else []), cwd=root, check=True)
        deadline = time.monotonic() + 60
        while not ready():
            if time.monotonic() >= deadline:
                raise SystemExit('Launcher did not become ready within 60 seconds. Close any older launcher and retry.')
            time.sleep(0.5)
    subprocess.run(['/usr/bin/open'] + (['-n'] if args.new_instance else []) + [str(app)], check=True)
    print('Launcher relay opened.')


if __name__ == '__main__':
    main()
