#!/usr/bin/env python3
"""Build the scoped mtld3d material fix and activate a separate runtime copy."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
PATCH = 'patches/mtld3d-zero-multiply.patch'
RUNTIME_KEYS = ('wine', 'wineserver', 'library_paths')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_renderer(config):
    value = config.get('material_fix')
    if not isinstance(value, dict) or value.get('patch_sha256') != sha(ROOT / PATCH):
        raise RuntimeError('Material patch provenance changed; rebuild with material_fix.py or --disable.')
    native = Path(config['wine']).resolve().parent.parent / 'lib/wine/x86_64-unix/mtld3d.so'
    if not native.is_file() or sha(native) != value.get('native_sha256'):
        raise RuntimeError('Configured material-fix renderer is missing or changed.')


def candidate(config, runtime, native):
    previous = {key: config[key] for key in RUNTIME_KEYS}
    old = Path(config['wine']).resolve().parent.parent
    result = dict(config)
    result.update(wine=str(runtime / 'bin/wine'), wineserver=str(runtime / 'bin/wineserver'))
    result['library_paths'] = [str(runtime / Path(p).resolve().relative_to(old))
                               if Path(p).resolve().is_relative_to(old) else p
                               for p in config['library_paths']]
    result['material_fix'] = {'patch_sha256': sha(ROOT / PATCH), 'native_sha256': sha(native),
                              'previous_runtime': previous, 'upstream': 'mtld3d v0.15.5'}
    return result


def clone_runtime(source, destination):
    if destination.exists():
        raise RuntimeError('Runtime copy already exists; choose a new --work-dir.')
    libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    libc.clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    libc.clonefile.restype = ctypes.c_int
    if libc.clonefile(os.fsencode(source), os.fsencode(destination), 0):
        shutil.copytree(source, destination, symlinks=True)


def activate(path, work, archive, cargo_home=None, rustup_home=None, disable=False):
    import dev
    import install
    import metal_runtime
    from runtime_environment import METAL_PROFILE, wine_environment
    from x87_audio import save, stopped
    if path.is_symlink():
        raise RuntimeError('Refusing a symlinked configuration.')
    path = path.expanduser().resolve()
    before = path.read_bytes()
    config = json.loads(before)
    if config.get('runtime_profile') != METAL_PROFILE:
        raise RuntimeError('This fix requires an existing Metal source installation.')
    stop_config = dict(config)
    if disable:
        stop_config.pop('material_fix', None)
    stopped(stop_config)
    if disable:
        value = config.pop('material_fix', None)
        if not value:
            raise RuntimeError('No material-fix activation to undo.')
        config.update(value['previous_runtime'])
        save(path, before, config)
        print('Previous runtime restored; the material-fix copy is retained.')
        return
    if config.get('material_fix'):
        raise RuntimeError('A material fix is already active; --disable it before another build.')
    dev.require_runtime(config)
    item = install.MANIFEST['metal_renderer_source']
    work = work.expanduser().resolve()
    if work.is_relative_to(Path(config['wine']).resolve().parent.parent):
        raise RuntimeError('Choose a work directory outside the active runtime.')
    if work.exists() and not (work / '.material-build').is_file():
        raise RuntimeError('Refusing an unowned work directory.')
    work.mkdir(parents=True, exist_ok=True)
    (work / '.material-build').write_text('Owned material source build\n')
    env = os.environ.copy()
    if cargo_home:
        env['CARGO_HOME'] = str(cargo_home.expanduser().resolve())
        env['PATH'] = str(cargo_home.expanduser().resolve() / 'bin') + os.pathsep + env.get('PATH', '')
    if rustup_home:
        env['RUSTUP_HOME'] = str(rustup_home.expanduser().resolve())
    # Fail before changing a runtime or config when the pinned toolchains are absent.
    install.run(['cargo', '+' + item['rust_stable'], '--version'], env=env)
    archive = archive.expanduser().resolve() if archive else install.fetch(item, work)
    install.verify(archive, item)
    install.unpack(archive, work / 'source')
    source = work / 'source/mtld3d-0.15.5'
    marker = source / '.lineage-material-patch'
    if not marker.exists():
        install.run(['/usr/bin/patch', '-p1', '--batch', '--dry-run', '-i', ROOT / PATCH], cwd=source)
        install.run(['/usr/bin/patch', '-p1', '--batch', '-i', ROOT / PATCH], cwd=source)
        marker.write_text(sha(ROOT / PATCH))
    elif marker.read_text() != sha(ROOT / PATCH):
        raise RuntimeError('Applied patch differs; use a new work directory.')
    locks = {p: sha(source / p) for p in ('windows/Cargo.lock', 'unix/Cargo.lock')}
    stable = '+' + item['rust_stable']
    commands = [
        ['cargo', stable, 'test', '--locked', '--manifest-path', 'windows/Cargo.toml',
         '-p', 'mtld3d-core', '-p', 'mtld3d-types', '--features', 'mtld3d-core/disk-cache',
         '--target', 'aarch64-apple-darwin'],
        ['cargo', stable, 'test', '--locked', '--manifest-path', 'unix/Cargo.toml'],
    ]
    make = ['make', 'RUST_STABLE=' + item['rust_stable'], 'RUST_NIGHTLY=' + item['rust_nightly'],
            'WINE_SDK=' + str(Path(config['wine']).resolve().parent.parent), 'WINE_INSTALL_DIR=', 'PROD=1']
    commands += [make + ['unix-x64'], make + ['production-assert-gate',
                  'ASSERT_GATE_FILES=unix/target/x86_64-apple-darwin/production/mtld3d.so']]
    with (work / 'build.log').open('w') as log:
        for command in commands:
            print('Checking/building: ' + ' '.join(command[:5]), flush=True)
            subprocess.run(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    if any(sha(source / p) != expected for p, expected in locks.items()):
        raise RuntimeError('Cargo lockfile changed; configuration was not activated.')
    native = source / 'unix/target/x86_64-apple-darwin/production/mtld3d.so'
    def exports(path):
        text = subprocess.check_output(['/usr/bin/nm', '-gU', str(path)], text=True)
        return {line.split()[-1] for line in text.splitlines() if line.split()}
    original = Path(config['wine']).resolve().parent.parent / 'lib/wine/x86_64-unix/mtld3d.so'
    symbols = exports(native)
    if not symbols or symbols != exports(original):
        raise RuntimeError('Native renderer exports differ; configuration was not activated.')
    runtime = work / 'runtime'
    clone_runtime(Path(config['wine']).resolve().parent.parent, runtime)
    destination = runtime / 'lib/wine/x86_64-unix/mtld3d.so'
    if not destination.resolve().is_relative_to(runtime):
        raise RuntimeError('Renderer destination redirects outside runtime copy.')
    shutil.copy2(native, destination)
    install.run(['codesign', '--force', '--sign', '-', destination])
    result = candidate(config, runtime, destination)
    verify_renderer(result)
    # Real device/presentation probe on the new library; respect the current audio mode.
    compiler = Path(config['mingw_clang']).with_name('i686-w64-mingw32-clang')
    probe = work / 'MaterialMetalProbe.exe'
    install.run([compiler, ROOT / 'MetalAudioProbe.c', '-O2', '-o', probe, '-ld3d9', '-lole32', '-luuid'])
    probe_env = wine_environment(result)
    probe_env['WINEDLLOVERRIDES'] += ';d3d9=n,b'
    command = [result['wine'], str(probe)] + (['--audio-enabled'] if result.get('x87_audio') else [])
    checked = subprocess.run(command, env=probe_env, capture_output=True, text=True, timeout=90)
    (work / 'metal-probe.log').write_text(checked.stdout + checked.stderr)
    checked.check_returncode()
    if not any(token in checked.stdout for token in ('METAL_AUDIO_OK', 'X87_AUDIO_OK')):
        raise RuntimeError('Metal presentation check failed; configuration was not activated.')
    subprocess.run([result['wineserver'], '-w'], env=probe_env, check=True, timeout=15)
    stopped(result)
    save(path, before, result)
    (work / 'validation.json').write_text(json.dumps({'upstream': 'mtld3d v0.15.5',
        'patch_sha256': sha(ROOT / PATCH), 'native_sha256': sha(destination),
        'core_and_unix_tests': 'passed', 'production_assert_gate': 'passed',
        'exports_match': True, 'real_metal_present': 'passed', 'original_runtime_modified': False}, indent=2) + '\n')
    print('Material fix active in a separate runtime. Run ./dev run. Reconnect is unchanged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'config.local.json')
    parser.add_argument('--work-dir', type=Path, default=ROOT / '.local-material-fix-v1')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--cargo-home', type=Path)
    parser.add_argument('--rustup-home', type=Path)
    parser.add_argument('--disable', action='store_true')
    args = parser.parse_args()
    try:
        activate(args.config, args.work_dir, args.archive, args.cargo_home, args.rustup_home, args.disable)
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        raise SystemExit(str(error))


if __name__ == '__main__':
    main()
