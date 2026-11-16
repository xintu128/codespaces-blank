# TYC4A eDP and USB keyboard test variant

`rk3566-tyc4a-edp01-usb.dts` includes the eDP experiment and enables only the
USB2 host1 path used by the actual built-in keyboard. Read-only Android sysfs
inspection on 2026-11-16 found:

- Keyboard 6080:8060 on hub 1a40:0101, under `fd880000.usb` (EHCI host1).
- Its PHY is the `fe8b0000` host port.
- The stock 5V host supply is enabled by GPIO0_A6, active high and always on.

The shipping 5V supply mapping is modeled with fixed regulators. The kernel's
existing EHCI/OHCI, Rockchip USB2 PHY and HID drivers require no new kernel
configuration. This variant leaves the OTG/charging path, USB3, camera host0,
SDIO and internal eMMC at their inherited disabled settings. It does not claim
the keyboard or display works until a real boot supplies evidence.

Compile with the same patched 6.18.63 source and include paths as the eDP DTS.
It uses the same `6.18.63-tyc4a-edp01` Image and modules. Keep the eDP-only DTB
and the previously proven SD diagnostics DTB as separate fallback entries.
