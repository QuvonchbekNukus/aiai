from __future__ import annotations

from hashlib import md5
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.integrations.image_generators.base import GeneratedImageResult, ImageGenerator
from app.utils import wrap_text


class MockImageGenerator(ImageGenerator):
    def generate(
        self,
        *,
        prompt: str,
        topic: str,
        scene_text: str,
        channel_name: str,
        visual_theme: str,
        scene_index: int,
        output_path: Path,
        width: int,
        height: int,
    ) -> GeneratedImageResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        background = self._color_from_prompt(prompt)
        image = Image.new("RGB", (width, height), background)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        overlay_margin = 80
        draw.rounded_rectangle(
            [
                (overlay_margin, height - 620),
                (width - overlay_margin, height - 180),
            ],
            radius=32,
            fill=(12, 12, 12),
            outline=(255, 255, 255),
            width=3,
        )
        draw.multiline_text(
            (overlay_margin + 32, height - 580),
            wrap_text(prompt[:220], width=36),
            fill=(255, 255, 255),
            font=font,
            spacing=8,
        )
        draw.text(
            (overlay_margin + 32, 120),
            f"{channel_name} | {scene_index:02d}",
            fill=(255, 255, 255),
            font=font,
        )
        draw.text(
            (overlay_margin + 32, 160),
            wrap_text(scene_text[:90], width=24),
            fill=(240, 240, 240),
            font=font,
        )
        image.save(output_path)
        return GeneratedImageResult(path=output_path, width=width, height=height)

    def _color_from_prompt(self, prompt: str) -> tuple[int, int, int]:
        digest = md5(prompt.encode("utf-8"), usedforsecurity=False).hexdigest()
        return (int(digest[0:2], 16), int(digest[2:4], 16), int(digest[4:6], 16))
