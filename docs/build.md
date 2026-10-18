# Build and integration notes

This is a source release for an experimental setup. The G513QY reference is
hardware-specific. There is no automatic installer or universal binary bundle.
Keep a stock Plasma session available while working through these stages.

## Get the patched sources

Requirements: Git and Python 3.11+. Run from the repository root:

```sh
python3 tools/prepare_sources.py --output build-src
```

The tool clones KWin and ZSS, checks out the revisions in
`patches/upstreams.json`, checks each patch, then applies it. It refuses an
existing output directory. It does not build, install, or start anything.
Inspect the diffs with `git -C build-src/kwin diff` and the equivalent for ZSS.

## Build ZSS

Install Meson, Ninja, a C compiler, Python, Vulkan development files, X11/XCB
and Wayland development files, and `glslangValidator` for the shader probes.
The pinned source's Meson files define the remaining requirements and obtain
the matching Vulkan-Headers subproject.

```sh
meson setup build-src/zss/build build-src/zss --buildtype=debugoptimized
meson compile -C build-src/zss/build
```

Run CPU-only regression tests separately from hardware probes. Inspect
`meson test -C build-src/zss/build --list` first; do not run every hardware
test on a working desktop without reading what it does.

The useful build outputs are:

```text
build/src/daemon/zssd
build/src/zssctl/zssctl
build/src/layer/zss-run
build/src/layer/zss_icd.json
build/src/layer/libzss_airlock.so
```

The generated launcher and ICD manifest initially point into the build tree.
For a separate installed prefix, update those paths together. The reference
uses `/opt/frost-gpu/bin`, `/opt/frost-gpu/lib`, and `/opt/frost-gpu/share`.
Do not replace the system Vulkan ICD files.

## Build KWin

Use the Qt, KDE Frameworks, Wayland, graphics, and protocol development
dependencies required by the pinned KWin `CMakeLists.txt`. Match the installed
stack rather than mixing libraries from a different release.

```sh
cmake -S build-src/kwin -B build-src/kwin/build -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX=/opt/frost-gpu/kwin \
  -DBUILD_TESTING=OFF
cmake --build build-src/kwin/build --parallel 4
```

This is the full desktop build. Keep screen locking and the normal production
features enabled. Earlier stripped-down nested builds were only test fixtures.
The tested full build had `KWIN_BUILD_SCREENLOCKER=ON`.

Review the install manifest before running an installation. Stage into a
temporary directory with `DESTDIR` if you need to inspect every output. An
installation under `/opt/frost-gpu/kwin` must not overwrite `/usr/bin/kwin_wayland`
or package-owned libraries. You still need to validate its ABI against your
current Qt/KDE/Mesa packages.

## Connect the G513QY reference

This map describes the tested integration. Review the files and
[porting requirements](porting.md) before installing them on another machine.
Do not copy the obsolete initial stock-session charger policy from older work.

| Source | Reference destination / purpose |
| :--- | :--- |
| `frost_session.py`, `frost_app.py`, `frost_manage.py`, `frost_power.py` | Root-owned `/usr/local/libexec/` |
| `frost_gpu_live.py`, another `frost_power.py` | Root-owned `/opt/frost-gpu/libexec/` |
| `session-integration/frost-gpu` | `/usr/local/bin/frost-gpu` |
| `frost-gpu-session`, `frost-gpu-app` | `/usr/local/libexec/` executable wrappers |
| `session-integration/kwin_wayland` | `/usr/local/libexec/frost-gpu-dispatch/kwin_wayland` |
| `frost-gpu-live.desktop` | `/usr/share/wayland-sessions/`, separate login choice |
| `90-frost-kwin.conf` | User drop-in for `plasma-kwin_wayland.service` |
| `90-frost-plasma.conf` | User drop-in for `plasma-plasmashell.service` |
| `frost-gpu-render.service`, `frost-gpu-switch.service` | User units under `plasma-workspace.target` |
| Controller wrapper shown below | `/opt/frost-gpu/bin/frost-gpu-live` |
| `power/frost-gpu-power.service`, udev rule | System oneshot service and power-supply trigger |
| `frost-gpu-power` | Root-owned executable `/usr/local/libexec/` |
| Shell hooks | Explicit Bash/Fish interactive integration for GUI-launched terminals |
| `wezterm-blur.cpp`, `frost-wezterm-blur.service` | User XCB bridge for WezTerm's XWayland blur request |

The controller wrapper is:

```sh
#!/bin/sh
exec /usr/bin/python3 -I /opt/frost-gpu/libexec/frost_gpu_live.py "$@"
```

Use a private user runtime socket, not a system-wide privileged migration
daemon. The reference `zssd.conf` is empty except for a comment: it configures
no hardware detach, power-cut, service-stop, or automatic-off backend. The user
render service passes both GPUs explicitly and uses `--no-auto-attach`.

`frost_session.compatible()` requires `/opt/frost-gpu/share/manifest.json`.
Its `packages` object maps `kwin`, `qt6-base`, and `mesa` to the **exact package
version strings used to build and test this stack**. Record them after a
successful matching build. Do not refresh the manifest just to silence an ABI
mismatch after an update. Its expected private KWin helpers and libraries must
also exist; a missing part causes stock fallback.

Ensure the login's Frost session flag, login-session marker, and `ZSS_SOCKET`
reach the user service manager before its units start. The dedicated session
entry is the opt-in point. Use `systemctl --user cat` to review final merged
units and `systemctl --user daemon-reload` after changes. Do not enable the
controller until the manual tests in [validation](validation.md) pass.

For each chosen application, make a backed-up per-user desktop entry that
passes its original command and arguments to `frost-gpu-app PROFILE -- COMMAND`.
Preserve file/URL placeholders and existing security wrappers. Do not publish
personal profile paths or proxy assignments. Test launch from both the menu
and any custom keyboard shortcut. The shell hooks do not clean every possible
noninteractive child; use `frost-gpu native -- COMMAND` when needed.

For ROG Control Center's live route, build the upstream revision listed in the
app matrix with Slint's X11/OpenGL backend and install that private binary at
the path expected by the dispatcher. The stock package can remain in place.
LibreOffice's GTK route needs its GTK integration and the GStreamer codecs
used by your documents.

## Build the tray

```sh
cd reference/g513qy/indicator
./build.sh
```

This requires a C++ compiler, `pkg-config`, Qt6 Widgets, and Qt6 DBus. Install
the result at `~/.local/libexec/frost-gpu-indicator`, then review the included
user service. Its `%h` path is portable, while the C++ hardware constants are
still specific to the reference laptop. In KDE, set the indicator to always
show in the system tray. A mode label reports renderer choice separately from
the observed RX runtime state.

For WezTerm blur on the XWayland route, build `wezterm-blur.cpp` with a C++17
compiler and XCB, place the executable at `~/.local/libexec/frost-wezterm-blur`,
and enable its included user service. It adds KWin's blur property only to
WezTerm-class windows that do not already have one. It watches X11 events,
does not poll, and does not change theme or opacity. The native Wayland blur
option alone cannot cover this XWayland route.

## First real login

Save your work and select **Plasma (Frost GPU switching)** manually at the
display manager. Verify KWin's actual executable and renderer, a nonblank
display, registered Plasma contexts, and the private daemon socket. Then run
the physical charger tests. Keep the stock session selectable and keep local
backups of every user drop-in and desktop entry you change.

This repository deliberately excludes the machine's autologin and forced
relogin scripts. Use the [recovery guide](recovery.md) if startup or switching
does not behave as expected.
