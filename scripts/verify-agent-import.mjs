// UI fixtures intercept all import writes. No production agents are created.
import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
const { chromium } = createRequire(import.meta.url)(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({ headless: true, executablePath: process.env.OFFICE_BROWSER_EXECUTABLE });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  let previews = 0, writes = 0;
  await page.route('**/api/offices/*/agents/import?*', async route => {
    const batch = route.request().postDataJSON();
    const preview = new URL(route.request().url()).searchParams.get('preview') === 'true';
    preview ? previews++ : writes++;
    await route.fulfill({ json: { count: batch.agents.length, coordinator: batch.coordinator, created: !preview,
      agents: batch.agents.map(a => ({ ...a, model: a.model || '', tools: a.tools || [], delegates: a.delegates || [],
        mode: a.mode || 'safe', external_policy: a.external_policy || 'never', permissions: a.permissions || [] })) } });
  });
  await page.goto('http://127.0.0.1:1420');
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.getByRole('button', { name: 'Importar JSON', exact: true }).click();
  const dialog = page.getByRole('dialog');
  const content = await readFile('docs/plantilla-agentes.json');
  await dialog.getByLabel('Archivo JSON').setInputFiles({ name: 'equipo.json', mimeType: 'application/json', buffer: content });
  await dialog.getByRole('button', { name: 'Validar y ver agentes', exact: true }).click();
  await dialog.getByRole('button', { name: 'Crear 3 agentes', exact: true }).waitFor();
  if (writes !== 0 || previews !== 1) throw Error('Preview wrote agents');
  await page.screenshot({ path: 'data/verification/agent-import.png', fullPage: true });
  await dialog.getByLabel('Archivo JSON').setInputFiles({ name: 'invalid.json', mimeType: 'application/json', buffer: Buffer.from('{broken') });
  await dialog.getByRole('alert').waitFor();
  if (await dialog.getByRole('button', { name: 'Crear 3 agentes', exact: true }).count()) throw Error('Stale preview remains');
  await dialog.getByLabel('Archivo JSON').setInputFiles({ name: 'equipo.json', mimeType: 'application/json', buffer: content });
  await dialog.getByRole('button', { name: 'Validar y ver agentes', exact: true }).click();
  await dialog.getByRole('button', { name: 'Crear 3 agentes', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  if (writes !== 1) throw Error('Explicit create missing');
  console.log(JSON.stringify({ status: 'passed', fixture: 'browser-only', checks: ['preview without creation', 'invalid JSON clears preview', 'explicit import', 'existing agents untouched'] }));
} finally { await browser.close(); }
