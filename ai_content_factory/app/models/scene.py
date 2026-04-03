from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Scene(BaseModel):
    scene_index: int = Field(ge=1)
    scene_text: str
    image_prompt: str
    voice_text: str
    duration_seconds: float = Field(gt=0)
    headline_text: str = ""
    supporting_text: str = ""
    icon_key: str = "spark"
    background_style: str = "motion_gradient"
    layout_variant: str = "split_left"
    emphasis_text: str | None = None
    visual_source: str = "motion_background"
    image_path: str | None = None
    audio_path: str | None = None


class ScenePlan(BaseModel):
    job_id: str
    channel_id: str
    topic: str
    scenes: list[Scene]
    created_at: datetime
