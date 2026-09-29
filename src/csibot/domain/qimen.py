from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

HEAVENLY_STEMS = {
    "甲": {"element": "木", "polarity": "阳"},
    "乙": {"element": "木", "polarity": "阴"},
    "丙": {"element": "火", "polarity": "阳"},
    "丁": {"element": "火", "polarity": "阴"},
    "戊": {"element": "土", "polarity": "阳"},
    "己": {"element": "土", "polarity": "阴"},
    "庚": {"element": "金", "polarity": "阳"},
    "辛": {"element": "金", "polarity": "阴"},
    "壬": {"element": "水", "polarity": "阳"},
    "癸": {"element": "水", "polarity": "阴"},
}

EARTHLY_BRANCHES = tuple("子丑寅卯辰巳午未申酉戌亥")

TWELVE_STAGES = {
    "长生": 5,
    "沐浴": 4,
    "冠带": 3,
    "临官": 2,
    "帝旺": 10,
    "衰": -2,
    "病": -3,
    "死": -5,
    "墓": -8,
    "绝": -10,
    "胎": 1,
    "养": 2,
}

GATES_SCORES = {"开": 5, "休": 4, "生": 6, "景": 1, "杜": 0, "伤": -3, "惊": -4, "死": -5}
STARS_SCORES = {
    "天辅": 3,
    "辅": 3,
    "天任": 2,
    "任": 2,
    "天禽": 4,
    "禽": 4,
    "天冲": 1,
    "冲": 1,
    "天心": 3,
    "心": 3,
    "天柱": 0,
    "柱": 0,
    "天芮": -3,
    "芮": -3,
    "天蓬": -4,
    "蓬": -4,
    "天英": 1,
    "英": 1,
}
SPIRITS_SCORES = {
    "值符": 5,
    "腾蛇": 0,
    "螣蛇": 0,
    "太阴": 2,
    "六合": 3,
    "白虎": -2,
    "玄武": -3,
    "九地": 1,
    "九天": 4,
}
CRITICAL_STEM_COMBINATIONS = {
    ("丙", "戊"): ("Птица падает в гнездо", 25),
    ("戊", "丙"): ("Дракон поворачивает голову", 20),
    ("乙", "癸"): ("Зелёный дракон в воду", 15),
    ("庚", "辛"): ("Белый тигр в лес", -15),
    ("丙", "庚"): ("Великий огонь", -20),
}
CRITICAL_SPECIALS = {
    "三奇": 18,
    "刑": -15,
    "冲": -15,
    "自煞": -25,
}
XUN_KONG = {
    "甲子": ["戌", "亥"],
    "甲戌": ["申", "酉"],
    "甲申": ["午", "未"],
    "甲午": ["辰", "巳"],
    "甲辰": ["寅", "卯"],
    "甲寅": ["子", "丑"],
}
PALACE_ELEMENTS = {
    "坎一": "水",
    "坤二": "土",
    "震三": "木",
    "巽四": "木",
    "中五": "土",
    "乾六": "金",
    "兑七": "金",
    "艮八": "土",
    "离九": "火",
}
EXPECTED_PALACES = tuple(PALACE_ELEMENTS)
OPPOSITE_PALACES = {
    "坎一": "离九",
    "离九": "坎一",
    "震三": "兑七",
    "兑七": "震三",
    "艮八": "坤二",
    "坤二": "艮八",
    "乾六": "巽四",
    "巽四": "乾六",
    "中五": "坎一",
}


class TrueSolarTimeCalculator:
    @staticmethod
    def equation_of_time(value: datetime) -> float:
        day_of_year = value.timetuple().tm_yday
        b = 2 * math.pi * (day_of_year - 81) / 364
        return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    @classmethod
    def calculate(
        cls,
        local_time: datetime,
        longitude: float,
        utc_offset_hours: float = 3.0,
        dst: bool = False,
    ) -> datetime:
        standard_meridian = utc_offset_hours * 15.0
        longitude_minutes = (longitude - standard_meridian) * 4.0
        equation_minutes = cls.equation_of_time(local_time)
        dst_minutes = 60.0 if dst else 0.0
        return local_time + timedelta(minutes=longitude_minutes + equation_minutes - dst_minutes)


