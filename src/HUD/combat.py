"""Combat accounting for EQ's observable log events. No inferred ownership."""
from collections import Counter, deque
from dataclasses import dataclass
import datetime as dt
import json
import re
import html
from functools import lru_cache

STAMP = re.compile(r'^\[([^]]+)\] (.*)$')
VERBS = r'hit|slash|pierce|crush|bash|kick|punch|backstab|bite|claw|frenzy|maul|strike|shoot|smash'
OUT = re.compile(r'^You (' + VERBS + r') (.+) for (\d+) points? of damage[.!]$', re.I)
MISS = re.compile(r'^You try to (.+?) (.+), but (?:miss|.+? avoids your attack)[.!]?$', re.I)
IN = re.compile(r'^(.+?) (?:hits|slashes|pierces|crushes|bashes|kicks|punches|backstabs|bites|claws|mauls|strikes|shoots|smashes) YOU for (\d+) points? of damage[.!]$', re.I)
IN_MAGIC = re.compile(r'^(?:You were hit by non-melee for|.*You have taken) (\d+)(?: points? of)? damage[.!]$', re.I)
OWN_SPELL = re.compile(r'^(.+?) has taken (\d+) damage from your (.+?)[.!]$', re.I)
OWN_DD = re.compile(r'^Your (.+?) (?:hits|strikes) (.+?) for (\d+)(?: points? of)? damage[.!]$', re.I)
UNKNOWN = re.compile(r'^(.+?) was hit by non-melee for (\d+)(?: points? of)? damage[.!]$', re.I)
OTHER_HIT = re.compile(r'^(.+?) (hits|slashes|pierces|crushes|bashes|kicks|punches|backstabs|bites|claws|mauls|strikes|shoots|smashes) (.+?) for (\d+) points? of damage[.!]$', re.I)
KILL = re.compile(r'^(?:You have slain (.+?)|(.+?) has been slain(?: by .+?)?)[.!]$', re.I)

@dataclass
class Event:
    timestamp: float
    kind: str
    target: str = ''
    amount: int = 0
    ability: str = ''

@lru_cache(maxsize=128)
def event_time(stamp):
    return dt.datetime.strptime(stamp, '%a %b %d %H:%M:%S %Y').timestamp()

def parse(line, pet_names=()):
    stamp = STAMP.match(line.rstrip())
    if not stamp:
        return None
    text = stamp[2]
    if 'damage' not in text.lower() and not any(marker in text.lower() for marker in
            ('you try to', 'slain', 'you have entered', 'loading, please wait')):
        return None
    try:
        timestamp = event_time(stamp[1])
    except ValueError:
        return None
    m = OUT.match(text)
    if m:
        return Event(timestamp, 'melee', m[2], int(m[3]), m[1].lower())
    m = OTHER_HIT.match(text)
    if m and m[1].casefold() in pet_names and m[3].upper() != 'YOU':
        return Event(timestamp, 'pet', m[3], int(m[4]), 'Pet: ' + m[2].lower())
    m = MISS.match(text)
    if m:
        return Event(timestamp, 'miss', m[2], ability=m[1].lower())
    m = IN.match(text)
    if m:
        return Event(timestamp, 'incoming', m[1], int(m[2]))
    m = IN_MAGIC.match(text)
    if m:
        return Event(timestamp, 'incoming', '', int(m[1]))
    m = OWN_SPELL.match(text)
    if m:
        return Event(timestamp, 'spell', m[1], int(m[2]), m[3])
    m = OWN_DD.match(text)
    if m:
        return Event(timestamp, 'spell', m[2], int(m[3]), m[1])
    m = UNKNOWN.match(text)
    if m:
        return Event(timestamp, 'unknown', m[1], int(m[2]))
    m = KILL.match(text)
    if m:
        return Event(timestamp, 'kill', m[1] or m[2])
    if text.startswith('You have been slain'):
        return Event(timestamp, 'death')
    if text.startswith('You have entered ') or text == 'LOADING, PLEASE WAIT...':
        return Event(timestamp, 'zone')
    return None

