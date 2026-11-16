#!/usr/bin/env python3
"""Check the live-board SDIO mapping while retaining display/keyboard checks."""
import importlib.util,json,sys,tarfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('usb_verify',Path(__file__).resolve().parents[1]/'usb/verify.py')
usb=importlib.util.module_from_spec(spec);spec.loader.exec_module(usb)
def verify(path):
 result=usb.verify(path)
 n=usb.edp.base.read_fdt(path);cells=usb.edp.cells
 ph={cells(p['phandle'])[0]:k for k,p in n.items() if 'phandle' in p}
 mmc=n['/mmc@fe2c0000']
 assert mmc['status']==b'okay\0'
 assert cells(mmc['bus-width'])==(4,)
 assert cells(mmc['max-frequency'])==(50000000,)
 for prop in ('non-removable','cap-sdio-irq','no-sd','no-mmc','no-1-8-v'):
  assert prop in mmc
 seq=n[ph[cells(mmc['mmc-pwrseq'])[0]]]
 assert seq['compatible']==b'mmc-pwrseq-simple\0'
 reset=cells(seq['reset-gpios'])
 assert ph[reset[0]]=='/pinctrl/gpio@fe750000' and reset[1:]==(9,1)
 assert cells(seq['post-power-on-delay-ms'])==(200,)
 clk=cells(seq['clocks'])
 assert ph[clk[0]]=='/i2c@fdd40000/pmic@20' and clk[1:]==(1,)
 rail=n['/regulator-wifi'];gpio=cells(rail['gpio'])
 assert ph[gpio[0]]=='/pinctrl/gpio@fe740000' and gpio[1:]==(0,0)
 assert 'regulator-always-on' in rail and 'enable-active-high' in rail
 result.update(kernel_release='6.18.63-tyc4a-wifi01',sdio_wiring='pass',sdio_max_hz=50000000,wifi_hardware_tested=False)
 return result
if __name__=='__main__':
 directory=Path(sys.argv[1]);result=verify(directory/'rk3566-tyc4a-wifi01.dtb')
 if '--dtb-only' not in sys.argv:
  image=(directory/'Image').read_bytes()
  assert len(image)>1024*1024 and image[56:60]==b'ARM\x64'
  assert (directory/'kernelrelease').read_text().strip()==result['kernel_release']
  config=(directory/'kernel.config').read_text().splitlines()
  for option in ('RTW88','RTW88_CORE','RTW88_SDIO','RTW88_8822C','RTW88_8822CS','PHY_ROCKCHIP_NANENG_EDP','DRM_ROCKCHIP','DRM_ANALOGIX_DP','DRM_PANEL_EDP','BACKLIGHT_PWM'):
   assert 'CONFIG_'+option+'=m' in config,option
  assert 'CONFIG_PWRSEQ_SIMPLE=y' in config
  with tarfile.open(directory/'modules.tar.gz') as tar:
   names=tar.getnames()
   for module in ('rtw88_core.ko','rtw88_sdio.ko','rtw88_8822c.ko','rtw88_8822cs.ko'):
    assert any(name.endswith('/'+module) for name in names),module
  result['kernel_and_wifi_modules']='pass'
 (directory/'wifi-validation.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
