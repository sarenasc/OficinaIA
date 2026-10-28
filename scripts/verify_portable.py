"""Verify the compiled EXE using a new disposable database, without opening a browser."""
from pathlib import Path
import os
import socket
import sqlite3
import subprocess
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
executable = ROOT / 'Oficina IA.exe'
directory = ROOT / 'data/verification' / ('portable-' + uuid4().hex[:8])
env = dict(os.environ)
temp = ROOT / 'build/temp'
temp.mkdir(parents=True, exist_ok=True)
env.update(TEMP=str(temp), TMP=str(temp))
env.pop('PYTHONPATH', None)
env['PATH'] = str(Path(os.environ['SYSTEMROOT']) / 'System32')
directory.parent.mkdir(parents=True, exist_ok=True)
log_path = directory.parent / (directory.name + '.log')
with log_path.open('w', encoding='utf-8') as log:
    process = subprocess.Popen([str(executable), '--self-test', '--data-dir', str(directory)],
        cwd=ROOT, env=env, stdout=log, stderr=log)
    try:
        process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'], check=False)
        raise
output = log_path.read_text(encoding='utf-8')
print(output)
assert process.returncode == 0, process.returncode
assert 'SELF-TEST OK' in output
with sqlite3.connect(directory / 'office.db') as connection:
    assert connection.execute('SELECT count(*) FROM offices').fetchone()[0] == 1
    assert connection.execute('SELECT count(*) FROM agents').fetchone()[0] == 1
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 38080))
    probe.listen()
    conflict = subprocess.run([str(executable), '--self-test', '--data-dir', str(directory) + '-port'],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert conflict.returncode != 0
print('PASS: compiled EXE, persisted SQLite, clean shutdown and occupied port rejection.')
