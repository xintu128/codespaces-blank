#!/usr/bin/env python3
import importlib.util
import struct
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('assemble', Path(__file__).with_name('assemble-image.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source, output = root / 'rootfs.ext4', root / 'candidate.img'
    payload = bytes(range(256)) * 8
    source.write_bytes(payload)
    module.assemble(source, output)
    with output.open('rb') as image:
        mbr = image.read(512)
        assert mbr[510:] == b'\x55\xaa'
        assert struct.unpack_from('<I', mbr, 440)[0] == 0x74C4A007
        boot, _, kind, _, start, sectors = struct.unpack_from('<B3sB3sII', mbr, 446)
        assert (boot, kind, start, sectors) == (0x80, 0x83, 32768, 4)
        image.seek(start * 512)
        assert image.read() == payload
    try:
        module.assemble(source, output)
        raise RuntimeError('Overwriting an existing image must fail')
    except AssertionError:
        pass
    try:
        module.assemble(Path('/dev/null'), root / 'bad.img')
        raise RuntimeError('Device inputs must fail')
    except AssertionError:
        pass
    link = root / 'link.img'
    link.symlink_to(source)
    try:
        module.assemble(source, link)
        raise RuntimeError('Symlink outputs must fail')
    except AssertionError:
        pass
print('PASS: partition metadata, payload, overwrite guard and device guard')
