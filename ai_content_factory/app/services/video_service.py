from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import Settings
from app.logger import get_logger
from app.models import ChannelConfig, ScenePlan
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
            for scene in scene_plan.scenes:
                clip_path = work_dir / f"scene_{scene.scene_index:02d}.mp4"
                self._render_scene_clip(scene, clip_path)
                clip_paths.append(clip_path)

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
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-pix_fmt",
                    "yuv420p",
                    str(merged_path),
                ]
            )

            self._burn_subtitles_and_music(
                merged_path=merged_path,
                subtitle_path=subtitle_path,
                output_path=final_path,
                background_music_path=self._resolve_background_music(channel),
                total_duration=sum(scene.duration_seconds for scene in scene_plan.scenes),
            )
            return final_path
        finally:
            if final_path.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

    def _render_scene_clip(self, scene, clip_path: Path) -> None:
        if not scene.image_path or not scene.audio_path:
            raise ValueError(f"Scene {scene.scene_index} is missing image or audio assets.")

        duration = max(2.5, scene.duration_seconds)
        frame_count = max(1, int(duration * self.settings.default_fps))
        fade_out_start = max(0.2, duration - 0.35)
        audio_fade_out_start = max(0.1, duration - 0.2)
        video_filter = (
            f"scale={self.settings.default_video_width}:{self.settings.default_video_height}:"
            "force_original_aspect_ratio=increase,"
            f"crop={self.settings.default_video_width}:{self.settings.default_video_height},"
            f"zoompan=z='min(zoom+0.0006,1.08)':d={frame_count}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={self.settings.default_video_width}x{self.settings.default_video_height}:"
            f"fps={self.settings.default_fps},"
            "fade=t=in:st=0:d=0.20,"
            f"fade=t=out:st={fade_out_start:.2f}:d=0.28,"
            "format=yuv420p"
        )
        audio_filter = f"afade=t=in:st=0:d=0.08,afade=t=out:st={audio_fade_out_start:.2f}:d=0.18"
        self._run_ffmpeg(
            [
                self.settings.ffmpeg_bin,
                "-y",
                "-loop",
                "1",
                "-i",
                scene.image_path,
                "-i",
                scene.audio_path,
                "-vf",
                video_filter,
                "-af",
                audio_filter,
                "-r",
                str(self.settings.default_fps),
                "-t",
                f"{duration:.2f}",
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                str(self.settings.default_video_crf),
                "-b:v",
                self.settings.default_video_bitrate,
                "-maxrate",
                self.settings.default_video_bitrate,
                "-bufsize",
                "12M",
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

    def _burn_subtitles_and_music(
        self,
        *,
        merged_path: Path,
        subtitle_path: Path,
        output_path: Path,
        background_music_path: Path | None,
        total_duration: float,
    ) -> None:
        subtitle_filter = (
            f"subtitles='{self._escape_filter_path(subtitle_path)}':"
            "force_style='Alignment=2,"
            f"Fontsize={self.settings.subtitle_fontsize},"
            f"MarginV={self.settings.subtitle_margin_v},"
            "Outline=2,Shadow=1,BorderStyle=1,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H64000000'"
        )

        if background_music_path and background_music_path.exists():
            filter_complex = (
                f"[0:v]{subtitle_filter}[v];"
                f"[1:a]volume={self.settings.background_music_volume:.2f},atrim=0:{total_duration:.2f}[bg];"
                "[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
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
                    "-c:v",
                    "libx264",
                    "-preset",
                    "slow",
                    "-crf",
                    str(self.settings.default_video_crf),
                    "-b:v",
                    self.settings.default_video_bitrate,
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
                subtitle_filter,
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                str(self.settings.default_video_crf),
                "-b:v",
                self.settings.default_video_bitrate,
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
        if channel.background_music_path:
            candidate = Path(channel.background_music_path)
            if not candidate.is_absolute():
                candidate = self.settings.base_dir / candidate
            return candidate
        return self.settings.background_music_path

    def _escape_filter_path(self, path: Path) -> str:
        return path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")

    def _run_ffmpeg(self, command: list[str]) -> None:
        try:
            result = run_command(command)
            if result.stderr:
                self.logger.debug(result.stderr)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "Unknown ffmpeg error"
            raise RuntimeError(stderr) from exc
