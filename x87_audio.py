#!/usr/bin/env python3
"""Opt in to pinned x87sidecar and audio on an existing Metal source installation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent


def dependency():
    return json.loads((ROOT / 'dependencies.json').read_text())['x87_sidecar']


def verified_sidecar(config):
    value = config.get('x87_audio')
    if not isinstance(value, dict) or not isinstance(value.get('sidecar'), str):
        raise RuntimeError('Invalid x87_audio configuration; disable it with x87_audio.py --disable.')
    path = Path(value['sidecar']).expanduser().resolve()
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != dependency()['binary_sha256']:
        raise RuntimeError('Pinned x87sidecar is missing or changed; run x87_audio.py again or --disable.')
    if not os.access(path, os.X_OK):
        raise RuntimeError('Pinned x87sidecar is not executable.')
    return path


def unpack_sidecar(archive, destination):
    from install import verify
    verify(archive, dependency())
    # Extract exactly one regular file, never archive links or arbitrary paths.
    with tarfile.open(archive) as bundle:
        member = bundle.getmember('x87sidecar')
        if not member.isfile():
            raise RuntimeError('Unexpected sidecar archive layout.')
        data = bundle.extractfile(member).read()
    if hashlib.sha256(data).hexdigest() != dependency()['binary_sha256']:
        raise RuntimeError('Sidecar binary hash mismatch; no downloaded code was run.')
    if destination.is_symlink():
        raise RuntimeError('Refusing a redirected sidecar destination.')
    destination.write_bytes(data)
    destination.chmod(0o755)


def stopped(config):
    from runtime_environment import wine_environment
    baseline = dict(config)
    baseline.pop('x87_audio', None)
    try:
        subprocess.run([config['wineserver'], '-w'], env=wine_environment(baseline),
                       check=True, timeout=2, capture_output=True)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Close this installation launcher/game before changing audio mode.')


def validate(config, work):
    from runtime_environment import wine_environment
    sidecar = verified_sidecar(config)
    env = wine_environment(config)
    probe = subprocess.run([str(sidecar), '--probe'], env=env, capture_output=True,
                           text=True, timeout=15)
    (work / 'rosetta-probe.log').write_text(probe.stdout + probe.stderr)
    if probe.returncode:
        raise RuntimeError('This Rosetta is unsupported; configuration was not activated.')
    compiler = Path(config['mingw_clang']).with_name('i686-w64-mingw32-clang')
    executable = work / 'X87AudioProbe.exe'
    subprocess.run([str(compiler), str(ROOT / 'MetalAudioProbe.c'), '-O2', '-o', str(executable),
                    '-ld3d9', '-lole32', '-luuid'], check=True, timeout=60)
    env['WINEDLLOVERRIDES'] += ';d3d9=n,b'
    env['X87_LOGS'] = '1'
    result = subprocess.run([config['wine'], str(executable), '--audio-enabled'], env=env,
                            capture_output=True, text=True, timeout=60)
    output = result.stdout + result.stderr
    (work / 'activation-probe.log').write_text(output)
    hooked = ('M2: receive thread running' in output
              and 'RUNNING WITHOUT X87 ACCELERATION' not in output)
    if result.returncode or 'X87_AUDIO_OK' not in output or not hooked:
        raise RuntimeError('x87/Metal/audio checks failed; configuration was not activated. See local probe logs.')
    summary = {'sidecar_version': dependency()['version'], 'rosetta_supported': True,
               'cooperative_hook_confirmed': True, 'metal_d3d9_present': True,
               'active_audio_endpoint': True, 'x87_numeric_check': True,
               'gameplay_checked_by_this_command': False}
    (work / 'validation.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('Verified cooperative x87, 32-bit Metal presentation and an active audio endpoint.')


def save(path, before, config):
    if path.is_symlink() or path.read_bytes() != before:
        raise RuntimeError('Configuration changed during validation; nothing was activated.')
    backup = path.parent / '.build/x87-audio-backups'
    backup.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ.json')
    (backup / name).write_bytes(before)
    fd, temporary = tempfile.mkstemp(prefix='.x87-audio-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(config, stream, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def activate(path, archive=None, disable=False):
    from runtime_environment import METAL_PROFILE
    from install import fetch
    import dev
    path = path.expanduser().resolve() if not path.is_symlink() else path
    if path.is_symlink():
        raise RuntimeError('Refusing a symlinked configuration.')
    before = path.read_bytes()
    config = json.loads(before)
    if config.get('runtime_profile') != METAL_PROFILE:
        raise RuntimeError('This opt-in requires an existing Metal source setup; run ./dev setup first.')
    stopped(config)
    if disable:
        config.pop('x87_audio', None)
        save(path, before, config)
        print('Restored the previous Metal/audio-disabled profile. Run ./dev run.')
        return
    dev.require_runtime(config)
    ntdll = Path(config['wine']).resolve().parent.parent / 'lib/wine/x86_64-unix/ntdll.so'
    if not ntdll.is_file() or b'ROSETTA_X87_PATH' not in ntdll.read_bytes():
        raise RuntimeError('Configured Wine lacks cooperative x87 support; do not substitute another runtime.')
    work = Path(config['prefix']).expanduser().resolve().parent / 'x87-audio'
    if work.is_symlink():
        raise RuntimeError('Refusing a redirected x87 work directory.')
    work.mkdir(exist_ok=True)
    archive = archive.expanduser().resolve() if archive else fetch(dependency(), work)
    destination = work / 'x87sidecar'
    unpack_sidecar(archive, destination)
    config['x87_audio'] = {'sidecar': str(destination), 'version': dependency()['version']}
    validate(config, work)
    from runtime_environment import wine_environment
    subprocess.run([config['wineserver'], '-w'], env=wine_environment(config),
                   check=True, timeout=15, capture_output=True)
    # Do not replace a configuration while a newly started game uses it.
    stopped(config)
    save(path, before, config)
    print('x87sidecar and audio enabled for this source installation. Run ./dev run.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'config.local.json')
    parser.add_argument('--archive', type=Path, help='Use a locally cached pinned archive; hashes are still checked.')
    parser.add_argument('--disable', action='store_true', help='Restore the previous audio-disabled profile.')
    args = parser.parse_args()
    if args.archive and args.disable:
        parser.error('--archive does not apply to --disable')
    try:
        activate(args.config, args.archive, args.disable)
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        raise SystemExit(str(error))


if __name__ == '__main__':
    main()
