import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from app.tools import network
from conftest import create
from test_stage3_tools import approve, assign_connection, run, setup


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/slow":
                time.sleep(0.2)
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "http://169.254.169.254/latest/meta-data")
                self.end_headers()
                return
            content = b"team,goals\nA,2\nB,1\n" if self.path == "/sports.csv" else json.dumps({"fixture": "local-api", "games": 3}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv" if self.path == "/sports.csv" else "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass
    service = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{service.server_port}"
    service.shutdown()
    service.server_close()


@pytest.mark.parametrize("url", ["http://127.0.0.1", "http://localhost", "http://169.254.169.254", "http://[::1]", "http://10.0.0.1", "http://192.168.1.1"])
def test_ssrf_blocks_internal_and_metadata(url):
    with pytest.raises(PermissionError, match="SSRF"):
        network.addresses(url)


def test_real_http_transport_timeout_size_and_redirect_authorization(server):
    def allowed(url):
        if network.origin(url) != network.origin(server):
            raise PermissionError("redirect denied")
    result = network.request(server + "/api", allowed, allow_private=True)
    assert result["status"] == 200
    assert json.loads(result["body"])["games"] == 3
    with pytest.raises(TimeoutError):
        network.request(server + "/slow", allowed, timeout=0.05, allow_private=True)
    with pytest.raises(ValueError, match="tamaño"):
        network.request(server + "/api", allowed, max_bytes=5, allow_private=True)
    with pytest.raises(PermissionError, match="redirect"):
        network.request(server + "/redirect", allowed, allow_private=True)


def test_private_api_requires_explicit_approval_even_trusted(client, tmp_path, server):
    office, agent, resource = setup(client, tmp_path)
    connection = create(client, "connections", name="API local de prueba", kind="http_api",
                        config={"base_url": server, "auth": "none", "allow_private": True})
    assign_connection(client, agent, connection, ["connect", "select"])
    task = run(client, office, agent, "api.request", {"connection_id": connection["id"], "endpoint": "api", "method": "GET", "params": {}})
    assert task["status"] == "waiting_approval"
    task = approve(client, task)
    assert task["status"] == "completed", task
    assert json.loads(task["result"])["data"]["fixture"] == "local-api"
    saved = run(client, office, agent, "api.request", {"connection_id": connection["id"], "endpoint": "api",
                "destination": {"resource_id": resource["id"], "path": "respuesta.json"}})
    assert saved["status"] == "waiting_approval"
    assert approve(client, saved)["status"] == "completed"
    assert json.loads((tmp_path / "respuesta.json").read_text())["games"] == 3
    assert run(client, office, agent, "api.request", {"connection_id": connection["id"], "endpoint": "../outside"})["status"] == "error"


def test_web_download_local_fixture_pipeline_and_denied_source(client, tmp_path, server, monkeypatch):
    office, agent, resource = setup(client, tmp_path)
    url_resource = create(client, "resources", name="Origen de prueba", kind="url", path=server + "/")
    assignments = client.get(f"/api/agents/{agent['id']}/assignments").json()
    assignments["resources"].append({"resource_id": url_resource["id"], "permissions": ["read"]})
    client.put(f"/api/agents/{agent['id']}/assignments", json=assignments)
    # TEST ONLY: inject the local fixture's IP into public transport. Production keeps SSRF checks.
    original = network.addresses
    monkeypatch.setattr(network, "addresses", lambda url, allow_private=False, timeout=5: ["127.0.0.1"] if network.origin(url) == network.origin(server) else original(url, allow_private, timeout))
    task = run(client, office, agent, "web.download", {"url": server + "/sports.csv", "destination": {"resource_id": resource["id"]}})
    assert task["status"] == "completed", task
    assert (tmp_path / "sports.csv").read_text() == "team,goals\nA,2\nB,1\n"
    assert run(client, office, agent, "web.fetch", {"url": "http://example.invalid/unauthorized"})["status"] == "error"


def test_rate_limits_and_encoded_endpoint_escapes():
    key = "test-rate-" + str(time.monotonic())
    network.rate_limit(key, 1)
    with pytest.raises(ValueError, match="minuto"):
        network.rate_limit(key, 1)
    for url in ["file:///etc/passwd", "http://user:password@example.org/", "https://example.org/ok/%2e%2e/private"]:
        with pytest.raises(PermissionError):
            network.origin(url)


def test_private_api_exception_never_opens_cloud_metadata():
    with pytest.raises(PermissionError, match="SSRF"):
        network.addresses("http://169.254.169.254", allow_private=True)
