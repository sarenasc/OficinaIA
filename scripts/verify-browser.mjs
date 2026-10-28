// Exercises the actual frontend against a running launch.py --local session.
// Set OFFICE_PLAYWRIGHT_MODULE to an installed playwright package if not local.
import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.OFFICE_PLAYWRIGHT_MODULE || 'playwright');
const output = path.resolve('data/verification');
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.OFFICE_BROWSER_EXECUTABLE || undefined,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
try {
  await page.goto('http://127.0.0.1:1420');
  await page.locator('.local').filter({ hasText: 'Backend conectado' }).waitFor();
  if (await page.getByRole('heading', { name: 'Oficina Demo Analítica', exact: true }).count()) {
    await page.getByLabel('Filtrar oficina').selectOption({ label: 'Oficina Demo Analítica' });
    await page.getByRole('button', { name: 'Procedimientos', exact: true }).click();
  } else {
    await page.getByRole('button', { name: 'Configuración', exact: true }).click();
    await page.getByLabel('Carpeta autorizada de salida').fill(output);
    await page
      .getByRole('button', { name: 'Instalar demo y autorizar creación de Excel', exact: true })
      .click();
  }
  await page.getByRole('heading', { name: 'Procedimientos', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Nueva tarea', exact: true }).click();
  await page
    .getByLabel('Modo', { exact: true })
    .selectOption({ label: 'Procedimiento: CSV demo → Excel' });
  const file = `browser-${Date.now()}.xlsx`;
  await page
    .getByLabel('Entradas del procedimiento (JSON)')
    .fill(JSON.stringify({ output_name: file }));
  await page.getByRole('button', { name: 'Ejecutar tarea', exact: true }).click();
  await page.getByRole('heading', { name: 'Flujo de ejecución', exact: true }).waitFor();
  await page.getByText('Completada', { exact: true }).first().waitFor({ timeout: 15000 });
  await page.getByText(file, { exact: true }).waitFor();
  const stat = await fs.stat(path.join(output, file));
  if (stat.size < 1000) throw new Error('Excel vacío');
  await page.screenshot({ path: path.join(output, 'tarea-completada.png'), fullPage: true });
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.getByRole('button', { name: 'Actualizar', exact: true }).click();
  await page.locator('.react-flow__node').first().waitFor();
  await page.screenshot({ path: path.join(output, 'organigrama.png'), fullPage: true });
  await page.getByRole('button', { name: 'Resumen', exact: true }).click();
  await page.getByRole('heading', { name: 'Consumo IA', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Configuración', exact: true }).click();
  await page.getByRole('heading', { name: 'Backups locales', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Crear backup', exact: true }).click();
  await page.locator('.list-row strong').filter({ hasText: /\.db$/ }).first().waitFor();
  if (errors.length) throw new Error(errors.join('\n'));
  console.log(
    JSON.stringify({
      status: 'passed',
      file: path.join(output, file),
      browserErrors: errors,
      screenshots: ['tarea-completada.png', 'organigrama.png'],
    }),
  );
} catch (error) {
  await page.screenshot({ path: path.join(output, 'error.png'), fullPage: true });
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}
