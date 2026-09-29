import pytest

from csibot.bot_helpers import (
    format_comparison,
    format_vision_summary,
    image_bytes_to_data_url,
    parse_location_input,
)
from csibot.domain.qimen import calculate_comparison
from tests.test_qimen import sample_vision_data


def test_parse_location_input_uses_default_offset() -> None:
    longitude, offset = parse_location_input("37.6173", default_utc_offset=3.0)
    assert longitude == pytest.approx(37.6173)
    assert offset == pytest.approx(3.0)


def test_parse_location_input_accepts_explicit_offset() -> None:
    longitude, offset = parse_location_input("11.5 1", default_utc_offset=3.0)
    assert longitude == pytest.approx(11.5)
    assert offset == pytest.approx(1.0)


@pytest.mark.parametrize("raw", ["", "181", "-181", "37.6 15", "abc"])
def test_parse_location_input_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_location_input(raw, default_utc_offset=3.0)


def test_image_bytes_to_data_url() -> None:
    result = image_bytes_to_data_url(b"hello", "image/jpeg")
    assert result.startswith("data:image/jpeg;base64,")
    assert result.endswith("aGVsbG8=")


def test_vision_summary_contains_all_palaces_and_confidence() -> None:
    result = format_vision_summary(sample_vision_data())
    for palace in ("坎一", "坤二", "震三", "巽四", "中五", "乾六", "兑七", "艮八", "离九"):
        assert palace in result
    assert "97%" in result


def test_comparison_formatter_escapes_user_question() -> None:
    comparison = calculate_comparison(sample_vision_data())
    text = format_comparison(
        comparison,
        question="<b>опасный & вопрос</b>",
        event_time="15.04.2026 12:00",
        solar_time="12:03",
    )
    assert "&lt;b&gt;опасный &amp; вопрос&lt;/b&gt;" in text
    assert "<b>опасный" not in text


def test_comparison_formatter_bounds_long_question() -> None:
    comparison = calculate_comparison(sample_vision_data())
    text = format_comparison(
        comparison,
        question="x" * 5000,
        event_time="15.04.2026 12:00",
        solar_time="12:03",
    )
    assert len(text) < 4096
