#!/usr/bin/env bash
# Native ARM64 Linux build. Does not install or select a boot entry.
set -Eeuo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
source "$repo/kernel.env"
work="${TYC4A_BUILD_WORK:?Set TYC4A_BUILD_WORK to a dedicated build directory}"
mkdir -p "$work" "$work/artifacts" "$work/tmp"
exec > >(tee -a "$work/build.log") 2>&1
[[ $(uname -s) == Linux && $(uname -m) == aarch64 ]]
export ARCH=arm64 KBUILD_BUILD_USER=tyc4a KBUILD_BUILD_HOST=native-arm64
export KBUILD_BUILD_TIMESTAMP='2026-11-16 00:00:00 UTC'
export TMPDIR="$work/tmp"
archive="$work/linux-${KERNEL_VERSION}.tar.xz"
printf '%s  %s\n' "$KERNEL_SHA256" "$archive" | sha256sum --check
src="$work/linux-${KERNEL_VERSION}"
out="$work/kernel-out-wifi01"
if [[ ! -e "$src/.tyc4a-wifi01-patches-applied" ]]; then
    [[ ! -e "$src" ]]
    tar -xf "$archive" -C "$work"
    cd "$src"
    patch --batch --forward -p1 < "$repo/patches/0001-arm64-dts-rockchip-tyc4a.patch"
    for patch in "$repo"/experimental/edp/patches/*.patch; do
        patch --batch --forward -p1 < "$patch"
    done
    touch .tyc4a-wifi01-patches-applied
fi
cd "$src"
mkdir -p "$out"
if [[ ! -f "$out/.config" ]]; then
    cp "$repo/experimental/edp/base.config" "$out/.config"
fi
scripts/config --file "$out/.config" \
    --set-str LOCALVERSION '-tyc4a-wifi01' --disable LOCALVERSION_AUTO \
    --disable DEBUG_INFO --disable DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT \
    --disable DEBUG_INFO_DWARF4 --disable DEBUG_INFO_DWARF5 \
    --disable DEBUG_INFO_BTF --enable DEBUG_INFO_NONE \
    --module PHY_ROCKCHIP_NANENG_EDP --module DRM_ROCKCHIP \
    --module DRM_ANALOGIX_DP --module DRM_PANEL_EDP --module BACKLIGHT_PWM \
    --module RTW88 --module RTW88_8822CS --enable PWRSEQ_SIMPLE
make O="$out" olddefconfig
for option in PHY_ROCKCHIP_NANENG_EDP DRM_ROCKCHIP DRM_ANALOGIX_DP DRM_PANEL_EDP BACKLIGHT_PWM RTW88 RTW88_CORE RTW88_SDIO RTW88_8822C RTW88_8822CS; do
    grep -qx "CONFIG_${option}=m" "$out/.config"
done
release="$(make -s O="$out" kernelrelease)"
[[ "$release" == 6.18.63-tyc4a-wifi01 ]]
printf '%s\n' "$release" > "$work/artifacts/kernelrelease"
gcc --version
make --version
printf 'Compiling %s with %s jobs\n' "$release" "${TYC4A_BUILD_JOBS:-3}"
make O="$out" -j"${TYC4A_BUILD_JOBS:-3}" \
    drivers/phy/rockchip/phy-rockchip-naneng-edp.o \
    drivers/gpu/drm/rockchip/analogix_dp-rockchip.o \
    drivers/gpu/drm/bridge/analogix/analogix_dp_core.o \
    drivers/gpu/drm/panel/panel-edp.o
make O="$out" -j"${TYC4A_BUILD_JOBS:-3}" Image modules
gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
    -I "$src/include" -I "$src/arch/arm64/boot/dts/rockchip" \
    "$repo/experimental/wifi/rk3566-tyc4a-wifi01.dts" \
    -o "$work/artifacts/rk3566-tyc4a-wifi01.preprocessed.dts"
dtc -I dts -O dtb \
    -o "$work/artifacts/rk3566-tyc4a-wifi01.dtb" \
    "$work/artifacts/rk3566-tyc4a-wifi01.preprocessed.dts"
make O="$out" INSTALL_MOD_PATH="$work/module-stage" INSTALL_MOD_STRIP=1 modules_install
find "$work/module-stage" -type l \( -name build -o -name source \) -delete
tar -C "$work/module-stage" -czf "$work/artifacts/modules.tar.gz" lib
cp "$out/arch/arm64/boot/Image" "$work/artifacts/"
cp "$out/.config" "$work/artifacts/kernel.config"
cp "$out/System.map" "$out/Module.symvers" "$work/artifacts/"
python3 "$repo/experimental/wifi/verify.py" "$work/artifacts"
(cd "$work/artifacts" && sha256sum Image *.dtb modules.tar.gz kernel.config System.map Module.symvers kernelrelease *validation.json > SHA256SUMS)
date -u > "$work/build-success"
echo 'Build verified; Wi-Fi kernel has not yet been tested on hardware.'
