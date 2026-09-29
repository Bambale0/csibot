from __future__ import annotations

import base64
import html
from typing import Any

from csibot.domain.qimen import EXPECTED_PALACES, QimenComparison


def image_bytes_to_data_url(data: bytes, mime_type: str = "image/jpeg") -> str:
    if not data:
        raise ValueError("image is empty")
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def parse_location_input(raw: str, *, default_utc_offset: float) -> tuple[float, float]:
    normalized = raw.strip().replace(",", ".")
    parts = normalized.split()
    if len(parts) not in {1, 2}:
        raise ValueError("Use: longitude or longitude UTC_offset")
    try:
        longitude = float(parts[0])
        utc_offset = float(parts[1]) if len(parts) == 2 else float(default_utc_offset)
    except ValueError as exc:
        raise ValueError("Longitude and UTC offset must be numbers") from exc
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180")
    if not -14 <= utc_offset <= 14:
        raise ValueError("UTC offset must be between -14 and +14")
    return longitude, utc_offset


def _compact_value(value: Any, *, limit: int = 80) -> str:
    text = str(value or "—")
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return html.escape(text)


def format_vision_summary(data: dict[str, Any]) -> str:
    grid = data.get("palace_grid") or {}
    lines = ["🔎 <b>ОЦИФРОВКА КАРТЫ — ПРОВЕРЬТЕ ПЕРЕД РАСЧЁТОМ</b>", ""]
    for palace_name in EXPECTED_PALACES:
        palace = grid.get(palace_name) or {}
        special = palace.get("special") or []
        if isinstance(special, list):
            special_text = ",".join(str(item) for item in special) or "—"
        else:
            special_text = str(special)
        lines.append(
            f"<b>{palace_name}</b>: "
            f"干 {_compact_value(palace.get('stem'))} · "
            f"支 {_compact_value(palace.get('branch'))} · "
            f"门 {_compact_value(palace.get('door'))} · "
            f"星 {_compact_value(palace.get('star'))} · "
            f"神 {_compact_value(palace.get('god'))} · "
            f"暗干 {_compact_value(palace.get('hidden_stem'))} · "
            f"特殊 {_compact_value(special_text)}"
        )

    confidence = data.get("confidence_score")
    if isinstance(confidence, (int, float)):
        lines.extend(["", f"<b>Уверенность GLM:</b> {confidence:.0%}"])

    time_info = data.get("time_info") or {}
    lines.extend(
        [
            "",
            (
                "<b>Время карты:</b> "
                f"{_compact_value(time_info.get('year'))} / "
                f"{_compact_value(time_info.get('month'))} / "
                f"{_compact_value(time_info.get('day'))} / "
                f"{_compact_value(time_info.get('hour'))}"
            ),
            "",
            "Расчёт ещё <b>не выполнен</b>. Подтвердите, что символы распознаны верно.",
        ]
    )
    return "\n".join(lines)


def format_comparison(
    comparison: QimenComparison,
    *,
    question: str,
    event_time: str,
    solar_time: str,
) -> str:
    host = comparison.host
    guest = comparison.guest
    safe_question = html.escape(question[:800])
    return f"""🔮 <b>МАТЕМАТИЧЕСКИЙ АНАЛИЗ ЦИ МЭНЬ v2.1</b>

<b>Вопрос:</b> {safe_question}
<b>Время события:</b> {html.escape(event_time)}
<b>Истинное солнечное:</b> {html.escape(solar_time)}

<b>ХОЗЯИН — {comparison.host_palace}</b>
S_base: <code>{host["s_base"]:+.1f}</code>
K_empty: <code>{host["k_empty"]:.1f}</code>
W_struct: <code>{host["w_struct"]:+d}</code>
C_inter: <code>{host["c_inter"]:+d}</code>
<b>ИТОГО: {host["final_score"]:+.1f}</b>

<b>ГОСТЬ — {comparison.guest_palace}</b>
S_base: <code>{guest["s_base"]:+.1f}</code>
K_empty: <code>{guest["k_empty"]:.1f}</code>
W_struct: <code>{guest["w_struct"]:+d}</code>
C_inter: <code>{guest["c_inter"]:+d}</code>
<b>ИТОГО: {guest["final_score"]:+.1f}</b>

<b>{html.escape(comparison.verdict)}</b>
Разница: <code>{comparison.difference:.1f}</code>

<b>Стратегия:</b> {html.escape(comparison.recommendation)}

<i>Формула: (S_base × K_empty) + W_struct + C_inter</i>"""


def format_bazi(result: dict[str, Any]) -> str:
    pillars = result["pillars"]
    elements = result["elements"]
    favorable = ", ".join(result["favorable"])
    return f"""🎋 <b>БА ЦЗЫ (八字)</b>

<b>Четыре столпа:</b>
Год: <code>{html.escape(pillars["year"])}</code>
Месяц: <code>{html.escape(pillars["month"])}</code>
День: <code>{html.escape(pillars["day"])}</code>
Час: <code>{html.escape(pillars["hour"])}</code>

<b>Дневной господин:</b> {html.escape(result["day_master"])}
Стихия: {html.escape(result["day_master_element"])}
Полярность: {html.escape(result["day_master_polarity"])}

<b>Баланс пяти элементов:</b>
木 Дерево: <code>{elements["木"]:.1f}</code>
火 Огонь: <code>{elements["火"]:.1f}</code>
土 Земля: <code>{elements["土"]:.1f}</code>
金 Металл: <code>{elements["金"]:.1f}</code>
水 Вода: <code>{elements["水"]:.1f}</code>

<b>Благоприятные элементы по восстановленному алгоритму:</b> {html.escape(favorable)}"""
