from __future__ import annotations

from pathlib import Path
from typing import Sequence

from app.integrations.script_generators.base import GeneratedScriptPayload, ScriptGenerator
from app.integrations.script_generators.deterministic_generator import DeterministicScriptGenerator
from app.config import Settings
from app.logger import get_logger
from app.models import ChannelConfig, ScriptDraft, TopicRecord
from app.utils import load_text_file, split_sentences, utcnow, write_json_file, write_text_file


class ScriptService:
    def __init__(self, settings: Settings, generators: Sequence[ScriptGenerator] | None = None) -> None:
        self.settings = settings
        self.prompt_template = load_text_file(self.settings.prompts_dir / "script_prompt.txt")
        self.generators = list(generators or [DeterministicScriptGenerator()])
        self.fallback_generator = DeterministicScriptGenerator()
        self.logger = get_logger(self.__class__.__name__)

    def generate_script(
        self,
        *,
        channel: ChannelConfig,
        topic: TopicRecord,
        job_id: str,
    ) -> tuple[ScriptDraft, Path]:
        payload = self._generate_payload(channel=channel, topic=topic)

        draft = ScriptDraft(
            job_id=job_id,
            channel_id=channel.channel_id,
            topic=topic.topic,
            language=channel.language,
            hook=payload.hook,
            body=payload.body,
            cta=payload.cta,
            created_at=utcnow(),
            provider_name=payload.provider_name,
            prompt_template=self.prompt_template,
        )

        channel_dir = self.settings.scripts_dir / channel.output_folder
        channel_dir.mkdir(parents=True, exist_ok=True)
        json_path = channel_dir / f"{job_id}_script.json"
        text_path = channel_dir / f"{job_id}_script.txt"

        write_json_file(json_path, draft.model_dump(mode="json"))
        write_text_file(
            text_path,
            "\n".join(
                [
                    f"Topic: {draft.topic}",
                    f"Provider: {draft.provider_name}",
                    f"Word Count: {draft.word_count()}",
                    "",
                    f"Hook: {draft.hook}",
                    "",
                    f"Body: {draft.body}",
                    "",
                    f"CTA: {draft.cta}",
                ]
            ),
        )
        return draft, json_path

    def _generate_payload(self, *, channel: ChannelConfig, topic: TopicRecord) -> GeneratedScriptPayload:
        for generator in self.generators:
            try:
                payload = generator.generate(channel=channel, topic=topic, prompt_template=self.prompt_template)
                normalized = self._normalize_payload(payload=payload, channel=channel)
                if self._is_usable(normalized):
                    return normalized
                self.logger.warning(
                    "Script provider %s returned unusable output for topic %s.",
                    payload.provider_name,
                    topic.topic,
                )
            except Exception as exc:
                self.logger.warning(
                    "Script provider %s failed for topic %s: %s",
                    getattr(generator, "provider_name", generator.__class__.__name__),
                    topic.topic,
                    exc,
                )

        fallback = self.fallback_generator.generate(channel=channel, topic=topic, prompt_template=self.prompt_template)
        return self._normalize_payload(payload=fallback, channel=channel)

    def _normalize_payload(self, *, payload: GeneratedScriptPayload, channel: ChannelConfig) -> GeneratedScriptPayload:
        hook = self._truncate_words(self._normalize_sentence(payload.hook), max_words=9)
        body_sentences = [
            self._truncate_words(self._normalize_sentence(sentence), max_words=11)
            for sentence in split_sentences(payload.body)
        ]
        if len(body_sentences) < 2:
            compact = self._truncate_words(self._normalize_sentence(payload.body), max_words=30)
            body_sentences = self._fallback_body_sentences(compact)
        body = " ".join(body_sentences[:3])
        cta_default = channel.cta_template or "Follow for more tech facts."
        cta = self._truncate_words(self._normalize_sentence(payload.cta or cta_default), max_words=6, terminal=".")
        return GeneratedScriptPayload(
            hook=hook,
            body=body,
            cta=cta,
            provider_name=payload.provider_name,
            raw_response=payload.raw_response,
        )

    def _normalize_sentence(self, text: str) -> str:
        normalized = " ".join(text.replace("\n", " ").split()).strip(" -")
        if normalized and normalized[-1] not in ".!?":
            normalized += "."
        return normalized

    def _fallback_body_sentences(self, text: str) -> list[str]:
        words = text.replace(".", "").split()
        if not words:
            return []
        chunks: list[str] = []
        for index in range(0, len(words), 8):
            sentence = " ".join(words[index : index + 8]).strip()
            if sentence:
                chunks.append(self._normalize_sentence(sentence))
        return chunks[:3]

    def _truncate_words(self, text: str, *, max_words: int, terminal: str = ".") -> str:
        words = text.split()
        truncated = " ".join(words[:max_words]).strip()
        if truncated and truncated[-1] not in ".!?":
            truncated += terminal
        return truncated

    def _is_usable(self, payload: GeneratedScriptPayload) -> bool:
        if not payload.hook or not payload.body or not payload.cta:
            return False
        total_words = len(f"{payload.hook} {payload.body} {payload.cta}".split())
        if total_words < 32 or total_words > 56:
            return False
        sentence_count = len(split_sentences(payload.body))
        if sentence_count < 2 or sentence_count > 3:
            return False
        return all(len(sentence.split()) <= 11 for sentence in split_sentences(payload.body))
