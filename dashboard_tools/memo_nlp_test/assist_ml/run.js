// 비서 명령 시험 (의도 + 날짜 · 시각 · 기간 · 옮기기) — node run.js [holdout2|blind3|train_a|train_b] [RULES=1 이면 규칙만]
const N = require('../nlp.js'), mmIntent = process.env.RULES ? (t, c) => { const r = N.mmRules(t, c); return r && r.intent === '_dash' ? null : r; } : N.mmIntent;
const T = require('./' + (process.argv[2] || 'blind3') + '.js'), now = new Date(2026, 10, 19, 10, 5), by = {}, fails = [];
const pullable = s => /수행|입찰|이슈|CO2|스케줄|schedule|통합\s*업무|to\s*do|PO\s*전망|FAT\s*전망|현안|R&R|유닛|기술\s*공유|전달\s*사항|일반\s*업무|구매\s*일정|PSR/i.test(s);
for (const [t, e, x0] of T) { const x = x0 || {}; const r = mmIntent(t, { now, pullable, nlpOpt:{ users:['김철수', '이영희', '홍길동', '박민수'] } }); const g = r ? r.intent : null; let ok = g === (e ?? null), why = '';
  if (ok && e === 'add' && r.p) { if (x.due && r.p.due !== x.due) { ok = false; why = `due ${r.p.due}≠${x.due}`; } if (x.time && r.p.time !== x.time) { ok = false; why += ` time ${r.p.time}≠${x.time}`; } }
  if (ok && e === 'query' && x.win && r.win !== x.win) { ok = false; why = `win ${r.win}≠${x.win}`; }
  if (ok && e === 'move') { if (x.due && r.due !== x.due) { ok = false; why = `due ${r.due}≠${x.due}`; } if (x.time && r.time !== x.time) { ok = false; why += ` time ${r.time}≠${x.time}`; } if (x.shift) { const m = { '+1d':1440, '-1d':-1440, '+2d':2880, '+7d':10080, '+1h':60, '-1h':-60, '+30m':30, '-30m':-30 }[x.shift]; if (r.shift !== m) { ok = false; why += ` shift ${r.shift}≠${x.shift}`; } } }
  by[e] = by[e] || [0, 0]; by[e][1]++; if (ok) by[e][0]++; else fails.push(`✗ [${e}${why ? ' ' + why : ''}] ${t.replace(/\n/g, ' ⏎ ').slice(0, 90)} → ${g}`); }
let a = 0, n = 0; for (const [k, [o, m]] of Object.entries(by)) { a += o; n += m; console.log(`  ${String(k)}: ${o}/${m}`); } console.log(`전체 ${a}/${n} = ${(100 * a / n).toFixed(1)}%`); if (process.env.SHOW) fails.forEach(f => console.log(f));
