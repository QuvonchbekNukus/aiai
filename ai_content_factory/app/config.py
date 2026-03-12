from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])
    ffmpeg_bin: str = "ffmpeg"
    output_dir: Path | None = None
    data_dir: Path | None = None
    default_video_width: int = 1080
    default_video_height: int = 1920
    default_fps: int = 30
    default_video_crf: int = 18
    default_video_bitrate: str = "8M"
    default_audio_bitrate: str = "192k"
    default_language: str = "en"
    enable_mock_upload: bool = True
    enable_mock_image_generation: bool = True
    enable_mock_tts: bool = True
    script_provider: str = "auto"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b-instruct"
    ollama_timeout_seconds: int = 90
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    openai_timeout_seconds: int = 90
    piper_bin: str = "piper"
    piper_model_path: Path | None = None
    piper_speaker: int | None = None
    windows_tts_rate: int = -1
    subtitle_fontsize: int = 30
    subtitle_margin_v: int = 120
    background_music_volume: float = 0.08
    background_music_path: Path | None = None
    scheduler_timezone: str = "UTC"
    scheduler_autostart: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context: object) -> None:
        self.base_dir = self.base_dir.resolve()
        if self.output_dir is not None and not self.output_dir.is_absolute():
            self.output_dir = (self.base_dir / self.output_dir).resolve()
        if self.data_dir is not None and not self.data_dir.is_absolute():
            self.data_dir = (self.base_dir / self.data_dir).resolve()
        if self.background_music_path is not None and not self.background_music_path.is_absolute():
            self.background_music_path = (self.base_dir / self.background_music_path).resolve()
        if self.piper_model_path is not None and not self.piper_model_path.is_absolute():
            self.piper_model_path = (self.base_dir / self.piper_model_path).resolve()

    @property
    def resolved_output_dir(self) -> Path:
        return self.output_dir or (self.base_dir / "output").resolve()

    @property
    def resolved_data_dir(self) -> Path:
        return self.data_dir or (self.base_dir / "data").resolve()

    @property
    def prompts_dir(self) -> Path:
        return (self.base_dir / "prompts").resolve()

    @property
    def scripts_dir(self) -> Path:
        return self.resolved_output_dir / "scripts"

    @property
    def scenes_dir(self) -> Path:
        return self.resolved_output_dir / "scenes"

    @property
    def images_dir(self) -> Path:
        return self.resolved_output_dir / "images"

    @property
    def audio_dir(self) -> Path:
        return self.resolved_output_dir / "audio"

    @property
    def subtitles_dir(self) -> Path:
        return self.resolved_output_dir / "subtitles"

    @property
    def videos_dir(self) -> Path:
        return self.resolved_output_dir / "videos"

    @property
    def metadata_dir(self) -> Path:
        return self.resolved_output_dir / "metadata"

    @property
    def logs_dir(self) -> Path:
        return self.resolved_output_dir / "logs"

    @property
    def channels_file(self) -> Path:
        return self.resolved_data_dir / "channels.json"

    @property
    def used_topics_file(self) -> Path:
        return self.resolved_data_dir / "used_topics.json"

    @property
    def published_videos_file(self) -> Path:
        return self.resolved_data_dir / "published_videos.json"

    @property
    def failed_jobs_file(self) -> Path:
        return self.resolved_data_dir / "failed_jobs.json"

    def ensure_runtime_paths(self) -> None:
        directories = (
            self.base_dir,
            self.resolved_data_dir,
            self.prompts_dir,
            self.resolved_output_dir,
            self.scripts_dir,
            self.scenes_dir,
            self.images_dir,
            self.audio_dir,
            self.subtitles_dir,
            self.videos_dir,
            self.metadata_dir,
            self.logs_dir,
        )
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        defaults = {
            self.channels_file: "[]\n",
            self.used_topics_file: '{\n  "version": 1,\n  "channels": {}\n}\n',
            self.published_videos_file: "[]\n",
            self.failed_jobs_file: "[]\n",
        }
        for path, content in defaults.items():
            if not path.exists():
                path.write_text(content, encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_paths()
    return settings
