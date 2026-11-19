const { mmNLP } = require('./nlp.js'); const N = +process.argv[2] || 3000; let seed = +process.argv[3] || 11;
const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648, pick = a => a[Math.floor(rnd() * a.length)], ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));
const P = n => String(n).padStart(2, '0'), fd = d => `${d.getFullYear()}-${P(d.getMonth() + 1)}-${P(d.getDate())}`, ad = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const SUBJ = [['미터링 업체랑 미팅', 'meet'], ['Emerson 통화', 'call'], ['FAT 입회', 'insp'], ['견적서 제출', 'due'], ['고객사 방문', 'trip'], ['안전 교육', 'edu'], ['팀 회식', 'meal'], ['P&ID 리뷰 회의', 'meet'], ['DCS 사양 협의', 'meet'], ['Control Valve 사이징', ''], ['계장 도면 체크', ''], ['TBE 회의', 'meet']];
const PRE = ['', '', '아 맞다 ', '참고: ', '- ', '✅ ', '메모) ', '[중요] ', 'ㅇㅇ '], LOC = ['', '', '', ' 3층 회의실에서', ' 대회의실', ' 팀즈로', ' 본사에서'], PRI = ['', '', '', ' 긴급', ' 중요', ' ASAP'], WHO = ['', '', '', ' @김철수', ' @이영희'];
let fail = 0; const bad = {};
for (let it = 0; it < N; it++) {
  const now = new Date(2026, ri(0, 11), ri(1, 28), ri(7, 21), pick([0, 10, 20, 30, 40, 50])), D0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dk = pick(['오늘', '내일', '모레', 'nd']); let dp, de; if (dk === 'nd') { const k = ri(2, 6); dp = `${k}일뒤`; de = ad(D0, k); } else { dp = dk; de = ad(D0, { 오늘:0, 내일:1, 모레:2 }[dk]); }
  const k = ri(1, 11), pm = rnd() < .5, tp = `${pm ? '오후' : '오전'}${k}시`, th = pm ? k + 12 : k;
  const [sj, kind] = pick(SUBJ), loc = pick(LOC), pri = pick(PRI), who = pick(WHO), pre = pick(PRE);
  const glue = rnd() < .5 ? '' : ' ', txt = pre + dp + glue + tp + glue + (rnd() < .3 ? '에 ' : ' ') + sj + loc + pri + who + pick(['', ' 있음', ' 잇음', '예정', '!!', '.']);
  const r = mmNLP(txt, now), e = [];
  if (r.due !== fd(de)) e.push(`due ${r.due}≠${fd(de)}`); if (r.time !== P(th) + '00') e.push(`time ${r.time}≠${P(th)}00`);
  if (/(오늘|내일|모레|\d+\s*시|오전|오후|\d+일뒤)/.test(r.title)) e.push(`title잔여 "${r.title}"`);
  if (!r.title.includes(sj.replace(/랑 미팅/, ' 미팅').split(' ')[0])) e.push(`title잃음 "${r.title}"`);
  if (kind && r.kind !== kind && !(kind === 'due' && r.kind)) e.push(`kind ${r.kind}≠${kind}`);
  if (loc.trim() && !r.loc) e.push('loc없음'); if (who.trim() && r.who !== who.trim().slice(1)) e.push('who'); if (pri.trim() && r.pri !== 'h') e.push('pri');
  if (e.length) { fail++; const key = e.map(x => x.split(/[ "]/)[0]).join('+'); (bad[key] = bad[key] || []).push(`${txt} → ${e.join(', ')} | title="${r.title}"`); }
}
console.log(`${N - fail}/${N} 통과 (${(100 * (N - fail) / N).toFixed(2)}%)`); Object.entries(bad).sort((a, b) => b[1].length - a[1].length).slice(0, 10).forEach(([k, l]) => console.log(`\n[${k}] ${l.length}\n  ` + l.slice(0, 4).join('\n  ')));
