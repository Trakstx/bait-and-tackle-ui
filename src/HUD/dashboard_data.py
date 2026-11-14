"""Read-only dashboard data from local exports and bounded combat history."""
import json
from collections import deque
from pathlib import Path
from bank_view import read_export,bank_layout

def bank_snapshot(game):
    snapshots=[]
    if game is not None:
        for path in sorted(Path(game).glob('*-Inventory.txt')):
            try:
                before=path.stat();items=read_export(path);slots=bank_layout(path);after=path.stat()
                if (before.st_mtime_ns,before.st_size)!=(after.st_mtime_ns,after.st_size):continue
                snapshots.append({'character':path.name[:-len('-Inventory.txt')], 'updated':after.st_mtime,'items':items,'slots':slots})
            except (OSError,ValueError):continue
    active=''
    if game is not None:
        logs=list((Path(game)/'Logs').glob('eqlog_*.txt'))
        if logs:
            try: active=max(logs,key=lambda p:p.stat().st_mtime_ns).stem.split('_')[1]
            except (OSError,IndexError): pass
    return {'characters':snapshots,'active':active}

def history_snapshot(directory, character=''):
    files=sorted(Path(directory).glob('eqlog_*.jsonl'))
    choices=[{'id':p.stem,'name':p.stem.removeprefix('eqlog_')} for p in files]
    selected=next((p for p in files if p.stem==character),None)
    if selected is None and not character and files:
        selected=max(files,key=lambda p:p.stat().st_mtime_ns)
    records=deque(maxlen=100)
    if selected:
        try:
            with selected.open('rb') as source:
                offset=max(0,selected.stat().st_size-1048576);source.seek(offset)
                if offset:source.readline()
                for line in source:
                    try:
                        record=json.loads(line)
                        if isinstance(record,dict):records.append(record)
                    except (ValueError,TypeError):continue
        except OSError:pass
    return {'characters':choices,'selected':selected.stem if selected else '', 'fights':list(reversed(records))}
