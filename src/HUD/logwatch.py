"""Choose the actively written EQ log; never mix characters' combat state."""
from pathlib import Path
import datetime as dt
import re
import time

NAME = re.compile(r'^eqlog_([^_]+)_(.+)\.txt$', re.I)
STAMP = re.compile(rb'^\[([^]]+)\]')

def identity(path):
    match = NAME.match(Path(path).name)
    if not match:
        return 'Unknown', 'Unknown'
    character, server = match.groups()
    server = {'p1999green': 'Green', 'project1999': 'Blue'}.get(server.lower(), server)
    return character, server

def recent_event(path, now):
    try:
        with path.open('rb') as source:
            source.seek(max(0, path.stat().st_size - 8192))
            lines = source.read().splitlines()
        for line in reversed(lines):
            match = STAMP.match(line)
            if match:
                timestamp = dt.datetime.strptime(match[1].decode('ascii'), '%a %b %d %H:%M:%S %Y').timestamp()
                return abs(now - timestamp) < 180
    except (OSError, ValueError, UnicodeError):
        pass
    return False

class LogFollower:
    def __init__(self, directory, pinned=None):
        self.directory = Path(directory)
        self.pinned = Path(pinned) if pinned else None
        self.path = None
        self.stream = None
        self.seen = {}
        self.initialized = False

    def refresh(self, now=None):
        now = time.time() if now is None else now
        files = [self.pinned] if self.pinned else list(self.directory.glob('eqlog_*.txt'))
        stats = {}
        for path in files:
            try:
                if path.is_file():
                    stats[path] = path.stat()
            except OSError:
                pass
        chosen, offset = None, 0
        if not self.initialized:
            self.initialized = True
            if stats:
                chosen = max(stats, key=lambda p: stats[p].st_mtime_ns)
                offset = stats[chosen].st_size  # Start live, not by replaying an old archive.
        elif self.pinned:
            if self.stream is None and self.pinned in stats:
                chosen = self.pinned
        else:
            candidates = []
            for path, stat in stats.items():
                before = self.seen.get(path)
                changed = before is None or stat.st_size != before.st_size
                if path != self.path and changed and recent_event(path, now):
                    candidates.append(path)
            if candidates:
                chosen = max(candidates, key=lambda p: stats[p].st_mtime_ns)
                before = self.seen.get(chosen)
                offset = before.st_size if before and stats[chosen].st_size >= before.st_size else 0
        # A rotated or truncated current file starts a clean encounter.
        if chosen is None and self.path in stats and self.stream:
            stat, opened = stats[self.path], self.stream.fileno()
            import os
            if stat.st_ino != os.fstat(opened).st_ino or stat.st_size < self.stream.tell():
                chosen, offset = self.path, 0
        self.seen = stats
        if chosen is None:
            return False
        try:
            stream = chosen.open('r', encoding='utf-8', errors='replace')
            stream.seek(offset)
        except OSError:
            return False
        if self.stream:
            self.stream.close()
        self.stream, self.path = stream, chosen
        return True

    def read_lines(self, limit=1000):
        if not self.stream:
            return
        for _ in range(limit):
            position = self.stream.tell()
            line = self.stream.readline()
            if not line:
                return
            if not line.endswith('\n'):
                self.stream.seek(position)
                return
            yield line

    def close(self):
        if self.stream:
            self.stream.close()
