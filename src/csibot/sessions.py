from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from csibot.domain.qimen import QimenComparison


@dataclass
class SessionData:
    mode: str = "qimen"
    user_birthdate: str | None = None
    user_birthtime: str | None = None
    user_bazi: dict[str, Any] | None = None
    map_image_data_url: str | None = None
    question: str | None = None
    event_datetime: datetime | None = None
    longitude: float | None = None
    utc_offset: float | None = None
    true_solar_time: datetime | None = None
    vision_data: dict[str, Any] | None = None
    qimen_comparison: QimenComparison | None = None
    context: dict[str, Any] = field(default_factory=dict)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[int, SessionData] = {}

    def get(self, user_id: int) -> SessionData:
        return self._sessions.setdefault(user_id, SessionData())

    def reset(self, user_id: int, *, mode: str = "qimen") -> SessionData:
        session = SessionData(mode=mode)
        self._sessions[user_id] = session
        return session

    def clear(self, user_id: int) -> None:
        self._sessions.pop(user_id, None)
