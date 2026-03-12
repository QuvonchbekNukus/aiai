from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings
from app.integrations.image_generators.base import ImageGenerator
from app.integrations.image_generators.styled_card_generator import StyledCardImageGenerator
from app.integrations.script_generators.base import ScriptGenerator
from app.integrations.script_generators.deterministic_generator import DeterministicScriptGenerator
from app.integrations.script_generators.ollama_generator import OllamaScriptGenerator
from app.integrations.script_generators.openai_compatible_generator import OpenAICompatibleScriptGenerator
from app.integrations.tts.base import TextToSpeechProvider
from app.integrations.tts.mock_tts import MockTTSProvider
from app.integrations.tts.piper_tts import PiperTTSProvider
from app.integrations.tts.windows_sapi_tts import WindowsSapiTTSProvider
from app.integrations.uploaders.base import Uploader
from app.integrations.uploaders.mock_instagram_uploader import MockInstagramUploader
from app.integrations.uploaders.mock_youtube_uploader import MockYouTubeUploader
from app.logger import configure_logging, get_logger
from app.models import (
    ChannelConfig,
    JobStatus,
    PipelineRunResult,
    PlatformName,
    UploadRecord,
    VideoJob,
)
from app.services.channel_service import ChannelService
from app.services.image_service import ImageService
from app.services.metadata_service import MetadataService
from app.services.publish_registry_service import PublishRegistryService
from app.services.scene_service import SceneService
from app.services.script_service import ScriptService
from app.services.subtitle_service import SubtitleService
from app.services.topic_service import TopicService
from app.services.video_service import VideoService
from app.services.voice_service import VoiceService
from app.utils import slugify, utcnow


@dataclass(slots=True)
class PipelineDependencies:
    channel_service: ChannelService
    topic_service: TopicService
    script_service: ScriptService
    scene_service: SceneService
    image_service: ImageService
    voice_service: VoiceService
    subtitle_service: SubtitleService
    video_service: VideoService
    metadata_service: MetadataService
    publish_registry_service: PublishRegistryService
    uploaders: dict[PlatformName, Uploader]


