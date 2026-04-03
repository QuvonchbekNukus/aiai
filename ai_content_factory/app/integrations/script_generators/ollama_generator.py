from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.integrations.script_generators.base import GeneratedScriptPayload, ScriptGenerator
from app.models import ChannelConfig, TopicRecord


class OllamaScriptGenerator(ScriptGenerator):
    provider_name = "ollama"

    def __init__(self, *, base_url: str, model: str, timeout_seconds: int) -> None:
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
            "stream": False,
            "format": "json",
            "prompt": self._build_prompt(channel=channel, topic=topic, prompt_template=prompt_template),
            "options": {
                "temperature": 0.6,
                "top_p": 0.9,
                "num_predict": 220,
            },
        }

        request = Request(
            url=f"{self.base_url}/api/generate",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"Ollama unavailable: {exc.reason}") from exc

        content = str(payload.get("response", "")).strip()
        parsed = self._parse_content(content)
        return GeneratedScriptPayload(
            hook=parsed["hook"],
            body=parsed["body"],
            cta=parsed["cta"],
            provider_name=self.provider_name,
            raw_response=content,
        )

    def _build_prompt(self, *, channel: ChannelConfig, topic: TopicRecord, prompt_template: str) -> str:
        return (
            f"{prompt_template}\n\n"
            "Return a compact JSON object with keys: hook, body, cta.\n"
            "Rules:\n"
            "- Language must match the channel language.\n"
            "- Total spoken length should fit an 18-28 second short video.\n"
            "- Hook must be simple and under 10 words.\n"
            "- Body must be 2 or 3 short sentences.\n"
            "- CTA must be under 6 words.\n"
            "- Each sentence should express one idea only.\n"
            "- Use plain spoken language and avoid filler.\n"
            "- Avoid markdown, labels, bullet points, emojis, and jargon.\n\n"
            f"Channel name: {channel.channel_name}\n"
            f"Niche: {channel.niche}\n"
            f"Audience: {channel.audience}\n"
            f"Prompt style: {channel.prompt_style}\n"
            f"Additional style notes: {channel.script_style_notes or 'none'}\n"
            f"Topic: {topic.topic}\n"
            f"Language: {channel.language}\n"
        )

    def _parse_content(self, content: str) -> dict[str, str]:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise RuntimeError("Ollama returned non-JSON script content.")
        parsed = json.loads(content[start : end + 1])
        return {
            "hook": self._coerce_text(parsed.get("hook", "")),
            "body": self._coerce_text(parsed.get("body", "")),
            "cta": self._coerce_text(parsed.get("cta", "")),
        }

    def _coerce_text(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            parts = [self._coerce_text(item) for item in value]
            return " ".join(part for part in parts if part).strip()
        if isinstance(value, dict):
            parts = [self._coerce_text(item) for item in value.values()]
            return " ".join(part for part in parts if part).strip()
        return str(value).strip()
