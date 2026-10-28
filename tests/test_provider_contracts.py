import json

import httpx
import pytest
from app.ai.providers import HTTPProvider
from app.models import Agent, Provider
from app.security.secrets import secrets


@pytest.mark.parametrize(
    "kind,url,path",
    [
        ("ollama", "http://127.0.0.1:11434", "/api/chat"),
        ("openai", "https://api.openai.com/v1", "/v1/chat/completions"),
        ("anthropic", "https://api.anthropic.com/v1", "/v1/messages"),
        ("gemini", "https://generativelanguage.googleapis.com/v1beta", "/v1beta/models/test-model:generateContent"),
    ],
)
async def test_http_provider_contract(kind, url, path, monkeypatch):
    action = json.dumps({"type": "final", "content": "test-only"})
    payloads = {
        "ollama": {"message": {"content": action}, "prompt_eval_count": 12, "eval_count": 8,
                   "total_duration": 600000000, "load_duration": 100000000,
                   "prompt_eval_duration": 100000000, "eval_duration": 400000000},
        "openai": {
            "choices": [{"message": {"content": action}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        },
        "anthropic": {"content": [{"type": "text", "text": action}], "usage": {"input_tokens": 12, "output_tokens": 8}},
        "gemini": {
            "candidates": [{"content": {"parts": [{"text": action}]}}],
            "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 8},
        },
    }

    def handler(request):
        assert request.url.path == path
        assert request.method == "POST"
        body = json.loads(request.content)
        assert "test-model" in request.url.path or body["model"] == "test-model"
        return httpx.Response(200, json=payloads[kind])

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs)
    )
    monkeypatch.setattr(secrets, "get", lambda ref: "test-credential-only")
    provider = Provider(kind=kind, url=url, credential_ref="test-ref")
    agent = Agent(name="Test", temperature=0.2, context_limit=8192)
    response = await HTTPProvider().complete(
        provider,
        agent,
        "test-model",
        [{"role": "system", "content": "JSON actions"}, {"role": "user", "content": "test"}],
    )
    assert response.action["content"] == "test-only"
    assert response.tokens_in == 12 and response.tokens_out == 8
    if kind == "ollama":
        assert response.metrics["load_ms"] == 100 and response.metrics["total_ms"] == 600
        assert response.metrics["generation_rate_per_second"] == 20
