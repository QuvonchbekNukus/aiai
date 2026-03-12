from __future__ import annotations

from app.services.topic_service import TopicService
from app.utils import read_json_file, write_json_file


def test_topic_duplicate_check(temp_settings, sample_channel) -> None:
    write_json_file(
        temp_settings.used_topics_file,
        {"version": 1, "channels": {sample_channel.channel_id: ["Topic A"]}},
    )
    service = TopicService(temp_settings)

    first = service.generate_topic(sample_channel)
    second = service.generate_topic(sample_channel)
    registry = read_json_file(temp_settings.used_topics_file, default={})

    assert first.topic == "Topic B"
    assert second.topic not in {"Topic A", "Topic B"}
    assert len(registry["channels"][sample_channel.channel_id]) == 3

