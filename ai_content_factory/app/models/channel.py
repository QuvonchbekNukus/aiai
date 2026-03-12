from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PlatformName(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"


class ChannelConfig(BaseModel):
    channel_id: str
    channel_name: str
    niche: str
    platforms: list[PlatformName]
    language: str = "en"
    audience: str = "curious viewers"
    videos_per_day: int = Field(default=3, ge=1, le=24)
    active: bool = True
    prompt_style: str = "concise, factual, curiosity-driven"
    output_folder: str = "default"
    visual_theme: str = "clean editorial cards"
    cta_template: str | None = None
    script_style_notes: str | None = None
    seed_topics: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    background_music_path: str | None = None
