#!/usr/bin/env python3
"""Set local game display preferences; preserve a byte-for-byte backup."""
import json
from pathlib import Path
import re

from app_paths import DATA, CONFIG, HELPERS, RESOURCES, PACKAGED

ROOT = Path(__file__).resolve().parent
VALUES = {'UseBorderlessWindow': 'False', 'StartupFullScreen': 'False',
          'GamePlayViewportX': '1280', 'GamePlayViewportY': '720'}

def main():
    config = json.loads(CONFIG.read_text())
    path = Path(config['prefix']).expanduser().resolve() / 'drive_c/Games/LineageII EU/system/Option.ini'
    original = path.read_bytes()
    text = original.decode('utf-8')
    newline = '\r\n' if b'\r\n' in original else '\n'
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().lower() == '[video]')
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith('[')), len(lines))
    section = lines[start + 1:end]
    for key, value in VALUES.items():
        pattern = re.compile(r'^\s*' + re.escape(key) + r'\s*=', re.I)
        section = [line for line in section if not pattern.match(line)]
        section.append(key + '=' + value)
    updated = newline.join(lines[:start + 1] + section + lines[end:]) + newline
    backup = path.with_name('Option.ini.before-windowed.bak')
    if not backup.exists():
        with backup.open('xb') as stream:
            stream.write(original)
    path.write_bytes(updated.encode('utf-8'))
    print('Local display preferences saved: bordered window, 1280x720. Restart the game to test.')
    print('Original preferences preserved in Option.ini.before-windowed.bak beside Option.ini.')

if __name__ == '__main__':
    main()
