from __future__ import annotations

from PIL import Image

from app.integrations.image_generators.styled_card_generator import StyledCardImageGenerator


def test_styled_card_generator_creates_vertical_image(tmp_path) -> None:
    output_path = tmp_path / "card.png"
    generator = StyledCardImageGenerator()

    result = generator.generate(
        prompt="Show a sleek tech insight card with network signals and speed theme.",
        topic="Why Wi-Fi slows down at night",
        scene_text="Your router is not the only device competing for signal.",
        headline_text="Wi-Fi Feels Slower",
        supporting_text="More nearby devices crowd the same channels.",
        icon_key="wifi",
        background_style="signal",
        layout_variant="split_left",
        channel_name="Tech Facts Daily",
        visual_theme="sleek tech editorial",
        scene_index=1,
        output_path=output_path,
        width=1080,
        height=1920,
    )

    assert result.path.exists()
    with Image.open(result.path) as image:
        assert image.size == (1080, 1920)
