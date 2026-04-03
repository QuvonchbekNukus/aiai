from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.integrations.script_generators.base import GeneratedScriptPayload, ScriptGenerator
from app.models import ChannelConfig, TopicRecord


class OpenAICompatibleScriptGenerator(ScriptGenerator):
    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        *,
        channel: ChannelConfig,
        topic: TopicRecord,
        prompt_template: str,
    ) -> GeneratedScriptPayload:
        request_payload = {
            "model": self.model,
            "temperature": 0.6,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You write short-form vertical video scripts. "
                        "Return only valid JSON with keys hook, body, cta."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_prompt(channel=channel, topic=topic, prompt_template=prompt_template),
                },
            ],
        }
        request = Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"OpenAI-compatible provider unavailable: {exc.reason}") from exc

        content = str(payload["choices"][0]["message"]["content"]).strip()
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise RuntimeError("OpenAI-compatible provider returned non-JSON script content.")
        parsed = json.loads(content[start : end + 1])
        return GeneratedScriptPayload(
            hook=str(parsed.get("hook", "")).strip(),
            body=str(parsed.get("body", "")).strip(),
            cta=str(parsed.get("cta", "")).strip(),
            provider_name=self.provider_name,
            raw_response=content,
        )

    def _build_prompt(self, *, channel: ChannelConfig, topic: TopicRecord, prompt_template: str) -> str:
        return (
            f"{prompt_template}\n\n"
            "Write an 18-28 second script for a short vertical video.\n"
            "Use plain spoken language and tight pacing.\n"
            "Hook: exactly 1 sentence under 10 words.\n"
            "Body: 2 or 3 short connected sentences.\n"
            "CTA: exactly 1 sentence under 6 words.\n"
            "Every sentence should carry one idea only.\n"
            "Avoid filler, jargon, and obvious AI phrasing.\n\n"
            f"Channel name: {channel.channel_name}\n"
            f"Niche: {channel.niche}\n"
            f"Audience: {channel.audience}\n"
            f"Prompt style: {channel.prompt_style}\n"
            f"Style notes: {channel.script_style_notes or 'none'}\n"
            f"Topic: {topic.topic}\n"
            f"Language: {channel.language}\n"
        )
