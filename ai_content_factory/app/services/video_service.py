from __future__ import annotations

import shutil
import subprocess
from hashlib import md5
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.config import Settings
from app.logger import get_logger
from app.models import ChannelConfig, ScenePlan
from app.utils import run_command, wrap_text


class VideoService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(self.__class__.__name__)

    def compose_video(
        self,
        *,
        channel: ChannelConfig,
        scene_plan: ScenePlan,
        subtitle_path: Path,
    ) -> Path:
        channel_dir = self.settings.videos_dir / channel.output_folder
        channel_dir.mkdir(parents=True, exist_ok=True)
        work_dir = channel_dir / f"{scene_plan.job_id}_work"
        work_dir.mkdir(parents=True, exist_ok=True)
        final_path = channel_dir / f"{scene_plan.job_id}.mp4"
        try:
            clip_paths: list[Path] = []
            total_duration = 0.0

            hook_duration = self.settings.hook_screen_duration_seconds
            hook_clip = work_dir / "scene_00_hook.mp4"
            self._render_title_clip(
                output_dir=work_dir,
                clip_path=hook_clip,
                duration=hook_duration,
                primary_text=self._build_hook_text(channel),
                secondary_text=scene_plan.topic,
                eyebrow_text="STOP THE SCROLL",
                variant="hook",
                motion_seed=0,
            )
            clip_paths.append(hook_clip)
            total_duration += hook_duration

            for scene in scene_plan.scenes:
                clip_path = work_dir / f"scene_{scene.scene_index:02d}.mp4"
                self._render_scene_clip(scene, clip_path)
                clip_paths.append(clip_path)
                total_duration += max(1.9, scene.duration_seconds)

            cta_duration = self.settings.cta_end_screen_duration_seconds
            cta_clip = work_dir / "scene_99_cta.mp4"
            self._render_title_clip(
                output_dir=work_dir,
                clip_path=cta_clip,
                duration=cta_duration,
                primary_text=channel.cta_template or "Follow for more smart tech facts.",
                secondary_text="Daily short-form explainers for curious people.",
                eyebrow_text="COME BACK TOMORROW",
                variant="cta",
                motion_seed=len(scene_plan.scenes) + 1,
            )
            clip_paths.append(cta_clip)
            total_duration += cta_duration

            concat_file = work_dir / "concat.txt"
            concat_file.write_text(
                "".join(f"file '{clip_path.resolve().as_posix()}'\n" for clip_path in clip_paths),
                encoding="utf-8",
            )

            merged_path = work_dir / "merged.mp4"
            self._run_ffmpeg(
                [
                    self.settings.ffmpeg_bin,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
                    *self._video_encoding_args(maxrate="16M", bufsize="24M"),
                    "-c:a",
                    "aac",
                    "-b:a",
                    self.settings.default_audio_bitrate,
                    "-movflags",
                    "+faststart",
                    str(merged_path),
                ]
            )

            self._burn_subtitles_and_music(
                merged_path=merged_path,
                subtitle_path=subtitle_path,
                output_path=final_path,
                background_music_path=self._resolve_background_music(channel),
                total_duration=total_duration,
            )
            return final_path
        finally:
            if final_path.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

    def _render_scene_clip(self, scene, clip_path: Path) -> None:
        if not scene.image_path or not scene.audio_path:
            raise ValueError(f"Scene {scene.scene_index} is missing image or audio assets.")

        duration = max(1.9, scene.duration_seconds)
        self._render_motion_clip(
            image_path=Path(scene.image_path),
            clip_path=clip_path,
            duration=duration,
            audio_path=Path(scene.audio_path),
            motion_seed=scene.scene_index,
            variant="scene",
        )

    def _render_title_clip(
        self,
        *,
        output_dir: Path,
        clip_path: Path,
        duration: float,
        primary_text: str,
        secondary_text: str,
        eyebrow_text: str,
        variant: str,
        motion_seed: int,
    ) -> None:
        frame_path = output_dir / f"{clip_path.stem}.png"
        self._create_title_card(
            output_path=frame_path,
            primary_text=primary_text,
            secondary_text=secondary_text,
            eyebrow_text=eyebrow_text,
            variant=variant,
        )
        self._render_motion_clip(
            image_path=frame_path,
            clip_path=clip_path,
            duration=duration,
            audio_path=None,
            motion_seed=motion_seed,
            variant=variant,
        )

    def _render_motion_clip(
        self,
        *,
        image_path: Path,
        clip_path: Path,
        duration: float,
        audio_path: Path | None,
        motion_seed: int,
        variant: str,
    ) -> None:
        frame_count = max(1, int(duration * self.settings.default_fps))
        fade_out_start = max(0.18, duration - 0.30)
        audio_fade_out_start = max(0.12, duration - 0.18)
        motion_filter = self._build_motion_filter(
            frame_count=frame_count,
            motion_seed=motion_seed,
            variant=variant,
            fade_out_start=fade_out_start,
        )
        if audio_path:
            audio_filter = (
                "volume=1.0,"
                "aresample=48000,"
                "afade=t=in:st=0:d=0.08,"
                f"afade=t=out:st={audio_fade_out_start:.2f}:d=0.16"
            )
            command = [
                self.settings.ffmpeg_bin,
                "-y",
                "-loop",
                "1",
                "-i",
                str(image_path),
                "-i",
                str(audio_path),
                "-vf",
                motion_filter,
                "-af",
                audio_filter,
                "-t",
                f"{duration:.2f}",
                *self._video_encoding_args(maxrate="14M", bufsize="20M"),
                "-c:a",
                "aac",
                "-b:a",
                self.settings.default_audio_bitrate,
                "-movflags",
                "+faststart",
                "-shortest",
                str(clip_path),
            ]
            self._run_ffmpeg(command)
            return

        command = [
            self.settings.ffmpeg_bin,
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-vf",
            motion_filter,
            "-af",
            f"atrim=0:{duration:.2f}",
            "-t",
            f"{duration:.2f}",
            *self._video_encoding_args(maxrate="14M", bufsize="20M"),
            "-c:a",
            "aac",
            "-b:a",
            self.settings.default_audio_bitrate,
            "-movflags",
            "+faststart",
            "-shortest",
            str(clip_path),
        ]
        self._run_ffmpeg(command)

    def _build_motion_filter(
        self,
        *,
        frame_count: int,
        motion_seed: int,
        variant: str,
        fade_out_start: float,
    ) -> str:
        phase_x = 8 + (motion_seed % 5) * 5
        phase_y = 10 + (motion_seed % 7) * 4
        zoom_speed = "0.0013" if variant in {"hook", "cta"} else "0.0009"
        max_zoom = "1.18" if variant in {"hook", "cta"} else "1.12"
        color_boost = "contrast=1.06:saturation=1.12:brightness=0.015"
        if variant == "cta":
            color_boost = "contrast=1.04:saturation=1.15:brightness=0.01"

        return (
            f"scale={self.settings.default_video_width}:{self.settings.default_video_height}:"
            "force_original_aspect_ratio=increase,"
            f"crop={self.settings.default_video_width}:{self.settings.default_video_height},"
            f"zoompan=z='min(zoom+{zoom_speed},{max_zoom})':d={frame_count}:"
            f"x='iw/2-(iw/zoom/2)+((iw-iw/zoom)*0.07*sin((on+{phase_x})/34))':"
            f"y='ih/2-(ih/zoom/2)+((ih-ih/zoom)*0.05*cos((on+{phase_y})/42))':"
            f"s={self.settings.default_video_width}x{self.settings.default_video_height}:"
            f"fps={self.settings.default_fps},"
            f"eq={color_boost},"
            "unsharp=5:5:0.6:5:5:0.0,"
            "fade=t=in:st=0:d=0.16,"
            f"fade=t=out:st={fade_out_start:.2f}:d=0.18,"
            "format=yuv420p"
        )

    def _burn_subtitles_and_music(
        self,
        *,
        merged_path: Path,
        subtitle_path: Path,
        output_path: Path,
        background_music_path: Path | None,
        total_duration: float,
    ) -> None:
        subtitle_style = (
            "Alignment=2,"
            "FontName=Bahnschrift SemiBold,"
            f"Fontsize={self.settings.subtitle_fontsize},"
            f"MarginV={self.settings.subtitle_margin_v},"
            "Outline=4,Shadow=0,BorderStyle=1,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,"
            "Spacing=0.1"
        )
        subtitle_filter = (
            f"subtitles='{self._escape_filter_path(subtitle_path)}':"
            f"force_style='{subtitle_style}'"
        )
        progress_background = "drawbox=x=0:y=ih-14:w=iw:h=10:color=black@0.38:t=fill"
        progress_fill = (
            f"drawbox=x=0:y=ih-14:w='iw*min(t/{total_duration:.2f},1)':"
            "h=10:color=white@0.92:t=fill"
        )
        video_filter = f"{progress_background},{progress_fill},{subtitle_filter}"

        if background_music_path and background_music_path.exists():
            music_fade_out = max(0.1, total_duration - 1.0)
            filter_complex = (
                f"[0:v]{video_filter}[v];"
                f"[1:a]aresample=48000,volume={self.settings.background_music_volume:.2f},"
                "afade=t=in:st=0:d=0.8,"
                f"afade=t=out:st={music_fade_out:.2f}:d=0.8,"
                f"atrim=0:{total_duration:.2f}[bg];"
                "[0:a][bg]amix=inputs=2:duration=first:weights='1 0.18':normalize=0,"
                "alimiter=limit=0.95[aout]"
            )
            self._run_ffmpeg(
                [
                    self.settings.ffmpeg_bin,
                    "-y",
                    "-i",
                    str(merged_path),
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(background_music_path),
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[v]",
                    "-map",
                    "[aout]",
                    *self._video_encoding_args(maxrate="16M", bufsize="24M"),
                    "-c:a",
                    "aac",
                    "-b:a",
                    self.settings.default_audio_bitrate,
                    "-movflags",
                    "+faststart",
                    str(output_path),
                ]
            )
            return

        self._run_ffmpeg(
            [
                self.settings.ffmpeg_bin,
                "-y",
                "-i",
                str(merged_path),
                "-vf",
                video_filter,
                *self._video_encoding_args(maxrate="16M", bufsize="24M"),
                "-c:a",
                "aac",
                "-b:a",
                self.settings.default_audio_bitrate,
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )

    def _resolve_background_music(self, channel: ChannelConfig) -> Path | None:
        if not self.settings.enable_background_music:
            return None
        if channel.background_music_path:
            candidate = Path(channel.background_music_path)
            if not candidate.is_absolute():
                candidate = self.settings.base_dir / candidate
            return candidate
        return self.settings.background_music_path

    def _build_hook_text(self, channel: ChannelConfig) -> str:
        niche = channel.niche.lower()
        if "tech" in niche or "technology" in niche or "digital" in niche:
            return "Most people don't know this tech fact"
        return "Most people miss this part"

    def _create_title_card(
        self,
        *,
        output_path: Path,
        primary_text: str,
        secondary_text: str,
        eyebrow_text: str,
        variant: str,
    ) -> None:
        width = self.settings.default_video_width
        height = self.settings.default_video_height
        palette = self._title_palette(variant)

        base = Image.new("RGBA", (width, height), palette[0])
        self._draw_title_gradient(base, palette)

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse((width - 420, -80, width + 120, 540), fill=palette[2] + (128,))
        overlay_draw.ellipse((-160, height - 760, 500, height - 120), fill=palette[1] + (92,))
        overlay_draw.rounded_rectangle((82, 182, width - 82, height - 220), radius=62, fill=(10, 14, 24, 208))
        overlay = overlay.filter(ImageFilter.GaussianBlur(34))
        composed = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(composed)
        headline_font = self._load_font(size=94, bold=True)
        support_font = self._load_font(size=34, bold=False)
        eyebrow_font = self._load_font(size=28, bold=True)
        footer_font = self._load_font(size=24, bold=False)

        draw.rounded_rectangle((90, 156, 420, 232), radius=28, fill=palette[2] + (54,))
        draw.text((120, 178), eyebrow_text, font=eyebrow_font, fill=(255, 255, 255))

        draw.multiline_text(
            (104, 390),
            wrap_text(primary_text, width=15),
            font=headline_font,
            fill=(255, 255, 255),
            spacing=18,
        )
        draw.rounded_rectangle((96, 1038, width - 96, 1246), radius=40, fill=(255, 255, 255, 22))
        draw.multiline_text(
            (124, 1082),
            wrap_text(secondary_text, width=28),
            font=support_font,
            fill=(236, 242, 248),
            spacing=12,
        )
        draw.rounded_rectangle((96, height - 266, width - 96, height - 178), radius=28, fill=(255, 255, 255, 16))
        footer = "Fast vertical storytelling built for Shorts and Reels"
        if variant == "cta":
            footer = "See you in the next short"
        draw.text((124, height - 236), footer, font=footer_font, fill=(214, 222, 236))

        for index in range(4):
            left = width - 240 + index * 28
            bar_top = 820 - index * 48
            draw.rounded_rectangle(
                (left, bar_top, left + 18, 980),
                radius=8,
                fill=palette[2] + (185 - index * 20,),
            )

        composed.convert("RGB").save(output_path, quality=95)

    def _title_palette(self, variant: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
        seeds = {
            "hook": ("09111F", "0F4C81", "4FF3FF"),
            "cta": ("1A101B", "8C2949", "FF9A4D"),
        }
        first, second, accent = seeds.get(variant, seeds["hook"])
        return (self._hex_to_rgb(first), self._hex_to_rgb(second), self._hex_to_rgb(accent))

    def _draw_title_gradient(
        self,
        image: Image.Image,
        palette: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for y in range(height):
            ratio = y / max(1, height - 1)
            if ratio < 0.55:
                color = self._blend(palette[0], palette[1], ratio / 0.55)
            else:
                color = self._blend(palette[1], palette[2], (ratio - 0.55) / 0.45)
            draw.line([(0, y), (width, y)], fill=color + (255,))

        stripe_width = 180
        for x in range(-width // 4, width, stripe_width):
            draw.polygon(
                [
                    (x, 0),
                    (x + 92, 0),
                    (x + stripe_width + 160, height),
                    (x + stripe_width + 68, height),
                ],
                fill=(255, 255, 255, 9),
            )

    def _video_encoding_args(self, *, maxrate: str, bufsize: str) -> list[str]:
        return [
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-profile:v",
            "high",
            "-level:v",
            "4.2",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(self.settings.default_fps),
            "-crf",
            str(self.settings.default_video_crf),
            "-b:v",
            self.settings.default_video_bitrate,
            "-maxrate",
            maxrate,
            "-bufsize",
            bufsize,
            "-g",
            str(self.settings.default_fps * 2),
        ]

    def _escape_filter_path(self, path: Path) -> str:
        return path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")

    def _run_ffmpeg(self, command: list[str]) -> None:
        try:
            self.logger.debug("Running ffmpeg: %s", " ".join(command))
            result = run_command(command)
            if result.stderr:
                self.logger.debug(result.stderr)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "Unknown ffmpeg error"
            raise RuntimeError(stderr) from exc

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

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        digest = md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()
        source = value if len(value) == 6 else digest[:6]
        return (int(source[0:2], 16), int(source[2:4], 16), int(source[4:6], 16))
