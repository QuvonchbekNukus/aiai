from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.models import ChannelConfig, ScenePlan
from app.utils import format_srt_timestamp, wrap_text, write_text_file


class SubtitleService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_subtitles(self, *, channel: ChannelConfig, scene_plan: ScenePlan) -> Path:
        channel_dir = self.settings.subtitles_dir / channel.output_folder
        channel_dir.mkdir(parents=True, exist_ok=True)
        subtitle_path = channel_dir / f"{scene_plan.job_id}.srt"

        cursor = 0.0
        blocks: list[str] = []
        for index, scene in enumerate(scene_plan.scenes, start=1):
            start = cursor
            end = cursor + scene.duration_seconds
            blocks.append(
                "\n".join(
                    [
                        str(index),
                        f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}",
                        self._format_caption(scene.voice_text),
                    ]
                )
            )
            cursor = end

        write_text_file(subtitle_path, "\n\n".join(blocks) + "\n")
        return subtitle_path

    def _format_caption(self, text: str) -> str:
        lines = wrap_text(text, width=28).splitlines()
        if len(lines) <= 2:
            return "\n".join(lines)
        return "\n".join([lines[0], " ".join(lines[1:])])
