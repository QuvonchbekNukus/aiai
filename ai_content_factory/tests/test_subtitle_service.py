from __future__ import annotations

from app.models import Scene, ScenePlan
from app.services.subtitle_service import SubtitleService
from app.utils import utcnow


def test_subtitle_timing_generation(temp_settings, sample_channel) -> None:
    service = SubtitleService(temp_settings)
    scene_plan = ScenePlan(
        job_id="job-subtitles",
        channel_id=sample_channel.channel_id,
        topic="Timing Topic",
        created_at=utcnow(),
        scenes=[
            Scene(
                scene_index=1,
                scene_text="Intro",
                image_prompt="Intro visual",
                voice_text="First line.",
                duration_seconds=1.5,
            ),
            Scene(
                scene_index=2,
                scene_text="Outro",
                image_prompt="Outro visual",
                voice_text="Second line.",
                duration_seconds=2.0,
            ),
        ],
    )

    subtitle_path = service.generate_subtitles(channel=sample_channel, scene_plan=scene_plan)
    content = subtitle_path.read_text(encoding="utf-8")

    assert subtitle_path.suffix == ".ass"
    assert "Dialogue: 0,0:00:00.00,0:00:01.50" in content
    assert "Dialogue: 0,0:00:01.50,0:00:03.50" in content
    assert "{\\c&H004CE7FF&\\b1}" in content
