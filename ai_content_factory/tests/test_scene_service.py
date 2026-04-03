from __future__ import annotations

from app.models import ScriptDraft
from app.services.scene_service import SceneService
from app.utils import utcnow


def test_scene_split_produces_short_form_visual_scenes(temp_settings, sample_channel) -> None:
    service = SceneService(temp_settings)
    script = ScriptDraft(
        job_id="job-scenes",
        channel_id=sample_channel.channel_id,
        topic="Interesting Topic",
        language="en",
        hook="This topic changes more than you think.",
        body=(
            "First show the simple cause. "
            "Then show one clear example people can picture. "
            "That makes the takeaway easier to remember."
        ),
        cta="Follow for more facts.",
        created_at=utcnow(),
    )

    scene_plan, path = service.plan_scenes(channel=sample_channel, script=script)

    assert path.exists()
    assert 4 <= len(scene_plan.scenes) <= 5
    assert scene_plan.scenes[0].voice_text
    assert scene_plan.scenes[0].headline_text
    assert scene_plan.scenes[1].supporting_text
    assert scene_plan.scenes[1].icon_key
    assert scene_plan.scenes[1].visual_source == "motion_background"
