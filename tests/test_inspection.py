import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("inspect_system", Path(__file__).resolve().parents[1] / "tools/inspect_system.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class InspectionTests(unittest.TestCase):
    def row(self, name, kind="Mains", online="1"):
        return {"name": name, "type": kind, "online": online}

    def test_no_profile_does_not_assume_aggregate_mains_is_barrel(self):
        self.assertEqual(tool.classify([self.row("ADP0")], None)["target"], "igpu")

    def test_usb_overrides_aggregate_mains(self):
        rows = [self.row("ADP0"), self.row("ucsi-source-psy-USBC000:001", "USB")]
        self.assertEqual(tool.classify(rows, "ADP0")["source"], "usb-c")

    def test_custom_barrel_mapping(self):
        self.assertEqual(tool.classify([self.row("AC1")], "AC1")["target"], "dgpu")

    def test_malformed_or_offline_supply_cannot_request_dgpu(self):
        for value in (None, "bad", "0", "-1"):
            self.assertEqual(tool.classify([self.row("AC1", online=value)], "AC1")["target"], "igpu")

    def test_battery_online_does_not_count_as_external_input(self):
        self.assertEqual(tool.classify([self.row("BAT0", "Battery")], "ADP0")["source"], "battery")

    def test_missing_sysfs_is_readable(self):
        self.assertEqual(tool.graphics(Path("/nonexistent-pci-fixture"), Path("/nonexistent-drm-fixture")), [])
        self.assertEqual(tool.supplies(Path("/nonexistent-power-fixture")), [])

    def test_graphics_filters_pci_class_and_resolves_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); pci = base / "pci"; drm = base / "drm"
            pci.mkdir(); drm.mkdir()
            gpu = pci / "0000:00:02.0"; gpu.mkdir()
            (gpu / "class").write_text("0x030000")
            (gpu / "vendor").write_text("0x8086")
            node = drm / "card7"; node.mkdir(); (node / "device").symlink_to(gpu)
            connector = drm / "card7-eDP-1"; connector.mkdir()
            (connector / "status").write_text("connected")
            other = pci / "0000:00:03.0"; other.mkdir(); (other / "class").write_text("0x020000")
            rows = tool.graphics(pci, drm)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["drmNodes"], ["/dev/dri/card7"])
            self.assertEqual(rows[0]["outputs"][0]["status"], "connected")

    def test_profile_rejects_same_gpu_and_path_strings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            for igpu, dgpu in [("0000:00:02.0", "0000:00:02.0"), ("../../bad", "0000:01:00.0")]:
                path.write_text(json.dumps({"igpu": igpu, "dgpu": dgpu}))
                with self.assertRaises(ValueError):
                    tool.load_profile(path)


if __name__ == "__main__":
    unittest.main()
