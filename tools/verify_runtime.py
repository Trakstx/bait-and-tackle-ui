"""Exercise the isolated embedded interpreter, including hostile startup-hook canaries."""
import argparse, json, os, subprocess, tempfile
from pathlib import Path

def verify(hud):
    hud=Path(hud).resolve(); python=hud/'runtime/python.exe'
    # These locations were searched by the old _pth/site startup path.
    with tempfile.TemporaryDirectory(prefix='bft-startup-canary-') as tmp:
        external=Path(tmp)
        hook=external/'sitecustomize.py'; hook.write_text("raise RuntimeError('EXTERNAL_STARTUP_HOOK_EXECUTED')",encoding='utf8')
        code="import sys,json,tkinter,sqlite3,ssl,ctypes,settings_hub,class_triggers,recorder,feeder,ch_overlay; print(json.dumps({'paths':sys.path,'site':'site' in sys.modules,'tk':tkinter.Tcl().eval('info patchlevel')}))"
        result=subprocess.run([str(python),'-B','-c',code],cwd=external,env=dict(os.environ,PYTHONPATH=str(external)),capture_output=True,text=True,check=True)
        data=json.loads(result.stdout)
        expected=[hud/'runtime',hud/'runtime/DLLs',hud/'runtime/Lib',hud]
        assert [Path(p).resolve() for p in data['paths']]==expected, data
        assert not data['site'] and 'EXTERNAL_STARTUP' not in result.stderr, result.stderr
    print('PASS: private paths only, site hooks disabled, dashboard/recording/parser/Tk imports intact')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hud',required=True);a=p.parse_args();verify(a.hud)
