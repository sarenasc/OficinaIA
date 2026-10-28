// Browser-only error fixture: no tasks or production records are modified.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({ headless: true, executablePath: process.env.OFFICE_BROWSER_EXECUTABLE,
  args: ['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.routeWebSocket('**/ws/offices/**', socket => socket.close());
  await page.route('**/api/offices/*/scene', async route => {
    const response = await route.fetch();
    const scene = await response.json();
    if (scene.agents[0]) scene.agents[0].activity = {
      task_id: 'browser-test-only', request: 'Leer ventas', task_status: 'error', tool: 'excel.read',
      execution_status: 'error', resource: 'Prueba Oficina', path: '/ventas',
      error: 'La ruta resuelta escapa del recurso autorizado',
    };
    await route.fulfill({ response, json: scene });
  });
  await page.goto('http://127.0.0.1:1420');
  await page.getByLabel('Filtrar oficina').selectOption({ label: 'Oficina Demo Analítica' });
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.locator('.team-activity').getByText('La ruta resuelta escapa del recurso autorizado', { exact: false }).waitFor();
  await page.locator('.team-activity').getByText('Recurso: Prueba Oficina').waitFor();
  await page.locator('.team-activity').getByText('Archivo: /ventas').waitFor();
  await page.getByRole('button', { name: 'Plano 2D', exact: true }).click();
  await page.locator('.team-activity').getByText('La ruta resuelta escapa del recurso autorizado', { exact: false }).waitFor();
  const room = await page.locator('.scene-body').boundingBox();
  const activity = await page.locator('.team-activity').boundingBox();
  if (!room || !activity || activity.y < room.y + room.height - 1) throw Error('Activity must be below the office');
  await page.setViewportSize({ width: 750, height: 1100 });
  const mobile = await page.locator('.team-activity').boundingBox();
  if (!mobile || mobile.x + mobile.width > 751) throw Error('Activity overflows mobile viewport');
  await page.setViewportSize({ width: 1600, height: 1100 });
  await page.screenshot({ path: 'data/verification/office-activity.png', fullPage: true });
  if (errors.length) throw Error(errors.join('\n'));
  await page.unrouteAll({ behavior: 'wait' });
  console.log(JSON.stringify({ status: 'passed', fixture: 'browser-only', checks: ['all-agent activity panel', 'resource and path', 'visible error', '2D/3D shared panel'], errors }));
} finally { await browser.close(); }
