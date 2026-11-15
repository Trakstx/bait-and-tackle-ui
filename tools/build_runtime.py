"""Assemble PSF's matching embedded Python + Tk MSI payload; never install system Python."""
import argparse,ctypes,hashlib,json,shutil,subprocess,tempfile,urllib.request,zipfile
from pathlib import Path
VERSION='3.14.10'
PINS={
 'python-3.14.10-embed-amd64.zip.spdx.json':'d448c78f5fae170303d3b022d61507155e4d30e541c32bff3a4edd2b1e8dbf47',
 'python-3.14.10-embed-amd64.zip':'90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159',
 'amd64/tcltk.msi':'9642593510b188aa35dcdf1995cbe2b3c3c07446a0ac1dd0c1d1958bf25526f5',
}
class Database:
 def __init__(self,path):
  self.api=ctypes.WinDLL('msi');self.handle=ctypes.c_uint()
  self.api.MsiOpenDatabaseW.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint)]
  self.api.MsiDatabaseOpenViewW.argtypes=[ctypes.c_uint,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint)]
  self.api.MsiRecordGetStringW.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint)]
  if self.api.MsiOpenDatabaseW(str(path),None,ctypes.byref(self.handle)):raise OSError('Cannot open vendor MSI read-only')
 def close(self):
  if self.handle.value:self.api.MsiCloseHandle(self.handle.value);self.handle.value=0
 def __del__(self):self.close()
def rows(database,sql):
 api=database.api;view=ctypes.c_uint();record=ctypes.c_uint();result=[]
 if api.MsiDatabaseOpenViewW(database.handle.value,sql,ctypes.byref(view)):raise OSError('Cannot query MSI')
 try:
  if api.MsiViewExecute(view.value,0):raise OSError('MSI query failed')
  while True:
   code=api.MsiViewFetch(view.value,ctypes.byref(record))
   if code==259:break
   if code:raise OSError('MSI row fetch failed')
   try:
    values=[]
    for field in range(1,api.MsiRecordGetFieldCount(record.value)+1):
     size=ctypes.c_uint(0);api.MsiRecordGetStringW(record.value,field,None,ctypes.byref(size))
     buffer=ctypes.create_unicode_buffer(size.value+1);size.value+=1
     if api.MsiRecordGetStringW(record.value,field,buffer,ctypes.byref(size)):raise OSError('MSI field read failed')
     values.append(buffer.value)
    result.append(values)
   finally:api.MsiCloseHandle(record.value);record.value=0
 finally:api.MsiCloseHandle(view.value)
 return result
def cabinet(msi,path):
 api=ctypes.WinDLL('msi');handle=ctypes.c_uint();view=ctypes.c_uint();record=ctypes.c_uint()
 api.MsiOpenDatabaseW.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint)]
 api.MsiDatabaseOpenViewW.argtypes=[ctypes.c_uint,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint)]
 assert api.MsiOpenDatabaseW(str(msi),None,ctypes.byref(handle))==0
 try:
  assert api.MsiDatabaseOpenViewW(handle.value,"SELECT `Data` FROM `_Streams` WHERE `Name`='cab1.cab'",ctypes.byref(view))==0
  assert api.MsiViewExecute(view.value,0)==0 and api.MsiViewFetch(view.value,ctypes.byref(record))==0
  with path.open('wb') as f:
   while True:
    buffer=ctypes.create_string_buffer(65536);size=ctypes.c_uint(len(buffer))
    code=api.MsiRecordReadStream(record.value,1,buffer,ctypes.byref(size))
    if code:raise OSError('MSI stream read failed: '+str(code))
    if not size.value:break
    f.write(buffer.raw[:size.value])
 finally:
  for value in (record,view,handle):
   if value.value:api.MsiCloseHandle(value.value)
def build(cache,output):
 cache=Path(cache).resolve();output=Path(output).resolve();cache.mkdir(parents=True,exist_ok=True)
 if output.exists():raise ValueError('Runtime output must be a new directory.')
 for relative,digest in PINS.items():
  destination=cache/Path(relative).name
  if not destination.exists():urllib.request.urlretrieve('https://www.python.org/ftp/python/'+VERSION+'/'+relative,destination)
  if hashlib.sha256(destination.read_bytes()).hexdigest()!=digest:raise ValueError('PSF runtime input hash mismatch: '+relative)
 output.mkdir(parents=True)
 with zipfile.ZipFile(cache/'python-3.14.10-embed-amd64.zip') as z:z.extractall(output)
 msi=cache/'tcltk.msi';database=Database(msi)
 directories={a:(b,c) for a,b,c in rows(database,'SELECT `Directory`,`Directory_Parent`,`DefaultDir` FROM `Directory`')}
 components={a:b for a,b in rows(database,'SELECT `Component`,`Directory_` FROM `Component`')}
 def directory(key):
  if key in ('TARGETDIR','INSTALLDIR'):return Path()
  parent,name=directories[key];name=name.split(':')[0].split('|')[-1]
  return directory(parent)/(name if name not in ('.','SourceDir') else '')
 with tempfile.TemporaryDirectory(dir=cache) as temporary:
  temp=Path(temporary);cabinet(msi,temp/'tk.cab');(temp/'expanded').mkdir()
  subprocess.run([str(Path('C:/Windows/System32/expand.exe')),'-F:*',str(temp/'tk.cab'),str(temp/'expanded')],check=True,stdout=subprocess.DEVNULL)
  for identifier,component,filename in rows(database,'SELECT `File`,`Component_`,`FileName` FROM `File`'):
   relative=directory(components[component])/filename.split('|')[-1]
   if any(x in relative.parts for x in ('nmake','demos','test','tests','idlelib','turtledemo','__pycache__')) or relative.suffix in ('.lib','.h','.c','.vc','.pyc'):continue
   destination=output/relative;destination.resolve().relative_to(output)
   destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(temp/'expanded'/identifier,destination)
 for p in output.glob('_test*'):p.unlink()
 (output/'python314._pth').write_bytes(b'python314.zip\n.\nDLLs\nLib\n..\n')
 shutil.copyfile(cache/'python-3.14.10-embed-amd64.zip.spdx.json',output/'python-runtime.spdx.json')
 files={str(f.relative_to(output)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(output.rglob('*')) if f.is_file()}
 (output/'runtime-provenance.json').write_text(json.dumps({'python':VERSION,'inputs':PINS,'files':files,'source':'Python Software Foundation official embedded archive and matching Tcl/Tk MSI; no mixed-version DLLs'},indent=2)+'\n',encoding='utf8')
 print('Runtime assembled:',VERSION,len(files),'files')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--output',required=True);a=p.parse_args();build(a.cache,a.output)
