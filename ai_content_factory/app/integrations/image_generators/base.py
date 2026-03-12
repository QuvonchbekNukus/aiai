from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GeneratedImageResult:
    path: Path
    width: int
    height: int


class ImageGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        prompt: str,
        topic: str,
        scene_text: str,
        channel_name: str,
        visual_theme: str,
        scene_index: int,
        output_path: Path,
        width: int,
        height: int,
    ) -> GeneratedImageResult:
        raise NotImplementedError
