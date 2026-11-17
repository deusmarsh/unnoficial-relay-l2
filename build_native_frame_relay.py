#!/usr/bin/env python3
"""Build the native macOS display/input relay for the official launcher."""
from pathlib import Path
import plistlib
import subprocess
import shutil
import json
import struct
import sys

root = Path(__file__).resolve().parent
app = root / '4gameRelay.app'
contents = app / 'Contents'
binary = contents / 'MacOS/4gameRelay'
binary.parent.mkdir(parents=True, exist_ok=True)
resources = contents / 'Resources'
resources.mkdir(exist_ok=True)
# Deferred artwork: source setup/run/CI skip icon generation by default.
# Keep the generator for optional distribution builds: pass --with-icons.
with_icons = '--with-icons' in sys.argv
if with_icons:
    icons = root / '.build/icons'
    icons.mkdir(parents=True, exist_ok=True)
    icon_builder = root / '.build/build-icons'
    subprocess.run(['xcrun', 'swiftc', '-module-cache-path', str(root / '.build/module-cache'), str(root / 'build_icons.swift'), '-o', str(icon_builder)], check=True)
    subprocess.run([str(icon_builder), str(icons)], check=True)
    for role in ('Relay', 'Runtime'):
        subprocess.run(['iconutil', '-c', 'icns', str(icons / (role + '.iconset')), '-o', str(icons / (role + '.icns'))], check=True)
    # Windows ICO stores the same padded artwork as the macOS runtime icon.
    frames = []
    for size in (16, 32, 128, 256):
        frames.append((size, (icons / 'Runtime.iconset' / ('icon_%dx%d.png' % (size, size))).read_bytes()))
    offset = 6 + 16 * len(frames)
    entries = []
    for size, data in frames:
        entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (icons / 'Runtime.ico').write_bytes(struct.pack('<HHH', 0, 1, len(frames)) + b''.join(entries) + b''.join(data for _, data in frames))
    shutil.copyfile(icons / 'Relay.icns', resources / 'Relay.icns')
info = {
    'CFBundleName': 'Lineage II Launcher', 'CFBundleDisplayName': 'Lineage II Launcher', 
    'CFBundleIdentifier': 'org.lineagemacos.community.relay', 'CFBundleExecutable': '4gameRelay',
    'CFBundlePackageType': 'APPL', 'CFBundleVersion': '3', 'CFBundleShortVersionString': '0.3',
    'LSMinimumSystemVersion': '13.0', 'NSHighResolutionCapable': True,
    'NSAppTransportSecurity': {'NSAllowsLocalNetworking': True},
}
if with_icons:
    info['CFBundleIconFile'] = 'Relay.icns'
(contents / 'Info.plist').write_bytes(plistlib.dumps(info))
(root / '.build').mkdir(exist_ok=True)
main_source = root / '.build/main.swift'
shutil.copyfile(root / 'NativeFrameRelay.swift', main_source)
staging = binary.with_name(binary.name + '.new')
subprocess.run(['xcrun','swiftc','-target','arm64-apple-macos13.0','-framework','AppKit',
                '-module-cache-path',str(root / '.build/module-cache'),
                str(main_source),str(root / 'SetupWizard.swift'),str(root / 'AppPaths.swift'),'-o',str(staging)], check=True)
staging.replace(binary)
subprocess.run(['codesign','--force','--sign','-',str(app)], check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(app)], check=True)
print('Built native relay:', app)

config_path = root / 'config.local.json'
if config_path.is_file() and '--relay-only' not in sys.argv:
    compiler = json.loads(config_path.read_text()).get('mingw_clang')
    if compiler:
        subprocess.run([compiler, str(root / 'NativeLauncherWindow.c'), '-municode', '-mwindows', '-O2', '-o', str(root / '.build/NativeLauncherWindow.exe'), '-luser32', '-lshell32', '-ladvapi32'], check=True)
