from __future__ import annotations

from app.logger import get_logger
from app.pipelines.content_pipeline import ContentPipeline

logger = get_logger(__name__)


def run_all_active_channels(pipeline: ContentPipeline) -> None:
    logger.info("Running scheduled batch for all active channels.")
    pipeline.run_once()


def run_single_channel(pipeline: ContentPipeline, channel_id: str) -> None:
    logger.info("Running scheduled job for channel %s.", channel_id)
    pipeline.run_once(channel_id=channel_id)

