const { mmNLP } = require('./nlp.js'); const cases = require('./cases.js'); const now = new Date(2026, 10, 19, 10, 5); let fail = 0;
for (const [t, exp] of cases) { const r = mmNLP(t, now); const bad = Object.entries(exp).filter(([k, v]) => (r[k] || '') !== v); if (bad.length) { fail++; console.log('✗', t, '\n   ', bad.map(([k, v]) => `${k}: got "${r[k] || ''}" want "${v}"`).join(' | ')); } }
console.log(`\n${cases.length - fail}/${cases.length} 통과`);
