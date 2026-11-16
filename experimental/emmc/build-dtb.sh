#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
src="${KERNEL_SOURCE_ROOT:?Set KERNEL_SOURCE_ROOT to Linux 6.18.63 sources}"
out="${TYC4A_DTB_OUTPUT:?Set TYC4A_DTB_OUTPUT to an output directory}"
mkdir -p "$out"
for name in wifi01 emmc01; do
 if [[ "$name" == wifi01 ]]; then board="$repo/experimental/wifi/rk3566-tyc4a-wifi01.dts"; else board="$repo/experimental/emmc/rk3566-tyc4a-emmc01.dts"; fi
 "${CC:-cc}" -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
   -I "$src/include" -I "$src/arch/arm64/boot/dts/rockchip" \
   "$board" -o "$out/rk3566-tyc4a-$name.preprocessed.dts"
 "${DTC:-dtc}" -I dts -O dtb -o "$out/rk3566-tyc4a-$name.dtb" "$out/rk3566-tyc4a-$name.preprocessed.dts" 2>"$out/$name-dtc.log"
done
python3 "$repo/experimental/emmc/verify.py" "$out/rk3566-tyc4a-wifi01.dtb" "$out/rk3566-tyc4a-emmc01.dtb"
