from __future__ import annotations

from app.config import Settings
from app.models import ChannelConfig, TopicRecord
from app.utils import read_json_file, unique_strings, utcnow, write_json_file


class TopicService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_topic(self, channel: ChannelConfig) -> TopicRecord:
        registry = read_json_file(
            self.settings.used_topics_file,
            default={"version": 1, "channels": {}},
        )
        channels_bucket = registry.setdefault("channels", {})
        used_topics = channels_bucket.setdefault(channel.channel_id, [])
        used_normalized = {str(item).strip().lower() for item in used_topics}

        selected_topic: str | None = None
        source = "seed"
        for topic in unique_strings(channel.seed_topics):
            if topic.strip().lower() not in used_normalized:
                selected_topic = topic.strip()
                break

        if not selected_topic:
            source = "generated"
            candidate_index = len(used_topics) + 1
            while True:
                candidate = f"{channel.niche.title()} angle {candidate_index}"
                if candidate.lower() not in used_normalized:
                    selected_topic = candidate
                    break
                candidate_index += 1

        used_topics.append(selected_topic)
        write_json_file(self.settings.used_topics_file, registry)

        return TopicRecord(
            channel_id=channel.channel_id,
            topic=selected_topic,
            source=source,
            prompt_style=channel.prompt_style,
            created_at=utcnow(),
        )

