#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
repo="$PWD"
[[ $(id -u) == 0 && $(uname -s) == Linux && $(uname -m) == aarch64 ]]
mkdir -p artifacts/debian work
exec > >(tee artifacts/debian/rootfs-build.log) 2>&1
python3 scripts/verify-artifacts.py artifacts/kernel
(cd artifacts/kernel && sha256sum --check SHA256SUMS)
flavor="${TYC4A_DTB_FLAVOR:-v07}"
case "$flavor" in
    v07) selected_dtb="$repo/artifacts/kernel/rk3566-tyc4a.dtb" ;;
    experimental-sd)
        bash scripts/build-experimental-dtb.sh
        selected_dtb="$repo/artifacts/experimental/rk3566-tyc4a-sd-experimental.dtb"
        ;;
    *) echo "Unknown DTB flavor: $flavor"; exit 1 ;;
esac
rootfs="$repo/work/debian-rootfs"
[[ ! -e "$rootfs" ]]
mmdebstrap --mode=root --architectures=arm64 --variant=minbase \
    --keyring=/usr/share/keyrings/debian-archive-keyring.gpg \
    --include=systemd-sysv,udev,kmod,ca-certificates,iproute2,iputils-ping,systemd-resolved,systemd-timesyncd,sudo \
    trixie "$rootfs" \
    'deb https://deb.debian.org/debian trixie main' \
    'deb https://deb.debian.org/debian trixie-updates main' \
    'deb https://security.debian.org/debian-security trixie-security main'
release="$(cat artifacts/kernel/kernelrelease)"
[[ -L "$rootfs/lib" ]]
tar --keep-directory-symlink -xJf artifacts/kernel/modules.tar.xz -C "$rootfs"
[[ -L "$rootfs/lib" ]]
depmod -b "$rootfs" "$release"
mkdir -p "$rootfs/boot/dtb/rockchip" "$rootfs/boot/extlinux" \
    "$rootfs/etc/systemd/network" "$rootfs/etc/ssh" "$rootfs/usr/share/tyc4a"
install -m 0644 artifacts/kernel/Image "$rootfs/boot/Image"
install -m 0644 "$selected_dtb" "$rootfs/boot/dtb/rockchip/rk3566-tyc4a.dtb"
install -m 0644 artifacts/kernel/rk3566-tyc4a.dtb "$rootfs/boot/dtb/rockchip/rk3566-tyc4a-v07.dtb"
cp artifacts/kernel/kernel.config "$rootfs/boot/config-$release"
cp artifacts/kernel/validation.json "$rootfs/usr/share/tyc4a/"
if [[ "$flavor" == experimental-sd ]]; then
    cp artifacts/experimental/validation.json "$rootfs/usr/share/tyc4a/validation.json"
fi
cp README.md "$rootfs/usr/share/tyc4a/README.md"
printf 'tyc4a\n' > "$rootfs/etc/hostname"
printf '127.0.0.1 localhost\n127.0.1.1 tyc4a\n::1 localhost ip6-localhost ip6-loopback\n' > "$rootfs/etc/hosts"
printf 'PARTUUID=74c4a007-01 / ext4 defaults,noatime 0 1\n' > "$rootfs/etc/fstab"
cat > "$rootfs/boot/extlinux/extlinux.conf" <<'EOF'
TIMEOUT 50
DEFAULT tyc4a-v07-UNTESTED
LABEL tyc4a-v07-UNTESTED
  MENU LABEL TYC4A V0.7 - SD AND PMIC DISABLED - HARDWARE UNTESTED
  LINUX /boot/Image
  FDT /boot/dtb/rockchip/rk3566-tyc4a.dtb
  APPEND root=PARTUUID=74c4a007-01 rootfstype=ext4 rootwait rw console=ttyS2,1500000n8 earlycon=uart8250,mmio32,0xfe660000
EOF
if [[ "$flavor" == experimental-sd ]]; then
    sed -i 's/tyc4a-v07-UNTESTED/tyc4a-sd-experimental-UNTESTED/g; s/TYC4A V0.7 - SD AND PMIC DISABLED - HARDWARE UNTESTED/TYC4A experimental SD - HARDWARE UNTESTED/' "$rootfs/boot/extlinux/extlinux.conf"
