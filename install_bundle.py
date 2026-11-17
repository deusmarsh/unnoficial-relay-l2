#!/usr/bin/env python3
"""First-run setup for the self-contained macOS application; no compiler or system Python."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tempfile

import install as setup
from app_paths import ROOT, DATA, CONFIG, RESOURCES
from prepare_net3132 import prepare

PAYLOAD = RESOURCES / 'Payload'
MARKER = '.lineage-app-data'


def verify_payload():
    manifest = json.loads((PAYLOAD / 'manifest.json').read_text())
    for relative, expected in manifest['files'].items():
        file = PAYLOAD / relative
        if not file.is_file() or setup.digest(file,'sha256') != expected:
            raise RuntimeError('Bundled component is missing or damaged: ' + relative)
    return manifest


def prepare_runtime(manifest):
    cache = DATA / 'downloads'; cache.mkdir(exist_ok=True)
    archives = {}
    for key in ('engine','support'):
        archives[key] = setup.fetch(setup.MANIFEST[key],cache)
    unpacked = DATA / 'packages';unpacked.mkdir(exist_ok=True)
    for key in ('engine','support'):
        setup.unpack(archives[key],unpacked / key)
    app = DATA / 'LineageRuntime.app';contents = app / 'Contents'
    prepared = DATA / '.runtime-prepared'
    if app.exists() and not prepared.is_file():
        app.rename(DATA / ('Interrupted Runtime '+str(time.time_ns())+'.app'))
    if not prepared.exists():
        contents.mkdir(parents=True)
        engine = unpacked / 'engine/wswine.bundle'
        shutil.copytree(engine/'bin',contents/'MacOS')
        for name in ('lib','share'):shutil.copytree(engine/name,contents/name,symlinks=True)
        (contents/'bin').symlink_to('MacOS')
        shutil.copy2(PAYLOAD/'wine-kernel/ntoskrnl.exe',contents/'lib/wine/x86_64-windows/ntoskrnl.exe')
        shutil.copy2(PAYLOAD/'wine-mac/winemac.so',contents/'lib/wine/x86_64-unix/winemac.so')
        libraries = DATA/'libraries';libraries.mkdir(exist_ok=True)
        support = unpacked/'support/Wine Devel.app/Contents/Resources/wine/lib'
        for name in manifest['support_files']:
            if Path(name).name != name: raise RuntimeError('Invalid support library name.')
            source = support/name
            if not source.is_file():raise RuntimeError('Support library is missing: '+name)
            shutil.copy2(source,libraries/name)
            setup.run([PAYLOAD/'tools/rcodesign','-C',PAYLOAD/'tools/empty.toml','sign',libraries/name])
        import plistlib
        resources = contents/'Resources';resources.mkdir()
        shutil.copyfile(RESOURCES/'Relay.icns',resources/'Runtime.icns')
        # Runtime artwork has its own glyph but the same padding as the launcher.
        shutil.copyfile(PAYLOAD/'helpers/Runtime.icns',resources/'Runtime.icns')
        (contents/'Info.plist').write_bytes(plistlib.dumps({
            'CFBundleName':'Lineage II Runtime','CFBundleDisplayName':'Lineage II Runtime',
            'CFBundleIdentifier':'org.lineagemacos.runtime','CFBundleExecutable':'wine',
            'CFBundlePackageType':'APPL','CFBundleVersion':'1','CFBundleIconFile':'Runtime.icns','NSHighResolutionCapable':True,
            'LSUIElement':True,
        }))
        setup.run([PAYLOAD/'tools/rcodesign','-C',PAYLOAD/'tools/empty.toml','sign',app])
        setup.run(['/usr/bin/codesign','--verify','--deep','--strict',app])
        prepared.write_text(manifest['build_id']+'\n')
    if prepared.read_text().strip()!=manifest['build_id']:
        raise RuntimeError('This app uses a different runtime revision. Use a separate data directory for this preview.')
    setup.run(['/usr/bin/codesign','--verify','--deep','--strict',app])
    return {'prefix':str(DATA/'prefix'),'wine':str(contents/'MacOS/wine'),
            'wineserver':str(contents/'MacOS/wineserver'),'library_paths':[str(DATA/'libraries')]}


def bootstrap(config, installer):
    env=setup.wine_env(config)
    prefix=Path(config['prefix'])
    if prefix.exists() and not (prefix/setup.MARKER).is_file():raise RuntimeError('Refusing an unowned Windows environment.')
    prefix.mkdir(exist_ok=True);(prefix/setup.MARKER).write_text('Isolated app-owned prefix\n')
    log=DATA/'runtime-checks.log'
    with log.open('a') as output:
        log.chmod(0o600)
        commands=[[str(PAYLOAD/'helpers/NativeLauncherWindow.exe'),'--background-setup'],['wineboot','-u'],['cmd','/c','ver'],['reg','add',r'HKCU\Software\Microsoft\Avalon.Graphics','/v','DisableHWAcceleration','/t','REG_DWORD','/d','1','/f']]
        for args in commands:
            subprocess.run([config['wine'],*args],env=env,stdout=output,stderr=output,check=True,timeout=180)
    prepare(installer,PAYLOAD/'dotnet-runtime-3.1.32-win-x86.zip',DATA/'installer-net3132')
    result=subprocess.run([config['wine'],str(DATA/'dotnet31-runtime/dotnet.exe'),'--list-runtimes'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
    if result.returncode or 'Microsoft.NETCore.App 3.1.32' not in result.stdout:raise RuntimeError('The .NET host check failed. See runtime-checks.log in the app data folder.')
    result=subprocess.run([config['wine'],str(PAYLOAD/'helpers/GuardedMutexProbe.exe')],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
    if result.returncode or 'GUARDED_MUTEX_OK' not in result.stdout:raise RuntimeError('The Wine synchronization check failed.')
    with log.open('a') as output:output.write('NET_HOST_OK\n'+result.stdout)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui',action='store_true')
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    setup.GUI=args.gui
    if setup.GUI and os.getpgrp()!=os.getpid():os.setsid()
    setup.stage('Checking the app','No system Python or developer tools are needed.')
    manifest=verify_payload()
    if sys.platform!='darwin':raise RuntimeError('This application requires macOS.')
    if subprocess.run(['/usr/bin/arch','-x86_64','/usr/bin/true'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        setup.confirm('Rosetta is required. Open Apple’s installation and license prompt in Terminal?')
        script=Path(tempfile.mkdtemp(prefix='lineage-rosetta-'))/'Install Rosetta.command';script.write_text('#!/bin/zsh\n/usr/sbin/softwareupdate --install-rosetta\nprintf "\\nReturn to the Lineage II setup window when finished.\\n"\nread -r\n');script.chmod(0o700)
        setup.run(['/usr/bin/open','-a','Terminal',script])
        setup.prompt('Finish Apple’s Rosetta installation, then return here.','continue')
        if subprocess.run(['/usr/bin/arch','-x86_64','/usr/bin/true'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:raise RuntimeError('Rosetta is not installed yet.')
    if DATA.exists() and any(DATA.iterdir()) and not (DATA/MARKER).exists():raise RuntimeError('The app data folder is not owned by this app. Choose a clean folder.')
    setup.confirm('Prepare Lineage II? Runtime downloads are about 380 MB. Setup uses several GB; the game needs about 41 GB separately.')
    DATA.mkdir(parents=True,exist_ok=True);DATA.chmod(0o700);(DATA/MARKER).write_text('Lineage II app-owned data\n')
    setup.stage('Preparing the runtime','Downloading verified Wine packages. Nothing needs to be compiled.')
    config=prepare_runtime(manifest)
    cache=DATA/'downloads'
    setup.stage('Getting the official installer','The installer is downloaded directly from the publisher.')
    installer=setup.fetch(setup.MANIFEST['installer'],cache)
    setup.stage('Checking the runtime','Preparing a fresh Windows environment and testing bundled components.')
    bootstrap(config,installer)
    (DATA/'config.prepared.json').write_text(json.dumps(config,indent=2)+'\n');(DATA/'config.prepared.json').chmod(0o600)
    if args.prepare_only:
        setup.event('complete',title='Preparation complete',detail='Runtime checks passed. No publisher terms were accepted.',launch=False)
        return
    runner=Path(config['prefix'])/'drive_c/Program Files (x86)/Innova/4game_global/Inn.games.exe'
    launcher=runner.parent/'bin/Launcher.exe'
    if not runner.is_file() or not launcher.is_file():
        setup.stage('Install the official launcher','Review its agreement in the installer window. Return here when installation is complete.')
        setup.confirm('Open the official launcher installer now? Its agreement is yours to review and accept.')
        with (DATA/'official-installer.log').open('a') as output:
            (DATA/'official-installer.log').chmod(0o600)
            subprocess.Popen([config['wine'],str(DATA/'dotnet31-runtime/dotnet.exe'),'exec','Launcher.Installer.dll'],cwd=DATA/'installer-net3132',env=setup.wine_env(config),stdout=output,stderr=output)
        setup.prompt('Wait for Inn.games installation to finish, then click I\'ve Finished here. A blank runtime window may appear. Use this Mac app instead of the Windows desktop shortcut.','continue')
        if not runner.is_file() or not launcher.is_file():raise RuntimeError('The official launcher is not installed yet. Complete its installer, then reopen the app.')
    if CONFIG.exists():shutil.copyfile(CONFIG,DATA/('config.previous-'+str(time.time_ns())+'.json'))
    CONFIG.write_text(json.dumps(config,indent=2)+'\n');CONFIG.chmod(0o600)
    setup.event('complete',title='Ready to launch',detail='Open Launcher connects the official launcher to this Mac app. Use this app from Applications, not the Windows desktop shortcut.',launch=True)


if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:sys.exit(130)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        message = 'A runtime step failed. Your files were kept; open details for the error and reopen setup to retry.' if isinstance(error,subprocess.SubprocessError) else str(error)
        setup.event('failed',message=message);print('Setup stopped: '+str(error),file=sys.stderr);sys.exit(1)
