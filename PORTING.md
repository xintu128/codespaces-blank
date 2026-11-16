# Hardware port status

The kernel artifact preserves V0.7. The additional diagnostic SD variant has booted Debian to multi-user state on one board.
See [boot evidence and limits](docs/BOOT-TEST-2026-11-16.md).
The Debian workflow also offers an experimental SD/serial DTB under `experimental/sd/`.
That DTB enables PMIC, IO domains, SD and UART2. It disables CPU DVFS.
The V0.7 DTB cannot mount an SD rootfs.

| Area | Local evidence | Remaining work |
| --- | --- | --- |
| PMIC | Vendor tree identifies RK809 at I2C0 address 0x20, GPIO0 pin 3, level-low IRQ. | Experimental SD PMIC is enabled and exercised during boot. Full electrical and suspend testing remains. |
| SD | Vendor controller is 0xfe2b0000. VMMC uses SWITCH_REG2. VQMMC uses LDO_REG5 at 3.3 V. | Diagnostic SD boot detected the SDXC card at 50 MHz and mounted rootfs read-write; stress testing remains. |
| IO domains | Vendor PMU IO-domain node supplies vccio3 from the SD rail. | Experimental supply mapping is checked; the observed SD boot uses fixed 3.3 V. Voltage switching remains disabled. |
| CPU supply | Vendor tree also has a Silergy regulator at I2C0 address 0x40. | Audit the regulator before enabling CPU frequency scaling. |
| UART | Android earlycon uses 0xfe660000. Vendor UART2 is disabled and Android uses FIQ console. | Enable and test a mainline UART console with the correct pin group. |
| eMMC | Vendor controller is 0xfe310000. Internal Android uses this device. | The development DTBs keep this controller disabled. Internal installation remains untested. |
| Wi-Fi | Vendor controller is 0xfe2c0000 with an SDIO power sequence. | Port power, reset, clock and firmware before enabling SDIO. |
| Bootloader | Stock bootcmd starts Android before FIT, Rockchip and distro fallback. | Vendor loaders on SD booted the diagnostic configuration without internal writes or bootcmd changes. Cold/warm and repeated-boot coverage remains limited. |
| User interface | Android confirms a connected eDP inner panel; Linux currently has no enabled VOP. | Backport RK3568 eDP controller/PHY support and port the panel/backlight, then keyboard and USB. |

Successful compilation verifies syntax and build integration. It does not verify electrical behavior.
No bootloader binary or full Android backup is published with this project.
