from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    api_key: str
    api_base: str = "https://api.xn--e1aikcel5c5a.online"
    model: str = "glm-5.3-flash"
    reasoning_effort: str = "high"
    default_utc_offset: float = 3.0
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        api_key = os.getenv("NEIRONYCH_API_KEY", "").strip()
        missing = [
            name
            for name, value in (("BOT_TOKEN", bot_token), ("NEIRONYCH_API_KEY", api_key))
            if not value
        ]
        if missing:
            raise ValueError("Missing required environment variables: " + ", ".join(missing))

        reasoning_effort = os.getenv("NEIRONYCH_REASONING_EFFORT", "high").strip().lower()
        if reasoning_effort not in {"high", "max"}:
            raise ValueError("NEIRONYCH_REASONING_EFFORT must be high or max")

        try:
            default_utc_offset = float(os.getenv("DEFAULT_UTC_OFFSET", "3"))
        except ValueError as exc:
            raise ValueError("DEFAULT_UTC_OFFSET must be a number") from exc
        if not -14 <= default_utc_offset <= 14:
            raise ValueError("DEFAULT_UTC_OFFSET must be between -14 and +14")

        return cls(
            bot_token=bot_token,
            api_key=api_key,
            api_base=os.getenv("NEIRONYCH_API_BASE", "https://api.xn--e1aikcel5c5a.online").rstrip(
                "/"
            ),
            model=os.getenv("NEIRONYCH_MODEL", "glm-5.3-flash").strip(),
            reasoning_effort=reasoning_effort,
            default_utc_offset=default_utc_offset,
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        )
