from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.models import ChannelConfig, ScenePlan
from app.utils import format_srt_timestamp, split_sentences, wrap_text, write_text_file


class SubtitleService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_subtitles(self, *, channel: ChannelConfig, scene_plan: ScenePlan) -> Path:
        channel_dir = self.settings.subtitles_dir / channel.output_folder
        channel_dir.mkdir(parents=True, exist_ok=True)
        subtitle_path = channel_dir / f"{scene_plan.job_id}.srt"

        cursor = self.settings.hook_screen_duration_seconds
        blocks: list[str] = []
        block_index = 1
        for scene in scene_plan.scenes:
            scene_start = cursor
            scene_end = cursor + scene.duration_seconds
            chunks = self._chunk_caption(scene.voice_text)
            total_words = sum(max(1, len(chunk.split())) for chunk in chunks)
            running_start = scene_start
            remaining_words = total_words

            for chunk_position, chunk in enumerate(chunks):
                chunk_words = max(1, len(chunk.split()))
                if chunk_position == len(chunks) - 1 or remaining_words <= chunk_words:
                    running_end = scene_end
                else:
                    share = scene.duration_seconds * (chunk_words / max(1, remaining_words))
                    running_end = min(scene_end, running_start + max(0.6, share))

                blocks.append(
                    "\n".join(
                        [
                            str(block_index),
                            f"{format_srt_timestamp(running_start)} --> {format_srt_timestamp(running_end)}",
                            self._format_caption(chunk),
                        ]
                    )
                )
                block_index += 1
                running_start = running_end
                remaining_words -= chunk_words

            cursor = scene_end

        write_text_file(subtitle_path, "\n\n".join(blocks) + "\n")
        return subtitle_path

    def _format_caption(self, text: str) -> str:
        lines = wrap_text(text, width=20).splitlines()
        if len(lines) <= 2:
            return "\n".join(lines)
        return "\n".join([lines[0], " ".join(lines[1:])])

    def _chunk_caption(self, text: str) -> list[str]:
        normalized_sentences = split_sentences(text) or [text.strip()]
        chunks: list[str] = []
        for sentence in normalized_sentences:
            words = sentence.split()
            if len(words) <= 6:
                chunks.append(sentence.strip())
                continue

            chunk_size = 4 if len(words) >= 12 else 5
            for index in range(0, len(words), chunk_size):
                chunks.append(" ".join(words[index : index + chunk_size]).strip())

        return [chunk for chunk in chunks if chunk]
