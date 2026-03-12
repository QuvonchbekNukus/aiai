from __future__ import annotations

from pathlib import Path

from app.config import Settings


def test_relative_paths_resolve_from_base_dir(tmp_path: Path) -> None:
    settings = Settings(
        base_dir=tmp_path,
        data_dir=Path("data"),
        output_dir=Path("output"),
        background_music_path=Path("music/track.mp3"),
    )

    assert settings.base_dir == tmp_path.resolve()
    assert settings.resolved_data_dir == (tmp_path / "data").resolve()
    assert settings.resolved_output_dir == (tmp_path / "output").resolve()
    assert settings.background_music_path == (tmp_path / "music/track.mp3").resolve()

