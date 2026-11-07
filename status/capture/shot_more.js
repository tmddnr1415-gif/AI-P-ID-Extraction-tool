const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1600,height:900}});const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('dialog',d=>d.accept());
await p.goto('file://'+process.cwd()+'/s7src/app/index.html');await p.waitForTimeout(2000);
await p.getByText('PSV MR 작성해줘',{exact:true}).first().click();await p.getByRole('button',{name:'전송'}).click().catch(()=>{});await p.waitForTimeout(5000);
await p.getByText('Anatomy',{exact:true}).first().click();await p.waitForTimeout(1000);await p.getByText('개념·시뮬레이션',{exact:true}).first().click().catch(e=>errs.push(e.message));await p.waitForTimeout(3000);await p.screenshot({path:'shots/s7_concept.png'});
await p.goto('http://localhost:8000/logic/draw');await p.waitForTimeout(3500);
const it=p.getByText('ES1S_G002',{exact:false}).first();if(await it.count()){await it.click();await p.waitForTimeout(5000);}
await p.screenshot({path:'shots/s3_draw_sheet.png'});
console.log(errs.slice(0,5));await b.close();})();
