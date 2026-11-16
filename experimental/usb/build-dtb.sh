#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
work="${TYC4A_BUILD_WORK:?Set TYC4A_BUILD_WORK}"
src="${KERNEL_SOURCE_ROOT:?Set KERNEL_SOURCE_ROOT to patched Linux 6.18.63}"
out="$work/artifacts"
mkdir -p "$out"
gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
    -I "$src/include" -I "$src/arch/arm64/boot/dts/rockchip" \
    "$repo/experimental/usb/rk3566-tyc4a-edp01-usb.dts" \
    -o "$out/rk3566-tyc4a-edp01-usb.preprocessed.dts"
dtc -I dts -O dtb -o "$out/rk3566-tyc4a-edp01-usb.dtb" \
    "$out/rk3566-tyc4a-edp01-usb.preprocessed.dts"
python3 "$repo/experimental/usb/verify.py" "$out/rk3566-tyc4a-edp01-usb.dtb"
