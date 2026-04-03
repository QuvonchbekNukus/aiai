from __future__ import annotations

from app.config import Settings
from app.integrations.tts.base import TextToSpeechProvider
from app.models import ChannelConfig, ScenePlan
from app.utils import split_sentences


class VoiceService:
    def __init__(self, settings: Settings, provider: TextToSpeechProvider) -> None:
        self.settings = settings
        self.provider = provider

    def generate_scene_audio(self, *, channel: ChannelConfig, scene_plan: ScenePlan) -> ScenePlan:
        job_dir = self.settings.audio_dir / channel.output_folder / scene_plan.job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        for scene in scene_plan.scenes:
            output_path = job_dir / f"scene_{scene.scene_index:02d}.wav"
            prepared_text = self._prepare_text(scene.voice_text)
            result = self.provider.synthesize(
                text=prepared_text,
                output_path=output_path,
                language=channel.language,
            )
            scene.voice_text = prepared_text
            scene.audio_path = str(result.path)
            scene.duration_seconds = max(scene.duration_seconds, result.duration_seconds + 0.28)
        return scene_plan

    def _prepare_text(self, text: str) -> str:
        sentences = split_sentences(text)
        if not sentences:
            return text.strip()
        prepared = []
        for sentence in sentences:
            cleaned = sentence.strip().rstrip(".!?")
            if cleaned:
                prepared.append(f"{cleaned}.")
        return " ... ".join(prepared) if prepared else text.strip()
