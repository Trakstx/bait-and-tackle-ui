"""Optional data requests are opt-in. Explicit update/vendor-download actions are separate."""
def validate(data=None):
    data=data or {}
    if not isinstance(data,dict):raise ValueError('Invalid network preferences.')
    if any(not isinstance(value,bool) for value in data.values()):raise ValueError('Network choices must be true or false.')
    return {key:bool(data.get(key,False)) for key in ('shared_timers','item_lookups','artwork')}
def require(feature):
    import json,settings_store
    try:data=json.loads((settings_store.RUNTIME/'settings.json').read_text(encoding='utf8'))
    except (OSError,ValueError):data={}
    if not validate(data.get('network'))[feature]:raise ValueError('Online '+feature.replace('_',' ')+' is disabled. Enable it in Misc > Online features.')
