#!/usr/bin/env python3
import hashlib,importlib.util,json,struct,sys
from pathlib import Path
baseline,new=map(Path,sys.argv[1:3])
assert hashlib.sha256(baseline.read_bytes()).hexdigest()=="4cbc7f8c3d59166d6ddec466865c257abf546c4721f42a8244940fa66a4a1aa9"
spec=importlib.util.spec_from_file_location('verify',Path(__file__).resolve().parents[2]/'scripts/verify-artifacts.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
a,b=v.read_fdt(baseline),v.read_fdt(new)
cells=lambda data:struct.unpack('>'+'I'*(len(data)//4),data)
pa={cells(props['phandle'])[0]:path for path,props in a.items() if 'phandle' in props};pb={cells(props['phandle'])[0]:path for path,props in b.items() if 'phandle' in props}
allowed={'status','max-frequency','cap-mmc-highspeed','no-sd','no-sdio','pinctrl-names','pinctrl-0'};changes=[]
for path in set(a)|set(b):
 if path not in a:
  assert path.startswith('/pinctrl/emmc/'),path
  continue
 assert path in b,path
 for prop in set(a[path])|set(b[path]):
  before=a[path].get(prop);after=b[path].get(prop)
  if before==after:continue
  if path=='/mmc@fe310000' and prop in allowed:changes.append(prop);continue
  assert before is not None and after is not None and len(before)==len(after) and len(before)%4==0,(path,prop)
  assert all(x==y or x in pa and y in pb and pa[x]==pb[y] for x,y in zip(cells(before),cells(after))),(path,prop)
emmc=b['/mmc@fe310000'];assert emmc['status']==b'okay\0' and cells(emmc['bus-width'])==(8,) and cells(emmc['max-frequency'])==(52000000,)
assert not any(x in emmc for x in ('mmc-hs200-1_8v','mmc-hs400-1_8v','mmc-ddr-1_8v'))
report={'baseline_matches_installed_dtb':True,'unrelated_nodes_unchanged_except_phandle_renumbering':True,'emmc_properties_changed':sorted(changes),'emmc_max_hz':52000000,'high_speed_modes_not_enabled':True,'sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'hardware_tested':False}

ph={cells(props['phandle'])[0]:path for path,props in b.items() if 'phandle' in props}
assert [ph[x] for x in cells(emmc['pinctrl-0'])]==['/pinctrl/emmc/emmc-bus8','/pinctrl/emmc/emmc-clk','/pinctrl/emmc/emmc-cmd']
for node,pins in [('emmc-bus8',list(range(12,20))),('emmc-clk',[21]),('emmc-cmd',[20])]:
 values=cells(b['/pinctrl/emmc/'+node]['rockchip,pins'])
 assert len(values)==4*len(pins)
 for group,pin in zip(zip(*[iter(values)]*4),pins):
  assert group[:3]==(1,pin,1) and ph[group[3]]=='/pinctrl/pcfg-pull-up-drv-level-2'
(new.parent/'emmc-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
