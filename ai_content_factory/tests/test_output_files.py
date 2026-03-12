from __future__ import annotations

from app.services.script_service import ScriptService
from app.services.topic_service import TopicService


def test_output_file_creation(temp_settings, sample_channel) -> None:
    topic_service = TopicService(temp_settings)
    topic = topic_service.generate_topic(sample_channel)

    service = ScriptService(temp_settings)
    script, path = service.generate_script(channel=sample_channel, topic=topic, job_id="job-output")

    assert path.exists()
    assert path.with_suffix(".txt").exists()
    assert script.topic == topic.topic

