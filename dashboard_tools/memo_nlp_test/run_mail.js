const { mmMail } = require('./nlp.js'); const C = require(process.argv[2] || './real_cases.js'); const noise = process.argv[3] || '';
let sc = {}; const add = (k, ok) => { sc[k] = sc[k] || [0, 0]; sc[k][0] += ok ? 1 : 0; sc[k][1]++; };
for (const [txt0, g] of C) { const txt = noise ? require('./ocrnoise.js')(txt0, +noise) : txt0; const r = mmMail(txt, { now:new Date(2026, 10, 19, 10, 0) }); const e = []; const ok = (k, c, m) => { add(k, c); if (!c) e.push(m); };
  const nz = x => String(x).toLowerCase().replace(/\s+|[:.,;]/g, '').replace(/0/g, 'o').replace(/i/g, 'l'); if (g.subj != null && g.subj) ok('제목', nz(r.subj) === nz(g.subj), `subj "${r.subj}"`); if (g.from) ok('보낸 사람', nz(r.from.name) === nz(g.from), `from "${r.from.name}"`); if (g.date) ok('메일 날짜', r.date === g.date && (!g.time || r.time === g.time), `date ${r.date} ${r.time}`);
  for (const [kw, due] of g.reqs || []) { const m = r.reqs.find(x => (x.t + ' ' + x.src).toLowerCase().replace(/\s+/g, '').includes(kw.toLowerCase().replace(/\s+/g, ''))); ok('요청 찾기', !!m, `req miss "${kw}"`); if (m && due) ok('요청 기한', m.due === due, `due "${kw}" ${m.due}≠${due}`); }
  if (g.noReq) ok('요청 없음(공지)', r.reqs.length === 0, `false reqs: ${r.reqs.map(x => x.t).join(' / ')}`); else ok('요청 오검출 없음', r.reqs.length <= (g.reqs || []).length + 1, `extra: ${r.reqs.map(x => x.t).join(' / ')}`);
  for (const [d, t] of g.sched || []) ok('일정', r.sched.some(x => x.due === d && (!t || x.time === t)), `sched miss ${d} ${t} got ${r.sched.map(x => x.due + ' ' + x.time).join(',')}`);
  for (const it of g.items || []) ok('품목', r.items.includes(it), `item ${it} not in [${r.items}]`);
  if (e.length) console.log('✗', (g.subj || txt.split('\n')[0]).slice(0, 50), '\n   ', e.join('\n    '), '\n    reqs:', r.reqs.map(x => `${x.t}(${x.due})`).join(' / '));
}
let s = 0, n = 0; for (const [k, [a, b]] of Object.entries(sc)) { console.log(`  ${k}: ${(100 * a / b).toFixed(1)}% (${a}/${b})`); s += a / b; n++; } console.log(`  평균: ${(100 * s / n).toFixed(1)}%`);
