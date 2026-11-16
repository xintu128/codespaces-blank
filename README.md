# TYC4A RK3566 Linux development build

Hardware boot is **UNTESTED**. Internal installation has not been validated.
V0.7 disables RK809/I2C0, SDMMC0, SDIO and internal eMMC.
This DTB cannot mount an SD root filesystem.

## Build

The Actions workflow uses `ubuntu-24.04-arm` and Linux **6.18.63** from kernel.org.
`kernel.env` pins the source archive SHA-256.
`patches/0001-arm64-dts-rockchip-tyc4a.patch` changes exactly three kernel files.
The original patch variants remain unchanged in `originals/`.
`board/rk3566-tyc4a.dts` is the existing V0.7 source.

The first job builds Image, the DTB, modules, kernel configuration and System.map.
It checks the ARM64 Image header and the DTB storage-disable properties.
It uploads logs even when compilation fails.
The second job builds a Debian trixie ARM64 rootfs and a partitioned SD candidate.
Both jobs save checksums and validation metadata.
Run once by pushing the build branch, or use **Actions → Run workflow** on the default branch.
The separate Debian workflow reuses an existing successful kernel job.
Rootfs-only changes trigger that workflow without recompiling the kernel.
That workflow defaults to the experimental SD/serial DTB and also supports V0.7.
The experimental DTB enables PMIC, IO domains, SD and UART2 using vendor source mappings.
It limits SD to 3.3 V / 50 MHz and disables CPU DVFS until the CPU regulator is ported.
The kernel artifact continues to preserve the original V0.7 DTB.

Artifacts expire after 14 days.
The rootfs contains locked `root` and `tyc4a` accounts. Configure credentials offline before use.
No SSH service or default password is included.
This is a Debian development image, not an Armbian release.

## Boot limits

The candidate includes an ext4 partition, kernel, DTB, modules and extlinux configuration.
The first partition starts at 16 MiB. Its PARTUUID is `74c4a007-01`.
No Rockchip loader, U-Boot, trust firmware or Android partition is included.
The original U-Boot starts Android before its distribution scan.
SD scanning and extlinux boot have not been verified on this machine.
The UART setting derives from the Android earlycon address. It needs a hardware test.
PMIC rails, SD power, display, keyboard and Wi-Fi still need porting and testing.
An assembled `.img` file is not evidence of successful boot.

## Reproduce on ARM64 Linux

Install the packages listed in `.github/workflows/build.yml`, then run:

```sh
bash scripts/build-kernel.sh
sudo bash scripts/build-rootfs.sh
```

Use a clean checkout for each build. The scripts refuse to reuse source and rootfs directories.
The image assembler accepts regular files only. No script writes to a disk device.

## Provenance

Source: <https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.18.63.tar.xz>
Checksum: <https://cdn.kernel.org/pub/linux/kernel/v6.x/sha256sums.asc>
Runner: <https://docs.github.com/en/actions/reference/runners/github-hosted-runners>
Rootfs tool: <https://manpages.debian.org/trixie/mmdebstrap/mmdebstrap.1.en.html>

The local source archive matches the official checksum.
The original patch applies to clean 6.18.63 files.
The DTB compiles locally. Full kernel and rootfs builds require the Linux workflow.
No board has been boot-tested with these outputs.

See [BOOTLOADER.md](BOOTLOADER.md) for the validated local vendor-loader preparation path.
