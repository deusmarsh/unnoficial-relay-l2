#!/usr/bin/env python3
"""Prepare the pinned runtime from upstream downloads, build the relay, and run the official installer."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
from prepare_game_fonts import prepare_game_fonts

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / 'dependencies.json').read_text())
MARKER = '.lineage-relay-install'


GUI = False


def event(kind, **values):
    if GUI:
        print('@@LINEAGE_SETUP@@' + json.dumps(dict(kind=kind, **values)), flush=True)


def stage(title, detail=''):
    event('stage', title=title, detail=detail)
    if not GUI: print(title, flush=True)


def prompt(message, kind='confirm'):
    if GUI:
        event('prompt', message=message, response=kind)
        answer = sys.stdin.readline()
        if not answer: raise RuntimeError('Setup window closed.')
        return answer.strip().lower()
    if not sys.stdin.isatty():
        raise RuntimeError('Interactive confirmation required. Open Install.command.')
    return input(message + (' [y/N] ' if kind == 'confirm' else ' ')).strip().lower()


def confirm(message):
    if prompt(message) not in ('y', 'yes'):
        raise RuntimeError('Cancelled; completed local preparation is kept for the next run.')


def run(command, cwd=None, env=None, timeout=None):
    print('> ' + str(command[0]) + (' ' + ' '.join(map(str, command[1:3])) if len(command)>1 else ''), flush=True)
    if cwd is not None and (Path(str(command[0])).name == 'configure' or str(command[0]) == 'make'):
        log = Path(cwd) / 'setup-build.log'
        with log.open('a') as output:
            result = subprocess.run(list(map(str, command)), cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            print('Build details: ' + str(log), file=sys.stderr)
            print('\n'.join(log.read_text(errors='replace').splitlines()[-20:]), file=sys.stderr)
            result.check_returncode()
    else:
        subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True, timeout=timeout)


def digest(path, algorithm):
    h = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify(path, item):
    algorithm = 'sha512' if 'sha512' in item else 'sha256'
    if digest(path, algorithm) != item[algorithm]:
        raise RuntimeError('Checksum mismatch: ' + path.name + '. No downloaded code was run. Upstream may have changed; do not bypass this check.')


def fetch(item, cache):
    target = cache / item['file']
    if not target.is_file():
        partial = target.with_name(target.name + '.partial')
        run(['/usr/bin/curl', '--fail', '--location', '--retry', '3', '--proto', '=https', '--tlsv1.2', '--output', partial, item['url']])
        verify(partial, item)
        partial.replace(target)
    verify(target, item)
    print('Verified: ' + target.name, flush=True)
    return target


def safe_name(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:
        raise RuntimeError('Unsafe archive entry: ' + name)
    return p


def unpack(archive, target):
    # Only owned extraction roots are ever reused. Reject traversal through links,
    # special files and symlinks escaping the extraction directory.
    if (target / '.extracted').is_file():
        return
    if target.exists() and any(target.iterdir()):
        raise RuntimeError('Incomplete extraction at ' + str(target) + '; move it aside and retry.')
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        links = set()
        for m in members:
            safe_name(m.name)
            if m.issym(): links.add(PurePosixPath(m.name))
            elif not (m.isfile() or m.isdir() or m.islnk()):
                raise RuntimeError('Unsupported archive entry: ' + m.name)
        for m in members:
            p = PurePosixPath(m.name)
            if any(parent in links for parent in p.parents):
                raise RuntimeError('Archive entry nested under a symlink: ' + m.name)
            if m.issym():
                link = PurePosixPath(m.linkname)
                if link.is_absolute(): raise RuntimeError('Absolute archive symlink: ' + m.name)
                resolved = os.path.normpath(str(p.parent / link))
                safe_name(resolved)
            elif m.islnk():
                safe_name(m.linkname)
                if PurePosixPath(m.linkname) in links:
                    raise RuntimeError('Hardlink to symlink rejected')
        tar.extractall(target, members=members)
    (target / '.extracted').write_text('Verified upstream archive\n')


def support_libraries(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    pending = ['libinotify.0.dylib', 'libfreetype.6.dylib', 'libgnutls.30.dylib', 'libMoltenVK.dylib']
    copied = set()
    while pending:
        name = pending.pop()
        if name in copied: continue
        copied.add(name)
        original = source / name
        if not original.is_file(): raise RuntimeError('Missing upstream support library: ' + name)
        shutil.copy2(original, destination / name)
        links = subprocess.check_output(['otool', '-L', str(original)], text=True)
        for line in links.splitlines()[1:]:
            dep = line.strip().split(' (')[0]
            if dep.startswith(('@loader_path/', '@rpath/')):
                pending.append(Path(dep).name)
        run(['codesign', '--force', '--sign', '-', destination / name])
    print('Prepared support libraries:', len(copied))


def build_background_driver(work, jobs=8):
    """Build the opt-in Mac driver patch without replacing Wine's other modules."""
    source=work/'wine-source/wine-wine-10.0';build=work/'wine-build'
    patch_file=ROOT/'patches/winemac-background-app.patch'
    marker=source/'.applied-winemac-background-app.patch'
    identity=digest(patch_file,'sha256')
    if marker.exists() and marker.read_text()!=identity:
        raise RuntimeError('The Mac driver patch changed; use a clean maintainer work directory.')
    if not marker.exists():
        args=['/usr/bin/patch','-p1','--batch','--forward','--dry-run','-i',patch_file]
        result=subprocess.run(list(map(str,args)),cwd=source,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if result.returncode==0:run(['/usr/bin/patch','-p1','--batch','--forward','-i',patch_file],cwd=source)
        else:run(['/usr/bin/patch','-R','-p1','--batch','--dry-run','-i',patch_file],cwd=source)
        marker.write_text(identity)
    env=os.environ.copy()
    toolbins=list((work/'toolchain').glob('llvm-mingw-*/bin'))
    if len(toolbins)!=1:raise RuntimeError('Expected one maintainer toolchain.')
    env['PATH']=str(work/'bison/bin')+os.pathsep+str(toolbins[0])+os.pathsep+env.get('PATH','/usr/bin:/bin')
    env['MACOSX_DEPLOYMENT_TARGET']='13.0'
    flags='-O2 -mmacosx-version-min=13.0 -ffile-prefix-map='+str(source)+'=/wine-source -ffile-prefix-map='+str(build)+'=/wine-build'
    stamp=build/'.lineage-macdrv-flags'
    if not stamp.exists() or stamp.read_text()!=flags:
        for obj in (build/'dlls/winemac.drv').glob('*.o'):obj.unlink()
        stamp.write_text(flags)
    run(['make','-j'+str(jobs),'CFLAGS='+flags,'LDFLAGS=-mmacosx-version-min=13.0','dlls/winemac.drv/winemac.so'],cwd=build,env=env)
    output=work/'wine-background/winemac.so';output.parent.mkdir(exist_ok=True)
    run(['/usr/bin/strip','-S','-x','-o',output,build/'dlls/winemac.drv/winemac.so'])
    if str(work).encode() in output.read_bytes():raise RuntimeError('A private maintainer path remains in the Mac driver.')
    return output


def prepare_runtime(work, archives, jobs):
    engine_dir, support_dir, compiler_dir, source_dir, bison_dir = [work / x for x in ('engine', 'wine-support', 'toolchain', 'wine-source', 'bison-source')]
    for key, folder in [('engine',engine_dir),('support',support_dir),('compiler',compiler_dir),('wine_source',source_dir),('bison',bison_dir)]:
        unpack(archives[key], folder)
    compiler_roots = list(compiler_dir.glob('llvm-mingw-*/bin/x86_64-w64-mingw32-clang'))
    if len(compiler_roots) != 1: raise RuntimeError('Unexpected LLVM-MinGW archive layout.')
    compiler = compiler_roots[0]  # Do not resolve this symlink: its filename selects the target.
    bison_install = work / 'bison'
    build_env = os.environ.copy()
    build_env['PATH'] = str(compiler.parent) + os.pathsep + build_env.get('PATH','/usr/bin:/bin')
    if not (bison_install / 'bin/bison').is_file():
        bison_build = work / 'bison-build'; bison_build.mkdir(exist_ok=True)
        run([bison_dir / 'bison-3.8.2/configure', '--prefix=' + str(bison_install)], cwd=bison_build, env=build_env)
        run(['make', '-j' + str(jobs)], cwd=bison_build, env=build_env)
        run(['make', 'install'], cwd=bison_build, env=build_env)
    build_env['PATH'] = str(bison_install / 'bin') + os.pathsep + build_env['PATH']
    source = source_dir / 'wine-wine-10.0'
    # Detect changed patches rather than silently reusing a stale build.
    patch_id = hashlib.sha256(b''.join((ROOT / 'patches' / name).read_bytes() for name in ('sync.c.patch','ntoskrnl.exe.spec.patch','winemac-background-app.patch'))).hexdigest()
    patched = source / '.relay-patch'
    if patched.exists() and patched.read_text() != patch_id:
        raise RuntimeError('Patch changed. Use a new --work-dir to rebuild from clean source.')
    if not patched.exists():
        for name in ('sync.c.patch','ntoskrnl.exe.spec.patch','winemac-background-app.patch'):
            patch_file = ROOT / 'patches' / name
            applied = source / ('.applied-' + name)
            identity = digest(patch_file, 'sha256')
            if applied.exists():
                if applied.read_text() != identity: raise RuntimeError('Applied patch changed; use a new work directory.')
            else:
                run(['/usr/bin/patch', '-p1', '--batch', '--dry-run', '-i', patch_file], cwd=source)
                run(['/usr/bin/patch', '-p1', '--batch', '-i', patch_file], cwd=source)
                applied.write_text(identity)
    patched.write_text(patch_id)
    build = work / 'wine-build'; build.mkdir(exist_ok=True)
    if not (build / 'Makefile').is_file():
        flags = ['--host=x86_64-apple-darwin','--enable-archs=x86_64','--disable-tests']
        flags += ['--without-' + name for name in ('x','freetype','fontconfig','gnutls','gstreamer','vulkan','gettext','sdl','ffmpeg')]
        build_env.update(CC='clang -arch x86_64', CXX='clang++ -arch x86_64')
        run([source / 'configure'] + flags, cwd=build, env=build_env)
    run(['make','-j'+str(jobs),'x86_64_CFLAGS=-g -O2 -ffile-prefix-map='+str(source)+'=/wine-source -ffile-prefix-map='+str(build)+'=/wine-build','dlls/ntoskrnl.exe/x86_64-windows/ntoskrnl.exe'], cwd=build, env=build_env)
    mac_driver = build_background_driver(work,jobs)
    kernel = build / 'dlls/ntoskrnl.exe/x86_64-windows/ntoskrnl.exe'
    if not kernel.is_file(): raise RuntimeError('Kernel build did not produce its expected output.')
    host = work / 'LineageRuntime.app'
    if not host.exists():
        contents = host / 'Contents'; contents.mkdir(parents=True)
        engine = engine_dir / 'wswine.bundle'
        shutil.copytree(engine / 'bin', contents / 'MacOS')
        for name in ('lib','share'): shutil.copytree(engine / name, contents / name, symlinks=True)
        (contents / 'bin').symlink_to('MacOS')
    contents = host / 'Contents'
    shutil.copy2(kernel, contents / 'lib/wine/x86_64-windows/ntoskrnl.exe')
    shutil.copy2(mac_driver, contents / 'lib/wine/x86_64-unix/winemac.so')
    run(['codesign','--force','--sign','-',contents / 'lib/wine/x86_64-unix/winemac.so'])
    libraries = work / 'libraries'
    support = support_dir / 'Wine Devel.app/Contents/Resources/wine/lib'
    support_libraries(support, libraries)
    (contents / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleName':'Lineage II Runtime', 'CFBundleDisplayName':'Lineage II Runtime',
        'CFBundleIdentifier':'org.lineagemacos.community.runtime','CFBundleExecutable':'wine',
        'CFBundlePackageType':'APPL','CFBundleVersion':'1','NSHighResolutionCapable':True,'LSUIElement':True,
    }))
    run(['codesign','--force','--sign','-',host])
    run(['codesign','--verify','--deep','--strict',host])
    return {'prefix':str(work / 'prefix'), 'wine':str(contents / 'MacOS/wine'),
            'wineserver':str(contents / 'MacOS/wineserver'), 'library_paths':[str(libraries),str(support)],
            'mingw_clang':str(compiler)}


