#!/usr/bin/env python3
"""Validate this TYC4A's vendor loaders and add them to a regular SD image."""
import argparse
import hashlib
import json
import shutil
import stat
import struct
import tempfile
import zlib
from pathlib import Path

SECTOR = 512
ROOT_OFFSET = 16 * 1024 * 1024
SLOT_SIZE = 512 * 1024
SLOT_OFFSETS = [32768 + i * SLOT_SIZE for i in range(5)]
UBOOT_OFFSET = 8 * 1024 * 1024
UBOOT_SIZE = 4 * 1024 * 1024
IDB_SHA256 = "e8bd07500a80244b4e0ec36a5f8122e3e1516ec7792f0761e26aa0e8fbaa57da"
UBOOT_SHA256 = "3faf5a1febc269121dbb49b0c14c4c4c215c47f062a5485f2cbd6ced61a442d1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular(path):
    path = Path(path)
    require(stat.S_ISREG(path.stat().st_mode), f"Expected a regular file: {path}")
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fdt_nodes(data):
    magic, total, pos, strings = struct.unpack_from(">4I", data)
    require(magic == 0xD00DFEED and total <= len(data), "Invalid FIT tree")
    stack, nodes = [], {}
    while True:
        token, = struct.unpack_from(">I", data, pos)
        pos += 4
        if token == 1:
            end = data.index(b"\0", pos)
            stack.append(data[pos:end].decode())
            pos = (end + 4) & ~3
            nodes["/".join(stack) or "/"] = {}
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, name = struct.unpack_from(">2I", data, pos)
            pos += 8
            start = strings + name
            end = data.index(b"\0", start)
            nodes["/".join(stack) or "/"][data[start:end].decode()] = data[pos:pos + length]
            pos = (pos + length + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            return nodes
        else:
            raise ValueError("Invalid FIT token")


def verify_idb(data):
    require(len(data) == SLOT_SIZE and digest(data) == IDB_SHA256,
            "IDB differs from the validated TYC4A loader")
    magic, = struct.unpack_from("<I", data)
    header, flags = struct.unpack_from("<II", data, 8)
    count, hash_offset = header >> 16, (header & 0xFFFF) * 4
    require(magic == 0x534E4B52 and count == 2 and flags == 1, "Unexpected RKNS header")
    require(hashlib.sha256(data[:hash_offset]).digest() == data[hash_offset:hash_offset + 32],
            "RKNS header hash mismatch")
    images = []
    for index in range(count):
        entry = 120 + index * 88
        value, = struct.unpack_from("<I", data, entry)
        offset, size = (value & 0xFFFF) * SECTOR, (value >> 16) * SECTOR
        require(offset >= 2048 and size > 0 and offset + size <= SLOT_SIZE, "Invalid RKNS image range")
        calculated = hashlib.sha256(data[offset:offset + size]).digest()
        require(calculated == data[entry + 24:entry + 56], "RKNS payload hash mismatch")
        images.append({"offset": offset, "bytes": size, "sha256": calculated.hex()})
    return images


def verify_uboot(data):
    require(len(data) == UBOOT_SIZE and digest(data) == UBOOT_SHA256,
            "U-Boot differs from the validated TYC4A firmware")
    require(data[:UBOOT_SIZE // 2] == data[UBOOT_SIZE // 2:], "U-Boot copies differ")
    checked = []
    for base in (0, UBOOT_SIZE // 2):
        tree_size, = struct.unpack_from(">I", data, base + 4)
        require(40 <= tree_size <= 4096, "Unexpected FIT tree size")
        nodes = fdt_nodes(data[base:base + tree_size])
        require(not any("signature" in name and props.get("value")
                        for name, props in nodes.items()),
                "This tool does not verify cryptographic FIT signatures")
        images = []
        for name, props in nodes.items():
            if "data-position" not in props:
                continue
            offset, = struct.unpack(">I", props["data-position"])
            size, = struct.unpack(">I", props["data-size"])
            require(4096 <= offset and size > 0 and offset + size <= UBOOT_SIZE // 2,
                    "Invalid FIT payload range")
            expected = nodes[name + "/hash"]
            require(expected["algo"] == b"sha256\0", "Unsupported FIT hash")
            actual = hashlib.sha256(data[base + offset:base + offset + size]).digest()
            require(actual == expected["value"], f"FIT hash mismatch: {name}")
            images.append(name)
        require(len(images) == 9, "Unexpected FIT image count")
        checked.append({"offset": base, "validated_images": images})
    return checked


def extract(backup, destination):
    backup = regular(backup)
    with backup.open("rb") as source:
        prefix = source.read(ROOT_OFFSET)
    require(len(prefix) == ROOT_OFFSET, "Backup is too short for the loader region")
    require(prefix[512:520] == b"EFI PART", "Expected the original GPT")
    header_size, = struct.unpack_from("<I", prefix, 524)
    require(92 <= header_size <= 512, "Invalid GPT header size")
    header = bytearray(prefix[512:512 + header_size])
    expected_crc, = struct.unpack_from("<I", header, 16)
    header[16:20] = bytes(4)
    require(zlib.crc32(header) == expected_crc, "GPT header CRC mismatch")
    entries_lba, count, entry_size, entries_crc = struct.unpack_from("<QIII", prefix, 584)
    require(count <= 128 and entry_size == 128, "Unexpected GPT entry layout")
    entries = prefix[entries_lba * SECTOR:entries_lba * SECTOR + count * entry_size]
    require(zlib.crc32(entries) == entries_crc, "GPT entries CRC mismatch")
    partitions = {}
    for offset in range(0, len(entries), entry_size):
        entry = entries[offset:offset + entry_size]
        if any(entry[:16]):
            name = entry[56:].decode("utf-16le").rstrip("\0")
            first, last = struct.unpack_from("<QQ", entry, 32)
            partitions[name] = (first, last)
    require(partitions.get("uboot") == (16384, 24575), "Unexpected U-Boot partition")
    idb = prefix[SLOT_OFFSETS[0]:SLOT_OFFSETS[0] + SLOT_SIZE]
    idb_images = verify_idb(idb)
    require(all(prefix[offset:offset + SLOT_SIZE] == idb for offset in SLOT_OFFSETS),
            "Loader redundancy slots differ")
    uboot = prefix[UBOOT_OFFSET:UBOOT_OFFSET + UBOOT_SIZE]
    fits = verify_uboot(uboot)
    require(not any(prefix[12 * 1024 * 1024:ROOT_OFFSET]), "Unexpected separate trust payload")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "idbloader-slot.bin").write_bytes(idb)
    (destination / "uboot.img").write_bytes(uboot)
    last_lba, = struct.unpack_from("<Q", prefix, 544)
    expected_size = (last_lba + 1) * SECTOR
    report = {
        "source_backup_bytes": backup.stat().st_size,
        "original_device_bytes": expected_size,
        "backup_is_complete": backup.stat().st_size == expected_size,
        "gpt_crc": "pass",
        "idb_sha256": digest(idb), "idb_images": idb_images,
        "idb_slots": SLOT_OFFSETS, "uboot_sha256": digest(uboot),
        "fit_copies": fits, "bootcmd_modified": False, "hardware_boot_tested": False,
    }
    (destination / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify_bundle(bundle):
    bundle = Path(bundle)
    idb = regular(bundle / "idbloader-slot.bin").read_bytes()
    uboot = regular(bundle / "uboot.img").read_bytes()
    verify_idb(idb)
    verify_uboot(uboot)
    return idb, uboot


def hash_tail(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        stream.seek(ROOT_OFFSET)
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def apply(base, bundle, destination):
    base = regular(base)
    destination = Path(destination)
    require(not destination.exists() and not destination.is_symlink(), "Output must be a new regular file")
    sidecar = destination.with_name(destination.name + ".validation.json")
    require(not sidecar.exists() and not sidecar.is_symlink(), "Validation output must be new")
    idb, uboot = verify_bundle(bundle)
    with base.open("rb") as source:
        prefix = source.read(ROOT_OFFSET)
        require(len(prefix) == ROOT_OFFSET and prefix[510:512] == b"\x55\xaa", "Invalid base MBR")
        require(struct.unpack_from("<I", prefix, 440)[0] == 0x74C4A007, "Unexpected base image identity")
        boot, _, kind, _, start, sectors = struct.unpack_from("<B3sB3sII", prefix, 446)
        require((boot, kind, start) == (0x80, 0x83, ROOT_OFFSET // SECTOR), "Unexpected rootfs partition")
        require(not any(prefix[462:510]), "Expected one rootfs partition")
        require(base.stat().st_size == ROOT_OFFSET + sectors * SECTOR, "Base image size mismatch")
        require(not any(prefix[512:]), "Reserved bootloader region is already occupied")
        source.seek(ROOT_OFFSET + 1080)
        require(source.read(2) == b"\x53\xef", "Expected an ext4 root filesystem")
        source.seek(0)
        with destination.open("xb") as output:
            shutil.copyfileobj(source, output, 4 * 1024 * 1024)
    root_before = hash_tail(base)
    with destination.open("r+b") as output:
        for offset in SLOT_OFFSETS:
            output.seek(offset)
            output.write(idb)
        output.seek(UBOOT_OFFSET)
        output.write(uboot)
    require(hash_tail(destination) == root_before, "Rootfs payload changed")
    with destination.open("rb") as output:
        result_prefix = output.read(ROOT_OFFSET)
    require(result_prefix[:512] == prefix[:512], "MBR changed")
    require(all(result_prefix[offset:offset + SLOT_SIZE] == idb for offset in SLOT_OFFSETS),
            "IDB copy verification failed")
    require(result_prefix[UBOOT_OFFSET:UBOOT_OFFSET + UBOOT_SIZE] == uboot,
            "U-Boot copy verification failed")
    report = {"image_bytes": destination.stat().st_size, "mbr_preserved": True,
              "rootfs_sha256": root_before, "rootfs_preserved": True,
              "idb_slots_verified": 5, "fit_copies_verified": 2,
              "bootcmd_modified": False, "hardware_boot_tested": False,
              "bootable_claim": False}
    with sidecar.open("x") as output:
        output.write(json.dumps(report, indent=2) + "\n")
    return report


def self_test(bundle):
    verify_bundle(bundle)
    spec = __import__("importlib.util", fromlist=["util"])
    module_spec = spec.spec_from_file_location("assemble", Path(__file__).with_name("assemble-image.py"))
    module = spec.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        payload = bytearray(bytes(range(256)) * 4096)
        payload[1080:1082] = b"\x53\xef"
        filesystem, base, result = directory / "fake.ext4", directory / "base.img", directory / "test.img"
        filesystem.write_bytes(payload)
        module.assemble(filesystem, base)
        report = apply(base, bundle, result)
        require(hash_tail(result) == digest(payload), "Synthetic payload mismatch")
        try:
            apply(base, bundle, result)
        except ValueError:
            pass
        else:
            raise ValueError("Overwrite guard failed")
        try:
            apply("/dev/null", bundle, directory / "invalid.img")
        except ValueError:
            pass
        else:
            raise ValueError("Device guard failed")
        blocked = directory / "blocked.img"
        blocked.with_name(blocked.name + ".validation.json").symlink_to(filesystem)
        try:
            apply(base, bundle, blocked)
        except ValueError:
            require(not blocked.exists(), "Sidecar guard created an image")
        else:
            raise ValueError("Sidecar guard failed")
        report["test_scope"] = "synthetic image; actual validated vendor loader; no hardware writes"
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("extract")
    command.add_argument("backup")
    command.add_argument("directory")
    command = commands.add_parser("apply")
    command.add_argument("image")
    command.add_argument("bundle")
    command.add_argument("output")
    command = commands.add_parser("self-test")
    command.add_argument("bundle")
    arguments = parser.parse_args()
    if arguments.command == "extract":
        result = extract(arguments.backup, arguments.directory)
    elif arguments.command == "apply":
        result = apply(arguments.image, arguments.bundle, arguments.output)
    else:
        result = self_test(arguments.bundle)
    print(json.dumps(result, indent=2))
