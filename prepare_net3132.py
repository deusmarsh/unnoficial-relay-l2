#!/usr/bin/env python3
"""Prepare an isolated installer experiment with .NET 3.1.32 x86.

Does not run the installer, change the original file, or modify a Wine prefix.
The original self-contained WPF application is extracted in full. Only files
supplied by the Microsoft.NETCore.App 3.1.32 runtime are overlaid in that copy.
WindowsDesktop assemblies remain the original 3.1.7 versions. Compatibility
of this mixed patch-level self-contained layout is experimental and untested.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import struct
import zipfile

INSTALLER_SHA256 = 'f9606fbcd2adf2339a2d8d78ea13d2bf2d7f08d1f9537958b0feeda770d888c0'
RUNTIME_SHA512 = '3cddda423359bc178dd5df8695a0b98c69c39ce846d53c316eda1436837147ba863ab01a606c72c9fae47fb82890a69a3c1916b1c4fdc1590c7113026617cf09'
BUNDLE_SIGNATURE = bytes.fromhex('8b1202b96a612038727b930214d7a03213f5b9e6efae3318ee3b2dce24b36aae')


def safe_path(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError('Unsafe bundle path')
    return root.joinpath(*relative.parts)


def prepare(installer, runtime, target):
    original = installer.read_bytes()
    if hashlib.sha256(original).hexdigest() not in (INSTALLER_SHA256, 'a478274ade8465c5da55b63dec15fb9f628d6b622615c2775d42a8f354d78cd0'):
        raise ValueError('Installer differs from the researched original')
    if hashlib.sha512(runtime.read_bytes()).hexdigest() != RUNTIME_SHA512:
        raise ValueError('Runtime does not match Microsoft release metadata')
    marker = target / 'PREPARED-BY-LINEAGE-MAC-LAB'
    if target.exists() and any(target.iterdir()) and not marker.is_file():
        raise ValueError('Refusing to use a nonempty unowned output directory')
    target.mkdir(parents=True, exist_ok=True)
    marker.write_text('Installer runtime experiment; no success claimed.\n')
    signature = original.find(BUNDLE_SIGNATURE)
    if signature < 8:
        raise ValueError('Bundle signature missing')
    header = struct.unpack_from('<Q', original, signature - 8)[0]
    stream = io.BytesIO(original)
    stream.seek(header)

    def read(fmt):
        return struct.unpack(fmt, stream.read(struct.calcsize(fmt)))

    def string():
        length = shift = 0
        while True:
            value = stream.read(1)[0]
            length |= (value & 127) << shift
            shift += 7
            if value < 128:
                return stream.read(length).decode('utf-8')

    major, minor, count = read('<IIi')
    if (major, minor) != (1, 0) or count != 529:
        raise ValueError('Unexpected bundle layout')
    string()
    for _ in range(count):
        offset, size = read('<qq')
        read('<B')
        name = string()
        if not (0 <= offset <= offset + size <= len(original)):
            raise ValueError('Invalid bundle range')
        path = safe_path(target, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original[offset:offset + size])
    overlaid = 0
    deps = json.loads((target / 'Launcher.Installer.deps.json').read_text())
    desktop_files = set()
    for packages in deps['targets'].values():
        for name, assets in packages.items():
            if name.startswith('runtimepack.Microsoft.WindowsDesktop.App.Runtime.'):
                for kind in ('runtime', 'native'):
                    desktop_files.update(assets.get(kind, {}))
    runtime_root = target.parent / 'dotnet31-runtime'
    runtime_marker = runtime_root / 'PREPARED-BY-LINEAGE-MAC-LAB'
    if runtime_root.exists() and any(runtime_root.iterdir()) and not runtime_marker.is_file():
        raise ValueError('Refusing an unowned runtime directory')
    runtime_root.mkdir(exist_ok=True)
    runtime_marker.write_text('Clean official Microsoft .NET 3.1.32 x86 runtime layout\n')
    with zipfile.ZipFile(runtime) as archive:
        prefix = 'shared/Microsoft.NETCore.App/3.1.32/'
        for item in archive.infolist():
            if item.is_dir():
                continue
            path = safe_path(target, item.filename)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read(item)
            path.write_bytes(data)
            clean_runtime_file = safe_path(runtime_root, item.filename)
            clean_runtime_file.parent.mkdir(parents=True, exist_ok=True)
            clean_runtime_file.write_bytes(data)
            if item.filename.startswith(prefix):
                relative = item.filename[len(prefix):]
                # Core runtime contains a WindowsBase facade; WPF requires
                # the implementation shipped by WindowsDesktop instead.
                if relative in desktop_files:
                    continue
                local = safe_path(target, relative)
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_bytes(data)
                overlaid += 1
        # The extracted self-contained bundle also has a root hostfxr.dll.
        # dotnet.exe may prefer that app-local resolver over host/fxr/3.1.32.
        # Upgrade it too, so an old 3.1.7 resolver is not left beside the host.
        (target / 'hostfxr.dll').write_bytes(archive.read('host/fxr/3.1.32/hostfxr.dll'))
    if (runtime_root / 'coreclr.dll').exists():
        raise ValueError('Runtime root contains unexpected app-local CoreCLR')
    print(f'Extracted {count} bundle entries; overlaid {overlaid} verified runtime files.')
    print('Prepared only, not executed:', target.resolve())
    print('Use the clean dotnet host in:', runtime_root.resolve())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installer', type=Path)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('--target', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.installer, args.runtime, args.target)


if __name__ == '__main__':
    main()
