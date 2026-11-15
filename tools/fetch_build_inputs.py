"""Retrieve only hash-pinned inputs; extract the verified build toolchain and SDK."""
import argparse, hashlib, json, subprocess, urllib.request, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def fetch(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    pins=json.loads((ROOT/'tools/build-inputs.json').read_text())
    names={'compiler':'compiler.7z.exe','sdk':'sdk.zip','vendor_seed':'vendor-seed.zip','vision_fixture':'vision.zip'}
    for key,name in names.items():
        destination=output/name
        if not destination.exists():
            request=urllib.request.Request(pins[key]['url'],headers={'User-Agent':'BFT-reproducible-build/1'})
            with urllib.request.urlopen(request,timeout=60) as response,destination.open('wb') as result:
                size=0
                while chunk:=response.read(1024*1024):
                    size+=len(chunk)
                    if size>512*1024*1024:raise ValueError('Build input exceeds size limit')
                    result.write(chunk)
        if hashlib.sha256(destination.read_bytes()).hexdigest()!=pins[key]['sha256']:
            raise ValueError('Pinned build input mismatch: '+key)
    subprocess.run([str(output/names['compiler']),'-y','-o'+str(output/'compiler')],check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL)
    with zipfile.ZipFile(output/names['sdk']) as z:
        for member in z.infolist():
            if not (output/'sdk'/member.filename).resolve().is_relative_to(output/'sdk'):raise ValueError('Unsafe SDK path')
        z.extractall(output/'sdk')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();fetch(a.output)
