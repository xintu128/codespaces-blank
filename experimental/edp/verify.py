#!/usr/bin/env python3
"""Verify the experimental eDP graph, card identity assumptions, and Image."""
import argparse
import importlib.util
import json
import struct
from pathlib import Path

loader = importlib.util.spec_from_file_location('base_verify', Path(__file__).resolve().parents[2] / 'scripts/verify-artifacts.py')
base = importlib.util.module_from_spec(loader)
loader.loader.exec_module(base)

def cells(data):
    return struct.unpack('>' + 'I' * (len(data) // 4), data)

def verify(dtb):
    n = base.read_fdt(dtb)
    by_phandle = {cells(p['phandle'])[0]: path for path, p in n.items() if 'phandle' in p}
    assert n['/mmc@fe310000']['status'] == b'disabled\0'
    assert n['/mmc@fe2b0000']['status'] == b'okay\0'
    for path in ('/vop@fe040000', '/iommu@fe043e00', '/edp@fe0c0000', '/syscon@fdcb0000/phy@0', '/pwm@fe6e0000'):
        assert n[path]['status'] == b'okay\0', path
    edp = n['/edp@fe0c0000']
    assert by_phandle[cells(edp['phys'])[0]] == '/syscon@fdcb0000/phy@0'
    assert 'force-hpd' in edp
    # analogix_dp-rockchip.c uses encoder_set_crtc_endpoint_id(..., 0, 0).
    # VP1 is the remote port number; the local bridge endpoint must be zero.
    bridge_input = '/edp@fe0c0000/ports/port@0/endpoint@0'
    vop_output = '/vop@fe040000/ports/port@1/endpoint@3'
    assert cells(n[bridge_input]['reg']) == (0,)
    assert by_phandle[cells(n[bridge_input]['remote-endpoint'])[0]] == vop_output
    assert cells(n[vop_output]['reg']) == (3,)
    # RK3568 binding IDs: PLL_VPLL=5, DCLK_VOP1=224. Set both the PLL and
    # divider explicitly: this composite clock has no rate propagation.
    vop = n['/vop@fe040000']
    clocks = cells(vop['assigned-clocks'])
    parents = cells(vop['assigned-clock-parents'])
    assert len(clocks) == 4 and clocks[0] == clocks[2]
    assert by_phandle[clocks[0]] == '/clock-controller@fdd20000'
    assert clocks[1::2] == (5, 224), clocks
    assert parents == (0, clocks[0], 5), parents
    assert cells(vop['assigned-clock-rates']) == (594000000, 148500000)
    bl = n['/backlight-edp']
    pwm = cells(bl['pwms'])
    assert by_phandle[pwm[0]] == '/pwm@fe6e0000' and pwm[1:] == (0, 25000, 0)
    assert cells(bl['enable-gpios'])[1:] == (23, 0)
    panel = n['/panel-edp']
    assert panel['compatible'] == b'tyc4a,internal-edp-panel\0'
    assert cells(panel['enable-gpios'])[1:] == (20, 0)
    assert 'no-hpd' in panel
    for path, props in n.items():
        if 'remote-endpoint' in props:
            other = by_phandle[cells(props['remote-endpoint'])[0]]
            assert by_phandle[cells(n[other]['remote-endpoint'])[0]] == path
    return {'dtb_format': 'pass', 'reciprocal_display_graph': 'pass',
            'bridge_input_endpoint_zero': 'pass',
            'vp1_pixel_clock_assignment': 'pass',
            'panel_gpio_pwm_mapping': 'pass', 'internal_emmc_enabled': False,
            'display_hardware_tested': False, 'kernel_release': '6.18.63-tyc4a-edp01'}

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('directory', type=Path)
    p.add_argument('--dtb-only', action='store_true')
    a = p.parse_args()
    result = verify(a.directory / 'rk3566-tyc4a-edp01.dtb')
    if not a.dtb_only:
        image = (a.directory / 'Image').read_bytes()
        assert len(image) > 1024 * 1024 and image[56:60] == b'ARM\x64'
        assert (a.directory / 'kernelrelease').read_text().strip() == result['kernel_release']
        config = (a.directory / 'kernel.config').read_text().splitlines()
        for symbol in ('PHY_ROCKCHIP_NANENG_EDP', 'DRM_ROCKCHIP', 'DRM_ANALOGIX_DP', 'DRM_PANEL_EDP', 'BACKLIGHT_PWM'):
            assert f'CONFIG_{symbol}=m' in config
        assert (a.directory / 'modules.tar.gz').stat().st_size > 1000000
        result['kernel_format'] = 'pass'
    (a.directory / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
