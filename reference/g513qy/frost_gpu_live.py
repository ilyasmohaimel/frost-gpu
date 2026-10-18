#!/usr/bin/env python3
"""Coordinate registered render contexts and the opt-in KWin renderer API."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

import importlib.util as _power_import
_power_spec = _power_import.spec_from_file_location('frost_power', Path(__file__).with_name('frost_power.py'))
_power_module = _power_import.module_from_spec(_power_spec)
_power_spec.loader.exec_module(_power_module)
power_source = _power_module.power_source

RX='0000:03:00.0'
IGPU='0000:07:00.0'

class UncertainOperation(RuntimeError):
    """A mutation lost its result; automatic retries must stop."""

class Backend:
    def __init__(self, socket_path):
        self.socket_path=socket_path
        self.nodes={gpu:os.path.realpath('/dev/dri/by-path/pci-'+gpu+'-render') for gpu in (RX,IGPU)}

    def property(self,name):
        return self.dbus('org.freedesktop.DBus.Properties.Get','org.kde.kwin.Compositing',name)

    def dbus(self,*args):
        p=subprocess.run(['qdbus6','org.kde.KWin','/Compositor',*args],capture_output=True,text=True,timeout=12)
        if p.returncode: raise RuntimeError((p.stderr or p.stdout).strip())
        return p.stdout.strip()

    def primary(self):
        node=self.property('primaryGpu')
        for gpu,path in self.nodes.items():
            if node == path:return gpu
        raise RuntimeError('KWin returned an unknown primary renderer: '+node)

    def switch(self,target):
        try:
            answer=self.dbus('org.kde.kwin.Compositing.switchPrimaryGpu',self.nodes[target])
        except (subprocess.TimeoutExpired,RuntimeError) as error:
            raise UncertainOperation('KWin switch result unavailable: '+str(error)) from error
        if answer != 'true':return False,self.property('gpuSwitchError')
        return True,''

    def rpc(self,message):
        mutation=message['type']=='move'
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                # A move can include the daemon's bounded migration and two
                # origin restores. Never kill an app or cut power on timeout.
                connection.settimeout(370 if mutation else 5)
                connection.connect(self.socket_path)
                connection.sendall((json.dumps(message)+'\n').encode())
                rows=[]
                with connection.makefile('rb') as stream:
                    while True:
                        line=stream.readline(8193)
                        if not line or len(line)>8192:raise RuntimeError('Incomplete daemon reply')
                        row=json.loads(line)
                        rows.append(row)
                        if row.get('type') in ('end','result'):return rows
        except (OSError,ValueError,RuntimeError) as error:
            if mutation:raise UncertainOperation('Application migration result unavailable: '+str(error)) from error
            raise RuntimeError('Migration daemon unavailable: '+str(error)) from error

    def status(self):
        rows=self.rpc({'type':'status','tracked_only':True})
        if not any(r.get('type')=='capabilities' and r.get('render_only_version')==1 for r in rows):
            raise RuntimeError('Render daemon protocol mismatch; restart the session daemon')
        return rows

    def move(self,source,target):
        rows=self.rpc({'type':'move','gpu':source,'to':target})
        result=rows[-1]
        if result.get('type')!='result':raise UncertainOperation('Missing migration result')
        if not isinstance(result.get('uncertain'),bool):raise UncertainOperation('Daemon omitted recovery status')
        if result.get('uncertain') is True:raise UncertainOperation(result.get('message','Application rollback failed'))
        return result.get('ok') is True,result.get('message','') or result.get('error','')

class Reconciler:
    def __init__(self,backend):
        self.backend=backend
        self.halted=None

    def reconcile(self,ac,power=None):
        target,source=(RX,IGPU) if ac else (IGPU,RX)
        report={'ac':ac,'target':target,'state':'checking','scope':'registered render contexts and KWin','allApplicationsCovered':False}
        if self.halted:return {**report,'state':'halted','error':self.halted}
        try:
            primary=self.backend.primary()
            report['compositor']=primary
            rows=self.backend.status()
            managed={r.get('gpu') for r in rows if r.get('type')=='gpu'}
            if not {RX,IGPU} <= managed:raise RuntimeError('Both GPUs must be managed by the render daemon')
            contexts=[r for r in rows if r.get('type')=='client' and r.get('registered') is True and r.get('gpu')==source and (r.get('devices',0)>0 or r.get('parked',0)>0)]
            report['sourceContexts']=sum(r.get('devices',0) for r in contexts)
            blockers=[r for r in contexts if r.get('class')!='migratable' or r.get('parked',0)>0 or r.get('render_only_version')!=1]
            if blockers:return {**report,'state':'blocked','error':'A registered context cannot migrate','blockers':blockers}
            if contexts:
                moved,error=self.backend.move(source,target)
                if not moved:return {**report,'state':'blocked','error':error}
            if power is not None and power()!=ac:
                return {**report,'state':'power-changed','error':'Power source changed during application migration'}
            if primary!=target:
                switched,error=self.backend.switch(target)
                if not switched:return {**report,'state':'blocked','error':error,'appsOnTarget':True}
            report['compositor']=self.backend.primary()
            if report['compositor']!=target:raise UncertainOperation('KWin renderer verification failed')
            remaining=[r for r in self.backend.status() if r.get('type')=='client' and r.get('registered') is True and r.get('gpu')==source and (r.get('devices',0)>0 or r.get('parked',0)>0)]
            if remaining:return {**report,'state':'retry','error':'A new source context appeared during switching'}
            return {**report,'state':'steady','sourceContexts':0}
        except UncertainOperation as error:
            self.halted=str(error)
            return {**report,'state':'halted','error':self.halted}
        except (RuntimeError,OSError,subprocess.TimeoutExpired) as error:
            return {**report,'state':'unavailable','error':str(error)}

def ac_online():
    # Compatibility name: true means barrel-performance power, not any charger.
    return power_source()['useRX']


def power_state():
    gpu=Path('/sys/bus/pci/devices')/RX
    result={}
    for key,path in [('policy','power/control'),('runtime','power/runtime_status'),('pci','power_state')]:
        try:result[key]=(gpu/path).read_text().strip()
        except OSError:result[key]='unavailable'
    result['d3cold']=result.get('runtime')=='suspended' and result.get('pci')=='D3cold'
    return result

def session_stop_reason(env):
    if env.get('FROST_GPU_LIVE_SESSION')!='1':return None
    config=Path(env.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
    runtime=Path(env.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))
    if (config/'frost-gpu-live/disabled').exists() or (runtime/'frost-gpu-live/fallback').exists():
        return 'Session switching disabled or compositor fell back to stock; restart a Frost session to resume'
    return None

def save(path,data):
    fd,name=tempfile.mkstemp(prefix='.status-',dir=path.parent)
    with os.fdopen(fd,'w') as stream:json.dump(data,stream,indent=2)
    Path(name).replace(path)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['watch','once','status'])
    parser.add_argument('--target',choices=['rx','igpu'],help='Explicit target for one manual/private test')
    parser.add_argument('--socket',default=os.environ.get('ZSS_SOCKET'))
    parser.add_argument('--test-power-file',type=Path,help='Private DRM test only: simulate power-source events')
    parser.add_argument('--state-dir',type=Path,default=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))/'frost-gpu-live')
    args=parser.parse_args()
    if args.action=='watch' and args.target:parser.error('--target is only valid with once')
    args.state_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
    if args.state_dir.stat().st_uid!=os.getuid():parser.error('State directory belongs to another user')
    statefile=args.state_dir/'status.json'
    if args.action=='status':
        print(statefile.read_text() if statefile.exists() else json.dumps({'state':'not-running'}));return 0
    if not args.socket:parser.error('Set ZSS_SOCKET or --socket to the session render daemon')
    read_power=ac_online
    if args.test_power_file:
        runtime=Path(os.environ.get('XDG_RUNTIME_DIR',''))
        if os.environ.get('FROST_GPU_LIVE_TEST')!='1' or not runtime.name.startswith('frost-drm-') or Path(args.socket).parent!=runtime:
            parser.error('Simulated power is restricted to the disposable DRM test')
        def read_power():
            value=args.test_power_file.read_text().strip()
            if value not in ('ac','battery'):raise RuntimeError('Invalid simulated power source')
            return value=='ac'
    with (args.state_dir/'controller.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:parser.error('A controller is already active for this session')
        controller=Reconciler(Backend(args.socket))
        candidate=read_power();since=time.monotonic();last_check=0;last_summary=None;interval=3
        while True:
            power=read_power()
            if power!=candidate:candidate=power;since=time.monotonic();last_check=0
            now=time.monotonic()
            if args.action=='once' or (now-since>=.75 and now-last_check>=interval):
                stop_reason=session_stop_reason(os.environ)
                if stop_reason:controller.halted=stop_reason
                selected=(args.target=='rx') if args.target else candidate
                result=controller.reconcile(selected,None if args.target else read_power)
                source=power_source()
                result.update(updatedAt=time.time(),rxPower=power_state(),manualTarget=bool(args.target),
                              powerSource=source['source'],externalPower=source['externalPower'],
                              performancePower=source['useRX'])
                save(statefile,result)
                summary=(result['state'],result['target'],result.get('error'))
                if summary!=last_summary:print(json.dumps(result),flush=True);last_summary=summary
                last_check=now
                interval=15 if result['state'] in ('blocked','unavailable','halted') else 3
                if args.action=='once':return 0 if result['state']=='steady' else 1
            time.sleep(.25)

if __name__=='__main__':raise SystemExit(main())
