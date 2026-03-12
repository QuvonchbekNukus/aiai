from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SpeechSynthesisResult:
    path: Path
    duration_seconds: float
    provider_name: str


class TextToSpeechProvider(ABC):
    @abstractmethod
    def synthesize(self, *, text: str, output_path: Path, language: str) -> SpeechSynthesisResult:
        raise NotImplementedError
