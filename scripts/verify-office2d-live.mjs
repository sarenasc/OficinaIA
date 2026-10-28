// Real server: WebSocket, drag, persistence and REST recovery.
// Walking uses an explicitly labelled browser-only message fixture; no production data is fabricated.
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.OFFICE_BROWSER_EXECUTABLE,
});
const errors = [];
async function openOffice(page) {
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('http://127.0.0.1:1420');
  await page.locator('.local').filter({ hasText: 'Backend conectado' }).waitFor();
  await page.getByLabel('Filtrar oficina').selectOption({ label: 'Oficina Demo Analítica' });
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.getByRole('button', { name: 'Plano 2D', exact: true }).click();
  await page.locator('.desk').first().waitFor();
}
async function save(page) {
  await page.getByRole('button', { name: 'Guardar distribución', exact: true }).click();
  await page.getByRole('button', { name: 'Editar distribución', exact: true }).waitFor();
}
function coordinates(value) {
  return value
    .match(/translate\(([^,]+),([^\)]+)\)/)
    .slice(1)
    .map(Number);
}
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await openOffice(page);
  await page.getByText('En vivo · WebSocket conectado', { exact: false }).waitFor();
  await page
    .getByText(/Ollama conectado|Ollama sin conexión/)
    .first()
    .waitFor();
  const desk = page.locator('.desk').first();
  const original = coordinates(await desk.getAttribute('transform'));
  await page.getByRole('button', { name: 'Editar distribución', exact: true }).click();
  const box = await desk.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + 25);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 55, box.y + 50, { steps: 12 });
  await page.mouse.up();
  const moved = coordinates(await desk.getAttribute('transform'));
  if (Math.abs(moved[0] - original[0]) < 30) throw Error('Drag did not move the desk');
  await desk.focus();
  await desk.press('ArrowRight');
  const expected = coordinates(await desk.getAttribute('transform'));
  if (Math.abs(expected[0] - moved[0] - 10) > 0.1) throw Error('Keyboard move failed');
  await save(page);
  await page.reload();
  await page.getByLabel('Filtrar oficina').selectOption({ label: 'Oficina Demo Analítica' });
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.getByRole('button', { name: 'Plano 2D', exact: true }).click();
  await page.locator('.desk').first().waitFor();
  const persisted = coordinates(await page.locator('.desk').first().getAttribute('transform'));
  if (Math.abs(persisted[0] - expected[0]) > 0.1) throw Error('Dragged position was not saved');
  await page.getByRole('button', { name: 'Editar distribución', exact: true }).click();
  await page.locator('.desk').first().click();
  const inputs = page.locator('.scene-panel input');
  await inputs.nth(0).fill(String(original[0]));
  await inputs.nth(1).fill(String(original[1]));
  await save(page);
  await page.screenshot({ path: 'data/verification/oficina-2d-en-vivo.png', fullPage: true });

  const fallback = await browser.newPage();
  await fallback.routeWebSocket('**/ws/offices/**', (socket) => socket.close());
  await openOffice(fallback);
  await fallback.getByText('Recuperando conexión · respaldo REST', { exact: false }).waitFor();
  await fallback.close();

  const fixture = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  let clientSocket, snapshot;
  await fixture.routeWebSocket('**/ws/offices/**', (socket) => {
    clientSocket = socket;
    const upstream = socket.connectToServer();
    upstream.onMessage((message) => {
      const value = JSON.parse(String(message));
      if (value.agents) snapshot = value;
      socket.send(message);
    });
  });
  await openOffice(fixture);
  await fixture.getByText('En vivo · WebSocket conectado', { exact: false }).waitFor();
  const visualFixture = {
    ...snapshot,
    messages: [
      {
        id: 'browser-only-delegation-fixture',
        source_id: snapshot.agents[0].id,
        target_id: snapshot.agents[1].id,
        task_id: 'browser-only-fixture',
      },
      ...snapshot.messages,
    ],
  };
  clientSocket.send(JSON.stringify(visualFixture));
  await fixture.locator('[data-walking="true"]').first().waitFor();
  await fixture.waitForFunction(
    () =>
      document.querySelector('[data-walking="true"]')?.getAttribute('transform') !==
      'translate(0,0)',
  );
  await fixture.screenshot({ path: 'data/verification/oficina-2d-caminata-fixture.png' });
  await fixture.locator('[data-walking="true"]').waitFor({ state: 'detached', timeout: 15000 });
  clientSocket.send(
    JSON.stringify({
      ...visualFixture,
      messages: [
        { ...visualFixture.messages[0], id: 'browser-only-reduced-motion-fixture' },
        ...visualFixture.messages,
      ],
    }),
  );
  await fixture.locator('[data-walking="true"]').first().waitFor();
  await fixture.emulateMedia({ reducedMotion: 'reduce' });
  await fixture.locator('[data-walking="true"]').waitFor({ state: 'detached' });
  if (errors.length) throw Error(errors.join('\n'));
  console.log(
    JSON.stringify({
      status: 'passed',
      checks: [
        'real WebSocket',
        'pointer drag',
        'keyboard position',
        'saved layout',
        'REST fallback',
        'browser-only walking contract',
      ],
      browserErrors: errors,
    }),
  );
} finally {
  await browser.close();
}
