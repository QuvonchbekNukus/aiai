from __future__ import annotations

from hashlib import md5
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.integrations.image_generators.base import GeneratedImageResult, ImageGenerator
from app.utils import wrap_text


class StyledCardImageGenerator(ImageGenerator):
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
        colors = self._palette(topic, scene_index)

        base = Image.new("RGBA", (width, height), colors[0])
        self._draw_gradient(base, colors[0], colors[1], colors[2])
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        self._draw_soft_glows(overlay_draw, width, height, colors)
        overlay = overlay.filter(ImageFilter.GaussianBlur(38))
        composed = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(composed)
        headline_font = self._load_font(size=74, bold=True)
        body_font = self._load_font(size=32, bold=False)
        chip_font = self._load_font(size=26, bold=True)
        footer_font = self._load_font(size=24, bold=False)

        panel = (72, 250, width - 72, height - 210)
        draw.rounded_rectangle(panel, radius=42, fill=(11, 16, 29, 212), outline=(255, 255, 255, 44), width=2)
        draw.rounded_rectangle((72, 90, 360, 160), radius=24, fill=(255, 255, 255, 42))
        draw.text((98, 107), channel_name.upper()[:22], fill=(255, 255, 255), font=chip_font)

        badge = (width - 190, 94, width - 72, 184)
        draw.rounded_rectangle(badge, radius=28, fill=(255, 255, 255, 38))
        draw.text((width - 155, 117), f"{scene_index:02d}", fill=(255, 255, 255), font=headline_font)

        title_text = wrap_text(scene_text, width=18)
        draw.multiline_text((110, 330), title_text, font=headline_font, fill=(255, 255, 255), spacing=12)

        accent_y = height - 360
        draw.rounded_rectangle((110, accent_y, width - 110, accent_y + 12), radius=8, fill=colors[2] + (255,))
        draw.multiline_text(
            (110, accent_y + 42),
            wrap_text(f"{visual_theme} | {topic}", width=34),
            font=body_font,
            fill=(230, 236, 245),
            spacing=10,
        )
        draw.multiline_text(
            (110, height - 210),
            wrap_text(prompt[:120], width=44),
            font=footer_font,
            fill=(196, 205, 220),
            spacing=8,
        )

        self._draw_tech_lines(draw, width, height, colors)
        composed.convert("RGB").save(output_path, quality=95)
        return GeneratedImageResult(path=output_path, width=width, height=height)

    def _palette(self, topic: str, scene_index: int) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
        digest = md5(f"{topic}-{scene_index}".encode("utf-8"), usedforsecurity=False).hexdigest()
        base = (int(digest[0:2], 16), int(digest[2:4], 16), int(digest[4:6], 16))
        accent = (int(digest[6:8], 16), int(digest[8:10], 16), int(digest[10:12], 16))
        bright = tuple(min(255, component + 75) for component in accent)
        return (self._darken(base, 0.42), self._brighten(accent, 0.18), bright)

    def _draw_gradient(
        self,
        image: Image.Image,
        top_color: tuple[int, int, int],
        mid_color: tuple[int, int, int],
        bottom_color: tuple[int, int, int],
    ) -> None:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for y in range(height):
            ratio = y / max(1, height - 1)
            if ratio < 0.55:
                color = self._blend(top_color, mid_color, ratio / 0.55)
            else:
                color = self._blend(mid_color, bottom_color, (ratio - 0.55) / 0.45)
            draw.line([(0, y), (width, y)], fill=color + (255,))

    def _draw_soft_glows(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        draw.ellipse((width - 460, -40, width + 60, 520), fill=colors[2] + (90,))
        draw.ellipse((-120, height - 620, 460, height - 40), fill=colors[1] + (74,))

    def _draw_tech_lines(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        line_color = colors[2] + (110,)
        points = [
            ((width - 340, 280), (width - 180, 280)),
            ((width - 220, 280), (width - 220, 440)),
            ((width - 220, 440), (width - 120, 440)),
            ((140, height - 320), (300, height - 320)),
            ((300, height - 320), (300, height - 450)),
        ]
        for start, end in points:
            draw.line([start, end], fill=line_color, width=5)
            draw.ellipse((start[0] - 7, start[1] - 7, start[0] + 7, start[1] + 7), fill=(255, 255, 255, 200))
            draw.ellipse((end[0] - 7, end[1] - 7, end[0] + 7, end[1] + 7), fill=(255, 255, 255, 200))

    def _load_font(self, *, size: int, bold: bool) -> ImageFont.ImageFont:
        candidates = [
            "C:/Windows/Fonts/bahnschrift.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for candidate in candidates:
            path = Path(candidate)
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
        return ImageFont.load_default()

    def _blend(self, first: tuple[int, int, int], second: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
        return tuple(int(first[index] + (second[index] - first[index]) * ratio) for index in range(3))

    def _brighten(self, color: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
        return tuple(min(255, int(component + (255 - component) * ratio)) for component in color)

    def _darken(self, color: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
        return tuple(max(0, int(component * ratio)) for component in color)
