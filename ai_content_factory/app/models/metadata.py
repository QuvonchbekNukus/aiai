from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str
    hashtags: list[str] = Field(default_factory=list)
    generated_at: datetime

