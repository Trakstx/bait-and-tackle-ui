"""Offline Windows SAPI speech in one bounded, asynchronous helper process."""
import base64,json,os,subprocess,threading,time
SCRIPT=r'''
$ErrorActionPreference='Stop'
[Console]::InputEncoding=New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
function Emit($value){[Console]::Out.WriteLine(($value|ConvertTo-Json -Compress -Depth 4));[Console]::Out.Flush()}
try {
Add-Type -TypeDefinition @"
using System;
using System.Collections.Concurrent;
using System.Threading.Tasks;
public static class BftSpeechInput {
 public static ConcurrentQueue<string> Lines = new ConcurrentQueue<string>();
 public static volatile bool Finished;
 public static void Start(){Task.Run(()=>{try{string s;while((s=Console.ReadLine())!=null){if(Lines.Count<16)Lines.Enqueue(s);}}finally{Finished=true;}});}
}
"@
$voice=New-Object -ComObject SAPI.SpVoice
$tokens=$voice.GetVoices()
if($tokens.Count -eq 0){throw 'No Windows speech voices are available.'}
$defaultVoice=$tokens.Item(0);$voice.Voice=$defaultVoice
$names=@();for($i=0;$i -lt $tokens.Count;$i++){$names+=($tokens.Item($i).GetDescription())}
Emit @{event='ready';voices=$names;default_voice=$defaultVoice.GetDescription()}
[BftSpeechInput]::Start();$pending=New-Object 'System.Collections.Generic.List[object]';$current=$null
while(-not [BftSpeechInput]::Finished){
 $line=$null
 while([BftSpeechInput]::Lines.TryDequeue([ref]$line)){
  $msg=$line|ConvertFrom-Json
  if($msg.kind -eq 'cancel'){[void]$voice.Speak('',3);$pending.Clear();$current=$null;continue}
  if($msg.kind -ne 'speak'){continue}
  if($msg.priority -eq 2 -and $null -ne $current -and $current.priority -lt 2){[void]$voice.Speak('',3);$current=$null}
  $pending.Add($msg)
  if($pending.Count -gt 4){$pending.RemoveAt(0)}
 }
 if($null -ne $current -and $voice.Status.RunningState -ne 2){Emit @{event='spoken';text=$current.text};$current=$null}
 if($null -eq $current -and $pending.Count -gt 0){
  $next=@($pending|Sort-Object @{Expression='priority';Descending=$true},@{Expression='at';Descending=$false})[0];[void]$pending.Remove($next)
  $now=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0
  if($now-$next.at -gt 5){continue}
  $voice.Volume=[int]$next.volume;$voice.Rate=[int]$next.rate;$voice.Voice=$defaultVoice
  if($next.voice){for($i=0;$i -lt $tokens.Count;$i++){if($tokens.Item($i).GetDescription() -eq $next.voice){$voice.Voice=$tokens.Item($i);break}}}
  [void]$voice.Speak([string]$next.text,17)
  $current=$next
 }
 Start-Sleep -Milliseconds 35
}
[void]$voice.Speak('',3)
} catch {Emit @{event='error';error=$_.Exception.Message}}
'''
class Speech:
 def __init__(self):
  self.lock=threading.RLock();self.process=None;self.state={'ready':False,'voices':[],'error':'','last_spoken':''};self.last={};self.enabled=False;self.retry_after=0
 def _read(self,process):
  try:
   for line in process.stdout:
    try:row=json.loads(line)
    except ValueError:continue
    with self.lock:
     if row.get('event')=='ready':self.state.update(ready=True,voices=row.get('voices',[]),default_voice=row.get('default_voice',''),error='')
     elif row.get('event')=='spoken':self.state['last_spoken']=row.get('text','')
     elif row.get('event')=='error':self.state.update(ready=False,error=row.get('error','Speech failed.'))
  finally:
   with self.lock:
    if self.process is process:self.state['ready']=False
 def start(self):
  if self.process and self.process.poll() is None:return
  if time.time()<self.retry_after:return
  self.retry_after=time.time()+30
  executable=os.path.join(os.environ.get('SystemRoot','C:/Windows'),'System32/WindowsPowerShell/v1.0/powershell.exe');command=base64.b64encode(SCRIPT.encode('utf-16le')).decode('ascii')
  try:
   self.process=subprocess.Popen([executable,'-NoLogo','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-EncodedCommand',command],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
   threading.Thread(target=self._read,args=(self.process,),daemon=True).start()
  except OSError as exc:self.state['error']=str(exc)
 def speak(self,text,config,severity='info'):
  text=' '.join(str(text).split())[:220]
  if not text:return
  with self.lock:
   now=time.time()
   if now-self.last.get(text,0)<1:return
   self.last={key:at for key,at in self.last.items() if now-at<30};self.last[text]=now;self.start()
   if not self.process:return
   try:self.process.stdin.write(json.dumps({'kind':'speak','text':text,'priority':2 if severity=='danger' else 1,'at':now,'volume':config.get('speech_volume',80),'rate':config.get('speech_rate',0),'style':'natural','voice':config.get('speech_voice','')})+'\n');self.process.stdin.flush()
   except (OSError,ValueError) as exc:self.state['error']=str(exc)
 def configure(self,config):
  enabled=bool(config.get('enabled') and config.get('sound_enabled') and config.get('audio_mode','speech')=='speech')
  if self.enabled and not enabled:self.cancel()
  self.enabled=enabled
 def cancel(self):
  with self.lock:
   if self.process and self.process.poll() is None:
    try:self.process.stdin.write('{"kind":"cancel"}\n');self.process.stdin.flush()
    except (OSError,ValueError):pass
 def snapshot(self):
  with self.lock:return dict(self.state)
 def close(self):
  with self.lock:
   process=self.process;self.process=None
   if process:
    try:process.stdin.close()
    except (OSError,ValueError):pass
    try:process.wait(timeout=2)
    except subprocess.TimeoutExpired:process.terminate()
