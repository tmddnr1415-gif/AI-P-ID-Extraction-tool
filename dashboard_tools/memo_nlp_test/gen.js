const { mmNLP } = require('./nlp.js'); const N = +process.argv[2] || 3000; let seed = +process.argv[3] || 7;
const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648, pick = a => a[Math.floor(rnd() * a.length)], ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));
const P = n => String(n).padStart(2, '0'), fd = d => `${d.getFullYear()}-${P(d.getMonth() + 1)}-${P(d.getDate())}`, ad = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const WD = '일월화수목금토', KN = ['', '한', '두', '세', '네', '다섯', '여섯', '일곱', '여덟', '아홉', '열', '열한', '열두'];
const SUBJ = [['미터링 업체랑 미팅', '미터링 업체 미팅', 'meet'], ['미터링 업체 미팅', '미터링 업체 미팅', 'meet'], ['Emerson 통화', 'Emerson 통화', 'call'], ['FAT 입회', 'FAT 입회', 'insp'], ['견적서 제출', '견적서 제출', 'due'], ['고객사 방문', '고객사 방문', 'trip'],
  ['안전 교육', '안전 교육', 'edu'], ['팀 회식', '팀 회식', 'meal'], ['주간 보고', '주간 보고', 'rep'], ['PO 발행', 'PO 발행', 'buy'], ['Valve datasheet 검토', 'Valve datasheet 검토', ''], ['P&ID 리뷰 회의', 'P&ID 리뷰 회의', 'meet'], ['DCS 사양 협의', 'DCS 사양 협의', 'meet'],
  ['계장 도면 체크', '계장 도면 체크', ''], ['Yokogawa 화상 회의', 'Yokogawa 회의', 'meet'], ['김과장이랑 점심', '김과장 점심', 'meal'], ['Control Valve 사이징', 'Control Valve 사이징', ''], ['SAT 준비 회의', 'SAT 준비 회의', 'meet'], ['협력사 회신 확인', '협력사 회신 확인', 'due'], ['CO2 PJT 킥오프', 'CO2 PJT 킥오프', 'meet']];
