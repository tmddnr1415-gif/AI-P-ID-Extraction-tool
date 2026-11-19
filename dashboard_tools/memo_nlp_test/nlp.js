// dashboard/dashboard.html 안의 해석기(mmNLP · mmRepNext · mmMail · mmIntent)를 그대로 꺼내 시험에 씀 (복사본을 두지 않음)
const fs = require('fs'), path = require('path'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', '..', 'dashboard', 'dashboard.html'), 'utf8');
const cut = (a, b) => { const i = html.indexOf(a), j = html.indexOf(b, i); if (i < 0 || j < 0) throw new Error('dashboard.html 에서 ' + a + ' 를 찾지 못함'); return html.slice(i, j); };
const ctx = { PRES:{ users:[{ name:'김철수' }, { name:'이영희' }, { name:'홍길동' }] } }; vm.createContext(ctx);
vm.runInContext(cut('/* mmNLP — 한국어 한 줄', '/* ---------- 2026-11-19 v18.09') + cut('/* mmMail — 메일', 'const mmPjts') + '\nthis.mmNLP = mmNLP; this.mmRepNext = mmRepNext; this.MM_KIND = MM_KIND; this.mmMail = mmMail; this.mmMailDate = mmMailDate; this.mmIntent = mmIntent; this.mmMailTags = mmMailTags; this.mmMailCodes = mmMailCodes;', ctx);
global.mmNLP = ctx.mmNLP;
module.exports = { mmNLP:ctx.mmNLP, mmRepNext:ctx.mmRepNext, MM_KIND:ctx.MM_KIND, mmMail:ctx.mmMail, mmMailDate:ctx.mmMailDate, mmIntent:ctx.mmIntent, mmMailTags:ctx.mmMailTags, mmMailCodes:ctx.mmMailCodes };
