"""Generate an auditable inventory; retain the vendor SPDX without inventing licenses."""
import hashlib,json
from pathlib import Path

def generate(package):
    package=Path(package);hud=package/'payload/BFT_HUD';runtime=hud/'runtime'
    vendor=json.loads((runtime/'python-runtime.spdx.json').read_text())
    native=json.loads((package/'native-build.json').read_text())
    components=[{'name':p['name'],'version':p.get('versionInfo'),'license':p.get('licenseConcluded','NOASSERTION'),
                 'evidence':'payload/BFT_HUD/runtime/python-runtime.spdx.json','scope':'vendor-reported runtime component'} for p in vendor['packages']]
    components += [
        {'name':'Bait & Tackle','version':'0.7.1-candidate','evidence':'source-package.json'},
        {'name':'ReShade','scope':'bundled vendor binary','evidence':'payload manifest SHA256 and ReShade-LICENSE.md'},
        {'name':'w64devkit / MinGW-w64','scope':'build toolchain and statically linked runtime','version':'2.10.0','evidence':'native-build.json and THIRD_PARTY_NOTICES.md'},
        {'name':'OBS Studio','version':'33.0.1','scope':'optional download, not in package','url':'https://github.com/obsproject/obs-studio/releases/download/33.0.1/OBS-Studio-33.0.1-Windows-x64.zip','sha256':'0d9436451c2d772b33428e3fdae9776f071895c335de17283176306fb72651d3'},
        {'name':'Rustle UI 2 / community skin and map assets','scope':'inherited assets','evidence':'THIRD_PARTY_NOTICES.md and exact payload hashes'}]
    files={str(f.relative_to(package)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest()
           for f in sorted((package/'payload').rglob('*')) if f.is_file()}
    result={'schema':'bft-dependency-inventory-1','components':components,'payload_sha256':files,
            'native_binaries':native['binaries'],'limitations':'Vendor SPDX includes upstream components; this inventory is not a vulnerability clearance or an assertion that every vendor component is reachable. Preserve original license texts.'}
    (package/'dependency-inventory.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
