from __future__ import annotations

from app.integrations.script_generators.deterministic_generator import DeterministicScriptGenerator
from app.services.script_service import ScriptService
from app.services.topic_service import TopicService


def test_script_service_fallback_creates_short_form_script(temp_settings, sample_channel) -> None:
    topic = TopicService(temp_settings).generate_topic(sample_channel)
    service = ScriptService(temp_settings, generators=[DeterministicScriptGenerator()])

    script, path = service.generate_script(channel=sample_channel, topic=topic, job_id="job-script")

    assert path.exists()
    assert script.provider_name == "deterministic_fallback"
    assert len(script.hook.split()) <= 14
    assert len(script.cta.split()) <= 8
    assert 38 <= script.word_count() <= 85

