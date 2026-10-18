# Bring it to your laptop

The AMD/AMD result is real. A second hardware family still needs its own proof.
This guide separates reusable policy from work that depends on your drivers,
display wiring, and firmware. Intel + NVIDIA is an example target, not a
supported preset.

## 1. Map the machine

```sh
python3 tools/inspect_system.py > hardware.json
lspci -nnk
ls -l /dev/dri/by-path
```

Find the iGPU, dGPU, kernel drivers, and connected display outputs. Use PCI
by-path symlinks, since `card0` and `renderD128` can change between boots.
Check which GPU owns the panel and every external output you need. A display
actively driven by the dGPU can prevent it from sleeping.

Copy `examples/g513qy.json` and replace its GPU identifiers and barrel supply
name with your observed values. The profile is consumed by the inspection tool
only. The reference controller and tray still contain hardware constants;
they do not load this JSON.

## 2. Identify your charger signals

Run inspection on battery, barrel-only, USB-C-only, and both connected. Save
the four reports locally and compare `powerSupplies`.

Do not copy the G513QY's `ADP0` assumption. Your machine may report separate
ports, one aggregate supply, a different UCSI name, or no usable distinction.
If the firmware exposes no reliable difference, use the conservative iGPU
policy or an explicit user choice. USB PD wattage alone does not establish
which renderer can run smoothly within the power budget.

Adapt `frost_power.py`, the tray classifier, and the root helper together.
Keep startup, newly launched apps, and the running controller consistent.
Test overlapping signals and missing nodes before using real charger events.

## 3. Establish the normal driver path first

For an Intel/NVIDIA laptop, first confirm that ordinary NVIDIA PRIME render
offload works with your installed driver. An OpenGL launch example is:

```sh
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia your-app
```

That chooses the GPU for a new process. It does not migrate an open app.
Use the [NVIDIA PRIME documentation for your driver version](https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/primerenderoffload.html).

NVIDIA runtime D3 depends on supported hardware, firmware, driver settings,
and idle PCI functions. A display or CUDA workload can keep it active. Check
your installed driver's documentation and `/proc/driver/nvidia/gpus/*/power`.
Do not copy old module options, device-removal rules, or another laptop's
ACPI calls. [NVIDIA runtime D3 documentation](https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/dynamicpowermanagement.html).

## 4. Prove cross-driver migration

Build the pinned patched sources locally using the [build notes](build.md).
Select the actual Vulkan ICDs for each target driver. The AMD-only
`radeon_icd.json`, Mesa device selectors, and Zink assumptions in the reference
are not drop-in NVIDIA settings.

Start with an isolated Vulkan triangle. Check that both physical devices can
expose a compatible feature set through the shim and that resource recreation,
memory type selection, queues, shaders, and synchronization survive a roundtrip.
Then test presentation, resize, video, and the graphics features your apps use.
Repeat with OpenGL through Zink only after the Vulkan path works.

Inspect the pinned ZSS source and its support limits before attempting a new
pair. This AMD extension uses render-only operations. Upstream's hardware
detach/power-cut path is a different mechanism; its existence does not validate
modern Intel/NVIDIA migration here.

If the devices cannot share the required contract, the port needs code changes
in the shim. Reject unsupported contexts before moving. Do not advertise a
working port based on an offload command or a successful empty test window.

## 5. Prove KWin and synchronization separately

The KWin patch targets one exact source revision. Rebase and review it for
your installed KDE/Qt stack. Test a nested session first, then a separate real
DRM login with a working stock-session fallback.

Keep the panel GPU first for synchronization only if the driver's imported
timelines and KWin's implementation support that arrangement. The AMD
cross-GPU syncobj result is not NVIDIA proof. Validate explicit sync,
buffer imports, XWayland, lock screen, capture refusal, and rollback on the
actual target drivers.

## 6. Adapt the integration

| Reference surface | What must change |
| :--- | :--- |
| `frost_session.py`, `frost_gpu_live.py`, `frost_manage.py` | PCI identities, selectors, packaging checks and driver paths |
| `frost_app.py` | Driver ICDs, app backend choices and unsupported-feature rules |
| Render service | `--gpu` arguments and installation prefix |
| `frost-gpu-power` | Exact PCI vendor/device checks and supported runtime PM policy |
| `frost_power.py`, `indicator/main.cpp` | Actual charger signals and GPU labels |
| Session units and display-manager entry | Distribution paths, stock fallback and user unit names |
| Per-app desktop entries | Original executable, arguments, sandbox requirements and update behavior |

Use a separate prefix. Keep package-owned KWin and drivers available. Do not
disable the screen locker or capture guard to get a green test result.

## 7. Earn the automatic policy

Only connect charger events after manual renderer moves, app workflows, and
real runtime suspend all pass. Use `power/control=auto` to allow driver-managed
sleep. Observe `runtime_status` and available PCI state; an "iGPU" indicator
does not prove the other GPU is off.

Repeat the full physical cable cycle with your normal apps and displays.
Write down exceptions. A useful port includes an honest app matrix and a
tested recovery path as well as the happy path.

If migration is not working yet, iGPU desktop plus per-app NVIDIA offload is
a practical interim setup. It preserves normal driver behavior while the
cross-driver work is being tested.
