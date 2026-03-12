from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models import ChannelConfig, TopicRecord


@dataclass(slots=True)
class GeneratedScriptPayload:
    hook: str
    body: str
    cta: str
    provider_name: str
    raw_response: str | None = None


class ScriptGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        channel: ChannelConfig,
        topic: TopicRecord,
        prompt_template: str,
    ) -> GeneratedScriptPayload:
        raise NotImplementedError

