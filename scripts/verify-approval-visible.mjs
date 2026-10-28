// Read-only verification: never authorizes or rejects the user's task.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)(process.env.OFFICE_PLAYWRIGHT_MODULE);
const browser = await chromium.launch({headless:true,executablePath:process.env.OFFICE_BROWSER_EXECUTABLE});
try {
 const page=await browser.newPage({viewport:{width:1400,height:1000}});
 await page.routeWebSocket('**/ws/tasks/**', socket => socket.close());
 await page.route('**/api/tasks', async route => {
  const response=await route.fetch(); const tasks=await response.json();
  const task=tasks.find(t=>t.id==='c6d3daf8-7ea2-478c-b186-236446541240');
  if(task) task.status='waiting_approval';
  await route.fulfill({response,json:tasks});
 });
 await page.route('**/api/tasks/*/details', async route => {
  const response=await route.fetch(); const detail=await response.json();
  detail.task.status='waiting_approval'; detail.task.error='';
  detail.approvals=detail.approvals.map(a=>({...a,status:'pending'}));
  await route.fulfill({response,json:detail});
 });
 await page.goto('http://127.0.0.1:1420');
 await page.locator('.local').filter({hasText:'Backend conectado'}).waitFor({timeout:60000});
 await page.getByRole('region',{name:'Aprobaciones pendientes'}).getByRole('button',{name:'Revisar aprobación'}).first().click();
 await page.getByRole('button',{name:'Autorizar esta tarea',exact:true}).waitFor();
 await page.getByText('Se requiere aprobación',{exact:true}).waitFor();
 const authorize=await page.getByRole('button',{name:'Autorizar esta tarea',exact:true}).boundingBox();
 const list=await page.getByRole('heading',{name:'Tareas y ejecuciones'}).boundingBox();
 if (!authorize || !list || authorize.y > list.y) throw Error('Approval must appear before task history');
 await page.screenshot({path:'data/verification/approval-visible.png',fullPage:true});
 await page.unrouteAll({behavior:'wait'});
 console.log(JSON.stringify({status:'passed',fixture:'browser-only',checks:['real pending approval visible','authorization button before history'],approved:false}));
} finally {await browser.close();}
