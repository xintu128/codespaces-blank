# Vendor SD loader preparation

Hardware boot remains untested. This tool prepares regular image files.

The stock boot selection script runs `rkimgtest mmc 1` before selecting SD.
Rockchip's implementation reads LBA 64 and accepts the `RKNS` header.
The current SD layout reserves that region but leaves it empty.

`scripts/vendor-sd-loader.py` extracts this board's validated loaders from the local backup.
The tool checks the primary GPT CRC, RKNS header and payload hashes, and both U-Boot FIT copies.
All nine payload hashes in each FIT copy must match.
The tool pins this board's loader hashes and rejects different firmware.

The tool places five original loader slots at their original offsets.
It places the original 4 MiB U-Boot partition at 8 MiB.
The tool preserves the MBR and verifies the complete rootfs payload after copying.
It refuses device files, existing output files, and occupied loader regions.
It keeps the stock boot command and its existing hash checks.

## Local use

Run these commands from the repository root:

```sh
python3 scripts/vendor-sd-loader.py extract /path/to/local-backup.img /path/to/new-loader-bundle
python3 scripts/vendor-sd-loader.py self-test /path/to/new-loader-bundle
python3 scripts/vendor-sd-loader.py apply /path/to/uncompressed-SD-layout.img /path/to/new-loader-bundle /path/to/new-SD-test.img
```

Use the uncompressed SD layout from the successful Debian build.
Keep the extracted vendor files local. This repository contains the preparation tool only.

## Evidence and limits

The available backup contains 10,876,691,966 bytes.
Its GPT describes a 31,272,730,624-byte device. It is not a complete recovery backup.
The required loader regions fall within the validated first 16 MiB.
The original U-Boot version is 2017.09, built on 2023-11-24.
The file previously called `uboot-test.img` is identical to the original U-Boot.

Adding the RKNS header should satisfy the stock SD selection check.
This is an inference from the source and local firmware strings.
It does not establish BootROM priority, SPL media selection, or successful Linux handoff.
Those stages still require a real boot log.

Sources:

- [Rockchip SD detection command](https://github.com/rockchip-linux/u-boot/blob/next-dev/cmd/rkimgtest.c)
- [U-Boot RKNS header implementation](https://github.com/u-boot/u-boot/blob/master/tools/rkcommon.c)
- [Rockchip boot documentation](https://docs.u-boot.org/en/stable/board/rockchip/rockchip.html)
