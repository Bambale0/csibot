from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Sequence
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NeironychAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class NeironychClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.xn--e1aikcel5c5a.online",
        model: str = "glm-5.3-flash",
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 120.0,
        default_reasoning_effort: str = "high",
    ) -> None:
        if not api_key:
            raise ValueError("Neironych API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        if default_reasoning_effort not in {"high", "max"}:
            raise ValueError("default_reasoning_effort must be high or max")
        self.default_reasoning_effort = default_reasoning_effort
        self._owns_client = http_client is None
        self.http = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self.http.aclose()

    async def list_models(self) -> list[str]:
        response = await self.http.get(f"{self.base_url}/v1/models")
        self._raise_for_status(response)
        payload = response.json()
        return [
            str(item["id"])
            for item in payload.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]

    async def assert_model_available(self) -> None:
        models = await self.list_models()
        if self.model not in models:
            raise NeironychAPIError(f"Configured model {self.model!r} is not present in /v1/models")

    async def chat(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        idempotency_key: str | None = None,
        reasoning_effort: str | None = None,
        max_completion_tokens: int = 8192,
    ) -> str:
        key = idempotency_key or str(uuid.uuid4())
        effort = reasoning_effort or self.default_reasoning_effort
        if effort not in {"high", "max"}:
            raise ValueError("reasoning_effort must be high or max")
        payload = {
            "model": self.model,
            "messages": list(messages),
            "max_completion_tokens": max_completion_tokens,
            "reasoning_effort": effort,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": key,
        }
        started = time.monotonic()
        try:
            response = await self.http.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise NeironychAPIError(
                "Neironych API timeout. Do not create a new paid request automatically."
            ) from exc
        except httpx.HTTPError as exc:
            raise NeironychAPIError(f"Neironych API transport error: {exc}") from exc

        self._raise_for_status(response)
        logger.info(
            "Neironych chat completed model=%s status=%s request_id=%s duration_ms=%d",
            self.model,
            response.status_code,
            response.headers.get("X-Request-Id"),
            int((time.monotonic() - started) * 1000),
        )
        data = response.json()
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise NeironychAPIError(
                "Neironych API returned no choices",
                request_id=response.headers.get("X-Request-Id"),
            )
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise NeironychAPIError(
                "Neironych API returned an empty assistant message",
                request_id=response.headers.get("X-Request-Id"),
            )
        return content.strip()

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        *,
        idempotency_key: str | None = None,
    ) -> str:
        return await self.chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            idempotency_key=idempotency_key,
            reasoning_effort=self.default_reasoning_effort,
            max_completion_tokens=8192,
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        request_id = response.headers.get("X-Request-Id")
        try:
            payload = response.json()
        except ValueError:
            payload = response.text[:500]
        logger.warning(
            "Neironych API error status=%s request_id=%s",
            response.status_code,
            request_id,
        )
        raise NeironychAPIError(
            f"Neironych API returned HTTP {response.status_code}: {payload}",
            status_code=response.status_code,
            request_id=request_id,
        )
