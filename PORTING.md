# Hardware port status

The kernel artifact preserves V0.7. Hardware boot remains untested.
The Debian workflow also offers an experimental SD/serial DTB under `experimental/sd/`.
That DTB enables PMIC, IO domains, SD and UART2. It disables CPU DVFS.
The V0.7 DTB cannot mount an SD rootfs.

| Area | Local evidence | Remaining work |
| --- | --- | --- |
| PMIC | Vendor tree identifies RK809 at I2C0 address 0x20, GPIO0 pin 3, level-low IRQ. | Audit mainline RK809 supply and regulator bindings before enabling I2C0 and the PMIC. |
| SD | Vendor controller is 0xfe2b0000. VMMC uses SWITCH_REG2. VQMMC uses LDO_REG5 at 3.3 V. | Port IO domains, enable the controller and verify card detection and power. |
| IO domains | Vendor PMU IO-domain node supplies vccio3 from the SD rail. | Resolve each vendor supply to a mainline label. Avoid voltage switching until verified. |
| CPU supply | Vendor tree also has a Silergy regulator at I2C0 address 0x40. | Audit the regulator before enabling CPU frequency scaling. |
| UART | Android earlycon uses 0xfe660000. Vendor UART2 is disabled and Android uses FIQ console. | Enable and test a mainline UART console with the correct pin group. |
| eMMC | Vendor controller is 0xfe310000. Internal Android uses this device. | The development DTBs keep this controller disabled. Internal installation remains untested. |
| Wi-Fi | Vendor controller is 0xfe2c0000 with an SDIO power sequence. | Port power, reset, clock and firmware before enabling SDIO. |
| Bootloader | Stock bootcmd starts Android before FIT, Rockchip and distro fallback. | Verify an external boot path without persistent environment writes or internal firmware changes. |
| User interface | Display, keyboard and USB power are not integrated in V0.7. | Port these after a serial boot and SD rootfs test. |

Successful compilation verifies syntax and build integration. It does not verify electrical behavior.
No bootloader binary or full Android backup is published with this project.
