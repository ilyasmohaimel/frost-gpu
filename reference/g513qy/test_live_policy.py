#!/usr/bin/env python3
"""Controller failure semantics with no display, daemon or GPU operations."""
import copy
import unittest
import tempfile
from pathlib import Path
from frost_gpu_live import RX,IGPU,Reconciler,UncertainOperation,session_stop_reason

class FakeBackend:
    def __init__(self,primary=RX,device=RX,migratable=True):
        self.renderer=primary;self.device=device;self.migratable=migratable;self.parked=0;self.calls=[];self.reject=False;self.uncertain=False
    def primary(self):return self.renderer
    def status(self):
        return [{'type':'gpu','gpu':g} for g in (RX,IGPU)]+[{'type':'client','registered':True,'render_only_version':1,'gpu':self.device,'devices':1,'parked':self.parked,'class':'migratable' if self.migratable else 'non-migratable','pid':100}]
    def move(self,source,target):
        self.calls.append(('move',source,target))
        self.device=target
        if self.uncertain:raise UncertainOperation('lost migration reply')
        return True,''
    def switch(self,target):
        self.calls.append(('switch',target))
        if self.reject:return False,'active screencast source'
        self.renderer=target;return True,''

class ControllerTests(unittest.TestCase):
    def test_disable_and_fallback_stop_live_session(self):
        with tempfile.TemporaryDirectory() as root:
            env={'FROST_GPU_LIVE_SESSION':'1','XDG_CONFIG_HOME':root,'XDG_RUNTIME_DIR':root}
            self.assertIsNone(session_stop_reason(env))
            directory=Path(root)/'frost-gpu-live';directory.mkdir()
            for filename in ('disabled','fallback'):
                file=directory/filename;file.touch()
                self.assertIsNotNone(session_stop_reason(env))
                self.assertIsNone(session_stop_reason({**env,'FROST_GPU_LIVE_SESSION':'0'}))
                file.unlink()

    def test_battery_moves_contexts_before_compositor(self):
        b=FakeBackend();r=Reconciler(b).reconcile(False)
        self.assertEqual(r['state'],'steady');self.assertEqual(b.calls,[('move',RX,IGPU),('switch',IGPU)])
    def test_ac_moves_apps_that_started_on_igpu(self):
        b=FakeBackend(primary=IGPU,device=IGPU);r=Reconciler(b).reconcile(True)
        self.assertEqual(r['state'],'steady');self.assertEqual(b.calls,[('move',IGPU,RX),('switch',RX)])
    def test_unsupported_context_never_touches_compositor(self):
        b=FakeBackend(migratable=False);r=Reconciler(b).reconcile(False)
        self.assertEqual(r['state'],'blocked');self.assertEqual(b.calls,[])
    def test_parked_context_is_a_blocker(self):
        b=FakeBackend();b.parked=1;r=Reconciler(b).reconcile(False)
        self.assertEqual(r['state'],'blocked');self.assertEqual(b.calls,[])
    def test_capture_refusal_preserves_apps_and_retries_renderer(self):
        b=FakeBackend();b.reject=True;c=Reconciler(b)
        self.assertEqual(c.reconcile(False)['state'],'blocked');self.assertEqual(b.device,IGPU);self.assertEqual(b.renderer,RX)
        b.reject=False;self.assertEqual(c.reconcile(False)['state'],'steady')
        self.assertEqual(b.calls,[('move',RX,IGPU),('switch',IGPU),('switch',IGPU)])
    def test_power_reversal_skips_stale_renderer_switch(self):
        b=FakeBackend();c=Reconciler(b);r=c.reconcile(False,power=lambda:True)
        self.assertEqual(r['state'],'power-changed');self.assertEqual(b.renderer,RX)
        self.assertEqual(c.reconcile(True)['state'],'steady')
        self.assertEqual(b.calls,[('move',RX,IGPU),('move',IGPU,RX)])
    def test_uncertain_mutation_halts_all_automatic_retries(self):
        b=FakeBackend();b.uncertain=True;c=Reconciler(b)
        self.assertEqual(c.reconcile(False)['state'],'halted');before=copy.copy(b.calls)
        self.assertEqual(c.reconcile(True)['state'],'halted');self.assertEqual(b.calls,before)
    def test_new_context_is_moved_even_when_compositor_already_matches(self):
        b=FakeBackend(primary=IGPU,device=RX);r=Reconciler(b).reconcile(False)
        self.assertEqual(r['state'],'steady');self.assertEqual(b.calls,[('move',RX,IGPU)])
    def test_missing_managed_gpu_never_moves_anything(self):
        b=FakeBackend();original=b.status;b.status=lambda:[r for r in original() if r.get('gpu')!=IGPU]
        self.assertEqual(Reconciler(b).reconcile(False)['state'],'unavailable');self.assertEqual(b.calls,[])

if __name__=='__main__':unittest.main(verbosity=2)
