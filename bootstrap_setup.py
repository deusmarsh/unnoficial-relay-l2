#!/usr/bin/env python3
"""Build and open the graphical setup window. No shell commands need to be typed."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    if subprocess.run(['xcrun','--find','swiftc'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        print('Apple Command Line Tools are needed to build this source release.')
        if input('Open Apple\'s installer? [y/N] ').strip().lower() not in ('y','yes'):
            raise SystemExit('Setup cancelled.')
        subprocess.run(['xcode-select','--install'],check=True)
        input('Complete Apple\'s installation, then press Enter here to continue: ')
        subprocess.run(['xcrun','--find','swiftc'],check=True)
    if subprocess.run(['/usr/bin/arch','-x86_64','/usr/bin/true'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        print('Rosetta is needed for the Windows compatibility runtime.')
        if input('Open Apple\'s Rosetta installation and license prompt? [y/N] ').strip().lower() not in ('y','yes'):
            raise SystemExit('Setup cancelled.')
        subprocess.run(['/usr/sbin/softwareupdate','--install-rosetta'],check=True)
    binary = ROOT / '4gameRelay.app/Contents/MacOS/4gameRelay'
    sources = [ROOT / name for name in ('AppPaths.swift','NativeFrameRelay.swift','SetupWizard.swift','build_native_frame_relay.py')]
    if not binary.is_file() or any(path.stat().st_mtime > binary.stat().st_mtime for path in sources):
        print('Preparing the setup window. This first build can take a minute.')
        subprocess.run([sys.executable,str(ROOT / 'build_native_frame_relay.py'),'--relay-only'],cwd=ROOT,check=True)
    subprocess.run(['/usr/bin/open','-n',str(ROOT / '4gameRelay.app'),'--args','--setup',*sys.argv[1:]],check=True)
    print('Continue in the Lineage II setup window. You can close this Terminal window.')


if __name__ == '__main__':
    try:
        main()
    except (OSError,subprocess.SubprocessError) as error:
        raise SystemExit('Could not open setup: ' + str(error))