class ContentPipeline:
    def __init__(self, settings: Settings, dependencies: PipelineDependencies) -> None:
        self.settings = settings
        self.channel_service = dependencies.channel_service
        self.topic_service = dependencies.topic_service
        self.script_service = dependencies.script_service
        self.scene_service = dependencies.scene_service
        self.image_service = dependencies.image_service
        self.voice_service = dependencies.voice_service
        self.subtitle_service = dependencies.subtitle_service
        self.video_service = dependencies.video_service
        self.metadata_service = dependencies.metadata_service
        self.publish_registry_service = dependencies.publish_registry_service
        self.uploaders = dependencies.uploaders
        self.logger = get_logger(self.__class__.__name__)

    @classmethod
    def build(cls, settings: Settings | None = None) -> "ContentPipeline":
        settings = settings or get_settings()
        configure_logging(settings)

        image_generator: ImageGenerator = StyledCardImageGenerator()
        script_generators = cls._build_script_generators(settings)
        tts_provider = cls._build_tts_provider(settings)
        uploaders: dict[PlatformName, Uploader] = {
            PlatformName.YOUTUBE: MockYouTubeUploader(),
            PlatformName.INSTAGRAM: MockInstagramUploader(),
        }

        get_logger(cls.__name__).info("Using styled local card generator for images.")

        dependencies = PipelineDependencies(
            channel_service=ChannelService(settings),
            topic_service=TopicService(settings),
            script_service=ScriptService(settings, generators=script_generators),
            scene_service=SceneService(settings),
            image_service=ImageService(settings, image_generator),
            voice_service=VoiceService(settings, tts_provider),
            subtitle_service=SubtitleService(settings),
            video_service=VideoService(settings),
            metadata_service=MetadataService(settings),
            publish_registry_service=PublishRegistryService(settings),
            uploaders=uploaders,
        )
        return cls(settings, dependencies)

    @classmethod
    def _build_script_generators(cls, settings: Settings) -> list[ScriptGenerator]:
        generators: list[ScriptGenerator] = []
        if settings.script_provider in {"auto", "ollama"}:
            generators.append(
                OllamaScriptGenerator(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                    timeout_seconds=settings.ollama_timeout_seconds,
                )
            )
        if settings.script_provider in {"auto", "openai"} and settings.openai_api_key:
            if settings.openai_base_url and settings.openai_model:
                generators.append(
                    OpenAICompatibleScriptGenerator(
                        api_key=settings.openai_api_key,
                        base_url=settings.openai_base_url,
                        model=settings.openai_model,
                        timeout_seconds=settings.openai_timeout_seconds,
                    )
                )
        generators.append(DeterministicScriptGenerator())
        return generators

    @classmethod
    def _build_tts_provider(cls, settings: Settings) -> TextToSpeechProvider:
        if PiperTTSProvider.is_available(binary=settings.piper_bin, model_path=settings.piper_model_path):
            get_logger(cls.__name__).info("Using Piper TTS provider.")
            return PiperTTSProvider(
                binary=settings.piper_bin,
                model_path=settings.piper_model_path,
                speaker=settings.piper_speaker,
            )
        if WindowsSapiTTSProvider.is_available():
            get_logger(cls.__name__).info("Using Windows SAPI TTS provider.")
            return WindowsSapiTTSProvider(rate=settings.windows_tts_rate)
        get_logger(cls.__name__).warning("Falling back to synthetic tone TTS provider.")
        return MockTTSProvider()

    def run_once(self, channel_id: str | None = None) -> list[PipelineRunResult]:
        channels = self.channel_service.load_channels()
        if channel_id:
            selected = [channel for channel in channels if channel.channel_id == channel_id]
            if not selected:
                raise ValueError(f"Unknown channel_id: {channel_id}")
            channels_to_run = selected
        else:
            channels_to_run = [channel for channel in channels if channel.active]

        results: list[PipelineRunResult] = []
        for channel in channels_to_run:
            results.append(self.run_for_channel(channel))
        return results

    def run_for_channel(self, channel: ChannelConfig) -> PipelineRunResult:
        started_at = utcnow()
        topic = self.topic_service.generate_topic(channel)
        job_id = f"{channel.channel_id}-{started_at:%Y%m%d%H%M%S}-{slugify(topic.topic, 24)}"
        job = VideoJob(
            job_id=job_id,
            channel_id=channel.channel_id,
            topic=topic.topic,
            status=JobStatus.PROCESSING,
            created_at=started_at,
        )

        try:
            script, script_path = self.script_service.generate_script(channel=channel, topic=topic, job_id=job_id)
            job.script_path = str(script_path)

            scene_plan, scene_path = self.scene_service.plan_scenes(channel=channel, script=script)
            job.scene_path = str(scene_path)

            scene_plan = self.image_service.generate_scene_images(channel=channel, scene_plan=scene_plan)
            scene_plan = self.voice_service.generate_scene_audio(channel=channel, scene_plan=scene_plan)
            scene_path = self.scene_service.save_scene_plan(channel=channel, scene_plan=scene_plan)
            job.scene_path = str(scene_path)

            subtitle_path = self.subtitle_service.generate_subtitles(channel=channel, scene_plan=scene_plan)
            job.subtitle_path = str(subtitle_path)

            metadata, metadata_path = self.metadata_service.generate_metadata(channel=channel, script=script)
            job.metadata_path = str(metadata_path)

            video_path = self.video_service.compose_video(
                channel=channel,
                scene_plan=scene_plan,
                subtitle_path=subtitle_path,
            )
            job.video_path = str(video_path)

            job.uploads = self._publish(channel=channel, video_path=video_path, metadata=metadata)
            job.status = JobStatus.COMPLETED
            job.completed_at = utcnow()
            self.publish_registry_service.record_success(channel=channel, job=job, metadata=metadata)
            return PipelineRunResult(job=job, published=bool(job.uploads))
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.completed_at = utcnow()
            job.error_message = str(exc)
            self.publish_registry_service.record_failure(channel=channel, job=job, error=exc)
            self.logger.exception("Pipeline failed for channel %s", channel.channel_id)
            return PipelineRunResult(job=job, published=False)

    def _publish(self, *, channel: ChannelConfig, video_path, metadata) -> list[UploadRecord]:
        if not self.settings.enable_mock_upload:
            self.logger.info(
                "Mock upload disabled and no real uploaders configured. Video kept locally for channel %s.",
                channel.channel_id,
            )
            return []

        uploads: list[UploadRecord] = []
        for platform in channel.platforms:
            uploader = self.uploaders.get(platform)
            if not uploader:
                continue
            response = uploader.upload(channel=channel, video_path=video_path, metadata=metadata)
            uploads.append(
                UploadRecord(
                    platform=response.platform,
                    upload_id=response.upload_id,
                    status=response.status,
                    uploaded_at=utcnow(),
                )
            )
        return uploads
