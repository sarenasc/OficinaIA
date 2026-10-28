import json

import httpx
import pytest
from app.ai.providers import HTTPProvider, ModelCallError, parse_response
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


async def test_anthropic_structured_action_decodes_tool_arguments(monkeypatch):
    def handler(request):
        body = json.loads(request.content)
        assert body['output_config']['format']['type'] == 'json_schema'
        assert body['output_config']['format']['schema']['additionalProperties'] is False
        assert 'arguments_json' in body['system']
        # Opus 5.5 does not support forced tool_choice; this uses JSON outputs instead.
        assert 'tool_choice' not in body
        action = {'type': 'tool', 'name': 'api.request', 'arguments_json': json.dumps({
            'connection_id': 'authorized-id', 'endpoint': 'scoreboard', 'params': {'dates': '20261025'}})}
        return httpx.Response(200, json={'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': json.dumps(action)}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(secrets, 'get', lambda ref: 'fixture-key')
    response = await HTTPProvider().complete(Provider(kind='anthropic', url='https://api.anthropic.com/v1'),
        Agent(temperature=0.2, context_limit=8192), 'claude-opus-5-5',
        [{'role': 'system', 'content': 'Actúa en JSON'}, {'role': 'user', 'content': 'Consulta'}])
    assert response.action['arguments']['params']['dates'] == '20261025'
    assert 'arguments_json' not in response.action


@pytest.mark.parametrize('case,category', [
    ('http_empty', 'provider_response'), ('http_html', 'provider_response'),
    ('text', 'invalid_model_action'), ('empty_content', 'invalid_model_action'),
    ('truncated', 'model_truncated'), ('refusal', 'model_refusal'),
])
async def test_anthropic_errors_are_specific_without_exposing_body_or_replaying(case, category, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        if case.startswith('http_'):
            return httpx.Response(200, content=b'' if case == 'http_empty' else b'<html>PRIVATE-DATA</html>')
        stop = {'truncated': 'max_tokens', 'refusal': 'refusal'}.get(case, 'end_turn')
        text = '' if case == 'empty_content' else 'PRIVATE-DATA respuesta sin JSON'
        return httpx.Response(200, json={'stop_reason': stop, 'content': [{'type': 'text', 'text': text}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(secrets, 'get', lambda ref: 'fixture-key')
    with pytest.raises(ModelCallError) as error:
        await HTTPProvider().complete(Provider(kind='anthropic', url='https://api.anthropic.com/v1'),
            Agent(temperature=0.2, context_limit=8192), 'claude-opus-5-5',
            [{'role': 'system', 'content': 'JSON'}, {'role': 'user', 'content': 'Hola'}])
    assert error.value.category == category
    assert 'PRIVATE-DATA' not in str(error.value)
    assert 'Expecting value' not in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize('content', ['```', 'no es json', '[]', '{"type":"tool"}',
    '{"type":"tool","name":"api.request","arguments_json":"invalid"}'])
def test_invalid_model_actions_have_safe_errors(content):
    with pytest.raises(ModelCallError) as error:
        parse_response(content, encoded_arguments=True)
    assert error.value.category == 'invalid_model_action'
