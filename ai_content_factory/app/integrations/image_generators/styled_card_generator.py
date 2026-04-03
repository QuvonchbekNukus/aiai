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
        headline_text: str | None = None,
        supporting_text: str | None = None,
        icon_key: str | None = None,
        background_style: str | None = None,
        layout_variant: str | None = None,
        channel_name: str,
        visual_theme: str,
        scene_index: int,
        output_path: Path,
        width: int,
        height: int,
    ) -> GeneratedImageResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        headline = (headline_text or scene_text or topic).strip()
        support = (supporting_text or scene_text or prompt[:120]).strip()
        icon = (icon_key or "spark").strip().lower()
        style = (background_style or "pulse").strip().lower()
        layout = (layout_variant or "split_left").strip().lower()
        colors = self._palette(f"{topic}-{style}-{scene_index}")

        base = Image.new("RGBA", (width, height), colors[0] + (255,))
        self._draw_gradient(base, colors)

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        self._draw_background_pattern(overlay_draw, width, height, colors, style)
        overlay = overlay.filter(ImageFilter.GaussianBlur(28))
        composed = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(composed)
        headline_font = self._load_font(size=90, bold=True)
        support_font = self._load_font(size=34, bold=False)
        chip_font = self._load_font(size=26, bold=True)
        footer_font = self._load_font(size=24, bold=False)

        self._draw_scene_chrome(
            draw=draw,
            width=width,
            height=height,
            channel_name=channel_name,
            scene_index=scene_index,
            chip_font=chip_font,
            colors=colors,
        )
        self._draw_layout(
            draw=draw,
            width=width,
            height=height,
            headline=headline,
            support=support,
            icon_key=icon,
            layout=layout,
            visual_theme=visual_theme,
            headline_font=headline_font,
            support_font=support_font,
            footer_font=footer_font,
            colors=colors,
        )

        composed.convert("RGB").save(output_path, quality=95)
        return GeneratedImageResult(path=output_path, width=width, height=height)

    def _draw_layout(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        headline: str,
        support: str,
        icon_key: str,
        layout: str,
        visual_theme: str,
        headline_font: ImageFont.ImageFont,
        support_font: ImageFont.ImageFont,
        footer_font: ImageFont.ImageFont,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        if layout == "split_right":
            self._draw_split_layout(
                draw=draw,
                width=width,
                height=height,
                headline=headline,
                support=support,
                icon_key=icon_key,
                reverse=True,
                headline_font=headline_font,
                support_font=support_font,
                footer_font=footer_font,
                colors=colors,
                visual_theme=visual_theme,
            )
            return
        if layout == "stacked":
            self._draw_stacked_layout(
                draw=draw,
                width=width,
                height=height,
                headline=headline,
                support=support,
                icon_key=icon_key,
                headline_font=headline_font,
                support_font=support_font,
                footer_font=footer_font,
                colors=colors,
                visual_theme=visual_theme,
            )
            return
        if layout == "focus":
            self._draw_focus_layout(
                draw=draw,
                width=width,
                height=height,
                headline=headline,
                support=support,
                icon_key=icon_key,
                headline_font=headline_font,
                support_font=support_font,
                footer_font=footer_font,
                colors=colors,
                visual_theme=visual_theme,
            )
            return
        if layout == "ticker":
            self._draw_ticker_layout(
                draw=draw,
                width=width,
                height=height,
                headline=headline,
                support=support,
                icon_key=icon_key,
                headline_font=headline_font,
                support_font=support_font,
                footer_font=footer_font,
                colors=colors,
                visual_theme=visual_theme,
            )
            return

        self._draw_split_layout(
            draw=draw,
            width=width,
            height=height,
            headline=headline,
            support=support,
            icon_key=icon_key,
            reverse=False,
            headline_font=headline_font,
            support_font=support_font,
            footer_font=footer_font,
            colors=colors,
            visual_theme=visual_theme,
        )

    def _draw_split_layout(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        headline: str,
        support: str,
        icon_key: str,
        reverse: bool,
        headline_font: ImageFont.ImageFont,
        support_font: ImageFont.ImageFont,
        footer_font: ImageFont.ImageFont,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
        visual_theme: str,
    ) -> None:
        text_box = (72, 264, 664, 1464) if not reverse else (416, 264, width - 72, 1464)
        icon_box = (724, 300, width - 72, 812) if not reverse else (72, 300, 356, 812)

        draw.rounded_rectangle(text_box, radius=56, fill=(10, 14, 26, 214), outline=colors[2] + (88,), width=3)
        draw.rounded_rectangle(icon_box, radius=56, fill=(255, 255, 255, 18), outline=colors[3] + (125,), width=3)
        self._draw_icon(draw, icon_box, icon_key, colors[3])

        headline_anchor = (text_box[0] + 42, text_box[1] + 88)
        support_anchor = (text_box[0] + 42, text_box[1] + 748)
        draw.multiline_text(
            headline_anchor,
            wrap_text(headline, width=12),
            font=headline_font,
            fill=(255, 255, 255),
            spacing=18,
        )
        draw.multiline_text(
            support_anchor,
            wrap_text(support, width=24),
            font=support_font,
            fill=(230, 236, 245),
            spacing=12,
        )
        self._draw_footer(draw, footer_font, visual_theme, colors, width, height)

    def _draw_stacked_layout(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        headline: str,
        support: str,
        icon_key: str,
        headline_font: ImageFont.ImageFont,
        support_font: ImageFont.ImageFont,
        footer_font: ImageFont.ImageFont,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
        visual_theme: str,
    ) -> None:
        hero_box = (96, 248, width - 96, 760)
        body_box = (96, 840, width - 96, 1456)

        draw.rounded_rectangle(hero_box, radius=60, fill=(10, 14, 24, 202), outline=colors[2] + (86,), width=3)
        draw.rounded_rectangle(body_box, radius=52, fill=(12, 18, 32, 216), outline=(255, 255, 255, 46), width=2)
        self._draw_icon(draw, (width - 346, 308, width - 120, 534), icon_key, colors[3])

        draw.multiline_text(
            (132, 326),
            wrap_text(headline, width=12),
            font=headline_font,
            fill=(255, 255, 255),
            spacing=16,
        )
        draw.multiline_text(
            (132, 938),
            wrap_text(support, width=24),
            font=support_font,
            fill=(236, 242, 248),
            spacing=12,
        )
        self._draw_footer(draw, footer_font, visual_theme, colors, width, height)

    def _draw_focus_layout(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        headline: str,
        support: str,
        icon_key: str,
        headline_font: ImageFont.ImageFont,
        support_font: ImageFont.ImageFont,
        footer_font: ImageFont.ImageFont,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
        visual_theme: str,
    ) -> None:
        draw.ellipse((width - 450, 200, width - 20, 630), fill=colors[3] + (42,))
        draw.rounded_rectangle((84, 1018, width - 84, 1498), radius=62, fill=(8, 12, 24, 218))
        self._draw_icon(draw, (120, 1084, 324, 1288), icon_key, colors[3])

        draw.multiline_text(
            (96, 326),
            wrap_text(headline, width=13),
            font=headline_font,
            fill=(255, 255, 255),
            spacing=18,
        )
        draw.multiline_text(
            (366, 1116),
            wrap_text(support, width=20),
            font=support_font,
            fill=(234, 240, 246),
            spacing=12,
        )
        self._draw_footer(draw, footer_font, visual_theme, colors, width, height)

    def _draw_ticker_layout(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        headline: str,
        support: str,
        icon_key: str,
        headline_font: ImageFont.ImageFont,
        support_font: ImageFont.ImageFont,
        footer_font: ImageFont.ImageFont,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
        visual_theme: str,
    ) -> None:
        draw.rounded_rectangle((76, 304, width - 76, 612), radius=56, fill=(10, 14, 24, 212))
        draw.rounded_rectangle((76, 698, width - 76, 1284), radius=56, fill=(14, 20, 34, 220))
        draw.rounded_rectangle((76, 1362, width - 76, 1518), radius=42, fill=colors[3] + (48,))
        self._draw_icon(draw, (width - 314, 362, width - 110, 566), icon_key, colors[3])

        draw.multiline_text(
            (118, 372),
            wrap_text(headline, width=12),
            font=headline_font,
            fill=(255, 255, 255),
            spacing=12,
        )
        draw.multiline_text(
            (118, 802),
            wrap_text(support, width=24),
            font=support_font,
            fill=(232, 238, 246),
            spacing=12,
        )
        draw.text((118, 1412), visual_theme[:42].upper(), font=footer_font, fill=(255, 255, 255))
        self._draw_footer(draw, footer_font, visual_theme, colors, width, height)

    def _draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        footer_font: ImageFont.ImageFont,
        visual_theme: str,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
        width: int,
        height: int,
    ) -> None:
        draw.rounded_rectangle((92, height - 226, width - 92, height - 146), radius=28, fill=(255, 255, 255, 14))
        draw.text(
            (120, height - 198),
            wrap_text(visual_theme, width=38).replace("\n", " "),
            font=footer_font,
            fill=(214, 224, 236),
        )
        for index in range(4):
            left = width - 232 + index * 28
            bar_top = height - 420 - index * 36
            draw.rounded_rectangle((left, bar_top, left + 16, height - 264), radius=8, fill=colors[3] + (180,))

    def _draw_scene_chrome(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        channel_name: str,
        scene_index: int,
        chip_font: ImageFont.ImageFont,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        draw.rounded_rectangle((72, 78, 370, 154), radius=28, fill=(255, 255, 255, 28))
        draw.text((102, 102), channel_name.upper()[:20], fill=(255, 255, 255), font=chip_font)
        draw.rounded_rectangle((width - 218, 78, width - 72, 170), radius=32, fill=colors[3] + (42,))
        draw.text((width - 182, 106), f"SC {scene_index:02d}", fill=(255, 255, 255), font=chip_font)

    def _draw_background_pattern(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
        style: str,
    ) -> None:
        if style == "signal":
            for offset in range(0, 6):
                draw.arc((width - 540 - offset * 60, 90 - offset * 50, width - 130 + offset * 30, 580 + offset * 50), 212, 334, fill=colors[3] + (78,), width=6)
            return
        if style == "grid":
            for x in range(44, width, 88):
                draw.line([(x, 0), (x, height)], fill=colors[3] + (26,), width=1)
            for y in range(52, height, 104):
                draw.line([(0, y), (width, y)], fill=colors[3] + (24,), width=1)
            return
        if style == "scan":
            for y in range(-200, height, 56):
                draw.rectangle((0, y, width, y + 18), fill=colors[3] + (12,))
            return
        if style == "bars":
            for index in range(8):
                left = 86 + index * 114
                draw.rounded_rectangle((left, height - 760 + (index % 3) * 38, left + 58, height - 120), radius=26, fill=colors[3] + (38 + index * 10,))
            return
        if style == "orbit":
            draw.ellipse((width - 480, 120, width - 40, 560), fill=colors[3] + (38,))
            draw.ellipse((40, height - 660, 460, height - 240), fill=colors[2] + (30,))
            return
        if style == "charge":
            for index in range(5):
                draw.rounded_rectangle((100 + index * 160, 240, 190 + index * 160, 700), radius=24, fill=colors[3] + (36 + index * 18,))
            return
        if style == "shield":
            draw.polygon([(width - 250, 220), (width - 120, 290), (width - 150, 490), (width - 250, 620), (width - 350, 490), (width - 380, 290)], fill=colors[3] + (48,))
            return
        if style == "glow":
            draw.ellipse((width - 430, -60, width + 60, 430), fill=colors[3] + (82,))
            draw.ellipse((-140, height - 700, 520, height - 40), fill=colors[2] + (74,))
            return

        for index in range(5):
            radius = 260 + index * 90
            draw.ellipse((width - radius - 60, 120 - index * 40, width - 60, 120 + radius - index * 20), outline=colors[3] + (40,), width=5)

    def _draw_icon(
        self,
        draw: ImageDraw.ImageDraw,
        bounds: tuple[int, int, int, int],
        icon_key: str,
        accent: tuple[int, int, int],
    ) -> None:
        left, top, right, bottom = bounds
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        draw.rounded_rectangle(bounds, radius=46, fill=(8, 12, 20, 138), outline=accent + (120,), width=3)

        if icon_key == "wifi":
            for radius in (32, 68, 104):
                draw.arc((center_x - radius, center_y - radius, center_x + radius, center_y + radius), 210, 330, fill=accent + (255,), width=8)
            draw.ellipse((center_x - 14, center_y + 66, center_x + 14, center_y + 94), fill=accent + (255,))
            return
        if icon_key == "battery":
            draw.rounded_rectangle((center_x - 86, center_y - 44, center_x + 70, center_y + 44), radius=18, outline=accent + (255,), width=8)
            draw.rectangle((center_x + 74, center_y - 18, center_x + 98, center_y + 18), fill=accent + (255,))
            draw.polygon([(center_x - 8, center_y - 54), (center_x + 26, center_y - 8), (center_x + 4, center_y - 8), (center_x + 22, center_y + 52), (center_x - 26, center_y + 6), (center_x - 2, center_y + 6)], fill=accent + (255,))
            return
        if icon_key == "phone":
            draw.rounded_rectangle((center_x - 72, center_y - 118, center_x + 72, center_y + 118), radius=26, outline=accent + (255,), width=8)
            draw.ellipse((center_x - 10, center_y + 82, center_x + 10, center_y + 102), fill=accent + (255,))
            return
        if icon_key == "qr":
            for x_offset, y_offset in ((-82, -82), (38, -82), (-82, 38)):
                draw.rectangle((center_x + x_offset, center_y + y_offset, center_x + x_offset + 58, center_y + y_offset + 58), outline=accent + (255,), width=8)
            draw.rectangle((center_x - 6, center_y - 6, center_x + 26, center_y + 26), fill=accent + (255,))
            return
        if icon_key == "shield":
            draw.polygon([(center_x, center_y - 116), (center_x + 96, center_y - 56), (center_x + 70, center_y + 72), (center_x, center_y + 130), (center_x - 70, center_y + 72), (center_x - 96, center_y - 56)], outline=accent + (255,), fill=(255, 255, 255, 8), width=8)
            draw.line((center_x, center_y - 52, center_x, center_y + 70), fill=accent + (255,), width=8)
            draw.line((center_x - 46, center_y + 10, center_x + 46, center_y + 10), fill=accent + (255,), width=8)
            return
        if icon_key == "clock":
            draw.ellipse((center_x - 110, center_y - 110, center_x + 110, center_y + 110), outline=accent + (255,), width=8)
            draw.line((center_x, center_y, center_x, center_y - 58), fill=accent + (255,), width=8)
            draw.line((center_x, center_y, center_x + 42, center_y + 34), fill=accent + (255,), width=8)
            return
        if icon_key == "chart":
            for index, bar_height in enumerate((52, 96, 138, 176)):
                left_bar = center_x - 102 + index * 52
                draw.rounded_rectangle((left_bar, center_y + 86 - bar_height, left_bar + 30, center_y + 86), radius=10, fill=accent + (255,))
            return
        if icon_key == "target":
            for radius in (112, 72, 34):
                draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline=accent + (255,), width=8)
            draw.ellipse((center_x - 10, center_y - 10, center_x + 10, center_y + 10), fill=accent + (255,))
            return
        if icon_key == "bolt":
            draw.polygon([(center_x - 10, center_y - 118), (center_x + 36, center_y - 24), (center_x + 8, center_y - 24), (center_x + 40, center_y + 114), (center_x - 54, center_y + 8), (center_x - 22, center_y + 8)], fill=accent + (255,))
            return
        if icon_key == "globe":
            draw.ellipse((center_x - 112, center_y - 112, center_x + 112, center_y + 112), outline=accent + (255,), width=8)
            draw.arc((center_x - 78, center_y - 112, center_x + 78, center_y + 112), 90, 270, fill=accent + (255,), width=6)
            draw.arc((center_x - 78, center_y - 112, center_x + 78, center_y + 112), -90, 90, fill=accent + (255,), width=6)
            draw.line((center_x - 112, center_y, center_x + 112, center_y), fill=accent + (255,), width=6)
            return

        points = [
            (center_x, center_y - 116),
            (center_x + 30, center_y - 36),
            (center_x + 110, center_y - 20),
            (center_x + 42, center_y + 30),
            (center_x + 62, center_y + 110),
            (center_x, center_y + 56),
            (center_x - 62, center_y + 110),
            (center_x - 42, center_y + 30),
            (center_x - 110, center_y - 20),
            (center_x - 30, center_y - 36),
        ]
        draw.polygon(points, fill=accent + (255,))

    def _draw_gradient(
        self,
        image: Image.Image,
        colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for y in range(height):
            ratio = y / max(1, height - 1)
            if ratio < 0.5:
                color = self._blend(colors[0], colors[1], ratio / 0.5)
            else:
                color = self._blend(colors[1], colors[2], (ratio - 0.5) / 0.5)
            draw.line([(0, y), (width, y)], fill=color + (255,))

        for x in range(-width // 3, width, 170):
            draw.polygon(
                [
                    (x, 0),
                    (x + 82, 0),
                    (x + 252, height),
                    (x + 170, height),
                ],
                fill=(255, 255, 255, 8),
            )

    def _palette(
        self,
        seed: str,
    ) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
        digest = md5(seed.encode("utf-8"), usedforsecurity=False).hexdigest()
        base = (int(digest[0:2], 16), int(digest[2:4], 16), int(digest[4:6], 16))
        mid = (int(digest[6:8], 16), int(digest[8:10], 16), int(digest[10:12], 16))
        accent = (int(digest[12:14], 16), int(digest[14:16], 16), int(digest[16:18], 16))
        dark = self._darken(base, 0.28)
        rich = self._brighten(mid, 0.12)
        bright = self._brighten(accent, 0.22)
        soft = self._brighten(accent, 0.4)
        return dark, rich, bright, soft

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
