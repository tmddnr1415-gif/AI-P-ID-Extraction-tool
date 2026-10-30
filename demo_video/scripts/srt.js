const { chromium } = require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+process.argv[2]);
const caps=await p.evaluate(()=>{const out=[];for(const s of document.defaultView.eval('S')){
  if(s.type==='card'){const h=s.el.querySelector('h1').innerHTML.replace(/<br>/g,' ').replace(/<[^>]+>/g,'').replace(/&amp;/g,'&'),pp=s.el.querySelector('p')?.textContent||'';out.push([s.t0,s.t1,`${h} — ${pp}`]);continue}
  (s.cap||[]).forEach((c,i)=>{const e=i+1<s.cap.length?s.t0+s.cap[i+1][0]:s.t1;out.push([s.t0+c[0],e,`[${c[1]}] ${c[2]}`+(c[3]?` / ${c[3]}`:'')])})}return out});
const f=t=>{const ms=Math.round(t*1000),h=Math.floor(ms/3600000),m=Math.floor(ms/60000)%60,s=Math.floor(ms/1000)%60;return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`};
fs.writeFileSync(process.argv[3],caps.map((c,i)=>`${i+1}\n${f(c[0])} --> ${f(c[1])}\n${c[2]}\n`).join('\n'));await b.close()})();
