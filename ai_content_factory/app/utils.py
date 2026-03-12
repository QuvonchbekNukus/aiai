from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


def slugify(value: str, max_length: int = 80) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    slug = normalized.strip("-")
    if not slug:
        slug = "item"
    return slug[:max_length].rstrip("-")


def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return default
    return json.loads(raw)


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text_file(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def estimate_duration_seconds(text: str, words_per_minute: int = 155, minimum: float = 2.0) -> float:
    words = max(1, len(text.split()))
    seconds = (words / words_per_minute) * 60
    return round(max(minimum, seconds), 2)


def split_sentences(text: str) -> list[str]:
    fragments = re.split(r"(?<=[.!?])\s+", text.strip())
    return [fragment.strip() for fragment in fragments if fragment.strip()]


def batched(items: Sequence[str], batch_size: int) -> list[list[str]]:
    return [list(items[index : index + batch_size]) for index in range(0, len(items), batch_size)]


def wrap_text(text: str, width: int = 34) -> str:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in words:
        projected = current_length + len(word) + (1 if current else 0)
        if projected > width and current:
            lines.append(" ".join(current))
            current = [word]
            current_length = len(word)
        else:
            current.append(word)
            current_length = projected
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def format_srt_timestamp(total_seconds: float) -> str:
    whole_seconds = int(total_seconds)
    milliseconds = int(round((total_seconds - whole_seconds) * 1000))
    if milliseconds == 1000:
        whole_seconds += 1
        milliseconds = 0
    hours, remainder = divmod(whole_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=True,
    )


def unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
