# Video stutter and repeated RX wakeups

On October 22, 2026, video playback on the G513QY paused intermittently while
ROG Control reported alternating `dGPU status changed: active` and
`dGPU status changed: suspended` notifications. This occurred with Eco selected
and barrel power connected.

The notifications reported RX power transitions. KWin's primary renderer
stayed on the iGPU; the controller did not request renderer switches during
the observed loop.

## What caused the wakeups

Runtime-PM and ioctl traces identified KWin's main thread as the resume caller.
A recorded RX wake delayed its next ioctl by about 0.9 seconds. The call stack
ran through `VulkanQueue::submit` and `MultiGpuSwapchain::copyRgbBuffer`.
Inspection of the copied surface identified Plasma as its owner.

KWin kept a client's original DMA-BUF `main_device` after changing its own
renderer. A client that first connected while RX was primary could continue
receiving RX feedback after the renderer and its managed context moved to
iGPU. KWin then copied updated Plasma content through RX, waking the device.

The [Wayland DMA-BUF protocol](https://gitlab.freedesktop.org/wayland/wayland-protocols/-/blob/main/stable/linux-dmabuf/linux-dmabuf-v1.xml)
allows the advertised main device to change over time. The compositor needs
to send clients updated feedback when that happens.

## The patch

The updated [KWin patch](../patches/kwin-live-renderer.patch) changes the client
main device when experimental renderer switching is enabled. It sends updated
default and per-surface feedback to clients using protocol versions that
support feedback.

Xwayland keeps its existing stable device policy. Legacy clients and existing
`wl_buffer` import metadata retain their existing behavior and copy fallback.
The ordinary nonexperimental path keeps its previous feedback behavior.

This is separate from the earlier fix that kept KWin's explicit synchronization
manager on the panel GPU. Both changes are needed for the tested setup.

## What was verified

| Check | Observed result |
| :--- | :--- |
| Unpatched feedback reproduction | Existing version 4 and 5 clients still received RX after KWin switched to iGPU |
| Patched protocol test | Default and per-surface clients followed RX → iGPU → RX → iGPU |
| Isolated Plasma migration | Plasma and a test window kept the same processes, advanced frames and remained visible through RX → iGPU → RX |
| Live workaround | Restarting only Plasma cleared its stale route; the same video then played smoothly, confirmed by the user |
| Live power check | With Eco and barrel power, all 100 samples over about 30 seconds showed RX in D3cold and KWin steady on iGPU |

The updated KWin library was built and installed in the private prefix with a
backup. The current session kept its already mapped library. A login using
the updated library remains a separate smoke test; the nested tests do not
replace that check.

These observations establish this wakeup loop. They do not establish the cause
of every video pause or the earlier intermittent pointer-only stutter.

## Run the hardware regression test

First [prepare and build the patched KWin source](build.md). Then, from a
working Wayland session on the reference laptop, run:

```sh
python3 tests/hardware/kwin_feedback/run.py \
  --kwin-build build-src/kwin/build
```

The test needs two real GPUs, a matching full KWin build, `qdbus6`,
`dbus-daemon`, a C compiler, `pkg-config`, Wayland client development files,
`wayland-scanner` and the DMA-BUF protocol XML. If protocol discovery fails,
pass `--protocol-xml /path/to/linux-dmabuf-v1.xml`. `--qt-plugins` overrides
the reference Arch Qt plugin directory.

The default nodes match the G513QY PCI mapping. For a different machine, pass
`--rx-node /dev/dri/by-path/PCI-render` and
`--igpu-node /dev/dri/by-path/PCI-render` with its actual paths. Read the
[porting guide](porting.md) before testing another GPU pair.

The runner creates a nested compositor, private D-Bus and temporary app
directories. It does not replace the host compositor or run a system
power-policy service. It deliberately uses both GPUs, so RX wakeups during
the test are expected. It writes local logs and `result.json`, prints their
directory and removes its processes and private runtime socket directory.
It is a manual hardware test, outside portable CI.

## Activate an updated build

Rebuild and install the private KWin prefix using the build guide. A
`reconfigure` call cannot load a replacement shared library into an existing
compositor. Save your work and log out and back into the Frost session to
activate it. Keep the stock Plasma session and the previous library available
for recovery.

If the loop is already happening while KWin is on iGPU, restarting only
`plasma-plasmashell.service` cleared Plasma's route in the observed case without
closing other applications. This is a temporary recovery step, not a substitute
for loading the updated KWin build. Check the actual renderer, RX runtime state
and playback afterward.
