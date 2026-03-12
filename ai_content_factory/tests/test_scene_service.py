from __future__ import annotations

from app.models import ScriptDraft
from app.services.scene_service import SceneService
from app.utils import utcnow


def test_scene_split_produces_5_to_8_scenes(temp_settings, sample_channel) -> None:
    service = SceneService(temp_settings)
    script = ScriptDraft(
        job_id="job-scenes",
        channel_id=sample_channel.channel_id,
        topic="Interesting Topic",
        language="en",
        hook="This topic looks obvious until one missing detail changes the whole story.",
        body=(
            "First explain the core reason people care. "
            "Then give one concrete example the audience can visualize instantly. "
            "Finally connect the example back to a practical takeaway for repeatable content."
        ),
        cta="Follow for more quick lessons.",
        created_at=utcnow(),
    )

    scene_plan, path = service.plan_scenes(channel=sample_channel, script=script)

    assert path.exists()
    assert 5 <= len(scene_plan.scenes) <= 8
    assert scene_plan.scenes[0].voice_text

