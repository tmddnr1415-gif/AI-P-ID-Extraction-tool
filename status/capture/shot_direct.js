const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1600,height:900}});const errs=[];p.on('pageerror',e=>errs.push(e.message));
for(const [u,n] of [['http://localhost:8000/valve/','s6_valve'],['http://localhost:8000/logic/signal','s3_signal'],['http://localhost:8000/','s2_pid_direct']]){await p.goto(u);await p.waitForTimeout(3500);await p.screenshot({path:`shots/${n}.png`});}
console.log(errs.slice(0,5));await b.close();})();
