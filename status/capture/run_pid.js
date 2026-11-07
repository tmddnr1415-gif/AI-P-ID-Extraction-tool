const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1600,height:900}});const errs=[];p.on('pageerror',e=>errs.push(e.message));
p.on('dialog',d=>d.accept());
await p.goto('http://localhost:8000/');await p.waitForTimeout(2500);
await p.click('#home-new').catch(()=>{});await p.waitForTimeout(800);
await p.click('#proj-new-btn');await p.fill('#proj-name','DEMO PJT2');await p.click('#proj-save');await p.waitForTimeout(1500);
await p.setInputFiles('#file','samples/sample_pid2.pdf');await p.waitForTimeout(2500);
await p.screenshot({path:'shots/s2_step_after_file.png'});
// click any start button
for(const t of ['분석을 시작할게요','분석 시작','분석']){const l=p.getByRole('button',{name:t});if(await l.count()){await l.first().click().catch(()=>{});break;}}
const t0=Date.now();
while(Date.now()-t0<540000){await p.waitForTimeout(10000);const txt=await p.textContent('body');if(/결과 보기|Excel 출력/.test(txt)&&!/분석 중/.test(await p.textContent('#progress').catch(()=>''))) break;}
await p.waitForTimeout(3000);await p.screenshot({path:'shots/s2_after_analysis.png'});
console.log('elapsed',Math.round((Date.now()-t0)/1000),errs.slice(0,5));await b.close();})();
