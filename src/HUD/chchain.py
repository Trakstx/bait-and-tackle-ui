"""CH announcement parser. No game input, memory access, or inferred heal confirmations."""
import dataclasses
import datetime
import json
import re
from pathlib import Path

DEFAULTS = dict(enabled=True, template='{slot} CH -- {target}', channel='any',
                roster=[], my_slot='', cast_seconds=10.0, interval_seconds=3.0,
                idle_seconds=30.0, sound=False)
SLOT = r'(?:\d{1,3}|[A-Za-z]{3}|RAMP\d{1,3})'
CHAT = re.compile(r"^(?P<speaker>You|[A-Za-z][A-Za-z`'-]*) (?P<verb>tells the guild|tell the guild|tell your guild|say to your guild|tells the group|tell the group|tell your party|tells the raid|tell the raid|tell your raid|says out of character|say out of character|shouts|shout|auctions|auction|says|say), '(?P<message>.*)'$")

def normalize_slot(value):
    value = value.strip().upper()
    if not re.fullmatch(SLOT, value, re.I):
        raise ValueError('Slots must be 1-3 digits, three identical letters, or RAMP1-RAMP999.')
    if value.isalpha() and len(set(value)) != 1:
        raise ValueError('Letter slots must repeat: AAA, BBB, etc.')
    return str(int(value)).zfill(3) if value.isdigit() else value

def compile_template(template):
    if len(template) > 200 or template.count('{slot}') < 1 or template.count('{target}') != 1:
        raise ValueError('Announcement must contain {slot} and exactly one {target}.')
    parts = re.split(r'(\{slot\}|\{target\})', template.strip())
    result = []
    seen_slot = False
    for part in parts:
        if part == '{slot}':
            result.append('(?P=slot)' if seen_slot else '(?P<slot>' + SLOT + ')')
            seen_slot = True
        elif part == '{target}': result.append(r"(?P<target>[A-Za-z][A-Za-z0-9`' -]{0,63}?)")
        else:
            if '{' in part or '}' in part: raise ValueError('Only {slot} and {target} placeholders are supported.')
            result.append(re.sub(r'(?:\\ )+', r'\\s+', re.escape(part)))
    return re.compile(r'^\s*' + ''.join(result) + r'\s*$', re.I)

def validate(config):
    c = dict(DEFAULTS, **config)
    c['template'] = str(c['template']).strip()
    compile_template(c['template'])
    if c['channel'] not in ['any', 'guild', 'group', 'raid', 'shout', 'say', 'ooc', 'auction']:
        raise ValueError('Unknown chat channel.')
    if not isinstance(c['roster'], list) or len(c['roster']) > 64: raise ValueError('Roster must be a list of at most 64 slots.')
    c['roster'] = [normalize_slot(str(x)) for x in c['roster']]
    if len(set(c['roster'])) != len(c['roster']): raise ValueError('Roster contains duplicate slots.')
    c['my_slot'] = normalize_slot(c['my_slot']) if c['my_slot'].strip() else ''
    for key, low, high in [('cast_seconds', 1, 60), ('interval_seconds', .2, 60), ('idle_seconds', 5, 600)]:
        c[key] = float(c[key])
        if not low <= c[key] <= high: raise ValueError(f'{key} must be between {low} and {high}.')
    if c['idle_seconds'] < c['cast_seconds']: raise ValueError('Idle timeout must be at least the cast duration.')
    return c

def save_config(path, config):
    c = validate(config)
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(c, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
    return c

@dataclasses.dataclass
class Cast:
    slot: str
    speaker: str
    target: str
    started: float

class Chain:
    def __init__(self, config=None):
        self.config = validate(config or {})
        self.pattern = compile_template(self.config['template'])
        self.casts = {}
        self.last = None
        self.observed = set()
        self.seen = set()

    def consume(self, line, now, character='You'):
        if not self.config['enabled']: return False
        event_time = now
        stamp = re.match(r'^\[([^]]+)\]\s*(.*)', line.rstrip('\r\n'))
        if stamp:
            try: event_time = datetime.datetime.strptime(stamp[1], '%a %b %d %H:%M:%S %Y').timestamp()
            except ValueError: return False
            line = stamp[2]
        if now - event_time > self.config['idle_seconds'] or event_time > now + 2: return False
        chat = CHAT.fullmatch(line)
        if not chat: return False
        verb = chat['verb']
        channel = ('guild' if 'guild' in verb else 'group' if 'group' in verb or 'party' in verb else 'raid' if 'raid' in verb
                   else 'ooc' if 'out of character' in verb else 'shout' if verb.startswith('shout')
                   else 'auction' if verb.startswith('auction') else 'say')
        if self.config['channel'] not in ('any', channel): return False
        match = self.pattern.fullmatch(chat['message'])
        if not match: return False
        try: slot = normalize_slot(match['slot'])
        except ValueError: return False
        if self.config['roster'] and slot not in self.config['roster']: return False
        speaker = character if chat['speaker'] == 'You' else chat['speaker']
        key = (event_time, slot, speaker, match['target'].strip())
        if key in self.seen: return False
        # Never regress timers when a late-written log line arrives out of order.
        if self.last and event_time < self.last.started: return False
        if len(self.seen) > 2048: self.seen.clear()
        self.seen.add(key)
        self.last = Cast(slot, speaker, match['target'].strip(), event_time)
        self.casts[slot] = self.last
        self.observed.add(slot)
        return True

    def snapshot(self, now):
        c = self.config
        if not c['enabled']: return dict(state='DISABLED', casts=[], next='', due=0, last=None)
        if not self.last or now - self.last.started >= c['idle_seconds']:
            return dict(state='WAITING', casts=[], next='', due=0, last=None)
        roster = c['roster']
        next_slot = roster[(roster.index(self.last.slot) + 1) % len(roster)] if roster else ''
        due = self.last.started + c['interval_seconds'] - now
        active = []
        for cast in sorted(self.casts.values(), key=lambda x: x.started, reverse=True):
            remaining = cast.started + c['cast_seconds'] - now
            if remaining > 0:
                active.append(dict(slot=cast.slot, speaker=cast.speaker, target=cast.target,
                                   remaining=remaining, fraction=max(0, min(1, remaining / c['cast_seconds']))))
        return dict(state='LATE' if roster and due < -.5 else 'ACTIVE', casts=active,
                    next=next_slot, due=due, last=dataclasses.asdict(self.last))
