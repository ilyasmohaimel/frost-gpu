"""Migration rebuilds WSI buffers using the compositor's advertised main device."""
import unittest
import frost_gpu_live as live
from test_live_policy import FakeBackend

class AllocationBackend(FakeBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.buffer_devices=[]
    def move(self, source, target):
        self.buffer_devices.append(self.renderer)
        return super().move(source,target)

class BufferOrderTests(unittest.TestCase):
    def test_target_feedback_precedes_rebuilt_buffers_in_both_directions(self):
        for source,target,requested in ((live.RX,live.IGPU,False),(live.IGPU,live.RX,True)):
            with self.subTest(target=target):
                b=AllocationBackend(primary=source,device=source)
                self.assertEqual(live.Reconciler(b).reconcile(requested)['state'],'steady')
                self.assertEqual(b.buffer_devices,[target])

    def test_capture_refusal_does_not_rebuild_client_buffers(self):
        b=AllocationBackend();b.reject=True
        self.assertEqual(live.Reconciler(b).reconcile(False)['state'],'blocked')
        self.assertEqual(b.buffer_devices,[])

    def test_known_failed_move_restores_previous_renderer(self):
        b=AllocationBackend()
        def fail(source,target):
            b.calls.append(('move',source,target));return False,'rolled back'
        b.move=fail
        self.assertEqual(live.Reconciler(b).reconcile(False)['state'],'blocked')
        self.assertEqual(b.renderer,live.RX)
        self.assertEqual(b.calls,[('switch',live.IGPU),('move',live.RX,live.IGPU),('switch',live.RX)])

    def test_failed_renderer_rollback_halts_further_attempts(self):
        b=AllocationBackend()
        def fail(source,target):
            b.reject=True;return False,'app move rolled back'
        b.move=fail;c=live.Reconciler(b)
        self.assertEqual(c.reconcile(False)['state'],'halted')
        calls=list(b.calls)
        self.assertEqual(c.reconcile(True)['state'],'halted')
        self.assertEqual(b.calls,calls)

if __name__=='__main__':unittest.main(verbosity=2)
