from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

from app.integrations.tts.base import SpeechSynthesisResult, TextToSpeechProvider


class PiperTTSProvider(TextToSpeechProvider):
    provider_name = "piper"

    def __init__(
        self,
        *,
        binary: str,
        model_path: Path,
        speaker: int | None = None,
    ) -> None:
        self.binary = binary
        self.model_path = model_path
        self.speaker = speaker

    @classmethod
    def is_available(cls, *, binary: str, model_path: Path | None) -> bool:
        if model_path is None:
            return False
        executable = shutil.which(binary) or (Path(binary) if Path(binary).exists() else None)
        return bool(executable and model_path.exists())

    def synthesize(self, *, text: str, output_path: Path, language: str) -> SpeechSynthesisResult:
        output_path = output_path.with_suffix(".wav")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.binary,
            "--model",
            str(self.model_path),
            "--output_file",
            str(output_path),
        ]
        if self.speaker is not None:
            command.extend(["--speaker", str(self.speaker)])

        try:
            subprocess.run(
                command,
                input=text,
                text=True,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "Unknown Piper error"
            raise RuntimeError(stderr) from exc

        with wave.open(str(output_path), "rb") as wav_file:
            duration = wav_file.getnframes() / float(wav_file.getframerate())
        return SpeechSynthesisResult(
            path=output_path,
            duration_seconds=round(duration, 2),
            provider_name=self.provider_name,
        )
