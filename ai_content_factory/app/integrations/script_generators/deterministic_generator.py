from __future__ import annotations

from app.integrations.script_generators.base import GeneratedScriptPayload, ScriptGenerator
from app.models import ChannelConfig, TopicRecord


class DeterministicScriptGenerator(ScriptGenerator):
    provider_name = "deterministic_fallback"

    def generate(
        self,
        *,
        channel: ChannelConfig,
        topic: TopicRecord,
        prompt_template: str,
    ) -> GeneratedScriptPayload:
        subject = topic.topic.rstrip(".")
        lowercase_subject = subject.lower()
        hook = self._build_hook(lowercase_subject)
        body = self._build_body(lowercase_subject, channel)
        cta = self._build_cta(channel)
        return GeneratedScriptPayload(
            hook=hook,
            body=body,
            cta=cta,
            provider_name=self.provider_name,
        )

    def _build_hook(self, subject: str) -> str:
        return f"Most people get {subject} wrong for one simple reason."

    def _build_body(self, subject: str, channel: ChannelConfig) -> str:
        lines = [
            f"The real shift starts when you stop treating {subject} like random noise.",
            f"Focus on the mechanism, show one clear example, and connect it to a practical payoff fast.",
            f"That makes the idea easier to remember and much stronger for short-form retention.",
        ]
        return " ".join(lines)

    def _build_cta(self, channel: ChannelConfig) -> str:
        return channel.cta_template or "Follow for more tech facts."

