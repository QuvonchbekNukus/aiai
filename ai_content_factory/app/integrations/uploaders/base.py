from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.models import ChannelConfig, VideoMetadata


@dataclass(slots=True)
class UploadResponse:
    platform: str
    upload_id: str
    status: str
    url: str | None = None


class Uploader(ABC):
    @abstractmethod
    def upload(
        self,
        *,
        channel: ChannelConfig,
        video_path: Path,
        metadata: VideoMetadata,
        metadata_path: Path | None = None,
    ) -> UploadResponse:
        raise NotImplementedError