fi
cat > "$rootfs/etc/systemd/network/20-wired.network" <<'EOF'
[Match]
Name=en* eth*
[Network]
DHCP=yes
EOF
chroot "$rootfs" useradd --create-home --shell /bin/bash --groups sudo tyc4a
chroot "$rootfs" passwd --lock root
chroot "$rootfs" passwd --lock tyc4a
systemctl --root="$rootfs" enable systemd-networkd.service systemd-resolved.service serial-getty@ttyS2.service
ln -sfn /run/systemd/resolve/stub-resolv.conf "$rootfs/etc/resolv.conf"
truncate -s 0 "$rootfs/etc/machine-id"
chroot "$rootfs" /bin/true
chroot "$rootfs" /usr/lib/systemd/systemd --version
chroot "$rootfs" dpkg-query -W > artifacts/debian/packages.tsv
cat > artifacts/debian/READ-ME-FIRST.txt <<'EOF'
TYC4A Debian trixie ARM64 development candidate. Not an Armbian release.
No hardware boot test. The selected DTB flavor appears in validation.json.
V0.7 keeps PMIC and SD disabled; it cannot mount the SD rootfs.
The experimental SD flavor enables PMIC, SD and UART. CPU DVFS stays disabled.
Both flavors keep SDIO and eMMC disabled. Hardware behavior remains untested.
The image contains a partition layout, kernel, DTB, modules and rootfs.
It contains NO Rockchip loader, U-Boot, trust firmware or Android partitions.
Stock U-Boot starts Android first. SD discovery has not been established.
Internal installation is not validated. This file is a development candidate.
Both root and tyc4a accounts are locked. Set a password offline before use.
The extlinux serial port is a candidate derived from the Android earlycon address.
Display, keyboard, Wi-Fi, regulators and SD boot remain unverified.
EOF
cp artifacts/debian/READ-ME-FIRST.txt "$rootfs/NOT-BOOT-VERIFIED.txt"
tar --xattrs --acls --numeric-owner -C "$rootfs" -c . | zstd -T2 -6 -o artifacts/debian/TYC4A-Debian-trixie-arm64-rootfs-UNTESTED.tar.zst
root_image="$repo/work/tyc4a-rootfs.ext4"
truncate -s 3G "$root_image"
mkfs.ext4 -F -L TYC4A_ROOT -O '^metadata_csum_seed,^orphan_file,^64bit' \
    -E lazy_itable_init=0,lazy_journal_init=0 -d "$rootfs" "$root_image"
e2fsck -fn "$root_image"
image="$repo/artifacts/debian/TYC4A-SD-layout-UNTESTED-NO-BOOTLOADER.img"
# Assemble regular files only. No block device is opened.
python3 scripts/assemble-image.py "$root_image" "$image"
fdisk -l "$image" > artifacts/debian/partition-layout.txt
zstd -T2 -6 --rm "$image"
python3 - <<'PY'
import json
import shutil
from pathlib import Path
data = json.loads(Path('artifacts/kernel/validation.json').read_text())
experimental = Path('artifacts/experimental/validation.json')
if experimental.exists():
    data.update(json.loads(experimental.read_text()))
    data.pop('v07_disabled_nodes', None)
    shutil.copytree('artifacts/experimental', 'artifacts/debian/experimental')
else:
    data['dtb_flavor'] = 'v07'
data.update(debian_suite='trixie', architecture='arm64', rootfs_chroot_test='pass',
            rootfs_ext4_check='pass', bootable_claim=False,
            accounts_locked=True, armbian_release=False)
Path('artifacts/debian/validation.json').write_text(json.dumps(data, indent=2) + '\n')
PY
(
    cd artifacts/debian
    files=(*.zst *.json *.txt *.tsv)
    if [[ -d experimental ]]; then files+=(experimental/*); fi
    sha256sum "${files[@]}" > SHA256SUMS
)
printf 'Debian candidate assembled. Hardware boot remains untested.\n'
