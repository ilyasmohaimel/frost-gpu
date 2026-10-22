#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check live DMA-BUF feedback in an isolated nested KWin on two real GPUs."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import stat
import subprocess
import tempfile
import time

CASES = ((4, "default"), (5, "default"), (4, "surface"), (5, "surface"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def wait_for(predicate, message, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise RuntimeError(message)


def protocol_xml():
    directory = Path(subprocess.check_output(
        ["pkg-config", "--variable=pkgdatadir", "wayland-protocols"], text=True).strip())
    for part in ("stable/linux-dmabuf/linux-dmabuf-v1.xml",
                 "unstable/linux-dmabuf/linux-dmabuf-unstable-v1.xml"):
        if (directory / part).is_file():
            return directory / part
    raise RuntimeError("DMA-BUF protocol XML not found; pass --protocol-xml")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kwin-build", required=True, type=Path)
    parser.add_argument("--protocol-xml", type=Path)
    parser.add_argument("--rx-node", type=Path,
                        default=Path("/dev/dri/by-path/pci-0000:03:00.0-render"))
    parser.add_argument("--igpu-node", type=Path,
                        default=Path("/dev/dri/by-path/pci-0000:07:00.0-render"))
    parser.add_argument("--qt-plugins", type=Path, default=Path("/usr/lib/qt6/plugins"))
    parser.add_argument("--output", type=Path, help="New directory for private test evidence")
    args = parser.parse_args()
    build = args.kwin_build.resolve()
    require((build / "bin/kwin_wayland").is_file(), "KWin build executable is missing")
    rx, igpu = args.rx_node.resolve(strict=True), args.igpu_node.resolve(strict=True)
    require(rx != igpu, "Choose two different render nodes")
    for node in (rx, igpu):
        require(node.name.startswith("renderD") and stat.S_ISCHR(node.stat().st_mode),
                "Expected a DRM render node: " + str(node))
    host_runtime = Path(os.environ["XDG_RUNTIME_DIR"])
    host_display = Path(os.environ["WAYLAND_DISPLAY"])
    if not host_display.is_absolute():
        host_display = host_runtime / host_display
    require(host_display.is_socket(), "The host Wayland socket is unavailable")
    xml = args.protocol_xml.resolve() if args.protocol_xml else protocol_xml()
    if args.output:
        work = args.output.resolve()
        work.mkdir(mode=0o700, parents=True, exist_ok=False)
    else:
        work = Path(tempfile.mkdtemp(prefix="frost-feedback-results-"))
    # Keep UNIX socket names below 108 bytes, even in a deeply nested checkout.
    runtime = Path(tempfile.mkdtemp(prefix="fg-feedback-", dir=host_runtime))
    processes, logs = [], []
    report = {"passed": False, "stages": []}
    try:
        for name in ("home", "config", "data", "cache", "state"):
            (work / name).mkdir()
        for kind, output in (("client-header", "dmabuf-client.h"),
                             ("private-code", "dmabuf-protocol.c")):
            subprocess.run(["wayland-scanner", kind, str(xml), str(work / output)], check=True)
        flags = shlex.split(subprocess.check_output(
            ["pkg-config", "--cflags", "--libs", "wayland-client"], text=True))
        subprocess.run(["cc", "-Wall", "-I" + str(work),
                        str(Path(__file__).with_name("client.c")),
                        str(work / "dmabuf-protocol.c"), "-o", str(work / "client"), *flags],
                       check=True)
        excluded = {"DRI_PRIME", "LD_PRELOAD", "MESA_VK_DEVICE_SELECT",
                    "MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE", "DBUS_SESSION_BUS_ADDRESS",
                    "DBUS_STARTER_ADDRESS", "DBUS_STARTER_BUS_TYPE", "MESA_LOADER_DRIVER_OVERRIDE",
                    "GALLIUM_DRIVER", "QT_QPA_PLATFORM"}
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("ZSS_", "FROST_", "VK_", "KWIN_")) and key not in excluded}
        env.update({
            "HOME": str(work / "home"), "XDG_RUNTIME_DIR": str(runtime),
            "XDG_CONFIG_HOME": str(work / "config"), "XDG_DATA_HOME": str(work / "data"),
            "XDG_CACHE_HOME": str(work / "cache"), "XDG_STATE_HOME": str(work / "state"),
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + str(runtime / "bus"),
            "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent-frost-feedback-system-bus",
            "KWIN_ENABLE_EXPERIMENTAL_GPU_SWITCH": "1",
            "KWIN_DRM_DEVICES": f"{rx}:{igpu}", "KWIN_RENDER_NODES": f"{igpu}:{rx}",
            "QT_PLUGIN_PATH": str(build / "bin") + ":" + str(args.qt_plugins),
            "QT_QPA_PLATFORMTHEME": "generic", "KDE_FULL_SESSION": "false",
            "QT_FORCE_STDERR_LOGGING": "1",
        })
        plugins = "".join(plugin.stem + "Enabled=false\n"
                          for plugin in (args.qt_plugins / "kwin/plugins").glob("*.so"))
        (work / "config/kwinrc").write_text(
            "[Plugins]\n" + plugins + "\n[org.kde.kdecoration2]\nNoPlugin=true\n")

        def start(name, command, extra=None):
            log = open(work / (name + ".log"), "w")
            logs.append(log)
            process = subprocess.Popen(command, env={**env, **(extra or {})},
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(process)
            return process

        def dbus(*arguments):
            result = subprocess.run(["qdbus6", *arguments], env=env, text=True,
                                    capture_output=True, timeout=10)
            require(result.returncode == 0, result.stderr or result.stdout)
            return result.stdout.strip()

        def primary():
            return dbus("org.kde.KWin", "/Compositor", "org.freedesktop.DBus.Properties.Get",
                        "org.kde.kwin.Compositing", "primaryGpu")

        def devices(case):
            path = work / f"client-{case[0]}-{case[1]}.log"
            if not path.exists():
                return []
            return [line.split()[1] for line in path.read_text().splitlines()
                    if line.startswith("device ")]

        (work / "bus.conf").write_text(
            '<busconfig><type>session</type><listen>' + env["DBUS_SESSION_BUS_ADDRESS"] +
            '</listen><policy context="default"><allow send_destination="*"/>'
            '<allow own="*"/><allow receive_sender="*"/></policy></busconfig>')
        bus = start("bus", ["dbus-daemon", "--nofork", "--config-file=" + str(work / "bus.conf")])
        wait_for(lambda: (runtime / "bus").exists() or bus.poll() is not None,
                 "Private D-Bus did not start")
        require(bus.poll() is None, "Private D-Bus exited; see bus.log")
        compositor = start("kwin", [str(build / "bin/kwin_wayland"), "--no-global-shortcuts",
                                   "--no-kactivities", "--wayland-display", str(host_display),
                                   "--socket", "feedback-test", "--width", "640", "--height", "400"])

        def ready():
            require(compositor.poll() is None, "Nested KWin exited; see kwin.log")
            if (runtime / "feedback-test").exists():
                try:
                    return bool(primary())
                except (RuntimeError, subprocess.TimeoutExpired):
                    pass
            return False

        wait_for(ready, "Nested KWin did not become ready")
        require(primary() == str(rx), "Nested compositor did not start on the RX")
        clients = [start(f"client-{version}-{kind}",
                         [str(work / "client"), str(version), str(int(kind == "surface"))],
                         {"WAYLAND_DISPLAY": "feedback-test"}) for version, kind in CASES]

        def check_clients():
            require(all(client.poll() is None for client in clients), "A feedback client exited")
            require(compositor.poll() is None, "Nested KWin exited; see kwin.log")

        wait_for(lambda: all(devices(case) for case in CASES), "Missing initial feedback")
        for index, target in enumerate((rx, igpu, rx, igpu)):
            check_clients()
            if index:
                answer = dbus("org.kde.KWin", "/Compositor",
                              "org.kde.kwin.Compositing.switchPrimaryGpu", str(target))
                require(answer == "true", "KWin rejected renderer switch: " + answer)
                # A stale-feedback implementation also emits a complete update.
                wait_for(lambda: all(len(devices(case)) >= index + 1 for case in CASES),
                         "No feedback update after renderer switch")
            identifier = target.stat().st_rdev
            expected = f"{os.major(identifier)}:{os.minor(identifier)}"
            stage = {"gpu": primary(), "clients": {
                f"v{version}-{kind}": devices((version, kind)) for version, kind in CASES}}
            report["stages"].append(stage)
            require(stage["gpu"] == str(target), "Actual renderer differs from the target")
            require(all(values[-1] == expected for values in stage["clients"].values()),
                    "Stale main_device feedback: " + json.dumps(stage))
        check_clients()
        report["passed"] = True
    except Exception as error:
        report["error"] = str(error)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=5)
                except ProcessLookupError:
                    pass
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for log in logs:
            log.close()
        shutil.rmtree(runtime)
        (work / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print("Evidence:", work)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
