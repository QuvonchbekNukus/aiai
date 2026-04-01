from __future__ import annotations

from pathlib import Path

from app.integrations.uploaders.base import UploadResponse, Uploader
from app.models import ChannelConfig, VideoMetadata
from app.utils import slugify, utcnow


class MockInstagramUploader(Uploader):
    def upload(
        self,
        *,
        channel: ChannelConfig,
        video_path: Path,
        metadata: VideoMetadata,
        metadata_path: Path | None = None,
    ) -> UploadResponse:
        # TODO: Replace with Instagram Graph API publishing flow.
        suffix = utcnow().strftime("%Y%m%d%H%M%S")
        upload_id = f"ig_{channel.channel_id}_{slugify(metadata.title, 24)}_{suffix}"
        return UploadResponse(platform="instagram", upload_id=upload_id, status="mock_uploaded")
