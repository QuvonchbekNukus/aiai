from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ScriptDraft(BaseModel):
    job_id: str
    channel_id: str
    topic: str
    language: str
    hook: str
    body: str
    cta: str
    created_at: datetime
    provider_name: str | None = None
    prompt_template: str | None = None

    def full_text(self) -> str:
        return " ".join(part for part in (self.hook, self.body, self.cta) if part)

    def word_count(self) -> int:
        return len(self.full_text().split())
