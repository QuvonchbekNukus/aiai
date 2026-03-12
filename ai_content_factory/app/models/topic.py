from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TopicRecord(BaseModel):
    channel_id: str
    topic: str
    source: str
    prompt_style: str
    created_at: datetime

