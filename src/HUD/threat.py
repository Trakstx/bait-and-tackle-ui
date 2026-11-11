"""Original P99 personal threat estimator. No upstream implementation copied.
Model totals are estimates, not the server hate table. Unknown events mark partial.
"""
import csv
import io
import json
import re
import time
import os
from itemlookup import ItemResolver
from pathlib import Path
from combat import parse, STAMP, event_time

CAST = re.compile(r"^You begin casting (.+?)[.!]$")
RESIST = re.compile(r"^Your target resisted the (.+?)(?: spell)?[.!]$")
WEAPON_VERBS = {"slash":"1hs", "slashing":"1hs", "pierce":"1hp", "piercing":"1hp", "crush":"1hb", "crushing":"1hb", "punch":"h2h", "punching":"h2h", "hit":"hit"}


def read_inventory(path):
    """Only equipped slots; never confuse items inside bags with equipped weapons."""
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if not reader.fieldnames or not {"Location", "Name", "ID"}.issubset(reader.fieldnames):
        raise ValueError("Not an EverQuest inventory export")
    result = {}
    for row in reader:
        slot = row["Location"].strip().casefold()
        if slot not in ("primary", "secondary"): continue
        if slot in result: raise ValueError("Duplicate equipped " + slot)
        result[slot] = {"name":row["Name"].strip(), "id":int(row["ID"])}
    if len(result) != 2: raise ValueError("Export is missing equipped Primary/Secondary slots")
    return result


