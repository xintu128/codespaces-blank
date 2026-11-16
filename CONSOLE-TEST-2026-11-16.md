# TYC4A local SD text-console test, 2026-11-16

The user confirmed that the internal screen shows Debian login text and the
USB keyboard responds to Enter after the VP1 clock correction. The board was
left running Linux. This is a limited hardware result on one board and one
locally configured SD card, not a fully validated Armbian image or internal
installation procedure.

## Exact installed components

- Kernel release: `6.18.63-tyc4a-edp01`.
- Image SHA-256: `cd66bb6dad8a1016db9f18575c056b85caa62656d3ddd1a8c0b8f9c1e1e32576`.
- Selected entry: `tyc4a-edp03-usb`.
- Installed USB DTB: `rk3566-tyc4a-edp03-usb.dtb`.
- USB DTB SHA-256: `599cd66470bf4514b688e2dd141eb7a5de0712c9b66579b3fe9c26b13201707a`.
- Non-USB DTB SHA-256: `7f0b1f53b4ebcf7575eea912b15c09d8bd2af588cfb4b1e778c7f277770fddf3`.

The build source retains the `rk3566-tyc4a-edp01*.dtb` output names. Local
installation used side-by-side `edp02`/`edp03` filenames so that earlier boot
entries and their files could be kept unchanged. The clock fix only changes
the VOP's assigned clocks, parents and rates; Image and modules were reused.

## Evidence and fixes

1. The original diagnostics boot reached Debian userspace without an enabled
   VOP. The first eDP boot then failed with `Invalid interface id 0 on vp1`
   and repeated display timeouts.
2. The Analogix bridge requires input port 0, endpoint 0. Correcting the
   local input endpoint while retaining VOP VP1 output endpoint 3 removed
   these errors and created the framebuffer. The screen was still gray.
3. Flickering also occurred in Android. The user fixed the power cable and
   confirmed the Android flickering stopped. A repeat Linux boot with stable
   power still showed gray, separating this from the remaining display fault.
4. A read-only framebuffer capture contained Debian's login prompt and a
   diagnostic message. DRM state showed a 1920x1080 active VP1, but the clock
   summary showed `dclk_vop1` at 24 MHz under bypassed HPLL. Android instead
   used VPLL at 742.5 MHz and a 148.5 MHz pixel clock.
5. The pinned mainline clock table supports 594 MHz. Explicitly setting VPLL
   to 594 MHz, selecting it as VP1's parent and dividing to 148.5 MHz produced
   the user-confirmed visible login text and working Enter key.

The post-fix clock summary and raw logs have not yet been retrieved, because
the board is being kept in the working Linux session. The hardware result is
the user's direct observation; the preceding gray-screen boot has saved DRM,
clock, framebuffer and journal evidence locally.

## Limits and preservation

The original Image, DTB, SD loader and fallback entries were retained. No
internal Android firmware was modified. Internal eMMC remains disabled in
the experimental DTB. The cloud rootfs still has locked accounts; credentials
configured on the local card are private and not in this repository.

Wi-Fi, full keyboard layout, touchpad operation, audio, battery/charging,
CPU DVFS, suspend/resume, desktop graphics and repeated cold/warm boots have
not been validated. The older assembled image is retained unchanged. A
separate private local candidate has been rebuilt with the tested Image,
edp03 DTBs, 885 module files and the existing local login configuration. Its
ext4 check, component readbacks, preserved first 16 MiB, reconstructed rootfs
payload and compression round trip passed. The new 3,238,002,688-byte image
has not been flashed or boot-tested; it is not a complete backup of the
running card. It remains local because it includes private login configuration
and original vendor loaders. Cloud artifacts contain build outputs, not proof
that every SD image or device configuration will boot.
