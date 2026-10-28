"""Opt-in HTTP with pinned public DNS, no proxies and per-redirect authorization."""
import http.client
import ipaddress
import json
import socket
import ssl
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit

from sqlalchemy import select

from app.core.audit import SENSITIVE
from app.models import AgentConnection, AgentResource, Connection, Resource
from app.security.permissions import require_approval, resource_path
from app.security.secrets import secrets
from app.tools.files import publish_bytes

MAX_RESPONSE = 10 * 1024 * 1024
_requests = defaultdict(deque)
_lock = threading.Lock()
_dns = ThreadPoolExecutor(max_workers=4, thread_name_prefix="office-dns")


def origin(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise PermissionError("URL HTTP(S) sin credenciales requerida")
    if parsed.fragment or any(c in url for c in ("\r", "\n", "\\")):
        raise PermissionError("URL inválida")
    decoded = unquote(unquote(parsed.path))
    if ".." in decoded.split("/") or "\\" in decoded or any(c in decoded for c in ("\r", "\n")):
        raise PermissionError("URL con escapes de ruta no autorizados")
    return parsed.scheme, parsed.hostname.lower(), parsed.port or (443 if parsed.scheme == "https" else 80)


def addresses(url, allow_private=False, timeout=5):
    _, host, port = origin(url)
    pending = _dns.submit(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
    try:
        records = pending.result(timeout=timeout)
    except TimeoutError:
        pending.cancel()
        raise TimeoutError("DNS excedió el timeout") from None
    ips = list(dict.fromkeys(r[4][0] for r in records))
    for value in ips:
        ip = ipaddress.ip_address(value)
        if ip.is_link_local or ip.is_unspecified or ip.is_multicast or ip.is_reserved and not ip.is_loopback:
            raise PermissionError("SSRF: metadatos y direcciones especiales siempre bloqueados")
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips) and not allow_private:
        raise PermissionError("SSRF: destino interno, reservado o metadatos bloqueado")
    return ips


def rate_limit(key, limit=30):
    with _lock:
        now = time.monotonic()
        queue = _requests[key]
        while queue and now - queue[0] > 60:
            queue.popleft()
        if len(queue) >= limit:
            raise ValueError("Límite HTTP de solicitudes por minuto alcanzado; espere")
        queue.append(now)


def request(url, authorize_url, timeout=20, headers=None, method="GET", body=None, allow_private=False, max_bytes=MAX_RESPONSE):
    deadline = time.monotonic() + timeout
    for _ in range(4):
        authorize_url(url)
        ips = addresses(url, allow_private, min(5, max(0.01, deadline - time.monotonic())))
        parsed = urlsplit(url)
        scheme, host, port = origin(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("HTTP excedió el timeout")
        connection = http.client.HTTPConnection(host, port, timeout=remaining)
        sock = socket.create_connection((ips[0], port), timeout=remaining)
        close_connection = connection.close
        response = None
        try:
            if scheme == "https":
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            connection.sock = sock
            # HTTP/1.0 may close the connection object after headers while its response
            # file still owns the socket. Keep it live to enforce the total read deadline.
            connection.close = lambda: None
            connection.request(method, urlunsplit(("", "", parsed.path or "/", parsed.query, "")), body=body,
                               headers={"User-Agent": "OficinaIA/Etapa3", "Accept-Encoding": "identity", **(headers or {})})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                if method != "GET":
                    raise PermissionError("No se siguen redirecciones de operaciones de escritura")
                destination = urljoin(url, response.getheader("Location", ""))
                if origin(destination) != origin(url) and headers:
                    raise PermissionError("No se reenvían credenciales a otra procedencia")
                if scheme == "https" and origin(destination)[0] != "https":
                    raise PermissionError("Redirección a HTTP inseguro bloqueada")
                url = destination
                continue
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError("Respuesta comprimida no admitida; solicite identity")
            if int(response.getheader("Content-Length", "0")) > max_bytes:
                raise ValueError("HTTP excede el tamaño máximo")
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("HTTP excedió el timeout")
                sock.settimeout(remaining)
                chunk = response.read1(min(65536, max_bytes + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("HTTP excede el tamaño máximo")
                chunks.append(chunk)
            return {"url": url, "status": response.status, "content_type": response.getheader("Content-Type", ""),
                    "body": b"".join(chunks), "consulted_at": datetime.now(timezone.utc).isoformat(), "errors": []}
        finally:
            if response is not None:
                response.close()
            close_connection()
            sock.close()
    raise ValueError("Demasiadas redirecciones HTTP")


def web_authorizer(session, agent):
    roots = [r.path for r in session.scalars(select(Resource).join(AgentResource)
             .where(AgentResource.agent_id == agent.id, Resource.kind == "url", Resource.active.is_(True)))
             if "read" in session.get(AgentResource, (agent.id, r.id)).permissions]

    def authorize(url):
        target = urlsplit(url)
        if not any(origin(url) == origin(root) and (target.path or "/").startswith(urlsplit(root).path.rstrip("/") + "/")
                   or origin(url) == origin(root) and target.path == urlsplit(root).path for root in roots):
            raise PermissionError("URL no asignada como recurso con permiso read")
    return authorize


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data.strip())


def checked_connection(session, agent, connection_id, kind, write=False):
    connection = session.get(Connection, connection_id)
    assignment = session.get(AgentConnection, (agent.id, connection_id))
    required = {"connect", "execute" if write else "select"}
    if not connection or not connection.active or connection.kind not in kind or not assignment or not required.issubset(assignment.permissions):
        raise PermissionError("Conexión externa no asignada con permisos suficientes")
    return connection


def api_request(session, task, agent, args):
    method = args.get("method", "GET")
    connection = checked_connection(session, agent, args["connection_id"], {"http_api"}, method != "GET")
    from app.tools.connections import validate_connection_config
    validate_connection_config(connection.kind, connection.config, connection.active)
    config = connection.config
    base = config["base_url"].rstrip("/") + "/"
    endpoint = args["endpoint"]
    decoded = unquote(unquote(endpoint))
    if decoded.startswith(("/", "\\")) or ".." in decoded or ":" in decoded or "\\" in decoded:
        raise PermissionError("Endpoint debe ser relativo a la API configurada, sin escapes")
    url = urljoin(base, endpoint)
    params = args.get("params", {})
    if any(SENSITIVE.search(key) for key in params):
        raise ValueError("Las credenciales API se configuran en el almacén seguro, no en params")
    if args.get("destination"):
        destination = args["destination"]
        if not destination["path"].lower().endswith(".json"):
            raise ValueError("La respuesta API se guarda como .json")
        target = resource_path(session, agent, destination["resource_id"], destination["path"], "create")
        if target.exists():
            raise ValueError("La salida API ya existe; use otro nombre para evitar repetir una operación externa al aprobar sobrescrituras")
    if method == "GET":
        parsed = urlsplit(url)
        url = urlunsplit(parsed._replace(query=urlencode(parse_qsl(parsed.query) + list(params.items()))))
    def authorize(target):
        if origin(target) != origin(base) or not urlsplit(target).path.startswith(urlsplit(base).path):
            raise PermissionError("La petición escapa de la API configurada")
    private = bool(config.get("allow_private", False))
    if private or method != "GET":
        require_approval(session, task, agent, "api-request", {"connection_id": connection.id, "args": args,
                         "origin": origin(base), "allow_private": private},
                         "Autorizar llamada API de escritura o destino privado explícito")
    credential = secrets.get(connection.credential_ref)
    headers = {"Accept": "application/json"}
    if credential and config.get("auth", "bearer") != "none":
        if origin(base)[0] != "https":
            raise PermissionError("No se envían credenciales por HTTP")
        auth = config.get("auth", "bearer")
        headers["Authorization" if auth == "bearer" else config.get("auth_header", "X-API-Key")] = (
            "Bearer " + credential if auth == "bearer" else credential)
    rate_limit(agent.id + connection.id, config.get("requests_per_minute", 30))
    if method != "GET":
        headers["Content-Type"] = "application/json"
    result = request(url, authorize, timeout=20, headers=headers, method=method,
                     body=json.dumps(params).encode() if method != "GET" else None, allow_private=private)
    if result["status"] >= 400:
        raise ValueError(f"API devolvió HTTP {result['status']}")
    try:
        content = result.pop("body")
        if credential:
            content = content.replace(credential.encode("utf-8"), b"[REDACTED]")
        data = json.loads(content) if content else None
    except (ValueError, UnicodeError):
        raise ValueError("La API no devolvió JSON válido") from None
    if args.get("destination"):
        destination = args["destination"]
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        if not destination["path"].lower().endswith(".json"):
            raise ValueError("La respuesta API se guarda como .json")
        saved = publish_bytes(session, task, agent, destination["resource_id"], destination["path"], content, "api.request")
        return {**result, **saved, "data_saved": True,
                "dataset_ref": {"resource_id": destination["resource_id"], "path": destination["path"]},
                "record_count": len(data) if isinstance(data, list) else None}
    return {**result, "data": data}


def web_search(session, agent, args):
    connections = list(session.scalars(select(Connection).join(AgentConnection)
                       .where(AgentConnection.agent_id == agent.id, Connection.kind == "web_search", Connection.active.is_(True))))
    if len(connections) != 1:
        raise ValueError("Asigne exactamente una conexión de búsqueda web activa al agente")
    connection = checked_connection(session, agent, connections[0].id, {"web_search"})
    credential = secrets.get(connection.credential_ref)
    if not credential:
        raise ValueError("Configure la credencial de Brave Search en el almacén seguro")
    base = "https://api.search.brave.com/res/v1/web/search"
    params = {"q": args["query"], "count": args.get("max_results", 5), "search_lang": args.get("language", "es")}
    if args.get("date_range"):
        params["freshness"] = args["date_range"]
    rate_limit(agent.id + connection.id, connection.config.get("requests_per_minute", 30))
    response = request(base + "?" + urlencode(params), lambda target: None if origin(target) == origin(base) else
                       (_ for _ in ()).throw(PermissionError("Destino de búsqueda inválido")),
                       headers={"X-Subscription-Token": credential, "Accept": "application/json"})
    if response["status"] != 200:
        raise ValueError(f"Búsqueda devolvió HTTP {response['status']}")
    data = json.loads(response["body"])
    return {"results": [{"title": item.get("title"), "url": item.get("url"), "description": item.get("description"),
                          "date": item.get("page_age"), "source": "Brave Search"}
                         for item in data.get("web", {}).get("results", [])[:params["count"]]],
            "consulted_at": response["consulted_at"]}


def web_tool(session, task, agent, kind, args):
    if kind == "web.search":
        return web_search(session, agent, args)
    if kind == "web.fetch" and args.get("destination"):
        destination = args["destination"]
        if not destination["path"].lower().endswith(".txt"):
            raise ValueError("web.fetch guarda texto como .txt; datasets CSV/JSON/XLSX usan web.download")
        target = resource_path(session, agent, destination["resource_id"], destination["path"], "create")
        if target.exists():
            raise ValueError("Salida web existente; use otro nombre para evitar repetir la consulta")
    rate_limit(agent.id + origin(args["url"])[1])
    response = request(args["url"], web_authorizer(session, agent), timeout=args.get("timeout", 20))
    if response["status"] >= 400:
        raise ValueError(f"Web devolvió HTTP {response['status']}")
    body = response.pop("body")
    if kind == "web.fetch":
        text = body.decode("utf-8", errors="replace")
        if "html" in response["content_type"]:
            parser = PageText()
            parser.feed(text)
            text = "\n".join(part for part in parser.parts if part)
        saved = {}
        if args.get("destination"):
            destination = args["destination"]
            saved = publish_bytes(session, task, agent, destination["resource_id"], destination["path"],
                                  text.encode("utf-8"), "web.fetch")
            saved["dataset_ref"] = {"resource_id": destination["resource_id"], "path": destination["path"]}
        return {**response, **saved, "content": text[:2000], "truncated": len(text) > 2000,
                "content_chars": len(text), "data_saved": bool(saved),
                "notice": "Vista parcial; use destination para conservar el texto completo y web.download para datasets."}
    destination = args["destination"]
    filename = args.get("filename") or PurePosixPath(urlsplit(response["url"]).path).name
    if not filename or "/" in filename or "\\" in filename:
        raise ValueError("Nombre de dataset inválido")
    suffix = PurePosixPath(filename).suffix.lower()
    mime = response["content_type"].split(";")[0].strip().lower()
    allowed = {".csv": {"text/csv", "application/csv", "text/plain"}, ".json": {"application/json", "text/plain"},
               ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}}
    if suffix not in allowed or mime not in allowed[suffix]:
        raise ValueError("Formato o Content-Type de dataset no permitido")
    if suffix == ".json":
        json.loads(body)
    elif suffix == ".xlsx":
        from io import BytesIO
        from zipfile import ZipFile

        from openpyxl import load_workbook
        with ZipFile(BytesIO(body)) as archive:
            files = archive.infolist()
            if len(files) > 1000 or sum(file.file_size for file in files) > 50 * 1024 * 1024:
                raise ValueError("Excel descargado excede límites de expansión ZIP")
        book = load_workbook(BytesIO(body), read_only=True)
        book.close()
    else:
        body.decode("utf-8-sig")
    published = publish_bytes(session, task, agent, destination["resource_id"],
                              destination.get("path", "").rstrip("/") + "/" + filename
                              if destination.get("path") else filename, body, kind)
    relative = destination.get("path", "").rstrip("/") + "/" + filename if destination.get("path") else filename
    return {**response, **published, "dataset_ref": {"resource_id": destination["resource_id"], "path": relative}}
