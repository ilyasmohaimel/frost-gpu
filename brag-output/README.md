# Project tour

`brag.mp4` is a 22-second illustrated tour. `brag.jpg` is its poster and first
frame. The animation describes the tested policy, not an actual-time desktop
recording. The source is in `composition/`.

Requirements: Node.js 22+, npm, FFmpeg, and a Chromium-compatible browser.

```sh
cd brag-output/composition
npm ci
python3 make_audio.py
npm run check
npm run dev
```

To export after reviewing the preview:

```sh
npm run render
```

The dependencies are pinned in `package-lock.json`. Audio is synthesized by
the included script. No account captures, external fonts, narration, or bundled
third-party tracks are needed. The system sans-serif fallback can vary across
hosts. Rendering uses the normal browser/encoder paths, not GPU switching tests.

The poster was chosen from a settled closing frame. To reproduce the first-frame
poster after rendering, extract a closing frame and replace frame zero using
FFmpeg. The final distributed video keeps the same 22-second duration and audio.
