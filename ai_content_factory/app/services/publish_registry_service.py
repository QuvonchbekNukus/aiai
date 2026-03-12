from __future__ import annotations

from app.config import Settings
from app.models import ChannelConfig, VideoJob, VideoMetadata
from app.utils import read_json_file, utcnow, write_json_file


class PublishRegistryService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def record_success(
        self,
        *,
        channel: ChannelConfig,
        job: VideoJob,
        metadata: VideoMetadata,
    ) -> None:
        payload = read_json_file(self.settings.published_videos_file, default=[])
        payload.append(
            {
                "recorded_at": utcnow().isoformat(),
                "channel_id": channel.channel_id,
                "channel_name": channel.channel_name,
                "job": job.model_dump(mode="json"),
                "metadata": metadata.model_dump(mode="json"),
                "status": "published" if job.uploads else "ready",
            }
        )
        write_json_file(self.settings.published_videos_file, payload)

    def record_failure(
        self,
        *,
        channel: ChannelConfig,
        job: VideoJob,
        error: Exception,
    ) -> None:
        payload = read_json_file(self.settings.failed_jobs_file, default=[])
        payload.append(
            {
                "failed_at": utcnow().isoformat(),
                "channel_id": channel.channel_id,
                "channel_name": channel.channel_name,
                "job": job.model_dump(mode="json"),
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        write_json_file(self.settings.failed_jobs_file, payload)

