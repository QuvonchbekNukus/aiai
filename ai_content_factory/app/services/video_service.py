from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import Settings
from app.logger import get_logger
from app.models import ChannelConfig, Scene, ScenePlan
from app.utils import run_command


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

            for scene in scene_plan.scenes:
                clip_path = work_dir / f"scene_{scene.scene_index:02d}.mp4"
                self._render_scene_clip(scene=scene, clip_path=clip_path)
                clip_paths.append(clip_path)
                total_duration += max(2.2, scene.duration_seconds)

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

    def _render_scene_clip(self, *, scene: Scene, clip_path: Path) -> None:
        if not scene.image_path or not scene.audio_path:
            raise ValueError(f"Scene {scene.scene_index} is missing image or audio assets.")

        duration = max(2.2, scene.duration_seconds)
        self._render_motion_clip(
            image_path=Path(scene.image_path),
            clip_path=clip_path,
            duration=duration,
            audio_path=Path(scene.audio_path),
            motion_seed=scene.scene_index,
            background_style=scene.background_style,
            layout_variant=scene.layout_variant,
        )

    def _render_motion_clip(
        self,
        *,
        image_path: Path,
        clip_path: Path,
        duration: float,
        audio_path: Path,
        motion_seed: int,
        background_style: str,
        layout_variant: str,
    ) -> None:
        frame_count = max(1, int(duration * self.settings.default_fps))
        fade_out_start = max(0.18, duration - 0.24)
        audio_fade_out_start = max(0.14, duration - 0.16)
        motion_filter = self._build_motion_filter(
            frame_count=frame_count,
            motion_seed=motion_seed,
            background_style=background_style,
            layout_variant=layout_variant,
            fade_out_start=fade_out_start,
        )
        audio_filter = (
            "volume=1.0,"
            "aresample=48000,"
            "afade=t=in:st=0:d=0.08,"
            f"afade=t=out:st={audio_fade_out_start:.2f}:d=0.14"
        )
        self._run_ffmpeg(
            [
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
        )

    def _build_motion_filter(
        self,
        *,
        frame_count: int,
        motion_seed: int,
        background_style: str,
        layout_variant: str,
        fade_out_start: float,
    ) -> str:
        profile = self._motion_profile(background_style)
        direction = -1 if layout_variant == "split_right" else 1
        vertical_direction = -1 if layout_variant in {"focus", "stacked"} else 1
        phase_x = 8 + (motion_seed % 5) * 6
        phase_y = 10 + (motion_seed % 7) * 5

        return (
            f"scale={self.settings.default_video_width}:{self.settings.default_video_height}:"
            "force_original_aspect_ratio=increase,"
            f"crop={self.settings.default_video_width}:{self.settings.default_video_height},"
            f"zoompan=z='min(zoom+{profile['zoom_speed']},{profile['max_zoom']})':d={frame_count}:"
            f"x='iw/2-(iw/zoom/2)+{direction}*((iw-iw/zoom)*{profile['x_amp']}*sin((on+{phase_x})/28))':"
            f"y='ih/2-(ih/zoom/2)+{vertical_direction}*((ih-ih/zoom)*{profile['y_amp']}*cos((on+{phase_y})/34))':"
            f"s={self.settings.default_video_width}x{self.settings.default_video_height}:"
            f"fps={self.settings.default_fps},"
            f"eq={profile['eq']},"
            "unsharp=5:5:0.5:5:5:0.0,"
            "fade=t=in:st=0:d=0.12,"
            f"fade=t=out:st={fade_out_start:.2f}:d=0.16,"
            "format=yuv420p"
        )

    def _motion_profile(self, background_style: str) -> dict[str, str]:
        profiles: dict[str, dict[str, str]] = {
            "pulse": {
                "zoom_speed": "0.0018",
                "max_zoom": "1.17",
                "x_amp": "0.05",
                "y_amp": "0.03",
                "eq": "contrast=1.10:saturation=1.10:brightness=0.018",
            },
            "signal": {
                "zoom_speed": "0.0014",
                "max_zoom": "1.15",
                "x_amp": "0.06",
                "y_amp": "0.03",
                "eq": "contrast=1.08:saturation=1.13:brightness=0.012",
            },
            "grid": {
                "zoom_speed": "0.0011",
                "max_zoom": "1.12",
                "x_amp": "0.04",
                "y_amp": "0.05",
                "eq": "contrast=1.07:saturation=1.08:brightness=0.010",
            },
            "scan": {
                "zoom_speed": "0.0015",
                "max_zoom": "1.14",
                "x_amp": "0.07",
                "y_amp": "0.02",
                "eq": "contrast=1.09:saturation=1.12:brightness=0.016",
            },
            "bars": {
                "zoom_speed": "0.0013",
                "max_zoom": "1.13",
                "x_amp": "0.05",
                "y_amp": "0.04",
                "eq": "contrast=1.08:saturation=1.14:brightness=0.012",
            },
            "charge": {
                "zoom_speed": "0.0016",
                "max_zoom": "1.16",
                "x_amp": "0.04",
                "y_amp": "0.03",
                "eq": "contrast=1.09:saturation=1.15:brightness=0.014",
            },
            "shield": {
                "zoom_speed": "0.0012",
                "max_zoom": "1.11",
                "x_amp": "0.03",
                "y_amp": "0.05",
                "eq": "contrast=1.08:saturation=1.09:brightness=0.010",
            },
            "orbit": {
                "zoom_speed": "0.0012",
                "max_zoom": "1.12",
                "x_amp": "0.05",
                "y_amp": "0.05",
                "eq": "contrast=1.06:saturation=1.10:brightness=0.010",
            },
            "glow": {
                "zoom_speed": "0.0017",
                "max_zoom": "1.16",
                "x_amp": "0.05",
                "y_amp": "0.03",
                "eq": "contrast=1.10:saturation=1.12:brightness=0.020",
            },
        }
        return profiles.get(
            background_style,
            {
                "zoom_speed": "0.0013",
                "max_zoom": "1.13",
                "x_amp": "0.05",
                "y_amp": "0.04",
                "eq": "contrast=1.08:saturation=1.10:brightness=0.012",
            },
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
            f"Fontsize={max(36, self.settings.subtitle_fontsize - 2)},"
            f"MarginV={max(140, self.settings.subtitle_margin_v - 12)},"
            "Outline=3,Shadow=0,BorderStyle=1,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,"
            "Spacing=0.15"
        )
        subtitle_filter = (
            f"subtitles='{self._escape_filter_path(subtitle_path)}':"
            f"force_style='{subtitle_style}'"
        )
        progress_background = "drawbox=x=0:y=ih-14:w=iw:h=10:color=black@0.30:t=fill"
        progress_fill = (
            f"drawbox=x=0:y=ih-14:w='iw*min(t/{total_duration:.2f},1)':"
            "h=10:color=white@0.90:t=fill"
        )
        video_filter = f"{progress_background},{progress_fill},{subtitle_filter}"

        if background_music_path and background_music_path.exists():
            music_fade_out = max(0.1, total_duration - 0.9)
            filter_complex = (
                f"[0:v]{video_filter}[v];"
                f"[1:a]aresample=48000,volume={self.settings.background_music_volume:.2f},"
                "afade=t=in:st=0:d=0.6,"
                f"afade=t=out:st={music_fade_out:.2f}:d=0.7,"
                f"atrim=0:{total_duration:.2f}[bg];"
                "[0:a][bg]amix=inputs=2:duration=first:weights='1 0.12':normalize=0,"
                "alimiter=limit=0.93[aout]"
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
