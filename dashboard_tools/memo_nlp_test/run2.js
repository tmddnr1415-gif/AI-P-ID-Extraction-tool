const { mmNLP } = require('./nlp.js'); const cs = require('./cases2.js'); let f = 0;
for (const [t, n, exp] of cs) { const now = new Date(n[0], n[1] - 1, n[2], n[3], n[4]); const r = mmNLP(t, now, { users:['김철수', '이영희', '홍길동'] }); const bad = Object.entries(exp).filter(([k, v]) => (r[k] || '') !== v); if (bad.length) { f++; console.log('✗', t, '\n   ', bad.map(([k, v]) => `${k}: "${r[k] || ''}"≠"${v}"`).join(' | '), ' title=', r.title); } }
console.log(`${cs.length - f}/${cs.length} 통과`);
