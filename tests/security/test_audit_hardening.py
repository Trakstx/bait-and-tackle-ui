import ctypes,hashlib,json,os,socket,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src/HUD'))
from local_paths import local_folder
from file_transaction import FileTransaction
from secure_http import BoundedHTTPServer
import settings_store
from settings_hub import Hub
import urllib.request,urllib.error

class Paths(unittest.TestCase):
 def test_share_variants_rejected_before_filesystem_access(self):
  for path in ['\\\\server\\share','//server/share','\\/server/share','/\\server/share','\\\\?\\C:\\folder','\\\\.\\C:','C:relative','C:\\folder:stream','C:\\NUL','C:\\bad\npath']:
   with self.subTest(path=path),patch.object(Path,'lstat') as stat:
    with self.assertRaises(ValueError):local_folder(path)
    stat.assert_not_called()
 def test_local_path_normalizes_separators(self):self.assertEqual(str(local_folder('C:/recordings',inspect=False)),'C:\\recordings')
 def test_mapped_drive_rejected_before_directory_probe(self):
  from unittest.mock import MagicMock
  api=MagicMock();api.GetDriveTypeW.return_value=4
  with patch('ctypes.WinDLL',return_value=api),patch.object(Path,'lstat') as probe:
   with self.assertRaises(ValueError):local_folder('Z:\\recordings')
   probe.assert_not_called()

class Transactions(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp');self.root=Path(self.temp.name);self.game=self.root/'game';self.game.mkdir();self.backups=self.root/'recovery'
  self.a=self.game/'a';self.b=self.game/'b';self.a.write_bytes(b'old-a');self.b.write_bytes(b'old-b')
 def tearDown(self):self.temp.cleanup()
 def transaction(self):
  tx=FileTransaction(self.backups,[self.game]);tx.add(self.a,b'new-a');tx.add(self.b,b'new-b');return tx
 def test_commit_and_verified_restore(self):
  tx=self.transaction();new=self.game/'new';tx.add(new,b'created');tx.commit();self.assertEqual(self.a.read_bytes(),b'new-a')
  FileTransaction.restore(tx.directory,[self.game]);self.assertEqual(self.a.read_bytes(),b'old-a');self.assertEqual(self.b.read_bytes(),b'old-b');self.assertFalse(new.exists())
 def test_mid_commit_failure_rolls_back_all_targets(self):
  tx=self.transaction();replace=os.replace
  def fail(source,dest):
   if Path(dest)==self.b and Path(source).name.startswith('.bft-stage-'):raise OSError('injected second-file failure')
   return replace(source,dest)
  with patch('os.replace',side_effect=fail):
   with self.assertRaises(OSError):tx.commit()
  self.assertEqual(self.a.read_bytes(),b'old-a');self.assertEqual(self.b.read_bytes(),b'old-b')
 def test_interrupted_apply_recovered_on_next_run(self):
  tx=self.transaction();tx.commit();p=tx.directory/'journal.json';j=json.loads(p.read_text());j['state']='applying';p.write_text(json.dumps(j))
  FileTransaction.recover_pending(self.backups,[self.game]);self.assertEqual(self.a.read_bytes(),b'old-a')
 def test_conflict_and_corrupt_backup_refuse_restore(self):
  tx=self.transaction();tx.commit();self.a.write_bytes(b'personal-edit')
  with self.assertRaises(ValueError):FileTransaction.restore(tx.directory,[self.game])
  self.assertEqual(self.a.read_bytes(),b'personal-edit');self.assertEqual(self.b.read_bytes(),b'new-b')
 def test_no_external_root_or_internal_recovery_folder(self):
  tx=self.transaction()
  with self.assertRaises(ValueError):tx.add(self.root/'outside',b'bad')
  with self.assertRaises(ValueError):FileTransaction(self.game/'backups',[self.game])
 def test_delete_can_be_restored(self):
  tx=FileTransaction(self.backups,[self.game]);tx.add(self.a,None);tx.commit();self.assertFalse(self.a.exists());FileTransaction.restore(tx.directory,[self.game]);self.assertEqual(self.a.read_bytes(),b'old-a')

class ImportPreview(unittest.TestCase):
 def test_invalid_and_valid_preview_never_persist_or_enable_recording(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp') as temp,patch.object(settings_store,'RUNTIME',Path(temp)):
   path=Path(temp)/'settings.json';settings_store.save({},path);before=path.read_bytes();hub=Hub(path,game=Path(temp))
   try:
    def request(data):
     return urllib.request.urlopen(urllib.request.Request('http://'+hub.host+'/api/settings/preview',data=json.dumps(data).encode(),headers={'X-BFT-Token':hub.token,'Origin':'http://'+hub.host,'Content-Type':'application/json'}),timeout=3)
    with self.assertRaises(urllib.error.HTTPError):request({'dps':None,'recorder':{'enabled':True}})
    with request({'recorder':{'enabled':True},'network':{'item_lookups':True}}) as response:
     result=json.load(response);self.assertTrue(any(c['setting']=='recorder.enabled' for c in result['changes']))
    self.assertEqual(path.read_bytes(),before);self.assertFalse(hub.recorder.config['enabled'])
   finally:hub.close()

class Connections(unittest.TestCase):
 def test_incomplete_headers_expire_and_capacity_recovers(self):
  from http.server import BaseHTTPRequestHandler
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(b'ok')
  server=BoundedHTTPServer(('127.0.0.1',0),Handler,workers=2,deadline=.2);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();clients=[]
  try:
   for _ in range(2):
    c=socket.create_connection(server.server_address);c.sendall(b'GET / HTTP/1.1\r\nX-Incomplete: ');clients.append(c)
   time.sleep(.4)
   with urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port),timeout=2) as response:self.assertEqual(response.read(),b'ok')
  finally:
   for c in clients:c.close()
   server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
