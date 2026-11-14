"""Read-only EQ log feeder for the BFT graphics integration prototype."""
import argparse
import ctypes
import math
import mmap
import struct
import time
import os
import json
from pathlib import Path
from combat import CombatMeter
from threat import ThreatMeter
import settings_store
from logwatch import LogFollower, identity

MAP_NAME = r"Local\BFT_HUD_V1"
MAGIC = 0x31465442
# magic, generation, monotonic heartbeat, DPS, damage, encounter seconds, demo flag
PACK = struct.Struct("<IIdffff")
EXTRA = struct.Struct("<16f64s64s")

def publish(memory, generation, dps, damage, seconds, demo, stats=None, target="Waiting for combat", character="Waiting for login"):
    # Seqlock: an odd generation marks a write in progress.
    memory.seek(4)
    memory.write(struct.pack("<I", generation * 2 + 1))
    payload = PACK.pack(MAGIC, generation * 2 + 1, time.monotonic(), dps, damage, seconds, float(demo))
    memory.seek(0)
    memory.write(payload)
    if stats is None: stats = [0.] * 15 + [3.]
    memory.write(EXTRA.pack(*stats, target.encode("ascii", "replace")[:63].ljust(64, b"\0"), character.encode("ascii", "replace")[:63].ljust(64, b"\0")))
    memory.seek(4)
    memory.write(struct.pack("<I", generation * 2 + 2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--log", default=None)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--logs-dir", default=r"C:\EverQuest Project 1999\Logs")
    parser.add_argument("--seconds", type=float, default=0)
    args = parser.parse_args()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    mutex = kernel.CreateMutexW(None, False, r"Local\BFT_HUD_Feeder")
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle(mutex)
        print("A BFT HUD feed is already running. Close it before switching modes.")
        return
    runtime = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "BaitAndTackle"
    config_path = Path(__file__).with_name('config.json')
    config = json.loads(config_path.read_text()) if config_path.is_file() else {}
    follower = LogFollower(args.logs_dir, pinned=None if args.auto or not args.log else args.log)
    meter = CombatMeter()
    character = 'Waiting for login'
    threat_config=json.loads((Path(__file__).with_name('threat_config.json')).read_text())
    threat_meter=ThreatMeter(Path(args.logs_dir).parent,'',threat_config)
    threat_report_at=0
    def switched():
        nonlocal meter, character, threat_meter
        meter.finish('character/log changed')
        name, server = identity(follower.path)
        character = name + ' [' + server + ']'
        threat_meter.close();threat_meter=ThreatMeter(Path(args.logs_dir).parent,name,threat_config)
        try:
            with follower.path.open('rb') as log:
                log.seek(max(0,follower.path.stat().st_size-1048576));tail=log.read().decode('utf-8',errors='replace')
            for line in tail.splitlines():
                match=__import__('combat').STAMP.match(line)
                if match:threat_meter.learn(match[2])
        except OSError:pass
        history = runtime / 'history' / (follower.path.stem + '.jsonl')
        pets = config.get('pet_names_by_character', {}).get(name, config.get('pet_names', []))
        meter = CombatMeter(history=history, pet_names=pets)
        settings_store.apply_dps(meter, name, settings_store.load(), config)
        meter.write_history_page()
        print('Following ' + character + ': ' + str(follower.path), flush=True)
    if not args.demo and follower.refresh():
        switched()
    print('BFT HUD feed running: ' + ('DEMO TEST DATA' if args.demo else 'automatic log detection' if not follower.pinned else str(follower.pinned)), flush=True)
    print('Rolling/encounter DPS, attributed spell/pet damage, accuracy and saved fights. Ctrl+C stops.', flush=True)
    started = time.monotonic()
    generation = 0
    last_file_check = 0
    try:
        with mmap.mmap(-1, 4096, tagname=MAP_NAME, access=mmap.ACCESS_WRITE) as memory:
            while not args.seconds or time.monotonic() - started < args.seconds:
                elapsed = time.monotonic() - started
                if args.demo:
                    dps = 50 + 45 * math.sin(elapsed / 2)
                    damage, seconds = dps * max(1, elapsed), elapsed
                    stats = [dps, dps*.85, damage, seconds, 275., 100., 12., 89.3,
                             1240., 12., damage+25000., 135., 8., 1., 90., 3.]
                    target = "a drolvarg savage"
                    character = "Trackstack [Green]"
                else:
                    if time.monotonic() - last_file_check > 1:
                        last_file_check = time.monotonic()
                        if follower.refresh():
                            switched()
                        name, _ = identity(follower.path) if follower.path else ('', '')
                        settings_store.apply_dps(meter, name, settings_store.load(), config)
                    for line in follower.read_lines():
                        meter.consume(line)
                        threat_meter.consume(line)
                    stats, target = meter.snapshot(time.time())
                    dps, damage, seconds = stats[0], stats[2], stats[3]
                if not args.demo:
                    prefs=settings_store.load().get('aggro',{})
                    estimate=threat_meter.snapshot(time.time())
                    stats[9:13]=estimate if prefs.get('enabled',True) else [0.,0.,0.,-1.]
                    if time.monotonic()-threat_report_at>=1:
                        threat_report_at=time.monotonic();threat_meter.write_status(runtime/'threat-status.json',time.time())
                publish(memory, generation, dps, damage, seconds, (args.demo if getattr(meter,'visible',True) else -2.0), stats, target, character)
                generation += 1
                time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        if not args.demo:
            meter.finish("feed stopped")
        threat_meter.close()
        follower.close()
        kernel.CloseHandle(mutex)


if __name__ == "__main__":
    main()
