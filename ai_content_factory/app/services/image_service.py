from __future__ import annotations

from app.config import Settings
from app.integrations.image_generators.base import ImageGenerator
from app.models import ChannelConfig, ScenePlan


class ImageService:
    def __init__(self, settings: Settings, generator: ImageGenerator) -> None:
        self.settings = settings
        self.generator = generator

    def generate_scene_images(self, *, channel: ChannelConfig, scene_plan: ScenePlan) -> ScenePlan:
        job_dir = self.settings.images_dir / channel.output_folder / scene_plan.job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        for scene in scene_plan.scenes:
            output_path = job_dir / f"scene_{scene.scene_index:02d}.png"
            self.generator.generate(
                prompt=scene.image_prompt,
                topic=scene_plan.topic,
                scene_text=scene.scene_text,
                headline_text=scene.headline_text,
                supporting_text=scene.supporting_text,
                icon_key=scene.icon_key,
                background_style=scene.background_style,
                layout_variant=scene.layout_variant,
                channel_name=channel.channel_name,
                visual_theme=channel.visual_theme,
                scene_index=scene.scene_index,
                output_path=output_path,
                width=self.settings.default_video_width,
                height=self.settings.default_video_height,
            )
            scene.image_path = str(output_path)
        return scene_plan
