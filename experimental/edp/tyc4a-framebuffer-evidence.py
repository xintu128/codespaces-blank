#!/usr/bin/env python3
"""Read the active fbdev surface without changing its mode or pixels."""
import fcntl
import json
import os
from pathlib import Path
import struct
import sys

if os.uname().release != '6.18.63-tyc4a-edp01':
    raise SystemExit('This recorder is limited to the experimental TYC4A kernel')
directory = Path(sys.argv[1])
with open('/dev/fb0', 'rb', buffering=0) as framebuffer:
    variable = bytearray(160)
    fixed = bytearray(80)
    fcntl.ioctl(framebuffer, 0x4600, variable, True)  # FBIOGET_VSCREENINFO
    fcntl.ioctl(framebuffer, 0x4602, fixed, True)  # FBIOGET_FSCREENINFO
    values = struct.unpack('<40I', variable)
    metadata = dict(zip(('width', 'height', 'virtual_width', 'virtual_height',
                         'xoffset', 'yoffset', 'bits_per_pixel', 'grayscale'), values[:8]))
    for index, name in enumerate(('red', 'green', 'blue', 'alpha')):
        metadata[name] = dict(zip(('offset', 'length', 'msb_right'), values[8 + index * 3:11 + index * 3]))
    metadata['stride'] = struct.unpack_from('<I', fixed, 48)[0]
    metadata['memory_length'] = struct.unpack_from('<I', fixed, 24)[0]
    metadata['id'] = bytes(fixed[:16]).split(b'\0', 1)[0].decode(errors='replace')
    metadata['fixed_info_hex'] = fixed.hex()
    metadata['variable_info_hex'] = variable.hex()
    (directory / 'framebuffer.json').write_text(json.dumps(metadata, indent=2) + '\n')
    remaining = min(metadata['memory_length'], 16 * 1024 * 1024)
    with open(directory / 'framebuffer.bin', 'wb') as output:
        while remaining:
            block = framebuffer.read(min(remaining, 1024 * 1024))
            if not block:
                break
            output.write(block)
            remaining -= len(block)
