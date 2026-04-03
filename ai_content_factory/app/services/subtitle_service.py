from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.models import ChannelConfig, ScenePlan
from app.utils import format_ass_timestamp, split_sentences, wrap_text, write_text_file


class SubtitleService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_subtitles(self, *, channel: ChannelConfig, scene_plan: ScenePlan) -> Path:
        channel_dir = self.settings.subtitles_dir / channel.output_folder
        channel_dir.mkdir(parents=True, exist_ok=True)
        subtitle_path = channel_dir / f"{scene_plan.job_id}.ass"

        cursor = 0.0
        blocks: list[str] = []
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
                    remaining_duration = max(0.55, scene_end - running_start)
                    share = remaining_duration * (chunk_words / max(1, remaining_words))
                    running_end = min(scene_end, running_start + max(0.55, share))

                blocks.append(
                    "Dialogue: 0,"
                    f"{format_ass_timestamp(running_start)},"
                    f"{format_ass_timestamp(running_end)},"
                    f"Shorts,,0,0,0,,{self._format_caption(chunk)}"
                )
                running_start = running_end
                remaining_words -= chunk_words

            cursor = scene_end

        write_text_file(subtitle_path, self._ass_header() + "\n".join(blocks) + "\n")
        return subtitle_path

    def _ass_header(self) -> str:
        return (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Shorts,Bahnschrift SemiBold,42,&H00FFFFFF,&H004CE7FF,&H00000000,&H00000000,"
            "-1,0,0,0,100,100,0.2,0,1,3.4,0,2,92,92,152,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

    def _format_caption(self, text: str) -> str:
        lines = wrap_text(self._highlight_keywords(text), width=16).splitlines()
        if len(lines) <= 2:
            return r"\N".join(lines)
        return r"\N".join([lines[0], " ".join(lines[1:])])

    def _chunk_caption(self, text: str) -> list[str]:
        normalized_sentences = split_sentences(text) or [text.strip()]
        chunks: list[str] = []
        for sentence in normalized_sentences:
            words = sentence.split()
            if len(words) <= 5:
                chunks.append(sentence.strip())
                continue

            chunk_size = 3 if len(words) <= 9 else 4
            for index in range(0, len(words), chunk_size):
                chunks.append(" ".join(words[index : index + chunk_size]).strip())

        return [chunk for chunk in chunks if chunk]

    def _highlight_keywords(self, text: str) -> str:
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "your",
            "from",
            "they",
            "them",
            "into",
            "more",
            "just",
        }
        words = text.split()
        longest = ""
        for word in words:
            cleaned = word.strip(".,!?").lower()
            if len(cleaned) <= 3 or cleaned in stop_words:
                continue
            if len(cleaned) > len(longest):
                longest = cleaned
        if not longest:
            return self._escape_ass(text.upper())

        highlighted_words: list[str] = []
        replaced = False
        for word in words:
            cleaned = word.strip(".,!?").lower()
            if not replaced and cleaned == longest:
                suffix = word[len(word.rstrip(".,!?")) :]
                base = word.rstrip(".,!?").upper()
                highlighted_words.append(r"{\c&H004CE7FF&\b1}" + self._escape_ass(base) + r"{\c&H00FFFFFF&\b0}" + suffix)
                replaced = True
            else:
                highlighted_words.append(self._escape_ass(word.upper()))
        return " ".join(highlighted_words)

    def _escape_ass(self, text: str) -> str:
        return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
