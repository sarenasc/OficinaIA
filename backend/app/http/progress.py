import asyncio
import hmac
import json

from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from app.core.config import TOKEN
from app.core.db import SessionLocal
from app.http.common import ws_router
from app.http.tasks import task_details


@ws_router.websocket("/ws/tasks/{id}")
async def task_socket(websocket: WebSocket, id: str):
    origin = websocket.headers.get("origin", "")
    if origin not in {
        "http://127.0.0.1:38080",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    }:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        credentials = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        if not TOKEN or not hmac.compare_digest(str(credentials.get("token", "")), TOKEN):
            await websocket.close(code=1008)
            return
        previous = ""
        while True:
            with SessionLocal() as session:
                details = task_details(id, session)
            encoded = json.dumps(details, ensure_ascii=False)
            if encoded != previous:
                await websocket.send_text(encoded)
                previous = encoded
            if details["task"]["status"] in {"completed", "error", "cancelled"}:
                await websocket.close()
                return
            await asyncio.sleep(1)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        return


@ws_router.websocket("/ws/offices/{id}")
async def office_socket(websocket: WebSocket, id: str):
    from app.http.scene import scene

    if websocket.headers.get("origin", "") not in {
        "http://127.0.0.1:38080",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    }:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        credentials = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        if (
            not isinstance(credentials, dict)
            or not TOKEN
            or not hmac.compare_digest(str(credentials.get("token", "")), TOKEN)
        ):
            await websocket.close(code=1008)
            return
        previous = ""
        ticks = 0
        while True:
            with SessionLocal() as session:
                details = scene(id, session)
            encoded = json.dumps(details, ensure_ascii=False)
            if previous != encoded:
                await websocket.send_text(encoded)
                previous = encoded
            elif ticks % 5 == 0:
                await websocket.send_json({"type": "heartbeat"})
            ticks += 1
            # Receive disconnects promptly even when the office is idle.
            try:
                incoming = await asyncio.wait_for(websocket.receive(), timeout=1)
                if incoming["type"] == "websocket.disconnect":
                    return
            except asyncio.TimeoutError:
                pass
    except HTTPException:
        await websocket.close(code=1008)
    except ValueError:
        await websocket.close(code=1008)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        return
