// End-to-end verification with a disposable database; never loads the user's data.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = process.cwd();
const directory = path.join(root, 'data', 'verification', `floorplan-${randomUUID()}`);
await mkdir(directory, { recursive: true });
const base = 'http://127.0.0.1:38181';
const browserBase = 'http://127.0.0.1:38080';
const token = randomUUID();
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.OFFICE_PLAYWRIGHT_MODULE);
// Refuse to contend with a running application.
try {
  await fetch(base, { signal: AbortSignal.timeout(1500) });
  throw new Error('Puerto de prueba 38181 ocupado');
} catch (e) {
  if (e.message === 'Puerto de prueba 38181 ocupado') throw e;
}
const server = spawn(
  process.env.OFFICE_TEST_PYTHON || 'python',
  [
    '-c',
    "from app.main import app; from fastapi.staticfiles import StaticFiles; import uvicorn; app.mount('/', StaticFiles(directory='dist', html=True)); uvicorn.run(app, host='127.0.0.1', port=38181)",
  ],
  {
    cwd: root,
    windowsHide: true,
    env: {
      ...process.env,
      OFFICE_DATA_DIR: directory,
      OFFICE_DATABASE_URL: `sqlite:///${path.join(directory, 'office.db')}`,
      OFFICE_SESSION_TOKEN: token,
    },
  },
);
let log = '';
server.stdout.on('data', (d) => {
  log += d;
});
server.stderr.on('data', (d) => {
  log += d;
});
let browser;
let page;
try {
  const api = async (route, data) => {
    const response = await fetch(`${base}/api/${route}`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      method: data ? 'POST' : 'GET',
      body: data ? JSON.stringify(data) : undefined,
    });
    assert(response.ok, await response.clone().text());
    return response.json();
  };
  let ready = false;
  for (let i = 0; i < 120; i++) {
    if (server.exitCode !== null) throw new Error(log);
    try {
      await api('health');
      ready = true;
      break;
    } catch {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  assert(ready, log);
  const office = await api('offices', { name: 'Prueba constructor' });
  await api('agents', { name: 'Ana', office_id: office.id });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.OFFICE_BROWSER_EXECUTABLE,
    args: ['--enable-unsafe-swiftshader'],
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  // Keep the production origin while forwarding every request to the isolated server.
  await page.route(`${browserBase}/**`, async (route) => {
    try {
      const response = await route.fetch({ url: route.request().url().replace(browserBase, base) });
      await route.fulfill({ status: response.status(), headers: { ...response.headers(), 'access-control-allow-origin': browserBase }, body: await response.body() });
    } catch {
      await route.abort().catch(() => {});
    }
  });
  await page.addInitScript(() => {
    const NativeWebSocket = window.WebSocket;
    window.WebSocket = class extends NativeWebSocket {
      constructor(url, protocols) {
        super(String(url).replace('127.0.0.1:38080', '127.0.0.1:38181'), protocols);
      }
    };
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`${browserBase}/#session=${token}`);
  await page.locator('.local').filter({ hasText: 'Backend conectado' }).waitFor();
  await page.getByLabel('Filtrar oficina').selectOption(office.id);
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.getByRole('button', { name: 'Construir oficina', exact: true }).click();
  await page.getByRole('button', { name: '+ Sala', exact: true }).click();
  const room = page.locator('.floorplan-cards > fieldset').first();
  await room.getByLabel('Nombre', { exact: true }).fill('Reuniones');
  await room.getByLabel('Ancho', { exact: true }).fill('400');
  await room.getByLabel('Fondo', { exact: true }).fill('400');
  await room.getByLabel('Puerta', { exact: true }).selectOption('right');
  await page.getByRole('button', { name: 'Sala Reuniones', exact: true }).focus();
  await page.keyboard.press('ArrowRight');
  await page.getByRole('button', { name: '+ División', exact: true }).click();
  const plan = page.locator('.scene-canvas svg');
  await plan.scrollIntoViewIfNeeded();
  const dragPoints = await plan.evaluate(svg => {
    const matrix = svg.getScreenCTM();
    const a = new DOMPoint(440, 180).matrixTransform(matrix);
    const b = new DOMPoint(560, 180).matrixTransform(matrix);
    return { from: { x: a.x, y: a.y }, to: { x: b.x, y: b.y } };
  });
  await page.mouse.move(dragPoints.from.x, dragPoints.from.y);
  await page.mouse.down();
  await page.mouse.move(dragPoints.to.x, dragPoints.to.y, { steps: 8 });
  await page.mouse.up();
  await page.getByRole('button', { name: 'Guardar distribución', exact: true }).click();
  await page.getByRole('button', { name: 'Construir oficina', exact: true }).waitFor();
  let scene = await api(`offices/${office.id}/scene`);
  assert.equal(scene.layout.rooms[0].name, 'Reuniones');
  assert.equal(scene.layout.rooms[0].x, 100);
  assert.equal(scene.layout.rooms[0].width, 400);
  assert.equal(scene.layout.rooms[0].door, 'right');
  assert.equal(scene.layout.partitions.length, 1);
  assert.equal(scene.layout.partitions[0].x, 560);
  await page.screenshot({ path: path.join(directory, 'plano-2d.png'), fullPage: true });
  // Cancel must discard a removed room.
  await page.getByRole('button', { name: 'Construir oficina', exact: true }).click();
  await page.getByRole('button', { name: 'Eliminar sala', exact: true }).click();
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page.reload();
  await page.locator('.local').filter({ hasText: 'Backend conectado' }).waitFor();
  await page.getByLabel('Filtrar oficina').selectOption(office.id);
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.locator('.office-3d-canvas canvas').waitFor();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(directory, 'oficina-3d.png'), fullPage: true });
  scene = await api(`offices/${office.id}/scene`);
  assert.equal(scene.layout.rooms.length, 1);
  assert.equal(scene.layout.partitions.length, 1);
  assert.deepEqual(errors, []);
  console.log(
    'PASS: crear sala y división, dimensiones, puerta, movimiento, guardar, cancelar, recargar y vista 3D.',
  );
  console.log(`Capturas: ${directory}`);
} catch (error) {
  if (page)
    await page
      .screenshot({ path: path.join(directory, 'failure.png'), fullPage: true })
      .catch(() => {});
  console.error('Fallo de prueba:', error);
  throw error;
} finally {
  if (browser) await browser.close();
  server.kill();
  await writeFile(path.join(directory, 'server.log'), log);
}