class ThreatMeter:
    def __init__(self, game, character, config=None):
        self.game, self.character = Path(game), character
        self.config = config or {}
        self.profile = self.config.get("characters", {}).get(character, {})
        self.resolved = {}
        self.resolver = ItemResolver(self.config.get('item_cache', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'BaitAndTackle' / 'item-cache.json'))) if self.config.get('automatic_lookup', True) else None
        try: self.bonuses = json.loads(Path(__file__).with_name('damage_bonus.json').read_text())['rows']
        except (OSError, ValueError, KeyError): self.bonuses = {}
        self.tables = {}
        self.target = ""
        self.equipment = {}
        self.gear_status = "EXPORT"
        self.last_check = -10.
        self.signature = None
        self.pending = None
        self.last_activity = None

    def refresh_inventory(self, now):
        if self.resolver:
            for hand, item in self.equipment.items(): self.resolved[hand] = self.resolver.resolve(item, now)
        if now - self.last_check < 2: return
        self.last_check = now
        path = self.game / (self.character + "-Inventory.txt")
        try:
            st = path.stat()
            signature = (st.st_mtime_ns, st.st_size)
            status = "STALE" if now - st.st_mtime > 86400 else "READY"
            equipment = read_inventory(path)
        except (OSError, ValueError, KeyError):
            self.gear_status = "EXPORT"
            return
        if self.signature is not None and signature != self.signature:
            # A swap cannot retrospectively fix earlier swing attribution.
            self.tables.clear(); self.target = ""; self.pending = None
        self.signature = signature
        self.equipment = equipment
        self.gear_status = status
        if self.resolver:
            for hand, item in equipment.items(): self.resolved[hand] = self.resolver.resolve(item, now)

    def _hands(self, verb):
        profiles = self.config.get("weapons", {})
        result = []
        for hand, item in self.equipment.items():
            weapon = profiles.get(str(item["id"]), profiles.get(item["name"], self.resolved.get(hand) or {}))
            kind = weapon.get("type")
            if kind in ("instrument", "shield", "none", "nonweapon"): continue
            if kind not in ("1hs","1hp","1hb","2hs","2hp","2hb","h2h"): continue
            attack_type = WEAPON_VERBS.get(verb.lower())
            matches = attack_type == kind or (kind.startswith("2") and attack_type == "1"+kind[1:])
            # Generic 'hit' doesn't identify a weapon skill: no arbitrary hand assignment.
            if not matches: continue
            cost = weapon.get(hand + "_hate_per_swing")
            if cost is None:
                level = self.profile.get('level')
                klass = self.profile.get('class', '').upper()
                bonus = None
                if isinstance(level, int) and 1 <= level <= 60 and klass in ('WAR','PAL','RNG','SHD','MNK','BRD','ROG'):
                    if hand == 'secondary' or level < 28: bonus = 0
                    else:
                        row = '1h' if kind.startswith('1') or kind=='h2h' else str(weapon.get('delay'))
                        bonus = self.bonuses.get(row, {}).get(str(level))
                if bonus is not None and isinstance(weapon.get('damage'), (int,float)):
                    cost = weapon['damage'] + bonus
            if isinstance(cost, (int,float)) and cost >= 0:
                result.append(float(cost))
        return result

    def _table(self, target, now):
        key = target.casefold()
        self.target = key
        return self.tables.setdefault(key, {"name":target,"low":0.,"high":0.,"start":now,"last":now,"partial":not self.profile.get("complete_model", False),"swings":0,"spells":0,"pending_swings":[]})

    def consume(self, line):
        stamp = STAMP.match(line.rstrip())
        if not stamp: return
        try: now = event_time(stamp[1])
        except ValueError: return
        text = stamp[2]
        self.refresh_inventory(time.time())
        event = parse(line)
        if event and event.kind in ("death","zone"):
            self.tables.clear(); self.target=""; self.pending=None; return
        if event and event.kind == "kill":
            self.tables.pop(event.target.casefold(),None)
            if self.target == event.target.casefold(): self.target=""
            return
        cast = CAST.fullmatch(text)
        if cast:
            # Cast lines don't establish target or success. Used only for attribution.
            self.pending = (cast[1],now)
            for row in self.tables.values(): row["partial"] = True
            return
        if text.startswith(("Your spell is interrupted", "Your spell fizzles")):
            self.pending=None; return
        if not event or event.kind not in ("melee","miss","spell"):
            # Songs/procs with no attributable target are intentionally not allocated
            # to the next melee target, unlike some older parsers.
            return
        row = self._table(event.target,now); row["last"]=now; self.last_activity=now
        if event.kind in ("melee","miss"):
            values = self._hands(event.ability)
            row["swings"] += 1
            if values and self.gear_status == "READY":
                row["low"] += min(values); row["high"] += max(values)
            else:
                row["partial"] = True
                if len(row["pending_swings"])<1000: row["pending_swings"].append(event.ability)
        else:
            rule = self.config.get("spells", {}).get(event.ability, {})
            # Per-spell calibration is explicit: don't treat every song/debuff as DD.
            fixed, scale = rule.get("fixed_hate"), rule.get("damage_multiplier")
            if fixed is None and scale is None: row["partial"] = True
            else:
                value = float(fixed or 0) + event.amount * float(scale or 0)
                row["low"] += value; row["high"] += value; row["spells"] += 1

    def snapshot(self, now):
        self.refresh_inventory(now)
        row = self.tables.get(self.target)
        for target in self.tables.values():
            pending=[]
            for verb in target['pending_swings']:
                values=self._hands(verb)
                if values and self.gear_status=='READY':
                    target['low']+=min(values);target['high']+=max(values)
                else: pending.append(verb)
            target['pending_swings']=pending
        # State 0: export/profile missing, 1: partial, 2: modeled total, 3: stale gear.
        if self.gear_status != "READY": return [0.,0.,0.,3. if self.gear_status=="STALE" else 0.]
        if not row: return [0.,0.,0.,4.]
        if now-row["last"] > 120: return [0.,0.,0.,0.]
        if row["partial"] and row["high"] == 0: return [0.,0.,0.,4.]
        elapsed=max(1.,now-row["start"]+1.)
        return [row["low"],row["high"],row["high"]/elapsed,1. if row["partial"] else 2.]

    def write_status(self, path, now):
        row = self.tables.get(self.target)
        payload = {"character":self.character,"updated":now,"gear_status":self.gear_status,
                   "equipment":self.equipment,"resolved_items":self.resolved,"lookup_errors":self.resolver.errors if self.resolver else {},"target":row,"estimate":self.snapshot(now),
                   "notes":"Personal estimate only. No tank comparison or server threat percentage. Unsupported abilities, procs, songs and other unobserved hate are not counted."}
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix(".tmp");temp.write_text(json.dumps(payload,indent=2));temp.replace(path)

    def close(self):
        if self.resolver: self.resolver.close()
