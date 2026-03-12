from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from app.integrations.tts.base import SpeechSynthesisResult, TextToSpeechProvider
from app.utils import estimate_duration_seconds


class MockTTSProvider(TextToSpeechProvider):
    sample_rate = 22_050
    provider_name = "tone_fallback"

    def synthesize(self, *, text: str, output_path: Path, language: str) -> SpeechSynthesisResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_seconds = estimate_duration_seconds(text=text, words_per_minute=165, minimum=1.6)
        total_samples = int(self.sample_rate * duration_seconds)
        base_frequency = 180 + (len(text) % 7) * 22
        amplitude = 11_000

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            for index in range(total_samples):
                fade = min(1.0, index / 500, (total_samples - index) / 500)
                carrier = math.sin((2 * math.pi * base_frequency * index) / self.sample_rate)
                harmonic = 0.35 * math.sin((2 * math.pi * (base_frequency * 2) * index) / self.sample_rate)
                pulse = 0.15 * math.sin((2 * math.pi * 6 * index) / self.sample_rate)
                value = int(amplitude * fade * (carrier + harmonic + pulse))
                wav_file.writeframes(struct.pack("<h", value))

        # TODO: Swap this provider with real local TTS such as Coqui, Piper, or pyttsx3.
        return SpeechSynthesisResult(
            path=output_path,
            duration_seconds=duration_seconds,
            provider_name=self.provider_name,
        )
