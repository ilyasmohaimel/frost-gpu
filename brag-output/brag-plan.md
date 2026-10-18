# Frost GPU project tour

The project is a KDE Wayland experiment that moves supported rendering between
an AMD iGPU and RX 6800M. Its strongest result is keeping the session open while
the RX reaches runtime suspend after a switch.

The visual hook is the project's own two-chip diagram. Show the source policy
in use: barrel power, unplug, move the supported contexts, observe D3cold. This
is an illustration based on local tests, not footage or a live timing claim.

Tone: polished, with the feel of a hardware bench demonstration. Landscape,
1280 by 720, 22 seconds. Navy `#142d45`, ice `#f0f6fa`, blue `#99c9ef`, copper
`#e7a17e`. System sans-serif type. The large hardware diagram carries the frame.
Use readable holds and one continuous signal moving between chips.

## Storyboard

| Time | Picture and copy | Motion and audio |
| :--- | :--- | :--- |
| 0 to 4 seconds | "Keep the desktop. Change the GPU." Two chips and supported-app token on RX. | A circuit connection draws in; one soft synthesized chord. |
| 4 to 10 seconds | "Unplug. Keep working." Power label changes to Battery; supported-app token moves to iGPU. | Continuous token movement, brief click at the policy change. |
| 10 to 16 seconds | "Sync on iGPU. RX asleep." Show `suspended` and `D3cold`. | RX dims while the fixed synchronization path stays lit; soft confirmation. |
| 16 to 22 seconds | "Frost GPU" and "Source, patches, and a guide for your hardware." Show the repository address. | Clean closing hold; synthesized bed decays. |

The footer stays visible: "Illustrated sequence · AMD/AMD tested · app support
varies". No account data, desktop screenshots, invented measurements, universal
support claim, or narration.

Audio: locally synthesized, low-volume warm chord bed with two small accents.
No third-party music assets. Exact beat sync is unnecessary for the explanatory
movement. Audio-reactive visuals are omitted to keep state changes unambiguous.

Share caption: Frost GPU moves supported KDE rendering between iGPU and RX
6800M, then lets the RX sleep. The patches, app results, and porting guide are
public, including the limits.
