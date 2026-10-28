// Intercept every skill import write: no real skill is created.
import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
const { chromium } = createRequire(import.meta.url)(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({ headless: true, executablePath: process.env.OFFICE_BROWSER_EXECUTABLE });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 950 } });
  let previews = 0, writes = 0;
  await page.route('**/api/skills/import?*', async route => {
    const batch = route.request().postDataJSON();
    const preview = new URL(route.request().url()).searchParams.get('preview') === 'true';
    preview ? previews++ : writes++;
    await route.fulfill({ json: { count: batch.skills.length, skills: batch.skills, created: !preview } });
  });
  await page.goto('http://127.0.0.1:1420');
  await page.getByRole('button', { name: 'Habilidades', exact: true }).click();
  await page.getByRole('button', { name: 'Importar JSON', exact: true }).click();
  const dialog = page.getByRole('dialog');
  const content = await readFile('docs/plantilla-habilidades.json');
  await dialog.getByLabel('Archivo JSON').setInputFiles({ name: 'habilidades.json', mimeType: 'application/json', buffer: content });
  await dialog.getByRole('button', { name: 'Validar y ver habilidades', exact: true }).click();
  await dialog.getByRole('button', { name: 'Crear habilidades (1)', exact: true }).waitFor();
  if (writes || previews !== 1) throw Error('Preview created skills');
  await dialog.locator('summary').click();
  await dialog.getByText('Herramientas requeridas:', { exact: false }).waitFor();
  await page.screenshot({ path: 'data/verification/skill-import.png', fullPage: true });
  await dialog.getByLabel('Archivo JSON').setInputFiles({ name: 'invalid.json', mimeType: 'application/json', buffer: Buffer.from('{bad') });
  await dialog.getByRole('alert').waitFor();
  if (await dialog.getByRole('button', { name: 'Crear habilidades (1)', exact: true }).count()) throw Error('Stale preview');
  await dialog.getByLabel('Archivo JSON').setInputFiles({ name: 'habilidades.json', mimeType: 'application/json', buffer: content });
  await dialog.getByRole('button', { name: 'Validar y ver habilidades', exact: true }).click();
  await dialog.getByRole('button', { name: 'Crear habilidades (1)', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  if (writes !== 1) throw Error('Import missing');
  console.log(JSON.stringify({ status: 'passed', fixture: 'browser-only', checks: ['preview', 'full instructions shown', 'invalid JSON clears preview', 'explicit import'] }));
} finally { await browser.close(); }
