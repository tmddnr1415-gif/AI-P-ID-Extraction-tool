// dashboard/dashboard.html 안의 mmNLP · mmRepNext 를 그대로 꺼내 시험에 씀 (복사본을 두지 않음)
const fs = require('fs'), path = require('path'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', '..', 'dashboard', 'dashboard.html'), 'utf8');
const a = html.indexOf('/* mmNLP — 한국어 한 줄'), b = html.indexOf('const mmNowHM');
if (a < 0 || b < 0) throw new Error('dashboard.html 에서 mmNLP 를 찾지 못함');
const ctx = {}; vm.createContext(ctx); vm.runInContext(html.slice(a, b) + '\nthis.mmNLP = mmNLP; this.mmRepNext = mmRepNext; this.MM_KIND = MM_KIND;', ctx);
module.exports = { mmNLP:ctx.mmNLP, mmRepNext:ctx.mmRepNext, MM_KIND:ctx.MM_KIND };
