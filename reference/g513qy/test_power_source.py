"""Test the actual observed ADP0/UCSI overlap, not just separate power inputs."""
import tempfile,unittest
from pathlib import Path
from frost_power import power_source
class Source(unittest.TestCase):
 def detect(self,mains='0',usb='0',usb_type='USB',extra=(),missing_usb=False):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp)
   supplies=[('ADP0','Mains',mains),('BAT0','Battery','1')]+([]if missing_usb else[('ucsi-source-psy-USBC000:001',usb_type,usb)])+list(extra)
   for name,kind,online in supplies:
    p=root/name;p.mkdir();(p/'type').write_text(kind);(p/'online').write_text(online)
   return power_source(root)
 def test_battery(self):self.assertEqual(self.detect()['source'],'battery')
 def test_barrel_only(self):self.assertTrue(self.detect(mains='1')['useRX'])
 def test_observed_usb_pd_also_sets_aggregate_mains(self):
  d=self.detect(mains='1',usb='1');self.assertEqual(d['source'],'usb-c');self.assertTrue(d['externalPower']);self.assertFalse(d['useRX'])
 def test_usb_without_aggregate_mains(self):self.assertEqual(self.detect(usb='1')['source'],'usb-c')
 def test_both_inputs_conservatively_use_igpu(self):self.assertFalse(self.detect(mains='1',usb='1')['useRX'])
 def test_usb_pd_type_and_nonzero_online(self):self.assertFalse(self.detect(mains='1',usb='2',usb_type='USB_PD')['useRX'])
 def test_unknown_external_does_not_request_rx(self):self.assertFalse(self.detect(extra=[('unknown','Wireless','1')])['useRX'])
 def test_missing_usb_node_does_not_break_barrel(self):self.assertTrue(self.detect(mains='1',missing_usb=True)['useRX'])
 def test_unreadable_inventory_defaults_to_igpu(self):self.assertFalse(power_source('/no/such/power-supplies')['useRX'])
if __name__=='__main__':unittest.main()
