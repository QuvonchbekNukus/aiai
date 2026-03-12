from __future__ import annotations

from app.models import ChannelConfig
from app.pipelines.content_pipeline import ContentPipeline
from app.scheduler.scheduler import PipelineScheduler
from app.utils import write_json_file


def test_scheduler_builds_jobs_for_active_channels(temp_settings) -> None:
    channels = [
        ChannelConfig(
            channel_id="alpha",
            channel_name="Alpha",
            niche="tech",
            platforms=["youtube"],
            videos_per_day=3,
            output_folder="alpha",
        ),
        ChannelConfig(
            channel_id="beta",
            channel_name="Beta",
            niche="history",
            platforms=["instagram"],
            videos_per_day=2,
            output_folder="beta",
        ),
    ]
    write_json_file(
        temp_settings.channels_file,
        [channel.model_dump(mode="json") for channel in channels],
    )
    pipeline = ContentPipeline.build(temp_settings)
    scheduler = PipelineScheduler(
        settings=pipeline.settings,
        pipeline=pipeline,
        channel_service=pipeline.channel_service,
    )

    job_ids = scheduler.rebuild_jobs(run_immediately=False)

    assert "channel::alpha" in job_ids
    assert "channel::beta" in job_ids
    scheduler.shutdown()
