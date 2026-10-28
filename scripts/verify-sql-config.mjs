// Browser-only save fixture; never connects to SQL or changes real connections.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({ headless: true, executablePath: process.env.OFFICE_BROWSER_EXECUTABLE });
try {
 const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
 let submitted;
 await page.route('**/api/connections', async route => {
  if (route.request().method() === 'POST') {
   submitted = route.request().postDataJSON();
   await route.fulfill({json:{...submitted,id:'browser-draft-only'}});
  } else await route.continue();
 });
 await page.goto('http://127.0.0.1:1420');
 await page.getByRole('button',{name:'Conexiones',exact:true}).click();
 await page.getByRole('button',{name:'+ Crear',exact:true}).click();
 await page.locator('.modal').getByLabel('Nombre',{exact:true}).fill('SQL pendiente de ejemplo');
 await page.getByLabel('Servidor o instancia SQL').waitFor();
 if (await page.locator('.modal').getByLabel('Activo',{exact:true}).isChecked()) throw Error('Draft must start inactive');
 await page.getByLabel('Autenticación SQL').selectOption('password');
 await page.getByLabel('Usuario SQL').fill('lector');
 await page.screenshot({path:'data/verification/sql-config.png',fullPage:true});
 await page.getByRole('button',{name:'Guardar',exact:true}).click();
 await page.waitForFunction(()=>!document.querySelector('.modal'));
 if (!submitted || submitted.active !== false || submitted.kind !== 'sqlserver' || submitted.config.username !== 'lector') throw Error('Invalid draft payload');
 await page.unrouteAll({behavior:'wait'});
 console.log(JSON.stringify({status:'passed',fixture:'browser-only',checks:['SQL fields','inactive default','save incomplete draft','separate credential']}));
} finally {await browser.close();}
