"""Provider-independent JSON action protocol, validated by the agent engine."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import quote, urlparse

import httpx

from app.core.config import OLLAMA_THREADS
from app.models import Agent, Provider
from app.security.secrets import secrets


@dataclass
class AIResponse:
    action: dict
    tokens_in: int = 0
    tokens_out: int = 0
    metrics: dict = field(default_factory=dict)


class ModelCallError(ValueError):
    def __init__(self, message, category, attempts=1):
        super().__init__(message)
        self.category = category
        self.attempts = attempts


# Closed JSON shape supported by Claude structured outputs. Tool arguments remain
# a JSON string on the wire because arbitrary dictionary keys cannot be expressed
# in a closed schema; they are decoded and validated before any tool can run.
ANTHROPIC_ACTION_SCHEMA = {
    'type': 'object',
    'properties': {
        'type': {'type': 'string', 'enum': ['tool', 'delegate', 'final']},
        'name': {'type': 'string'},
        'arguments_json': {'type': 'string', 'description': 'Tool arguments serialized as a valid JSON object string'},
        'agent_id': {'type': 'string'}, 'request': {'type': 'string'}, 'content': {'type': 'string'},
    },
    'required': ['type'], 'additionalProperties': False,
}


def canonical_action(value: dict) -> dict:
    """Never replay model-invented tool results as trusted conversation state."""
    keys = {"tool": ("type", "name", "arguments"),
            "delegate": ("type", "agent_id", "request"), "final": ("type", "content")}
    kind = value.get("type")
    if kind not in keys or any(key not in value for key in keys[kind]):
        raise ValueError("Acción JSON incompleta o inválida")
    action = {key: value[key] for key in keys[kind]}
    if kind == "tool" and (not isinstance(action["name"], str) or not isinstance(action["arguments"], dict)):
        raise ValueError("Nombre y argumentos de herramienta inválidos")
    if kind == "delegate" and any(not isinstance(action[key], str) for key in ("agent_id", "request")):
        raise ValueError("Delegación inválida")
    if kind == "final" and not isinstance(action["content"], str):
        action["content"] = json.dumps(action["content"], ensure_ascii=False, allow_nan=False)
    return action


class AIProvider(ABC):
    @abstractmethod
    async def complete(self, provider: Provider, agent: Agent, model: str, messages: list[dict]) -> AIResponse: ...


def parse_response(content: str, *, encoded_arguments=False) -> dict:
    if not isinstance(content, str) or not content.strip():
        raise ModelCallError('El modelo devolvió una respuesta vacía; no se ejecutó ninguna acción', 'invalid_model_action')
    content = content.strip().lstrip('\ufeff')
    if content.startswith("```"):
        if '\n' not in content or not content.endswith('```'):
            raise ModelCallError('El modelo devolvió un bloque JSON incompleto', 'invalid_model_action')
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        value = json.loads(content)
    except (ValueError, TypeError):
        raise ModelCallError('El modelo devolvió texto o JSON mal formado en lugar de una acción válida; '
                             'no se ejecutó ninguna acción', 'invalid_model_action') from None
    if not isinstance(value, dict) or value.get("type") not in {"tool", "delegate", "final"}:
        raise ModelCallError('El modelo no devolvió una acción JSON válida', 'invalid_model_action')
    if encoded_arguments and value.get('type') == 'tool' and 'arguments_json' in value:
        try:
            value['arguments'] = json.loads(value.pop('arguments_json'))
        except (ValueError, TypeError):
            raise ModelCallError('El modelo devolvió argumentos de herramienta con JSON inválido', 'invalid_model_action') from None
    try:
        canonical_action(value)
    except (ValueError, TypeError):
        raise ModelCallError('El modelo devolvió una acción incompleta o argumentos inválidos', 'invalid_model_action') from None
    return value


def validate_provider(provider: Provider, model: str = ""):
    parsed = urlparse(provider.url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("URL de proveedor inválida")
    if provider.kind == "ollama":
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "host.docker.internal"}:
            raise ValueError("Ollama local requiere HTTP loopback o host.docker.internal")
        if ":cloud" in model or model.endswith("-cloud"):
            raise ValueError("Modelos Ollama cloud no admitidos por la política local")
    else:
        hosts = {
            "openai": "api.openai.com",
            "anthropic": "api.anthropic.com",
            "gemini": "generativelanguage.googleapis.com",
        }
        if parsed.scheme != "https" or parsed.hostname != hosts.get(provider.kind):
            raise ValueError("Proveedor externo requiere su endpoint HTTPS oficial")
        if provider.kind == "gemini" and parsed.path.rstrip("/") not in {"/v1beta", "/v1"}:
            raise ValueError(
                "Gemini requiere una URL base, por ejemplo https://generativelanguage.googleapis.com/v1beta; no incluya /models ni :generateContent"
            )


def provider_error_detail(response) -> str:
    """'invalid_request_error: ...' from OpenAI/Anthropic/Gemini error bodies, bounded and redacted."""
    from app.core.audit import redact

    try:
        error = response.json().get("error")
    except (ValueError, AttributeError):
        return ""
    if isinstance(error, dict):
        kind = error.get("type") or error.get("status") or ""
        message = error.get("message") or ""
    else:
        kind, message = "", error if isinstance(error, str) else ""
    text = ": ".join(str(part) for part in (kind, message) if part)
    return f" ({redact(text)[:300]})" if text else ""


class HTTPProvider(AIProvider):
    async def complete(self, provider: Provider, agent: Agent, model: str, messages: list[dict]) -> AIResponse:
        validate_provider(provider, model)
        base = provider.url.rstrip("/")
        headers = {}
        if provider.kind == "ollama":
            endpoint = base + "/api/chat"
            body = {
                "model": model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": agent.temperature,
                    "num_ctx": agent.context_limit,
                    "num_thread": OLLAMA_THREADS,
                },
            }
            if model.split(":", 1)[0] == "qwen3":
                # Agent actions need concise JSON, rather than an extended thinking phase.
                body["think"] = False
            body["options"]["num_predict"] = 2048
        else:
            key = secrets.get(provider.credential_ref)
            if not key:
                raise ValueError("Configure una API key en Windows Credential Manager")
            if provider.kind == "openai":
                endpoint = base + "/chat/completions"
                headers = {"Authorization": "Bearer " + key}
                body = {"model": model, "messages": messages, "response_format": {"type": "json_object"}}
            elif provider.kind == "anthropic":
                endpoint = base + "/messages"
                headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
                body = {"model": model, "max_tokens": 4096, "system": messages[0]["content"], "messages": messages[1:]}
                body['output_config'] = {'format': {'type': 'json_schema', 'schema': ANTHROPIC_ACTION_SCHEMA}}
                body['system'] += ('\nFormato de transporte: devuelve un objeto con type=tool/delegate/final. '
                                   'Para tool usa name y arguments_json (argumentos serializados como cadena JSON), '
                                   'no el campo arguments. Para delegate usa agent_id y request; para final usa content. '
                                   'No agregues explicaciones fuera del objeto ni resultados de herramientas inventados.')
            elif provider.kind == "gemini":
                endpoint = base + "/models/" + quote(model.removeprefix("models/"), safe="") + ":generateContent"
                headers = {"x-goog-api-key": key}
                body = {
                    "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
                    "contents": [
                        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                        for m in messages[1:]
                    ],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": agent.temperature},
                }
            else:
                raise ValueError("Proveedor pendiente")
        seconds = 300 if provider.kind == "ollama" else 120
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(seconds, connect=10), follow_redirects=False, trust_env=False
        ) as client:
            attempts = 0
            try:
                # A failed connection has not submitted inference. Retry it once;
                # read timeouts/HTTP errors may have started work and are not replayed.
                for attempts in (1, 2):
                    try:
                        response = await client.post(endpoint, json=body, headers=headers)
                        break
                    except httpx.ConnectError:
                        if attempts == 2:
                            raise
            except httpx.TimeoutException as exc:
                raise ModelCallError(
                    f"{provider.kind} / {model}: tiempo de espera agotado ({seconds} s). El modelo puede estar cargando o ser demasiado lento; pruebe una solicitud breve o un modelo menor",
                    "model_timeout", attempts,
                ) from exc
            except httpx.ConnectError as exc:
                raise ModelCallError(
                    f"No se pudo conectar con {provider.kind}; compruebe que el servicio esté iniciado", "network_connect", attempts,
                ) from exc
            except httpx.RequestError as exc:
                raise ModelCallError(f"La conexión con {provider.kind} se interrumpió ({type(exc).__name__})", "network", attempts) from exc
            if response.status_code >= 400:
                # Only the provider's own error type/message; never headers or credential-bearing URLs.
                raise ModelCallError(f"Proveedor {provider.kind} devolvió HTTP {response.status_code}"
                                     + provider_error_detail(response), "provider_http", attempts)
            try:
                data = response.json()
            except ValueError:
                raise ModelCallError(f'Proveedor {provider.kind}: HTTP {response.status_code} sin un cuerpo JSON válido '
                                     '(respuesta vacía o no JSON)', 'provider_response', attempts) from None
            if not isinstance(data, dict):
                raise ModelCallError(f'Proveedor {provider.kind}: estructura de respuesta HTTP inválida', 'provider_response', attempts)
        if provider.kind == "ollama":
            if data.get("done_reason") == "length":
                raise ValueError(
                    "Ollama alcanzó el límite de generación antes de completar la acción JSON; reduzca la solicitud"
                )
            if not data.get("message", {}).get("content"):
                raise ValueError("Ollama devolvió una respuesta vacía; revise el modelo y su configuración")
            content = data["message"]["content"]
            tin, tout = data.get("prompt_eval_count", 0), data.get("eval_count", 0)
        elif provider.kind == "openai":
            content = data["choices"][0]["message"]["content"]
            tin, tout = data.get("usage", {}).get("prompt_tokens", 0), data.get("usage", {}).get("completion_tokens", 0)
        elif provider.kind == "anthropic":
            if data.get('stop_reason') == 'max_tokens':
                raise ModelCallError('Claude cortó la respuesta por el límite de tokens; reduzca la salida solicitada',
                                     'model_truncated', attempts)
            if data.get('stop_reason') == 'refusal':
                raise ModelCallError('Claude rechazó la solicitud; revise la tarea antes de volver a intentarla',
                                     'model_refusal', attempts)
            blocks = data.get('content')
            if not isinstance(blocks, list):
                raise ModelCallError('Claude devolvió una estructura de respuesta inesperada', 'provider_response', attempts)
            content = "".join(part.get('text', '') for part in blocks
                              if isinstance(part, dict) and part.get('type') == 'text' and isinstance(part.get('text'), str))
            tin, tout = data.get("usage", {}).get("input_tokens", 0), data.get("usage", {}).get("output_tokens", 0)
        else:
            content = "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"])
            tin, tout = (
                data.get("usageMetadata", {}).get("promptTokenCount", 0),
                data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
            )
        usage_keys = {'ollama': ('prompt_eval_count', 'eval_count'), 'openai': ('prompt_tokens', 'completion_tokens'),
                      'anthropic': ('input_tokens', 'output_tokens'), 'gemini': ('promptTokenCount', 'candidatesTokenCount')}
        usage = data if provider.kind == 'ollama' else data.get('usageMetadata' if provider.kind == 'gemini' else 'usage', {})
        metrics = {"attempts": attempts, "usage_available": all(key in usage for key in usage_keys[provider.kind])}
        if provider.kind == "ollama":
            for key in ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration"):
                value = data.get(key)
                if isinstance(value, (int, float)) and value >= 0:
                    metrics[key.removesuffix("_duration") + "_ms"] = value / 1000000
            metrics.update(prompt_eval_count=tin, eval_count=tout)
            if data.get("eval_duration", 0) > 0:
                metrics["generation_rate_per_second"] = tout * 1000000000 / data["eval_duration"]
        return AIResponse(parse_response(content, encoded_arguments=provider.kind == 'anthropic'), tin, tout, metrics)


providers: dict[str, AIProvider] = {kind: HTTPProvider() for kind in ["ollama", "openai", "anthropic", "gemini"]}


async def discover(provider: Provider):
    validate_provider(provider)
    headers = {}
    if provider.kind == "ollama":
        url = provider.url.rstrip("/") + "/api/tags"
    else:
        key = secrets.get(provider.credential_ref)
        if provider.kind == "openai":
            url = provider.url.rstrip("/") + "/models"
            headers = {"Authorization": "Bearer " + key}
        elif provider.kind == "anthropic":
            url = provider.url.rstrip("/") + "/models"
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        else:
            url = provider.url.rstrip("/") + "/models"
            headers = {"x-goog-api-key": key}
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        result = await client.get(url, headers=headers)
        if result.status_code >= 400:
            raise ValueError(f"Prueba de proveedor falló: HTTP {result.status_code}")
        data = result.json()
    if provider.kind == "ollama":
        return [
            m["name"] for m in data.get("models", []) if not (":cloud" in m["name"] or m["name"].endswith("-cloud"))
        ]
    return [m.get("id", m.get("name", "")).removeprefix("models/") for m in data.get("data", data.get("models", []))]
