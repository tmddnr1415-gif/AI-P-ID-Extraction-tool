// 계측제어 메일 1000통(따로 쓴 생성기 gen_ic.js — 해석기를 보지 않고 만듦) 채점 — node run_ic.js [dev|test|all] [보여줄 틀린 종류] [보여줄 개수]
// dev = 짝수 번째(고칠 때 봄) · test = 홀수 번째(마지막에 한 번만 점수)
const fs = require('fs'), path = require('path');
const MAIL = require('../nlp.js'); if (!fs.existsSync(path.join(__dirname, 'ic_mails.json'))) require('child_process').execFileSync(process.execPath, [path.join(__dirname, 'gen_ic.js'), '1000', '7'], { stdio:'ignore' });   // 없으면 만듦 (같은 씨앗 → 늘 같은 1000통)
const mmMail = MAIL.mmMail; const [part = 'all', ONLY = '', SHOWN = '3'] = process.argv.slice(2);
const all = JSON.parse(fs.readFileSync(path.join(__dirname, 'ic_mails.json'), 'utf8')), L = all.filter((x, i) => part === 'all' || (part === 'dev' ? i % 2 === 0 : i % 2 === 1));
const nz = x => String(x || '').toLowerCase().normalize('NFKC').replace(/\s+|[:.,;'"“”‘’()\[\]<>_\-–—/]/g, '').replace(/0/g, 'o').replace(/[il1|]/g, 'l');
const sc = {}, fails = {}; const add = (k, ok) => { sc[k] = sc[k] || [0, 0]; sc[k][0] += ok ? 1 : 0; sc[k][1]++; };
for (const m of L) { const g = m.gold, r = mmMail(m.text, { now:new Date(2026, 10, 19, 10, 0) }), e = [], ok = (k, c, msg) => { add(k, c); if (!c) e.push(k + ': ' + msg); };
  if (g.subj) ok('제목', nz(r.subj) === nz(g.subj), `"${r.subj}" ≠ "${g.subj}"`);
  if (g.from) ok('보낸 사람', nz(r.from.name) === nz(g.from) || nz(r.from.name).includes(nz(g.from)) && nz(g.from).length >= 4, `"${r.from.name}" ≠ "${g.from}"`);
  if (g.date) ok('메일 날짜', r.date === g.date, `${r.date} ≠ ${g.date}`);
  if (g.time) ok('메일 시각', r.time === g.time, `${r.time} ≠ ${g.time}`);
  const used = new Set();
  for (const q of g.reqs) { const k = nz(q.kw); const i = r.reqs.findIndex((x, j) => !used.has(j) && nz(x.t + ' ' + x.src).includes(k)); ok('요청 찾기', i >= 0, `못 찾음 "${q.kw}"`); if (i >= 0) { used.add(i); const x = r.reqs[i]; if (q.due || m.style !== 'nohdr') ok('요청 기한', (x.due || '') === (q.due || ''), `"${q.kw}" ${x.due || '없음'} ≠ ${q.due || '없음'}`); } }
  ok('요청 더 찾음 없음', r.reqs.length <= g.reqs.length, `${r.reqs.length} > ${g.reqs.length}: ${r.reqs.filter((x, j) => !used.has(j)).map(x => x.t.slice(0, 50)).join(' / ')}`);
  if (g.noreq) ok('요청 없는 메일', r.reqs.length === 0, `${r.reqs.length}개: ${r.reqs.map(x => x.t.slice(0, 40)).join(' / ')}`);
  const ev = r.sched.filter(x => !x.req); for (const s of g.sched) ok('일정', ev.some(x => x.due === s.due && (!s.time || x.time === s.time)), `못 찾음 ${s.due} ${s.time} (찾은 것: ${ev.map(x => x.due + ' ' + x.time).join(', ')})`);
  for (const it of g.items) ok('품목', r.items.includes(it), `${it} 없음 (${r.items.join(', ')})`);
  if (e.length) for (const x of e) { const k = x.split(':')[0]; (fails[k] = fails[k] || []).push(`--- [${m.id} ${m.lang}/${m.style}] ${x}\n${m.text.slice(0, +process.env.CH || 600)}`); } }
let sum = 0, n = 0; console.log(`메일 ${L.length}통 (${part})`); for (const [k, [a, b]] of Object.entries(sc)) { console.log(`  ${k}: ${(100 * a / b).toFixed(1)}% (${a}/${b})`); sum += a / b; n++; } console.log(`  평균: ${(100 * sum / n).toFixed(1)}%`);
if (ONLY) (fails[ONLY] || []).slice(0, +SHOWN).forEach(x => console.log('\n' + x));
