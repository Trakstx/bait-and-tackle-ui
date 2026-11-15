import sys,unittest,datetime
from pathlib import Path
sys.path.insert(0,str(Path('outputs/Bait-and-Tackle-Package/payload/BFT_HUD').resolve()))
from klandicar import Encounter,validate
from encounter_strip import geometry
class Tests(unittest.TestCase):
 def engage(self):
  e=Encounter();e.consume('Klandicar hits YOU for 500 points of damage.',100,'westwastes');return e
 def test_generic_fear_does_not_identify_dragon(self):
  e=Encounter();e.consume('You flee in terror.',100,'westwastes');self.assertFalse(e.snapshot(100)['active'])
 def test_chat_mentions_do_not_arm_or_anchor(self):
  e=Encounter();e.consume("Cleric says, 'Klandicar hits YOU for 500 points of damage.'",100,'westwastes');self.assertFalse(e.snapshot(100)['active']);e.arm(100);e.consume("You say, 'You resist the Dragon Roar spell!'",101);self.assertIsNone(e.snapshot(101)['spells'][0]['observed_at'])
 def test_da_warning_at_configured_lead(self):
  e=self.engage();e.consume('You resist the Dragon Roar spell!',101,'westwastes');self.assertFalse(e.snapshot(133.9)['da_warning']);self.assertTrue(e.snapshot(134)['da_warning']);self.assertIn('ESTIMATED',e.snapshot(134)['message']);self.assertFalse(e.snapshot(137)['da_warning'])
 def test_no_assumed_cycles_when_immune_or_missing(self):
  e=self.engage();e.consume('You resist the Dragon Roar spell!',101,'westwastes');self.assertEqual(e.snapshot(146)['spells'][0]['status'],'unknown');self.assertFalse(e.snapshot(170)['da_warning'])
 def test_silver_breath_does_not_start_da_warning(self):
  e=self.engage();e.consume('You feel your skin freeze.',101,'westwastes');s=e.snapshot(110);self.assertFalse(s['da_warning']);self.assertIsNone(s['spells'][0]['observed_at']);self.assertEqual(s['spells'][1]['remaining'],3)
 def test_duplicates_do_not_shift_anchor(self):
  e=self.engage();e.consume('You resist the Dragon Roar spell!',101,'westwastes');e.consume('You flee in terror.',102,'westwastes');self.assertEqual(e.snapshot(102)['spells'][0]['observed_at'],101)
 def test_character_zone_death_clear(self):
  for event,zone in [('LOADING, PLEASE WAIT...',None),('You have been slain by Klandicar!',None),('Klandicar has been slain by Tank!',None),('something','kael')]:
   e=self.engage();e.consume(event,102,zone);self.assertFalse(e.snapshot(102)['active'])
  e=self.engage();e.set_character('Other');self.assertFalse(e.snapshot(102)['active'])
 def test_stale_lines_rejected_and_timestamp_used(self):
  e=self.engage();now=datetime.datetime(2026,11,14,12).timestamp();e.consume('[Sat Nov 14 11:59:00 2026] You resist the Dragon Roar spell!',now,'westwastes');self.assertIsNone(e.snapshot(now)['spells'][0]['observed_at'])
  e.arm(now);e.consume('[Sat Nov 14 11:59:58 2026] You resist the Dragon Roar spell!',now,'westwastes');self.assertEqual(e.snapshot(now)['spells'][0]['remaining'],34)
 def test_enrage_and_rampage(self):
  e=self.engage();e.consume('Klandicar has become ENRAGED.',101,'westwastes');self.assertIn('STOP FRONTAL',e.snapshot(101)['message']);e.consume('Klandicar is no longer enraged.',102,'westwastes');e.consume('Klandicar goes on a RAMPAGE!',103,'westwastes');self.assertEqual(e.snapshot(103)['severity'],'warn')
 def test_explicit_cast_arms_but_does_not_identify_ae(self):
  e=Encounter();e.consume('Klandicar begins to cast a spell.',100,'westwastes');self.assertTrue(e.snapshot(100)['active']);self.assertEqual(e.snapshot(100)['spells'][0]['status'],'unknown')
 def test_disabling_and_bad_lead(self):
  e=self.engage();e.configure({'enabled':False});self.assertFalse(e.snapshot(101)['active'])
  for v in [0,11,float('nan')]:
   with self.assertRaises(ValueError):validate({'da_lead':v})
 def test_anchor_and_small_screen(self):
  self.assertEqual(geometry((1,40,20,1680,1050),(8,4)),(48,70,1664,62));x,y,w,h=geometry((1,0,0,300,100),(500,500));self.assertEqual((x,y,w,h),(16,38,284,62))
if __name__=='__main__':unittest.main()
