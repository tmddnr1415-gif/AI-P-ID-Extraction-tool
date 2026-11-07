const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const c=await b.newContext({viewport:{width:1600,height:900}});
const tok=process.argv[2];
await c.addInitScript(t=>{localStorage.setItem('dept-auth',JSON.stringify({token:t,id:'demo',name:'시연자'}));localStorage.setItem('dept-server-url','http://localhost:8777');},tok);
const p=await c.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
await p.goto('http://localhost:8777/#home');await p.waitForTimeout(3500);await p.getByText('오늘은 팝업 그만 보기').click().catch(()=>{});await p.getByRole('button',{name:'닫고 툴바로 보기'}).click().catch(()=>{});await p.waitForTimeout(600);
for(const h of process.argv.slice(3)){await p.evaluate(x=>location.hash=x,'#'+h);await p.waitForTimeout(4500);await p.screenshot({path:`shots/s1_${h}.png`});}
console.log('errs',errs.slice(0,5));await b.close();})();