def wine_env(config):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('COMPlus_', 'DOTNET_', 'WINE')): env.pop(key, None)
    env.update(WINEPREFIX=config['prefix'], WINEDEBUG='-all,err+all',
               WINEDLLOVERRIDES='winemenubuilder.exe=d', DOTNET_MULTILEVEL_LOOKUP='0',
               DYLD_FALLBACK_LIBRARY_PATH=':'.join(config['library_paths']) + ':/usr/local/lib:/usr/lib')
    return env


def bootstrap(work, config, archives):
    env = wine_env(config)
    prefix = Path(config['prefix'])
    if prefix.exists() and not (prefix / MARKER).exists():
        raise RuntimeError('Refusing to bootstrap an unowned prefix.')
    prefix.mkdir(exist_ok=True)
    (prefix / MARKER).write_text('Isolated installer-owned Wine prefix\n')
    run([config['wine'], 'wineboot', '-u'], env=env, timeout=180)
    prepare_game_fonts(prefix)
    run([config['wine'], 'cmd', '/c', 'ver'], env=env, timeout=60)
    run([config['wine'], 'reg', 'add', r'HKCU\Software\Microsoft\Avalon.Graphics', '/v', 'DisableHWAcceleration', '/t', 'REG_DWORD', '/d', '1', '/f'], env=env, timeout=60)
    from prepare_net3132 import prepare
    prepare(archives['installer'], archives['dotnet'], work / 'installer-net3132')
    dotnet = work / 'dotnet31-runtime/dotnet.exe'
    run([config['wine'], dotnet, '--list-runtimes'], env=env, timeout=60)
    # Exercise the rebuilt synchronization exports before invoking any game code.
    probe = work / 'GuardedMutexProbe.exe'
    run([config['mingw_clang'], ROOT / 'GuardedMutexProbe.c', '-O2', '-o', probe])
    result = subprocess.run([config['wine'], str(probe)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    print(result.stdout)
    result.check_returncode()
    if 'overlaps=0' not in result.stdout:
        raise RuntimeError('Guarded-mutex smoke test did not report its success marker.')


def prerequisites():
    if sys.platform != 'darwin' or platform.machine() != 'arm64':
        raise RuntimeError('This recipe targets Apple Silicon macOS only. Run Terminal natively, not under Rosetta.')
    for name in ('swiftc','clang'):
        if subprocess.run(['xcrun','--find',name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            confirm('Xcode Command Line Tools are required. Open Apple\'s installer?')
            run(['xcode-select','--install'])
            raise RuntimeError('Complete Apple\'s installer, then rerun Install.command.')
    if subprocess.run(['/usr/bin/arch','-x86_64','/usr/bin/true'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        if GUI: raise RuntimeError('Rosetta is missing. Reopen Install.command and complete Apple\'s installation prompt first.')
        confirm('Rosetta is required. Open Apple\'s Rosetta installation command (review its license prompts)?')
        run(['/usr/sbin/softwareupdate','--install-rosetta'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--work-dir', type=Path, default=ROOT / '.local')
    parser.add_argument('--prepare-only', action='store_true', help='Download, build and smoke-test; do not open the official installer or activate this installation.')
    parser.add_argument('--plan', action='store_true', help='Show the recipe without downloading or changing anything.')
    parser.add_argument('--jobs',type=int,default=min(os.cpu_count() or 2,8))
    args = parser.parse_args()
    global GUI
    GUI = args.gui
    if GUI and os.getpgrp() != os.getpid():
        os.setsid()  # Setup owns this process group; cancellation never targets other apps.
    if args.plan:
        print('1. Check Apple Silicon, Command Line Tools and Rosetta.\n2. Confirm downloads; verify pinned hashes.\n3. Build Bison and the Wine synchronization backport.\n4. Package Wine and support libraries; create an isolated prefix.\n5. Prepare .NET and official installer; run smoke tests.\n6. Confirm and open the official installer; finish its prompts yourself.\n7. Build relay/icons and activate the local configuration.\n8. Install the game and sign in using the official launcher.')
        for key, item in MANIFEST.items(): print(key + ': ' + item['url'])
        return
    if args.jobs < 1: parser.error('--jobs must be positive')
    stage('Checking your Mac', 'Apple Silicon, developer tools and Rosetta')
    prerequisites()
    work = args.work_dir.expanduser().resolve()
    if work == ROOT or ROOT.is_relative_to(work): raise RuntimeError('Choose a dedicated work directory, not the source directory or its parent.')
    if work.exists() and any(work.iterdir()) and not (work / MARKER).is_file(): raise RuntimeError('Refusing a nonempty, unowned work directory: ' + str(work))
    confirm('Download and prepare the runtime? Setup needs several GB; the game needs about 41 GB separately. Your existing installation will be kept.' if GUI else 'Prepare an isolated Wine installation at ' + str(work) + '? Downloads total several hundred MB; builds require several GB. Game download (~41 GB) is separate. No account data is requested by this script.')
    work.mkdir(parents=True,exist_ok=True); (work / MARKER).write_text('Owned by Lineage macOS installer\n')
    cache = work / 'cache'; cache.mkdir(exist_ok=True)
    stage('Downloading dependencies', 'Each download is checked against its pinned hash.')
    archives = {key:fetch(item,cache) for key,item in MANIFEST.items() if key in ('engine','support','compiler','wine_source','bison','dotnet','installer')}
    stage('Building the runtime', 'The first build takes several minutes. You can leave this window open.')
    config = prepare_runtime(work,archives,args.jobs)
    (work / 'config.prepared.json').write_text(json.dumps(config,indent=2)+'\n'); (work / 'config.prepared.json').chmod(0o600)
    stage('Testing the runtime', 'Preparing an isolated Windows environment and checking the Wine patch.')
    bootstrap(work,config,archives)
    print('Runtime build and smoke tests passed. Prepared config:',work / 'config.prepared.json')
    if args.prepare_only:
        event('complete', title='Preparation complete', detail='Runtime checks passed. Your active installation was not changed.', launch=False)
        return
    runner = Path(config['prefix']) / 'drive_c/Program Files (x86)/Innova/4game_global/Inn.games.exe'
    launcher = runner.parent / 'bin/Launcher.exe'
    if not runner.is_file() or not launcher.is_file():
        stage('Install the official launcher', 'Its installer opens separately. Review its terms there, then return here.')
        confirm('Open the official launcher installer now? You must review and accept any publisher terms yourself in its window.')
        log = work / 'official-installer.log'
        with log.open('a') as output:
            log.chmod(0o600)
            process = subprocess.Popen([config['wine'], str(work / 'dotnet31-runtime/dotnet.exe'), 'exec', 'Launcher.Installer.dll'], cwd=work / 'installer-net3132', env=wine_env(config), stdout=output, stderr=output)
        print('Finish the official installer. The original launcher may be black until the relay is opened.')
        prompt('Finish the official installer, then click Continue here.', 'continue')
        if not runner.is_file() or not launcher.is_file():
            raise RuntimeError('Expected official launcher files not found. Complete installation at its default path and rerun.')
    local = ROOT / 'config.local.json'
    def debug_port_busy():
        try:
            with socket.create_connection(('127.0.0.1',8088),timeout=1): return True
        except OSError: return False
    if debug_port_busy():
        prompt('Close the official launcher from your previous installation, then continue.', 'continue')
        if debug_port_busy(): raise RuntimeError('Port 8088 is still in use; active configuration was not changed.')
    confirm('Activate this isolated installation and build the launcher? Existing config will be backed up; your previous prefix is kept.')
    if local.exists():
        backup = work / ('config.previous-' + str(time.time_ns()) + '.json'); shutil.copyfile(local,backup); backup.chmod(0o600)
    local.write_text(json.dumps(config,indent=2)+'\n'); local.chmod(0o600)
    stage('Finishing setup', 'Building the launcher and window helper. Your previous installation is kept.')
    run([sys.executable,ROOT / 'build_native_frame_relay.py'],cwd=ROOT)
    # Custom icons are deferred in source development; see docs/deferred-icons.md.
    run([sys.executable,ROOT / 'start_native_frame_relay.py','--check-layout'],cwd=ROOT)
    event('complete', title='Ready to launch', detail='Open the launcher, sign in and install Lineage II. Windowed mode will be applied automatically before Play.', launch=True)
    print('Ready. Open Start-4game-Relay.command. Sign in and install Lineage II through the official launcher. After the game is installed and closed, run configure_game_window.py once for windowed mode.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped. Existing preparation is kept; rerun to resume.',file=sys.stderr)
        sys.exit(130)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        event('failed', message=str(error))
        print('Setup stopped: ' + str(error),file=sys.stderr)
        print('No game files or account profiles were uploaded. Existing preparation is kept.',file=sys.stderr)
        sys.exit(1)
