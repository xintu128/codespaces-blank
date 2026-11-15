#!/usr/bin/env python3
"""Check experimental hardware state and supply references. No hardware test is implied."""
import importlib.util
import json
import struct
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location('verify', Path(__file__).with_name('verify-artifacts.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
directory = Path(sys.argv[1])
nodes = module.read_fdt(directory / 'rk3566-tyc4a-sd-experimental.dtb')
for node in ('/mmc@fe2b0000', '/i2c@fdd40000', '/i2c@fdd40000/pmic@20', '/serial@fe660000'):
    assert nodes[node]['status'] == b'okay\0', node
for node in ('/mmc@fe310000', '/mmc@fe2c0000'):
    assert nodes[node]['status'] == b'disabled\0', node
cpus = [v for k, v in nodes.items() if k.startswith('/cpus/cpu@') and k.count('/') == 2]
assert len(cpus) == 4 and all('operating-points-v2' not in c for c in cpus)
sd = nodes['/mmc@fe2b0000']
assert 'no-1-8-v' in sd and struct.unpack('>I', sd['max-frequency'])[0] == 50000000
phandles = {struct.unpack('>I', v['phandle'])[0]: v for v in nodes.values() if 'phandle' in v}
expected = {'vmmc-supply': b'vcc3v3_sd\0', 'vqmmc-supply': b'vccio_sd\0'}
for prop, name in expected.items():
    assert phandles[struct.unpack('>I', sd[prop])[0]]['regulator-name'] == name
domains = [v for v in nodes.values() if b'rockchip,rk3568-pmu-io-voltage-domain\0' in v.get('compatible', b'')]
assert len(domains) == 1 and domains[0]['status'] == b'okay\0'
for prop, name in {'pmuio1-supply': 'vcc3v3_pmu', 'pmuio2-supply': 'vcc3v3_pmu',
                   'vccio1-supply': 'vccio_acodec', 'vccio2-supply': 'vcc_1v8',
                   'vccio3-supply': 'vccio_sd', 'vccio4-supply': 'vcc_1v8',
                   'vccio5-supply': 'vcc_3v3', 'vccio6-supply': 'vcc_1v8',
                   'vccio7-supply': 'vcc_3v3'}.items():
    assert phandles[struct.unpack('>I', domains[0][prop])[0]]['regulator-name'] == name.encode() + b'\0'
result = {'dtb_format': 'pass', 'dtb_flavor': 'experimental-sd', 'sd_pmic_uart_enabled': True,
          'supply_references': 'pass', 'cpu_dvfs_enabled': False, 'internal_emmc_enabled': False,
          'hardware_boot_tested': False, 'sd_boot_verified': False, 'bootloader_included': False}
(directory / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