const FILL = [['', 0], [' 있음', 0], [' 잇음', 0], [' 예정', 0], [' 있습니다', 0], [' 잡혀있음', 0], ['.', 0], ['!', 0]];
let fail = 0, n = 0; const bad = {};
for (let it = 0; it < N; it++) {
  const now = new Date(2026, ri(0, 11), ri(1, 28), ri(7, 21), pick([0, 5, 15, 30, 45, 55])), D0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  // 날짜
  const dk = pick(['none', 'none', 'today', 'tom', 'moreh', 'nd', 'nw', 'tw', 'wd', 'md', 'slash', 'iso', 'nm']); let dp = '', de = null;
  if (dk === 'today') { dp = pick(['오늘', '금일']); de = D0; } else if (dk === 'tom') { dp = pick(['내일', '낼', '명일']); de = ad(D0, 1); } else if (dk === 'moreh') { dp = pick(['모레', '내일모레']); de = ad(D0, 2); }
  else if (dk === 'nd') { const k = ri(1, 9); dp = `${k}일 ${pick(['뒤', '후'])}`; de = ad(D0, k); }
  else if (dk === 'nw' || dk === 'tw') { const w = ri(0, 6), mon = ad(D0, -((now.getDay() + 6) % 7)); dp = `${dk === 'nw' ? pick(['다음 주', '다음주', '담주', '차주']) : pick(['이번 주', '이번주'])} ${WD[w]}${pick(['요일', '욜'])}`; de = ad(mon, (dk === 'nw' ? 7 : 0) + (w + 6) % 7); }
  else if (dk === 'wd') { const w = ri(0, 6); dp = WD[w] + pick(['요일', '욜']); de = ad(D0, (w - now.getDay() + 7) % 7); }
  else if (dk === 'md' || dk === 'slash' || dk === 'iso') { const x = ad(D0, ri(0, 200)); de = x; dp = dk === 'md' ? `${x.getMonth() + 1}월 ${x.getDate()}일` : dk === 'slash' ? `${x.getMonth() + 1}/${x.getDate()}` : fd(x); if (dk !== 'iso' && x.getFullYear() !== now.getFullYear() && false) {} }
  else if (dk === 'nm') { const dd = ri(1, 28); de = new Date(now.getFullYear(), now.getMonth() + 1, dd); dp = `다음 달 ${dd}일`; }
  // 시간
  const tk = pick(['none', 'h', 'pm', 'am', 'hm', 'half', 'hmin', 'eve', 'kn']); let tp = '', th = null, tm = 0;
  if (tk === 'h') { const k = ri(1, 12); tp = `${k}시`; th = k <= 6 ? k + 12 : k; } else if (tk === 'pm') { const k = ri(1, 11); tp = `오후 ${k}시`; th = k + 12; } else if (tk === 'am') { const k = ri(7, 11); tp = `오전 ${k}시`; th = k; }
  else if (tk === 'hm') { th = ri(7, 21); tm = pick([0, 10, 15, 30, 45]); tp = `${th}:${P(tm)}`; } else if (tk === 'half') { const k = ri(7, 12); tp = `${k}시 반`; th = k; tm = 30; } else if (tk === 'hmin') { th = ri(13, 20); tm = pick([10, 20, 40, 50]); tp = `${th}시 ${tm}분`; }
  else if (tk === 'eve') { const k = ri(6, 10); tp = `저녁 ${k}시`; th = k + 12; } else if (tk === 'kn') { const k = ri(1, 12); tp = `${KN[k]} 시`; th = k <= 6 ? k + 12 : k; }
  const [sj, title, kind] = pick(SUBJ), [fl] = pick(FILL); if (th === null && /점심/.test(sj)) th = 12;
  if (de === null && th !== null) de = th * 60 + tm < now.getHours() * 60 + now.getMinutes() - 5 ? ad(D0, 1) : D0;
  const parts = [dp && dp + pick(['', '', '에']), tp && tp + pick(['', '', '에']), sj].filter(Boolean); const ord = parts.length < 2 ? 0 : pick([0, 0, 1, 2]);
  const txt = (ord === 0 ? parts : ord === 1 ? [parts[parts.length - 1], ...parts.slice(0, -1)] : [parts[0], parts[parts.length - 1], ...parts.slice(1, -1)].filter((x, i, a) => a.indexOf(x) === i)).join(' ') + fl;
  const r = mmNLP(txt, now); n++; const errs = [];
  if ((r.due || '') !== (de ? fd(de) : '')) errs.push(`due ${r.due}≠${de ? fd(de) : ''}`);
  if ((r.time || '') !== (th !== null ? P(th) + P(tm) : '')) errs.push(`time ${r.time}≠${th !== null ? P(th) + P(tm) : ''}`);
  if (r.title !== title) errs.push(`title "${r.title}"≠"${title}"`);
  if ((r.kind || '') !== kind && !(kind === '' && r.kind)) errs.push(`kind ${r.kind}≠${kind}`);
  if (errs.length) { fail++; const key = errs.map(e => e.split(' ')[0]).join('+') + ':' + dk + '/' + tk; (bad[key] = bad[key] || []).push(`${txt}  [now ${fd(now)} ${P(now.getHours())}:${P(now.getMinutes())} ${WD[now.getDay()]}] → ${errs.join(', ')}`); }
}
console.log(`${n - fail}/${n} 통과 (${(100 * (n - fail) / n).toFixed(2)}%)`);
Object.entries(bad).sort((a, b) => b[1].length - a[1].length).slice(0, 14).forEach(([k, l]) => console.log(`\n[${k}] ${l.length}건\n  ` + l.slice(0, 3).join('\n  ')));
