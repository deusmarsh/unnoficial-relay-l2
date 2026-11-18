#!/usr/bin/env python3
"""One entry point for source development; uses the existing installer and builders."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
NATIVE_INPUTS = ('AppPaths.swift', 'NativeFrameRelay.swift', 'SetupWizard.swift',
                 'build_native_frame_relay.py', 'NativeLauncherWindow.c')
PATCHES = ('sync.c.patch', 'ntoskrnl.exe.spec.patch', 'winemac-background-app.patch')


def environment():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('LINEAGE_'):
            env.pop(key)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def run(*args):
    subprocess.run(list(map(str, args)), cwd=ROOT, env=environment(), check=True)


def script(name, *args):
    run(sys.executable, ROOT / name, *args)


def config():
    path = ROOT / 'config.local.json'
    if not path.is_file():
        raise RuntimeError('No development environment yet. Run ./dev setup first.')
    value = json.loads(path.read_text())
    for key in ('prefix', 'wine', 'wineserver', 'library_paths'):
        if key not in value:
            raise RuntimeError('Incomplete local configuration. Run ./dev setup.')
    return value


def runtime_matches(value):
    """A source-built runtime must match the currently published patches."""
    work = Path(value['prefix']).expanduser().resolve().parent
    marker = work / 'wine-source/wine-wine-10.0/.relay-patch'
    expected = hashlib.sha256(b''.join((ROOT / 'patches' / name).read_bytes()
                                      for name in PATCHES)).hexdigest()
    return marker.is_file() and marker.read_text().strip() == expected


def require_runtime(value):
    if not runtime_matches(value):
        raise RuntimeError('Wine patch provenance is missing or patches changed. Close the launcher/game, '
                           'then run ./dev setup --work-dir .local-rebuild-1 with a NEW dedicated directory. '
                           'The previous prefix and game are kept. See CONTRIBUTING.md.')


def build_key(value):
    digest = hashlib.sha256()
    for name in NATIVE_INPUTS:
        digest.update(name.encode())
        digest.update((ROOT / name).read_bytes())
    compiler = value.get('mingw_clang')
    if not compiler or not Path(compiler).is_file():
        raise RuntimeError('Development compiler missing. Run ./dev setup.')
    # Preserve the target-selecting compiler symlink name.
    digest.update(compiler.encode())
    stat = Path(compiler).stat()
    digest.update(str((stat.st_size, stat.st_mtime_ns)).encode())
    return digest.hexdigest()


def build(value):
    key = build_key(value)
    stamp = ROOT / '.build/dev-build.sha256'
    products = (ROOT / '4gameRelay.app/Contents/MacOS/4gameRelay',
                ROOT / '.build/NativeLauncherWindow.exe')
    if stamp.is_file() and stamp.read_text().strip() == key and all(p.is_file() for p in products):
        print('Native components are up to date.', flush=True)
        return
    # Invalidate before building so a partial failure can never look current.
    stamp.unlink(missing_ok=True)
    script('build_native_frame_relay.py')
    if not all(p.is_file() for p in products):
        raise RuntimeError('Build did not produce the native app and Windows helper.')
    stamp.write_text(key + '\n')


def doctor():
    problems = []
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        problems.append('Source runtime requires an Apple Silicon Mac.')
    if subprocess.run(['xcrun', '--find', 'swiftc'], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode:
        problems.append('Apple Command Line Tools missing: run ./dev setup.')
    if subprocess.run(['/usr/bin/arch', '-x86_64', '/usr/bin/true'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        problems.append('Rosetta missing: run ./dev setup.')
    value = config()
    for key in ('prefix', 'wine', 'wineserver'):
        if not Path(value[key]).expanduser().exists():
            problems.append('Missing configured ' + key + '; run ./dev setup.')
    for directory in value['library_paths']:
        if not Path(directory).expanduser().is_dir():
            problems.append('A runtime library directory is missing; run ./dev setup.')
    require_runtime(value)
    build_key(value)  # Validate compiler without rebuilding or launching.
    if problems:
        raise RuntimeError('\n'.join(problems))
    script('run_stock_launcher.py', '--check-layout')
    print('Development runtime and official launcher layout are ready. No game was launched.')


def check():
    from package_source import FILES
    for name in FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('Missing or symlinked publication source: ' + name)
        if path.suffix == '.py':
            ast.parse(path.read_text(), filename=name)
    # Bundle integration tests are deliberately excluded from the portable suite.
    env = environment()
    env.pop('LINEAGE_TEST_APP', None)
    subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v',
                    'test_installer', 'test_bundle', 'test_dev', 'test_launcher'],
                   cwd=ROOT, env=env, check=True)
    print('Portable checks passed. This does not establish game rendering or gameplay.')


def report():
    from package_source import FILES
    # Allowlist-only: never read config, logs, process arguments, accounts or environment values.
    data = {'format': 1, 'system': platform.system(), 'architecture': platform.machine(),
            'macos': platform.mac_ver()[0], 'python': platform.python_version(),
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in FILES},
            'manual_results': 'Fill in scenario, before/after result and checks not performed.'}
    output = ROOT / '.build/development-report.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + '\n')
    output.chmod(0o600)
    print('Wrote .build/development-report.json (source hashes and system versions only).')
    print('Review it before attaching. Raw runtime logs are intentionally excluded.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=('setup', 'run', 'doctor', 'check', 'report'))
    parser.add_argument('--work-dir', type=Path, help='Setup only: a new dedicated runtime directory.')
    parser.add_argument('--prepare-only', action='store_true', help='Setup only: runtime checks without activation.')
    parser.add_argument('--relay', action='store_true', help='Run only: use the legacy screenshot relay.')
    args = parser.parse_args()
    if args.action is None:
        if not sys.stdin.isatty():
            parser.print_help()
            return
        actions = ('setup', 'run', 'doctor', 'check', 'report')
        print('Lineage II development\n1. Set up / resume\n2. Run changed sources\n3. Diagnose\n4. Check\n5. Create report')
        answer = input('Choose 1–5 (Enter to exit): ').strip()
        if not answer:
            return
        if answer not in ('1', '2', '3', '4', '5'):
            parser.error('Choose a number from 1 to 5.')
        args.action = actions[int(answer) - 1]
    if args.action != 'setup' and (args.work_dir or args.prepare_only):
        parser.error('--work-dir and --prepare-only apply only to setup.')
    if args.relay and args.action != 'run':
        parser.error('--relay applies only to run.')
    if args.action == 'setup':
        extra = []
        if args.work_dir:
            extra += ['--work-dir', str(args.work_dir.expanduser().resolve())]
        if args.prepare_only:
            extra += ['--prepare-only']
        script('bootstrap_setup.py', *extra)
    elif args.action == 'run':
        value = config()
        require_runtime(value)
        build(value)
        script('start_native_frame_relay.py', *(['--relay'] if args.relay else []))
    elif args.action == 'doctor':
        doctor()
    elif args.action == 'check':
        check()
    elif args.action == 'report':
        report()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('Development command stopped: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
