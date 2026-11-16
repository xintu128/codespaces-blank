# Internal eMMC migration work

The user explicitly authorized replacing Android on the internal eMMC.
The existing SD system is retained as the recovery environment.

`rk3566-tyc4a-emmc01.dts` adds only the eMMC controller to the tested
Wi-Fi/eDP/USB configuration. It uses an eight-bit bus and caps the clock at
52 MHz without enabling HS200/HS400. The running controller reports an actual
50 MHz clock, high-speed MMC timing, and an AK411G 31,272,730,624-byte device.
The first probe boots from the SD rootfs and sets the internal disk read-only.
This is not yet a verified internal-boot result.

Before writing internally, a complete user-area backup is saved on the SD card,
with source length/SHA-256 matched against a full decompression of the backup.
The two hardware boot areas are backed up separately. The older Mac backup is
incomplete and does not satisfy this requirement.

The planned migration retains the original security, U-Boot, trust and display
parameter partitions. The existing Android userdata partition is large enough
for the Debian root filesystem. First test that rootfs while booting the kernel
from SD. Then change the original Android boot partition label and mark the
Linux root partition bootable for the vendor U-Boot distribution scan. This is
an inference from the extracted boot commands and the vendor source; a final
cold boot with the SD card removed is required before claiming internal boot.

No vendor firmware binaries, personal data, credentials or backups belong in
this public repository.

Rebuild only this DTB using the existing kernel:

```sh
export KERNEL_SOURCE_ROOT=/absolute/path/to/linux-6.18.63
export TYC4A_DTB_OUTPUT=/absolute/path/to/dtb-output
bash experimental/emmc/build-dtb.sh
```

The verifier first reproduces the checksum-pinned installed Wi-Fi DTB. It then
checks the candidate differs only in the eMMC properties and their pinctrl
references. The eDP clocks, display graph, keyboard and Wi-Fi nodes remain
unchanged. `gpt.py` prepares and checks the two limited GPT changes in memory;
it contains no device-writing operation. Tests with the real original GPT
also reject damaged primary/backup headers and partition tables.

The extracted vendor U-Boot boot command runs Android first, followed by its
distribution scan. The expected fallback and GPT bootable attribute handling
are supported by the vendor sources:

- https://github.com/rockchip-linux/u-boot/blob/next-dev/common/android_bootloader.c
- https://github.com/rockchip-linux/u-boot/blob/next-dev/include/config_distro_bootcmd.h
- https://github.com/rockchip-linux/u-boot/blob/next-dev/disk/part_efi.c
