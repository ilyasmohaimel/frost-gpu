# App support

Results from the real custom KDE session on the G513QY, completed
2026-10-17 through 2026-10-18. A pass covers the workflow in the table.
It does not cover every feature an application might use.

**Live migration** means a registered render context moved with the process
still alive. **Compatibility** means the tested workflow stayed usable through
both desktop switches, without an app context moving. **Fixed iGPU** is a
deliberate exception to the RX-on-barrel policy.

| App | Route | Tested across both directions | Remaining limits |
| :--- | :--- | :--- | :--- |
| Brave | Live, ANGLE Vulkan / XWayland | WebGL, input state, local WebRTC encode/decode with advancing frames and the same GPU helper | Hardware decode, protected media, arbitrary sites/codecs/extensions |
| Codex / ChatGPT | Live, Chromium route | Signed-in UI and GPU helper stayed alive; agent tool use continued through later switches | Every embedded view, upload, media path, or future tool |
| T3 Code Nightly | Live, Chromium route | Project UI, unsent draft, terminal drawer, local Git state, same GPU helper | Agent execution unverified; a terminal command did not execute in the fresh draft setup |
| VSCodium | Live, Chromium route | Extension-host editing and saving JavaScript; integrated terminal counter continued | Third-party extensions; Microsoft VS Code itself was not installed/tested |
| WezTerm | Live, OpenGL / Zink / X11 | Actual user config, advancing shell counter, native child environment, same GUI process | The route overrides WebGpu; other backends and terminal protocols |
| Hiddify | Live, OpenGL / Zink / X11 | Same GUI context; nine HTTPS requests through the active local proxy returned 200, zero errors | Full TUN routing, every protocol, reconnect behavior |
| ROG Control Center | Live, rebuilt Slint X11 / OpenGL | Visible existing app, same context and process | Individual hardware controls were not exercised |
| RedPanda C++ | Native raster | GUI Compile and Run produced the expected output, 42; IDE stayed open | Debugger, other toolchains and plugins |
| Konsole | Native raster | Shell counter and child environment continued; same visible process | No independent app GPU context needed moving in this test |
| WeChat | Fixed native iGPU / X11 | Signed-in File Transfer view and editable unsent draft survived both desktop moves | Does not move to RX; calls, camera, video and mini-apps untested |
| Blip | Default software | Signed-in UI survived both moves; a generated text file transfer to a local phone completed | Transfer finished before switching; in-flight transfer and receiver hash unverified |
| LibreOffice | Native GTK3 / X11 | Writer edit/save; Calc 500 formulas with verified sums; Impress 3D sphere, advancing local video and save | CPU Calc only; no OpenCL platform; Draw, Base, Math and other plugins untested |

## Fixes behind those results

- WeChat's Zink helper used recorded query commands that could not safely move.
  Its launcher now uses the native iGPU route.
- LibreOffice's Qt media backend crashed during video-thumbnail handling before
  a switch. GTK3/X11 plus the required GStreamer codecs passed the tested workflow.
- VSCodium's integrated terminal clears the GUI driver's interposer variables
  before launching child commands. Bash and Fish have matching interactive hooks.
- WezTerm keeps the user's config but selects the tested OpenGL/X11 backend.
  Its Wayland blur setting cannot announce blur on XWayland. The included
  event-driven XCB bridge restores KWin's blur request on WezTerm windows,
  preserving the user's opacity and theme. Existing and newly opened windows
  were checked visually; other applications are left alone.
- ROG Control Center was rebuilt from upstream commit
  `ec09e7629da3e4081d9c342e7f323e30158cccfd` with X11/OpenGL support.

The dispatcher contains additional routes used during exploration. Presence in
`ROUTES` or its default set is not an end-to-end support result. Bitwarden,
Alacritty, Chromium, Firefox, Vesktop, Spotify, Flatpak apps, and other inventory
entries need separate workflow verification before being added to this table.
OBS output was not verified. LocalSend startup failed in its probe.

## Unsupported or unverified paths

Recorded query commands/results, advanced Vulkan features, compute, 32-bit
apps, Steam/Proton and game workloads have no supported result in this setup.
An unsupported registered context blocks the automatic operation.

Existing unwrapped processes cannot acquire migration support after launch.
Keep such apps on iGPU or relaunch them through an explicitly tested route.
Do not assume that an app update keeps the same graphics feature use.

There were no WeChat calls or messages in these tests. Private account captures,
contacts, proxy settings, and full installed-package inventories are not part
of this repository.
