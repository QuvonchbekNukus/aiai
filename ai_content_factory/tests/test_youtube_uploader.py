from __future__ import annotations

from pathlib import Path

from app.integrations.uploaders.youtube_uploader import (
    build_youtube_description,
    build_youtube_hashtags,
    load_upload_metadata,
    normalize_hashtag,
)
from app.models import VideoMetadata


def test_normalize_hashtag_prefixes_and_strips_spaces() -> None:
    assert normalize_hashtag(" tech facts ") == "#techfacts"
    assert normalize_hashtag("#shorts") == "#shorts"
    assert normalize_hashtag("   ") == ""


def test_build_youtube_description_appends_default_shorts_hashtags() -> None:
    metadata = VideoMetadata(
        title="Demo title",
        description="Demo description",
        hashtags=["#AI", "TechFacts"],
        generated_at="2026-03-13T12:00:00Z",
    )

    hashtags = build_youtube_hashtags(metadata)
    description = build_youtube_description(metadata)

    assert hashtags[:2] == ["#AI", "#TechFacts"]
    assert "#shorts" in hashtags
    assert description.endswith("#AI #TechFacts #shorts #didyouknow")


def test_load_upload_metadata_prefers_metadata_json_when_available(tmp_path: Path) -> None:
    fallback = VideoMetadata(
        title="Fallback",
        description="Fallback description",
        hashtags=["#Fallback"],
        generated_at="2026-03-13T12:00:00Z",
    )
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        (
            '{'
            '"title":"JSON title",'
            '"description":"JSON description",'
            '"hashtags":["#Json"],'
            '"generated_at":"2026-03-13T12:30:00Z"'
            '}'
        ),
        encoding="utf-8",
    )

    resolved = load_upload_metadata(metadata_path, fallback)

    assert resolved.title == "JSON title"
    assert resolved.description == "JSON description"
    assert resolved.hashtags == ["#Json"]
