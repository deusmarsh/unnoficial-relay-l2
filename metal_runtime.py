"""Reproduce the pinned x86-64 Metal runtime in a new prefix."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from runtime_environment import METAL_PROFILE

PATCHES = ('ntoskrnl.exe.spec.patch', 'sync.c.patch')
DEPENDENCIES = ('metal_engine', 'metal_renderer', 'metal_wine_source', 'support', 'compiler', 'bison')


def identity(root, manifest):
    value = {'profile': METAL_PROFILE,
             'dependencies': {key: manifest[key] for key in DEPENDENCIES},
             'patches': {name: hashlib.sha256((root / 'patches' / name).read_bytes()).hexdigest()
                         for name in PATCHES}}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def prepare(work, archives, jobs, setup):
    root = setup.ROOT
    expected = identity(root, setup.MANIFEST)
    stamp = work / '.metal-runtime-identity'
    if (work / 'prefix').exists() and not stamp.is_file():
        raise RuntimeError('This directory contains an older prefix; use a NEW dedicated --work-dir for Metal.')
    if stamp.exists() and stamp.read_text().strip() != expected:
        raise RuntimeError('Metal dependencies or patches changed; use a NEW dedicated --work-dir.')
    prepared = work / 'config.prepared.json'
    if (work / 'prefix').exists() and prepared.is_file():
        from runtime_environment import wine_environment
        config = json.loads(prepared.read_text())
        try:
            setup.subprocess.run([config['wineserver'], '-w'], env=wine_environment(config),
                                 timeout=2, check=True)
        except setup.subprocess.TimeoutExpired:
            raise RuntimeError('Close this installation launcher and game before resuming setup.')
    # Claim the recipe before modifying any extraction or runtime. Interrupted builds
    # may resume this identity, but cannot silently reuse a different recipe.
    stamp.write_text(expected + '\n')
    for key, folder in [('metal_engine', 'metal-engine'), ('metal_renderer', 'metal-renderer'),
                        ('metal_wine_source', 'crossover-source'), ('support', 'wine-support'),
                        ('compiler', 'toolchain'), ('bison', 'bison-source')]:
        setup.unpack(archives[key], work / folder)
    tools = list((work / 'toolchain').glob('llvm-mingw-*/bin/x86_64-w64-mingw32-clang'))
    if len(tools) != 1:
        raise RuntimeError('Unexpected LLVM-MinGW archive layout.')
    compiler = tools[0]
    env = os.environ.copy()
    env['PATH'] = str(compiler.parent) + os.pathsep + env.get('PATH', '/usr/bin:/bin')
    bison = work / 'bison'
    if not (bison / 'bin/bison').is_file():
        build = work / 'bison-build'
        build.mkdir(exist_ok=True)
        setup.run([work / 'bison-source/bison-3.8.2/configure', '--prefix=' + str(bison)], cwd=build, env=env)
        setup.run(['make', '-j' + str(jobs)], cwd=build, env=env)
        setup.run(['make', 'install'], cwd=build, env=env)
    env['PATH'] = str(bison / 'bin') + os.pathsep + env['PATH']
    env.update(CC='/usr/bin/clang -arch x86_64', CXX='/usr/bin/clang++ -arch x86_64',
               MACOSX_DEPLOYMENT_TARGET='13.0')
    source = work / 'crossover-source/sources/wine'
    for name in PATCHES:
        marker = source / ('.lineage-applied-' + name)
        patch = root / 'patches' / name
        if not marker.exists():
            setup.run(['/usr/bin/patch', '-p1', '--batch', '--dry-run', '-i', patch], cwd=source)
            setup.run(['/usr/bin/patch', '-p1', '--batch', '-i', patch], cwd=source)
            marker.write_text(setup.digest(patch, 'sha256'))
        elif marker.read_text() != setup.digest(patch, 'sha256'):
            raise RuntimeError('Applied Wine patch changed; use a NEW dedicated --work-dir.')
    build = work / 'metal-kernel-build'
    build.mkdir(exist_ok=True)
    if not (build / 'Makefile').exists():
        flags = ['--host=x86_64-apple-darwin', '--enable-archs=x86_64', '--disable-tests']
        flags += ['--without-' + name for name in
                  ('x', 'freetype', 'fontconfig', 'gnutls', 'gstreamer', 'vulkan', 'gettext', 'sdl', 'ffmpeg')]
        setup.run([source / 'configure', *flags], cwd=build, env=env)
    setup.run(['make', '-j' + str(jobs),
               'x86_64_CFLAGS=-g -O2 -ffile-prefix-map=' + str(source) + '=/wine-source -ffile-prefix-map=' + str(build) + '=/wine-build',
               'dlls/ntoskrnl.exe/x86_64-windows/ntoskrnl.exe'], cwd=build, env=env)
    engine = work / 'metal-engine/engine'
    tree = engine / 'lib/wine'
    shutil.copy2(build / 'dlls/ntoskrnl.exe/x86_64-windows/ntoskrnl.exe',
                 tree / 'x86_64-windows/ntoskrnl.exe')
    renderer = work / 'metal-renderer'
    for arch in ('i386-windows', 'x86_64-windows', 'x86_64-unix'):
        name = 'mtld3d.so' if arch.endswith('-unix') else 'mtld3d.dll'
        shutil.copy2(renderer / 'wine' / arch / name, tree / arch / name)
    libraries = work / 'libraries'
    setup.support_libraries(work / 'wine-support/Wine Devel.app/Contents/Resources/wine/lib', libraries)
    config = {'prefix': str(work / 'prefix'), 'wine': str(engine / 'bin/wine'),
              'wineserver': str(engine / 'bin/wineserver'),
              'library_paths': [str(engine / 'lib'), str(libraries)],
              'framework_path': str(work / 'metal-engine/frameworks'),
              'mingw_clang': str(compiler), 'runtime_profile': METAL_PROFILE,
              'runtime_identity': expected, 'metal_renderer_dir': str(renderer)}
    return config


def install_prefix(config, setup):
    """Called after wineboot; only in an installer-owned prefix before activation."""
    prefix = Path(config['prefix'])
    if not (prefix / setup.MARKER).is_file():
        raise RuntimeError('Refusing to install Metal into an unowned prefix.')
    renderer = Path(config['metal_renderer_dir'])
    for arch, folder in [('i386-windows', 'syswow64'), ('x86_64-windows', 'system32')]:
        destination = prefix / 'drive_c/windows' / folder
        shutil.copy2(renderer / 'native' / arch / 'd3d9.dll', destination / 'd3d9.dll')
        shutil.copy2(renderer / 'prefix-markers' / folder / 'mtld3d.dll', destination / 'mtld3d.dll')
    env = setup.wine_env(config)
    for exe in ('L2.exe', 'L2.bin'):
        key = 'HKCU\\Software\\Wine\\AppDefaults\\' + exe + '\\DllOverrides'
        setup.run([config['wine'], 'reg', 'add', key, '/v', 'd3d9', '/t', 'REG_SZ',
                   '/d', 'native,builtin', '/f'], env=env, timeout=60)


def source_defaults(work, config, archives, setup):
    """Stage the two validated components before Wine starts in a new setup."""
    import material_fix
    import x87_audio

    audio = work / 'x87-audio'
    audio.mkdir(exist_ok=True)
    sidecar = audio / 'x87sidecar'
    x87_audio.unpack_sidecar(archives['x87_sidecar'], sidecar)
    config = dict(config, x87_audio={'sidecar': str(sidecar), 'version': x87_audio.dependency()['version']})

    # The stock runtime stays available for material_fix.py --disable.
    # Publish the clone and its identity together so interrupted builds can resume.
    target = work / 'corrected-metal'
    runtime = target / 'runtime'
    manifest = setup.MANIFEST
    recipe = {'base': config['runtime_identity'],
              'source': manifest['metal_renderer_source'],
              'patch': material_fix.sha(material_fix.ROOT / material_fix.PATCH)}
    if not target.exists():
        cargo = work / 'cargo'
        rustup = work / 'rustup'
        env = dict(os.environ, CARGO_HOME=str(cargo), RUSTUP_HOME=str(rustup))
        installer = archives['rustup_init']
        installer.chmod(0o755)
        stable = manifest['metal_renderer_source']['rust_stable']
        setup.run([installer, '-y', '--no-modify-path', '--profile', 'minimal',
                   '--default-toolchain', stable, '--component', 'llvm-tools-preview',
                   '--target', 'x86_64-apple-darwin'], env=env)
        native = material_fix.build_library(config, work / 'material-build',
                                             archives['metal_renderer_source'], cargo, rustup, test_tools=False)
        with tempfile.TemporaryDirectory(dir=work) as tmp:
            stage = Path(tmp) / 'corrected-metal'
            stage.mkdir()
            installed = material_fix.install_library(config, stage / 'runtime', native)
            (stage / 'build.json').write_text(json.dumps({'recipe': recipe, 'sha256': material_fix.sha(installed)}))
            stage.rename(target)
    record = json.loads((target / 'build.json').read_text())
    if record['recipe'] != recipe:
        raise RuntimeError('The prepared material build has changed. Use a new setup work directory.')
    native = runtime / 'lib/wine/x86_64-unix/mtld3d.so'
    result = material_fix.candidate(config, runtime, native)
    if result['material_fix']['native_sha256'] != record['sha256']:
        raise RuntimeError('Prepared material renderer checksum mismatch.')
    material_fix.verify_renderer(result)
    x87_audio.verified_sidecar(result)
    return result
