"""An explicit one-tool request needs no model to choose or rewrite its result."""
import json

PREFIX = 'Ejecuta únicamente la herramienta autorizada: '


def direct_tool_request(request):
    if not request.startswith(PREFIX):
        return None
    value = json.loads(request[len(PREFIX):])
    if not isinstance(value, dict) or set(value) != {'name', 'arguments'} or not isinstance(value['name'], str) or not isinstance(value['arguments'], dict):
        raise ValueError('Solicitud directa requiere name y arguments; una sola herramienta')
    return {'type': 'tool', **value}
