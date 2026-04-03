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
        headline_text: str | None = None,
        supporting_text: str | None = None,
        icon_key: str | None = None,
        background_style: str | None = None,
        layout_variant: str | None = None,
        channel_name: str,
        visual_theme: str,
        scene_index: int,
        output_path: Path,
        width: int,
        height: int,
    ) -> GeneratedImageResult:
        raise NotImplementedError
