"""Run a fake EQ host and recording stub, never load an add-on into the actual game."""
import argparse, ctypes, os, shutil, subprocess, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test(compiler, scratch):
    compiler=str(Path(compiler).resolve());scratch=Path(scratch).resolve();scratch.mkdir(parents=True,exist_ok=True)
    source=ROOT/'src/native-and-tests'
    with tempfile.TemporaryDirectory(prefix='native bootstrap spaces ',dir=scratch) as temp:
        root=Path(temp);base=root/'BFT_HUD';(base/'runtime').mkdir(parents=True)
        flags=['-std=c++17','-m32','-D_WIN32_WINNT=0x0601','-static','-I'+str(source)]
        subprocess.run([compiler,*flags,str(source/'autostart_host_test.cpp'),'-o',str(root/'eqgame.exe'),'-luserenv','-ladvapi32','-luser32'],check=True)
        subprocess.run([compiler,*flags,'-municode','-mwindows',str(source/'autostart_recorder_test.cpp'),'-o',str(base/'runtime/pythonw.exe')],check=True)
        (base/'launcher.py').write_text('# inert fixture',encoding='utf8')
        proc=subprocess.Popen([str(root/'eqgame.exe')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        pid=proc.pid;stdout,stderr=proc.communicate(timeout=10)
        assert proc.returncode==0,(proc.returncode,stdout,stderr)
        no_desktop=b'BFT_EXPECT_BLOCKED=1' in stdout
        print(stdout.decode().strip())
        record=base/'record.txt'
        for _ in range(20):
            if record.exists():break
            time.sleep(.05)
        if no_desktop:
            assert not record.exists(),'Headless elevated host must not launch an elevated fallback'
        else:
            text=record.read_text(encoding='utf-16le')
            assert text.count(' HIDDEN\n')==1,text
            assert '--attach-only --game-pid '+str(pid) in text,text
            record.unlink()
        shutil.copy2(root/'eqgame.exe',root/'Other.exe')
        subprocess.run([str(root/'Other.exe')],check=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
        assert not record.exists()
    if no_desktop:print('PASS: elevated host without a matching standard desktop token refuses startup; no elevated fallback; non-EQ host ignored. Positive desktop handoff requires interactive validation.')
    else:print('PASS: automatic helper bootstrap once, hidden child, quoted spaced paths, exact PID, non-EQ host ignored')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--compiler',required=True);p.add_argument('--scratch',required=True)
    a=p.parse_args();test(a.compiler,a.scratch)
