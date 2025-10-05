class DummyResponse:
    def __init__(self, status_code: int, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json

def test_get_chatgpt_response_fallback(monkeypatch):
    import asyncio
    from services import chatgpt_service

    responses = [
        DummyResponse(status_code=500, text="Internal Server Error"),
        DummyResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": "second model success"}}]},
        ),
    ]
    requested_models = []

    class DummyAsyncClient:
        call_count = 0

        def __init__(self, *args, **kwargs):
            DummyAsyncClient.call_count += 1

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            requested_models.append(json["model"])
            return responses.pop(0)

    monkeypatch.setattr(chatgpt_service, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(chatgpt_service, "CHATGPT_MODELS", ["model-a", "model-b"], raising=False)
    monkeypatch.setattr(chatgpt_service.httpx, "AsyncClient", DummyAsyncClient)

    async def run_test():
        return await chatgpt_service.get_chatgpt_response([{"role": "user", "content": "hi"}])

    result = asyncio.run(run_test())

    assert result == "second model success"
    assert requested_models == ["model-a", "model-b"]
    assert DummyAsyncClient.call_count == 1