class CombatMeter:
    def __init__(self, history=None, idle_seconds=15, pet_names=()):
        self.history = history
        self.idle_seconds = idle_seconds
        self.current = None
        self.last = None
        self.rolling = deque()
        self.session_damage = 0
        self.session_seconds = 0
        self.encounters = 0
        self.pet_names = {name.casefold() for name in pet_names}

    def finish(self, reason):
        if self.current is None:
            return
        f = self.current
        duration = max(1, f['last'] - f['start'] + 1)
        summary = {**f, 'targets': sorted(f['targets']), 'alive': sorted(f['alive']),
                   'abilities': dict(f['abilities']), 'duration': duration,
                   'dps': f['damage'] / duration, 'reason': reason}
        self.last = summary
        self.encounters += 1
        self.session_seconds += duration
        self.current = None
        if self.history:
            self.history.parent.mkdir(parents=True, exist_ok=True)
            with self.history.open('a', encoding='utf-8') as output:
                output.write(json.dumps(summary, ensure_ascii=True) + '\n')
            self.write_history_page()

    def write_history_page(self):
        # Bound report work even after many sessions; the JSONL retains all records.
        records = deque(maxlen=100)
        self.history.parent.mkdir(parents=True, exist_ok=True)
        self.history.touch(exist_ok=True)
        with self.history.open('rb') as source:
            offset = max(0, self.history.stat().st_size - 1_048_576)
            source.seek(offset)
            if offset:
                source.readline()
            for line in source:
                try:
                    records.append(json.loads(line))
                except (ValueError, TypeError):
                    continue
        rows = []
        for fight in reversed(records):
            when = dt.datetime.fromtimestamp(fight['start']).strftime('%b %d %H:%M:%S')
            targets = ', '.join(fight['targets']) or 'Incoming damage'
            abilities = ' · '.join(f'{name}: {amount:,}' for name, amount in
                sorted(fight['abilities'].items(), key=lambda x: -x[1]))
            attempts = fight['hits'] + fight['misses']
            accuracy = f"{100*fight['hits']/attempts:.1f}%" if attempts else '—'
            rows.append(f"<tr><td>{when}</td><td>{html.escape(targets)}<small>{html.escape(abilities)}</small></td>"
                f"<td>{fight['damage']:,}</td><td>{fight['dps']:.1f}</td><td>{fight['duration']:.0f}s</td>"
                f"<td>{fight['biggest']:,}</td><td>{accuracy}</td><td>{fight['incoming']:,}</td>"
                f"<td>{fight['unattributed']:,}</td><td>{html.escape(fight['reason'])}</td></tr>")
        document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="15">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Bait &amp; Tackle — Combat History</title>
