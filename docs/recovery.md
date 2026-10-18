# Return to the stock session

Save work before any logout. A renderer change normally keeps applications
open, but a logout closes them.

## Stop further automatic work

In a responsive desktop:

```sh
frost-gpu disable
systemctl --user stop frost-gpu-switch.service
```

The disable marker halts future controller passes after the current operation
and sends future routed launches down their original path. It does not undo
an in-progress migration or move existing apps back.

Select the ordinary Plasma Wayland entry at the next login. The session helper
chooses stock binaries unless the custom session is explicitly active and the
package compatibility checks pass.

## If the desktop will not start

Use a text console and create the per-user disable marker:

```sh
mkdir -p ~/.config/frost-gpu-live
touch ~/.config/frost-gpu-live/disabled
```

Log out or restart the failed login through the display manager after saving
anything recoverable. Choose stock Plasma. If necessary, restore the backed-up
Frost drop-ins for KWin and Plasma, then reload the user service manager. Do not
remove unrelated drop-ins or alter package-owned KWin files.

If you installed the optional power helper and want its policy removed too,
disable its service and remove only the Frost-owned udev rule after making a
backup. Stopping the live controller alone does not disable the independent
runtime-power helper. Leaving `power/control=auto` permits the normal driver
to manage runtime sleep; use your distribution's normal GPU policy afterward.

## What a blocked state means

- **Capture or lock:** finish recording/sharing or unlock, then let the
  controller re-evaluate. Do not bypass the guard.
- **Unsupported context:** stop or relaunch that app through a compatible route.
  Apps already on the target may stay there while KWin remains blocked.
- **Halted / uncertain:** an operation lost its result. Inspect logs and the
  actual renderer before restarting anything. Automatic retries deliberately stop.
- **ABI mismatch:** rebuild against the current graphics stack. Do not merely
  edit the version manifest to claim compatibility.
- **iGPU mode, RX active:** inspect display wiring and GPU clients. The renderer
  label is not a force-off command. An active client can correctly keep RX awake.

Useful local reads:

```sh
frost-gpu status
systemctl --user status frost-gpu-render.service frost-gpu-switch.service
journalctl --user -u frost-gpu-switch.service -b
python3 tools/inspect_system.py --profile examples/g513qy.json
```

Review logs before posting an issue. Remove account data, personal paths, URLs,
network/proxy settings, device serials, and unrelated application arguments.
