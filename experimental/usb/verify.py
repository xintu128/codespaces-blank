#!/usr/bin/env python3
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location('edp_verify', Path(__file__).resolve().parents[1] / 'edp/verify.py')
edp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(edp)

def verify(path):
    result = edp.verify(path)
    nodes = edp.base.read_fdt(path)
    phandles = {edp.cells(p['phandle'])[0]: name for name, p in nodes.items() if 'phandle' in p}
    host = '/usb2phy@fe8b0000/host-port'
    for name in ('/usb@fd880000', '/usb@fd8c0000', '/usb2phy@fe8b0000', host):
        assert nodes[name]['status'] == b'okay\0', name
    for name in ('/usb@fd800000', '/usb@fd840000', '/usb2phy@fe8b0000/otg-port'):
        assert nodes[name]['status'] == b'disabled\0', name
    for name in ('/usb@fd880000', '/usb@fd8c0000'):
        assert phandles[edp.cells(nodes[name]['phys'])[0]] == host
    supply = phandles[edp.cells(nodes[host]['phy-supply'])[0]]
    assert supply == '/regulator-5v0-host'
    gpio = edp.cells(nodes[supply]['gpio'])
    assert phandles[gpio[0]] == '/pinctrl/gpio@fdd60000' and gpio[1:] == (6, 0)
    assert 'enable-active-high' in nodes[supply]
    result.update({'host1_keyboard_mapping': 'pass', 'otg_charging_path_changed': False,
                   'usb_hardware_tested': False})
    return result

if __name__ == '__main__':
    path = Path(sys.argv[1])
    result = verify(path)
    (path.parent / 'usb-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
