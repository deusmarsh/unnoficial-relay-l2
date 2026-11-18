"""Prepare publisher-owned updater files locally and add one pinned missing root CA."""
import hashlib
import io
import os
from pathlib import Path
import re
import ssl
import struct
import tempfile
import zipfile

ROOT_CA = Path(__file__).with_name('certificates') / 'isrg-root-x1.pem'
ROOT_SHA256 = '96bcec06264976f37460779acf28c5a7cfe8a3c0aae11a8ffcee05c0bddf08c6'
UPDATER_FILES = frozenset(('4updater.exe', '4updater.properties', 'libeay32.dll',
    'msvcp120.dll', 'msvcr120.dll', 'PocoCrypto.dll', 'PocoFoundation.dll',
    'PocoNet.dll', 'PocoNetSSL.dll', 'PocoUtil.dll', 'rootcert.ca', 'ssleay32.dll'))


def certificates(data):
    for pem in re.findall(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', data, re.S):
        yield ssl.PEM_cert_to_DER_cert(pem.decode('ascii'))


def atomic_write(path, data):
    if path.is_symlink():
        raise RuntimeError('Refusing a linked updater file: ' + path.name)
    fd, temporary = tempfile.mkstemp(prefix='.ca-prepare-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def updater_payload(assembly):
    """Read the updater ZIP resource without modifying or executing the assembly."""
    data = assembly.read_bytes()
    offset = 0
    while True:
        end = data.find(b'PK\x05\x06', offset)
        if end < 0:
            raise RuntimeError('Publisher updater ZIP resource not found.')
        offset = end + 4
        if end + 22 > len(data):
            continue
        length = struct.unpack_from('<H', data, end + 20)[0]
        try:
            with zipfile.ZipFile(io.BytesIO(data[:end + 22 + length])) as archive:
                entries = archive.infolist()
                names = [entry.filename for entry in entries]
                if '4updater.exe' not in names:
                    continue
                if len(names) != len(UPDATER_FILES) or set(names) != UPDATER_FILES:
                    raise RuntimeError('Unexpected publisher updater ZIP contents.')
                if sum(entry.file_size for entry in entries) > 32 * 1024 * 1024:
                    raise RuntimeError('Publisher updater ZIP exceeds expected size.')
                if any(entry.is_dir() or (entry.external_attr >> 16) & 0o170000 == 0o120000 for entry in entries):
                    raise RuntimeError('Linked or directory entry in publisher updater ZIP.')
                return {name: archive.read(name) for name in names}
        except zipfile.BadZipFile:
            continue


def prepare_updater_ca(application_dir):
    """Called before installer/launcher startup, including lazy updater extraction.

    Publisher code extracts its resource only when forgameUpdater/4updater.exe is
    absent. Preparing that same directory first keeps our CA addition in place.
    Existing executables, SSL settings and unrelated certificates are preserved.
    """
    application_dir = Path(application_dir)
    if application_dir.is_symlink():
        raise RuntimeError('Refusing a linked launcher directory.')
    pem = ROOT_CA.read_bytes()
    roots = list(certificates(pem))
    if len(roots) != 1 or hashlib.sha256(roots[0]).hexdigest() != ROOT_SHA256:
        raise RuntimeError('Bundled ISRG Root X1 fingerprint mismatch.')
    updater = application_dir / 'forgameUpdater'
    if updater.is_symlink():
        raise RuntimeError('Refusing a linked updater directory.')
    executable = updater / '4updater.exe'
    if executable.is_symlink():
        raise RuntimeError('Refusing a linked updater executable.')
    payload = None
    if not executable.is_file():
        assembly = application_dir / 'Launcher.Updater.Core.dll'
        if not assembly.is_file():
            raise RuntimeError('Publisher updater assembly is missing.')
        payload = updater_payload(assembly)
    updater.mkdir(exist_ok=True)
    ca = updater / 'rootcert.ca'
    if ca.is_symlink():
        raise RuntimeError('Refusing a linked updater CA file.')
    current = payload['rootcert.ca'] if payload is not None else ca.read_bytes()
    updated = current if roots[0] in certificates(current) else current.rstrip() + b'\n' + pem
    if payload is not None:
        # Validate all destinations before writing; publish the executable last.
        if any((updater / name).is_symlink() for name in payload):
            raise RuntimeError('Refusing a linked updater payload destination.')
        for name, content in payload.items():
            if name not in ('4updater.exe', 'rootcert.ca'):
                atomic_write(updater / name, content)
        atomic_write(ca, updated)
        atomic_write(executable, payload['4updater.exe'])
    elif updated != current:
        atomic_write(ca, updated)
    return ca