class QimenCalculator:
    @staticmethod
    def seasonal_strength(element: str, month_element: str) -> int:
        generation = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
        control = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
        if element == month_element:
            return 10
        if generation.get(month_element) == element:
            return 5
        if generation.get(element) == month_element:
            return 0
        if control.get(month_element) == element:
            return -5
        if control.get(element) == month_element:
            return -10
        return 0

    @staticmethod
    def twelve_stage(stem: str, branch: str) -> str:
        yang_start = {"甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申"}
        yin_start = {"乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯"}
        polarity = HEAVENLY_STEMS.get(stem, {}).get("polarity")
        start = yang_start.get(stem, "亥") if polarity == "阳" else yin_start.get(stem, "午")
        try:
            start_idx = EARTHLY_BRANCHES.index(start)
            current_idx = EARTHLY_BRANCHES.index(branch)
        except ValueError:
            return "养"
        stages = ("长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养")
        return stages[(current_idx - start_idx) % 12]

    @classmethod
    def base_balance(
        cls,
        palace: dict[str, Any],
        day_stem: str,
        hour_stem: str,
        month_element: str,
        zhi_fu: str,
        zhi_shi: str,
    ) -> float:
        score = 0.0
        stem = str(palace.get("stem", ""))
        if stem == zhi_fu or palace.get("god") == "值符":
            score += 15
        if palace.get("door") == zhi_shi:
            score += 12
        if stem == hour_stem:
            score += 8
        if stem == day_stem:
            score += 5

        score += cls.seasonal_strength(str(palace.get("element", "")), month_element)

        branch = str(palace.get("branch", ""))
        if branch:
            score += TWELVE_STAGES.get(cls.twelve_stage(day_stem, branch), 0)

        score += GATES_SCORES.get(str(palace.get("door", "")), 0)
        score += STARS_SCORES.get(str(palace.get("star", "")), 0)
        score += SPIRITS_SCORES.get(str(palace.get("god", "")), 0)
        return float(score)

    @staticmethod
    def empty_coefficient(
        palace_branch: str,
        day_branch: str,
        hour_branch: str,
        xun_kong_branches: list[str],
    ) -> float:
        if palace_branch not in xun_kong_branches:
            return 1.0
        if palace_branch in {day_branch, hour_branch}:
            return 1.0
        combinations = (
            ("子", "丑"),
            ("寅", "亥"),
            ("卯", "戌"),
            ("辰", "酉"),
            ("巳", "申"),
            ("午", "未"),
        )
        for first, second in combinations:
            if palace_branch == first and second in {day_branch, hour_branch}:
                return 1.0
            if palace_branch == second and first in {day_branch, hour_branch}:
                return 1.0
        return 0.2

    @staticmethod
    def critical_structures(
        palace: dict[str, Any], other_palace: dict[str, Any] | None = None
    ) -> int:
        score = 0
        stem = str(palace.get("stem", ""))
        hidden = str(palace.get("hidden_stem", ""))
        other_stem = str((other_palace or {}).get("stem", ""))
        for (first, second), (_, value) in CRITICAL_STEM_COMBINATIONS.items():
            if stem == first and (hidden == second or other_stem == second):
                score += value
        specials = palace.get("special", [])
        if isinstance(specials, str):
            specials = [specials]
        for marker in specials:
            score += CRITICAL_SPECIALS.get(str(marker), 0)
        return score

    @staticmethod
    def palace_interaction(
        host_palace: dict[str, Any], guest_palace: dict[str, Any]
    ) -> tuple[int, int]:
        generation = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
        control = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
        host_element = str(host_palace.get("element", ""))
        guest_element = str(guest_palace.get("element", ""))
        if generation.get(host_element) == guest_element:
            return -10, 10
        if generation.get(guest_element) == host_element:
            return 10, -10
        if control.get(host_element) == guest_element:
            return 15, -15
        if control.get(guest_element) == host_element:
            return -15, 15
        return 0, 0

    @classmethod
    def final_score(
        cls,
        palace: dict[str, Any],
        *,
        day_stem: str,
        hour_stem: str,
        month_element: str,
        zhi_fu: str,
        zhi_shi: str,
        day_branch: str,
        hour_branch: str,
        xun_kong: list[str],
        opponent_palace: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        s_base = cls.base_balance(palace, day_stem, hour_stem, month_element, zhi_fu, zhi_shi)
        branch = str(palace.get("branch", ""))
        k_empty = cls.empty_coefficient(branch, day_branch, hour_branch, xun_kong)
        w_struct = cls.critical_structures(palace, opponent_palace)
        c_inter = 0
        if opponent_palace:
            c_inter, _ = cls.palace_interaction(palace, opponent_palace)
        final_score = float((s_base * k_empty) + w_struct + c_inter)
        return {
            "s_base": float(s_base),
            "k_empty": float(k_empty),
            "s_base_corrected": float(s_base * k_empty),
            "w_struct": int(w_struct),
            "c_inter": int(c_inter),
            "final_score": final_score,
            "details": {
                "palace_element": palace.get("element"),
                "phase": cls.seasonal_strength(str(palace.get("element", "")), month_element),
                "is_empty": branch in xun_kong,
                "empty_filled": k_empty == 1.0 and branch in xun_kong,
            },
        }


@dataclass(frozen=True)
class QimenComparison:
    host_palace: str
    guest_palace: str
    host: dict[str, Any]
    guest: dict[str, Any]
    verdict: str
    recommendation: str

    @property
    def difference(self) -> float:
        return abs(float(self.host["final_score"]) - float(self.guest["final_score"]))


def extract_json_object(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("GLM response does not contain a JSON object")
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("GLM returned malformed JSON") from exc
    if not isinstance(parsed, dict):
        raise TypeError("GLM response JSON must be an object")
    return parsed


def validate_vision_data(data: dict[str, Any]) -> dict[str, Any]:
    grid = data.get("palace_grid")
    if not isinstance(grid, dict):
        raise TypeError("palace_grid is missing")
    missing = [name for name in EXPECTED_PALACES if name not in grid]
    if missing:
        raise ValueError("GLM did not recognize all nine palaces: " + ", ".join(missing))

    required_palace_fields = ("stem", "branch", "door", "star", "god")
    for name in EXPECTED_PALACES:
        palace = grid[name]
        if not isinstance(palace, dict):
            raise TypeError(f"palace {name} must be an object")
        missing_fields = [
            field for field in required_palace_fields if not str(palace.get(field, "")).strip()
        ]
        if missing_fields:
            raise ValueError(f"palace {name} is missing fields: " + ", ".join(missing_fields))

    time_info = data.get("time_info")
    if not isinstance(time_info, dict):
        raise TypeError("time_info is missing")
    missing_time = [
        key for key in ("day", "hour", "xun") if not str(time_info.get(key, "")).strip()
    ]
    if missing_time:
        raise ValueError("time_info is missing: " + ", ".join(missing_time))

    system_info = data.get("system_info")
    if not isinstance(system_info, dict):
        raise TypeError("system_info is missing")
    missing_system = [
        key
        for key in ("zhi_fu", "zhi_shi", "month_element")
        if not str(system_info.get(key, "")).strip()
    ]
    if missing_system:
        raise ValueError("system_info is missing: " + ", ".join(missing_system))
    return data


def _validate_calculable_vision_data(data: dict[str, Any]) -> None:
    grid = data["palace_grid"]
    for name in EXPECTED_PALACES:
        palace = grid[name]
        checks = (
            ("stem", HEAVENLY_STEMS),
            ("branch", EARTHLY_BRANCHES),
            ("door", GATES_SCORES),
            ("star", STARS_SCORES),
            ("god", SPIRITS_SCORES),
        )
        for field, allowed in checks:
            value = str(palace.get(field, ""))
            if value not in allowed:
                raise ValueError(
                    f"palace {name}: {field}={value!r} is not reliable enough for calculation"
                )

    time_info = data["time_info"]
    day = str(time_info["day"])
    hour = str(time_info["hour"])
    if len(day) < 2 or day[0] not in HEAVENLY_STEMS or day[1] not in EARTHLY_BRANCHES:
        raise ValueError("time_info.day is not a valid stem-branch pair")
    if len(hour) < 2 or hour[0] not in HEAVENLY_STEMS or hour[1] not in EARTHLY_BRANCHES:
        raise ValueError("time_info.hour is not a valid stem-branch pair")
    if str(time_info["xun"]) not in XUN_KONG:
        raise ValueError("time_info.xun is not recognized")

    system_info = data["system_info"]
    if str(system_info["zhi_shi"]) not in GATES_SCORES:
        raise ValueError("system_info.zhi_shi is not a recognized Gate")
    if str(system_info["month_element"]) not in {"木", "火", "土", "金", "水"}:
        raise ValueError("system_info.month_element is not recognized")


def _stem_branch(value: Any, fallback_stem: str, fallback_branch: str) -> tuple[str, str]:
    text = str(value or "")
    stem = text[0] if len(text) >= 1 else fallback_stem
    branch = text[1] if len(text) >= 2 else fallback_branch
    return stem, branch


def calculate_comparison(vision_data: dict[str, Any]) -> QimenComparison:
    validate_vision_data(vision_data)
    _validate_calculable_vision_data(vision_data)
    grid = {name: dict(value) for name, value in vision_data["palace_grid"].items()}
    time_info = vision_data.get("time_info") or {}
    system_info = vision_data.get("system_info") or {}

    day_stem, day_branch = _stem_branch(time_info.get("day"), "甲", "子")
    hour_stem, hour_branch = _stem_branch(time_info.get("hour"), "甲", "子")
    month_element = str(system_info.get("month_element") or "木")
    zhi_fu = str(system_info.get("zhi_fu") or "甲")
    zhi_shi = str(system_info.get("zhi_shi") or "休")
    xun = str(time_info.get("xun") or "甲子")
    xun_kong = XUN_KONG.get(xun, ["戌", "亥"])

    host_name: str | None = None
    guest_name: str | None = None
    for name in EXPECTED_PALACES:
        palace = grid[name]
        if host_name is None and (palace.get("stem") == day_stem or palace.get("god") == "值符"):
            host_name = name
        if guest_name is None and palace.get("stem") == hour_stem:
            guest_name = name

    host_name = host_name or EXPECTED_PALACES[0]
    if not guest_name or guest_name == host_name:
        guest_name = OPPOSITE_PALACES[host_name]

    host_palace = grid[host_name]
    guest_palace = grid[guest_name]
    host_palace["element"] = PALACE_ELEMENTS[host_name]
    guest_palace["element"] = PALACE_ELEMENTS[guest_name]

    common = {
        "day_stem": day_stem,
        "hour_stem": hour_stem,
        "month_element": month_element,
        "zhi_fu": zhi_fu,
        "zhi_shi": zhi_shi,
        "day_branch": day_branch,
        "hour_branch": hour_branch,
        "xun_kong": xun_kong,
    }
    host_score = QimenCalculator.final_score(host_palace, opponent_palace=guest_palace, **common)
    guest_score = QimenCalculator.final_score(guest_palace, opponent_palace=host_palace, **common)

    host_final = float(host_score["final_score"])
    guest_final = float(guest_score["final_score"])
    difference = abs(host_final - guest_final)
    if host_final > guest_final + 5:
        verdict = "Дворец Хозяина сильнее"
        recommendation = "Действовать активнее и удерживать инициативу."
    elif guest_final > host_final + 5:
        verdict = "Дворец Гостя сильнее"
        recommendation = "Снизить прямое давление и выбрать более осторожную тактику."
    elif difference < 5:
        verdict = "Силы близки"
        recommendation = "Искать компромисс или третий путь."
    else:
        verdict = "主客皆伤"
        recommendation = "Избегать прямого конфликта: потери вероятны у обеих сторон."

    return QimenComparison(
        host_palace=host_name,
        guest_palace=guest_name,
        host=host_score,
        guest=guest_score,
        verdict=verdict,
        recommendation=recommendation,
    )
