#!/usr/bin/env python3
"""Inspect or disable the optional Frost GPU session without logging out."""
import argparse
import json
import os
from pathlib import Path
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['status','disable','enable','native'],default='status',nargs='?')
p.add_argument('command',nargs=argparse.REMAINDER)
a=p.parse_args()
config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'frost-gpu-live'
state=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))/'frost-gpu-live'
if a.action=='native':
 import importlib.util
 spec=importlib.util.spec_from_file_location('frost_session',Path(__file__).with_name('frost_session.py'))
 session=importlib.util.module_from_spec(spec);spec.loader.exec_module(session)
 args=a.command[1:]if a.command[:1]==['--']else a.command
 if not args:p.error('native requires a command')
 os.execvpe(args[0],args,session.clean(dict(os.environ)))
elif a.action=='disable':
 config.mkdir(mode=0o700,parents=True,exist_ok=True);(config/'disabled').touch(mode=0o600)
 print('Automatic switching will halt after its current operation. Future launches use their original route; existing apps remain open. The next login uses stock Plasma.')
elif a.action=='enable':
 (config/'disabled').unlink(missing_ok=True)
 print('Frost GPU switching is available at login. Log into Plasma (Frost GPU switching) to activate or resume it.')
else:
 result={'session':'stock or inactive','optionalSessionInstalled':Path('/usr/share/wayland-sessions/frost-gpu-live.desktop').exists(),'disabled':(config/'disabled').exists(),'allApplicationsSupported':False}
 check=subprocess.run(['/usr/local/libexec/frost-gpu-session','check'],capture_output=True,text=True)
 try:
  result['installation']=json.loads(check.stdout)
  if result['installation'].get('optedIn'):result['session']='Frost'
 except ValueError:result['installation']={'compatible':False,'error':'Session helper unavailable'}
 try:result['controller']=json.loads((state/'status.json').read_text())
 except (OSError,ValueError):result['controller']={'state':'not-running'}
 for field in ('runtime_status','control'):
  try:result['rx_'+field]=Path('/sys/bus/pci/devices/0000:03:00.0/power',field).read_text().strip()
  except OSError:result['rx_'+field]='unknown'
 print(json.dumps(result,indent=2))
