#!/usr/bin/env python3
"""Read GPU topology, charger signals and runtime state without changing them."""
import argparse
import json
from pathlib import Path
import re


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def supplies(root):
    rows = []
    if not root.is_dir():
        return rows
    for path in sorted(root.iterdir()):
        rows.append({"name": path.name, "type": read(path / "type"),
                     "online": read(path / "online"),
                     "usbType": read(path / "usb_type")})
    return rows


def classify(rows, barrel_supply):
    active = []
    for row in rows:
        try:
            online = int(row.get("online") or "0") > 0
        except ValueError:
            online = False
        if online and row.get("type") != "Battery":
            active.append(row)
    usb = any((r.get("type") or "").startswith("USB") or
              r["name"].startswith("ucsi-source-psy-") for r in active)
    barrel = bool(barrel_supply) and not usb and any(
        r["name"] == barrel_supply and r.get("type") == "Mains" for r in active)
    source = "usb-c" if usb else "barrel" if barrel else "external-unknown" if active else "battery"
    return {"source": source, "target": "dgpu" if barrel else "igpu",
            "runtimePolicy": "on" if barrel else "auto",
            "scope": "inspection only; no settings applied"}


def graphics(root, drm):
    rows = []
    if not root.is_dir():
        return rows
    for device in sorted(root.iterdir()):
        code = read(device / "class")
        try:
            if (int(code or "0", 16) >> 16) != 3:
                continue
        except ValueError:
            continue
        nodes, outputs = [], []
        if drm.is_dir():
            for node in sorted(drm.iterdir()):
                if not re.fullmatch(r"(?:card\d+|renderD\d+)", node.name):
                    continue
                if (node / "device").resolve() != device.resolve():
                    continue
                nodes.append("/dev/dri/" + node.name)
                if node.name.startswith("card"):
                    for connector in sorted(drm.glob(node.name + "-*")):
                        outputs.append({"name": connector.name,
                                        "status": read(connector / "status")})
        driver = device / "driver"
        rows.append({"pci": device.name, "vendor": read(device / "vendor"),
                     "device": read(device / "device"),
                     "driver": driver.resolve().name if driver.exists() else None,
                     "drmNodes": nodes, "outputs": outputs,
                     "runtimeStatus": read(device / "power/runtime_status"),
                     "runtimeControl": read(device / "power/control"),
                     "pciPowerState": read(device / "power_state")})
    return rows


def load_profile(path):
    profile = json.loads(path.read_text())
    for key in ("igpu", "dgpu"):
        if not re.fullmatch(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]", profile.get(key, "")):
            raise ValueError("Invalid " + key + " PCI address")
    if profile["igpu"].lower() == profile["dgpu"].lower():
        raise ValueError("The two GPU addresses must differ")
    name = profile.get("barrel_supply")
    if name is not None and (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]+", name)):
        raise ValueError("Invalid barrel supply name")
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    try:
        profile = load_profile(args.profile) if args.profile else {}
    except (OSError, ValueError, TypeError, AttributeError) as error:
        parser.error(str(error))
    rows = supplies(Path("/sys/class/power_supply"))
    gpus = graphics(Path("/sys/bus/pci/devices"), Path("/sys/class/drm"))
    found = {gpu["pci"].lower() for gpu in gpus}
    print(json.dumps({"graphics": gpus, "powerSupplies": rows,
                      "policyPreview": classify(rows, profile.get("barrel_supply")),
                      "profileGpuMatches": {key: profile[key].lower() in found
                                            for key in ("igpu", "dgpu") if key in profile}}, indent=2))


if __name__ == "__main__":
    main()
