#!/usr/bin/env python3
"""Assemble a regular-file MBR image. Never open a device path."""
import argparse
import shutil
import stat
import struct
from pathlib import Path

OFFSET = 16 * 1024 * 1024
DISK_SIGNATURE = 0x74C4A007


def assemble(source, destination):
    source, destination = Path(source), Path(destination)
    assert stat.S_ISREG(source.stat().st_mode), 'Source must be a regular file'
    assert not destination.exists() and not destination.is_symlink(), 'Destination must be new'
    assert '/dev/' not in str(destination.resolve()), 'Devices are forbidden'
    size = source.stat().st_size
    assert size > 0 and size % 512 == 0
    assert (size + OFFSET) // 512 < 2**32
    mbr = bytearray(512)
    struct.pack_into('<I', mbr, 440, DISK_SIGNATURE)
    # One bootable Linux partition. LBA fields carry the actual geometry.
    struct.pack_into('<B3sB3sII', mbr, 446, 0x80, b'\xfe\xff\xff', 0x83,
                     b'\xfe\xff\xff', OFFSET // 512, size // 512)
    mbr[510:512] = b'\x55\xaa'
    with destination.open('xb') as output, source.open('rb') as content:
        output.write(mbr)
        output.seek(OFFSET)
        shutil.copyfileobj(content, output, 4 * 1024 * 1024)
    assert destination.stat().st_size == size + OFFSET


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    assemble(args.source, args.destination)
