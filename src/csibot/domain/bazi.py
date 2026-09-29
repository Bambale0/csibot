from __future__ import annotations

from datetime import date
from typing import Any

HEAVENLY_STEMS = {
    "甲": {"element": "木", "polarity": "阳", "number": 1},
    "乙": {"element": "木", "polarity": "阴", "number": 2},
    "丙": {"element": "火", "polarity": "阳", "number": 3},
    "丁": {"element": "火", "polarity": "阴", "number": 4},
    "戊": {"element": "土", "polarity": "阳", "number": 5},
    "己": {"element": "土", "polarity": "阴", "number": 6},
    "庚": {"element": "金", "polarity": "阳", "number": 7},
    "辛": {"element": "金", "polarity": "阴", "number": 8},
    "壬": {"element": "水", "polarity": "阳", "number": 9},
    "癸": {"element": "水", "polarity": "阴", "number": 10},
}
EARTHLY_BRANCHES = {
    "子": {"element": "水"},
    "丑": {"element": "土"},
    "寅": {"element": "木"},
    "卯": {"element": "木"},
    "辰": {"element": "土"},
    "巳": {"element": "火"},
    "午": {"element": "火"},
    "未": {"element": "土"},
    "申": {"element": "金"},
    "酉": {"element": "金"},
    "戌": {"element": "土"},
    "亥": {"element": "水"},
}
JIA_ZI_CYCLE = (
    "甲子",
    "乙丑",
    "丙寅",
    "丁卯",
    "戊辰",
    "己巳",
    "庚午",
    "辛未",
    "壬申",
    "癸酉",
    "甲戌",
    "乙亥",
    "丙子",
    "丁丑",
    "戊寅",
    "己卯",
    "庚辰",
    "辛巳",
    "壬午",
    "癸未",
    "甲申",
    "乙酉",
    "丙戌",
    "丁亥",
    "戊子",
    "己丑",
    "庚寅",
    "辛卯",
    "壬辰",
    "癸巳",
    "甲午",
    "乙未",
    "丙申",
    "丁酉",
    "戊戌",
    "己亥",
    "庚子",
    "辛丑",
    "壬寅",
    "癸卯",
    "甲辰",
    "乙巳",
    "丙午",
    "丁未",
    "戊申",
    "己酉",
    "庚戌",
    "辛亥",
    "壬子",
    "癸丑",
    "甲寅",
    "乙卯",
    "丙辰",
    "丁巳",
    "戊午",
    "己未",
    "庚申",
    "辛酉",
    "壬戌",
    "癸亥",
)
HIDDEN_STEMS = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}
TEN_GODS = {
    "阳": {
        "same": "比肩",
        "opposite": "劫财",
        "generate_me": "偏印",
        "generate_me_same": "正印",
        "i_generate": "食神",
        "i_generate_opposite": "伤官",
        "control_me": "七杀",
        "control_me_same": "正官",
        "i_control": "偏财",
        "i_control_same": "正财",
    },
    "阴": {
        "same": "比肩",
        "opposite": "劫财",
        "generate_me": "正印",
        "generate_me_same": "偏印",
        "i_generate": "伤官",
        "i_generate_opposite": "食神",
        "control_me": "正官",
        "control_me_same": "七杀",
        "i_control": "正财",
        "i_control_same": "偏财",
    },
}


