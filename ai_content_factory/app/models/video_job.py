from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadRecord(BaseModel):
    platform: str
    upload_id: str
    status: str
    uploaded_at: datetime


class VideoJob(BaseModel):
    job_id: str
    channel_id: str
    topic: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    script_path: str | None = None
    scene_path: str | None = None
    subtitle_path: str | None = None
    metadata_path: str | None = None
    video_path: str | None = None
    uploads: list[UploadRecord] = Field(default_factory=list)


class PipelineRunResult(BaseModel):
    job: VideoJob
    published: bool = False

