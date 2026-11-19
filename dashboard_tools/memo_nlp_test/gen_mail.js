const { mmMail } = require('./nlp.js');
const N = +process.argv[2] || 1000; let seed = +process.argv[3] || 3; const SHOW = +process.argv[4] || 0, ONLY = process.argv[5] || '';
const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648, pick = a => a[Math.floor(rnd() * a.length)], ri = (a, b) => a + Math.floor(rnd() * (b - a + 1)), chance = p => rnd() < p;
const P = n => String(n).padStart(2, '0'), fd = d => `${d.getFullYear()}-${P(d.getMonth() + 1)}-${P(d.getDate())}`, ad = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const WD = '일월화수목금토', WDE = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'], MON = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const KO = [['홍길동', '책임'], ['김철수', '프로'], ['이영희', '선임'], ['박민수', '수석'], ['최지은', '프로'], ['정우성', '책임'], ['강하늘', '과장'], ['윤서연', '대리']];
const EN = [['John Smith', 'emerson.com', 'Emerson'], ['Sarah Lee', 'yokogawa.com', 'Yokogawa'], ['Michael Brown', 'rotork.com', 'Rotork'], ['Anna Müller', 'samson-group.com', 'Samson'], ['David Kim', 'endress.com', 'Endress'], ['Tom Wilson', 'flowserve.com', 'Flowserve']];
const PJT = ['CO2 PJT', 'Ruwais LNG', 'Qatar NFE', 'Hydrogen Plant', 'Saudi Jafurah'];
const ITEMS = [['Control Valve', 'Control Valve'], ['컨트롤 밸브', 'Control Valve'], ['On/Off Valve', 'On/Off Valve'], ['PSV', 'PSV'], ['MOV', 'MOV'], ['Flow Meter', 'Flow Meter'], ['유량계', 'Flow Meter'], ['Pressure Transmitter', 'Transmitter'], ['Gas Analyzer', 'Analyzer'], ['DCS', 'DCS/SIS']];
const DOCS_KO = [['Datasheet', 'Datasheet'], ['TBE 결과', 'TBE 결과'], ['견적서', '견적서'], ['도면', '도면'], ['사양서', '사양서'], ['VDR', 'VDR'], ['검사 성적서', '검사 성적서']];
const DOCS_EN = [['revised datasheet', 'revised datasheet'], ['updated quotation', 'updated quotation'], ['GA drawing', 'GA drawing'], ['TBE clarification', 'TBE clarification'], ['inspection test plan', 'inspection test plan']];
let tot = 0; const sc = {}; const add = (k, ok) => { sc[k] = sc[k] || [0, 0]; sc[k][0] += ok ? 1 : 0; sc[k][1]++; }; const fails = {};
for (let it = 0; it < N; it++) {
  let md = new Date(2026, ri(0, 11), ri(1, 28)), hh = ri(7, 19), mm = pick([0, 5, 12, 23, 30, 47]); const style = pick(['knox', 'knox', 'olko', 'olen', 'gmail', 'none']); if (style === 'none') md = new Date(2026, 10, 19); const en = style === 'olen' || style === 'gmail' ? chance(.8) : chance(.1);
  const it1 = pick(ITEMS), pj = pick(PJT), doc = en ? pick(DOCS_EN) : pick(DOCS_KO);
  const subj = en ? pick([`[${pj}] ${it1[0]} - Request for ${doc[0]}`, `RE: ${it1[0]} ${doc[0]} review`, `FW: ${pj} ${it1[0]} delivery schedule`, `${it1[0]} quotation for ${pj}`]) : pick([`[${pj}] ${it1[0]} ${doc[0]} 회신 요청`, `RE: [${pj}] ${it1[0]} ${doc[0]} 송부`, `FW: ${it1[0]} 납기 일정 안내`, `[${pj}] ${it1[0]} FAT 일정 협의`, `${it1[0]} 관련 협조 요청`]);
  const isVen = en || chance(.3), s1 = isVen ? pick(EN) : null, k1 = pick(KO);
  const fromName = isVen ? s1[0] : k1[0], fromLine = isVen ? `${s1[0]} <${s1[0].toLowerCase().replace(/\s+/g, '.').replace('ü', 'u')}@${s1[1]}>` : pick([`${k1[0]}/${k1[1]}/계장ENG그룹/삼성물산 <${'u' + ri(10, 99)}@samsung.com>`, `${k1[0]} ${k1[1]} <${'u' + ri(10, 99)}@samsung.com>`, `${k1[0]}/${k1[1]}/구매팀/삼성물산`]);
  const toLine = pick(['김철수/프로/계장ENG그룹/삼성물산 <cs.kim@samsung.com>', '계장ENG그룹 <ieg@samsung.com>; 이영희/선임/계장ENG그룹/삼성물산']);
  const hm = `${P(hh)}${P(mm)}`, h12 = hh % 12 || 12, ampm = hh < 12 ? '오전' : '오후', ampE = hh < 12 ? 'AM' : 'PM';
  // 기한 표현 (메일 날짜 기준)
  const dueKO = () => { const k = pick(['md', 'slash', 'tom', 'tw', 'nw', 'nd', 'today']); let d, txt;
    if (k === 'md') { d = ad(md, ri(1, 30)); txt = `${d.getMonth() + 1}월 ${d.getDate()}일까지`; } else if (k === 'slash') { d = ad(md, ri(1, 30)); txt = `${d.getMonth() + 1}/${d.getDate()}까지`; } else if (k === 'tom') { d = ad(md, 1); txt = '내일까지'; }
    else if (k === 'tw') { const mon = ad(md, -((md.getDay() + 6) % 7)); d = ad(mon, 4); txt = '이번 주 금요일까지'; } else if (k === 'nw') { const mon = ad(md, -((md.getDay() + 6) % 7)); const w = ri(0, 4); d = ad(mon, 7 + w); txt = `다음 주 ${'월화수목금'[w]}요일까지`; }
    else if (k === 'nd') { const n = ri(2, 7); d = ad(md, n); txt = `${n}일 이내`; } else { d = md; txt = '금일 중'; } return [txt, fd(d)]; };
  const dueEN = () => { const k = pick(['mon', 'day', 'eod', 'fri']); let d, txt; if (k === 'mon') { d = ad(md, ri(1, 30)); txt = `by ${MON[d.getMonth()].slice(0, 3)} ${d.getDate()}`; } else if (k === 'day') { d = ad(md, ri(1, 30)); txt = `by ${d.getDate()} ${MON[d.getMonth()]}`; }
    else if (k === 'eod') { d = md; txt = 'by EOD'; } else { d = ad(md, ((5 - md.getDay() + 7) % 7) || 7); txt = 'by Friday'; } return [txt, fd(d)]; };
  const reqs = [], sched = []; const nreq = ri(1, 3), nsch = ri(0, 2), body = [];
  body.push(en ? pick([`Dear ${pick(['Mr. Kim', 'Sir', 'All', 'Kim'])},`, 'Hi Kim,', 'Hello,']) : pick(['김철수 프로님, 안녕하세요.', '안녕하세요.', '수고 많으십니다.', '안녕하십니까, 구매팀 ' + k1[0] + '입니다.']));
  body.push(en ? pick([`We have reviewed the ${it1[0]} documents for ${pj}.`, `Following our discussion, please see the details below.`, `Thank you for your prompt support on ${pj}.`]) : pick([`${pj} ${it1[0]} 관련하여 아래와 같이 안내드립니다.`, `${isVen ? s1[2] : '업체'}에서 ${it1[0]} ${doc[0]}를 송부하였습니다.`, `지난 회의에서 논의된 ${it1[0]} 건 공유드립니다.`]));
  const RK = [['검토 후 회신', '회신'], ['송부', '송부'], ['확인', '확인'], ['제출', '제출']];
  const used = new Set();
  for (let q = 0; q < nreq; q++) { const withDue = chance(.75); let [dt, dd] = withDue ? (en ? dueEN() : dueKO()) : ['', ''];
    if (en) { const d2 = pick(DOCS_EN.filter(x => !used.has(x[0]))); used.add(d2[0]); const v = pick(['send', 'submit', 'confirm', 'provide']); body.push(`${pick(['Please', 'Kindly', 'Could you please'])} ${v} the ${d2[0]}${dt ? ' ' + dt : ''}${/Could/.test(body[body.length - 1]) ? '?' : '.'}`); reqs.push({ kw:d2[0], due:dd }); }
    else { const d2 = pick(DOCS_KO.filter(x => !used.has(x[0]))); used.add(d2[0]); const [vk] = pick(RK); body.push(`${chance(.4) ? pick(['또한 ', '아울러 ', '그리고 ']) : ''}${it1[0]} ${d2[0]} ${vk}${dt ? ' ' : ''}${dt ? dt + ' ' : ' '}${pick(['부탁드립니다.', '해 주시기 바랍니다.', '요청드립니다.', '부탁드립니다!'])}`.replace(/\s+/g, ' ').replace(` ${vk} ${dt} `, ` ${dt} ${vk} `)); reqs.push({ kw:d2[0], due:dd }); } }
  for (let q = 0; q < nsch; q++) { const d = ad(md, ri(2, 40)), h = ri(9, 16), mi = pick([0, 30]); const t24 = `${P(h)}${P(mi)}`;
    if (en) body.push(`The ${pick(['kick-off meeting', 'FAT', 'TBE meeting', 'site visit'])} is scheduled on ${MON[d.getMonth()]} ${d.getDate()} at ${h > 12 ? h - 12 : h}:${P(mi)} ${h >= 12 ? 'PM' : 'AM'}.`);
    else body.push(`${pick(['FAT 일정은', 'TBE 회의는', '킥오프 미팅은', '현장 방문은'])} ${d.getMonth() + 1}월 ${d.getDate()}일 ${h < 12 ? '오전' : '오후'} ${h > 12 ? h - 12 : h}시${mi ? ' 30분' : ''}에 ${pick(['진행 예정입니다.', '예정되어 있습니다.', '본사 3층 회의실에서 진행합니다.'])}`);
    sched.push({ due:fd(d), time:t24 }); }
  if (chance(.5)) body.push(en ? 'Please find the attached file for your reference.' : pick(['참고 부탁드립니다.', '양해 부탁드립니다.', '문의 사항 있으시면 연락 주세요.']));
  body.push(en ? pick(['Best regards,', 'Thanks and regards,', 'Regards,']) : pick(['감사합니다.', '수고하세요.', '이상입니다. 감사합니다.']));
  body.push(en ? `${fromName}\n${isVen ? s1[2] : 'Samsung C&T'} | Sales Engineer\nTel: +82-2-${ri(1000, 9999)}-${ri(1000, 9999)}` : `${fromName} ${k1[1]} 드림\n계장ENG그룹 | Tel 02-${ri(1000, 9999)}-${ri(1000, 9999)}`);
  if (chance(.3)) body.push(en ? `\n-----Original Message-----\nFrom: Kim <cs.kim@samsung.com>\nSent: Monday, ${MON[md.getMonth()]} 1, ${md.getFullYear()} 9:00 AM\nSubject: ${subj}\n\nPlease review by tomorrow.` : `\n-----Original Message-----\n보낸 사람: 김철수 <cs.kim@samsung.com>\n보낸 날짜: ${md.getFullYear()}-01-02 오전 9:00\n제목: 이전 메일\n\n이전 메일 내용 확인 부탁드립니다. 내일까지 회신 바랍니다.`);
  let head;
  if (style === 'knox') head = `${chance(.4) ? '답장 전체답장 전달 삭제\n' : ''}${subj}\n보낸 사람 ${fromLine}\n받는 사람 ${toLine}\n${chance(.5) ? '참조 이영희/선임/계장ENG그룹/삼성물산\n' : ''}보낸 날짜 ${fd(md)} (${WD[md.getDay()]}) ${ampm} ${h12}:${P(mm)}`;
  else if (style === 'olko') head = `보낸 사람: ${fromLine}\n보낸 날짜: ${md.getFullYear()}년 ${md.getMonth() + 1}월 ${md.getDate()}일 ${WD[md.getDay()]}요일 ${ampm} ${h12}:${P(mm)}\n받는 사람: ${toLine}\n${chance(.5) ? '참조: 이영희\n' : ''}제목: ${subj}`;
  else if (style === 'olen') head = `From: ${fromLine}\nSent: ${WDE[md.getDay()]}, ${MON[md.getMonth()]} ${md.getDate()}, ${md.getFullYear()} ${h12}:${P(mm)} ${ampE}\nTo: ${toLine}\n${chance(.5) ? 'Cc: Lee <yh.lee@samsung.com>\n' : ''}Subject: ${subj}`;
  else if (style === 'gmail') head = `${subj}\n${fromLine}\n${MON[md.getMonth()].slice(0, 3)} ${md.getDate()}, ${md.getFullYear()}, ${h12}:${P(mm)} ${ampE}`;
  else head = '';
  const txt = (head ? head + '\n\n' : '') + body.join('\n');
  const NZ = +process.env.NOISE || 0; const r = mmMail(NZ ? require('./ocrnoise.js')(txt, NZ) : txt, { now:new Date(2026, 10, 19, 10, 0) }); tot++;
  const e = []; const ok = (k, c, msg) => { add(k, c); if (!c) e.push(msg); };
  if (style !== 'none') { const nz = x => String(x).toLowerCase().replace(/\s+|[:.,;]/g, '').replace(/0/g, 'o').replace(/i/g, 'l'); ok('제목', nz(r.subj) === nz(subj), `subj "${r.subj}"`); ok('보낸 사람', nz(r.from.name) === nz(fromName), `from "${r.from.name}"`); ok('메일 날짜', r.date === fd(md) && (style === 'none' || r.time === hm), `date ${r.date} ${r.time}≠${fd(md)} ${hm}`); }
  for (const g of reqs) { const m = r.reqs.find(x => (x.t + ' ' + x.src).toLowerCase().replace(/\s+/g, '').replace(/0/g, 'o').replace(/i/g, 'l').includes(g.kw.toLowerCase().replace(/\s+/g, '').replace(/0/g, 'o').replace(/i/g, 'l'))); ok('요청 찾기', !!m, `req miss "${g.kw}"`); if (m) ok('요청 기한', m.due === g.due, `due ${g.kw} ${m.due}≠${g.due}`); }
  ok('요청 오검출 없음', r.reqs.length <= reqs.length, `extra req ${r.reqs.length}>${reqs.length}: ${r.reqs.map(x => x.t).join(' / ')}`);
  for (const g of sched) { const m = r.sched.find(x => x.due === g.due && x.time === g.time); ok('일정', !!m, `sched miss ${g.due} ${g.time}`); }
  if (txt.includes(it1[0])) ok('품목', r.items.includes(it1[1]), `item ${it1[1]} not in ${r.items}`);
  if (e.length) { const k = e.map(x => x.split(' ')[0]).join('+'); (fails[k] = fails[k] || []).push(`--- [${style}${en ? '/en' : ''}] ${e.join(' | ')}\n${txt.slice(0, 900)}`); }
}
let sum = 0, cnt = 0; console.log(`메일 ${tot}통`); for (const [k, [a, b]] of Object.entries(sc)) { console.log(`  ${k}: ${(100 * a / b).toFixed(1)}% (${a}/${b})`); sum += a / b; cnt++; } console.log(`  평균: ${(100 * sum / cnt).toFixed(1)}%`);
Object.entries(fails).filter(([k]) => !ONLY || k.includes(ONLY)).sort((a, b) => b[1].length - a[1].length).slice(0, SHOW).forEach(([k, l]) => console.log(`\n[${k}] ${l.length}\n${l.slice(0, 2).join('\n\n')}`));
