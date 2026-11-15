"""Rebuild every first-party PE; emit exact input/output hashes, never reuse old binaries."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    'BFT_HUD.addon32': ('bft_addon.cpp', ['-shared']),
    'Play Bait and Tackle.exe': ('play_bft.cpp', ['-municode', '-mwindows']),
    'Refresh Bait and Tackle.exe': ('refresh_bft.cpp', ['-municode', '-mwindows']),
    'Restart BFT Settings.exe': ('restart_bft_ch.cpp', ['-municode', '-mwindows']),
    'CH Chain.exe': ('helper_launcher.cpp', ['-municode', '-mwindows', '-DBFT_SCRIPT=L"ch_overlay.py"', '-DBFT_SETTINGS']),
    'CH Chain Demo.exe': ('ch_demo_launcher.cpp', ['-municode', '-mwindows']),
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def build(compiler, sdk, output):
    compiler = Path(compiler).resolve(); sdk = Path(sdk).resolve(); output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'src/native-and-tests'
    inputs = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p)
              for p in sorted(source.iterdir()) if p.suffix in ('.cpp', '.hpp')}
    sdk_files = {str(p.relative_to(sdk)).replace('\\', '/'): sha(p) for p in sorted(sdk.rglob('*')) if p.is_file()}
    sdk_digest = hashlib.sha256(json.dumps(sdk_files, sort_keys=True).encode()).hexdigest()
    environment = dict(os.environ, SOURCE_DATE_EPOCH='1700000000')
    flags = ['-std=c++17', '-m32', '-D_WIN32_WINNT=0x0601', '-O2', '-static', '-s',
             '-Wl,--no-insert-timestamp', '-frandom-seed=bft-native-v1',
             '-ffile-prefix-map='+str(ROOT)+'=.', '-I'+str(sdk)]
    commands = {}; outputs = {}
    for name, (filename, mode) in TARGETS.items():
        args = [str(compiler), *flags, *mode, *(['-Wl,--image-base,0x68000000'] if name.endswith('.addon32') else []), 'src/native-and-tests/'+filename,
                '-o', str(output/name), '-luserenv', '-ladvapi32', '-luser32', '-lshell32', '-lole32', '-luuid']
        subprocess.run(args, cwd=ROOT, env=environment, check=True)
        commands[name] = [arg.replace(str(ROOT), '${SOURCE}').replace(str(output), '${OUTPUT}').replace(str(sdk), '${SDK}').replace(str(compiler), '${CXX}') for arg in args]
        outputs[name] = sha(output/name)
    receipt = {'schema': 1, 'compiler_sha256': sha(compiler),
               'compiler_version': subprocess.check_output([str(compiler), '--version'], text=True).splitlines()[0],
               'sdk_tree_sha256': sdk_digest, 'sources': inputs, 'commands': commands, 'binaries': outputs,
               'signed': False, 'note': 'Build receipt, not independent security certification or P1999 approval.'}
    (output/'native-build.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--compiler', required=True)
    parser.add_argument('--sdk', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); build(args.compiler, args.sdk, args.output)