<style>body{background:#08191d;color:#e3e9e4;font:15px system-ui;margin:32px}h1{color:#d3b362;font-size:28px}p{color:#a6bdbc;max-width:960px}table{border-collapse:collapse;width:100%;background:#10262a}th,td{text-align:right;padding:12px;border-bottom:1px solid #294347}th{color:#d3b362}td:nth-child(1),td:nth-child(2),th:nth-child(1),th:nth-child(2){text-align:left}small{display:block;color:#87a5a7;margin-top:5px;font-size:12px}tr:hover{background:#1d3b3e}</style>
<h1>BAIT &amp; TACKLE</h1><p>Last 100 completed encounters, newest first. DPS uses the complete recorded fight duration. Unassigned magic is excluded from your damage. Pet ownership is not inferred. Same-name enemies can share a bucket. This page refreshes every 15 seconds.</p>
<table><thead><tr><th>Started</th><th>Target / abilities</th><th>Damage</th><th>DPS</th><th>Time</th><th>Biggest</th><th>Melee hit %</th><th>Taken</th><th>Unassigned</th><th>Ended</th></tr></thead><tbody>'''
        document += ''.join(rows) or '<tr><td colspan="10">No completed fights yet.</td></tr>'
        document += '</tbody></table></html>'
        self.history.with_suffix('.html').write_text(document, encoding='utf-8')
        (self.history.parent / 'latest.html').write_text(document, encoding='utf-8')

    def tick(self, now):
        if self.current and now - self.current['last'] > self.idle_seconds:
            self.finish('idle')
        while self.rolling and self.rolling[0][0] <= now - 12:
            self.rolling.popleft()

    def consume(self, line):
        event = parse(line, self.pet_names)
        if event is None:
            return False
        self.tick(event.timestamp)
        if event.kind in ('death', 'zone'):
            self.finish(event.kind)
            self.rolling.clear()
            return True
        if event.kind == 'kill':
            if self.current:
                matching = next((t for t in self.current['alive'] if t.casefold() == event.target.casefold()), None)
                if matching:
                    self.current['alive'].remove(matching)
                    if not self.current['alive']:
                        self.current['last'] = event.timestamp
                        self.finish('slain')
            return True
        if event.kind == 'unknown':
            # Nearby non-melee damage does not establish ownership, or start a fight.
            if self.current and any(t.casefold() == event.target.casefold() for t in self.current['targets']):
                self.current['unattributed'] += event.amount
            return True
        if self.current is None:
            self.current = {'start': event.timestamp, 'last': event.timestamp,
                'damage': 0, 'melee': 0, 'spell': 0, 'pet': 0, 'incoming': 0, 'unattributed': 0,
                'biggest': 0, 'hits': 0, 'misses': 0, 'targets': set(), 'alive': set(), 'abilities': Counter()}
        f = self.current
        f['last'] = max(f['last'], event.timestamp)
        if event.target:
            event.target = next((t for t in f['targets'] if t.casefold() == event.target.casefold()), event.target)
            # Log files lack unique NPC IDs; same-name NPCs share this bucket.
            f['targets'].add(event.target)
            f['alive'].add(event.target)
        if event.kind in ('melee', 'spell', 'pet'):
            f['damage'] += event.amount
            f[event.kind] += event.amount
            f['abilities'][event.ability] += event.amount
            f['biggest'] = max(f['biggest'], event.amount)
            self.session_damage += event.amount
            self.rolling.append((event.timestamp, event.amount))
            if event.kind == 'melee':
                f['hits'] += 1
        elif event.kind == 'miss':
            f['misses'] += 1
        elif event.kind == 'incoming':
            f['incoming'] += event.amount
        return True

    def snapshot(self, now):
        self.tick(now)
        f = self.current or self.last
        if f is None:
            return [0.] * 15 + [3.], 'Waiting for combat'
        elapsed = max(1, (now if self.current else f['last']) - f['start'] + 1)
        # Roll over a fixed 12-second window after its initial ramp-up.
        first = self.rolling[0][0] if self.rolling else now - 12
        denominator = max(1, min(12, now - min(first, f['start']) + 1))
        rolling_dps = sum(amount for _, amount in self.rolling) / denominator
        swings = f['hits'] + f['misses']
        active_seconds = self.session_seconds + (elapsed if self.current else 0)
        stats = [rolling_dps, f['damage'] / elapsed, float(f['damage']), elapsed,
            float(f['biggest']), float(f['hits']), float(f['misses']),
            100 * f['hits'] / swings if swings else 0., float(f['incoming']),
            f['incoming'] / elapsed, float(self.session_damage),
            self.session_damage / max(1, active_seconds), float(self.encounters),
            float(self.current is not None), float(f['unattributed']), 3.]
        targets = sorted(f['targets'])
        name = targets[0] if len(targets) == 1 else ('Multiple targets' if targets else 'Incoming damage')
        return stats, name
