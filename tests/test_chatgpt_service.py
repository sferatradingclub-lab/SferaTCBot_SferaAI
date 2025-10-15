import asyncio
from typing import Iterable, List

import httpx


class DummyStreamResponse:
    def __init__(self, status_code: int, lines: Iterable[str] | None = None, text: str = ""):
        self.status_code = status_code
        self._lines: List[str] = list(lines or [])
        self.text = text
        self._url: str = "http://test"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Ничего не делаем при выходе из контекста.
        return False

    def set_url(self, url: str) -> None:
        self._url = url

    def raise_for_status(self) -> None:
        if 400 <= self.status_code:
            request = httpx.Request("POST", self._url)
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    async def aiter_lines(self):
        for line in self._lines:
            yield line


def test_get_chatgpt_response_fallback(monkeypatch):
    from services import chatgpt_service

    responses = [
        DummyStreamResponse(status_code=500, text="Internal Server Error"),
        DummyStreamResponse(
            status_code=200,
            lines=[
                'data: {"choices": [{"delta": {"content": "second model success"}}]}',
                "data:",
            ],
        ),
        DummyStreamResponse(
            status_code=200,
            lines=[
                'data: {"choices": [{"delta": {"content": "second call success"}}]}',
                "data:",
            ],
        ),
    ]
    requested_models = []

    class DummyAsyncClient:
        instances_created = 0

        def __init__(self):
            type(self).instances_created += 1
            self.post_calls = 0

        def stream(self, method, url, json, headers):
            self.post_calls += 1
            requested_models.append(json["model"])
            response = responses.pop(0)
            response.set_url(url)
            return response

        async def aclose(self):
            pass

    dummy_client = DummyAsyncClient()
    dummy_application = type("DummyApplication", (), {"bot_data": {"httpx_client": dummy_client}})()

    monkeypatch.setattr(chatgpt_service.settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(chatgpt_service.settings, "CHATGPT_MODELS", ["model-a", "model-b"], raising=False)

    async def run_test():
        chunks: list[str] = []
        async for chunk in chatgpt_service.get_chatgpt_response(
            [{"role": "user", "content": "hi"}],
            dummy_application,
        ):
            chunks.append(chunk)
        return "".join(chunks)

    first_result = asyncio.run(run_test())
    second_result = asyncio.run(run_test())

    assert first_result == "second model success"
    assert second_result == "second call success"
    assert requested_models == ["model-a", "model-b", "model-a"]
    assert DummyAsyncClient.instances_created == 1
    assert dummy_client.post_calls == 3


def test_get_chatgpt_response_missing_choices(monkeypatch):
    from services import chatgpt_service

    responses = [
        DummyStreamResponse(status_code=200, lines=["data: {}", "data:"]),
        DummyStreamResponse(
            status_code=200,
            lines=[
                'data: {"choices": [{"delta": {"content": "fallback success"}}]}',
                "data:",
            ],
        ),
    ]
    requested_models = []

    class DummyAsyncClient:
        instances_created = 0

        def __init__(self):
            type(self).instances_created += 1
            self.post_calls = 0

        def stream(self, method, url, json, headers):
            self.post_calls += 1
            requested_models.append(json["model"])
            response = responses.pop(0)
            response.set_url(url)
            return response

        async def aclose(self):
            pass

    dummy_client = DummyAsyncClient()
    dummy_application = type("DummyApplication", (), {"bot_data": {"httpx_client": dummy_client}})()

    monkeypatch.setattr(chatgpt_service.settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(chatgpt_service.settings, "CHATGPT_MODELS", ["model-a", "model-b"], raising=False)

    async def run_test():
        chunks: list[str] = []
        async for chunk in chatgpt_service.get_chatgpt_response(
            [{"role": "user", "content": "hi"}],
            dummy_application,
        ):
            chunks.append(chunk)
        return "".join(chunks)

    result = asyncio.run(run_test())

    assert result == "fallback success"
    assert requested_models == ["model-a", "model-b"]
    assert DummyAsyncClient.instances_created == 1
    assert dummy_client.post_calls == 2
