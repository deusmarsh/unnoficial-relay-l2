#!/usr/bin/env python3
"""Apply the bundled runtime icon to the configured macOS Wine host."""
import json
from pathlib import Path
import plistlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent

def main():
    config = json.loads((ROOT / 'config.local.json').read_text())
    host = Path(config['wine']).expanduser().absolute()
    if host.parent.name != 'MacOS' or host.parent.parent.name != 'Contents':
        raise SystemExit('Expected a wine executable inside a macOS .app bundle.')
    contents = host.parent.parent
    app = contents.parent
    plist = contents / 'Info.plist'
    source = ROOT / '.build/icons/Runtime.icns'
    if not source.is_file():
        raise SystemExit('Build icons first: python3 build_native_frame_relay.py')
    backup = app.with_name(app.stem + '-Info.before-icon.plist')
    if not backup.exists():
        shutil.copyfile(plist, backup)
    data = plistlib.loads(plist.read_bytes())
    data.update(CFBundleDisplayName='Lineage II Runtime', CFBundleName='Lineage II Runtime', CFBundleIconFile='Runtime.icns', LSUIElement=True)
    resources = contents / 'Resources'
    resources.mkdir(exist_ok=True)
    shutil.copyfile(source, resources / 'Runtime.icns')
    plist.write_bytes(plistlib.dumps(data))
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    print('Runtime bundle icon applied. Restart the runtime to refresh its Dock icon.')

if __name__ == '__main__':
    main()
