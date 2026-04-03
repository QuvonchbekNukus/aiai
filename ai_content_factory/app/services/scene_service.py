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
        segments = self._scene_segments(script)
        scenes: list[Scene] = []
        for index, segment in enumerate(segments, start=1):
            role = self._scene_role(index=index, scene_count=len(segments))
            icon_key = self._pick_icon_key(segment=segment, topic=script.topic, channel=channel)
            layout_variant = self._pick_layout_variant(index=index)
            background_style = self._pick_background_style(role=role, icon_key=icon_key, index=index)
            headline_text = self._headline_from_segment(segment=segment, topic=script.topic, role=role)
            supporting_text = self._supporting_text_from_segment(segment)
            scenes.append(
                Scene(
                    scene_index=index,
                    scene_text=headline_text,
                    image_prompt=self._build_image_prompt(
                        segment=segment,
                        topic=script.topic,
                        channel=channel,
                        role=role,
                        icon_key=icon_key,
                        background_style=background_style,
                        layout_variant=layout_variant,
                    ),
                    voice_text=segment,
                    duration_seconds=self._scene_duration(
                        segment=segment,
                        role=role,
                        scene_index=index - 1,
                        scene_count=len(segments),
                    ),
                    headline_text=headline_text,
                    supporting_text=supporting_text,
                    icon_key=icon_key,
                    background_style=background_style,
                    layout_variant=layout_variant,
                    emphasis_text=self._pick_emphasis_text(segment),
                    visual_source="motion_background",
                )
            )

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

    def _scene_segments(self, script: ScriptDraft) -> list[str]:
        segments = [script.hook, *split_sentences(script.body), script.cta]
        return [segment.strip() for segment in segments if segment.strip()]

    def _scene_role(self, *, index: int, scene_count: int) -> str:
        if index == 1:
            return "hook"
        if index == scene_count:
            return "cta"
        return "body"

    def _scene_duration(self, *, segment: str, role: str, scene_index: int, scene_count: int) -> float:
        base_duration = estimate_duration_seconds(segment, words_per_minute=128, minimum=2.6)
        if role == "hook":
            return round(max(self.settings.hook_screen_duration_seconds + 0.6, min(base_duration * 1.04, 3.6)), 2)
        if role == "cta":
            return round(max(self.settings.cta_end_screen_duration_seconds + 0.8, min(base_duration * 1.02, 3.2)), 2)

        rhythm = scene_index % 3
        factors = (1.0, 1.08, 1.02)
        minimums = (3.2, 3.45, 3.3)
        return round(max(minimums[rhythm], min(base_duration * factors[rhythm], 5.4)), 2)

    def _build_image_prompt(
        self,
        *,
        segment: str,
        topic: str,
        channel: ChannelConfig,
        role: str,
        icon_key: str,
        background_style: str,
        layout_variant: str,
    ) -> str:
        return (
            f"Vertical 9:16 short-video motion background for {topic}. "
            f"Scene role: {role}. Scene focus: {segment}. "
            f"Niche: {channel.niche}. Audience: {channel.audience}. "
            f"Style: {channel.prompt_style}. Visual theme: {channel.visual_theme}. "
            f"Use icon {icon_key}, background style {background_style}, layout {layout_variant}. "
            "Avoid plain text-only slide visuals."
        )

    def _headline_from_segment(self, *, segment: str, topic: str, role: str) -> str:
        source = f"{topic} {segment}".lower()
        headline_map = {
            "wi-fi": {
                "hook": "Wi-Fi Feels Slower",
                "body": "Too Much Channel Traffic",
                "cta": "Watch For More Tech Facts",
            },
            "wifi": {
                "hook": "Wi-Fi Feels Slower",
                "body": "Too Much Channel Traffic",
                "cta": "Watch For More Tech Facts",
            },
            "battery": {
                "hook": "Battery Drain Starts Here",
                "body": "Background Apps Keep Working",
                "cta": "Watch For More Tech Facts",
            },
            "smartphone": {
                "hook": "Hidden Phone Tools",
                "body": "Small Settings Save Time",
                "cta": "Watch For More Tech Facts",
            },
            "phone": {
                "hook": "Hidden Phone Tools",
                "body": "Small Settings Save Time",
                "cta": "Watch For More Tech Facts",
            },
            "qr": {
                "hook": "A QR Code Can Trick You",
                "body": "Check The Link First",
                "cta": "Watch For More Tech Facts",
            },
            "ai": {
                "hook": "Small AI Saves Minutes",
                "body": "Speed Beats Busywork",
                "cta": "Watch For More Tech Facts",
            },
        }

        for keyword, variants in headline_map.items():
            if keyword in source:
                return variants.get(role, variants["body"])

        words = [word for word in segment.replace(".", "").split() if len(word) > 2][:4]
        headline = " ".join(words).title().strip()
        return headline or "Quick Short Breakdown"

    def _supporting_text_from_segment(self, segment: str) -> str:
        words = segment.replace("\n", " ").split()
        supporting = " ".join(words[:10]).strip()
        if supporting and supporting[-1] not in ".!?":
            supporting += "."
        return supporting

    def _pick_icon_key(self, *, segment: str, topic: str, channel: ChannelConfig) -> str:
        source = f"{topic} {segment} {channel.niche}".lower()
        icon_map = {
            "wi-fi": "wifi",
            "wifi": "wifi",
            "router": "wifi",
            "battery": "battery",
            "charge": "battery",
            "smartphone": "phone",
            "phone": "phone",
            "app": "phone",
            "qr": "qr",
            "security": "shield",
            "shield": "shield",
            "ai": "spark",
            "model": "spark",
            "history": "globe",
            "castle": "shield",
            "rome": "globe",
            "map": "globe",
            "focus": "target",
            "habit": "bolt",
            "productivity": "chart",
            "time": "clock",
        }
        for keyword, icon in icon_map.items():
            if keyword in source:
                return icon
        return "spark"

    def _pick_background_style(self, *, role: str, icon_key: str, index: int) -> str:
        if role == "hook":
            return "pulse"
        if role == "cta":
            return "glow"
        styles = {
            "wifi": "signal",
            "battery": "charge",
            "phone": "grid",
            "qr": "scan",
            "shield": "shield",
            "clock": "orbit",
            "chart": "bars",
            "target": "focus",
        }
        return styles.get(icon_key, ("grid", "orbit", "bars")[index % 3])

    def _pick_layout_variant(self, *, index: int) -> str:
        variants = (
            "split_left",
            "split_right",
            "stacked",
            "focus",
            "ticker",
        )
        return variants[(index - 1) % len(variants)]

    def _pick_emphasis_text(self, segment: str) -> str | None:
        stop_words = {"the", "and", "for", "with", "that", "this", "your", "from", "into", "more"}
        candidates = [word.strip(".,!?").upper() for word in segment.split() if len(word) > 3]
        for candidate in candidates:
            if candidate.lower() not in stop_words:
                return candidate
        return None
