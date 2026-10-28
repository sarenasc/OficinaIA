import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.OFFICE_BROWSER_EXECUTABLE,
  args: ['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
try {
  await page.goto('http://127.0.0.1:1420');
  await page.locator('.local').filter({ hasText: 'Backend conectado' }).waitFor();
  await page.getByLabel('Filtrar oficina').selectOption({ label: 'Oficina Demo Analítica' });
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  const canvas = page.locator('.office-3d-canvas canvas');
  await canvas.waitFor({ timeout: 60000 });
  await page.waitForFunction(
    () =>
      Number(document.querySelector('.office-3d-canvas canvas')?.getAttribute('data-moving')) > 0,
    {},
    { timeout: 30000 },
  );
  await page.locator('.office-3d-people button').filter({ hasText: 'Coordinador' }).click();
  await page.locator('.scene-panel h3').waitFor();
  await page.screenshot({ path: 'data/verification/oficina-3d.png', fullPage: true });
  const bounds = await canvas.boundingBox();
  await page.mouse.move(bounds.x + bounds.width * 0.6, bounds.y + bounds.height * 0.6);
  await page.mouse.wheel(0, -180);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width * 0.6 + 90, bounds.y + bounds.height * 0.6 + 20, {
    steps: 10,
  });
  await page.mouse.up();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.waitForFunction(
    () => document.querySelector('.office-3d-canvas canvas')?.getAttribute('data-moving') === '0',
  );
  await page.getByRole('button', { name: 'Plano 2D', exact: true }).click();
  await page.locator('.desk').first().waitFor();
  await page.getByRole('button', { name: 'Oficina 3D', exact: true }).click();
  await canvas.waitFor();
  if (errors.length) throw Error(errors.join('\n'));
  console.log(
    JSON.stringify({
      status: 'passed',
      checks: [
        'WebGL render',
        'idle roaming',
        'agent selection',
        'camera orbit and zoom',
        'reduced motion',
        '2D/3D switch',
      ],
      browserErrors: errors,
    }),
  );
} catch (error) {
  console.log('Page errors', errors);
  await page.screenshot({ path: 'data/verification/oficina-3d-error.png', fullPage: true });
  throw error;
} finally {
  await browser.close();
}
