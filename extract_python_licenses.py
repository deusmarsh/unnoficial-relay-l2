#!/usr/bin/env python3
"""Maintainer utility: extract notices from the pinned full Python archive using libzstd."""
import ctypes
import json
from pathlib import Path
import sys
import tarfile


def main():
    archive, library, output = map(Path, sys.argv[1:])
    output.mkdir(parents=True,exist_ok=True)
    decoded = output/'python-full.tar'
    z=ctypes.CDLL(str(library))
    class Buffer(ctypes.Structure):
        _fields_=[('data',ctypes.c_void_p),('size',ctypes.c_size_t),('pos',ctypes.c_size_t)]
    z.ZSTD_createDStream.restype=ctypes.c_void_p
    z.ZSTD_initDStream.argtypes=[ctypes.c_void_p];z.ZSTD_initDStream.restype=ctypes.c_size_t
    z.ZSTD_decompressStream.argtypes=[ctypes.c_void_p,ctypes.POINTER(Buffer),ctypes.POINTER(Buffer)];z.ZSTD_decompressStream.restype=ctypes.c_size_t
    z.ZSTD_isError.argtypes=[ctypes.c_size_t];z.ZSTD_isError.restype=ctypes.c_uint
    z.ZSTD_freeDStream.argtypes=[ctypes.c_void_p]
    ctx=z.ZSTD_createDStream();z.ZSTD_initDStream(ctx)
    remaining=1
    try:
        with archive.open('rb') as src,decoded.open('wb') as dst:
            for chunk in iter(lambda:src.read(1024*1024),b''):
                block=ctypes.create_string_buffer(chunk);inp=Buffer(ctypes.cast(block,ctypes.c_void_p),len(chunk),0)
                while inp.pos<inp.size:
                    storage=ctypes.create_string_buffer(1024*1024);out=Buffer(ctypes.cast(storage,ctypes.c_void_p),len(storage),0)
                    remaining=z.ZSTD_decompressStream(ctx,ctypes.byref(out),ctypes.byref(inp))
                    if z.ZSTD_isError(remaining):raise RuntimeError('Zstandard decompression failed.')
                    dst.write(storage.raw[:out.pos])
        if remaining:raise RuntimeError('Truncated compressed archive.')
    finally:z.ZSTD_freeDStream(ctx)
    count=0
    with tarfile.open(decoded) as tar:
        for member in tar.getmembers():
            if member.isfile() and (member.name=='python/PYTHON.json' or member.name.startswith('python/licenses/')):
                relative=Path(member.name).relative_to('python')
                if '..' in relative.parts:raise RuntimeError('Unsafe notice path.')
                target=output/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read());count+=1
    if not (output/'PYTHON.json').is_file():raise RuntimeError('Python metadata missing.')
    print('Extracted Python metadata/notices:',count)

if __name__=='__main__':main()
