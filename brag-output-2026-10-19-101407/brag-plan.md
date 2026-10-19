# Frost GPU: keep going

A 24-second film for an experimental AMD/AMD KDE session. Use a custom G513QY model, a custom illustrated cutaway and actual desktop captures. This replaces the rejected flat card video and the abandoned wide-board Three.js draft.

## Product and evidence

Frost GPU changes KWin's renderer between the RX 6800M and Vega iGPU. The internal panel remains physically attached to the iGPU. Migration requires supported clients; native games do not migrate. The film does not promise universal app migration, zero stutter, measured switching speed or battery-life improvements.

The paired desktop images are actual captures on this machine, with the same Brave, VSCodium and WezTerm windows. The renderer was changed using the existing controller's manual target command for capture, then restored to the automatic barrel/USB-C/battery policy. The capture terminal used a fixed iGPU OpenGL context because the initial WebGPU capture terminal was rejected by the migration guard for compute pipelines. The images visibly retain RX runtime active; they are evidence of the KWin renderer change, not proof of RX power-off. The policy scene describes the installed intended power-source policy, with bounded app support shown on screen.

## Visual direction

- Silver field #E8EBEF, inspired by the laptop's light reflections.
- Slate ink #19222F for clear type.
- Blue-grey #202A3C for the power policy scene.
- Violet #6446B2 and muted blue #285B7D distinguish renderer ownership, drawn from the real keyboard lighting.
- White #F2F4F7 for light text.

Barlow Condensed Semibold carries large short phrases. Barlow carries supporting labels. JetBrains Mono appears in the real terminal. Keyboard legends follow the ASUS reference material.

Use subject-specific motion: a low camera push, a vertical shutter into the model, a screen match into the desktop, then an illustrated GPU handoff. Avoid a repeated feature-card format. Keep text separate from the detailed hardware. The hardware render uses Blender, a custom enclosure traced against ASUS reference views, a rebuilt keyboard without a number pad, integrated clickpad, thin screen frame and red rear accent. User-supplied photographs guide those corrections. The visible layout follows the exact supplied G513QY product reference. Hidden dimensions use the official views and service guide.

## Storyboard

| Time | Picture | Copy and purpose |
| --- | --- | --- |
| 0-2.8 | Macro Blender shot of the keyboard and front edge beside large type. | Unplug. Keep going. |
| 2.8-6.3 | Moving Blender camera across the matched laptop with a real recording of Brave scrolling the public repository on its screen. | Keep your desktop. KDE stays open. |
| 6.3-10.8 | Actual same workspace before and after the manual KWin renderer change. | Same windows. Different GPU. Manual capture qualification. |
| 10.8-15.8 | Tight illustrated chassis section around the APU and RX, with the vapor chamber retained, local apertures over the APU and RX, and the right blower and exhaust assembly visible. A graphical ownership line moves between the processors. | Two GPUs. One session. Cutaway qualification. |
| 15.8-19.8 | Large readable power-source policy, one row for battery/USB-C and one for barrel power. | Vega iGPU / RX 6800M. Experimental supported-app limitation. |
| 19.8-24 | Settled laptop render, Frost GPU wordmark and repository. | Your desktop stays with you. Source, patches and a porting guide. |

24 seconds at 1920x1080, 60 fps. The opening and product camera moves are rendered at 30 fps and interpolated to 60 fps. The cutaway uses an RX-rendered still with a five-second camera push. Keep motion and reading time ahead of musical beat matching.

## Audio

Machina by Scott Buckley, CC BY 4.0. Use a 24-second excerpt with soft fades and a restrained edit. Kenney CC0 interface sounds mark the shutter, renderer change and final arrival. No voiceover. Full attribution travels in CREDITS.md and share-copy.txt.

## Delivery

Local MP4, selected poster baked into frame zero, editable Hyperframes project, camera build scripts and clear provenance notes. No commit, push or upload for this revision. Keep private reference images and editable Blender scene files outside the editable web composition.
