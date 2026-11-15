import sys,tempfile,unittest,json,time,os
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str((Path(__file__).resolve().parents[2]/'src/HUD')))
from layout_tools import LayoutService,geometry,merge_geometry,hotkey_sections,tick_snapshot
import settings_store
SRC='[Main]\r\nUISkin=BAIT_AND_FUCKING_TACLE\r\n[MainChat]\r\nXPos1680x1050=10\r\nYPos1680x1050=20\r\nWidth1680x1050=400\r\nHeight1680x1050=200\r\nChannelMap0=8\r\nAlpha=99\r\n[InventoryWindow]\r\nXPos1920x1080=100\r\nYPos1920x1080=300\r\n'
DST='; preserve comment\r\n[Main]\r\nUISkin=BAIT_AND_FUCKING_TACLE\r\n[MainChat]\r\nXPos1680x1050=1\r\nYPos1680x1050=2\r\nWidth1680x1050=3\r\nHeight1680x1050=4\r\nChannelMap0=7\r\nAlpha=255\r\nLocked=false\r\n[Other]\r\nKeep=untouched\r\n'
KEYS='[Friends]\nFriend0=FriendA\n[HotButtons]\nPage1Button1=E13\n[Socials]\nPage1Button1Name=Heal\nPage1Button1Line1=/cast 1\n[Abilities]\nAbility1=40\n[CombatSkills]\nCombatSkill1=20\n'
TARGET_KEYS='[Friends]\nFriend0=FriendB\n[Ignored]\nIgnored0=Other\n[HotButtons]\nPage1Button1=E99\n[Socials]\nPage1Button1Name=Old\nPage1Button2Name=Stale\n[Abilities]\nAbility1=1\n[InspectText]\nText=My text\n'
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parents[2]/'.test-tmp'));self.root=Path(self.temp.name).resolve();self.game=self.root/'game';self.game.mkdir();self.a=self.game/'UI_Healer_project1999.ini';self.b=self.game/'UI_Bard_P1999Green.ini';self.a.write_bytes(SRC.encode());self.b.write_bytes(DST.encode());(self.game/'Healer_project1999.ini').write_text(KEYS);(self.game/'Bard_P1999Green.ini').write_text(TARGET_KEYS);self.service=LayoutService(self.game,self.root/'runtime')
 def tearDown(self):self.temp.cleanup()
 def req(self,**extra):return dict(source_kind='character',source=self.a.name,targets=[self.b.name],template_name='',**extra)
 def test_queue_does_not_touch_live_files(self):
  before=self.b.read_bytes();value=self.service.queue(self.req());self.assertEqual(self.b.read_bytes(),before);self.assertEqual(len(self.service.snapshot()['pending']),1);self.assertEqual(value['targets'][0]['changed_values'],6)
 def test_only_geometry_preserving_all_other_settings_and_backups(self):
  before=self.b.read_bytes();r=self.service.queue(self.req());self.service.apply_pending();new=self.b.read_bytes().decode();self.assertEqual(geometry(new),geometry(SRC));self.assertIn('ChannelMap0=7\r\nAlpha=255\r\nLocked=false',new);self.assertIn('; preserve comment',new);self.assertIn('[Other]\r\nKeep=untouched',new);self.assertEqual((Path(self.service.read('results.json',[])[-1]['backup'])/'0').read_bytes(),before);self.assertEqual((self.game/'Bard_P1999Green.ini').read_text(),TARGET_KEYS)
 def test_copy_reads_final_saved_source(self):
  self.service.queue(self.req());self.a.write_bytes(SRC.replace('=10\r\n','=33\r\n').encode());self.service.apply_pending();self.assertEqual(geometry(self.b.read_text())['MainChat']['XPos1680x1050'],'33')
 def test_template_with_hotkeys_then_template_to_character(self):
  self.service.queue(dict(source_kind='character',source=self.a.name,targets=[],template_name='Cleric',include_hotkeys=True));self.service.apply_pending();snapshot=self.service.snapshot();self.assertTrue(snapshot['templates'][0]['has_hotkeys']);self.assertNotIn('hotkeys',snapshot['templates'][0]);self.assertNotIn('layout',snapshot['templates'][0]);key=snapshot['templates'][0]['id']
  self.a.write_bytes(SRC.replace('=10\r\n','=99\r\n').encode());self.service.queue(dict(source_kind='template',source=key,targets=[self.b.name],include_hotkeys=True));self.service.apply_pending();self.assertEqual(geometry(self.b.read_text())['MainChat']['XPos1680x1050'],'10');self.assertIn('Page1Button1Name=Heal',(self.game/'Bard_P1999Green.ini').read_text())
 def test_hotkeys_exact_replacement_keeps_friends_and_inspect(self):
  before=(self.game/'Bard_P1999Green.ini').read_bytes();queued=self.service.queue(self.req(include_hotkeys=True));self.service.apply_pending();new=(self.game/'Bard_P1999Green.ini').read_text();self.assertEqual({k:v.strip() for k,v in hotkey_sections(new).items()},{k:v.strip() for k,v in hotkey_sections(KEYS).items()});self.assertIn('Friend0=FriendB',new);self.assertIn('Ignored0=Other',new);self.assertIn('Text=My text',new);self.assertNotIn('Stale',new);self.assertEqual((Path(self.service.read('results.json',[])[-1]['backup'])/'1').read_bytes(),before)
 def test_template_positions_only_cannot_erase_hotkeys(self):
  self.service.queue(dict(source_kind='character',source=self.a.name,template_name='Bard'));self.service.apply_pending();key=self.service.snapshot()['templates'][0]['id']
  with self.assertRaises(ValueError):self.service.queue(dict(source_kind='template',source=key,targets=[self.b.name],include_hotkeys=True))
 def test_rejects_paths_and_bad_names(self):
  for data in [dict(source_kind='character',source='../file',targets=[self.b.name]),dict(source_kind='character',source=self.a.name,targets=['../file']),dict(source_kind='character',source=self.a.name,template_name='../escape')]:
   with self.assertRaises(ValueError):self.service.queue(data)
 def test_duplicate_template_and_cancel(self):
  a=dict(source_kind='character',source=self.a.name,template_name='Cleric');job=self.service.queue(a)
  with self.assertRaises(ValueError):self.service.queue(a)
  self.service.cancel(job['queued']['id']);self.assertFalse(self.service.snapshot()['pending']);self.assertFalse(self.service.apply_pending())
 def test_deleted_source_retains_failed_job_without_writing_target(self):
  before=self.b.read_bytes();self.service.queue(self.req());self.a.unlink();self.assertFalse(self.service.apply_pending());self.assertEqual(self.b.read_bytes(),before);self.assertFalse(self.service.snapshot()['results'][0]['ok']);self.assertEqual(len(self.service.snapshot()['pending']),1)
 def test_server_tick_math_and_settings(self):
  self.assertIsNone(tick_snapshot({'tick_anchor':0},20)['remaining']);self.assertEqual(tick_snapshot({'tick_anchor':100},102)['remaining'],4);self.assertEqual(tick_snapshot({'tick_anchor':100},106)['remaining'],6)
  self.assertFalse(settings_store.validate({})['misc']['tick_enabled'])
  for n in [float('nan'),float('inf'),-1]:
   with self.assertRaises(ValueError):settings_store.validate({'misc':{'tick_anchor':n}})
 def test_hotkey_write_failure_restores_geometry_too(self):
  before=self.b.read_bytes();keys=(self.game/'Bard_P1999Green.ini').read_bytes();self.service.queue(self.req(include_hotkeys=True));replace=os.replace
  def fail(source,target):
   if Path(target).name=='Bard_P1999Green.ini' and Path(source).name.startswith('.bft-stage-'):raise OSError('injected hotkey failure')
   return replace(source,target)
  with patch('os.replace',side_effect=fail):self.assertEqual(self.service.apply_pending(),[])
  self.assertEqual(self.b.read_bytes(),before);self.assertEqual((self.game/'Bard_P1999Green.ini').read_bytes(),keys)
  self.assertEqual(len(self.service.snapshot()['pending']),1)
if __name__=='__main__':unittest.main()

