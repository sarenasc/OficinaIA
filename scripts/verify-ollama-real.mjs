import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.OFFICE_BROWSER_EXECUTABLE,
});
const page = await browser.newPage();
try {
  await page.goto('http://127.0.0.1:1420');
  await page.locator('.local').filter({ hasText: 'Backend conectado' }).waitFor();
  await page.getByLabel('Filtrar oficina').selectOption({ label: 'Oficina Demo Analítica' });
  await page.getByRole('button', { name: 'Nueva tarea', exact: true }).click();
  await page
    .getByLabel('Solicitud', { exact: true })
    .fill(
      'Prueba de conexión local: no delegues ni uses herramientas. Responde con una sola acción final JSON cuyo content sea Hola, Ollama está funcionando.',
    );
  const created = page.waitForResponse(
    (response) => response.url().endsWith('/api/tasks') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Ejecutar tarea', exact: true }).click();
  const response = await created;
  const task = await response.json();
  console.log('Tarea real Ollama iniciada:', task.id);
  await page.getByRole('heading', { name: 'Flujo de ejecución', exact: true }).waitFor();
  const authorization = response.request().headers()['authorization'];
  const deadline = Date.now() + 330000;
  let current;
  while (Date.now() < deadline) {
    const result = await fetch(`http://127.0.0.1:38080/api/tasks/${task.id}`, {
      headers: { Authorization: authorization },
    });
    current = await result.json();
    if (current.status === 'completed') break;
    if (['error', 'cancelled', 'waiting_approval'].includes(current.status))
      throw Error(`${current.status}: ${current.error || 'La tarea no se completó'}`);
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  if (current?.status !== 'completed') throw Error('Tiempo de espera agotado para la tarea exacta');
  console.log(JSON.stringify({ task_id: task.id, status: current.status, result: current.result }));
  await page.screenshot({ path: 'data/verification/ollama-generacion-real.png', fullPage: true });
  console.log('Generación real Ollama completada');
} catch (error) {
  await page.screenshot({ path: 'data/verification/ollama-prueba-error.png', fullPage: true });
  throw error;
} finally {
  await browser.close();
}
