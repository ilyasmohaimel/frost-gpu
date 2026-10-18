"""Generate the project's own quiet chord bed and two short switch accents."""
from array import array
import math
from pathlib import Path
import sys
import wave

RATE = 44100
DURATION = 22
samples = array('h')
for n in range(RATE * DURATION):
    t = n / RATE
    # A slowly settling major-sixth voicing, with no samples or external assets.
    envelope = min(t / 1.4, 1) * max(0, min((DURATION - t) / 2.2, 1))
    chord = sum(math.sin(2 * math.pi * hz * t) for hz in (130.8128, 196, 220, 329.6276)) / 4
    value = chord * .10 * envelope
    for start, hz in ((4.15, 660), (10.3, 880)):
        dt = t - start
        if 0 <= dt < .35:
            value += .055 * math.sin(2 * math.pi * hz * dt) * math.exp(-dt * 22)
    samples.append(round(max(-1, min(1, value)) * 32767))
if sys.byteorder != 'little':
    samples.byteswap()
target = Path(__file__).with_name('assets') / 'frost-tone.wav'
target.parent.mkdir(exist_ok=True)
with wave.open(str(target), 'wb') as stream:
    stream.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
    stream.writeframes(samples.tobytes())
