from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.models import ChannelConfig


@pytest.fixture()
def temp_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        base_dir=tmp_path,
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        ffmpeg_bin="ffmpeg",
    )
    settings.ensure_runtime_paths()
    prompts_dir = settings.prompts_dir
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "script_prompt.txt").write_text("script prompt", encoding="utf-8")
    (prompts_dir / "scene_prompt.txt").write_text("scene prompt", encoding="utf-8")
    (prompts_dir / "metadata_prompt.txt").write_text("metadata prompt", encoding="utf-8")
    return settings


@pytest.fixture()
def sample_channel() -> ChannelConfig:
    return ChannelConfig(
        channel_id="demo_channel",
        channel_name="Demo Channel",
        niche="demo niche",
        platforms=["youtube"],
        language="en",
        audience="busy tech viewers",
        videos_per_day=2,
        active=True,
        prompt_style="clear and concise",
        output_folder="demo_channel",
        visual_theme="neon tech editorial",
        cta_template="Follow for more quick tech facts.",
        script_style_notes="keep the tone smart, fast, and specific",
        seed_topics=["Topic A", "Topic B"],
        hashtags=["#Demo"],
    )
