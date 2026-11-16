"""Validate and prepare bounded GPT label/type changes, without writing devices."""
import struct,uuid,zlib
LINUX_FS=uuid.UUID('0fc63daf-8483-4772-8e79-3d69d8477de4').bytes_le

def header_info(h):
 assert len(h)==512 and h[:8]==b'EFI PART'
 size,crc=struct.unpack_from('<II',h,12);assert 92<=size<=512
 check=bytearray(h[:size]);struct.pack_into('<I',check,16,0)
 assert zlib.crc32(check)==crc,'GPT header CRC mismatch'
 current,other,first,last=struct.unpack_from('<QQQQ',h,24)
 lba,n,entry_size,entries_crc=struct.unpack_from('<QIII',h,72)
 assert 0<n<=1024 and entry_size==128
 return {'current':current,'other':other,'first':first,'last':last,'entries_lba':lba,'count':n,'entry_size':entry_size,'entries_crc':entries_crc,'disk_guid':h[56:72]}

def validate(primary,entries,backup,backup_entries):
 a,b=header_info(primary),header_info(backup)
 assert a['current']==1 and a['other']==b['current'] and b['other']==1
 for key in ('first','last','count','entry_size','disk_guid','entries_crc'):assert a[key]==b[key],key
 assert entries==backup_entries and len(entries)==a['count']*a['entry_size']
 assert zlib.crc32(entries)==a['entries_crc'],'GPT entries CRC mismatch'
 return a,b

def partition(entries,number):
 e=entries[(number-1)*128:number*128]
 assert len(e)==128 and any(e[:16])
 start,end,attrs=struct.unpack_from('<QQQ',e,32)
 return {'type':e[:16],'uuid':e[16:32],'start':start,'end':end,'attrs':attrs,'name':e[56:128].decode('utf-16-le').rstrip('\0')}

def prepare(primary,entries,backup,backup_entries):
 a,b=validate(primary,entries,backup,backup_entries)
 boot,root=partition(entries,7),partition(entries,15)
 assert boot['name']=='boot' and boot['start']==51200 and boot['end']==133119
 assert root['name']=='userdata' and root['start']==8343552 and root['end']==61079487
 assert uuid.UUID(bytes_le=root['uuid'])==uuid.UUID('350d0000-0000-4722-8000-46f2000007ad')
 changed=bytearray(entries)
 for number,name in ((7,'android_boot_previous'),(15,'rootfs')):
  offset=(number-1)*128;changed[offset+56:offset+128]=name.encode('utf-16-le').ljust(72,b'\0')
 offset=14*128;changed[offset:offset+16]=LINUX_FS
 struct.pack_into('<Q',changed,offset+48,root['attrs']|4)
 def update(h):
  h=bytearray(h);struct.pack_into('<I',h,88,zlib.crc32(changed));struct.pack_into('<I',h,16,0)
  struct.pack_into('<I',h,16,zlib.crc32(h[:struct.unpack_from('<I',h,12)[0]]));return bytes(h)
 primary_new,backup_new=update(primary),update(backup)
 validate(primary_new,bytes(changed),backup_new,bytes(changed))
 for number in range(1,a['count']+1):
  before=entries[(number-1)*128:number*128];after=changed[(number-1)*128:number*128]
  if number not in (7,15):assert before==after,number
  else:
   assert before[16:48]==after[16:48],number
   if number==7:assert before[:56]==after[:56]
 return {'primary_header':primary_new,'backup_header':backup_new,'entries':bytes(changed),'primary_info':a,'backup_info':b}