class BaZiCalculator:
    @staticmethod
    def calculate_pillars(year: int, month: int, day: int, hour: int) -> dict[str, Any]:
        year_pillar = JIA_ZI_CYCLE[(year - 4) % 60]
        month_stems_start = {
            "甲": "丙",
            "乙": "戊",
            "丙": "庚",
            "丁": "庚",
            "戊": "庚",
            "庚": "戊",
            "辛": "戊",
            "壬": "甲",
            "癸": "甲",
        }
        year_stem = year_pillar[0]
        month_stem_base = month_stems_start.get(year_stem, "甲")
        stems = list(HEAVENLY_STEMS)
        branches = list(EARTHLY_BRANCHES)
        month_stem_idx = (HEAVENLY_STEMS[month_stem_base]["number"] - 1 + month - 1) % 10
        month_stem = stems[month_stem_idx]
        month_branch = branches[(month + 1) % 12]
        month_pillar = month_stem + month_branch

        base_date = date(1900, 1, 31)
        target_date = date(year, month, day)
        day_pillar = JIA_ZI_CYCLE[(40 + (target_date - base_date).days) % 60]

        day_stem = day_pillar[0]
        hour_stems_start = {
            "甲": "甲",
            "乙": "丙",
            "丙": "戊",
            "丁": "庚",
            "戊": "壬",
            "己": "甲",
            "庚": "丙",
            "辛": "戊",
            "壬": "庚",
            "癸": "壬",
        }
        hour_stem_base = hour_stems_start.get(day_stem, "甲")
        hour_stem_idx = (HEAVENLY_STEMS[hour_stem_base]["number"] - 1 + (hour // 2)) % 10
        hour_stem = stems[hour_stem_idx]
        hour_branch = branches[((hour + 1) // 2) % 12]
        hour_pillar = hour_stem + hour_branch

        return {
            "year": year_pillar,
            "month": month_pillar,
            "day": day_pillar,
            "hour": hour_pillar,
            "day_master": day_stem,
            "day_master_element": HEAVENLY_STEMS[day_stem]["element"],
            "day_master_polarity": HEAVENLY_STEMS[day_stem]["polarity"],
        }

    @staticmethod
    def calculate_elements_balance(pillars: dict[str, Any]) -> dict[str, float]:
        elements = {"木": 0.0, "火": 0.0, "土": 0.0, "金": 0.0, "水": 0.0}
        for key in ("year", "month", "day", "hour"):
            pillar = str(pillars[key])
            stem, branch = pillar[0], pillar[1]
            elements[HEAVENLY_STEMS[stem]["element"]] += 1.0
            elements[EARTHLY_BRANCHES[branch]["element"]] += 0.6
            for hidden_stem in HIDDEN_STEMS.get(branch, []):
                elements[HEAVENLY_STEMS[hidden_stem]["element"]] += 0.2
        return elements

    @staticmethod
    def determine_favorable_elements(day_master: str, elements: dict[str, float]) -> list[str]:
        dm_element = HEAVENLY_STEMS[day_master]["element"]
        generation = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
        control = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
        total = sum(elements.values())
        ratio = elements.get(dm_element, 0.0) / total if total else 0.0
        if ratio > 0.25:
            return [control[dm_element], generation[dm_element]]
        supporting = next(
            (element for element, generated in generation.items() if generated == dm_element),
            dm_element,
        )
        return [supporting, dm_element]

    @staticmethod
    def _determine_relation(
        dm_element: str, dm_polarity: str, target_element: str, target_polarity: str
    ) -> str:
        generation = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
        control = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
        same_polarity = dm_polarity == target_polarity
        gods = TEN_GODS[dm_polarity]
        if target_element == dm_element:
            return gods["same" if same_polarity else "opposite"]
        if generation.get(target_element) == dm_element:
            return gods["generate_me_same" if same_polarity else "generate_me"]
        if generation.get(dm_element) == target_element:
            return gods["i_generate" if same_polarity else "i_generate_opposite"]
        if control.get(target_element) == dm_element:
            return gods["control_me_same" if same_polarity else "control_me"]
        if control.get(dm_element) == target_element:
            return gods["i_control" if same_polarity else "i_control_same"]
        return "Unknown"

    @classmethod
    def calculate_ten_gods(
        cls, day_master: str, pillars: dict[str, Any]
    ) -> dict[str, dict[str, str]]:
        dm_info = HEAVENLY_STEMS[day_master]
        result: dict[str, dict[str, str]] = {}
        for key in ("year", "month", "day", "hour"):
            pillar = str(pillars[key])
            stem = pillar[0]
            info = HEAVENLY_STEMS[stem]
            result[key] = {
                "pillar": pillar,
                "stem": stem,
                "branch": pillar[1],
                "ten_god": cls._determine_relation(
                    dm_info["element"],
                    dm_info["polarity"],
                    info["element"],
                    info["polarity"],
                ),
            }
        return result

    @classmethod
    def calculate(cls, year: int, month: int, day: int, hour: int) -> dict[str, Any]:
        pillars = cls.calculate_pillars(year, month, day, hour)
        elements = cls.calculate_elements_balance(pillars)
        return {
            "pillars": {key: pillars[key] for key in ("year", "month", "day", "hour")},
            "day_master": pillars["day_master"],
            "day_master_element": pillars["day_master_element"],
            "day_master_polarity": pillars["day_master_polarity"],
            "elements": elements,
            "favorable": cls.determine_favorable_elements(pillars["day_master"], elements),
            "ten_gods": cls.calculate_ten_gods(pillars["day_master"], pillars),
        }
