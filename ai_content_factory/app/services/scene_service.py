from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.models import ChannelConfig, Scene, ScenePlan, ScriptDraft
from app.utils import estimate_duration_seconds, load_text_file, split_sentences, utcnow, write_json_file


class SceneService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.prompt_template = load_text_file(self.settings.prompts_dir / "scene_prompt.txt")

    def plan_scenes(
        self,
        *,
        channel: ChannelConfig,
        script: ScriptDraft,
    ) -> tuple[ScenePlan, Path]:
        raw_segments = [script.hook, *split_sentences(script.body), script.cta]
        segments = self._rebalance_segments([segment for segment in raw_segments if segment.strip()])

        scenes = [
            Scene(
                scene_index=index,
                scene_text=self._build_scene_text(segment),
                image_prompt=self._build_image_prompt(segment, script.topic, channel),
                voice_text=segment,
                duration_seconds=self._scene_duration(
                    segment=segment,
                    scene_index=index - 1,
                    scene_count=len(segments),
                ),
            )
            for index, segment in enumerate(segments, start=1)
        ]

        scene_plan = ScenePlan(
            job_id=script.job_id,
            channel_id=channel.channel_id,
            topic=script.topic,
            scenes=scenes,
            created_at=utcnow(),
        )

        channel_dir = self.settings.scenes_dir / channel.output_folder
        channel_dir.mkdir(parents=True, exist_ok=True)
        json_path = channel_dir / f"{script.job_id}_scenes.json"
        payload = scene_plan.model_dump(mode="json")
        payload["prompt_template"] = self.prompt_template
        write_json_file(json_path, payload)
        return scene_plan, json_path

    def save_scene_plan(self, *, channel: ChannelConfig, scene_plan: ScenePlan) -> Path:
        channel_dir = self.settings.scenes_dir / channel.output_folder
        channel_dir.mkdir(parents=True, exist_ok=True)
        json_path = channel_dir / f"{scene_plan.job_id}_scenes.json"
        payload = scene_plan.model_dump(mode="json")
        payload["prompt_template"] = self.prompt_template
        write_json_file(json_path, payload)
        return json_path

    def _rebalance_segments(self, segments: list[str]) -> list[str]:
        normalized = [segment.strip() for segment in segments if segment.strip()]
        while len(normalized) < 5:
            split_index = max(range(len(normalized)), key=lambda idx: len(normalized[idx].split()))
            parts = self._split_segment(normalized[split_index])
            if len(parts) == 1:
                break
            normalized.pop(split_index)
            for offset, part in enumerate(parts):
                normalized.insert(split_index + offset, part)

        while len(normalized) > 6:
            merge_index = min(range(len(normalized)), key=lambda idx: len(normalized[idx].split()))
            if merge_index == 0:
                normalized[1] = f"{normalized[0]} {normalized[1]}"
                normalized.pop(0)
            else:
                normalized[merge_index - 1] = f"{normalized[merge_index - 1]} {normalized[merge_index]}"
                normalized.pop(merge_index)
        return normalized

    def _split_segment(self, segment: str) -> list[str]:
        words = segment.split()
        if len(words) < 8:
            return [segment]
        midpoint = len(words) // 2
        return [" ".join(words[:midpoint]), " ".join(words[midpoint:])]

    def _build_scene_text(self, segment: str) -> str:
        return segment if len(segment) <= 82 else f"{segment[:79]}..."

    def _scene_duration(self, *, segment: str, scene_index: int, scene_count: int) -> float:
        base_duration = estimate_duration_seconds(segment, minimum=2.2)
        if scene_index == 0:
            return round(max(2.0, min(base_duration * 0.68, 2.7)), 2)
        if scene_index == scene_count - 1:
            return round(max(3.1, base_duration * 1.28), 2)

        rhythm = (scene_index - 1) % 3
        factors = (0.88, 0.96, 0.91)
        minimums = (2.1, 2.35, 2.2)
        return round(max(minimums[rhythm], base_duration * factors[rhythm]), 2)

    def _build_image_prompt(self, segment: str, topic: str, channel: ChannelConfig) -> str:
        return (
            f"Vertical 9:16 short video card for {topic}. "
            f"Scene focus: {segment}. "
            f"Niche: {channel.niche}. Audience: {channel.audience}. "
            f"Style: {channel.prompt_style}. Visual theme: {channel.visual_theme}."
        )
