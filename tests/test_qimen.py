from datetime import UTC, datetime

import pytest

from csibot.domain.qimen import (
    QimenCalculator,
    TrueSolarTimeCalculator,
    calculate_comparison,
    extract_json_object,
)


def sample_vision_data() -> dict:
    palaces = {
        "坎一": {
            "stem": "甲",
            "branch": "子",
            "door": "休",
            "star": "天心",
            "god": "值符",
            "hidden_stem": "",
        },
        "坤二": {
            "stem": "乙",
            "branch": "丑",
            "door": "生",
            "star": "天任",
            "god": "六合",
            "hidden_stem": "",
        },
        "震三": {
            "stem": "丙",
            "branch": "寅",
            "door": "开",
            "star": "天冲",
            "god": "九天",
            "hidden_stem": "",
        },
        "巽四": {
            "stem": "丁",
            "branch": "卯",
            "door": "景",
            "star": "天辅",
            "god": "太阴",
            "hidden_stem": "",
        },
        "中五": {
            "stem": "戊",
            "branch": "辰",
            "door": "杜",
            "star": "天禽",
            "god": "九地",
            "hidden_stem": "",
        },
        "乾六": {
            "stem": "己",
            "branch": "巳",
            "door": "伤",
            "star": "天柱",
            "god": "白虎",
            "hidden_stem": "",
        },
        "兑七": {
            "stem": "庚",
            "branch": "午",
            "door": "惊",
            "star": "天芮",
            "god": "玄武",
            "hidden_stem": "",
        },
        "艮八": {
            "stem": "辛",
            "branch": "未",
            "door": "死",
            "star": "天蓬",
            "god": "腾蛇",
            "hidden_stem": "",
        },
        "离九": {
            "stem": "壬",
            "branch": "申",
            "door": "开",
            "star": "天英",
            "god": "九天",
            "hidden_stem": "",
        },
    }
    return {
        "palace_grid": palaces,
        "time_info": {"day": "甲子", "hour": "丙寅", "xun": "甲子"},
        "system_info": {"zhi_fu": "甲", "zhi_shi": "休", "month_element": "木"},
        "confidence_score": 0.97,
    }


def test_extract_json_object_accepts_wrapped_json() -> None:
    raw = 'text before {"palace_grid": {}, "confidence_score": 0.9} text after'
    parsed = extract_json_object(raw)
    assert parsed["confidence_score"] == 0.9


def test_extract_json_object_rejects_missing_json() -> None:
    with pytest.raises(ValueError):
        extract_json_object("no structured data here")


def test_true_solar_time_uses_local_timezone_meridian() -> None:
    local = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    result = TrueSolarTimeCalculator.calculate(local, longitude=45.0, utc_offset_hours=3.0)
    correction_minutes = abs((result - local).total_seconds() / 60)
    assert correction_minutes < 20


def test_calculate_comparison_produces_host_guest_scores() -> None:
    result = calculate_comparison(sample_vision_data())
    assert result.host_palace == "坎一"
    assert result.guest_palace == "震三"
    assert isinstance(result.host["final_score"], float)
    assert isinstance(result.guest["final_score"], float)
    assert result.verdict


def test_zhi_shi_scores_matching_gate_not_stem() -> None:
    palace = {
        "stem": "乙",
        "branch": "丑",
        "door": "休",
        "star": "",
        "god": "",
        "element": "土",
    }
    with_chief_gate = QimenCalculator.base_balance(
        palace,
        day_stem="甲",
        hour_stem="丙",
        month_element="水",
        zhi_fu="甲",
        zhi_shi="休",
    )
    without_chief_gate = QimenCalculator.base_balance(
        palace,
        day_stem="甲",
        hour_stem="丙",
        month_element="水",
        zhi_fu="甲",
        zhi_shi="开",
    )
    assert with_chief_gate - without_chief_gate == 12


def test_short_star_name_from_vision_prompt_is_scored() -> None:
    palace = {
        "stem": "乙",
        "branch": "丑",
        "door": "",
        "star": "辅",
        "god": "",
        "element": "土",
    }
    score = QimenCalculator.base_balance(
        palace,
        day_stem="甲",
        hour_stem="丙",
        month_element="水",
        zhi_fu="甲",
        zhi_shi="开",
    )
    without_star = dict(palace, star="")
    base = QimenCalculator.base_balance(
        without_star,
        day_stem="甲",
        hour_stem="丙",
        month_element="水",
        zhi_fu="甲",
        zhi_shi="开",
    )
    assert score - base == 3


def test_comparison_rejects_missing_time_metadata() -> None:
    data = sample_vision_data()
    data["time_info"] = {}
    with pytest.raises(ValueError, match="time_info"):
        calculate_comparison(data)


def test_comparison_rejects_unclear_required_palace_symbol() -> None:
    data = sample_vision_data()
    data["palace_grid"]["坎一"]["stem"] = "unclear"
    with pytest.raises(ValueError, match="坎一"):
        calculate_comparison(data)
