// 비서 의도 분류기 다시 배우기 → dashboard.html 의 const MM_MLW 를 바꿈 — node train.js [--write]
// 배우는 말: train_a(반말 · 줄임말 900) · train_b(존댓말 · 영어 · 전문 용어 900) · holdout2(392) · blind3(400, 8명 말투) · train_gen(규칙 생성) · train_ra(53)
const fs = require('fs'), path = require('path'), ml = require('./ml.js'); const seen = new Set(), data = [];
for (const f of ['train_a', 'train_b', 'holdout2', 'blind3', 'train_gen', 'train_ra']) for (const row of require('./' + f + '.js')) { const t = row[0]; if (seen.has(t)) continue; seen.add(t); data.push([t, row[1] === undefined ? null : row[1]]); }
const q = ml.quant(ml.train(data, { B:8192, epochs:25, l2:3e-4 })); console.log('배운 문장', data.length, '· 가중치', (q.w.length / 1024).toFixed(1) + 'KB (4비트)');
if (process.argv.includes('--write')) { const p = path.join(__dirname, '..', '..', '..', 'dashboard', 'dashboard.html'); let h = fs.readFileSync(p, 'utf8'); const i = h.indexOf('const MM_MLW = '), j = h.indexOf(';\n', i); if (i < 0) throw new Error('MM_MLW 없음'); h = h.slice(0, i) + 'const MM_MLW = ' + JSON.stringify(q) + h.slice(j); fs.writeFileSync(p, h); console.log('dashboard.html 의 MM_MLW 를 바꿈 — APP_VERSION 올리기 · 시험 다시 돌리기'); }
