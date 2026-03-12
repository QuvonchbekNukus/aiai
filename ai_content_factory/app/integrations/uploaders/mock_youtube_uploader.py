from __future__ import annotations

from pathlib import Path

from app.integrations.uploaders.base import UploadResponse, Uploader
from app.models import ChannelConfig, VideoMetadata
from app.utils import slugify, utcnow


class MockYouTubeUploader(Uploader):
    def upload(
        self,
        *,
        channel: ChannelConfig,
        video_path: Path,
        metadata: VideoMetadata,
    ) -> UploadResponse:
        # TODO: Replace with YouTube Data API v3 integration and OAuth credential flow.
        suffix = utcnow().strftime("%Y%m%d%H%M%S")
        upload_id = f"yt_{channel.channel_id}_{slugify(metadata.title, 24)}_{suffix}"
        return UploadResponse(platform="youtube", upload_id=upload_id, status="mock_uploaded")

