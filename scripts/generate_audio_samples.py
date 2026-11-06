"""Generate small placeholder WAV files for the built-in demo scenarios."""

import math
import struct
import wave
from pathlib import Path


SAMPLE_RATE = 16_000
DURATION_SECONDS = 4
SCENARIOS = {
    "hinglish_refund_noisy.wav": 220,
    "tamil_complaint.wav": 247,
    "english_order_status.wav": 262,
    "bengali_technical.wav": 294,
}


def generate_placeholder_wav(path: Path, frequency: int) -> None:
    """Write a low-volume mono tone as a valid 16-bit PCM WAV file."""
    sample_count = SAMPLE_RATE * DURATION_SECONDS
    pcm = struct.pack(
        f"<{sample_count}h",
        *(
            round(3276.7 * math.sin(2 * math.pi * frequency * index / SAMPLE_RATE))
            for index in range(sample_count)
        ),
    )

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm)


def main() -> None:
    output_dir = Path(__file__).resolve().parents[1] / "assets" / "sample_audio"
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, frequency in SCENARIOS.items():
        path = output_dir / filename
        generate_placeholder_wav(path, frequency)
        print(f"Generated {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
