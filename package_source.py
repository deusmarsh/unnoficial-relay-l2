#!/usr/bin/env python3
"""Create an allowlisted source archive; never archive the working directory."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = (
    'dev', 'dev.py', 'Develop.command', 'test_dev.py', 'AGENTS.md', 'CONTRIBUTING.md',
    'docs/alpha-login.jpg', 'docs/gludio-world-entry.jpg', 'docs/character-selection.jpg', 'docs/world-loading.jpg', 'docs/architecture.md', 'docs/experiments.md', 'docs/deferred-icons.md',
    '.github/pull_request_template.md', '.github/ISSUE_TEMPLATE/bug_report.md', '.github/workflows/check.yml',
    'test_bundle.py', 'AppPaths.swift', 'app_paths.py', 'install_bundle.py', 'build_bundle.py', 'extract_python_licenses.py',
    'PROCESSES.md', 'TECHNICAL.md', 'SetupWizard.swift', 'bootstrap_setup.py', 'INSTALL.md', 'Install.command', 'install.py', 'dependencies.json', 'prepare_net3132.py',
    'GuardedMutexProbe.c', 'test_installer.py',
    'patches/winemac-background-app.patch', 'patches/sync.c.patch', 'patches/ntoskrnl.exe.spec.patch', 'patches/README.md',
    'licenses/WINE-LICENSE', 'licenses/WINE-COPYING.LIB',
    '.gitignore', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md',
    'NativeFrameRelay.swift', 'build_native_frame_relay.py',
    'run_stock_launcher.py', 'start_native_frame_relay.py', 'launcher_startup.py', 'launcher_connection.py', 'test_launcher.py',
    'Start-4game-Relay.command', 'cef-switches.txt', 'cef-direct-window.txt', 'config.example.json',
    'package_source.py', 'configure_game_window.py',
    'build_icons.swift', 'NativeLauncherWindow.c', 'launcher_window.py', 'configure_runtime_icon.py',
)

def main():
    for name in FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit('Missing or symlinked source: ' + name)
    output = ROOT / '.build' / 'lineage-macos-relay-source.zip'
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, 'lineage-macos-relay/' + name)
    print('Packaged', len(FILES), 'reviewed source files:', output)

if __name__ == '__main__':
    main()
