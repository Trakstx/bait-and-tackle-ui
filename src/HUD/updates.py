"""Explicit GitHub release checks; no background telemetry or automatic installation."""
import hashlib,json,os,re,threading,urllib.request,zipfile
from pathlib import Path
VERSION="0.7.0"
REPO="Trakstx/bait-and-tackle-ui"
ROOT="https://github.com/"+REPO
class Updates:
 def __init__(self):
  self.lock=threading.Lock();self.state={"current":VERSION,"status":"idle","message":"Check GitHub for a newer release."};self.release=None
 def snapshot(self):
  with self.lock:return dict(self.state)
 def request(self,action):
  if action not in ("check","download"):raise ValueError("Unknown update action")
  with self.lock:
   if self.state["status"] in ("checking","downloading"):raise ValueError("An update operation is already running")
   if action=="download" and not self.release:raise ValueError("Check for updates first")
   self.state.update(status="checking" if action=="check" else "downloading",message="Contacting GitHub…" if action=="check" else "Downloading and verifying package…")
  threading.Thread(target=self.work,args=(action,),daemon=True).start();return self.snapshot()
 def get(self,url,limit):
  req=urllib.request.Request(url,headers={"User-Agent":"BaitAndTackle/"+VERSION,"Accept":"application/vnd.github+json"})
  with urllib.request.urlopen(req,timeout=45) as response:
   data=response.read(limit+1)
  if len(data)>limit:raise ValueError("Release download exceeds the allowed size")
  return data
 def work(self,action):
  try:
   if action=="check":
    r=json.loads(self.get("https://api.github.com/repos/"+REPO+"/releases/latest",1024*1024));v=r["tag_name"].removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+",v):raise ValueError("Unsupported release version")
    assets={a["name"]:a for a in r["assets"]};name="Bait-and-Tackle-v"+v+".zip"
    newer=tuple(map(int,v.split(".")))>tuple(map(int,VERSION.split(".")))
    self.release=(v,name,assets) if newer and name in assets and "SHA256SUMS.txt" in assets else None
    result={"status":"available" if self.release else "current","latest":v,"message":("Version "+v+" is available.") if self.release else "No newer installable release is available.","release_url":ROOT+"/releases/tag/v"+v}
   else:
    v,name,assets=self.release
    def asset(n):
     u=assets[n]["browser_download_url"]
     if not u.startswith(ROOT+"/releases/download/v"+v+"/"):raise ValueError("Unexpected release asset URL")
     return self.get(u,300*1024*1024 if n==name else 65536)
    checks=asset("SHA256SUMS.txt").decode();expected=None
    for line in checks.splitlines():
     parts=line.split()
     if len(parts)==2 and parts[1].lstrip("*")==name:expected=parts[0]
    if not expected or not re.fullmatch("[a-fA-F0-9]{64}",expected):raise ValueError("Release checksum is missing")
    data=asset(name)
    if hashlib.sha256(data).hexdigest().lower()!=expected.lower():raise ValueError("Release checksum mismatch")
    folder=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"BaitAndTackle"/"updates"/v;folder.mkdir(parents=True,exist_ok=True)
    archive=folder/name;archive.write_bytes(data)
    with zipfile.ZipFile(archive) as z:
     if sum(i.file_size for i in z.infolist())>1024*1024*1024:raise ValueError("Expanded package too large")
     for i in z.infolist():
      target=(folder/i.filename).resolve();target.relative_to(folder.resolve())
      if "\\" in i.filename or ":" in i.filename:raise ValueError("Invalid archive path")
     z.extractall(folder)
    result={"status":"ready","message":"Verified update ready. Close EQ, open this folder and run Install Bait and Tackle.cmd. Your settings remain in LocalAppData.","folder":str(folder)}
   with self.lock:self.state.update(result)
  except Exception as e:
   with self.lock:self.state.update(status="error",message=str(e))
