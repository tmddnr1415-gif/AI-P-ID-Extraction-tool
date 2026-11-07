const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1600,height:900}});const errs=[];p.on('pageerror',e=>errs.push(e.message));
await p.goto('file://'+process.cwd()+'/s7src/app/index.html');await p.waitForTimeout(2500);await p.screenshot({path:'shots/s7_org.png'});
await p.getByText('PSV MR 작성해줘',{exact:true}).first().click();await p.waitForTimeout(500);await p.getByRole('button',{name:'전송'}).click().catch(()=>{});await p.waitForTimeout(5000);await p.screenshot({path:'shots/s7_mr.png'});
await p.getByText('Anatomy',{exact:true}).first().click().catch(e=>errs.push('anat '+e.message));await p.waitForTimeout(3000);await p.screenshot({path:'shots/s7_anatomy.png'});
console.log(errs.slice(0,5));await b.close();})();
