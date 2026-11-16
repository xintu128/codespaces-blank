# SD boot diagnostics

These additions provide progress evidence when HDMI and networking are unavailable.
The original Android DTB assigns the work LED to GPIO0_B7, active high.
The diagnostic DTB adds that LED with the heartbeat trigger to the experimental SD DTB.
The existing kernel has GPIO LEDs and heartbeat built in; no kernel rebuild is needed.
SD, PMIC, IO-domain, CPU DVFS, SDIO and eMMC behavior otherwise follows the experimental SD tree.

A heartbeat indicates the kernel reached and initialized the GPIO LED driver.
An unlit LED alone cannot locate the failure or establish whether the kernel started.
HDMI output remains unconfigured in this minimal diagnostic tree.

The oneshot service records the boot ID, uptime, command line, mounts and dmesg under
`/var/log/tyc4a-boots/<boot-id>/`. The `latest` link identifies the newest capture.
The marker `userspace-reached.txt` is evidence of reaching this userspace service.
A missing marker is inconclusive: the system may have stopped earlier or failed to write the card.
Persistent systemd journal storage is limited to 64 MiB.
Accounts remain locked and no network service is added.

## Build

Use the same checksum-verified Linux 6.18.63 include tree as the normal experimental DTB.
From the repository root, set `source_root` to the extracted Linux source and run:

```sh
clang -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
  -I board -I "$source_root/include" \
  -I "$source_root/arch/arm64/boot/dts/rockchip" \
  experimental/diagnostics/rk3566-tyc4a-sd-diagnostics.dts \
  -o rk3566-tyc4a-sd-diagnostics.preprocessed.dts
dtc -@ -I dts -O dtb -o rk3566-tyc4a-sd-diagnostics.dtb \
  rk3566-tyc4a-sd-diagnostics.preprocessed.dts
```

## Install into an identified SD rootfs

Back up `/boot/extlinux/extlinux.conf` before making changes.
Install the diagnostic DTB beside the existing DTB and add a separate extlinux entry
pointing to it. Preserve the original entry as a fallback.
Use the existing kernel and root PARTUUID, optionally adding `ignore_loglevel log_buf_len=2M`.

Install `tyc4a-boot-evidence.sh` as `/usr/local/sbin/tyc4a-boot-evidence`, mode 0755.
Install the service under `/etc/systemd/system/` and enable it with the link
`sysinit.target.wants/tyc4a-boot-evidence.service -> ../tyc4a-boot-evidence.service`.
Install the journal fragment under `/etc/systemd/journald.conf.d/` and create `/var/log/journal`.
Read back the installed files and verify their hashes before rebooting.
Only edit the confirmed SD rootfs; these changes do not require editing internal Android or U-Boot.

The diagnostic DTB has passed compilation, relevant schema checks, supply-reference checks,
and GPIO comparison against the original Android tree.
A subsequent test confirmed SD boot to multi-user state and the persistent marker service;
see [hardware evidence](../../docs/BOOT-TEST-2026-11-16.md).
