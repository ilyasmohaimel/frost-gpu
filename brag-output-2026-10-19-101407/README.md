# Frost GPU film

A 24-second remake with a matched G513QY model, an illustrated vapor chamber with two chip openings and the right blower tucked against the chamber with only its edge exposed, actual before/after desktop captures, a real Brave window recording mapped onto the model display and custom motion design. Personal photographs are references only and do not appear in the video or its assets.

- `brag.mp4`: final 1080p, 60 fps video.
- `brag.jpg`: selected poster, also baked into the first video frame.
- `preview.webp`: silent, looping preview shown at the top of the repository README.
- `composition/`: editable Hyperframes project.
- `production/`: original Blender scene builder and reference-tracing geometry.
- `CREDITS.md`: picture, music and font provenance.
- `share-copy.txt`: suggested post copy with music attribution.

## Edit the film

From `composition/`, run `npm ci`, then `node build.mjs` after source edits. `film.template` contains the scene structure, `film.css` the layout and `film.js` the paused GSAP timeline. Video and audio playback belong to Hyperframes.

Run `npx hyperframes check --samples 13 --snapshots --json`, then use `npx hyperframes preview --background` to inspect the timeline. The preview URL includes `#project/composition`. This host uses the installed Chromium because the bundled headless browser failed to decode media. Set `HYPERFRAMES_BROWSER_PATH=/usr/lib/chromium/chromium` for the check, preview and render commands here. On another system, use its own working Chromium path or the bundled browser. Render with `npm run render`, then `npm run finalize` to create the poster and final MP4. The finalizer requires Python and Pillow. It checks the duration, frame count, audio stream and poster, then decodes the whole video.

## Rebuild the model footage

Blender 4.5 LTS was used. The opening and product camera moves were rendered at 30 fps, then interpolated to 60 fps. The final cutaway uses an RX-rendered full-resolution still with a slow 4.5% push over five seconds; its markers follow that image transform. The macro introduction holds its last frame during the first transition. The product display uses the included real laptop recording as a Blender movie texture.

The source model is built from geometry. Keyboard outlines are traced from the exact ASUS G513QY reference, including its shaped Enter key, five hotkeys and short function row. ASUS reference imagery supplies calibrated model materials for legends and the deck pattern. Personal photographs are not model textures. Hidden dimensions are reconstructed from available official views and the service guide, not manufacturing CAD.

Keep the ASUS references in a local asset cache, outside the web composition. The default is `~/.local/share/frost-gpu-film/online-reference/`; set `FROST_FILM_CACHE` to use another location. Download `asus-top.png` from https://dlcdnwebimgs.asus.com/gain/FB052830-05EB-4A54-8727-E2D391A2755C/w1600/h1200 and `asus-top-hires.png` from https://dlcdnwebimgs.asus.com/gain/FB052830-05EB-4A54-8727-E2D391A2755C/w3200/h2400. Expected dimensions are 1600x1176 and 3200x2352.

The board outline and passive locations use the G513QY motherboard photograph from page 25 of the linked service guide. The rendered PCB uses consistent procedural materials; the vapor chamber is retained with local chip openings. Keep that image at `references/extracted/board-004.png` under the same local asset cache. Its original dimensions are 1118x797. `production/board-trace.json` stores the outline and raised passive locations; `production/board_detail.py` builds the board.

`production/traced-keys.json` already contains the traced outlines. To regenerate it, use Python with NumPy and OpenCV in an isolated environment, then run `production/trace_keys.py`. The tracer checks that the key silhouettes do not overlap.

Run Blender with `--background --factory-startup --disable-autoexec --python-exit-code 1 --python production/matched_model.py -- product`. Repeat with `intro`. For the delivered cutaway, set `FROST_FRAME_START=1 FROST_FRAME_END=1` and use `cut`, then run `python production/encode-cut.py` and `python production/sync-callouts.py` before rebuilding the composition. `top` renders the layout check. Frame sequences go to `composition/assets/blender/`. The private editable scenes are saved to `FROST_FILM_CACHE`.

## What the desktop capture proves

The paired images show the same open workspace before and after a real KWin renderer change. The capture was triggered manually using the installed controller, then automatic policy was restored. The fixed-iGPU OpenGL capture terminal stays open. The screenshots show RX runtime active in both states; they do not prove RX power-off or measure switching speed.

Live migration remains experimental and limited to supported clients. Native games do not migrate. The internal display stays physically attached to the iGPU in every mode.

## Record a replacement screen clip

`production/record-live-screen.py --window <x11-window-id> --pid <owned-brave-pid>` records an inspected XWayland Brave window and verifies ownership and focus. It expects a 1920x1040 content window with the public repository open. It writes a six-second 1080p clip to `composition/assets/desktop/repo-screen.mp4`. The browser must be isolated from private tabs. The supplied clip is already recorded; rebuilding the model does not require a new recording.
