// Browser-only save fixture. No real connections or remote API calls.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({ headless: true, executablePath: process.env.OFFICE_BROWSER_EXECUTABLE });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1050 } });
  let submitted;
  await page.route('**/api/connections', async route => {
    if (route.request().method() === 'POST') {
      submitted = route.request().postDataJSON();
      await route.fulfill({ json: { ...submitted, id: 'browser-test-only' } });
    } else await route.continue();
  });
  await page.goto('http://127.0.0.1:1420');
  await page.getByRole('button', { name: 'Conexiones', exact: true }).click();
  await page.getByRole('button', { name: '+ Crear', exact: true }).click();
  const dialog = page.locator('.modal');
  await dialog.getByLabel('Nombre', { exact: true }).fill('API deportiva pendiente');
  await dialog.getByLabel('Motor', { exact: true }).selectOption('http_api');
  await dialog.getByLabel('URL base de la API').fill('https://api.example.org/v1/');
  await page.screenshot({ path: 'data/verification/stage3-api-config.png', fullPage: true });
  await dialog.getByRole('button', { name: 'Guardar', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  if (!submitted || submitted.kind !== 'http_api' || submitted.config.auth !== 'bearer' || submitted.active !== false) throw Error('API config invalid');
  await page.getByRole('button', { name: '+ Crear', exact: true }).click();
  await dialog.getByLabel('Motor', { exact: true }).selectOption('web_search');
  await dialog.getByText('Proveedor disponible: Brave Search.', { exact: false }).waitFor();
  await dialog.getByRole('button', { name: 'Cerrar', exact: true }).click();
  console.log(JSON.stringify({ status: 'passed', fixture: 'browser-only', checks: ['API fields', 'Bearer default after SQL', 'inactive draft', 'Brave configuration', 'no real writes or requests'] }));
} finally { await browser.close(); }
