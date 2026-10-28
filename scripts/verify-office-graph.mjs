// Read-only browser verification using actual imported agents. No mutations.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({ headless: true, executablePath: process.env.OFFICE_BROWSER_EXECUTABLE });
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  await page.goto('http://127.0.0.1:1420');
  await page.getByLabel('Filtrar oficina').selectOption({ label: 'Analisis deportivas' });
  await page.getByRole('button', { name: 'Agentes', exact: true }).click();
  await page.locator('.graph .react-flow__node').first().waitFor();
  await page.waitForFunction(() => {
    const nodes = [...document.querySelectorAll('.graph .react-flow__node')];
    return nodes.length === 6 && nodes.every(node => node.getBoundingClientRect().width > 0);
  });
  const positions = await page.locator('.graph .react-flow__node').evaluateAll(nodes => nodes.map(node => {
    const rect = node.getBoundingClientRect();
    return { name: node.textContent, x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  }));
  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      const a = positions[i], b = positions[j];
      if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y) {
        throw Error(`Overlapping agents: ${a.name} / ${b.name}`);
      }
    }
  }
  await page.locator('.graph').scrollIntoViewIfNeeded();
  const edges = page.locator('.graph .react-flow__edge');
  await edges.first().waitFor();
  if (await edges.count() !== 5) throw Error('Expected five actual outgoing relations');
  const flow = await edges.evaluateAll(edges => edges.map(edge => ({
    direction: edge.getAttribute('aria-label'),
    path: edge.querySelector('.react-flow__edge-path')?.getAttribute('d'),
    motion: edge.querySelector('animateMotion')?.getAttribute('path'),
    arrow: edge.querySelector('.react-flow__edge-path')?.getAttribute('marker-end'),
  })));
  if (flow.some(edge => !edge.direction?.startsWith('Coordinador delega a ') || !edge.arrow || edge.path !== edge.motion)) {
    throw Error('Arrow or motion does not match the actual source-to-target path');
  }
  await page.getByLabel('Leyenda del flujo de delegación').waitFor();
  await page.waitForTimeout(650);
  await page.locator('.graph').screenshot({ path: 'data/verification/office-graph-separated.png' });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  if (await page.locator('.delegation-flow-dot:visible').count() !== 0) throw Error('Reduced motion ignored');
  console.log(JSON.stringify({ status: 'passed', count: positions.length, edges: flow.length, checks: ['actual imported agents', 'distinct positions', 'no overlapping cards', 'outgoing direction labels', 'arrows', 'source-to-target particle paths', 'reduced motion'] }));
} finally { await browser.close(); }
