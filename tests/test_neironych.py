import json
import uuid

import httpx
import pytest

from csibot.services.neironych import NeironychClient


@pytest.mark.asyncio
async def test_glm_chat_uses_documented_contract_and_idempotency() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"X-Request-Id": "req-test"},
            json={
                "id": "chat-1",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Ready."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = NeironychClient(
            api_key="test-key",
            http_client=http,
            base_url="https://api.example.test",
            model="glm-5.3-flash",
        )
        key = str(uuid.uuid4())
        text = await client.chat(
            [{"role": "user", "content": "hello"}],
            idempotency_key=key,
            reasoning_effort="high",
            max_completion_tokens=2048,
        )

    assert text == "Ready."
    assert seen["headers"]["authorization"] == "Bearer test-key"
    assert seen["headers"]["idempotency-key"] == key
    assert seen["body"]["model"] == "glm-5.3-flash"
    assert seen["body"]["reasoning_effort"] == "high"
    assert seen["body"]["max_completion_tokens"] == 2048
    assert "temperature" not in seen["body"]


@pytest.mark.asyncio
async def test_glm_vision_uses_image_url_block() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": '{"palace_grid": {}}'}}]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = NeironychClient("test-key", http_client=http, base_url="https://api.example.test")
        await client.analyze_image("data:image/jpeg;base64,AAAA", "digitize")

    content = seen["body"]["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "digitize"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
