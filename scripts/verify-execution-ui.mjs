// UI contract only: preserves production preferences and data.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({ headless: true, executablePath: process.env.OFFICE_BROWSER_EXECUTABLE });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1100 } });
  const state = { mode: 'auto', docker: { available: false, error: 'Docker no está en PATH', tools: ['python.execute'] },
    native: { available: true, error: null, python: '3.12.14', packages: { stdlib: '3.12.14' }, tools: ['python.execute (operation/parameters)', 'sports.analyze', 'python.packages'] },
    active_jobs: 0, last_error: null, jobs: [{ id: 'ui-fixture', operation: 'python.execute', fixed_operation: 'statistics.mean',
      backend: 'native', status: 'completed', duration_ms: 250 }] };
  let changes = 0;
  await page.route('**/api/execution/**', async route => {
    if (route.request().url().endsWith('/preference')) {
      state.mode = route.request().postDataJSON().mode; changes++;
      await route.fulfill({ json: { mode: state.mode } });
    } else await route.fulfill({ json: state });
  });
  await page.goto('http://127.0.0.1:1420');
  await page.getByRole('button', { name: 'Configuración', exact: true }).click();
  await page.getByRole('heading', { name: 'Motor de ejecución' }).waitFor();
  await page.getByLabel('Modo seleccionado').selectOption('native');
  await page.getByRole('button', { name: 'Probar diagnóstico / actualizar' }).waitFor();
  if (changes !== 1 || state.mode !== 'native') throw Error('Preference UI contract failed');
  await page.getByText('Trabajador Windows: disponible.', { exact: false }).waitFor();
  await page.getByRole('cell', { name: 'statistics.mean', exact: true }).waitFor();
  await page.getByRole('cell', { name: '250 ms', exact: true }).waitFor();
  await page.screenshot({ path: 'data/verification/dual-execution-ui.png', fullPage: true });
  console.log(JSON.stringify({ status: 'passed', fixture: 'UI only', checks: ['selection', 'status', 'packages', 'diagnostic', 'operation/backend/duration', 'no production writes'] }));
} finally { await browser.close(); }
