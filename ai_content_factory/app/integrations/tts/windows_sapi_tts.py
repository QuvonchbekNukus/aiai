from __future__ import annotations

import subprocess
import sys
import wave
from pathlib import Path

from app.integrations.tts.base import SpeechSynthesisResult, TextToSpeechProvider


class WindowsSapiTTSProvider(TextToSpeechProvider):
    provider_name = "windows_sapi"

    def __init__(self, *, rate: int = -1) -> None:
        self.rate = max(-10, min(10, rate))

    @classmethod
    def is_available(cls) -> bool:
        return sys.platform.startswith("win")

    def synthesize(self, *, text: str, output_path: Path, language: str) -> SpeechSynthesisResult:
        output_path = output_path.with_suffix(".wav")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        escaped_path = str(output_path).replace("'", "''")
        escaped_text = text.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$speaker.Rate = {self.rate};"
            f"$speaker.SetOutputToWaveFile('{escaped_path}');"
            f"$speaker.Speak('{escaped_text}');"
            "$speaker.Dispose();"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "Unknown Windows SAPI error"
            raise RuntimeError(stderr) from exc

        with wave.open(str(output_path), "rb") as wav_file:
            duration = wav_file.getnframes() / float(wav_file.getframerate())
        return SpeechSynthesisResult(
            path=output_path,
            duration_seconds=round(duration, 2),
            provider_name=self.provider_name,
        )
