import asyncio


class DummyResponse:
    def __init__(self, status_code: int, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


def test_get_chatgpt_response_fallback(monkeypatch):
    from services import chatgpt_service

    responses = [
        DummyResponse(status_code=500, text="Internal Server Error"),
        DummyResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": "second model success"}}]},
        ),
        DummyResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": "second call success"}}]},
        ),
    ]
    requested_models = []

    class DummyAsyncClient:
        instances_created = 0

        def __init__(self):
            type(self).instances_created += 1
            self.post_calls = 0

        async def post(self, url, json, headers):
            self.post_calls += 1
            requested_models.append(json["model"])
            return responses.pop(0)

        async def aclose(self):
            pass

    dummy_client = DummyAsyncClient()

    client_ids = []

    async def dummy_get_async_client():
        client_ids.append(id(dummy_client))
        return dummy_client

    monkeypatch.setattr(chatgpt_service, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(chatgpt_service, "CHATGPT_MODELS", ["model-a", "model-b"], raising=False)
    monkeypatch.setattr(chatgpt_service, "get_async_client", dummy_get_async_client)

    async def run_test():
        return await chatgpt_service.get_chatgpt_response([{"role": "user", "content": "hi"}])

    first_result = asyncio.run(run_test())
    second_result = asyncio.run(run_test())

    assert first_result == "second model success"
    assert second_result == "second call success"
    assert requested_models == ["model-a", "model-b", "model-a"]
    assert DummyAsyncClient.instances_created == 1
    assert len(set(client_ids)) == 1
    assert dummy_client.post_calls == 3


def test_get_chatgpt_response_missing_choices(monkeypatch):
    from services import chatgpt_service

    responses = [
        DummyResponse(status_code=200, json_data={}),
        DummyResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": "fallback success"}}]},
        ),
    ]
    requested_models = []

    class DummyAsyncClient:
        instances_created = 0

        def __init__(self):
            type(self).instances_created += 1
            self.post_calls = 0

        async def post(self, url, json, headers):
            self.post_calls += 1
            requested_models.append(json["model"])
            return responses.pop(0)

        async def aclose(self):
            pass

    dummy_client = DummyAsyncClient()

    async def dummy_get_async_client():
        return dummy_client

    monkeypatch.setattr(chatgpt_service, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(chatgpt_service, "CHATGPT_MODELS", ["model-a", "model-b"], raising=False)
    monkeypatch.setattr(chatgpt_service, "get_async_client", dummy_get_async_client)

    async def run_test():
        return await chatgpt_service.get_chatgpt_response([{"role": "user", "content": "hi"}])

    result = asyncio.run(run_test())

    assert result == "fallback success"
    assert requested_models == ["model-a", "model-b"]
    assert DummyAsyncClient.instances_created == 1
    assert dummy_client.post_calls == 2
