#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
repo="$PWD"
source kernel.env
for option in I2C_RK3X MFD_RK8XX_I2C REGULATOR_RK808 ROCKCHIP_IODOMAIN MMC_DW_ROCKCHIP SERIAL_8250_DW; do
    grep -qx "CONFIG_${option}=y" artifacts/kernel/kernel.config
done
mkdir -p work/experimental-source artifacts/experimental
archive="work/experimental-linux-${KERNEL_VERSION}.tar.xz"
curl --fail --location --retry 4 --retry-all-errors \
    "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz" -o "$archive"
printf '%s  %s\n' "$KERNEL_SHA256" "$archive" | sha256sum --check
tar -xf "$archive" -C work/experimental-source \
    "linux-${KERNEL_VERSION}/arch/arm64/boot/dts/rockchip" \
    "linux-${KERNEL_VERSION}/include/dt-bindings"
source_root="$repo/work/experimental-source/linux-${KERNEL_VERSION}"
clang -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
    -I board -I "$source_root/include" -I "$source_root/arch/arm64/boot/dts/rockchip" \
    experimental/sd/rk3566-tyc4a-sd-experimental.dts \
    -o artifacts/experimental/rk3566-tyc4a-sd-experimental.preprocessed.dts
dtc -@ -I dts -O dtb -o artifacts/experimental/rk3566-tyc4a-sd-experimental.dtb \
    artifacts/experimental/rk3566-tyc4a-sd-experimental.preprocessed.dts
python3 scripts/verify-experimental.py artifacts/experimental
cp experimental/sd/rk3566-tyc4a-sd-experimental.dts artifacts/experimental/
(cd artifacts/experimental && sha256sum *.dtb *.dts *.json > SHA256SUMS)
