"""Standalone loopback server, compiled UI and fixed native worker."""
import argparse
import ctypes
import json
import multiprocessing
import os
import runpy
import secrets
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


def main():
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    if '--native-worker' in sys.argv:
        sys.argv = [str(bundled / 'app/execution/sports_worker.py'), *sys.argv[2:]]
        runpy.run_path(sys.argv[0], run_name='__main__')
        return
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--self-test', action='store_true', help='Prueba aislada; exige una carpeta nueva')
    parser.add_argument('--base-nueva', action='store_true',
                        help='Empieza con una base vacía; la actual se conserva apartada, no se borra')
    args = parser.parse_args()
    if args.self_test and (not args.data_dir or args.data_dir.exists()):
        raise ValueError('--self-test requiere --data-dir con una carpeta que no exista')
    root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else bundled
    directory = (args.data_dir or root / 'data').resolve()
    directory.mkdir(parents=True, exist_ok=True)
    os.chdir(root)
    token = secrets.token_urlsafe(32)
    os.environ['OFFICE_SESSION_TOKEN'] = token
    os.environ['OFFICE_DATA_DIR'] = str(directory)
    if getattr(sys, 'frozen', False):
        os.environ['OFFICE_NATIVE_EXECUTABLE'] = sys.executable
    else:
        sys.path.insert(0, str(root / 'backend'))
    from app.core.storage import database_path, reset
    # Outside OneDrive/Dropbox: synchronized SQLite files get corrupted.
    database = database_path(directory)
    if args.base_nueva:
        kept = reset(database)
        print('Base nueva. ' + ('Base anterior apartada como ' + str(kept) if kept else 'No había base anterior.'),
              flush=True)
    os.environ['OFFICE_DATABASE_URL'] = 'sqlite:///' + str(database)
    # Reserve-check before initializing the database or starting background jobs.
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', 38080))
        except OSError:
            print('ERROR: no se pudo reservar 127.0.0.1:38080. Compruebe si ya hay otra instancia abierta.', flush=True)
            raise
    import uvicorn
    from app.main import app
    from fastapi.staticfiles import StaticFiles
    app.mount('/', StaticFiles(directory=str(bundled / 'dist'), html=True), name='frontend')

    def open_when_ready():
        for _ in range(120):
            try:
                request = urllib.request.Request('http://127.0.0.1:38080/api/health',
                    headers={'Authorization': 'Bearer ' + token})
                with urllib.request.urlopen(request, timeout=1):
                    pass
                webbrowser.open('http://127.0.0.1:38080/#session=' + token)
                return
            except OSError:
                time.sleep(0.5)

    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=38080, access_log=False))
    failures = []

    def verify():
        try:
            for _ in range(200):
                if server.started:
                    break
                time.sleep(0.1)
            assert server.started, 'Servidor no inició'
            base = 'http://127.0.0.1:38080'

            def request(path, data=None):
                req = urllib.request.Request(base + '/api/' + path,
                    headers={'Authorization': 'Bearer ' + token, 'Origin': base,
                             'Content-Type': 'application/json'},
                    data=None if data is None else json.dumps(data).encode())
                with urllib.request.urlopen(req, timeout=30) as response:
                    return json.load(response)

            with urllib.request.urlopen(base) as response:
                assert '<html' in response.read().decode().lower()
            try:
                urllib.request.urlopen(base + '/api/agents')
                raise AssertionError('API sin token permitida')
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            assert request('agents') == []
            office = request('offices', {'name': 'Prueba EXE'})
            from websockets.sync.client import connect
            with connect('ws://127.0.0.1:38080/ws/offices/' + office['id'], origin=base) as ws:
                ws.send(json.dumps({'token': token}))
                assert isinstance(json.loads(ws.recv(timeout=10)), dict)
            agent = request('agents', {'name': 'Analista', 'office_id': office['id'],
                'permissions': ['python.execute'], 'mode': 'trusted'})
            tool = next(t for t in request('tools') if t['name'] == 'python.execute')
            req = urllib.request.Request(base + '/api/agents/' + agent['id'] + '/assignments',
                method='PUT', headers={'Authorization': 'Bearer ' + token, 'Origin': base,
                    'Content-Type': 'application/json'},
                data=json.dumps({'tools': [tool['id']], 'skills': [], 'resources': []}).encode())
            urllib.request.urlopen(req).close()
            procedure = request('procedures', {'name': 'Media', 'office_id': office['id'],
                'steps': [{'agent_id': agent['id'], 'tool': 'python.execute',
                    'arguments': {'operation': 'statistics.mean', 'parameters': {'values': [2, 4, 6]}}}]})
            task = request('tasks', {'office_id': office['id'], 'agent_id': agent['id'],
                'procedure_id': procedure['id'], 'request': 'Media sin Docker'})
            for _ in range(300):
                task = request('tasks/' + task['id'])
                if task['status'] in {'completed', 'error', 'waiting_approval'}:
                    break
                time.sleep(0.1)
            assert task['status'] == 'completed', task
            result = json.loads(task['result'])
            assert result['mean'] == 4 and result['backend'] == 'native', result
            assert request('execution/status')['native']['available']
            print('SELF-TEST OK: interfaz, token, origen, CRUD, tarea y worker nativo (media=4).', flush=True)
        except Exception as exc:
            failures.append(exc)
        finally:
            server.should_exit = True

    if args.self_test:
        threading.Thread(target=verify, daemon=True).start()
    elif not args.no_browser:
        threading.Thread(target=open_when_ready, daemon=True).start()
    print('Oficina IA sin Docker. Cierre esta ventana para detener el sistema.', flush=True)
    print('Datos: ' + str(directory), flush=True)
    print('Base de datos: ' + str(database), flush=True)
    server.run()
    if failures:
        raise failures[0]


if __name__ == '__main__':
    multiprocessing.freeze_support()
    try:
        main()
    except Exception as exc:
        if sys.platform == 'win32' and '--native-worker' not in sys.argv and '--self-test' not in sys.argv:
            ctypes.windll.user32.MessageBoxW(None, 'No se pudo iniciar Oficina IA.\n'
                'Compruebe que el puerto 38080 esté libre y que pueda escribir en la carpeta.\n\n' + str(exc),
                'Oficina IA', 0x10)
        raise
