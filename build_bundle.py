#!/usr/bin/env python3
"""Maintainer build: package the native app, embedded Python and stable payload into a drag-install DMG."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import sys
import time
import zipfile

import install as setup

ROOT=Path(__file__).resolve().parent


def run(args,**kwargs):subprocess.run(list(map(str,args)),check=True,**kwargs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-dir',type=Path,default=ROOT/'.local')
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    parser.add_argument('--skip-dmg',action='store_true')
    args=parser.parse_args()
    work=args.prepared_dir.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    cache=work/'cache'
    if not (work/setup.MARKER).is_file():raise SystemExit('Prepare the maintainer runtime first with install.py --prepare-only.')
    python_archive=setup.fetch(setup.MANIFEST['python'],cache)
    signing_archive=setup.fetch(setup.MANIFEST['rcodesign'],cache)
    signing_source=setup.fetch(setup.MANIFEST['rcodesign_source'],cache)
    signing_stage=ROOT/'.build/rcodesign'
    setup.unpack(signing_archive,signing_stage)
    full_archive=setup.fetch(setup.MANIFEST['python_full'],cache)
    for key in ('dotnet','wine_source'):setup.verify(cache/setup.MANIFEST[key]['file'],setup.MANIFEST[key])
    kernel=work/'wine-build/dlls/ntoskrnl.exe/x86_64-windows/ntoskrnl.exe'
    if not kernel.is_file():raise SystemExit('The prepared Wine patch is missing.')
    # Remove maintainer paths from Wine's assertion strings as well as debug info.
    source=work/'wine-source/wine-wine-10.0';build=work/'wine-build'
    if str(work).encode() in kernel.read_bytes():
        for obj in kernel.parent.glob('*.o'):obj.unlink()
        env=os.environ.copy()
        toolbin=work/'toolchain/llvm-mingw-20261104-ucrt-macos-universal/bin'
        env['PATH']=str(work/'bison/bin')+os.pathsep+str(toolbin)+os.pathsep+env.get('PATH','/usr/bin:/bin')
        flags='x86_64_CFLAGS=-g -O2 -ffile-prefix-map='+str(source)+'=/wine-source -ffile-prefix-map='+str(build)+'=/wine-build'
        run(['make','-j8',flags,'dlls/ntoskrnl.exe/x86_64-windows/ntoskrnl.exe'],cwd=build,env=env)

    mac_driver=setup.build_background_driver(work)
    run([sys.executable,ROOT/'build_native_frame_relay.py','--relay-only','--with-icons'],cwd=ROOT)
    app=out/'Lineage II Launcher.app'
    if app.exists():
        if not (app/'Contents/Resources/packaged-build.json').is_file():raise SystemExit('Refusing to replace an unowned bundle.')
        previous=out/('Previous Build '+str(time.time_ns())+'.app');app.rename(previous)
    shutil.copytree(ROOT/'4gameRelay.app',app,symlinks=True)
    resources=app/'Contents/Resources';code=resources/'app';code.mkdir()
    code_files=['install_bundle.py','install.py','app_paths.py','dependencies.json','prepare_net3132.py','run_stock_launcher.py','configure_game_window.py','launcher_window.py','cef-switches.txt']
    code_files.append('prepare_game_fonts.py')
    for name in code_files:shutil.copyfile(ROOT/name,code/name)
    py_stage=ROOT/'.build/python-install'
    setup.unpack(python_archive,py_stage)
    shutil.copytree(py_stage/'python',resources/'Python',symlinks=True)
    notices=ROOT/'.build/python-notices'
    if not (notices/'PYTHON.json').is_file():
        # The maintainer's verified support library supplies a Zstandard decoder.
        run(['/usr/bin/arch','-x86_64',sys.executable,ROOT/'extract_python_licenses.py',full_archive,work/'libraries/libzstd.1.dylib',notices])
    licenses=resources/'Licenses';licenses.mkdir()
    shutil.copytree(notices/'licenses',licenses/'Python')
    shutil.copyfile(notices/'PYTHON.json',licenses/'Python-build-metadata.json')
    for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):shutil.copyfile(ROOT/name,licenses/name)
    shutil.copytree(ROOT/'licenses',licenses/'Wine')
    payload=resources/'Payload';helpers=payload/'helpers';helpers.mkdir(parents=True)
    tools=payload/'tools';tools.mkdir()
    shutil.copyfile(signing_stage/'apple-codesign-0.29.0-aarch64-apple-darwin/rcodesign',tools/'rcodesign');(tools/'rcodesign').chmod(0o755)
    (tools/'empty.toml').write_text('# No user signing identities or external configuration.\n')
    shutil.copyfile(signing_stage/'apple-codesign-0.29.0-aarch64-apple-darwin/COPYING',licenses/'rcodesign-COPYING.txt')
    for name in ('Runtime.icns','Runtime.ico'):shutil.copyfile(ROOT/'.build/icons'/name,helpers/name)
    compiler=work/'toolchain/llvm-mingw-20261104-ucrt-macos-universal/bin/x86_64-w64-mingw32-clang'
    run([compiler,ROOT/'NativeLauncherWindow.c','-municode','-mwindows','-O2','-o',helpers/'NativeLauncherWindow.exe','-luser32','-lshell32','-ladvapi32'])
    run([compiler,ROOT/'GuardedMutexProbe.c','-O2','-o',helpers/'GuardedMutexProbe.exe'])
    (payload/'wine-mac').mkdir();shutil.copyfile(mac_driver,payload/'wine-mac/winemac.so')
    (payload/'wine-kernel').mkdir();shutil.copyfile(kernel,payload/'wine-kernel/ntoskrnl.exe')
    strip=compiler.with_name('x86_64-w64-mingw32-strip')
    for file in [payload/'wine-kernel/ntoskrnl.exe',*helpers.glob('*.exe')]:run([strip,'--strip-all',file])
    shutil.copyfile(cache/setup.MANIFEST['dotnet']['file'],payload/'dotnet-runtime-3.1.32-win-x86.zip')
    with zipfile.ZipFile(payload/'dotnet-runtime-3.1.32-win-x86.zip') as archive:
        for name in ('LICENSE.txt','ThirdPartyNotices.txt'):
            (licenses/('DotNet-'+name)).write_bytes(archive.read(name))
    source=resources/'Source';source.mkdir()
    shutil.copyfile(cache/setup.MANIFEST['wine_source']['file'],source/'wine-10.0-source.tar.gz')
    shutil.copytree(ROOT/'patches',source/'patches')
    shutil.copyfile(signing_source,source/'apple-platform-rs-0.29.0-source.tar.gz')
    for name in ('GuardedMutexProbe.c','NativeLauncherWindow.c','build_bundle.py','extract_python_licenses.py','install.py','dependencies.json'):
        shutil.copyfile(ROOT/name,source/name)
    manifest={'build_id':'wine10-guarded-mac-bg-v2','support_files':sorted(x.name for x in (work/'libraries').glob('*.dylib')),'files':{}}
    for file in payload.rglob('*'):
        if file.is_file():manifest['files'][str(file.relative_to(payload))]=setup.digest(file,'sha256')
    (payload/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    info=app/'Contents/Info.plist';data=plistlib.loads(info.read_bytes())
    data.update(CFBundleIdentifier='org.lineagemacos.launcher',CFBundleName='Lineage II Launcher',CFBundleDisplayName='Lineage II Launcher',CFBundleVersion='4',CFBundleShortVersionString='0.4')
    info.write_bytes(plistlib.dumps(data))
    (resources/'packaged-build.json').write_text(json.dumps({'version':'0.4','code_files':code_files,'embedded':['Python 3.12.16','Wine guarded-mutex module and corresponding source','Windows UI helpers','Microsoft .NET 3.1.32','Original icons'],'downloaded_on_first_use':['Pinned Wine engine and support packages','Official publisher installer','Game client through official launcher']},indent=2)+'\n')
    # Sign every Mach-O nested binary before sealing the outer bundle.
    magic={b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'}
    binaries=[]
    for file in app.rglob('*'):
        if file.is_file() and not file.is_symlink():
            with file.open('rb') as stream:
                if stream.read(4) in magic:binaries.append(file)
    for file in sorted(binaries,key=lambda x:len(x.parts),reverse=True):
        run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',file],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    manifest['files']={str(f.relative_to(payload)):setup.digest(f,'sha256') for f in payload.rglob('*') if f.is_file() and f.name!='manifest.json'}
    (payload/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',app])
    run(['/usr/bin/codesign','--verify','--deep','--strict',app])
    # Include the wrapper source with the distribution as well as the Wine source.
    run([sys.executable,ROOT/'package_source.py'])
    shutil.copyfile(ROOT/'.build/lineage-macos-relay-source.zip',out/'Source.zip')
    readme='''Lineage II Launcher — experimental preview

Drag Lineage II Launcher.app to Applications, then open it.
No Python, Xcode or Homebrew installation is needed. Rosetta may be requested by macOS.
The app downloads verified Wine packages on first use, then opens the official installer.
Review publisher terms yourself. Sign in and install the game through the official launcher.

Known issues: stuttering, missing text, incorrect model colors and a blocking blank dialog.
Character creation and entering the game world are not confirmed.

Private files are stored in ~/Library/Application Support/Lineage II for macOS.
No existing game account or Wine profile is included in this download.

This local preview is ad-hoc signed, not Developer ID signed or notarized.
Wrapper and Wine-patch source: Source.zip. Additional Wine source and notices are inside the app's Resources/Source and Resources/Licenses folders.
'''
    (out/'Read Me.txt').write_text(readme)
    archive=out/'Lineage II Launcher.app.zip'
    run(['/usr/bin/ditto','-c','-k','--sequesterRsrc','--keepParent',app,archive])
    if not args.skip_dmg:
        image_root=out/'Disk Image'
        if image_root.exists():
            image_root.rename(out/('Previous Disk Image '+str(time.time_ns())))
        image_root.mkdir()
        run(['/usr/bin/ditto',app,image_root/'Lineage II Launcher.app'])
        for name in ('Source.zip','Read Me.txt'):shutil.copyfile(out/name,image_root/name)
        (image_root/'Applications').symlink_to('/Applications')
        run(['/usr/bin/hdiutil','create','-volname','Lineage II Launcher','-srcfolder',image_root,'-format','UDZO','-ov',out/'Lineage II Launcher.dmg'])
    print('Built standalone bundle:',app)

if __name__=='__main__':main()
