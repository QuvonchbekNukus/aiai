from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, Request
from pydantic import BaseModel

from app.config import get_settings
from app.logger import configure_logging
from app.pipelines.content_pipeline import ContentPipeline
from app.scheduler.scheduler import PipelineScheduler


class RunOnceRequest(BaseModel):
    channel_id: str | None = None


class AppContainer:
    def __init__(self) -> None:
        self.settings = get_settings()
        configure_logging(self.settings)
        self.pipeline = ContentPipeline.build(self.settings)
        self.scheduler = PipelineScheduler(
            settings=self.settings,
            pipeline=self.pipeline,
            channel_service=self.pipeline.channel_service,
        )
        self.scheduler.rebuild_jobs(run_immediately=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = AppContainer()
    app.state.container = container
    if container.settings.scheduler_autostart:
        container.scheduler.start()
    yield
    container.scheduler.shutdown()


app = FastAPI(title="AI Content Factory", version="0.1.0", lifespan=lifespan)


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


@app.get("/health")
def health(request: Request) -> dict[str, object]:
    container = get_container(request)
    return {
        "status": "ok",
        "app_env": container.settings.app_env,
        "ffmpeg_bin": container.settings.ffmpeg_bin,
        "scheduler_running": container.scheduler.scheduler.running,
    }


@app.post("/run-once")
def run_once(request: Request, payload: RunOnceRequest | None = Body(default=None)) -> dict[str, object]:
    container = get_container(request)
    effective_payload = payload or RunOnceRequest()
    results = container.pipeline.run_once(channel_id=effective_payload.channel_id)
    return {
        "count": len(results),
        "results": [result.model_dump(mode="json") for result in results],
    }


@app.get("/channels")
def list_channels(request: Request) -> dict[str, object]:
    container = get_container(request)
    channels = container.pipeline.channel_service.get_channels()
    if not channels:
        channels = container.pipeline.channel_service.load_channels()
    return {
        "count": len(channels),
        "channels": [channel.model_dump(mode="json") for channel in channels],
    }


@app.post("/channels/reload-config")
def reload_channels(request: Request) -> dict[str, object]:
    container = get_container(request)
    channels = container.pipeline.channel_service.reload_channels()
    scheduled_jobs = container.scheduler.rebuild_jobs(run_immediately=False)
    return {
        "count": len(channels),
        "channels": [channel.model_dump(mode="json") for channel in channels],
        "scheduled_jobs": scheduled_jobs,
    }
