"""Shared, validated settings for the local BFT control page and log readers."""
import json
import os
import math
from pathlib import Path
from chchain import validate as validate_chain
from buff_timers import validate as validate_buffs
from class_triggers import validate as validate_triggers
from event_timers import validate as validate_timers
from recorder import validate as validate_recorder
from klandicar import validate as validate_klandicar

RUNTIME = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'BaitAndTackle'
PATH = RUNTIME / 'settings.json'

def validate(data):
    dps = data.get('dps', {})
    idle = float(dps.get('idle_seconds', 15))
    if not 3 <= idle <= 300: raise ValueError('Fight timeout must be between 3 and 300 seconds.')
    pets = dps.get('pet_names_by_character', {})
    if not isinstance(pets, dict) or len(pets)>100: raise ValueError('Invalid pet settings.')
    clean = {}
    for character, names in pets.items():
        if not isinstance(character, str) or not character.strip() or len(character)>64: raise ValueError('Invalid character name.')
        if not isinstance(names, list) or len(names)>20 or any(not isinstance(x,str) or not x.strip() or len(x)>64 for x in names): raise ValueError('Pet names must be a list of nonempty names.')
        clean[character.strip()] = list(dict.fromkeys(x.strip() for x in names))
    misc=data.get('misc',{})
    anchor=float(misc.get('tick_anchor',0))
    if not math.isfinite(anchor) or not 0<=anchor<=4102444800:raise ValueError('Invalid tick synchronization time.')
    from network_policy import validate as validate_network
    return {'network':validate_network(data.get('network')),'klandicar':validate_klandicar(data.get('klandicar',{})),'recorder':validate_recorder(data.get('recorder',{})),'timers':validate_timers(data.get('timers',{})),'triggers':validate_triggers(data.get('triggers',{})),'misc':{'tick_enabled':bool(misc.get('tick_enabled',False)),'tick_anchor':anchor},'dps':{'enabled':bool(dps.get('enabled',True)),'idle_seconds':idle,'pet_names_by_character':clean},
            'ch':validate_chain(data.get('ch', {})), 'aggro':{'available':True,'enabled':bool(data.get('aggro',{}).get('enabled',True))},'buffs':validate_buffs(data.get('buffs',{}))}

def load(path=PATH):
    try: return validate(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError,ValueError,TypeError,AttributeError):
        try: ch=json.loads((Path(path).parent/'ch_chain.json').read_text(encoding='utf-8'))
        except (OSError,ValueError): ch={}
        try: return validate({'ch':ch})
        except (ValueError,TypeError,AttributeError): return validate({})

def save(data, path=PATH):
    data=validate(data);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    from file_transaction import write_atomic
    write_atomic(path,(json.dumps(data,indent=2)+'\n').encode('utf8'))
    return data

def apply_dps(meter, character, settings, legacy=None):
    prefs=settings['dps']; meter.visible=prefs['enabled']; meter.idle_seconds=prefs['idle_seconds']
    names=prefs['pet_names_by_character'].get(character)
    if names is None:
        legacy=legacy or {};names=legacy.get('pet_names_by_character',{}).get(character,legacy.get('pet_names',[]))
    meter.pet_names={name.casefold() for name in names}
