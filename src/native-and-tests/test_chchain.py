import sys
from pathlib import Path
import tempfile
import unittest
module_dir = Path('outputs/Bait-and-Tackle-Package/payload/BFT_HUD').resolve()
if not module_dir.is_dir(): module_dir = Path(__file__).resolve().parents[1]/'payload/BFT_HUD'
if not module_dir.is_dir(): module_dir = Path(__file__).resolve().parents[1]/'HUD'
sys.path.insert(0, str(module_dir))
from chchain import Chain, validate, save_config, normalize_slot

class ChainTests(unittest.TestCase):
    def test_native_chat_and_live_countdown(self):
        c = Chain({'roster':['001','002','003']})
        self.assertTrue(c.consume("Alice shouts, '001 CH -- BigTank'", 100))
        s = c.snapshot(103)
        self.assertEqual(s['next'], '002'); self.assertEqual(s['casts'][0]['remaining'],7)
        self.assertEqual(s['casts'][0]['fraction'],.7)
        self.assertEqual(c.snapshot(104)['state'],'LATE')
    def test_idle_reset(self):
        c=Chain();c.consume("Alice shouts, '001 CH -- Tank'",100)
        self.assertEqual(c.snapshot(131)['state'],'WAITING')
    def test_filter_channel_and_tag(self):
        c=Chain({'channel':'guild','template':'GG {slot} CH -- {target}'})
        self.assertFalse(c.consume("Alice shouts, 'GG 001 CH -- Tank'",100))
        self.assertFalse(c.consume("Alice tells the guild, 'CA 001 CH -- Tank'",100))
        self.assertTrue(c.consume("Alice tells the guild, 'GG 001 CH -- Tank'",100))
    def test_reordered_template_literal_punctuation(self):
        c=Chain({'template':'CH [{target}] next:{slot}'})
        self.assertTrue(c.consume("Alice shouts, 'CH [Tank] next:AAA'",100))
        self.assertEqual(c.last.slot,'AAA')
    def test_self_and_normalization(self):
        c=Chain({'template':'{slot} CH {target}'})
        self.assertTrue(c.consume("You say, '1 CH Tank'",100,'Mycleric'))
        self.assertEqual(c.last.speaker,'Mycleric');self.assertEqual(c.last.slot,'001')
    def test_no_roster_does_not_invent_next(self):
        c=Chain();c.consume("Alice shouts, '001 CH -- Tank'",100)
        self.assertEqual(c.snapshot(101)['next'],'')
    def test_duplicate_and_out_of_order(self):
        c=Chain();line="Alice shouts, '001 CH -- Tank'"
        self.assertTrue(c.consume(line,100));self.assertFalse(c.consume(line,100))
        self.assertFalse(c.consume("Bob shouts, '002 CH -- Tank'",99))
    def test_unrelated_text_and_invalid_slots(self):
        c=Chain()
        for line in ["Alice shouts, 'please CH -- Tank'", "Alice shouts, 'ABC CH -- Tank'",'You begin casting Complete Heal.',"Alice shouts, '001 CH -- Tank' extra"]:
            self.assertFalse(c.consume(line,100))
    def test_future_and_stale_stamped_lines(self):
        c=Chain()
        self.assertFalse(c.consume("[Wed Nov 11 00:00:00 2026] Alice shouts, '001 CH -- Tank'",100))
        self.assertFalse(c.consume("[bad] Alice shouts, '001 CH -- Tank'",100))
    def test_validation(self):
        for conf in [{'template':'.*'}, {'template':'{slot} {target} {unknown}'}, {'roster':['1','001']}, {'cast_seconds':float('nan')}, {'interval_seconds':0}, {'cast_seconds':40,'idle_seconds':30}]:
            with self.assertRaises(ValueError):validate(conf)
    def test_roster_wrap_and_rejection(self):
        c=Chain({'roster':['001','002']})
        self.assertFalse(c.consume("Alice shouts, '003 CH -- Tank'",100))
        self.assertTrue(c.consume("Alice shouts, '002 CH -- Tank'",100))
        self.assertEqual(c.snapshot(101)['next'],'001')
    def test_config_atomic_roundtrip(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as td:
            p=Path(td)/'settings.json';cfg=save_config(p,{'roster':['1','2']})
            self.assertEqual(cfg['roster'],['001','002']);self.assertFalse(p.with_suffix('.tmp').exists())
    def test_disabled(self):
        c=Chain({'enabled':False});self.assertFalse(c.consume("Alice shouts, '001 CH -- Tank'",100))
        self.assertEqual(c.snapshot(101)['state'],'DISABLED')
    def test_repeated_chain_marker(self):
        c=Chain({'template':'{slot} CH <<{target}>> {slot}'})
        self.assertTrue(c.consume("Alice shouts, '111 CH <<Tank>> 111'",100))
        self.assertFalse(c.consume("Alice shouts, '222 CH <<Tank>> 333'",101))

if __name__=='__main__':unittest.main()
