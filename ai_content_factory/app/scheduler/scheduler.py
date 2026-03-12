from __future__ import annotations

from datetime import datetime
from threading import Event

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import Settings, get_settings
from app.logger import configure_logging, get_logger
from app.pipelines.content_pipeline import ContentPipeline
from app.scheduler.jobs import run_single_channel
from app.services.channel_service import ChannelService


class PipelineScheduler:
    def __init__(
        self,
        *,
        settings: Settings,
        pipeline: ContentPipeline,
        channel_service: ChannelService,
    ) -> None:
        self.settings = settings
        self.pipeline = pipeline
        self.channel_service = channel_service
        self.scheduler = BackgroundScheduler(timezone=self.settings.scheduler_timezone)
        self.logger = get_logger(self.__class__.__name__)

    def rebuild_jobs(self, *, run_immediately: bool = False) -> list[str]:
        self.scheduler.remove_all_jobs()
        channels = self.channel_service.load_channels()
        active_channels = [channel for channel in channels if channel.active]
        job_ids: list[str] = []

        for channel in active_channels:
            interval_minutes = max(1, int((24 * 60) / channel.videos_per_day))
            next_run_time = datetime.now().astimezone() if run_immediately else None
            job = self.scheduler.add_job(
                run_single_channel,
                trigger="interval",
                minutes=interval_minutes,
                id=f"channel::{channel.channel_id}",
                replace_existing=True,
                kwargs={"pipeline": self.pipeline, "channel_id": channel.channel_id},
                next_run_time=next_run_time,
            )
            job_ids.append(job.id)
            self.logger.info(
                "Scheduled channel %s every %s minutes.",
                channel.channel_id,
                interval_minutes,
            )
        return job_ids

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Scheduler started.")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.logger.info("Scheduler stopped.")


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    pipeline = ContentPipeline.build(settings)
    scheduler = PipelineScheduler(
        settings=settings,
        pipeline=pipeline,
        channel_service=pipeline.channel_service,
    )
    scheduler.rebuild_jobs(run_immediately=False)
    scheduler.start()

    stopper = Event()
    logger = get_logger(__name__)
    logger.info("Scheduler is running. Press Ctrl+C to stop.")
    try:
        stopper.wait()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down scheduler.")
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
