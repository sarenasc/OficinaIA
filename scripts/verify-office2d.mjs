import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.OFFICE_BROWSER_EXECUTABLE,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
try {
  await page.goto('http://127.0.0.1:1420');
  await page.locator('.local').filter({ hasText: 'Backend conectado' }).waitFor();
  await page.getByLabel('Filtrar oficina').selectOption({ label: 'Oficina Demo Analítica' });
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.getByRole('button', { name: 'Plano 2D', exact: true }).click();
  await page.locator('.desk').first().waitFor();
  await page.locator('.desk').first().click();
  await page.getByRole('button', { name: 'Editar distribución', exact: true }).click();
  await page.locator('.scene-panel input').first().fill('350');
  await page.getByRole('button', { name: 'Guardar distribución', exact: true }).click();
  await page.getByRole('button', { name: 'Editar distribución', exact: true }).waitFor();
  await page.reload();
  await page.getByLabel('Filtrar oficina').selectOption({ label: 'Oficina Demo Analítica' });
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.getByRole('button', { name: 'Plano 2D', exact: true }).click();
  await page.locator('.desk').first().waitFor();
  if (!(await page.locator('.desk').first().getAttribute('transform')).includes('350,'))
    throw Error('Plano no persistió');
  await page.locator('.desk').first().click();
  await page.getByRole('button', { name: 'Editar distribución', exact: true }).click();
  await page.locator('.scene-panel input').first().fill('220');
  await page.getByRole('button', { name: 'Guardar distribución', exact: true }).click();
  await page.getByRole('button', { name: 'Editar distribución', exact: true }).waitFor();
  await page.screenshot({ path: 'data/verification/oficina-2d.png', fullPage: true });
  if (errors.length) throw Error(errors.join('\n'));
  console.log('Oficina 2D: personas, edición y persistencia verificadas');
} finally {
  await browser.close();
}
