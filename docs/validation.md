# Validation record

This is a public summary of local observations. Private account logs, desktop
captures, process IDs, and full package inventories were excluded. These notes
are not an independent reproduction on another machine.

## Tested machine

| Component | Test setup |
| :--- | :--- |
| Laptop | ASUS ROG G513QY |
| Integrated GPU | AMD Vega / Cezanne, PCI `0000:07:00.0`, `1002:1638` |
| Discrete GPU | AMD RX 6800M, PCI `0000:03:00.0`, `1002:73df` |
| Display | Internal panel connected to iGPU |
| Desktop | Arch Linux, KDE Plasma Wayland, custom KWin 6.8.0 |
| KWin source | `066d1e17c945d9a89fee645e10a2bbd77f2e93a6` |
| ZSS source | `82d80f3e44e6a8ed696e4fe3b17655e3952a58cd` |

## Observed results

| Check | Result | Scope |
| :--- | :--- | :--- |
| Cross-GPU syncobj signaling | Passed | Imported timelines, both directions, eventfd, source-handle release |
| Fresh login after synchronization ordering fix | Passed | Real nonblank internal display, custom KWin and registered Plasma |
| Renderer roundtrip | Passed | iGPU to RX to iGPU; monitored GUI processes remained alive |
| Physical barrel unplug and reconnect | Passed | Renderer changed both ways; RX returned to D3cold on battery |
| Battery runtime suspend | Observed | `runtime_status=suspended`, PCI `power_state=D3cold`, stable for at least 10 seconds in sampled runs |
| Unplug to D3cold | About 8 seconds in one sampled run | One observation, not a latency guarantee or benchmark |
| USB-C PD, barrel disconnected | Passed | ADP0 and UCSI online; KWin and active registered contexts on iGPU; six samples showed RX suspended/D3cold |
| Physical barrel test after adding USB policy | Not repeated | Barrel-only fixture passed; physical barrel cycle happened before the USB policy change |
| Priority app workflows | Bounded passes | See the full app matrix; some routes use software or stay on iGPU |
| Battery runtime / energy improvement | Not measured | No hours, watts, or percentage claim |
| Original intermittent pointer stutter | Cause unconfirmed | A successful GPU policy change does not prove a stutter fix |

## Reproduce the evidence on your hardware

1. Launch a disposable window through the shim and record its PID and visible state.
2. Move iGPU to dGPU and back manually. Verify pixels, input, and the actual
   renderer, not just an exit code.
3. Repeat on a real DRM session. A nested compositor is an earlier test stage,
   not proof of physical display behavior or runtime suspend.
4. Add one application at a time and exercise its real workflow.
5. Test the screen lock and capture refusal paths before enabling automatic policy.
6. Physically unplug, reconnect, then test USB-C separately. Read the kernel's
   runtime state after activity settles. A tray label alone is not evidence.
7. Repeat after a graphics-stack update. Keep a stock-session recovery path.

The source-preparation helper checks both patches against their pinned upstream
commits. Repository CI tests only the portable inspection/policy fixtures and
controller/dispatch behavior. It does not have GPU hardware and cannot certify
the live migration or power-off results.
