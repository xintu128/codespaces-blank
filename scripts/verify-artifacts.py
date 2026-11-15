#!/usr/bin/env python3
"""Check ARM64 Image format and storage-disable invariants in the real DTB."""
import argparse
import json
import struct
from pathlib import Path


def read_fdt(path):
    data = Path(path).read_bytes()
    magic, size, off_struct, off_strings = struct.unpack_from('>4I', data)
    assert magic == 0xD00DFEED and size == len(data), 'Invalid DTB header'
    pos, stack, nodes = off_struct, [], {}
    while True:
        token, = struct.unpack_from('>I', data, pos)
        pos += 4
        if token == 1:
            end = data.index(b'\0', pos)
            stack.append(data[pos:end].decode())
            pos = (end + 4) & ~3
            nodes['/'.join(stack) or '/'] = {}
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, name_offset = struct.unpack_from('>2I', data, pos)
            pos += 8
            start = off_strings + name_offset
            end = data.index(b'\0', start)
            nodes['/'.join(stack) or '/'][data[start:end].decode()] = data[pos:pos + length]
            pos = (pos + length + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            return nodes
        else:
            raise AssertionError(f'Invalid FDT token: {token}')


def check_dtb(path):
    nodes = read_fdt(path)
    for node in ('/mmc@fe2b0000', '/mmc@fe2c0000', '/mmc@fe310000',
                 '/i2c@fdd40000', '/i2c@fdd40000/pmic@20'):
        assert nodes[node]['status'] == b'disabled\0', f'Unexpected enabled hardware: {node}'
    assert b'rockchip,rk3566-telecom-notebook\0' in nodes['/']['compatible']
    return {'dtb_format': 'pass', 'v07_disabled_nodes': 'pass', 'hardware_boot_tested': False,
            'sd_boot_verified': False, 'bootloader_included': False,
            'internal_emmc_enabled': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--dtb-only', action='store_true')
    args = parser.parse_args()
    result = check_dtb(args.directory / 'rk3566-tyc4a.dtb')
    if not args.dtb_only:
        image = (args.directory / 'Image').read_bytes()
        assert len(image) > 1024 * 1024 and image[56:60] == b'ARM\x64', 'Invalid ARM64 Image'
        result['kernel_format'] = 'pass'
        result['kernel_release'] = (args.directory / 'kernelrelease').read_text().strip()
    (args.directory / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
