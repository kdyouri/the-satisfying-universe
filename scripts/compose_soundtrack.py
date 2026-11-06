"""Create an original ambient pad from oscillators; no recordings or external music."""

import hashlib
import json
import math
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / "tsu/assets/calm-original.wav"
target.parent.mkdir(exist_ok=True)
rate, seconds = 44100, 32
# Original slow chord arrangement. No borrowed melody or sampled instrument.
chords = [(48, 55, 59, 62), (45, 52, 59, 62), (41, 48, 52, 55), (43, 50, 57, 59)]
frequencies = [[440 * 2 ** ((note - 69) / 12) for note in chord] for chord in chords]
with wave.open(str(target), "wb") as output:
    output.setparams((2, 2, rate, 0, "NONE", "not compressed"))
    for second in range(seconds):
        block = bytearray()
        for sample in range(rate):
            t = second + sample / rate
            position = t / 8
            index = min(int(position), 3)
            blend = min(1.0, max(0.0, (position % 1 - 0.75) * 4)) if index < 3 else 0
            envelope = min(1, t / 2, (seconds - t) / 3)
            channels = []
            for channel in range(2):
                value = 0.0
                for offset, weight in ((0, 1 - blend), (1, blend)):
                    for voice, frequency in enumerate(frequencies[min(index + offset, 3)]):
                        phase = 2 * math.pi * frequency * t + channel * (voice + 1) * 0.13
                        value += weight * (math.sin(phase) + 0.08 * math.sin(phase * 2))
                channels.append(round(value * envelope * 0.025 * 32767))
            block.extend(struct.pack("<hh", *channels))
        output.writeframes(block)
manifest = {
    "title": "TechnoInno — calme original 01",
    "duration_seconds": seconds,
    "source": "Original oscillator synthesis and chord arrangement in compose_soundtrack.py",
    "external_samples": False,
    "external_music": False,
    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
}
target.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Original ambient soundtrack prepared; no external API or music service used.")
