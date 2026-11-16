# TYC4A internal eDP experiment 01

The SD diagnostics configuration has booted the real board to Debian multi-user
in 9.3 seconds with Linux 6.18.63-tyc4a-v07. Its captured kernel log reports
`No available vop found for display-subsystem`. This experiment enables the
internal panel. With the route and VP1 clock corrections below, the user
confirmed on 2026-11-16 that the internal screen displays Debian login text
and the USB keyboard responds to Enter. This establishes a working text
console, not complete peripheral, power-management or desktop support.

The Android live device tree identifies an enabled Analogix RK3568-compatible
eDP controller and Naneng PHY, VOP video port 1, GPIO0_C4 panel enable,
GPIO0_C7 backlight enable, and PWM4 on GPIO0_C3 at 25,000 ns. The original
fixed timing is 1920x1080 at 148.5 MHz, horizontal 88/44/148 and vertical
4/5/36, both sync polarities negative. The EDID read returned no bytes.

## Changes

`patches/0002-*.patch` backports Damon Ding's accepted RK3568 Analogix bridge
support and v6 Naneng PHY / SoC device tree additions to Linux **6.18.63**.
Original extracted patches and primary mailing-list URLs are in `upstream/`.
The enum is appended to preserve existing type values. The 6.18 helper remains
named `is_rockchip()`; newer upstream code uses a renamed helper. Regulator
consumer headers and older probe API context are adapted explicitly.

`patches/0003-*.patch` adds a board-specific fixed panel descriptor to panel-edp
because this firmware exposes no EDID. No manufacturer or panel model is
assumed. 8 bits per color is an initial assumption to verify on hardware;
physical panel dimensions remain unspecified. The descriptor uses the shipping
120 ms sequencing delays and a conservative 500 ms power-off interval.

The DTS uses the confirmed SD diagnostics as its base and enables VOP/IOMMU,
eDP, PHY and PWM4. The existing fixed system supply is referenced by the panel;
GPIO0_C4 controls its actual enable. The brightness table is simplified to 14
levels, starting at 120/255. Internal eMMC remains disabled. This experiment
does not modify the vendor loader, Android firmware, network or CPU regulator.

## Build and validate

Use an ARM64 Linux host with GCC, make, bc, bison, flex, OpenSSL/ELF headers,
patch, xz, cpio, kmod, rsync, Python 3 and dtc. Put the checksum-pinned
`linux-6.18.63.tar.xz` in a fresh dedicated build directory, then run:

```sh
export TYC4A_BUILD_WORK=/absolute/path/to/dedicated-build
export TYC4A_BUILD_JOBS=3
bash experimental/edp/build.sh
```

`base.config` is the configuration extracted from the SD's original kernel
configuration file. It is re-resolved with the native compiler, a separate
`-tyc4a-edp01` release, no debug symbols, and the new PHY as a module. Output
contains Image, DTB, stripped modules, configuration, System.map,
Module.symvers, checksums, validation report and a build log. The verifier
checks the ARM64 Image, required modules, storage enablement, PWM/GPIO mapping,
PHY phandle and reciprocal display graph. These checks do not prove display
operation, correct colors, stability, or that the new kernel boots.

The build script does not install or select a boot entry. Install the new Image,
DTB and modules alongside the proven version, keep its files unchanged and
retain its extlinux entry. Before rebooting a board used as an Android-hosted
build machine, finish all processes, unmount all chroot binds and restore its
temporary DNS/service-policy files. Retrieve persistent boot evidence after a
test and record the result against this exact release and artifact hashes.

## First hardware result and route correction

The first edp01 kernel booted to Debian multi-user mode on 2026-11-16. The
eDP connector reported 1920x1080, but the screen remained black. The journal
recorded `Invalid interface id 0 on vp1`, followed by video stream clock and
page-flip timeouts. The USB keyboard successfully registered as a HID device.

The bridge driver's `rockchip_drm_encoder_set_crtc_endpoint_id(..., 0, 0)`
requires its input endpoint to be numbered zero. VP1 is identified by the
remote VOP port, whose eDP endpoint remains number 3. The original input
endpoint was incorrectly numbered 1. The corrected DTB changes only that
unit address and `reg` to zero; the local SD installation names this revision
edp02 and reuses the verified edp01 Image and modules. The verifier now rejects
the original route. The second hardware boot removed the invalid-interface,
bridge-commit and page-flip errors, created fb0, and enabled the backlight. The
keyboard was present after its initial re-enumeration. The observed screen was
still gray with no visible text, so display operation is not confirmed. The
user also reported flickering in the original Android system, then confirmed
that fixing the power cable stopped the Android flickering. A repeat Linux
test with stable power still showed gray without text. Its framebuffer and
additional display evidence were retrieved: the framebuffer contains Debian's
login prompt and the diagnostic message, while VP1 is active at 1920x1080.
The panel was still gray, so generated pixels have not reached a usable
physical display.

## VP1 pixel clock correction (local DTB revision edp03)

The stable-power boot's clock summary reports `dclk_vop1` at **24 MHz** under
HPLL, despite the mode requiring **148.5 MHz**. The original Android system
instead uses VPLL at 742.5 MHz and divides it down to 148.5 MHz. The pinned
6.18.63 clock driver does not list 742.5 MHz, but does support 594 MHz.

The corrected VOP assignments set VPLL to 594 MHz, select it as VP1's pixel
clock parent, and request 148.5 MHz (divide by four). This is explicit because
the RK3568 DCLK composite has `CLK_SET_RATE_NO_REPARENT` and does not propagate
rate changes to its parent. Only the VOP's three clock-assignment properties
change relative to edp02. The verifier checks the assignments and rejects the
previous DTB. The existing Image and modules are reused. After this correction,
the user confirmed visible Debian login text and a working Enter key. The
corrected boot's actual clock summary has not yet been retrieved; the last
retrieved evidence is from the preceding gray-screen boot. The board is left
running the working Linux console rather than rebooted solely for log retrieval.

The recorder saves dmesg before collecting connector status. Additional DRM,
clock and PWM reads now have individual time limits, since DRM state could
block behind a stalled modeset. The separate framebuffer helper saves the
fbdev geometry, color layout and at most 16 MiB of existing pixels without
changing the mode or drawing directly into framebuffer memory. Install it as
`/usr/local/sbin/tyc4a-framebuffer-evidence` with the shell recorder.
