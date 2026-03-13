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
        self._draw_orbit_shapes(overlay_draw, width, height, colors)
        overlay = overlay.filter(ImageFilter.GaussianBlur(38))
        composed = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(composed)
        headline_font = self._load_font(size=82, bold=True)
        support_font = self._load_font(size=34, bold=False)
        chip_font = self._load_font(size=26, bold=True)
        metric_font = self._load_font(size=24, bold=True)
        footer_font = self._load_font(size=24, bold=False)

        self._draw_grid(draw, width, height, colors)
        self._draw_corner_badges(draw, width, height, channel_name, scene_index, chip_font)

        headline_panel = (74, 260, width - 74, 940)
        draw.rounded_rectangle(
            headline_panel,
            radius=56,
            fill=(8, 12, 24, 206),
            outline=colors[2] + (112,),
            width=3,
        )
        draw.rounded_rectangle((92, 284, 390, 352), radius=26, fill=colors[2] + (52,))
        draw.text((122, 302), "QUICK TECH BREAKDOWN", fill=(255, 255, 255), font=chip_font)

        title_text = wrap_text(scene_text, width=17)
        draw.multiline_text((108, 390), title_text, font=headline_font, fill=(255, 255, 255), spacing=16)
        draw.rounded_rectangle((94, 840, width - 94, 920), radius=28, fill=(255, 255, 255, 22))
        draw.text(
            (120, 860),
            "Swipe-stopping visual with a single sharp takeaway",
            font=support_font,
            fill=(232, 238, 246),
        )

        insight_panel = (74, 1002, width - 74, 1450)
        draw.rounded_rectangle(
            insight_panel,
            radius=44,
            fill=(12, 18, 33, 214),
            outline=(255, 255, 255, 38),
            width=2,
        )
        draw.text((112, 1044), "WHY THIS MATTERS", font=chip_font, fill=colors[2] + (255,))
        draw.multiline_text(
            (112, 1106),
            wrap_text(f"{visual_theme} | {topic}", width=30),
            font=support_font,
            fill=(242, 246, 252),
            spacing=12,
        )
        draw.multiline_text(
            (112, 1278),
            wrap_text(prompt[:140], width=40),
            font=footer_font,
            fill=(196, 205, 220),
            spacing=10,
        )

        self._draw_metric_chips(draw, width, height, colors, metric_font)
        self._draw_signal_icon(draw, width, height, colors)

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

    def _draw_orbit_shapes(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        draw.rounded_rectangle((width - 310, 248, width - 86, 620), radius=56, fill=colors[1] + (68,))
        draw.ellipse((width - 286, 272, width - 110, 448), outline=(255, 255, 255, 82), width=5)
        draw.ellipse((width - 250, 306, width - 146, 410), fill=colors[2] + (145,))
        draw.rectangle((88, 1560, 324, 1788), fill=colors[2] + (36,))
        draw.polygon(
            [
                (150, 1622),
                (260, 1622),
                (296, 1700),
                (206, 1766),
                (116, 1708),
            ],
            fill=colors[2] + (92,),
        )

    def _draw_grid(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        grid_color = colors[2] + (28,)
        for x in range(72, width, 96):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(96, height, 108):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)

    def _draw_corner_badges(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        channel_name: str,
        scene_index: int,
        chip_font: ImageFont.ImageFont,
    ) -> None:
        draw.rounded_rectangle((72, 86, 392, 162), radius=28, fill=(255, 255, 255, 36))
        draw.text((102, 108), channel_name.upper()[:20], fill=(255, 255, 255), font=chip_font)
        draw.rounded_rectangle((width - 210, 86, width - 72, 180), radius=32, fill=(255, 255, 255, 32))
        draw.text((width - 176, 114), f"SC {scene_index:02d}", fill=(255, 255, 255), font=chip_font)

    def _draw_metric_chips(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
        metric_font: ImageFont.ImageFont,
    ) -> None:
        chips = [
            ((74, 1492, 344, 1610), "FAST HOOK"),
            ((370, 1492, 692, 1610), "HIGH RETENTION"),
            ((718, 1492, width - 74, 1610), "VERTICAL STORY"),
        ]
        for bounds, label in chips:
            draw.rounded_rectangle(bounds, radius=30, fill=(9, 14, 27, 218), outline=colors[2] + (70,), width=2)
            draw.text((bounds[0] + 28, bounds[1] + 34), label, fill=(244, 248, 252), font=metric_font)

    def _draw_signal_icon(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        origin_x = width - 220
        origin_y = height - 286
        for index, bar_height in enumerate((38, 62, 96, 132)):
            left = origin_x + index * 28
            draw.rounded_rectangle(
                (left, origin_y - bar_height, left + 18, origin_y),
                radius=8,
                fill=colors[2] + (190,),
            )
        draw.ellipse((origin_x - 62, origin_y - 62, origin_x - 24, origin_y - 24), outline=(255, 255, 255, 160), width=4)

    def _draw_tech_lines(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        line_color = colors[2] + (110,)
        points = [
            ((width - 370, 706), (width - 124, 706)),
            ((width - 250, 706), (width - 250, 888)),
            ((width - 250, 888), (width - 136, 888)),
            ((124, height - 246), (356, height - 246)),
            ((356, height - 246), (356, height - 424)),
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
