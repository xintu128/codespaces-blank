#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
repo="$PWD"
source kernel.env
mkdir -p work artifacts/kernel artifacts/logs
exec > >(tee artifacts/logs/kernel-build.log) 2>&1
[[ $(uname -s) == Linux && $(uname -m) == aarch64 ]]
archive="work/linux-${KERNEL_VERSION}.tar.xz"
if [[ ! -f "$archive" ]]; then
    curl --fail --location --retry 4 --retry-all-errors \
        "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz" \
        -o "${archive}.partial"
    mv "${archive}.partial" "$archive"
fi
printf '%s  %s\n' "$KERNEL_SHA256" "$archive" | sha256sum --check
[[ ! -e "work/linux-${KERNEL_VERSION}" ]]
tar -xf "$archive" -C work
cd "work/linux-${KERNEL_VERSION}"
patch_file="$repo/patches/0001-arm64-dts-rockchip-tyc4a.patch"
git apply --check "$patch_file"
git apply "$patch_file"
cmp arch/arm64/boot/dts/rockchip/rk3566-tyc4a.dts "$repo/board/rk3566-tyc4a.dts"
export ARCH=arm64 LLVM=1 KBUILD_BUILD_USER=tyc4a KBUILD_BUILD_HOST=github-actions
export KBUILD_BUILD_TIMESTAMP='2026-11-10 18:22:00 UTC'
make O=../kernel-out defconfig
config=../kernel-out/.config
# Limit defconfig to the target SoC family.
while read -r option; do
    [[ "$option" == ARCH_ROCKCHIP ]] || scripts/config --file "$config" --disable "$option"
done < <(sed -n 's/^\(CONFIG_ARCH_[A-Z0-9_]*\)=y$/\1/p' arch/arm64/configs/defconfig | sed 's/^CONFIG_//')
scripts/config --file "$config" --enable ARCH_ROCKCHIP \
    --set-str LOCALVERSION '-tyc4a-v07' --disable LOCALVERSION_AUTO \
    --disable DEBUG_INFO --disable DEBUG_INFO_BTF --enable DEBUG_INFO_NONE \
    --enable DEVTMPFS --enable DEVTMPFS_MOUNT --enable BLK_DEV_INITRD \
    --enable EXT4_FS --enable MMC --enable MMC_DW --enable MMC_DW_ROCKCHIP \
    --enable SERIAL_8250 --enable SERIAL_8250_CONSOLE --enable SERIAL_8250_DW
make O=../kernel-out olddefconfig
for option in ARCH_ROCKCHIP EXT4_FS MMC MMC_DW MMC_DW_ROCKCHIP SERIAL_8250_DW; do
    grep -qx "CONFIG_${option}=y" "$config"
done
jobs="$(nproc)"
make O=../kernel-out -j"$jobs" Image rockchip/rk3566-tyc4a.dtb modules
release="$(make -s O=../kernel-out kernelrelease)"
printf '%s\n' "$release" > "$repo/artifacts/kernel/kernelrelease"
make O=../kernel-out INSTALL_MOD_PATH="$repo/work/modules" modules_install
find "$repo/work/modules" -type l \( -name build -o -name source \) -delete
tar -C "$repo/work/modules" -cJf "$repo/artifacts/kernel/modules.tar.xz" lib
cp ../kernel-out/arch/arm64/boot/Image "$repo/artifacts/kernel/"
cp ../kernel-out/arch/arm64/boot/dts/rockchip/rk3566-tyc4a.dtb "$repo/artifacts/kernel/"
cp ../kernel-out/.config "$repo/artifacts/kernel/kernel.config"
cp ../kernel-out/System.map "$repo/artifacts/kernel/"
cp arch/arm64/boot/dts/rockchip/rk3566-tyc4a.dts "$repo/artifacts/kernel/"
cd "$repo"
python3 scripts/verify-artifacts.py artifacts/kernel
cp README.md artifacts/kernel/README.md
{
    printf 'source_sha256=%s\n' "$KERNEL_SHA256"
    printf 'commit=%s\n' "${GITHUB_SHA:-local}"
    clang --version
    dtc --version
    dpkg-query -W clang lld llvm
} > artifacts/kernel/toolchain.txt
(cd artifacts/kernel && sha256sum Image *.dtb *.xz kernel.config System.map kernelrelease *.dts *.json README.md toolchain.txt > SHA256SUMS)
printf 'Kernel compiled. Hardware boot remains untested.\n'
