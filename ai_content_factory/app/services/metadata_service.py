from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.models import ChannelConfig, ScriptDraft, VideoMetadata
from app.utils import load_text_file, unique_strings, utcnow, write_json_file


class MetadataService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.prompt_template = load_text_file(self.settings.prompts_dir / "metadata_prompt.txt")

    def generate_metadata(
        self,
        *,
        channel: ChannelConfig,
        script: ScriptDraft,
    ) -> tuple[VideoMetadata, Path]:
        hashtags = self._build_hashtags(channel, script.topic)
        metadata = VideoMetadata(
            title=self._build_title(script.topic),
            description=self._build_description(channel, script),
            hashtags=hashtags,
            generated_at=utcnow(),
        )

        channel_dir = self.settings.metadata_dir / channel.output_folder
        channel_dir.mkdir(parents=True, exist_ok=True)
        json_path = channel_dir / f"{script.job_id}_metadata.json"
        payload = metadata.model_dump(mode="json")
        payload["prompt_template"] = self.prompt_template
        write_json_file(json_path, payload)
        return metadata, json_path

    def _build_title(self, topic: str) -> str:
        title = f"{topic} in under 60 seconds"
        return title[:100]

    def _build_description(self, channel: ChannelConfig, script: ScriptDraft) -> str:
        return (
            f"Topic: {script.topic}\n"
            f"Niche: {channel.niche}\n"
            f"Hook: {script.hook}\n"
            f"CTA: {script.cta}"
        )

    def _build_hashtags(self, channel: ChannelConfig, topic: str) -> list[str]:
        generated = [f"#{part.title().replace('-', '')}" for part in topic.split()[:3]]
        return unique_strings(channel.hashtags + generated)

