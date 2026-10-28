import asyncio
import json

import httpx
import pytest
from app.ai import providers as module
from app.models import Agent, Provider


def request_model(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        module.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    provider = Provider(kind="ollama", url="http://127.0.0.1:11434")
    agent = Agent(temperature=0.2, context_limit=4096)
    return asyncio.run(
        module.HTTPProvider().complete(provider, agent, "qwen3:4b", [{"role": "user", "content": "Saluda"}])
    )


def test_qwen_actions_disable_extended_thinking(monkeypatch):
    def respond(request):
        body = json.loads(request.content)
        assert body["think"] is False
        assert body["options"]["num_predict"] == 2048
        assert body["options"]["num_thread"] == module.OLLAMA_THREADS
        assert request.extensions["timeout"]["read"] == 300
        return httpx.Response(200, json={"message": {"content": '{"type":"final","content":"Hola"}'}, "eval_count": 9})

    assert request_model(monkeypatch, respond).action["content"] == "Hola"


def test_empty_timeout_exception_has_actionable_message(monkeypatch):
    def timeout(request):
        raise httpx.ReadTimeout("", request=request)

    with pytest.raises(ValueError, match="tiempo de espera agotado.*300"):
        request_model(monkeypatch, timeout)


def test_ollama_empty_response_explains_failure(monkeypatch):
    with pytest.raises(ValueError, match="respuesta vacía"):
        request_model(monkeypatch, lambda request: httpx.Response(200, json={"message": {"content": ""}}))


@pytest.mark.parametrize("model", ["gemini-3.5-flash", "models/gemini-3.5-flash"])
def test_gemini_uses_base_url_and_single_model_path(monkeypatch, model):
    original = httpx.AsyncClient

    def respond(request):
        assert request.url.path == "/v1beta/models/gemini-3.5-flash:generateContent"
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": '{"type":"final","content":"Hola"}'}]}}]}
        )

    monkeypatch.setattr(
        module.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs)
    )
    monkeypatch.setattr(module.secrets, "get", lambda ref: "test-only-key")
    provider = Provider(kind="gemini", url="https://generativelanguage.googleapis.com/v1beta", credential_ref="test")
    result = asyncio.run(
        module.HTTPProvider().complete(
            provider,
            Agent(temperature=0.2, context_limit=8192),
            model,
            [{"role": "system", "content": "Devuelve JSON"}, {"role": "user", "content": "Saluda"}],
        )
    )
    assert result.action["content"] == "Hola"


def test_gemini_rejects_full_generation_endpoint():
    with pytest.raises(ValueError, match="URL base"):
        module.validate_provider(
            Provider(
                kind="gemini",
                url="https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
            )
        )
