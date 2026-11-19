#!/usr/bin/env node
'use strict';
/*
 * gen_ic.js — held-out test set of I&C (계측제어) EPC business e-mails for grading an
 * e-mail summarizing parser.  Node built-ins only.
 *
 *   node gen_ic.js [N=1000] [seed=7]      -> writes ic_mails.json next to this file
 *
 * Each record: { id, lang:'ko'|'en'|'mix', style, text, gold }
 *   gold = { subj, from, date:'YYYY-MM-DD', time:'HHMM', reqs:[{kw,due}], sched:[{due,time}],
 *            items:[category...], noreq:boolean }
 * h1..h40 are hand-written; g41.. are generated from a large combinatorial grammar.
 *
 * ---------------------------------------------------------------------------------------
 * LABELLING CONVENTIONS (what the gold means)
 *  - subj : subject exactly as shown (RE:/FW:/회신:/전달:/[tags] kept), '' if none shown.
 *  - from : person name of the sender of the NEWEST message, from the header only; display
 *           forms '김민준 책임', '김민준/책임/계장ENG그룹/한결E&C', '김민준(Minjun Kim)',
 *           'John Smith (Rotork)', 'Thomas Becker/AUMA' all -> the bare name as written.
 *           Mails without header ("nohdr") -> from/subj/date/time = '' (even if signed).
 *  - date/time : sent date/time of the newest message (24h 'HHMM').  오후 2:30 -> 1430.
 *  - reqs : actions requested OF THE READER in the NEWEST message only.  Quoted older
 *           messages (Original Message / "On .. wrote:" / "> " / 이전 메일 blocks) are ignored.
 *           NOT requests: sender's own commitments ("We will send..", "송부드리겠습니다"),
 *           "please find attached", "첨부와 같이 송부드립니다", "Please note that ...",
 *           "if you need anything let me know", "문의사항 있으시면 연락 주세요", thanks.
 *           Requests ARE: imperatives, imperative list items/comments, "~필요합니다", "확인 요망",
 *           "shall be ...", "are to be ...", "It is required that ...", "~해 주시면 감사하겠습니다".
 *           Conditional asks ("If payment has been made, please disregard", "if required ...") are not.
 *           Deadlines are sentence-local: a req gets the deadline written in its own sentence
 *           (or in a "기한:/Due date:" line right under that one request).  Exception: a list intro
 *           ending in ':' that carries a deadline ("아래 사항 11/25까지 회신 바랍니다:") -> the deadline
 *           applies to every list item and the intro is NOT a separate req.  Any other sentence with
 *           its own deadline (e.g. an outro "please give feedback by X") is its own req.
 *           kw is a substring of the request sentence (case-sensitive).
 *  - sched: dated EVENTS only (meeting, call, FAT/SAT/IFAT, inspection/witness, site visit,
 *           loop check, shipment ETD/ETA/ready-for-pickup, shutdown, training, business trip).
 *           Reply deadlines are NOT events; office closures / holidays / IT notices are NOT events.
 *           Only events on/after the sent date (past events are history).  Proposed/tentative
 *           dated events are labelled; undated ones ("week 49") are not.  Multi-day -> first day.
 *           time '' if the event has no time.  Time is taken as written (no TZ math).
 *  - items: categories (fixed list) the newest message is about; [] if none.
 *  - noreq: true iff reqs is empty.
 *
 * DATE RESOLUTION RULES (relative expressions are resolved against the SENT date S;
 * week = Monday..Sunday; no public holidays are considered):
 *  - 오늘/금일/당일/오늘 중/금일 중/today/EOD/COB/end of day/by close of business -> S
 *  - 내일/익일/명일/tomorrow (also "tomorrow morning", "내일 오전")            -> S+1 (calendar)
 *  - 모레/the day after tomorrow                                              -> S+2
 *  - bare weekday / "this <wd>" / "이번 주 <요일>" / "by Friday" / "금요일까지"
 *        -> that weekday in the current Mon-Sun week (generator only uses it when it is
 *           after S; i.e. = first such weekday on/after S)
 *  - "next <wd>" / "다음 주 <요일>" / "차주 <요일>" -> that weekday in the FOLLOWING Mon-Sun week
 *        (sent Wed 2026-11-18: next Monday = 11-23, next Friday = 11-27)
 *  - 금주 중 / 이번 주 내 / 이번 주까지 / 주중 / by end of this week / within this week -> Friday of S's week
 *  - 차주 중 / 다음 주 중 / 다음 주까지 / by next week / within next week / by end of next week
 *        -> Friday of the following week
 *  - N영업일 이내 / N working days / N business days -> S plus N weekdays (S not counted, Sat/Sun skipped)
 *  - N일 이내 / within N days / D+N -> S+N calendar days;  N주 이내 / within N weeks -> S+7N
 *  - 월말 / 이달 말 / 금월 말 / end of this month / end of the month / month-end -> last day of S's month
 *  - 다음 달 D일 / D일(only day) -> that day of next month / of S's month (if already past -> next month)
 *  - ASAP / 조속히 / 빠른 시일 내 / at your earliest convenience / promptly -> due ''
 *  - Explicit dates without a year take S's year; if that is >60 days before S, the next year.
 *  - "nohdr" mails (no sent date): dates are written with a year; relative ones -> due ''.
 *  - Numeric dates: Korean style is always month-first (11/25, 11.25, 2026.11.25).
 *    In English mails "a/b/yyyy" is mm/dd/yyyy UNLESS a>12, then dd/mm/yyyy.  The generator
 *    never writes an ambiguous dd/mm (day<=12 is always written as dd-Mon / 25th Nov etc.).
 *  - Times: 오전/오후 h시 (m분|반) ; "2 pm", "2:30 PM", "14:00", "1400 hrs", "10:00 KST",
 *    정오/noon = 1200.  Time zones are not converted.
 * ---------------------------------------------------------------------------------------
 */
const fs = require('fs');
const path = require('path');
const N = parseInt(process.argv[2] || '1000', 10);
const SEED = parseInt(process.argv[3] || '7', 10);

// ---------- deterministic PRNG ----------
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
let rnd = mulberry32(SEED);
const ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));
const pick = (a) => a[Math.floor(rnd() * a.length)];
const chance = (p) => rnd() < p;
function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const k = Math.floor(rnd() * (i + 1)); [a[i], a[k]] = [a[k], a[i]]; } return a; }
function pickN(a, n) { return shuffle(a).slice(0, n); }
function wpick(pairs) { let s = 0; for (const p of pairs) s += p[1]; let r = rnd() * s; for (const p of pairs) { r -= p[1]; if (r <= 0) return p[0]; } return pairs[pairs.length - 1][0]; }
const pad = (n, w = 2) => String(n).padStart(w, '0');

// ---------- calendar ----------
function D(s) { const [y, m, d] = s.split('-').map(Number); return new Date(Date.UTC(y, m - 1, d)); }
function iso(dt) { return dt.toISOString().slice(0, 10); }
function addDays(s, n) { const d = D(s); d.setUTCDate(d.getUTCDate() + n); return iso(d); }
function dow(s) { return D(s).getUTCDay(); } // 0 Sun .. 6 Sat
function addWorkDays(s, n) { let d = s; while (n > 0) { d = addDays(d, 1); const w = dow(d); if (w !== 0 && w !== 6) n--; } return d; }
function weekMonday(s) { return addDays(s, -((dow(s) + 6) % 7)); }
function thisWeekday(s, w) { return addDays(weekMonday(s), (w + 6) % 7); }
function nextWeekday(s, w) { return addDays(thisWeekday(s, w), 7); }
function monthEnd(s) { const d = D(s); return iso(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0))); }
function ymd(s) { const [y, m, d] = s.split('-').map(Number); return { y, m, d }; }
function diffDays(a, b) { return Math.round((D(b) - D(a)) / 86400000); }
const KO_DOW = ['일', '월', '화', '수', '목', '금', '토'];
const EN_DOW = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const EN_DOW3 = EN_DOW.map((x) => x.slice(0, 3));
const EN_MON = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const EN_MON3 = EN_MON.map((x) => x.slice(0, 3));
function ord(n) { const t = n % 100; if (t >= 11 && t <= 13) return n + 'th'; return n + ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] || 'th'); }

// ---------- date / time text ----------
// Korean explicit date text (no year ambiguity: year = S's year by rule)
function koDate(s, withYear) {
  const { y, m, d } = ymd(s); const w = KO_DOW[dow(s)];
  const f = withYear ? pick([
    `${y}년 ${m}월 ${d}일(${w})`, `${y}-${pad(m)}-${pad(d)}`, `${y}.${pad(m)}.${pad(d)}(${w})`, `${y}. ${m}. ${d}.`, `${y}/${pad(m)}/${pad(d)}`,
  ]) : pick([
    `${m}월 ${d}일`, `${m}월 ${d}일(${w})`, `${m}/${d}(${w})`, `${m}/${d}`, `${m}.${d}`, `${pad(m)}.${pad(d)}(${w})`, `${m}월 ${d}일 (${w})`, `${y}-${pad(m)}-${pad(d)}`, `${y}.${pad(m)}.${pad(d)}`,
  ]);
  return f;
}
function enDate(s, withYear) {
  const { y, m, d } = ymd(s); const w = dow(s);
  const opts = [
    `${pad(d)}-${EN_MON3[m - 1]}-${y}`, `${d} ${EN_MON3[m - 1]} ${y}`, `${EN_MON[m - 1]} ${d}, ${y}`, `${d} ${EN_MON[m - 1]} ${y}`, `${y}-${pad(m)}-${pad(d)}`,
    `${EN_DOW[w]}, ${d} ${EN_MON[m - 1]} ${y}`, `${ord(d)} ${EN_MON[m - 1]} ${y}`, `${pad(m)}/${pad(d)}/${y}`,
  ];
  if (d > 12) opts.push(`${pad(d)}/${pad(m)}/${y}`, `${d}/${m}/${y}`);
  if (!withYear) opts.push(`${d}-${EN_MON3[m - 1]}`, `${EN_MON3[m - 1]}. ${ord(d)}`, `${ord(d)} ${EN_MON[m - 1]}`, `${EN_DOW3[w]} ${d} ${EN_MON3[m - 1]}`, `${EN_MON[m - 1]} ${d}`, `${EN_DOW[w]}, ${EN_MON[m - 1]} ${ord(d)}`);
  return pick(opts);
}
function koTime(t) {
  const h = +t.slice(0, 2), mi = +t.slice(2);
  const ap = h < 12 ? '오전' : '오후'; const h12 = h > 12 ? h - 12 : h;
  return pick([
    `${pad(h)}:${pad(mi)}`, `${ap} ${h12}시` + (mi ? (mi === 30 && chance(0.5) ? ' 반' : ` ${mi}분`) : ''), `${h}시` + (mi ? ` ${mi}분` : ''), `${ap} ${h12}:${pad(mi)}`,
  ]);
}
function enTime(t) {
  const h = +t.slice(0, 2), mi = +t.slice(2);
  const ap = h < 12 ? 'AM' : 'PM'; const h12 = h > 12 ? h - 12 : h;
  return pick([
    `${pad(h)}:${pad(mi)}`, `${h12}:${pad(mi)} ${ap}`, mi ? `${h12}:${pad(mi)} ${ap.toLowerCase()}` : `${h12} ${ap.toLowerCase()}`, `${pad(h)}${pad(mi)} hrs`,
    `${pad(h)}:${pad(mi)} KST`, `${h12}:${pad(mi)}${ap.toLowerCase()}`, `${pad(h)}:${pad(mi)} hrs (KST)`,
  ]);
}
const EVENT_TIMES = ['0900', '0930', '1000', '1030', '1100', '1330', '1400', '1430', '1500', '1530', '1600', '1700', '0830', '1300'];

// Relative / explicit DEADLINE expression -> { ko|en text, due }
// mode 'rel' uses relative phrases, 'abs' explicit dates, 'none' ASAP-type
function dueExpr(S, lang, noRel) {
  const w = dow(S); const cands = [];
  const add = (wt, ko, en, due) => cands.push([{ ko, en, due }, wt]);
  if (!noRel) {
    add(2, '내일까지', 'by tomorrow', addDays(S, 1));
    add(1, '익일까지', 'by tomorrow noon', addDays(S, 1));
    add(1, '금일 중', 'by EOD today', S);
    add(1, '오늘 중으로', 'by COB today', S);
    if (w >= 1 && w <= 3) add(1, '모레까지', 'by the day after tomorrow', addDays(S, 2));
    if (w >= 1 && w <= 3) add(2, '금주 중', 'by end of this week', thisWeekday(S, 5));
    if (w >= 1 && w <= 3) add(1, '이번 주 내로', 'within this week', thisWeekday(S, 5));
    if (w >= 1 && w <= 3) add(2, '이번 주 금요일까지', 'by Friday', thisWeekday(S, 5));
    if (w >= 1 && w <= 2) add(1, '이번 주 목요일까지', 'by this Thursday', thisWeekday(S, 4));
    add(2, '차주 월요일까지', 'by next Monday', nextWeekday(S, 1));
    add(1, '다음 주 화요일까지', 'by next Tuesday', nextWeekday(S, 2));
    add(1, '다음 주 수요일까지', 'no later than next Wednesday', nextWeekday(S, 3));
    add(1, '차주 중', 'by end of next week', nextWeekday(S, 5));
    const n = pick([2, 3, 5, 7]);
    add(2, `${n}영업일 이내`, `within ${n} working days`, addWorkDays(S, n));
    add(1, `${n} 영업일 내`, `within ${n} business days`, addWorkDays(S, n));
    const c = pick([3, 7, 10, 14]);
    add(1, `D+${c}까지`, `within ${c} days`, addDays(S, c));
    if (ymd(S).d <= 24) add(1, pick(['월말까지', '이달 말까지', '금월 말까지']), pick(['by end of this month', 'by month-end', 'before the end of the month']), monthEnd(S));
  }
  const k = ri(2, 12); let ad = addDays(S, k); if (dow(ad) === 6) ad = addDays(ad, 2); else if (dow(ad) === 0) ad = addDays(ad, 1); // explicit deadlines fall on weekdays
  add(noRel ? 10 : 5, null, null, ad); // explicit
  const c = wpick(cands);
  if (c.ko === null) {
    return { ko: koDate(ad, noRel) + pick(['까지', ' 까지', '까지는']), en: pick(['by ', 'no later than ', 'before ', 'on or before ', 'by ']) + enDate(ad, noRel), due: ad, abs: true, dateKo: koDate(ad, noRel), dateEn: enDate(ad, noRel) };
  }
  return c;
}

// ---------- Korean particles ----------
function batchim(word) {
  const w = word.replace(/[\s)\]"'”’.]+$/, ''); if (!w) return false;
  const c = w.charCodeAt(w.length - 1);
  if (c >= 0xAC00 && c <= 0xD7A3) return (c - 0xAC00) % 28;
  const ch = w[w.length - 1];
  if (/[0-9]/.test(ch)) return { 0: 21, 1: 8, 3: 16, 6: 1, 7: 8, 8: 8 }[ch] || 0;
  if (/ng$/i.test(w)) return 21;
  if (/[LMN]$/.test(w) && /(^|[^A-Za-z])[A-Z]+$/.test(w)) return ch === 'L' ? 8 : 16; // acronyms: 엘/엠/엔
  if (/[mn]$/.test(w)) return 16;
  if (/l$/.test(w)) return 8;
  return 0;
}
function J(word, pair) {
  const [a, b] = pair.split('/'); const bc = batchim(word);
  if (pair === '으로/로') return word + (bc && bc !== 8 ? '으로' : '로');
  return word + (bc ? a : b);
}

// ---------- people / companies ----------
const OUR = { co: '한결E&C', coEn: 'Hangyeol E&C', dom: 'hgenc.com', addr: '서울특별시 강동구 고덕비즈밸리로 26, 한결타워 9층', addrEn: 'Hangyeol Tower 9F, 26 Godeok Bizvalley-ro, Gangdong-gu, Seoul 05203, Korea' };
const KO_SURN = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '류', '전', '홍', '고', '문', '양', '손', '배', '허', '남', '노', '하'];
const KO_GIVEN = ['민준', '서연', '지훈', '유진', '현우', '수빈', '성민', '재희', '하늘', '상철', '정민', '동욱', '혁준', '보람', '재석', '민호', '현석', '소영', '승표', '지원', '준영', '태호', '은지', '영수', '경호', '미정', '용준', '세영', '도윤', '주희', '창민', '나래', '기훈', '선영', '우성', '혜진', '종혁', '다은', '형준', '윤아'];
const ROMAN = { 김: 'kim', 이: 'lee', 박: 'park', 최: 'choi', 정: 'jung', 강: 'kang', 조: 'cho', 윤: 'yoon', 장: 'jang', 임: 'lim', 한: 'han', 오: 'oh', 서: 'seo', 신: 'shin', 권: 'kwon', 황: 'hwang', 안: 'ahn', 송: 'song', 류: 'ryu', 전: 'jeon', 홍: 'hong', 고: 'ko', 문: 'moon', 양: 'yang', 손: 'son', 배: 'bae', 허: 'heo', 남: 'nam', 노: 'noh', 하: 'ha' };
const KO_TITLES = ['사원', '대리', '과장', '차장', '부장', '책임', '선임', '수석', '프로', '매니저'];
const KO_TITLE_EN = { 사원: 'Engineer', 대리: 'Assistant Manager', 과장: 'Manager', 차장: 'Deputy General Manager', 부장: 'General Manager', 책임: 'Senior Engineer', 선임: 'Engineer', 수석: 'Principal Engineer', 프로: 'Professional', 매니저: 'Manager' };
const OUR_DEPTS = ['계장ENG그룹', '계장ENG그룹', '계장ENG그룹', '구매팀', '공정설계팀', '전기ENG그룹', '품질검사팀', '공무팀', '현장 계장팀', '시운전팀', 'PM팀', '배관설계팀'];
const DEPT_EN = { 계장ENG그룹: 'I&C Engineering Group', 구매팀: 'Procurement Team', 공정설계팀: 'Process Engineering Team', 전기ENG그룹: 'Electrical Engineering Group', 품질검사팀: 'QA/QC Team', 공무팀: 'Project Control Team', '현장 계장팀': 'Site I&C Team', 시운전팀: 'Commissioning Team', PM팀: 'PM Team', 배관설계팀: 'Piping Design Team' };
const FOREIGN = ['John Smith', 'Rajesh Kumar', 'Ahmed Al-Harbi', 'Marco Rossi', 'Hans Mueller', 'Sarah Thompson', 'Tan Wei Ming', 'Priya Nair', 'David Chen', 'Kenji Tanaka', 'Mohammed Al-Qahtani', 'Pieter de Vries', 'Carlos Mendez', 'Emma Johansson', 'Lukas Schneider', 'Nguyen Van Minh', 'Arjun Patel', 'Fatima Zahra', "Michael O'Brien", 'Thomas Becker', 'Satoshi Yamamoto', 'Liam Walsh', 'Sophie Martin', 'Ravi Shankar', 'Ivan Petrov', 'Lim Boon Keat', 'Anil Menon', 'Giulia Bianchi', 'Stefan Weber', 'Hiroshi Sato', 'Daniel Okafor', 'Chloe Dubois', 'Vikram Rao', 'Omar Haddad', 'Jessica Wong', 'Mark Jensen'];
const EN_TITLES = ['Project Manager', 'Sales Engineer', 'Application Engineer', 'Project Engineer', 'Document Controller', 'Quality Manager', 'Inspection Coordinator', 'Lead Instrument Engineer', 'Expediting Coordinator', 'Service Engineer', 'Key Account Manager', 'Technical Sales Manager', 'Order Handling Specialist'];
// vendor: name, sub(brand), domain, cats, local(korean branch?), tz
const VENDORS = [
  { co: 'Emerson Automation Solutions', brand: 'Fisher', dom: 'emerson.com', cats: ['Control Valve'], ko: '한국에머슨' },
  { co: 'Emerson Automation Solutions', brand: 'Rosemount', dom: 'emerson.com', cats: ['Transmitter', 'Level', 'Flow Meter'], ko: '한국에머슨' },
  { co: 'Emerson Automation Solutions', brand: 'Bettis', dom: 'emerson.com', cats: ['On/Off Valve'], ko: '한국에머슨' },
  { co: 'Emerson Automation Solutions', brand: 'Anderson Greenwood Crosby', dom: 'emerson.com', cats: ['PSV'], ko: '한국에머슨' },
  { co: 'Yokogawa Electric Korea', brand: 'Yokogawa', dom: 'yokogawa.com', cats: ['DCS/SIS', 'Transmitter', 'Analyzer', 'Flow Meter'], ko: '한국요꼬가와전기' },
  { co: 'Endress+Hauser', brand: 'Endress+Hauser', dom: 'endress.com', cats: ['Flow Meter', 'Level', 'Transmitter'], ko: '엔드레스하우저코리아' },
  { co: 'Rotork Controls', brand: 'Rotork', dom: 'rotork.com', cats: ['MOV'], ko: '로토크코리아' },
  { co: 'AUMA Riester GmbH & Co. KG', brand: 'AUMA', dom: 'auma.com', cats: ['MOV'], ko: '아우마코리아' },
  { co: 'SAMSON AG', brand: 'SAMSON', dom: 'samsongroup.com', cats: ['Control Valve'], ko: '삼손코리아' },
  { co: 'Flowserve Corporation', brand: 'Flowserve Valtek', dom: 'flowserve.com', cats: ['Control Valve'], ko: '플로우서브코리아' },
  { co: 'Flowserve Corporation', brand: 'Flowserve Pumps', dom: 'flowserve.com', cats: ['Pump'], ko: '플로우서브코리아' },
  { co: 'KROHNE Messtechnik', brand: 'KROHNE', dom: 'krohne.com', cats: ['Flow Meter', 'Level'], ko: '크로네코리아' },
  { co: 'VEGA Grieshaber KG', brand: 'VEGA', dom: 'vega.com', cats: ['Level'], ko: '베가코리아' },
  { co: 'Honeywell Process Solutions', brand: 'Honeywell', dom: 'honeywell.com', cats: ['DCS/SIS', 'F&G'], ko: '한국하니웰' },
  { co: 'ABB Ltd.', brand: 'ABB', dom: 'abb.com', cats: ['Analyzer', 'Transmitter', 'Flow Meter'], ko: 'ABB코리아' },
  { co: 'Siemens AG', brand: 'Siemens', dom: 'siemens.com', cats: ['Analyzer', 'DCS/SIS'], ko: '한국지멘스' },
  { co: 'Valmet Flow Control', brand: 'Neles', dom: 'valmet.com', cats: ['On/Off Valve', 'Control Valve'], ko: '발메트코리아' },
  { co: 'Baker Hughes', brand: 'Masoneilan', dom: 'bakerhughes.com', cats: ['Control Valve'], ko: '베이커휴즈코리아' },
  { co: 'Baker Hughes', brand: 'Consolidated', dom: 'bakerhughes.com', cats: ['PSV'], ko: '베이커휴즈코리아' },
  { co: 'Azbil Corporation', brand: 'Azbil', dom: 'azbil.com', cats: ['Control Valve'], ko: '아즈빌코리아' },
  { co: 'KSB SE & Co. KGaA', brand: 'KSB', dom: 'ksb.com', cats: ['Pump'], ko: 'KSB코리아' },
  { co: 'LESER GmbH', brand: 'LESER', dom: 'leser.com', cats: ['PSV'], ko: '레저코리아' },
  { co: 'Det-Tronics', brand: 'Det-Tronics', dom: 'det-tronics.com', cats: ['F&G'], ko: '' },
  { co: 'MSA Safety', brand: 'MSA', dom: 'msasafety.com', cats: ['F&G'], ko: 'MSA코리아' },
  { co: '동명계장(주)', brand: '동명계장', dom: 'dongmyung-ic.co.kr', cats: ['Cable/JB'], kor: true },
  { co: '한영케이블(주)', brand: '한영케이블', dom: 'hycable.co.kr', cats: ['Cable/JB'], kor: true },
  { co: '성진밸브(주)', brand: '성진밸브', dom: 'sjvalve.co.kr', cats: ['On/Off Valve'], kor: true },
  { co: '대성계전(주)', brand: '대성계전', dom: 'dsgj.co.kr', cats: ['Cable/JB', 'DCS/SIS'], kor: true },
  { co: '신일계기(주)', brand: '신일계기', dom: 'shinilgauge.co.kr', cats: ['Transmitter'], kor: true },
  { co: '삼우E&I(주)', brand: '삼우E&I', dom: 'samwoo-ei.com', cats: ['Analyzer'], kor: true },
];
const PROJECTS = [
  { code: 'P-2417', name: 'RUWAIS GPP Expansion', ko: '루와이스 GPP 증설' }, { code: 'P-2503', name: 'YEOSU NCC #3', ko: '여수 NCC 3기' },
  { code: 'P-2388', name: 'BORA PP/PE', ko: '보라 PP/PE' }, { code: 'P-2521', name: 'ULSAN PX Revamp', ko: '울산 PX 개조' },
  { code: 'P-2455', name: 'KASCO GOSP-4', ko: 'KASCO GOSP-4' }, { code: 'P-2602', name: 'DANG-JIN H2 Plant', ko: '당진 수소 플랜트' },
  { code: 'P-2490', name: 'HAI-AN LNG Terminal', ko: '하이안 LNG 터미널' }, { code: 'P-2533', name: 'SAMRA CCPP', ko: '삼라 복합화력' },
];

function koPerson(depts) {
  const s = pick(KO_SURN), g = pick(KO_GIVEN); const title = pick(KO_TITLES);
  const dept = pick(depts || OUR_DEPTS);
  const em = `${g === '민준' ? 'mj' : romanGiven(g)}.${ROMAN[s]}@${OUR.dom}`;
  return { name: s + g, title, dept, co: OUR.co, email: em, ko: true, en: `${capital(romanGiven(g))} ${capital(ROMAN[s])}`, ours: true };
}
function romanGiven(g) { const m = { 민: 'min', 준: 'jun', 서: 'seo', 연: 'yeon', 지: 'ji', 훈: 'hoon', 유: 'yu', 진: 'jin', 현: 'hyun', 우: 'woo', 수: 'su', 빈: 'bin', 성: 'sung', 재: 'jae', 희: 'hee', 하: 'ha', 늘: 'neul', 상: 'sang', 철: 'chul', 정: 'jung', 동: 'dong', 욱: 'wook', 혁: 'hyuk', 보: 'bo', 람: 'ram', 석: 'seok', 호: 'ho', 소: 'so', 영: 'young', 승: 'seung', 표: 'pyo', 원: 'won', 태: 'tae', 은: 'eun', 경: 'kyung', 미: 'mi', 용: 'yong', 세: 'se', 도: 'do', 윤: 'yoon', 주: 'joo', 창: 'chang', 나: 'na', 래: 'rae', 기: 'ki', 선: 'sun', 혜: 'hye', 종: 'jong', 다: 'da', 형: 'hyung', 아: 'a' }; return [...g].map((c) => m[c] || 'x').join(''); }
function capital(x) { return x.charAt(0).toUpperCase() + x.slice(1); }
function vendorPerson(v) {
  if (v.kor) { const s = pick(KO_SURN), g = pick(KO_GIVEN); return { name: s + g, title: pick(['과장', '대리', '부장', '차장', '이사', '팀장']), dept: pick(['영업팀', '기술영업팀', '공사팀', '품질팀', '설계팀']), co: v.co, email: `${romanGiven(g)}.${ROMAN[s]}@${v.dom}`, ko: true, vendor: v, en: `${capital(romanGiven(g))} ${capital(ROMAN[s])}` }; }
  if (v.ko && chance(0.3)) { const s = pick(KO_SURN), g = pick(KO_GIVEN); return { name: s + g, title: pick(['과장', '부장', '차장', '대리', '책임']), dept: pick(['프로젝트팀', '영업본부', '기술지원팀', 'Project Execution']), co: v.ko, email: `${romanGiven(g)}.${ROMAN[s]}@${v.dom}`, ko: true, vendor: v, en: `${capital(romanGiven(g))} ${capital(ROMAN[s])}`, enTitle: pick(EN_TITLES) }; }
  const n = pick(FOREIGN); return { name: n, title: pick(EN_TITLES), dept: v.brand, co: v.co, email: n.toLowerCase().replace(/[^a-z ]/g, '').replace(/ /g, '.') + '@' + v.dom, ko: false, vendor: v, en: n };
}

// ---------- display names in headers ----------
function dispName(p, style, lang) {
  if (!p.ko) return pick([p.name, p.name, `${p.name} (${p.vendor ? p.vendor.brand : 'EXT'})`]);
  if (style === 'knox') return lang === 'en' && chance(0.4) ? `${p.name}/${p.enTitle || KO_TITLE_EN[p.title] || p.title}/${DEPT_EN[p.dept] || p.dept}/${p.co}` : `${p.name}/${p.title}/${p.dept}/${p.co}`;
  return pick([p.name, `${p.name} ${p.title}`, `${p.name}(${p.en})`, `${p.name}/${p.dept}`, `${p.name} / ${p.title} / ${p.co}`]);
}
function addr(p, style, lang) { const d = dispName(p, style, lang); return chance(0.85) ? `${d} <${p.email}>` : `"${d}" <${p.email}>`; }
function addrList(ps, style, lang) { return ps.map((p) => addr(p, style, lang)).join(style === 'outlook_en' || style === 'outlook_ko' ? '; ' : ', '); }

// sent date/time strings per style
function sentStr(style, lang, S, T, ko) {
  const { y, m, d } = ymd(S); const h = +T.slice(0, 2), mi = +T.slice(2); const w = dow(S);
  const ap = h < 12 ? '오전' : '오후'; const apE = h < 12 ? 'AM' : 'PM'; const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  const sec = pad(ri(0, 59));
  switch (style) {
    case 'knox': return ko ? pick([`${y}-${pad(m)}-${pad(d)} (${KO_DOW[w]}) ${ap} ${h12}:${pad(mi)}`, `${y}-${pad(m)}-${pad(d)} ${pad(h)}:${pad(mi)}:${sec}`, `${y}.${pad(m)}.${pad(d)} ${pad(h)}:${pad(mi)}`, `${y}-${pad(m)}-${pad(d)} ${pad(h)}:${pad(mi)} (GMT+09:00)`])
      : pick([`${y}-${pad(m)}-${pad(d)} ${pad(h)}:${pad(mi)} (GMT+09:00)`, `${y}-${pad(m)}-${pad(d)} ${pad(h)}:${pad(mi)}:${sec}`]);
    case 'outlook_ko': return pick([`${y}년 ${m}월 ${d}일 ${KO_DOW[w]}요일 ${ap} ${h12}:${pad(mi)}`, `${y}년 ${m}월 ${d}일 ${KO_DOW[w]}요일 ${ap} ${h12}:${pad(mi)}`, `${y}-${pad(m)}-${pad(d)} (${KO_DOW[w]}) ${ap} ${h12}:${pad(mi)}`]);
    case 'outlook_en': return pick([`${EN_DOW[w]}, ${EN_MON[m - 1]} ${d}, ${y} ${h12}:${pad(mi)} ${apE}`, `${EN_DOW[w]}, ${EN_MON[m - 1]} ${d}, ${y} ${h12}:${pad(mi)} ${apE}`, `${EN_DOW[w]}, ${d} ${EN_MON[m - 1]} ${y} ${pad(h)}:${pad(mi)}`, `${EN_DOW3[w]}, ${d} ${EN_MON3[m - 1]} ${y} ${pad(h)}:${pad(mi)}:${sec} +0900`]);
    case 'gmail': return ko ? pick([`${y}년 ${m}월 ${d}일 (${KO_DOW[w]}) ${ap} ${h12}:${pad(mi)}`, `${y}. ${m}. ${d}. ${ap} ${h12}:${pad(mi)}`]) : pick([`${EN_MON3[m - 1]} ${d}, ${y}, ${h12}:${pad(mi)} ${apE}`, `${EN_DOW3[w]}, ${EN_MON3[m - 1]} ${d}, ${y} at ${h12}:${pad(mi)} ${apE}`, `${EN_DOW3[w]}, ${EN_MON3[m - 1]} ${d}, ${y}, ${h12}:${pad(mi)} ${apE}`]);
    case 'notes': return pick([`${pad(m)}/${pad(d)}/${y} ${pad(h12)}:${pad(mi)} ${apE}`, `${y}/${pad(m)}/${pad(d)} ${pad(h)}:${pad(mi)}`, d > 12 ? `${pad(d)}.${pad(m)}.${y} ${pad(h)}:${pad(mi)}` : `${y}-${pad(m)}-${pad(d)} ${pad(h)}:${pad(mi)}`]);
  }
  return '';
}

// header block. msg: {from,to,cc,subj,S,T}; ko = UI language Korean?
function header(style, lang, msg, ocr) {
  const ko = lang !== 'en' || (style === 'knox' && chance(0.5)) || style === 'outlook_ko';
  const fr = addr(msg.from, style, lang); const to = addrList(msg.to, style, lang); const cc = msg.cc.length ? addrList(msg.cc, style, lang) : '';
  const st = sentStr(style, lang, msg.S, msg.T, ko); const L = [];
  if (style === 'knox') {
    if (ko) {
      const sp = pick([' ', ' : ', '\t']);
      if (chance(0.6)) L.push(msg.subj); else L.push(`제목${sp}${msg.subj}`);
      L.push(`보낸 사람${sp}${fr}`); if (chance(0.5)) { L.push(`받는 사람${sp}${to}`); if (cc) L.push(`참조${sp}${cc}`); L.push(`보낸 날짜${sp}${st}`); }
      else { L.push(`보낸 날짜${sp}${st}`); L.push(`받는 사람${sp}${to}`); if (cc) L.push(`참조${sp}${cc}`); }
    } else {
      L.push(`Title : ${msg.subj}`, `Sender : ${fr}`, `Date : ${st}`, `To : ${to}`); if (cc) L.push(`CC : ${cc}`);
    }
  } else if (style === 'outlook_ko') {
    L.push(`보낸 사람: ${fr}`, `보낸 날짜: ${st}`, `받는 사람: ${to}`); if (cc) L.push(`참조: ${cc}`); L.push(`제목: ${msg.subj}`);
    if (msg.att && chance(0.5)) L.push(`첨부: ${msg.att.join('; ')}`);
  } else if (style === 'outlook_en') {
    L.push(`From: ${fr}`, `${chance(0.8) ? 'Sent' : 'Date'}: ${st}`, `To: ${to}`); if (cc) L.push(`Cc: ${cc}`); L.push(`Subject: ${msg.subj}`);
    if (msg.att && chance(0.5)) L.push(`Attachments: ${msg.att.join('; ')}`);
  } else if (style === 'gmail') {
    L.push(msg.subj + (chance(0.5) ? (ko ? '\n받은편지함' : '\nInbox') : ''), '');
    L.push(`${msg.from.name} <${msg.from.email}>`, st + (chance(0.4) ? (ko ? ` (${ri(1, 5)}시간 전)` : ` (${ri(1, 3)} days ago)`) : ''));
    L.push(ko ? `나에게${msg.cc.length ? ', ' + msg.cc[0].name : ''} ▼` : `to me${msg.cc.length ? ', ' + msg.cc[0].name : ''} ▾`);
  } else if (style === 'notes') {
    const fn = msg.from.ko ? `${msg.from.name}/${msg.from.dept}/${msg.from.co}` : `${msg.from.name}/${(msg.from.vendor || {}).brand || 'EXT'}`;
    if (chance(0.5)) { L.push(`${fn}`, `${st}`, ''); L.push(`${ko ? '받는 사람' : 'To'}: ${to}`); if (cc) L.push(`${ko ? '참조' : 'cc'}: ${cc}`); L.push(`${ko ? '제목' : 'Subject'}: ${msg.subj}`); }
    else { L.push(`From: ${fn}@${(msg.from.vendor || {}).brand ? msg.from.vendor.brand.toUpperCase().replace(/[^A-Z]/g, '') : 'HGENC'}`, `Date: ${st}`, `To: ${to}`); if (cc) L.push(`cc: ${cc}`); L.push(`Subject: ${msg.subj}`); }
  }
  let h = L.join('\n');
  if (ocr) h = ocrNoise(h, ko);
  return h;
}
function ocrNoise(h, ko) {
  const top = ko ? pick(['답장  전체답장  전달  삭제  스팸신고', '← 받은메일함   ☆', '답장 | 전체답장 | 전달 | ⋯', '메일 > 받은메일함']) : pick(['Reply   Reply All   Forward   ...', '← Inbox   ☆   ⋮', 'Reply | Reply all | Forward']);
  h = h.replace(/</g, chance(0.5) ? '<' : '‹').replace(/>/g, chance(0.5) ? '>' : '›');
  if (chance(0.5)) h = h.replace(/보낸 사람/g, '보낸사람').replace(/받는 사람/g, '받는사람');
  return top + '\n' + h + (chance(0.5) ? '\n' + pick(['□ 첨부파일 2개 (3.1MB)  모두 저장', '📎 2 attachments', '∨ 자세히']) : '');
}

// ---------- greetings / closings / signatures / disclaimers ----------
function greetKo(to, fr) { const p = to; return pick([`${p.name} ${p.title}님, 안녕하세요.`, fr ? `안녕하십니까, ${fr.co}${fr.ours ? ' ' + fr.dept : ''} ${fr.name}입니다.` : `${p.name} ${p.title}님께,`, `${p.name} ${p.title}님`, `수고 많으십니다.`, `${p.name}님 안녕하세요.`, `안녕하세요, ${p.name} ${p.title}님.\n${pick(['늘 협조에 감사드립니다.', '수고 많으십니다.', '바쁘신 와중에 회신 감사합니다.'])}`, `${p.co} ${p.name} ${p.title}님께,`]); }
function greetEn(to, fr) { const fn = to.ko ? `Mr. ${to.en.split(' ')[1]}` : to.name.split(' ')[0]; return pick([`Dear ${fn},`, `Dear Sir/Madam,`, `Hi ${fn},`, `Dear ${to.name},`, `Hello ${fn},`, `Dear All,`, `Good day ${fn},`, `Dear ${fn},\n\nGreetings from ${fr && !fr.ours && fr.vendor ? fr.vendor.brand : 'Seoul'}.`]); }
function sigKo(p) {
  const tel = `02-${ri(2000, 6999)}-${ri(1000, 9999)}`, mob = `010-${ri(2000, 9999)}-${ri(1000, 9999)}`;
  const close = pick(['감사합니다.', '감사합니다.\n', '수고하세요.', '감사합니다.\n' + p.name + ' 드림', '이상입니다.\n감사합니다.', '잘 부탁드립니다.']);
  if (!chance(0.6)) return close.includes(p.name) ? close : close.replace(/\n$/, '') + '\n' + p.name + (chance(0.5) ? ' 드림' : '');
  const ours = p.ours; const lines = [close, '', pick(['--', '———————————————', '', '-------------------------------------------'])];
  lines.push(`${p.name} ${p.title} | ${p.dept} | ${p.co}${ours ? ' 플랜트사업본부' : ''}`);
  lines.push(`Tel. ${tel} | Mobile. ${mob}`, `E-mail. ${p.email}`);
  if (ours && chance(0.6)) lines.push(OUR.addr);
  return lines.join('\n');
}
function sigEn(p) {
  const close = pick(['Best regards,', 'Kind regards,', 'Regards,', 'Thanks & regards,', 'Best Regards,', 'Thank you and best regards,', 'Sincerely,', 'BR,']);
  const nm = p.ko ? p.en : p.name;
  if (!chance(0.7)) return `${close}\n${nm}`;
  const t = p.ko ? (p.enTitle || KO_TITLE_EN[p.title] || p.title) : p.title;
  const lines = [close, nm, `${t}${p.vendor ? ' | ' + p.vendor.brand : ' | ' + (DEPT_EN[p.dept] || p.dept)}`, p.ours ? OUR.coEn : p.co];
  if (p.ours || p.ko) lines.push(`T +82 2 ${ri(2000, 6999)} ${ri(1000, 9999)} | M +82 10 ${ri(2000, 9999)} ${ri(1000, 9999)}`); else lines.push(pick([`T +82 2 ${ri(2000, 6999)} ${ri(1000, 9999)} | M +82 10 ${ri(2000, 9999)} ${ri(1000, 9999)}`, `Phone: +65 6${ri(100, 999)} ${ri(1000, 9999)}  Mobile: +65 9${ri(100, 999)} ${ri(1000, 9999)}`, `Tel: +49 ${ri(30, 89)} ${ri(100000, 999999)}`, `Direct: +971 2 ${ri(100, 999)} ${ri(1000, 9999)}`, `M: +91 98${ri(10000000, 99999999)}`]));
  lines.push(p.email); if (p.ours) lines.push(OUR.addrEn); else if (chance(0.4)) lines.push(`www.${p.vendor ? p.vendor.dom : 'example.com'}`);
  return lines.join('\n');
}
const DISCLAIMERS = [
  'CONFIDENTIALITY NOTICE: This e-mail message, including any attachments, is for the sole use of the intended recipient(s) and may contain confidential and privileged information. Any unauthorized review, use, disclosure or distribution is prohibited. If you are not the intended recipient, please contact the sender by reply e-mail and destroy all copies of the original message.',
  'This email has been scanned for viruses and malware by Mimecast Ltd.',
  'Please consider the environment before printing this e-mail.',
  '본 메일은 ' + OUR.co + '의 영업비밀 및 기밀정보를 포함하고 있을 수 있으며, 수신인 이외의 자가 열람·복사·배포하는 것을 금합니다. 잘못 수신하신 경우 발신인에게 회신하신 후 즉시 삭제하여 주시기 바랍니다.',
  '※ 본 메일은 발신전용이 아닙니다. 회신 시 참조인을 유지해 주시기 바랍니다.',
  'DISCLAIMER: The information contained in this communication is intended solely for the use of the individual or entity to whom it is addressed. If you have received this communication in error, please notify us immediately by responding to this email and then delete it from your system.',
  '[EXTERNAL] This email originated from outside of the organization. Do not click links or open attachments unless you recognize the sender and know the content is safe.',
  '이 메일은 보안 정책에 따라 외부로 발송되었습니다. 첨부파일은 30일 후 자동 삭제됩니다.',
  'Emerson and the Emerson logo are trademarks and service marks of Emerson Electric Co. This message may contain confidential information.',
  '--\nThis message has been scanned by Symantec Email Security.cloud.',
];

// =====================================================================================
// HAND-WRITTEN E-MAILS (h1..h40).  Labels are sentence-local: a req's due is the deadline
// stated in the same sentence (or in a "기한:/Due date:" line belonging to that one request).
// =====================================================================================
const HAND = [];
// r: [[kw,due],..]  s: [[due,time],..]
function H(o) { HAND.push(o); }

H({ lang: 'ko', style: 'knox', subj: '[P-2417] FCV-1101 외 12건 Control Valve Datasheet 검토 의견 송부 (Code 2)', from: '정현우', date: '2026-11-18', time: '1430',
  r: [['A351 CF8M', ''], ['Low-noise trim', '2026-11-20'], ['Class V', ''], ['PST 적용 여부', ''], ['FCV-1110', ''], ['Rev.1 재제출', '2026-11-25'], ['Cv 계산서', '']],
  s: [['2026-11-23', '1000']], items: ['Control Valve'], text:
`[P-2417] FCV-1101 외 12건 Control Valve Datasheet 검토 의견 송부 (Code 2)
보낸 사람 정현우/책임/계장ENG그룹/한결E&C <hyunwoo.jung@hgenc.com>
받는 사람 김태호/과장/프로젝트팀/한국에머슨 <taeho.kim@emerson.com>
참조 이서연/선임/계장ENG그룹/한결E&C <seoyeon.lee@hgenc.com>, 박기훈/대리/구매팀/한결E&C <kihoon.park@hgenc.com>
보낸 날짜 2026-11-18 (수) 오후 2:30

김태호 과장님, 안녕하세요.
한결E&C 계장ENG그룹 정현우입니다.

지난 11/9 제출해 주신 Control Valve Datasheet (P2417-EMR-IC-DS-0012 Rev.0) 검토 결과 Code 2 (Comments as noted, proceed with fabrication)로 회신드립니다.
주요 코멘트는 아래와 같습니다.

1. FCV-1101: Body material A216 WCB → A351 CF8M 으로 변경 필요합니다 (Process fluid: sour water).
2. FCV-1104 / FCV-1107: 계산 noise 87 dBA 이므로 85 dBA 이하 만족을 위한 Low-noise trim 적용 검토 부탁드립니다. (본 항목은 11/20(금)까지 우선 회신 요망)
3. 전체 Tag: Seat leakage class 를 ANSI/FCI 70-2 Class IV → Class V 로 수정 바랍니다 (Spec. 요구사항).
4. Positioner 가 DVC6200 HART 7 로 되어 있는데, Tag 별 PST 적용 여부를 Datasheet 에 표기 바랍니다.
5. Actuator fail action (FC/FO) 이 P&ID 와 상이한 Tag 3건 (FCV-1110, -1111, -1112) 확인 요망.

상기 코멘트 반영하여 11/25(수)까지 Rev.1 재제출 바랍니다.
Cv 계산서 (Fisher Specification Manager 출력본)는 별도로 송부 부탁드립니다.

참고로 다음 주 월요일(11/23) 오전 10시에 발주처 계장 코멘트 회의가 예정되어 있습니다.

감사합니다.
정현우 드림

정현우 책임 | 계장ENG그룹 | 한결E&C 플랜트사업본부
Tel. 02-3471-2286 | Mobile. 010-4418-2093
E-mail. hyunwoo.jung@hgenc.com` });

H({ lang: 'en', style: 'outlook_en', subj: 'RE: [P-2503] TBE Clarification - Pressure/DP Transmitters (Rosemount 3051S) - Round 2', from: 'Tan Wei Ming', date: '2026-11-19', time: '0947',
  r: [['nozzle elevation', ''], ['HART 7', ''], ['feedback', '2026-11-24']], s: [['2026-11-26', '']], items: ['Transmitter', 'Level'], text:
`From: Tan Wei Ming <weiming.tan@emerson.com>
Sent: Thursday, November 19, 2026 9:47 AM
To: 이서연/선임/계장ENG그룹/한결E&C <seoyeon.lee@hgenc.com>
Cc: Priya Nair <priya.nair@emerson.com>; 박기훈 <kihoon.park@hgenc.com>
Subject: RE: [P-2503] TBE Clarification - Pressure/DP Transmitters (Rosemount 3051S) - Round 2

Dear Ms. Lee,

Thank you for your clarification list. Please find our responses below.

Q1. Wetted parts for PT-3105A/B (H2S service) - NACE MR0175 compliance
A1. Confirmed. 316L SST diaphragm and process flange comply with NACE MR0175/ISO 15156. The certificate will be included in the final documentation.

Q2. Remote seal capillary length for LT-2101 (DP level)
A2. We have assumed 5 m on both sides. Kindly confirm the actual nozzle elevation difference so that we can finalize the capillary length and fill fluid (Syltherm XLT vs. DC 200).

Q3. SIL certificate for PT-3110A/B/C (SIS service, 2oo3)
A3. Rosemount 3051S SIS is SIL 2 capable (SIL 3 in redundant configuration) per exida FMEDA. FMEDA report attached.

Q4. Delivery
A4. 14-16 weeks ex-works after drawing approval.

In addition, the datasheet shows HART 5 while the DCS (CENTUM VP) supports HART 7. Could you please advise whether we should configure HART 5 or HART 7?

We would appreciate your feedback by Tuesday, 24 November, so that we can submit the revised TBE before your bid evaluation meeting on 26 Nov.

Best regards,
Tan Wei Ming
Application Engineer | Rosemount
Emerson Automation Solutions
Phone: +65 6777 8211  Mobile: +65 9123 4567
weiming.tan@emerson.com

-----Original Message-----
From: 이서연/선임/계장ENG그룹/한결E&C <seoyeon.lee@hgenc.com>
Sent: Monday, November 16, 2026 4:12 PM
To: Tan Wei Ming <weiming.tan@emerson.com>
Subject: [P-2503] TBE Clarification - Pressure/DP Transmitters (Rosemount 3051S) - Round 2

Dear Mr. Tan,

Please reply to the attached clarification list (Q1~Q4) by 18 Nov 2026.
Also please submit the updated price breakdown including 2-year operational spares.

Best regards,
Seoyeon Lee` });

H({ lang: 'ko', style: 'outlook_ko', subj: '[공지] 연말연시 계장ENG그룹 사무실 휴무 및 비상연락망 안내', from: '한상철', date: '2026-12-15', time: '1005',
  r: [], s: [], items: [], text:
`보낸 사람: 한상철 부장 <sangchul.han@hgenc.com>
보낸 날짜: 2026년 12월 15일 화요일 오전 10:05
받는 사람: 계장ENG그룹 전체 <ic-eng-all@hgenc.com>
참조: 공무팀 <pc-team@hgenc.com>
제목: [공지] 연말연시 계장ENG그룹 사무실 휴무 및 비상연락망 안내

계장ENG그룹 여러분, 한 해 동안 수고 많으셨습니다.

회사 방침에 따라 연말연시 휴무를 아래와 같이 안내드립니다.

  - 휴무 기간 : 2026년 12월 24일(목) ~ 2027년 1월 1일(금)
  - 업무 재개 : 2027년 1월 4일(월)
  - 비상 연락 : 현장 관련 긴급 사항은 각 프로젝트 Lead 에게 연락

휴무 기간 중 업체 발송 문서는 Aconex 로 정상 접수되며, 업무 재개 후 순차 처리 예정입니다.
문의사항 있으시면 공무팀 윤재희 과장(내선 2231)에게 연락 주시면 됩니다.

올 한 해 고생 많으셨습니다.
한상철 드림` });

H({ lang: 'en', style: 'gmail', subj: 'P-2455 KASCO GOSP-4 | Rotork IQ3 Pro Actuators - FAT Notification (PO 4500231187)', from: 'Anil Menon', date: '2026-11-17', time: '1842',
  r: [['names of attendees', '2026-11-24'], ['passport copies', '']], s: [['2026-12-03', '0930'], ['2026-11-30', '1400']], items: ['MOV'], text:
`P-2455 KASCO GOSP-4 | Rotork IQ3 Pro Actuators - FAT Notification (PO 4500231187)
Inbox

Anil Menon <anil.menon@rotork.com>
Nov 17, 2026, 6:42 PM (2 days ago)
to me, Kihoon ▾

Dear Mr. Kang,

Greetings from Rotork India.

We are pleased to inform you that the 46 nos. IQ3 Pro actuators for MOV-5101 ~ MOV-5146 have completed internal testing and are ready for FAT.

FAT details:
  Date / Time : Thursday, 3rd December 2026, 09:30 IST
  Venue       : Rotork Controls (India) Pvt. Ltd., Chennai works, Bay 4
  Scope       : Visual & dimensional check, torque/thrust test, insulation resistance, local/remote operation, Profibus DP-V1 communication test

A pre-FAT review meeting will be held via Teams on Monday, 30 Nov at 2:00 PM IST to walk through the FAT procedure (Doc. No. RTK-FATP-0231 Rev.1).

Kindly confirm the names of attendees (Company/TPI) by 24th November so that we can arrange gate passes.
For overseas attendees, please send us the passport copies for the visa invitation letters at your earliest convenience.

Please note that the FAT procedure was approved with Code 1 on 10-Nov-2026, so no further submission is required.

Thanks & regards,
Anil Menon
Project Engineer | Rotork Controls (India) Pvt. Ltd.
M: +91 98410 22871
anil.menon@rotork.com

This email has been scanned for viruses and malware by Mimecast Ltd.` });

H({ lang: 'ko', style: 'nohdr', subj: '', from: '', date: '', time: '',
  r: [['Loop folder', '2026-12-04'], ['교정 유효기간', ''], ['JB-105', '']], s: [['2026-12-07', ''], ['2026-12-09', '0900']], items: ['DCS/SIS', 'Cable/JB', 'Transmitter'], text:
`각 담당자님께,

Unit 100 (Feed Treating) Loop Check 일정 관련하여 공유드립니다.
DCS Energize 완료되어 2026년 12월 7일(월)부터 Unit 100 Loop Check 를 시작합니다.

  구분          대상            수량    비고
  AI/AO        PT/TT/FT/LT      312     HART 확인 포함
  DI/DO        XV/MOV/LS         148     Limit switch feedback
  SIS          ESD loop           64     발주처 입회 필수

발주처 입회 첫 회는 2026.12.09(수) 09:00, 100-CCR 에서 시작합니다.

요청 사항입니다.
- 서브콘(동명계장)은 Loop folder 출력본을 2026.12.04(금)까지 현장 사무실에 준비 바랍니다.
- 사용 예정 HART communicator (475/AMS Trex) 및 calibrator 의 교정 유효기간 확인 부탁드립니다.
- JB-105 ~ JB-112 는 아직 termination 미완료 상태이므로 금주 내 완료 여부 공유 부탁드립니다.

현장 계장팀 드림` });
// note: last request "금주 내" cannot be resolved (no sent date) -> due ''

H({ lang: 'en', style: 'outlook_en', subj: 'NCR-P2388-IC-017 / PMI Failure on FCV-2203 Body (Heat No. 7Y2215) - SAMSON PO 4500198822', from: 'Ji-won Moon', date: '2026-11-20', time: '1515',
  r: [['root cause analysis', '2026-11-27'], ['do not ship', ''], ['replacement body', '']], s: [['2026-12-01', '0900']], items: ['Control Valve'], text:
`From: Ji-won Moon <jiwon.moon@hgenc.com>
Sent: Friday, November 20, 2026 3:15 PM
To: Stefan Weber <stefan.weber@samsongroup.com>
Cc: Lukas Schneider <lukas.schneider@samsongroup.com>; 정현우 <hyunwoo.jung@hgenc.com>; QC Team <qc@hgenc.com>
Subject: NCR-P2388-IC-017 / PMI Failure on FCV-2203 Body (Heat No. 7Y2215) - SAMSON PO 4500198822
Attachments: NCR-P2388-IC-017.pdf; PMI_Report_FCV-2203.pdf

Dear Mr. Weber,

During the PMI test witnessed by our TPI (Bureau Veritas) on 19 November, the body of FCV-2203 (Type 3241, 6" CL600) showed Mo content of 1.62%, which is below the minimum 2.0% required for ASTM A351 CF8M. The NCR has been raised accordingly (attached).

Please submit the root cause analysis and corrective/preventive action plan within 5 working days.
Please do not ship any valves from the same heat number (7Y2215) until this NCR is formally closed.
We also request you to provide the EN 10204 3.1 material certificate of the replacement body prior to re-inspection.

Re-inspection (PMI on the replacement body) is tentatively scheduled for Tuesday, 1 December 2026 at 09:00 CET at your Frankfurt works.

Please note that the remaining 23 valves under this PO passed PMI and the IRN for those will be issued separately.

Best regards,
Jiwon Moon
QA/QC Team | Hangyeol E&C
T +82 2 3471 2510 | M +82 10 7721 4402
jiwon.moon@hgenc.com

CONFIDENTIALITY NOTICE: This e-mail message, including any attachments, is for the sole use of the intended recipient(s) and may contain confidential and privileged information. Any unauthorized review, use, disclosure or distribution is prohibited.` });

H({ lang: 'mix', style: 'knox', subj: '[회의록] 11/16 계장 주간회의 (P-2503 YEOSU NCC #3)', from: '이서연', date: '2026-11-16', time: '1740',
  r: [['I/O list Rev.C', '2026-11-20'], ['Hook-up drawing', '2026-11-24'], ['SPIR', ''], ['analyzer shelter', '2026-11-19']], s: [['2026-11-16', '0900'], ['2026-11-23', '0900'], ['2026-11-25', '1400'], ['2026-12-14', '']], items: ['DCS/SIS', 'Analyzer', 'Control Valve'], text:
`[회의록] 11/16 계장 주간회의 (P-2503 YEOSU NCC #3)
보낸 사람 이서연/선임/계장ENG그룹/한결E&C <seoyeon.lee@hgenc.com>
받는 사람 P2503 계장 TFT <p2503-ic@hgenc.com>
보낸 날짜 2026-11-16 (월) 오후 5:40

안녕하세요, 이서연입니다.
오늘 진행한 계장 주간회의 회의록 공유드립니다.

■ 일시/장소: 11/16(월) 09:00~10:30, 본사 9층 소회의실
■ 참석: 한상철 부장, 정현우 책임, 이서연 선임, 박기훈 대리(구매), 조성민 과장(공정)

1. Progress
 - Instrument Index Rev.B IFR 발행 완료 (11/13)
 - Control Valve TBE: Fisher / Samson / Valtek 3사 기술평가 완료, commercial open 대기
 - DCS IFAT 일정: Yokogawa 측 12/14 착수 제안 (확정 전)

2. Action Items
 - I/O list Rev.C 업데이트 (Hold 해제 18건 반영) → 정현우 책임, 11/20(금)까지 완료 부탁드립니다.
 - Hook-up drawing Typical 12종 IFC 발행 → 이서연 선임, 11/24(화)까지
 - Control valve SPIR 양식 vendor 송부 → 박기훈 대리, 진행 부탁드립니다.
 - AT-901~AT-915 analyzer shelter layout 공정팀 확인 → 조성민 과장님, 11/19(목)까지 의견 부탁드립니다.

3. 기타
 - 다음 주간회의: 차주 월요일 9시 동일 장소
 - 11/25(수) 오후 2시 발주처 Monthly progress meeting (Teams) 참석 예정

누락/수정 사항 있으면 말씀 주세요.
감사합니다.` });

H({ lang: 'en', style: 'notes', subj: 'P-2455 / AUMA SA 14.2 + AM - Revised delivery schedule (Notification of delay)', from: 'Thomas Becker', date: '2026-11-18', time: '0812',
  r: [], s: [['2026-12-15', ''], ['2027-01-20', '']], items: ['MOV'], text:
`Thomas Becker/AUMA
18.11.2026 08:12

To: 강기훈/구매팀/한결E&C <kihoon.kang@hgenc.com>
cc: Giulia Bianchi <giulia.bianchi@auma.com>, 정현우 <hyunwoo.jung@hgenc.com>
Subject: P-2455 / AUMA SA 14.2 + AM - Revised delivery schedule (Notification of delay)

Dear Mr. Kang,

We regret to inform you that the delivery of the 18 nos. SA 14.2 multi-turn actuators (MOV-5201 ~ MOV-5218) will be delayed by approximately two weeks due to a late delivery of the motor housings from our sub-supplier.

Revised schedule:
   Final inspection (internal)  : week 49
   Revised ETD Hamburg          : 15-Dec-2026
   Revised ETA Busan            : 20-Jan-2027 (subject to vessel schedule)

We will send you the updated manufacturing progress report and the revised delivery schedule by Friday.
Please note that this delay does not affect the remaining items under the same order (gearboxes GS 125.3), which will be shipped as originally planned.

We sincerely apologize for the inconvenience. Should you have any questions, please do not hesitate to contact me.

Mit freundlichen Gruessen / Best regards
Thomas Becker
Order Handling Specialist
AUMA Riester GmbH & Co. KG
Tel: +49 7631 809 1472
thomas.becker@auma.com` });

H({ lang: 'ko', style: 'outlook_ko', subj: 'RE: [P-2521] Analyzer Shelter RFQ 견적 접수 - TBE 작성 요청', from: '박기훈', date: '2026-11-12', time: '1120',
  r: [['TBE 작성', '2026-11-18'], ['Deviation list', '']], s: [['2026-11-19', '1500']], items: ['Analyzer'], text:
`보낸 사람: 박기훈 대리 <kihoon.park@hgenc.com>
보낸 날짜: 2026년 11월 12일 목요일 오전 11:20
받는 사람: 정현우 책임 <hyunwoo.jung@hgenc.com>
참조: 이서연 선임 <seoyeon.lee@hgenc.com>; 한상철 부장 <sangchul.han@hgenc.com>
제목: RE: [P-2521] Analyzer Shelter RFQ 견적 접수 - TBE 작성 요청
첨부: ABB_Quotation_Q26-0871.pdf; Siemens_Offer_AS-2611.pdf; 삼우EI_견적서.pdf

정현우 책임님,

Analyzer Shelter (AT-901~AT-915, GC 3대 포함) RFQ 에 대해 3개사 (ABB, Siemens, 삼우E&I) 견적서 접수되어 첨부와 같이 송부드립니다.
가격은 commercial 쪽에서 별도로 평가하고 있으니, 기술 사항만 봐 주시면 됩니다.

차주 수요일까지 TBE 작성 부탁드립니다.
특히 Siemens 오퍼는 shelter HVAC 이 별도 옵션으로 되어 있어 scope 비교가 필요하니, Deviation list 정리도 같이 부탁드립니다.

참고로 11/19(목) 오후 3시에 3개사 clarification meeting (Teams) 잡아 두었습니다.

감사합니다.
박기훈 드림

-----원본 메시지-----
보낸 사람: 정현우 책임 <hyunwoo.jung@hgenc.com>
보낸 날짜: 2026년 11월 3일 화요일 오후 3:02
받는 사람: 박기훈 대리 <kihoon.park@hgenc.com>
제목: [P-2521] Analyzer Shelter RFQ 견적 접수 - TBE 작성 요청

기훈 대리님, 견적 들어오면 바로 공유 부탁드립니다. 11월 둘째 주까지는 받아야 일정 맞출 수 있습니다.` });

H({ lang: 'en', style: 'gmail', subj: 'Thank you - Yokogawa CENTUM VP FAT completed (P-2533 SAMRA CCPP)', from: 'Satoshi Yamamoto', date: '2026-11-09', time: '0815',
  r: [], s: [], items: ['DCS/SIS'], text:
`Thank you - Yokogawa CENTUM VP FAT completed (P-2533 SAMRA CCPP)

Satoshi Yamamoto <satoshi.yamamoto@yokogawa.com>
Mon, Nov 9, 2026, 8:15 AM
to me, Hyunwoo ▾

Dear Mr. Jung and team,

On behalf of the Yokogawa project team, I would like to thank you for your support and active participation during the CENTUM VP / ProSafe-RS FAT held in our Singapore facility last week.

All 214 test procedures were completed, and the 37 punch items raised during the FAT have been recorded in the FAT punch list (attached). Category A items have already been closed and Category B items will be closed before shipment.

We will issue the FAT report and the Inspection Release Note request within this week.

It was a pleasure working with you. If you need anything further, please let me know.

Best regards,
Satoshi Yamamoto
Project Manager | Yokogawa Engineering Asia Pte. Ltd.
satoshi.yamamoto@yokogawa.com` });

H({ lang: 'ko', style: 'knox', subj: 'RE: [P-2602] TW-4501 외 Thermowell Wake Frequency 계산서 제출 요청', from: '오승표', date: '2026-11-18', time: '0905',
  r: [], s: [], items: ['Transmitter'], text:
`RE: [P-2602] TW-4501 외 Thermowell Wake Frequency 계산서 제출 요청
보낸 사람 오승표/과장/기술영업팀/신일계기(주) <seungpyo.oh@shinilgauge.co.kr>
보낸 날짜 2026-11-18 (수) 오전 9:05
받는 사람 정현우/책임/계장ENG그룹/한결E&C <hyunwoo.jung@hgenc.com>

정현우 책임님, 안녕하세요.
신일계기 오승표입니다.

요청하신 TW-4501~TW-4512 Thermowell wake frequency 계산서 (ASME PTC 19.3 TW-2016 기준)는 현재 작성 중이며, 금요일까지 송부드리겠습니다.
다만 TW-4507 은 유속이 높아 velocity collar 적용이 필요할 수 있어, 결과 나오는 대로 별도로 말씀드리겠습니다.

감사합니다.
오승표 드림

--------- Original Message ---------
Sender : 정현우/책임/계장ENG그룹/한결E&C <hyunwoo.jung@hgenc.com>
Date : 2026-11-17 16:40 (GMT+09:00)
Title : [P-2602] TW-4501 외 Thermowell Wake Frequency 계산서 제출 요청

오 과장님, TW-4501~4512 wake frequency 계산서를 11/20(금)까지 제출 부탁드립니다.
공정 data sheet 는 첨부 참고 바랍니다.` });

H({ lang: 'en', style: 'outlook_en', subj: 'P-2455 GOSP-4 | Comments on SIL Verification Report (Doc. 2455-HG-IC-RPT-0041 Rev.A) - Code 3', from: 'Mohammed Al-Qahtani', date: '2026-11-22', time: '1030',
  r: [['24 months', ''], ['IEC 61508-6', ''], ['SIL certificates', ''], ['Spurious trip rate', ''], ['resubmit the revised report', '2026-12-02']], s: [], items: ['DCS/SIS', 'On/Off Valve', 'Transmitter'], text:
`From: Mohammed Al-Qahtani <m.alqahtani@kasco-energy.com>
Sent: Sunday, November 22, 2026 10:30 AM
To: 한상철 <sangchul.han@hgenc.com>
Cc: 정현우 <hyunwoo.jung@hgenc.com>; Omar Haddad <o.haddad@kasco-energy.com>; DCC <dcc-p2455@hgenc.com>
Subject: P-2455 GOSP-4 | Comments on SIL Verification Report (Doc. 2455-HG-IC-RPT-0041 Rev.A) - Code 3

Dear Mr. Han,

Please find below COMPANY comments on the subject document. The document is returned with Code 3 (Rejected - Revise and Resubmit).

1. SIF-101 (HP Separator high pressure trip, PT-1101A/B/C -> XV-1103/XV-1104): the PFDavg has been calculated with a proof test interval of 36 months. COMPANY requires 24 months; revise the calculation accordingly.
2. The common cause factor of 2% for the 2oo3 transmitters is not justified. Use beta = 5% unless a justification per IEC 61508-6 Annex D is provided.
3. Provide the SIL certificates (exida/TUV) for XV-1103/XV-1104 including the solenoid valves (ASCO 8316) and the Bettis actuators.
4. Spurious trip rate (STR) shall be included for each SIF.

Please resubmit the revised report within 10 days from the date of this transmittal.
A comment resolution meeting can be arranged if required.

Regards,
Mohammed Al-Qahtani
Lead Instrument & Control Engineer
KASCO Energy - Projects Department
Direct: +966 13 874 2201

DISCLAIMER: The information contained in this communication is intended solely for the use of the individual or entity to whom it is addressed. If you have received this communication in error, please notify us immediately by responding to this email and then delete it from your system.` });

H({ lang: 'ko', style: 'gmail', subj: '[동명계장] P-2503 계장 케이블 물량 확정 요청 (Cable Schedule Rev.3)', from: '노경호', date: '2026-11-18', time: '1647',
  r: [['물량 확정', '2026-11-19'], ['cable gland', '']], s: [], items: ['Cable/JB'], text:
`[동명계장] P-2503 계장 케이블 물량 확정 요청 (Cable Schedule Rev.3)
받은편지함

노경호 <kyungho.noh@dongmyung-ic.co.kr>
2026년 11월 18일 (수) 오후 4:47
나에게, 이서연 ▼

이서연 선임님 안녕하세요.
동명계장 공사팀 노경호 차장입니다.

Cable Schedule Rev.3 기준 설계물량과 현장 실측물량을 비교한 결과 아래와 같이 차이가 발생하였습니다.

구분	규격	설계물량(m)	실측물량(m)	차이(m)
Signal	1P x 1.25SQ (IS)	48,200	51,650	+3,450
Multi-pair	12P x 0.75SQ	9,800	9,320	-480
Multi-pair	24P x 0.75SQ	6,450	7,010	+560
Power	3C x 2.5SQ	3,100	3,100	0

Cable schedule Rev.3 기준 물량 확정하여 내일 오전 중으로 회신 부탁드립니다.
회신 주시면 바로 자재 발주 진행하겠습니다.
또한 JB-105~JB-112 의 cable gland size (M20/M25) 확인 요청드립니다.

감사합니다.
노경호 드림
동명계장(주) 공사팀 | 010-5512-8830` });

H({ lang: 'en', style: 'nohdr', subj: '', from: '', date: '', time: '',
  r: [['SPIR', '2026-11-30'], ['commissioning spares', ''], ['capital spares', ''], ['native Excel', '']], s: [], items: ['Control Valve', 'On/Off Valve'], text:
`Dear Valve Vendors,

Reference is made to the Purchase Order requirements (Section 7.4 - Spare Parts).

Kindly submit the SPIR (Spare Parts Interchangeability Record) for all control valves and on/off valves by 30 November 2026, using the COMPANY SPIR template (Form F-SPIR-01 Rev.4).
Please also include the commissioning spares and 2-year operational spares in the same submission.
Note that capital spares (e.g. spare actuators, spare trim sets) are to be quoted separately as optional items.
It is required that the SPIR be submitted in native Excel format; PDF-only submissions will be returned with Code C.

Thank you for your cooperation.

Regards,
Procurement Team
Hangyeol E&C` });

H({ lang: 'ko', style: 'outlook_ko', subj: '[P-2533] Unit 300 계장 Punch List (Walkdown 결과) 조치 요청', from: '권혁준', date: '2026-11-27', time: '1710',
  r: [['Cat. A', '2026-12-04'], ['Cat. B', ''], ['사진', '']], s: [['2026-12-07', '1400']], items: ['Transmitter', 'Control Valve', 'Level', 'Cable/JB'], text:
`보낸 사람: 권혁준 과장 <hyukjun.kwon@hgenc.com>
보낸 날짜: 2026년 11월 27일 금요일 오후 5:10
받는 사람: 현장 계장팀 <site-ic@hgenc.com>; 동명계장 공사팀 <const@dongmyung-ic.co.kr>
참조: 정현우 책임 <hyunwoo.jung@hgenc.com>
제목: [P-2533] Unit 300 계장 Punch List (Walkdown 결과) 조치 요청

수고 많으십니다. 시운전팀 권혁준입니다.

금일 Unit 300 계장 walkdown 결과 Punch 항목 송부드립니다.

No.	Tag	내용	Cat.
P-031	PT-3105A	Impulse line slope 불량 (1/10 미만)	A
P-032	FCV-3110	Positioner air supply regulator 미설치	A
P-033	LT-3201	GWR probe 길이 부족 의심 - vendor 확인 필요	B
P-034	JB-305	Cable gland 미체결 3EA, IP 등급 미확보	A
P-035	TT-3301	Thermowell tag plate 누락	B

Cat. A 항목은 12/4(금)까지 조치 완료 요망합니다.
Cat. B 항목은 기계적 준공(MC) 전까지 조치 바랍니다.
조치 결과는 조치 전/후 사진 첨부하여 회신 바랍니다.

Punch 재점검(Walkdown)은 12/7(월) 14시, Unit 300 SRR 앞 집결입니다.

감사합니다.
권혁준 드림` });

H({ lang: 'en', style: 'outlook_en', subj: 'P-2503 YEOSU NCC #3 - DCS/SIS IFAT Schedule and Pre-requisites', from: 'David Chen', date: '2026-11-18', time: '1103',
  r: [['Cause & Effect', '2026-11-27'], ['marked-up graphics', '2026-11-25'], ['number of attendees', '']], s: [['2026-12-14', '0900']], items: ['DCS/SIS'], text:
`From: David Chen <david.chen@yokogawa.com>
Sent: Wednesday, November 18, 2026 11:03 AM
To: 정현우/책임/계장ENG그룹/한결E&C <hyunwoo.jung@hgenc.com>
Cc: Satoshi Yamamoto <satoshi.yamamoto@yokogawa.com>; 이서연 <seoyeon.lee@hgenc.com>
Subject: P-2503 YEOSU NCC #3 - DCS/SIS IFAT Schedule and Pre-requisites

Dear Mr. Jung,

Further to our discussion in last week's progress meeting, we would like to propose the Integrated FAT (IFAT) schedule as follows:

 - IFAT period : 14 - 18 December 2026 (Mon-Fri), 09:00-18:00 SGT
 - Location    : Yokogawa Engineering Asia, Singapore
 - Systems     : CENTUM VP (DCS), ProSafe-RS (SIS), Exaquantum, Compressor UCP via Modbus TCP

To keep this schedule, the following pre-requisites are required from your side:
 1. Please freeze the Cause & Effect diagrams and the I/O list by 27 November.
 2. Return the marked-up graphics (Round 2) by next Wednesday.
 3. Confirm the number of attendees from Hangyeol E&C and the end user, so that we can arrange the test room.

Kindly note that any I/O changes received after the freeze date will be handled as a change order.

Looking forward to your confirmation.

Best regards,
David Chen
Project Manager | Yokogawa Engineering Asia Pte. Ltd.
david.chen@yokogawa.com` });

H({ lang: 'mix', style: 'outlook_ko', subj: 'FW: PSV-7701 Set pressure change - recalculation request (Crosby JOS-E)', from: '서정민', date: '2026-11-17', time: '0852',
  r: [['PO 변경', '2026-11-20']], s: [], items: ['PSV'], text:
`보낸 사람: 서정민 책임 <jungmin.seo@hgenc.com>
보낸 날짜: 2026년 11월 17일 화요일 오전 8:52
받는 사람: 이윤아 과장 <yoona.lee@hgenc.com>
제목: FW: PSV-7701 Set pressure change - recalculation request (Crosby JOS-E)

이 과장님,

아래 메일 참고하세요.
공정팀에서 V-770 design pressure 변경 (18.5 → 21.0 barg) 에 따라 PSV-7701/7702 set pressure 가 변경되어, 업체(Crosby)에 orifice 재계산 요청해 두었습니다.
Orifice size 가 J → K 로 커지면 inlet/outlet flange rating 및 PO 금액 변경이 예상되니, 구매 쪽 PO 변경 필요 여부는 금주 중 알려 주세요.
공정 data sheet Rev.2 는 Aconex 에 올라가 있으니 참고 바랍니다.

서정민 드림

________________________________
From: 서정민 <jungmin.seo@hgenc.com>
Sent: Monday, November 16, 2026 6:20 PM
To: Ravi Shankar <ravi.shankar@emerson.com>
Subject: PSV-7701 Set pressure change - recalculation request (Crosby JOS-E)

Dear Ravi,

Due to the change of design pressure of V-770, the set pressure of PSV-7701/7702 is revised from 18.5 barg to 21.0 barg.
Please recalculate the required orifice area per API 520 Part I and submit the revised sizing calculation and datasheet by 20 Nov.

Best regards,
Jungmin Seo` });

H({ lang: 'en', style: 'gmail', subj: 'Re: Promass Q 300 (FT-1201/1202) - configuration sheet open points', from: 'Hans Mueller', date: '2026-11-16', time: '1021',
  r: [['totalizer units', ''], ['Modbus TCP', ''], ['this time works', '']], s: [['2026-11-19', '1600']], items: ['Flow Meter'], text:
`Re: Promass Q 300 (FT-1201/1202) - configuration sheet open points

Hans Mueller <hans.mueller@endress.com>
Mon, Nov 16, 2026, 10:21 AM
to me ▾

Hi Hyunwoo,

Thanks for sending the configuration sheet. Before we release the order to our Reinach factory, there are a few open points:

- Could you please advise the totalizer units for FT-1201/1202 (t or kg)?
- Please confirm whether the Modbus TCP option is required in addition to HART, as the I/O list only shows 4-20 mA/HART.
- Density calibration: the standard is +/-0.01 g/cc. Special density calibration (+/-0.0005 g/cc) is available at extra cost (EUR 1,850/unit).

We would like to propose a short Teams call this Thursday at 4 pm KST to go through the remaining items. Please let us know if this time works for you.

Cheers,
Hans

On Fri, Nov 13, 2026 at 5:02 PM 정현우 <hyunwoo.jung@hgenc.com> wrote:
> Dear Hans,
> Please find attached the configuration sheet for FT-1201/1202.
> Kindly confirm the delivery date by 20 Nov.
> Best regards, Hyunwoo` });

H({ lang: 'ko', style: 'knox', subj: '[성진밸브] P-2388 XV-2003 외 8대 On/Off Ball Valve 최종검사 입회 요청 (ITP Hold Point)', from: '손영수', date: '2026-11-18', time: '1315',
  r: [['입회 가능 여부', '2026-11-23'], ['revision 번호', '']], s: [['2026-11-26', '1000']], items: ['On/Off Valve'], text:
`제목 [성진밸브] P-2388 XV-2003 외 8대 On/Off Ball Valve 최종검사 입회 요청 (ITP Hold Point)
보낸 사람 손영수/차장/품질팀/성진밸브(주) <youngsu.son@sjvalve.co.kr>
받는 사람 문지원/과장/품질검사팀/한결E&C <jiwon.moon@hgenc.com>
참조 정현우/책임/계장ENG그룹/한결E&C <hyunwoo.jung@hgenc.com>
보낸 날짜 2026-11-18 (수) 오후 1:15

한결E&C 품질검사팀 문지원 과장님 / 계장ENG그룹 정현우 책임님,

안녕하십니까, 성진밸브 품질팀 손영수 차장입니다.
P-2388 BORA PP/PE 프로젝트 On/Off Ball Valve (XV-2003, XV-2004, XV-2010~XV-2016, 총 9대) 제작이 완료되어, 승인된 ITP (SJV-ITP-2388-01 Rev.2) Hold Point 에 따른 최종검사 입회를 요청드립니다.

 1. 일시 : 2026년 11월 26일(목) 오전 10시
 2. 장소 : 경남 김해시 주촌면 골든루트로 80-16, 성진밸브 제2공장
 3. 검사 항목 : Visual/Dimension, Hydrostatic shell test, Seat leak test (API 598), Fire-safe 인증서 확인, Actuator(Bettis) stroke time (2초 이내), Limit switch 동작 확인
 4. 입회 기관 : 발주처 TPI (Lloyd's Register) 포함

입회 가능 여부를 11/23(월)까지 회신 부탁드립니다.
아울러 검사 당일 지참하실 승인 도면(GA drawing) 최신 revision 번호도 알려 주시면 감사하겠습니다.

감사합니다.
손영수 드림` });

H({ lang: 'en', style: 'outlook_en', subj: 'Payment Reminder - Invoice No. 9001234 / PO 4500187763 (Valtek Control Valves) - OVERDUE', from: 'Sophie Martin', date: '2026-11-05', time: '0915',
  r: [['arrange payment', ''], ['expected payment date', '']], s: [], items: ['Control Valve'], text:
`From: Sophie Martin <sophie.martin@flowserve.com>
Sent: Thursday, November 5, 2026 9:15 AM
To: AP Team <ap@hgenc.com>
Cc: 박기훈 <kihoon.park@hgenc.com>
Subject: Payment Reminder - Invoice No. 9001234 / PO 4500187763 (Valtek Control Valves) - OVERDUE

Dear Sir/Madam,

This is a friendly reminder that the following invoice is now overdue:

Invoice No.    Invoice Date    Amount (USD)    Due Date       Days Overdue
9001234        31-Aug-2026     128,400.00      30-Oct-2026    6

Kindly arrange payment of the above invoice at your earliest convenience.
If payment has already been made, please disregard this reminder.
Please also advise the expected payment date by return email.

Our bank details remain unchanged (see attached).
Thank you for your continued business.

Kind regards,
Sophie Martin
Credit & Collections | Flowserve Corporation
sophie.martin@flowserve.com` });

H({ lang: 'ko', style: 'outlook_ko', subj: '[P-2521] Vendor Document Return - Transmittal No. HG-P2521-VTR-0388 (KROHNE / VEGA)', from: '윤재희', date: '2026-10-14', time: '1620',
  r: [['재제출', '2026-10-28'], ['다음 revision', '']], s: [], items: ['Flow Meter', 'Level'], text:
`보낸 사람: DCC 윤재희 <jaehee.yoon@hgenc.com>
보낸 날짜: 2026년 10월 14일 수요일 오후 4:20
받는 사람: 크로네코리아 <project.kr@krohne.com>; 베가코리아 <kr.project@vega.com>
참조: 계장ENG그룹 정현우 책임 <hyunwoo.jung@hgenc.com>
제목: [P-2521] Vendor Document Return - Transmittal No. HG-P2521-VTR-0388 (KROHNE / VEGA)

안녕하십니까, 한결E&C P-2521 DCC 입니다.

제출하신 Vendor Document 에 대한 검토 결과를 아래와 같이 회신드립니다.

Doc. No.                    Title                                   Rev.   Code
P2521-KRO-IC-DS-0003        Electromagnetic Flowmeter Datasheet      B      1
P2521-KRO-IC-CAL-0004       Flowmeter Sizing Calculation             A      2
P2521-KRO-IC-DWG-0005       Dimensional Drawing (OPTIFLUX 4100)      A      3
P2521-VEG-IC-DS-0011        Radar Level Transmitter Datasheet        A      2
P2521-VEG-IC-DWG-0012       Flange & Antenna Arrangement             A      3

※ Code 1: Approved / Code 2: Approved with comments / Code 3: Rejected, revise and resubmit

Code 3 문서는 코멘트 반영하여 2주 이내 재제출 바랍니다.
Code 2 문서는 코멘트 내용을 다음 revision 에 반영 바랍니다.
코멘트 원본은 Aconex 에서 확인 가능합니다.

감사합니다.
DCC 윤재희 드림` });

H({ lang: 'en', style: 'notes', subj: 'Quotation for Process GC (MAXUM edition II) - AT-901/902 - Ref. SIE-Q-26-11871', from: 'Stefan Weber', date: '2026-10-22', time: '1405',
  r: [], s: [], items: ['Analyzer'], text:
`From: Stefan Weber/SIEMENS@SIEMENS
Date: 2026/10/22 14:05
To: 박기훈/구매팀/한결E&C <kihoon.park@hgenc.com>
cc: 정현우/계장ENG그룹/한결E&C <hyunwoo.jung@hgenc.com>
Subject: Quotation for Process GC (MAXUM edition II) - AT-901/902 - Ref. SIE-Q-26-11871

Dear Mr. Park,

Thank you for your enquiry.
Please find attached our techno-commercial offer for 2 sets of MAXUM edition II process gas chromatographs including sample conditioning systems.

Main points:
 - Measuring components: H2, CH4, C2H6, C2H4 (AT-901) / CO, CO2 (AT-902)
 - Analysis cycle time: < 6 minutes
 - Sample system: heated, mounted on SS316 panel, ATEX/IECEx Zone 1
 - Delivery: 22 weeks after PO and approval of drawings

Please note that the price is valid until 31 December 2026 and is based on EXW Karlsruhe.
Should you require any clarification, please do not hesitate to contact us.

Best regards
Stefan Weber
Technical Sales Manager | Process Analytics
Siemens AG` });

H({ lang: 'mix', style: 'gmail', subj: 'Rosemount 5408 radar (LT-210) still pipe 관련 확인 요청', from: '김태호', date: '2026-11-19', time: '1512',
  r: [['still pipe', ''], ['PO 진행 일정', '']], s: [], items: ['Level'], text:
`Rosemount 5408 radar (LT-210) still pipe 관련 확인 요청

김태호 <taeho.kim@emerson.com>
Thu, Nov 19, 2026, 3:12 PM
to me ▾

안녕하세요 책임님, 한국에머슨 김태호입니다.

Rosemount 5408 non-contacting radar LT-210 관련해서 still pipe 필요 여부 확인 부탁드립니다.
Agitator 가 있는 tank (TK-210) 라서 blade 에 의한 false echo 우려가 있고, 저희 쪽 recommendation 은 4" still pipe 입니다.
Nozzle 은 6" CL150 으로 data sheet 상 확인했습니다.

그리고 quotation validity 가 11/30 까지라 PO 진행 일정 알려주시면 감사하겠습니다.

Thanks,
김태호 과장 / Emerson Automation Solutions Korea
M. 010-3382-1170` });

H({ lang: 'en', style: 'outlook_en', subj: '[P-2490] Kick-off Meeting - Fire & Gas System (Honeywell) - 2 Dec 2026', from: '한상철', date: '2026-11-24', time: '1645',
  r: [['agenda items', '2026-11-30'], ['confirm your attendance', '']], s: [['2026-12-02', '1400']], items: ['F&G'], text:
`From: 한상철 부장 <sangchul.han@hgenc.com>
Sent: Tuesday, November 24, 2026 4:45 PM
To: Jessica Wong <jessica.wong@honeywell.com>; Michael O'Brien <michael.obrien@honeywell.com>
Cc: 정현우 <hyunwoo.jung@hgenc.com>; 이서연 <seoyeon.lee@hgenc.com>; 박기훈 <kihoon.park@hgenc.com>
Subject: [P-2490] Kick-off Meeting - Fire & Gas System (Honeywell) - 2 Dec 2026

Dear Jessica,

With reference to PO 4500241190 for the Fire & Gas System (Safety Manager SC, flame/gas detectors and F&G mimic panel), we would like to hold the kick-off meeting as follows.

When: Wednesday, December 2, 2026 2:00 PM-4:00 PM (UTC+09:00) Seoul
Where: Hangyeol Tower 9F, Meeting Room 3 / Microsoft Teams (hybrid)

Agenda (draft):
 1. Project overview and organization
 2. Scope of supply & battery limits (F&G cabinets, GD/FD/HD, beacons & sounders)
 3. Document schedule (VDRL) and numbering
 4. Detector mapping study methodology
 5. FAT / SAT plan

Please submit your additional agenda items and your project organization chart by Monday, 30 November.
Please confirm your attendance and the names of participants.

________________________________________________________________________________
Microsoft Teams meeting
Join on your computer, mobile app or room device
Click here to join the meeting
Meeting ID: 412 778 903 15
Passcode: ab3Cd9
________________________________________________________________________________

Best regards,
Sang-chul Han
General Manager | I&C Engineering Group
Hangyeol E&C` });

H({ lang: 'ko', style: 'knox', subj: '[P-2602] Instrument Hook-up Drawing IFC 발행 알림 (Rev.0, 42매)', from: '이서연', date: '2026-10-30', time: '1802',
  r: [], s: [], items: ['Transmitter'], text:
`[P-2602] Instrument Hook-up Drawing IFC 발행 알림 (Rev.0, 42매)
보낸 사람 이서연/선임/계장ENG그룹/한결E&C <seoyeon.lee@hgenc.com>
보낸 날짜 2026-10-30 (금) 오후 6:02
받는 사람 P2602 계장 TFT <p2602-ic@hgenc.com>
참조 배관설계팀 <piping@hgenc.com>; 현장 계장팀 <site-ic@hgenc.com>

안녕하세요, 이서연입니다.

P-2602 Instrument Hook-up Drawing (Process / Pneumatic / Mounting) 42매를 금일 IFC Rev.0 로 발행하였습니다.
주요 변경 사항은 아래와 같습니다.

  1) PT/DPT impulse line: 3/4" → 1/2" OD tube 로 변경 (Piping class 변경 반영)
  2) 2-valve / 5-valve manifold typical 분리
  3) H2 service tag (PT-4105, PT-4106) 는 double block & bleed 적용

도면은 EDMS 에 업로드되어 있으니 참고 바랍니다.
현장 배포본은 다음 주 중 출력하여 송부드리겠습니다.

감사합니다.
이서연 드림

본 메일은 한결E&C의 영업비밀 및 기밀정보를 포함하고 있을 수 있으며, 수신인 이외의 자가 열람·복사·배포하는 것을 금합니다.` });

H({ lang: 'en', style: 'gmail', subj: 'Site visit to fabrication yard - Analyzer Shelters (P-2521)', from: 'Omar Haddad', date: '2026-11-25', time: '0940',
  r: [['safety induction', ''], ['S-curve', '']], s: [['2026-12-08', '1000']], items: ['Analyzer'], text:
`Site visit to fabrication yard - Analyzer Shelters (P-2521)

Omar Haddad <o.haddad@kasco-energy.com>
Wed, Nov 25, 2026 at 9:40 AM
to me, 박기훈 ▾

Dear Mr. Jung,

COMPANY representatives (4 persons) plan to visit the analyzer shelter fabrication yard of your subcontractor (Samwoo E&I, Changwon) on Tuesday, 8th December at 10:00 AM to review the progress of AH-901/902.

Please arrange the safety induction and PPE for 4 persons at the yard.
Kindly share the latest progress S-curve and the photo report before the visit.

We will arrive by car from Busan; no pick-up is required.

Regards,
Omar Haddad
Instrument Engineer, KASCO Energy` });

H({ lang: 'ko', style: 'knox_ocr', subj: '[긴급] MOV-5101~5146 Rotork 전원 사양 변경 확인 요청', from: '조성민', date: '2026-11-19', time: '1142',
  r: [['전원 사양', '2026-11-19']], s: [['2026-11-20', '1400']], items: ['MOV'], text:
`← 받은메일함   ☆   ⋮
[긴급] MOV-5101~5146 Rotork 전원 사양 변경 확인 요청
보낸사람 조성민/과장/전기ENG그룹/한결E&C ‹sungmin.cho@hgenc.com›
받는사람 정현우/책임/계장ENG그룹/한결E&C ‹hyunwoo.jung@hgenc.com›
보낸 날짜 2026-11-19 (목) 오전 11:42
□ 첨부파일 1개 (412KB)

정 책임님,
전기팀 조성민입니다.

발주처 최종 협의 결과 MCC 전원이 380V 3상 60Hz → 400V 3상 50Hz 로 최종 확정되었습니다.
Rotork IQ3 Pro 전원 사양 변경 가능한지 오늘 중으로 업체 확인 부탁드립니다.
FAT 전이라 아직 반영 가능할 것으로 보입니다.

내일 오후 2시에 전기팀/계장팀 interface 회의 잡혀 있으니 그 자리에서 결과 공유해 주시면 됩니다.

조성민 드림` });

H({ lang: 'en', style: 'outlook_en', subj: 'Change Order No. 3 - Low Noise Trim for FCV-1104/1107 - Masoneilan Ref. BHQ-26-0412 Rev.1', from: 'Rajesh Kumar', date: '2026-11-30', time: '1410',
  r: [['PO amendment', '2026-12-10'], ['revised delivery', '']], s: [], items: ['Control Valve'], text:
`From: Rajesh Kumar <rajesh.kumar@bakerhughes.com>
Sent: Monday, November 30, 2026 2:10 PM
To: 박기훈 <kihoon.park@hgenc.com>
Cc: 정현우 <hyunwoo.jung@hgenc.com>
Subject: Change Order No. 3 - Low Noise Trim for FCV-1104/1107 - Masoneilan Ref. BHQ-26-0412 Rev.1

Dear Mr. Park,

Further to your request, we are pleased to submit our quotation for the subject change.

Item  Tag        Description                                 Qty  Unit Price (USD)
1     FCV-1104   Lo-dB cage trim + body modification (8")    1    18,650
2     FCV-1107   Lo-dB cage trim + body modification (6")    1    14,200
3     -          Revised sizing/noise calc & documentation   1    1,500
                                                            Total: USD 34,350

Predicted noise level with Lo-dB trim: 82 dBA (FCV-1104) / 81 dBA (FCV-1107) at 1 m.
Price validity: 60 days. Delivery impact: +4 weeks for the two tags only.

Please issue the PO amendment by 10 December to keep the delivery of the remaining valves unchanged.
Kindly confirm your acceptance of the revised delivery (+4 weeks) for FCV-1104/1107.

We trust the above meets your requirements.

Best regards,
Rajesh Kumar
Sales Engineer | Masoneilan
Baker Hughes` });

H({ lang: 'ko', style: 'outlook_ko', subj: '[P-2455] HAZOP Action Item 회신 요청 (계장 해당분 7건)', from: '조성민', date: '2026-11-23', time: '0930',
  r: [['Action response', '2026-12-03']], s: [['2026-12-10', '1330']], items: ['DCS/SIS', 'PSV', 'Level'], text:
`보낸 사람: 조성민 과장 (공정설계팀) <sm.cho@hgenc.com>
보낸 날짜: 2026년 11월 23일 월요일 오전 9:30
받는 사람: 정현우 책임 <hyunwoo.jung@hgenc.com>; 이서연 선임 <seoyeon.lee@hgenc.com>
참조: 한상철 부장 <sangchul.han@hgenc.com>
제목: [P-2455] HAZOP Action Item 회신 요청 (계장 해당분 7건)

계장 담당자님들께,

지난주 완료된 HAZOP 에서 도출된 Action Item 중 계장 해당분 7건 공유드립니다.

No.     Node    Action                                                       담당
H-012   N-03    V-1101 LSHH 추가 및 SIS trip 연동 검토                        정현우
H-015   N-03    PSV-1105 relief load (fire case) 재검토                       이서연
H-021   N-05    FCV-1203 fail position 재확인 (FC → FL 검토)                  정현우
H-022   N-05    Low flow alarm FAL-1204 setpoint 근거 제시                    이서연
H-030   N-07    XV-1301 closing time 재산정 (surge 해석 결과 반영)            정현우
H-033   N-08    LT-1402 / LT-1403 독립성 확보 (별도 tapping)                  이서연
H-041   N-09    Analyzer AT-1501 고장 시 대응 절차 운전매뉴얼 반영             정현우

각 담당자는 12월 3일(목)까지 HAZOP Action response 작성 바랍니다 (양식: HAZOP-AR-01).
HAZOP close-out meeting 은 12/10(목) 오후 1시 30분, 본사 7층 대회의실에서 진행합니다.

감사합니다.
조성민 드림` });

H({ lang: 'en', style: 'gmail', subj: 'Aconex: Transmittal HGENC-TRN-004512 received - Orifice Plate & Flow Element Sizing Calculation', from: 'Aconex', date: '2026-11-18', time: '2359',
  r: [], s: [], items: ['Flow Meter'], text:
`Aconex: Transmittal HGENC-TRN-004512 received - Orifice Plate & Flow Element Sizing Calculation

Aconex <noreply@aconex.com>
Nov 18, 2026, 11:59 PM
to me ▾

You have received a new transmittal.

Project:        P-2503 YEOSU NCC #3
Transmittal No: HGENC-TRN-004512
From:           Lim Boon Keat (Emerson Automation Solutions)
Reason:         For Review
Documents:      P2503-EMR-IC-CAL-0021 Rev.B  Orifice Plate & Flow Element Sizing Calculation (FE-1201 ~ FE-1218)
                P2503-EMR-IC-DS-0022 Rev.B   Flow Element Datasheet
Date sent:      18-Nov-2026

To view the transmittal, log in to Aconex.

This is an automated message. Please do not reply to this email.` });

H({ lang: 'mix', style: 'knox', subj: '[P-2490] F&G Detector Mapping Study 결과 공유 및 추가 Detector 배치 검토 요청 / Request for review of additional detectors', from: '이서연', date: '2026-11-24', time: '1500',
  r: [['추가 detector', '2026-12-01'], ['additional detectors', '2026-12-01']], s: [], items: ['F&G'], text:
`[P-2490] F&G Detector Mapping Study 결과 공유 및 추가 Detector 배치 검토 요청 / Request for review of additional detectors
보낸 사람 이서연/선임/계장ENG그룹/한결E&C <seoyeon.lee@hgenc.com>
받는 사람 Jessica Wong <jessica.wong@honeywell.com>, 김도윤/차장/프로젝트팀/한국하니웰 <doyoon.kim@honeywell.com>
보낸 날짜 2026-11-24 (화) 오후 3:00

(English follows Korean)

김도윤 차장님,

F&G detector mapping study (Detect3D) 결과, Compressor shelter (Area 400) 의 gas detection coverage 가 목표치 90% 대비 81% 로 미달되었습니다.
GD-1241 ~ GD-1244 추가 detector 배치안을 첨부와 같이 송부드리니, 12/1(화)까지 추가 detector 배치안 검토 의견 부탁드립니다.

Dear Jessica,

According to the detector mapping study (Detect3D), the gas detection coverage of the compressor shelter (Area 400) is 81% against the target of 90%.
Please review the attached layout of additional detectors GD-1241 ~ GD-1244 and send us your comments by 1 Dec 2026.

Best regards,
Seoyeon Lee / 이서연 선임
I&C Engineering Group | Hangyeol E&C` });

H({ lang: 'en', style: 'outlook_en', subj: 'URGENT: Missing calibration certificates - TT-4501~4520 (Shipment No. 3)', from: 'Kim Do-yoon', date: '2026-12-03', time: '1320',
  r: [['calibration certificates', '2026-12-03'], ['HART tag', '']], s: [['2026-12-04', '1000']], items: ['Transmitter'], text:
`From: Kim Do-yoon <doyoon.kim@hgenc.com>
Sent: Thursday, December 3, 2026 1:20 PM
To: Arjun Patel <arjun.patel@abb.com>
Cc: Site Material Control <site-mc@hgenc.com>
Subject: URGENT: Missing calibration certificates - TT-4501~4520 (Shipment No. 3)

Dear Arjun,

Shipment No. 3 (temperature transmitters TT-4501 ~ TT-4520, ABB TTF300) arrived at site this morning. However, the calibration certificates are missing from the MDR and from the packing.

Please send the calibration certificates by EOD today, since the site receiving inspection is scheduled tomorrow at 10:00 with the COMPANY QC.
Also, please confirm the HART tag configured in each transmitter, as the tags on the stainless steel tag plates are not legible on 3 units.

Thanks,
Do-yoon Kim
Site Material Control | Hangyeol E&C` });

H({ lang: 'ko', style: 'gmail', subj: '[대성계전] P-2602 Junction Box 제작도면 승인 요청 (JB-401~JB-436)', from: '하종혁', date: '2026-11-10', time: '1405',
  r: [['제작도면 승인', '2026-11-13'], ['명판', '']], s: [], items: ['Cable/JB'], text:
`[대성계전] P-2602 Junction Box 제작도면 승인 요청 (JB-401~JB-436)

하종혁 <jonghyuk.ha@dsgj.co.kr>
2026. 11. 10. 오후 2:05
나에게 ▼

정현우 책임님 안녕하세요.
대성계전 설계팀 하종혁 과장입니다.

P-2602 Junction Box 36면 (JB-401~JB-436, Exe IIC T6, SS316L) 제작도면 송부드립니다.
Terminal 은 Phoenix Contact UT 2.5 로 반영하였고, spare terminal 20% 확보하였습니다.

자재 입고 일정상 이번 주 금요일까지 제작도면 승인 회신 부탁드립니다.
아울러 명판(Nameplate) 문구 (영문/국문 병기 여부) 확정 부탁드립니다.

감사합니다.
하종혁 드림
대성계전(주) 설계팀 | T. 031-8041-2270` });

H({ lang: 'en', style: 'nohdr', subj: '', from: '', date: '', time: '',
  r: [['arrange the forwarder', ''], ['shipping marks', '']], s: [['2026-12-07', '']], items: ['Flow Meter'], text:
`Dear Sir,

We are pleased to inform you that the shipment for PO 4500239902 (OPTIFLUX 4300 electromagnetic flowmeters FT-2101 ~ FT-2126 and OPTIMASS 6400 Coriolis meters FT-2201 ~ FT-2204) is ready.

   Packing list No. : KR-PL-26-3317
   No. of crates    : 12 (gross weight 4,820 kg)
   Ready for pick-up: 7 December 2026, KROHNE warehouse Duisburg

Please arrange the forwarder and advise the booking details.
Kindly also send us the shipping marks to be stencilled on the crates.

The final documentation (MDR) will be uploaded to Aconex together with the shipment release.

Best regards,
KROHNE Messtechnik GmbH
Order Processing` });

H({ lang: 'ko', style: 'outlook_ko', subj: 'RE: P-2455 Rotork IQ3 Pro FAT 지원 감사드립니다', from: '강기훈', date: '2026-12-04', time: '0840',
  r: [], s: [], items: ['MOV'], text:
`보낸 사람: 강기훈 대리 <kihoon.kang@hgenc.com>
보낸 날짜: 2026년 12월 4일 금요일 오전 8:40
받는 사람: 장윤아 과장 <yoona.jang@rotork.com>
참조: Anil Menon <anil.menon@rotork.com>; 정현우 책임 <hyunwoo.jung@hgenc.com>
제목: RE: P-2455 Rotork IQ3 Pro FAT 지원 감사드립니다

장윤아 과장님,

어제 첸나이 공장 FAT 기간 동안 세심하게 지원해 주셔서 감사합니다.
46대 전량 torque test 및 Profibus 통신 시험 이상 없이 완료되어 다행입니다.

FAT report 는 저희가 TPI 코멘트와 함께 정리하여 다음 주 중 공유드리겠습니다.
출하 관련해서는 구매팀에서 별도로 연락드릴 예정입니다.

다시 한 번 감사드리며, 한국 들어오시면 식사 한번 하시죠.

강기훈 드림` });

H({ lang: 'en', style: 'outlook_en', subj: 'RE: RE: FCV-1104/1107 Noise calculation (Lo-dB trim) - revised calc required', from: '정현우', date: '2026-11-25', time: '1755',
  r: [['noise calculation', '2026-11-26']], s: [], items: ['Control Valve'], text:
`From: 정현우/책임/계장ENG그룹/한결E&C <hyunwoo.jung@hgenc.com>
Sent: Wednesday, November 25, 2026 5:55 PM
To: Rajesh Kumar <rajesh.kumar@bakerhughes.com>
Cc: 박기훈 <kihoon.park@hgenc.com>
Subject: RE: RE: FCV-1104/1107 Noise calculation (Lo-dB trim) - revised calc required

Hi Rajesh,

Gentle reminder on the below. We still haven't received the revised noise calculation.
Please send it by tomorrow noon at the latest, as we have to forward it to the client.

Hyunwoo

-----Original Message-----
From: Rajesh Kumar <rajesh.kumar@bakerhughes.com>
Sent: Friday, November 20, 2026 11:02 AM
To: 정현우 <hyunwoo.jung@hgenc.com>
Subject: RE: FCV-1104/1107 Noise calculation (Lo-dB trim) - revised calc required

Dear Mr. Jung,

Noted. We will send the revised calculation by Monday next week.
Could you please confirm the downstream pipe schedule (SCH 40 or SCH 80) for both tags?

Regards,
Rajesh

-----Original Message-----
From: 정현우 <hyunwoo.jung@hgenc.com>
Sent: Thursday, November 19, 2026 4:30 PM
To: Rajesh Kumar <rajesh.kumar@bakerhughes.com>
Subject: FCV-1104/1107 Noise calculation (Lo-dB trim) - revised calc required

Dear Rajesh,

Please submit the revised noise calculation (IEC 60534-8-3) with Lo-dB trim by 23 Nov 2026.

Best regards,
Hyunwoo Jung` });

H({ lang: 'ko', style: 'knox', subj: '[출장] P-2455 Rotork IQ3 Pro FAT 입회 출장 일정 공유 (12/1~12/5, 인도 첸나이)', from: '강기훈', date: '2026-11-20', time: '1010',
  r: [['항공권 발권', '2026-11-25']], s: [['2026-12-01', ''], ['2026-12-03', '0930']], items: ['MOV'], text:
`[출장] P-2455 Rotork IQ3 Pro FAT 입회 출장 일정 공유 (12/1~12/5, 인도 첸나이)
보낸 사람 강기훈/대리/구매팀/한결E&C <kihoon.kang@hgenc.com>
받는 사람 공무팀 <pc-team@hgenc.com>
참조 정현우/책임/계장ENG그룹/한결E&C <hyunwoo.jung@hgenc.com>
보낸 날짜 2026-11-20 (금) 오전 10:10

공무팀 담당자님,

Rotork IQ3 Pro actuator FAT 입회를 위한 출장 일정 공유드립니다.

  - 출장자 : 정현우 책임, 강기훈 대리
  - 기간 : 2026.12.01(화) ~ 12.05(토), 4박 5일
  - 행선지 : 인도 첸나이 (Rotork Controls India)
  - FAT 일시 : 12/3(목) 09:30 (IST)

항공권 발권 진행 부탁드립니다 (11/25까지).
비자는 개별로 e-Visa 신청 완료하였으며, 출장비 정산 서류는 복귀 후 제출하겠습니다.

감사합니다.
강기훈 드림` });

H({ lang: 'en', style: 'gmail', subj: 'Re: VEGAPULS 6X (LT-3101~3108) - revised GA drawings', from: 'Pieter de Vries', date: '2026-11-17', time: '0715',
  r: [], s: [], items: ['Level'], text:
`Re: VEGAPULS 6X (LT-3101~3108) - revised GA drawings

Pieter de Vries <pieter.devries@vega.com>
Tue, Nov 17, 2026, 7:15 AM
to me ▾

Dear Ms. Lee,

Please find attached the revised GA drawings for LT-3101 ~ LT-3108 (VEGAPULS 6X, 80 GHz) incorporating your comments on the flange rating (CL300 RF) and the antenna extension length.

The updated datasheets and the SIL declaration of conformity will be sent to you by Friday.
Please note that the delivery date remains unchanged (week 2/2027).

Best regards,
Pieter de Vries
Project Engineer | VEGA Grieshaber KG

On Mon, Nov 16, 2026 at 3:44 PM 이서연 <seoyeon.lee@hgenc.com> wrote:
> Dear Pieter,
> Please revise the GA drawings per our comments (Code 2) and resubmit by 18 Nov.
> Also please submit the SIL declaration for LT-3105/3106.
> Regards, Seoyeon` });

H({ lang: 'mix', style: 'outlook_en', subj: 'Loop Diagram Rev.B comments - Yokogawa CENTUM VP / IS barrier wiring (P-2503)', from: '정현우', date: '2026-11-19', time: '1840',
  r: [['resubmit', '2026-11-23'], ['IS barrier', '']], s: [], items: ['DCS/SIS', 'Cable/JB'], text:
`From: 정현우 <hyunwoo.jung@hgenc.com>
Sent: Thursday, November 19, 2026 6:40 PM
To: 김영수 <youngsu.kim@yokogawa.com>
Cc: David Chen <david.chen@yokogawa.com>; 이서연 <seoyeon.lee@hgenc.com>
Subject: Loop Diagram Rev.B comments - Yokogawa CENTUM VP / IS barrier wiring (P-2503)

김 부장님, 안녕하세요.

Loop diagram Rev.B 관련 comments 첨부 드립니다. (총 63 sheets, comment 112건)
Please revise and resubmit by next Monday.
특히 IS barrier (MTL 4500) wiring 부분 terminal 번호가 marshalling cabinet drawing 과 안 맞는 부분이 많으니 IS barrier 쪽 확인 부탁드립니다.

David, FYI - most comments are on the marshalling terminal numbers, not on the DCS side.

Thanks,
Hyunwoo` });

H({ lang: 'ko', style: 'nohdr', subj: '', from: '', date: '', time: '',
  r: [['Cv 계산 결과', '']], s: [['2026-11-20', '1500']], items: ['Control Valve'], text:
`다들 수고 많으십니다.

Control valve sizing review 는 2026년 11월 20일(금) 오후 3시에 Teams 로 진행하겠습니다.
각자 맡은 Tag 의 Cv 계산 결과 (Max/Normal/Min, 개도율 포함) 가져와 주세요.
Noise 85 dBA 초과 Tag 는 따로 정리해 두었으니 회의 때 같이 보겠습니다.

정현우` });

// =====================================================================================
// GENERATOR VOCABULARY.  Placeholders: {T} tag, {T2} 2nd tag, {N} count, {R} rev, {C} return code,
// {V} vendor brand, {P} project code, {PN} project name, {DOC} doc no., {PO} PO no., {Q} qty
// req   : [koNoun, koVerb, enNoun, enVerb]   (kw = the noun)
// li    : imperative list items [ko, en, kwKo, kwEn]
// inf   : informational list lines [ko, en] (NOT requests)
// =====================================================================================
const TAGPRE = {
  'Control Valve': ['FCV', 'PCV', 'LCV', 'TCV', 'FV', 'PV', 'LV'], 'On/Off Valve': ['XV', 'SDV', 'BDV', 'XV'], PSV: ['PSV', 'PSV', 'PRV'], MOV: ['MOV'],
  'Flow Meter': ['FT', 'FE', 'FIT', 'FT'], Transmitter: ['PT', 'TT', 'DPT', 'PIT', 'TIT', 'PT'], Level: ['LT', 'LIT', 'LT'], Analyzer: ['AT', 'AIT', 'AT'],
  'DCS/SIS': ['SIF', 'UZ', 'HS'], 'F&G': ['GD', 'FD', 'GD', 'HD'], 'Cable/JB': ['JB', 'JB', 'MC'], Pump: ['P'],
};
function mkTag(cat) { const p = pick(TAGPRE[cat] || ['PT']); if (p === 'P') return `P-${ri(1, 7)}${ri(1, 4)}0${ri(1, 9)}${pick(['A', 'B', 'A/B'])}`; if (p === 'SIF') return `SIF-${ri(1, 6)}${pad(ri(1, 40))}`; return `${p}-${ri(1, 7)}${ri(1, 5)}${pad(ri(1, 40))}${chance(0.15) ? pick(['A', 'B', 'C']) : ''}`; }
const TOPICS = [];
function T(key, cats, w, o) { TOPICS.push(Object.assign({ key, cats, w }, o)); }

T('cv_ds', ['Control Valve'], 4, {
  sKo: ['[{P}] {T} 외 {N}건 Control Valve Datasheet 검토 의견 송부 (Code {C})', '{T} Control Valve 데이터시트 Rev.{R} 검토 코멘트', '[{P}] {V} Control Valve Datasheet 코멘트 회신'],
  sEn: ['[{P}] Control Valve Datasheet Review Comments - {T} and {N} others (Code {C})', 'Comments on {V} Control Valve Datasheet Rev.{R} ({T})', '{P} | {V} control valve datasheets - review status'],
  cKo: ['제출해 주신 {V} Control Valve Datasheet ({DOC} Rev.{R}) 검토 결과 Code {C}로 회신드립니다.', '{T} 외 {N}건 Control Valve Datasheet 를 공정 Data 와 비교 검토하였습니다.', '지난번 제출된 Datasheet 중 {T} 는 공정 조건 변경(Max flow 증가)이 반영되지 않았습니다.'],
  cEn: ['We have reviewed your Control Valve Datasheets ({DOC} Rev.{R}) and return them with Code {C}.', 'Our review of the datasheets for {T} and {N} other tags against the latest process data is complete.', 'The datasheet for {T} does not reflect the latest process conditions (increased max. flow).'],
  req: [['수정 Datasheet', '재제출', 'revised datasheets', 'resubmit'], ['Cv 계산서', '송부', 'Cv calculation', 'submit'], ['Comment Resolution Sheet', '작성', 'comment resolution sheet', 'complete'], ['Datasheet Rev.{R}', '회신', 'Rev.{R} datasheets', 'return']],
  li: [['{T}: Body material 을 A351 CF8M 으로 변경 바랍니다.', '{T}: Change the body material to A351 CF8M.', 'CF8M', 'CF8M'],
    ['Seat leakage class 를 ANSI/FCI 70-2 Class V 로 수정 바랍니다.', 'Revise the seat leakage class to ANSI/FCI 70-2 Class V.', 'Class V', 'Class V'],
    ['{T2}: Fail action (FC/FO) 을 P&ID 와 일치하도록 확인 요망.', '{T2}: Please check the fail action (FC/FO) against the P&ID.', 'Fail action', 'fail action'],
    ['Positioner 통신 사양을 HART 7 로 통일 바랍니다.', 'Align the positioner protocol to HART 7 for all tags.', 'HART 7', 'HART 7'],
    ['Handwheel 적용 여부를 Tag 별로 표기해 주십시오.', 'Indicate handwheel requirement per tag.', 'Handwheel', 'handwheel'],
    ['Travel stop 설정값을 Datasheet 에 추가 바랍니다.', 'Add the travel stop setting to the datasheet.', 'Travel stop', 'travel stop'],
    ['End connection 을 RF → RTJ 로 수정 필요합니다.', 'End connection shall be revised from RF to RTJ.', 'RTJ', 'RTJ']],
  inf: [['{T}: 계산 noise 83 dBA (허용치 85 dBA 이내)', '{T}: predicted noise 83 dBA (within 85 dBA)'], ['Body/Bonnet: A216 WCB / A216 WCB', 'Body/Bonnet: A216 WCB / A216 WCB'], ['Actuator: Spring diaphragm, Fail Close', 'Actuator: spring-diaphragm, fail close'], ['Rated Cv 145 / Required Cv 98 (개도율 72%)', 'Rated Cv 145 / required Cv 98 (72% open)']],
  ev: ['meeting', 'teams'],
});
T('cv_sizing', ['Control Valve'], 3, {
  sKo: ['{T} Control Valve Sizing / Noise 계산 재검토 요청', '[{P}] Control Valve Sizing Calculation Rev.{R} 검토', 'RE: {T} 개도율 및 Noise 계산 관련'],
  sEn: ['{T} control valve sizing & noise calculation - review', 'Request for revised sizing calculation - {T}', '[{P}] Valve sizing - rangeability issue on {T}'],
  cKo: ['{T} 의 Min flow 조건에서 개도율이 8% 로 계산되어 controllability 에 문제가 있어 보입니다.', 'Noise 계산 결과 {T} 가 88 dBA 로 Spec. 한계(85 dBA)를 초과합니다.', '공정 Data Rev.{R} 반영으로 Max flow 가 15% 증가했습니다.'],
  cEn: ['At minimum flow the calculated opening of {T} is only 8%, which raises a controllability concern.', 'The noise prediction for {T} is 88 dBA, exceeding the 85 dBA limit of the project specification.', 'Process data Rev.{R} increased the maximum flow by 15%.'],
  req: [['Sizing 계산서', '재제출', 'revised sizing calculation', 'submit'], ['Noise 계산서', '제출', 'noise calculation', 'provide'], ['Low-noise trim 적용 가능 여부', '검토', 'low-noise trim option', 'review'], ['Valve size 변경안', '회신', 'proposal for the valve size change', 'send']],
  li: [['Min/Normal/Max 조건별 개도율을 표기 바랍니다.', 'Show the valve opening at min/normal/max conditions.', '개도율', 'valve opening'], ['IEC 60534-8-3 기준으로 noise 재계산 바랍니다.', 'Recalculate the noise per IEC 60534-8-3.', 'IEC 60534-8-3', 'IEC 60534-8-3'], ['Choked flow 여부를 확인해 주십시오.', 'Confirm whether choked flow occurs.', 'Choked flow', 'choked flow'], ['Downstream pipe schedule 을 SCH 80 으로 반영 바랍니다.', 'Use downstream pipe schedule SCH 80.', 'SCH 80', 'SCH 80']],
  inf: [['{T}: Required Cv 212 / Rated Cv 260', '{T}: required Cv 212 / rated Cv 260'], ['Max ΔP 18.2 bar, Normal ΔP 9.6 bar', 'Max dP 18.2 bar, normal dP 9.6 bar']],
  ev: ['teams', 'meeting'],
});
T('xv_act', ['On/Off Valve'], 3, {
  sKo: ['[{P}] {T} On/Off Valve Actuator Sizing 검토 의견', '{T} SDV stroke time 및 actuator torque margin 확인 요청', '{V} On/Off Valve Datasheet Rev.{R} 코멘트'],
  sEn: ['{T} actuator sizing - torque margin and stroke time', '[{P}] On/Off valve datasheet comments ({T})', 'ESD valve {T} - partial stroke test requirement'],
  cKo: ['{T} actuator 의 safety factor 가 1.25 로 Spec. 요구치(1.5) 미만입니다.', 'ESD valve {T} 의 closing time 요구사항은 2초 이내입니다.', 'Partial Stroke Test(PST) 적용 대상 tag 가 SRS 와 상이합니다.'],
  cEn: ['The actuator safety factor for {T} is 1.25, below the specified 1.5.', 'The required closing time for ESD valve {T} is 2 seconds or less.', 'The tags requiring Partial Stroke Test (PST) differ from the SRS.'],
  req: [['Actuator sizing 계산서', '재제출', 'actuator sizing calculation', 'resubmit'], ['Stroke time 시험 기록', '송부', 'stroke time test records', 'send'], ['Solenoid valve 사양', '확인', 'solenoid valve specification', 'confirm'], ['PST 적용 tag list', '업데이트', 'PST tag list', 'update']],
  li: [['{T}: Torque safety factor 1.5 이상 확보 바랍니다.', '{T}: Ensure a torque safety factor of at least 1.5.', 'safety factor', 'safety factor'], ['Solenoid valve 를 SIL 3 인증품으로 변경 바랍니다.', 'Change the solenoid valve to a SIL 3 certified model.', 'SIL 3', 'SIL 3'], ['Limit switch box (open/close) 사양 추가 바랍니다.', 'Add the limit switch box (open/close) specification.', 'Limit switch', 'limit switch'], ['Fire-safe 인증서 (API 607) 제출 바랍니다.', 'Submit the fire-safe certificate (API 607).', 'API 607', 'API 607']],
  inf: [['{T}: 12" CL600 Trunnion ball valve, Bettis G-series', '{T}: 12" CL600 trunnion ball valve, Bettis G-series'], ['Required closing time ≤ 2 sec', 'Required closing time <= 2 s']],
  ev: ['meeting', 'inspection'],
});
T('psv', ['PSV'], 3, {
  sKo: ['[{P}] {T} PSV Sizing Calculation 검토 의견', '{T} Set pressure 변경에 따른 재계산 요청', '{V} PSV Datasheet Rev.{R} 코멘트 송부'],
  sEn: ['{T} PSV sizing - orifice selection per API 526', '[{P}] PSV datasheet & sizing calculation comments', 'Set pressure change for {T} - request for recalculation'],
  cKo: ['{T} 의 fire case relief load 가 공정팀 재검토로 변경되었습니다.', 'Built-up back pressure 가 set pressure 의 10% 를 초과하여 bellows type 검토가 필요합니다.', '{T} orifice 가 J 에서 K 로 변경될 가능성이 있습니다.'],
  cEn: ['The fire case relief load for {T} has been revised by the process team.', 'The built-up back pressure exceeds 10% of set pressure, so a balanced bellows design needs to be considered.', 'The orifice of {T} may change from J to K.'],
  req: [['PSV sizing 계산서', '재제출', 'revised PSV sizing calculation', 'submit'], ['Orifice 선정 결과', '회신', 'orifice selection', 'confirm'], ['Inlet pressure drop 계산', '제출', 'inlet pressure loss calculation', 'provide'], ['Bellows 적용 여부', '검토', 'bellows option', 'review']],
  li: [['API 520 Part I 기준으로 required area 재계산 바랍니다.', 'Recalculate the required area per API 520 Part I.', 'API 520', 'API 520'], ['Inlet pressure loss 3% 이내 확인 바랍니다.', 'Confirm the inlet pressure loss is within 3%.', 'pressure loss', 'pressure loss'], ['Cap/Lever 적용 여부 표기 바랍니다.', 'Indicate cap/lever requirement.', 'Lever', 'lever'], ['Body material 을 WCC 로 수정 바랍니다.', 'Revise the body material to WCC.', 'WCC', 'WCC']],
  inf: [['{T}: Set 21.0 barg, Orifice K, 3K4 CL300 x CL150', '{T}: set 21.0 barg, orifice K, 3K4 CL300 x CL150'], ['Relief case: Fire / Blocked outlet', 'Relief case: fire / blocked outlet']],
  ev: ['inspection', 'teams'],
});
T('psv_test', ['PSV'], 2, {
  sKo: ['{T} 외 {N}대 PSV Set Pressure Test 입회 요청', '[{P}] PSV Pop test 성적서 송부 요청'],
  sEn: ['Set pressure test witness - {T} and {N} others', '[{P}] PSV test certificates (API 527 seat tightness)'],
  cKo: ['{T} 외 {N}대 PSV 제작이 완료되어 set pressure test 및 seat tightness test (API 527) 를 진행합니다.', 'PSV 시험 성적서 중 {T} 의 cold differential test pressure 값이 누락되어 있습니다.'],
  cEn: ['Fabrication of {T} and {N} other PSVs is complete and the set pressure and seat tightness (API 527) tests are ready.', 'The cold differential test pressure for {T} is missing in the test certificates.'],
  req: [['시험 성적서', '송부', 'test certificates', 'send'], ['입회 가능 여부', '회신', 'attendance', 'confirm'], ['CDTP 값', '확인', 'CDTP value', 'confirm']],
  li: [['CDTP 를 성적서에 기재 바랍니다.', 'State the CDTP on the certificate.', 'CDTP', 'CDTP'], ['Seal wire 및 tag plate 사진 첨부 바랍니다.', 'Attach photos of the seal wire and tag plate.', 'Seal wire', 'seal wire']],
  inf: [['시험 매체: Air (상온)', 'Test medium: air (ambient)'], ['Seat tightness: API 527, 0 bubble/min', 'Seat tightness: API 527, 0 bubbles/min']],
  ev: ['inspection'],
});
T('mov', ['MOV'], 3, {
  sKo: ['[{P}] {T} MOV Actuator Datasheet 검토 의견', '{V} MOV wiring diagram 및 전원 사양 확인 요청', '{T} 외 {N}대 MOV Profibus 통신 사양 확인'],
  sEn: ['{T} MOV actuator - wiring diagram & power supply', '[{P}] {V} actuator datasheets - comments Rev.{R}', 'MOV {T}: torque setting and Profibus address list'],
  cKo: ['{T} MOV 의 output torque 가 valve 요구 torque 대비 margin 이 부족합니다.', 'MCC 전원이 400V 3상 50Hz 로 확정되었습니다.', '{V} actuator 의 Profibus DP 주소 할당표가 아직 제출되지 않았습니다.'],
  cEn: ['The output torque of MOV {T} does not have enough margin over the valve required torque.', 'The MCC supply has been confirmed as 400 V, 3-phase, 50 Hz.', 'The Profibus DP address list for the {V} actuators has not been submitted yet.'],
  req: [['Wiring diagram', '송부', 'wiring diagram', 'send'], ['Torque 계산서', '제출', 'torque calculation', 'submit'], ['Profibus 주소 할당표', '송부', 'Profibus address list', 'provide'], ['전원 사양 변경 가능 여부', '확인', 'feasibility of the power supply change', 'confirm']],
  li: [['Enclosure 를 IP68 로 확인 바랍니다.', 'Confirm the enclosure rating is IP68.', 'IP68', 'IP68'], ['Local control station 위치를 표기해 주십시오.', 'Show the location of the local control station.', 'Local control station', 'local control station'], ['Torque switch 설정값을 기재 바랍니다.', 'State the torque switch settings.', 'Torque switch', 'torque switch'], ['Space heater 전원 사양 추가 바랍니다.', 'Add the space heater supply rating.', 'Space heater', 'space heater']],
  inf: [['{T}: IQ3 Pro, 400V/3ph/50Hz, Profibus DP-V1', '{T}: IQ3 Pro, 400 V/3 ph/50 Hz, Profibus DP-V1'], ['Valve 요구 torque: 610 Nm', 'Valve required torque: 610 Nm']],
  ev: ['fat', 'teams'],
});
T('flow_dp', ['Flow Meter'], 3, {
  sKo: ['[{P}] {T} Orifice Flow Element 계산서 검토 의견', '{T} 외 {N}건 Flow Element Sizing (ISO 5167) 확인 요청', 'Orifice plate beta ratio 관련 문의 ({T})'],
  sEn: ['{T} orifice sizing per ISO 5167 - comments', '[{P}] Flow element calculation Rev.{R} review', 'Beta ratio issue on {T}'],
  cKo: ['{T} 의 beta ratio 가 0.72 로 계산되어 Spec. 범위(0.2~0.7)를 벗어납니다.', 'Straight run (upstream 20D) 이 배관 도면상 확보되지 않습니다.', 'Flow element 계산서 Rev.{R} 검토하였습니다.'],
  cEn: ['The beta ratio of {T} is calculated as 0.72, outside the specified range of 0.2-0.7.', 'The required upstream straight run (20D) is not available on the piping layout.', 'We have reviewed the flow element calculation Rev.{R}.'],
  req: [['Flow element 계산서', '재제출', 'flow element calculation', 'resubmit'], ['DP range', '확인', 'DP range', 'confirm'], ['Flow conditioner 적용안', '검토', 'flow conditioner option', 'review'], ['Orifice flange tapping 사양', '회신', 'orifice flange tapping details', 'advise']],
  li: [['Beta ratio 0.7 이하로 bore 재선정 바랍니다.', 'Reselect the bore to achieve a beta ratio below 0.7.', 'Beta ratio', 'beta ratio'], ['Permanent pressure loss 를 계산서에 추가 바랍니다.', 'Add the permanent pressure loss to the calculation.', 'Permanent pressure loss', 'permanent pressure loss'], ['Drain/vent hole 적용 여부 확인 바랍니다.', 'Confirm the drain/vent hole requirement.', 'Drain/vent hole', 'drain/vent hole']],
  inf: [['{T}: 8" Sch.40, Flange tap, DP 0~2500 mmH2O', '{T}: 8" Sch.40, flange taps, DP 0-2500 mmH2O'], ['Fluid: Fuel gas, MW 18.2', 'Fluid: fuel gas, MW 18.2']],
  ev: ['teams'],
});
T('flow_mag', ['Flow Meter'], 3, {
  sKo: ['{T} {V} 유량계 Configuration Sheet 확인 요청', '[{P}] Coriolis / Magnetic Flowmeter Datasheet 검토 의견', '{T} 유량계 grounding ring 및 liner 재질 확인'],
  sEn: ['{T} {V} flowmeter - configuration sheet open points', '[{P}] Coriolis/Mag flowmeter datasheet comments', 'Liner material and grounding rings for {T}'],
  cKo: ['{T} 의 공정 유체에 HF 성분이 있어 PTFE liner 적용이 필요할 것으로 보입니다.', 'Coriolis meter {T} 의 density calibration 사양이 확정되지 않았습니다.', '{V} 측에서 configuration sheet 회신을 기다리고 있습니다.'],
  cEn: ['The process fluid of {T} contains HF, so a PTFE liner seems necessary.', 'The density calibration requirement for Coriolis meter {T} is not yet fixed.', '{V} is waiting for our reply on the configuration sheet.'],
  req: [['Configuration sheet', '회신', 'configuration sheet', 'return'], ['Totalizer 단위', '확인', 'totalizer units', 'confirm'], ['Grounding ring 재질', '확인', 'grounding ring material', 'confirm'], ['Liner 재질 변경안', '검토', 'liner material change', 'review']],
  li: [['Totalizer 단위를 t/h 로 설정 바랍니다.', 'Set the totalizer unit to t/h.', 't/h', 't/h'], ['Grounding ring 재질은 Hastelloy C 로 변경 바랍니다.', 'Change the grounding rings to Hastelloy C.', 'Hastelloy C', 'Hastelloy C'], ['Remote transmitter cable 길이 15 m 반영 바랍니다.', 'Include a 15 m remote transmitter cable.', '15 m', '15 m']],
  inf: [['{T}: DN150, PTFE liner, Hastelloy C electrode', '{T}: DN150, PTFE liner, Hastelloy C electrodes'], ['Output: 4-20 mA/HART + Pulse', 'Output: 4-20 mA/HART + pulse']],
  ev: ['teams', 'fat'],
});
T('tx_cfg', ['Transmitter'], 3, {
  sKo: ['{T} 외 {N}건 Smart Transmitter Configuration 확인 요청', '[{P}] 압력/온도 Transmitter Range 및 Tag 설정 관련', '{V} Transmitter Datasheet Rev.{R} 검토 의견'],
  sEn: ['{T} and {N} others - smart transmitter configuration data', '[{P}] Transmitter range & damping settings', 'Comments on {V} transmitter datasheets Rev.{R}'],
  cKo: ['출하 전 factory configuration 을 위해 {T} 외 {N}건의 range, unit, damping 값이 필요합니다.', '{T} 의 calibrated range 가 Instrument Index 와 상이합니다.', 'H2S 서비스 tag 는 NACE MR0175 적합 재질이 요구됩니다.'],
  cEn: ['For factory configuration before shipment we need the range, unit and damping of {T} and {N} other tags.', 'The calibrated range of {T} differs from the instrument index.', 'Tags in H2S service require NACE MR0175 compliant materials.'],
  req: [['Configuration data', '송부', 'configuration data', 'send'], ['Calibrated range', '확인', 'calibrated range', 'confirm'], ['Instrument Index 최신본', '송부', 'latest instrument index', 'provide'], ['Damping 설정값', '회신', 'damping settings', 'advise']],
  li: [['{T}: Range 0~40 barg 로 수정 바랍니다.', '{T}: Change the range to 0-40 barg.', '0~40 barg', '0-40 barg'], ['Wetted part 를 316L SS (NACE) 로 확인 바랍니다.', 'Confirm 316L SS (NACE) wetted parts.', 'NACE', 'NACE'], ['LCD indicator 단위를 kPa 로 설정 바랍니다.', 'Set the LCD indicator unit to kPa.', 'kPa', 'kPa'], ['Burnout 방향을 High 로 설정 바랍니다.', 'Set the failure alarm (burnout) to high.', 'High', 'high']],
  inf: [['{T}: 3051S, 0~25 barg, HART 7', '{T}: 3051S, 0-25 barg, HART 7'], ['Damping: 0.5 sec (default)', 'Damping: 0.5 s (default)']],
  ev: ['fat', 'teams'],
});
T('thermowell', ['Transmitter'], 2, {
  sKo: ['{T} Thermowell Wake Frequency 계산서 제출 요청', '[{P}] Thermowell 계산 (ASME PTC 19.3 TW) 검토 의견'],
  sEn: ['Thermowell wake frequency calculation - {T}', '[{P}] Thermowell calc per ASME PTC 19.3 TW-2016 - comments'],
  cKo: ['{T} 의 유속이 높아 velocity collar 적용 또는 U-length 축소 검토가 필요합니다.', '고속 유체 라인 thermowell 의 wake frequency 검토 결과가 아직 없습니다.'],
  cEn: ['Due to the high velocity at {T}, a velocity collar or shorter U-length needs to be considered.', 'We have not yet received the wake frequency check for the thermowells in high-velocity lines.'],
  req: [['Wake frequency 계산서', '제출', 'wake frequency calculation', 'submit'], ['U-length 변경안', '검토', 'reduced U-length', 'review'], ['Thermowell 도면', '송부', 'thermowell drawing', 'send']],
  li: [['ASME PTC 19.3 TW-2016 기준으로 계산 바랍니다.', 'Calculate per ASME PTC 19.3 TW-2016.', 'PTC 19.3', 'PTC 19.3'], ['Tapered stem 적용 여부 확인 바랍니다.', 'Confirm whether a tapered stem is applied.', 'Tapered', 'tapered stem']],
  inf: [['{T}: U-length 250 mm, 1-1/2" flanged', '{T}: U-length 250 mm, 1-1/2" flanged'], ['Max velocity 32 m/s', 'Max velocity 32 m/s']],
  ev: ['teams'],
});
T('hookup', ['Transmitter'], 2, {
  sKo: ['[{P}] Instrument Hook-up Drawing 검토 의견 (Rev.{R})', '{T} impulse line / manifold 사양 확인 요청'],
  sEn: ['[{P}] Hook-up drawings Rev.{R} - comments', 'Impulse line and manifold for {T}'],
  cKo: ['Hook-up drawing typical 중 DP transmitter (gas service) 의 slope 방향이 반대로 되어 있습니다.', '{T} 는 H2 service 로 double block & bleed manifold 가 요구됩니다.'],
  cEn: ['In the hook-up typicals, the impulse line slope for DP transmitters in gas service is drawn in the wrong direction.', '{T} is in H2 service and requires a double block & bleed manifold.'],
  req: [['Hook-up drawing', '수정', 'hook-up drawings', 'revise'], ['Manifold 사양', '확인', 'manifold specification', 'confirm'], ['Bulk material 물량', '업데이트', 'bulk material take-off', 'update']],
  li: [['Gas service 는 transmitter 를 tapping 보다 위에 설치하도록 수정 바랍니다.', 'Revise so that transmitters in gas service are mounted above the tapping point.', 'tapping', 'tapping point'], ['Impulse line slope 1:10 이상 표기 바랍니다.', 'Indicate the minimum impulse line slope of 1:10.', '1:10', '1:10'], ['5-valve manifold 로 변경 바랍니다.', 'Change to a 5-valve manifold.', '5-valve', '5-valve']],
  inf: [['Tube: 1/2" OD SS316, 0.049" wall', 'Tube: 1/2" OD SS316, 0.049" wall'], ['Fitting: Swagelok or equal', 'Fittings: Swagelok or equal']],
  ev: ['meeting'],
});
T('level_radar', ['Level'], 3, {
  sKo: ['{T} Radar Level 설치 조건 확인 요청', '[{P}] {V} Radar/GWR Level Datasheet 검토 의견', '{T} GWR probe 길이 및 still pipe 관련'],
  sEn: ['{T} radar level - installation and still pipe', '[{P}] {V} radar/GWR datasheet comments Rev.{R}', 'GWR probe length for {T}'],
  cKo: ['{T} 설치 탱크에 agitator 가 있어 false echo 우려가 있습니다.', '유체 유전율(εr)이 1.8 로 낮아 GWR 적용이 유리해 보입니다.', 'Nozzle 높이 변경으로 {T} probe 길이 재산정이 필요합니다.'],
  cEn: ['The tank of {T} has an agitator, so false echoes are a concern.', 'The dielectric constant is as low as 1.8, so GWR seems more suitable.', 'Due to the nozzle height change, the probe length of {T} must be recalculated.'],
  req: [['Still pipe 적용 여부', '확인', 'still pipe requirement', 'confirm'], ['Probe 길이', '회신', 'probe length', 'confirm'], ['Nozzle 도면', '송부', 'nozzle drawing', 'send'], ['유전율 data', '확인', 'dielectric constant data', 'provide']],
  li: [['Antenna 재질을 PTFE 로 변경 바랍니다.', 'Change the antenna material to PTFE.', 'PTFE', 'PTFE'], ['Probe 길이를 3,200 mm 로 수정 바랍니다.', 'Revise the probe length to 3,200 mm.', '3,200 mm', '3,200 mm'], ['Blocking distance 를 datasheet 에 표기 바랍니다.', 'State the blocking distance on the datasheet.', 'Blocking distance', 'blocking distance']],
  inf: [['{T}: 80 GHz radar, 2" CL150, range 0~12 m', '{T}: 80 GHz radar, 2" CL150, range 0-12 m'], ['εr = 1.8 (LPG)', 'er = 1.8 (LPG)']],
  ev: ['teams', 'visit'],
});
T('level_dp', ['Level'], 2, {
  sKo: ['{T} DP Level (Remote seal) capillary 길이 확인', '[{P}] Displacer / DP Level 계산서 검토'],
  sEn: ['{T} DP level with remote seals - capillary length', '[{P}] Displacer & DP level calculation - review'],
  cKo: ['{T} remote seal 의 capillary 길이를 양측 5 m 로 가정하였습니다.', 'Interface level 측정용 displacer 의 density 조건이 변경되었습니다.'],
  cEn: ['The capillary length for the remote seals of {T} has been assumed as 5 m on both sides.', 'The density conditions for the interface displacer have changed.'],
  req: [['Nozzle elevation', '확인', 'nozzle elevation', 'confirm'], ['Level 계산서', '재제출', 'level calculation', 'resubmit'], ['Fill fluid 선정 결과', '회신', 'fill fluid selection', 'advise']],
  li: [['Fill fluid 를 Syltherm XLT 로 변경 바랍니다.', 'Change the fill fluid to Syltherm XLT.', 'Syltherm', 'Syltherm'], ['Upper/Lower density 를 datasheet 에 기재 바랍니다.', 'State the upper/lower density on the datasheet.', 'density', 'density']],
  inf: [['{T}: Nozzle 간 거리 4,500 mm', '{T}: nozzle distance 4,500 mm'], ['Ambient: -20 ~ 55 ℃', 'Ambient: -20 to 55 degC']],
  ev: ['teams'],
});
T('analyzer', ['Analyzer'], 3, {
  sKo: ['[{P}] {T} Analyzer 시스템 (GC/O2/H2S) 검토 의견', 'Analyzer Shelter HVAC 및 Sample System 확인 요청', '{V} Analyzer TBE Clarification'],
  sEn: ['[{P}] Analyzer system {T} - sample conditioning comments', 'Analyzer shelter HVAC & sample system - clarification', '{V} analyzer TBE clarification - round {R}'],
  cKo: ['{T} 의 sample lag time 이 60초를 초과합니다.', 'Analyzer shelter 의 HVAC 이 vendor scope 에서 빠져 있습니다.', 'Calibration gas cylinder 수량 및 사양이 견적에 누락되었습니다.'],
  cEn: ['The sample lag time of {T} exceeds 60 seconds.', 'The shelter HVAC is excluded from the vendor scope.', 'The calibration gas cylinders are missing from the offer.'],
  req: [['Sample lag time 계산서', '제출', 'sample lag time calculation', 'submit'], ['Calibration gas 사양', '확인', 'calibration gas specification', 'confirm'], ['Shelter layout', '송부', 'shelter layout drawing', 'send'], ['Utility consumption list', '업데이트', 'utility consumption list', 'update']],
  li: [['Fast loop 를 적용하여 lag time 60초 이내로 수정 바랍니다.', 'Apply a fast loop to keep the lag time below 60 s.', 'Fast loop', 'fast loop'], ['Shelter HVAC 을 scope 에 포함 바랍니다.', 'Include the shelter HVAC in your scope.', 'HVAC', 'HVAC'], ['Gas detector (H2S/LEL) 를 shelter 내부에 추가 바랍니다.', 'Add H2S/LEL detectors inside the shelter.', 'H2S/LEL', 'H2S/LEL']],
  inf: [['{T}: Process GC, cycle 6 min', '{T}: process GC, cycle time 6 min'], ['Shelter: 6.0 x 2.5 x 3.0 m, Zone 1', 'Shelter: 6.0 x 2.5 x 3.0 m, Zone 1']],
  ev: ['fat', 'visit', 'teams'],
});
T('dcs_io', ['DCS/SIS'], 3, {
  sKo: ['[{P}] I/O List Rev.{R} 및 Marshalling 검토 요청', 'DCS I/O 수량 변경 및 Spare 확보 관련', '[{P}] DCS Cabinet Arrangement 검토 의견'],
  sEn: ['[{P}] I/O list Rev.{R} and marshalling - review', 'DCS I/O count change and spare philosophy', '[{P}] DCS cabinet arrangement drawing comments'],
  cKo: ['I/O List Rev.{R} 에서 AI 36점, DI 52점이 추가되었습니다.', 'Spare 20% 확보 기준 대비 일부 cabinet 이 15% 수준입니다.', 'Marshalling cabinet 의 terminal 번호가 loop diagram 과 상이합니다.'],
  cEn: ['I/O list Rev.{R} adds 36 AI and 52 DI points.', 'Some cabinets have only 15% spare against the 20% requirement.', 'The terminal numbers in the marshalling cabinets do not match the loop diagrams.'],
  req: [['I/O list', '업데이트', 'I/O list', 'update'], ['Cabinet arrangement 도면', '수정', 'cabinet arrangement drawing', 'revise'], ['Spare 확보 방안', '검토', 'spare allocation proposal', 'review'], ['Marshalling 도면', '재제출', 'marshalling drawings', 'resubmit']],
  li: [['Cabinet 별 spare 20% 이상 확보 바랍니다.', 'Ensure at least 20% spare per cabinet.', 'spare 20%', '20% spare'], ['IS / non-IS 신호를 분리 배치 바랍니다.', 'Segregate IS and non-IS signals.', 'IS / non-IS', 'IS and non-IS'], ['Redundant power supply 구성 표기 바랍니다.', 'Show the redundant power supply arrangement.', 'Redundant power', 'redundant power']],
  inf: [['AI 412 / AO 96 / DI 588 / DO 230', 'AI 412 / AO 96 / DI 588 / DO 230'], ['Cabinet: 18 sets (System 6, Marshalling 12)', 'Cabinets: 18 (6 system, 12 marshalling)']],
  ev: ['ifat', 'meeting', 'teams'],
});

T('sis_ce', ['DCS/SIS'], 3, {
  sKo: ['[{P}] Cause & Effect Diagram Rev.{R} 검토 의견', 'SIL Verification Report 코멘트 회신 ({T})', '[{P}] SRS / SIF 목록 업데이트 요청'],
  sEn: ['[{P}] Cause & Effect diagrams Rev.{R} - comments', 'SIL verification report - comments on {T}', '[{P}] SRS update and SIF list'],
  cKo: ['{T} 의 PFDavg 계산에 proof test interval 이 36개월로 적용되어 있습니다.', 'C&E Rev.{R} 에서 ESD-2 level 의 trip action 이 일부 누락되었습니다.', 'HAZOP/LOPA 결과 SIL 2 SIF 가 3건 추가되었습니다.'],
  cEn: ['The PFDavg of {T} has been calculated with a 36-month proof test interval.', 'Some ESD-2 trip actions are missing in C&E Rev.{R}.', 'Three additional SIL 2 SIFs resulted from the HAZOP/LOPA.'],
  req: [['SIL verification report', '재제출', 'SIL verification report', 'resubmit'], ['C&E diagram', '수정', 'C&E diagrams', 'revise'], ['SRS', '업데이트', 'SRS', 'update'], ['Vendor SIL 인증서', '제출', 'vendor SIL certificates', 'submit']],
  li: [['Proof test interval 을 24개월로 재계산 바랍니다.', 'Recalculate with a 24-month proof test interval.', '24개월', '24-month'], ['β factor 5% 적용 바랍니다.', 'Apply a common cause factor of 5%.', 'β factor', 'common cause factor'], ['Spurious trip rate 를 SIF 별로 추가 바랍니다.', 'Add the spurious trip rate for each SIF.', 'Spurious trip rate', 'spurious trip rate'], ['{T} 의 voting 을 2oo3 로 수정 바랍니다.', 'Change the voting of {T} to 2oo3.', '2oo3', '2oo3']],
  inf: [['{T}: SIL 2 target, PFDavg 4.2E-3', '{T}: SIL 2 target, PFDavg 4.2E-3'], ['Final element: XV + SOV (1oo2)', 'Final element: XV + SOV (1oo2)']],
  ev: ['meeting', 'teams'],
});
T('dcs_gfx', ['DCS/SIS'], 2, {
  sKo: ['[{P}] DCS Graphic (Round {R}) 코멘트 송부', 'Alarm Management / Alarm list 검토 요청', '{V} DCS FAT Procedure 검토 의견'],
  sEn: ['[{P}] DCS graphics round {R} - marked-up comments', 'Alarm list and alarm rationalization - review', '{V} DCS FAT procedure - comments'],
  cKo: ['Graphic Round {R} 검토 결과 총 {N}건의 코멘트가 있습니다.', 'Alarm list 상 priority 가 정의되지 않은 alarm 이 다수 있습니다.', 'FAT procedure 에 SIS-DCS interface test 항목이 누락되어 있습니다.'],
  cEn: ['There are {N} comments in total on graphics round {R}.', 'Many alarms in the alarm list have no priority assigned.', 'The FAT procedure does not include the SIS-DCS interface test.'],
  req: [['Marked-up graphic', '반영', 'marked-up graphics', 'incorporate'], ['Alarm list', '검토', 'alarm list', 'review'], ['FAT procedure', '수정', 'FAT procedure', 'revise']],
  li: [['Overview 화면에 trip 상태 표시 추가 바랍니다.', 'Add trip status indication to the overview display.', 'trip 상태', 'trip status'], ['Alarm priority 를 EEMUA 191 기준으로 재분류 바랍니다.', 'Reclassify the alarm priorities per EEMUA 191.', 'EEMUA 191', 'EEMUA 191'], ['SIS-DCS interface test 항목을 추가 바랍니다.', 'Add the SIS-DCS interface test.', 'interface test', 'interface test']],
  inf: [['Graphic 수량: 148 sheets', 'Number of graphics: 148'], ['Alarm 수량: 3,412 points', 'Number of alarms: 3,412']],
  ev: ['fat', 'ifat', 'meeting'],
});
T('fg', ['F&G'], 3, {
  sKo: ['[{P}] F&G Detector Layout Rev.{R} 검토 의견', '{T} Gas Detector 교정 및 설정값 확인', 'Detector Mapping Study 결과 공유 및 검토 요청'],
  sEn: ['[{P}] F&G detector layout Rev.{R} - comments', 'Gas detector {T} - calibration and alarm set points', 'Detector mapping study results - request for review'],
  cKo: ['Compressor shelter 의 gas detection coverage 가 목표 90% 대비 82% 입니다.', '{T} 의 alarm set point 가 F&G philosophy (20/40 %LEL) 와 상이합니다.', 'Flame detector 의 시야각(cone of vision) 검토가 필요합니다.'],
  cEn: ['Gas detection coverage of the compressor shelter is 82% against the 90% target.', 'The alarm set points of {T} differ from the F&G philosophy (20/40 %LEL).', 'The cone of vision of the flame detectors needs to be checked.'],
  req: [['추가 detector 배치안', '검토', 'additional detector layout', 'review'], ['Alarm set point', '확인', 'alarm set points', 'confirm'], ['Mapping study report', '송부', 'mapping study report', 'submit'], ['Voting logic', '확인', 'voting logic', 'confirm']],
  li: [['{T} set point 를 20/40 %LEL 로 수정 바랍니다.', 'Revise the set points of {T} to 20/40 %LEL.', '20/40 %LEL', '20/40 %LEL'], ['Open path detector 추가 검토 바랍니다.', 'Consider adding open path detectors.', 'Open path', 'open path'], ['2ooN voting 적용 여부 확인 바랍니다.', 'Confirm whether 2ooN voting is applied.', '2ooN', '2ooN']],
  inf: [['{T}: IR point gas detector, 0~100 %LEL', '{T}: IR point gas detector, 0-100 %LEL'], ['Coverage: 82% (target 90%)', 'Coverage: 82% (target 90%)']],
  ev: ['meeting', 'sat', 'teams'],
});
T('cable', ['Cable/JB'], 3, {
  sKo: ['[{P}] 계장 Cable Schedule Rev.{R} 물량 확인 요청', '{T} Junction Box 제작도면 승인 요청', 'Cable gland / tray 사양 확인 ({T})'],
  sEn: ['[{P}] Instrument cable schedule Rev.{R} - quantity check', 'Junction box {T} - fabrication drawing approval', 'Cable glands and tray sizing for {T}'],
  cKo: ['Cable Schedule Rev.{R} 기준 설계물량과 현장 실측물량 간 차이가 있습니다.', '{T} 외 {N}면 Junction Box 제작도면을 송부드립니다.', 'Armoured cable 적용 구간의 gland 사양이 확정되지 않았습니다.'],
  cEn: ['There is a discrepancy between the cable schedule Rev.{R} and the site measured quantities.', 'Please find attached the fabrication drawings for {T} and {N} other junction boxes.', 'The gland specification for the armoured cable routes is not yet fixed.'],
  req: [['Cable 물량', '확정', 'cable quantities', 'confirm'], ['JB 제작도면', '승인', 'JB fabrication drawings', 'approve'], ['Cable gland size', '확인', 'cable gland sizes', 'confirm'], ['Cable schedule', '업데이트', 'cable schedule', 'update']],
  li: [['{T}: Gland size 를 M25 로 변경 바랍니다.', '{T}: Change the gland size to M25.', 'M25', 'M25'], ['Spare terminal 20% 확보 바랍니다.', 'Provide 20% spare terminals.', 'Spare terminal', 'spare terminals'], ['Multi-pair cable 의 overall screen 사양 확인 바랍니다.', 'Confirm the overall screen of the multi-pair cables.', 'overall screen', 'overall screen'], ['Tray fill ratio 40% 이내 확인 바랍니다.', 'Check that the tray fill ratio is within 40%.', 'fill ratio', 'fill ratio']],
  inf: [['Signal 1P x 1.25SQ: 48,200 m', 'Signal 1P x 1.25 mm2: 48,200 m'], ['{T}: Exe IIC T6, SS316L, 24P', '{T}: Exe IIC T6, SS316L, 24P']],
  ev: ['loop', 'visit', 'meeting'],
});
T('loop', ['DCS/SIS', 'Cable/JB'], 2, {
  sKo: ['[{P}] Unit {N}00 Loop Check 일정 및 준비사항', 'Loop Check 진행 현황 및 미결 사항 ({T})', 'Loop folder 준비 요청'],
  sEn: ['[{P}] Unit {N}00 loop check schedule and preparation', 'Loop check progress and open items ({T})', 'Preparation of loop folders'],
  cKo: ['DCS energize 가 완료되어 loop check 를 진행할 예정입니다.', '금주 loop check 진행률은 62% 이며 {T} 구간에서 지연이 있습니다.', 'Loop check 에 필요한 loop folder 와 calibrator 준비가 필요합니다.'],
  cEn: ['DCS energization is complete and the loop check will start soon.', 'Loop check progress this week is 62%, with delays around {T}.', 'Loop folders and calibrators must be ready before the loop check.'],
  req: [['Loop folder', '준비', 'loop folders', 'prepare'], ['Calibrator 교정 유효기간', '확인', 'calibrator validity', 'check'], ['Termination 완료 여부', '공유', 'termination status', 'report'], ['입회자 명단', '송부', 'list of witnesses', 'send']],
  li: [['{T} termination 을 완료 바랍니다.', 'Complete the termination of {T}.', 'termination', 'termination'], ['HART communicator 를 준비 바랍니다.', 'Prepare a HART communicator.', 'HART communicator', 'HART communicator'], ['Loop check sheet 양식을 최신본으로 사용 바랍니다.', 'Use the latest loop check sheet form.', 'Loop check sheet', 'loop check sheet']],
  inf: [['AI/AO 312 loops, DI/DO 148 loops', 'AI/AO 312 loops, DI/DO 148 loops'], ['진행률 62%', 'Progress: 62%']],
  ev: ['loop', 'meeting'],
});
T('pump', ['Pump'], 2, {
  sKo: ['[{P}] {T} Pump 계장 사양 (Seal Plan / Vibration) 확인', '{V} Pump Vendor Data - 계장 Interface 검토 의견', '{T} Seal plan 53B PT/LT 사양 확인 요청'],
  sEn: ['[{P}] {T} pump instrumentation - seal plan & vibration monitoring', '{V} pump vendor data - instrument interface comments', 'Seal plan 53B instruments for {T}'],
  cKo: ['{T} 의 seal plan 53B 용 pressure transmitter 사양이 프로젝트 standard 와 상이합니다.', 'Pump vibration monitoring (Bently Nevada 3500) interface 가 정의되지 않았습니다.', '{V} 에서 제출한 pump 계장 hook-up 이 프로젝트 기준과 맞지 않습니다.'],
  cEn: ['The pressure transmitter for seal plan 53B of {T} does not follow the project standard.', 'The interface for pump vibration monitoring (Bently Nevada 3500) is not defined.', 'The pump instrument hook-up from {V} does not comply with the project standard.'],
  req: [['Seal plan 계장 사양', '확인', 'seal plan instrument specification', 'confirm'], ['Vibration probe 사양', '송부', 'vibration probe data', 'send'], ['Pump 계장 hook-up', '수정', 'pump instrument hook-up', 'revise'], ['Motor RTD 사양', '확인', 'motor RTD details', 'confirm']],
  li: [['Seal plan 53B PT 를 프로젝트 standard (3051S) 로 변경 바랍니다.', 'Use the project standard transmitter (3051S) for seal plan 53B.', '53B', '53B'], ['Bearing RTD 를 3-wire Pt100 으로 확인 바랍니다.', 'Confirm 3-wire Pt100 bearing RTDs.', 'Pt100', 'Pt100'], ['Vibration alarm/trip 설정값 제시 바랍니다.', 'Provide the vibration alarm/trip settings.', 'alarm/trip', 'alarm/trip']],
  inf: [['{T}: API 610 OH2, Seal plan 11+53B', '{T}: API 610 OH2, seal plan 11+53B'], ['Motor: 315 kW, 6.6 kV', 'Motor: 315 kW, 6.6 kV']],
  ev: ['fat', 'inspection', 'teams'],
});
// ---- generic topics (cats come from the vendor's category) ----
T('vdr', null, 4, {
  sKo: ['[{P}] Vendor Document 제출 현황 및 지연 문서 독촉 ({V})', '[{P}] VDRL 문서 Return 결과 송부 - Transmittal {DOC}', '{V} 미제출 문서 (Overdue) 제출 요청'],
  sEn: ['[{P}] VDRL status and overdue documents - {V}', '[{P}] Document return - Transmittal {DOC}', 'Overdue vendor documents - {V} PO {PO}'],
  cKo: ['VDRL 상 제출 기한이 지난 문서가 {N}건 있습니다.', '제출하신 문서 검토 결과 일부 문서가 Code 3 (Rejected) 로 회신되었습니다.', '최종 문서(Final MDR) 제출 일정이 지연되고 있습니다.'],
  cEn: ['There are {N} documents past their due date in the VDRL.', 'Some of the submitted documents have been returned with Code 3 (rejected).', 'The submission of the final documentation (MDR) is delayed.'],
  req: [['미제출 문서', '제출', 'overdue documents', 'submit'], ['Code 3 문서', '재제출', 'Code 3 documents', 'resubmit'], ['VDRL 일정표', '업데이트', 'VDRL schedule', 'update'], ['Final MDR', '제출', 'final MDR', 'submit']],
  li: [['GA drawing ({DOC}) 제출 바랍니다.', 'Submit the GA drawing ({DOC}).', 'GA drawing', 'GA drawing'], ['ITP 를 Rev.{R} 로 재제출 바랍니다.', 'Resubmit the ITP as Rev.{R}.', 'ITP', 'ITP'], ['IOM manual 초안 제출 바랍니다.', 'Submit the draft IOM manual.', 'IOM manual', 'IOM manual']],
  inf: [['Code 1: {N}건 / Code 2: 7건 / Code 3: 2건', 'Code 1: {N} / Code 2: 7 / Code 3: 2'], ['Overdue: {N}건', 'Overdue: {N}']],
  ev: ['meeting', 'teams'],
});
T('insp', null, 4, { dir: 'in',
  sKo: ['[{P}] {T} 외 {N}대 최종검사 (Final Inspection) 통보', '{V} ITP Hold Point 입회 요청 ({T})', '[{P}] Hydro test / PMI 입회 일정 협의'],
  sEn: ['[{P}] Inspection notification - {T} and {N} others', '{V} ITP hold point witness request ({T})', '[{P}] Hydrostatic test and PMI witness - schedule'],
  cKo: ['승인된 ITP Rev.{R} 에 따라 {T} 외 {N}대의 최종검사를 진행합니다.', 'Hydrostatic test 및 PMI 는 TPI 입회 하에 진행 예정입니다.', '검사 준비가 완료되어 Inspection Release Note (IRN) 발행을 위한 검사를 요청드립니다.'],
  cEn: ['In accordance with the approved ITP Rev.{R}, the final inspection of {T} and {N} other items will be performed.', 'The hydrostatic test and PMI will be witnessed by the TPI.', 'The items are ready and we request the inspection for issuing the Inspection Release Note (IRN).'],
  req: [['입회 가능 여부', '회신', 'attendance', 'confirm'], ['검사 절차서', '검토', 'inspection procedure', 'review'], ['입회자 명단', '송부', 'names of inspectors', 'advise'], ['IRN', '발행', 'IRN', 'issue']],
  li: [['Calibration 유효기간이 지난 gauge 사용 금지 바랍니다.', 'Do not use gauges with expired calibration.', 'Calibration 유효기간', 'expired calibration'], ['검사 전 Material certificate (EN 10204 3.1) 제출 바랍니다.', 'Submit the EN 10204 3.1 material certificates before inspection.', '3.1', '3.1']],
  inf: [['Hydro test: 1.5 x design pressure, 10 min hold', 'Hydro test: 1.5 x design pressure, 10 min hold'], ['PMI: 100% (alloy parts)', 'PMI: 100% (alloy parts)']],
  ev: ['inspection', 'fat'],
});
T('ncr', null, 2, {
  sKo: ['[{P}] NCR-{N}{R} 발행 통보 ({T})', '{T} 부적합 (NCR) 시정조치 요청'],
  sEn: ['[{P}] NCR-{N}{R} raised against {T}', 'Non-conformance on {T} - corrective action required'],
  cKo: ['{T} 검사 중 PMI 결과 Mo 함량이 기준 미달로 확인되어 NCR 을 발행하였습니다.', '{T} 의 hydro test 중 body 에서 미세 누설이 확인되었습니다.'],
  cEn: ['During inspection, the PMI result for {T} showed Mo content below the minimum, and an NCR has been raised.', 'A minor leak was found on the body of {T} during the hydrostatic test.'],
  req: [['원인 분석 및 시정조치 계획', '제출', 'root cause analysis and corrective action plan', 'submit'], ['재검사 일정', '회신', 'proposed re-inspection date', 'advise'], ['대체품 Material certificate', '제출', 'material certificate of the replacement part', 'provide']],
  li: [['동일 heat number 자재 출하 보류 바랍니다.', 'Hold shipment of all items from the same heat number.', '출하 보류', 'Hold shipment'], ['재발 방지 대책을 포함 바랍니다.', 'Include preventive actions.', '재발 방지', 'preventive actions']],
  inf: [['Mo 함량: 1.62% (기준 2.0% 이상)', 'Mo content: 1.62% (min. 2.0%)'], ['NCR 등급: Major', 'NCR category: major']],
  ev: ['inspection'],
});
T('ship', null, 3, {
  sKo: ['[{P}] {V} 출하 일정 및 Packing List 송부', 'PO {PO} 납기 지연 관련 Expediting', '[{P}] {T} 외 {N}건 출하 준비 완료 통보'],
  sEn: ['[{P}] {V} shipment schedule and packing list', 'Expediting - PO {PO} delivery delay', '[{P}] Ready for shipment - {T} and {N} others'],
  cKo: ['{V} 자재 출하 준비가 완료되었습니다.', '공급업체 sub-supplier 지연으로 납기가 약 2주 지연될 예정입니다.', '선적 서류 (Packing list, Commercial invoice) 초안을 송부드립니다.'],
  cEn: ['The {V} materials are ready for shipment.', 'Delivery will be delayed by about two weeks due to a sub-supplier.', 'Please find attached the draft shipping documents (packing list, commercial invoice).'],
  req: [['Forwarder 지정', '진행', 'forwarder nomination', 'arrange'], ['Shipping mark', '확인', 'shipping marks', 'confirm'], ['Recovery schedule', '제출', 'recovery schedule', 'submit'], ['선적 서류', '검토', 'shipping documents', 'review']],
  li: [['Packing list 에 Tag No. 를 표기 바랍니다.', 'Show the tag numbers on the packing list.', 'Tag No.', 'tag numbers'], ['Crate 별 중량/치수 기재 바랍니다.', 'State the weight and dimensions of each crate.', '중량/치수', 'weight and dimensions']],
  inf: [['Crate: 12 EA, Gross 4,820 kg', 'Crates: 12, gross 4,820 kg'], ['Incoterms: FCA Hamburg', 'Incoterms: FCA Hamburg']],
  ev: ['ship', 'inspection'],
});
T('comm', null, 3, {
  sKo: ['[{P}] {V} 견적 (Quotation) 검토 및 Clarification', 'Change Order 견적 송부 요청 ({T})', '[{P}] RFQ 발송 - {T} 외 {N}건'],
  sEn: ['[{P}] {V} quotation - clarification', 'Change order request - {T}', '[{P}] RFQ - {T} and {N} other tags'],
  cKo: ['{V} 견적서 검토 결과 일부 scope 이 누락된 것으로 보입니다.', '공정 조건 변경으로 {T} 사양 변경에 따른 Change Order 가 필요합니다.', '첨부와 같이 RFQ 를 송부드립니다.'],
  cEn: ['Our review of the {V} quotation shows that some scope is missing.', 'Due to the process change, a change order is needed for {T}.', 'Please find attached our RFQ package.'],
  req: [['수정 견적서', '송부', 'revised quotation', 'submit'], ['Deviation list', '제출', 'deviation list', 'provide'], ['Change Order 견적', '제출', 'change order quotation', 'submit'], ['납기', '확인', 'delivery time', 'confirm']],
  li: [['Price breakdown 을 tag 별로 제시 바랍니다.', 'Provide a price breakdown per tag.', 'Price breakdown', 'price breakdown'], ['2년 운전 spare 가격 포함 바랍니다.', 'Include the price of 2-year operational spares.', '2년 운전 spare', '2-year operational spares'], ['견적 유효기간 90일 확인 바랍니다.', 'Confirm a validity of 90 days.', '유효기간', 'validity']],
  inf: [['Price validity: 60 days', 'Price validity: 60 days'], ['Delivery: 16 weeks ex-works', 'Delivery: 16 weeks ex-works']],
  ev: ['meeting', 'teams'],
});
T('inv', null, 1, { dir: 'in',
  sKo: ['PO {PO} 기성 청구 (Invoice) 관련 확인 요청', '[{P}] {V} Invoice 지급 일정 문의'],
  sEn: ['Invoice for PO {PO} - payment status', 'Payment reminder - {V} invoice ({PO})'],
  cKo: ['PO {PO} 의 2차 기성 (Milestone: FAT 완료) 청구서를 송부드립니다.', '지난달 청구한 invoice 의 지급이 아직 확인되지 않습니다.'],
  cEn: ['Please find attached our invoice for the second milestone (FAT completion) under PO {PO}.', 'We have not yet received payment for the invoice issued last month.'],
  req: [['지급 예정일', '회신', 'expected payment date', 'advise'], ['Invoice 승인', '진행', 'invoice approval', 'process'], ['송금 확인서', '송부', 'remittance advice', 'send']],
  li: [], inf: [['Invoice No. 9001{N}: USD 128,400', 'Invoice No. 9001{N}: USD 128,400']],
  ev: [],
});
T('spir', null, 2, {
  sKo: ['[{P}] SPIR (Spare Parts) 제출 요청 - {V}', '{T} 외 Commissioning / 2년 운전 Spare 견적 요청'],
  sEn: ['[{P}] SPIR submission - {V}', 'Spare parts (commissioning & 2-year) for {T} and others'],
  cKo: ['PO 조건에 따라 SPIR 제출이 필요합니다.', 'Commissioning spare 와 2년 운전 spare 를 구분하여 견적이 필요합니다.'],
  cEn: ['According to the PO, the SPIR shall be submitted.', 'We need separate prices for commissioning spares and 2-year operating spares.'],
  req: [['SPIR', '제출', 'SPIR', 'submit'], ['Spare 견적', '송부', 'spare parts quotation', 'submit'], ['Interchangeability 정보', '확인', 'interchangeability data', 'confirm']],
  li: [['SPIR 는 Excel 원본으로 제출 바랍니다.', 'Submit the SPIR in native Excel format.', 'Excel', 'Excel'], ['Capital spare 는 별도 옵션으로 견적 바랍니다.', 'Quote capital spares as a separate option.', 'Capital spare', 'capital spares']],
  inf: [['양식: F-SPIR-01 Rev.4', 'Form: F-SPIR-01 Rev.4']],
  ev: [],
});
T('cal', null, 2, {
  sKo: ['{T} 외 {N}건 교정 성적서 (Calibration Certificate) 송부 요청', '[{P}] 교정 성적서 누락 확인'],
  sEn: ['Calibration certificates for {T} and {N} others', '[{P}] Missing calibration certificates'],
  cKo: ['현장 입고 검사 중 {T} 외 {N}건의 교정 성적서가 누락된 것을 확인하였습니다.', '교정 성적서상 calibrated range 가 datasheet 와 상이한 tag 가 있습니다.'],
  cEn: ['During receiving inspection we found that the calibration certificates of {T} and {N} other items are missing.', 'Some calibration certificates show a calibrated range different from the datasheet.'],
  req: [['교정 성적서', '송부', 'calibration certificates', 'send'], ['Calibrated range', '확인', 'calibrated range', 'confirm'], ['재교정', '진행', 're-calibration', 'arrange']],
  li: [['성적서에 기준기 (reference standard) 교정 이력 포함 바랍니다.', 'Include the traceability of the reference standard.', '기준기', 'reference standard'], ['5-point calibration 결과 기재 바랍니다.', 'Include the 5-point calibration results.', '5-point', '5-point']],
  inf: [['누락: {N}건', 'Missing: {N} certificates']],
  ev: ['inspection'],
});
T('mtc', null, 2, {
  sKo: ['[{P}] Material Certificate (EN 10204 3.1) 및 PMI 기록 제출 요청', '{T} 재질 성적서 확인'],
  sEn: ['[{P}] EN 10204 3.1 material certificates and PMI records', 'Material certificates for {T}'],
  cKo: ['MDR 검토 결과 pressure retaining part 의 3.1 성적서 일부가 누락되었습니다.', '{T} 의 heat number 가 성적서와 일치하지 않습니다.'],
  cEn: ['Some EN 10204 3.1 certificates for pressure retaining parts are missing in the MDR.', 'The heat number of {T} does not match the certificate.'],
  req: [['3.1 성적서', '제출', '3.1 certificates', 'submit'], ['PMI 기록', '송부', 'PMI records', 'send'], ['Heat number', '확인', 'heat numbers', 'confirm'], ['NACE 적합 확인서', '제출', 'NACE compliance statement', 'provide']],
  li: [['Heat number 와 tag 대응표 작성 바랍니다.', 'Prepare a heat number vs. tag cross-reference.', '대응표', 'cross-reference'], ['Bolting 재질 성적서도 포함 바랍니다.', 'Include certificates for the bolting.', 'Bolting', 'bolting']],
  inf: [['Body: A351 CF8M, Heat 7Y2215', 'Body: A351 CF8M, heat 7Y2215']],
  ev: ['inspection'],
});
T('mtg', null, 2, {
  sKo: ['[{P}] {V} Kick-off Meeting 개최 안내', '[{P}] 계장 주간 Progress Meeting 안건', '{V} Technical Clarification Meeting (Teams) 일정 협의'],
  sEn: ['[{P}] Kick-off meeting with {V}', '[{P}] Weekly I&C progress meeting - agenda', 'Technical clarification meeting (Teams) - {V}'],
  cKo: ['PO 발행에 따라 {V} 와의 Kick-off meeting 을 아래와 같이 개최하고자 합니다.', '주간 progress meeting 안건 공유드립니다.', '미결 기술 사항 정리를 위해 Teams 회의를 요청드립니다.'],
  cEn: ['Following the PO award, we would like to hold the kick-off meeting with {V}.', 'Please see the agenda for the weekly progress meeting.', 'We would like to arrange a Teams meeting to close the open technical points.'],
  req: [['참석자 명단', '송부', 'list of attendees', 'send'], ['안건', '제출', 'agenda items', 'submit'], ['Organization chart', '송부', 'organization chart', 'provide'], ['참석 가능 여부', '회신', 'availability', 'confirm']],
  li: [['Document schedule (VDRL) 초안 준비 바랍니다.', 'Prepare a draft document schedule (VDRL).', 'VDRL', 'VDRL'], ['Sub-vendor list 준비 바랍니다.', 'Prepare the sub-vendor list.', 'Sub-vendor list', 'sub-vendor list']],
  inf: [['1) Project overview', '1) Project overview'], ['2) Scope of supply', '2) Scope of supply'], ['3) Document schedule', '3) Document schedule']],
  ev: ['kickoff', 'meeting', 'teams'],
});

// ---- event vocabulary: name [ko, en], places ----
const EVENTS = {
  fat: [['FAT', 'FAT'], ['공장검수(FAT)', 'Factory Acceptance Test'], ['FAT 입회', 'FAT witness']],
  ifat: [['IFAT', 'IFAT'], ['통합 FAT (IFAT)', 'Integrated FAT']],
  sat: [['SAT', 'SAT'], ['현장 시험 (SAT)', 'Site Acceptance Test']],
  inspection: [['최종검사', 'final inspection'], ['Hydro test 입회', 'hydrostatic test witness'], ['PMI 입회 검사', 'PMI witness'], ['출하 전 검사', 'pre-shipment inspection'], ['Calibration 입회', 'calibration witness']],
  kickoff: [['Kick-off meeting', 'kick-off meeting'], ['킥오프 미팅', 'KOM']],
  meeting: [['주간 진행회의', 'weekly progress meeting'], ['기술 협의 회의', 'technical meeting'], ['코멘트 협의 회의', 'comment resolution meeting'], ['Model review 회의', 'model review meeting']],
  teams: [['Teams 회의', 'Teams call'], ['화상회의', 'video conference'], ['Conference call', 'conference call']],
  visit: [['현장 방문', 'site visit'], ['공장 방문', 'factory visit'], ['Yard 방문', 'yard visit']],
  loop: [['Loop check', 'loop check'], ['Loop test', 'loop test']],
  ship: [['출하 (ETD)', 'shipment ETD'], ['선적', 'shipment'], ['현장 입고 (ETA)', 'ETA at site']],
  shutdown: [['정기보수 (Shutdown)', 'plant shutdown'], ['T/A 착수', 'turnaround']],
  training: [['운전원 교육', 'operator training'], ['Maintenance training', 'maintenance training']],
};
const PLACES_KO = ['본사 9층 대회의실', '본사 7층 소회의실 3', '현장 사무실 2층 회의실', '업체 공장', 'MS Teams', '울산 현장 CCR', '창원 공장', '판교 R&D 센터'];
const PLACES_EN = ['Hangyeol Tower 9F, Meeting Room 3', 'vendor works', 'MS Teams', 'site office, 2F meeting room', 'Singapore facility', 'Chennai works', 'Frankfurt works'];

// =====================================================================================
// GENERATOR
// =====================================================================================
const PP = { submit: 'submitted', resubmit: 'resubmitted', provide: 'provided', send: 'sent', confirm: 'confirmed', review: 'reviewed', revise: 'revised', update: 'updated', return: 'returned', complete: 'completed', advise: 'advised', incorporate: 'incorporated', approve: 'approved', prepare: 'prepared', check: 'checked', report: 'reported', arrange: 'arranged', issue: 'issued', process: 'processed', 'fill in': 'filled in' };
const INBOUND_REQ = [['도면 승인 결과', '회신', 'drawing approval', 'provide'], ['최신 공정 Data', '송부', 'latest process data', 'send'], ['PO 진행 일정', '회신', 'PO schedule', 'advise'], ['최종 기술 사양', '확정', 'final technical specification', 'confirm'], ['Tag list', '확인', 'tag list', 'confirm'], ['Nozzle 사양', '확인', 'nozzle details', 'confirm'], ['Shipping instruction', '송부', 'shipping instruction', 'issue'], ['문서 검토 결과', '회신', 'document review comments', 'return'], ['검사 입회 가능 여부', '회신', 'inspection attendance', 'confirm'], ['Hold 해제 여부', '확인', 'release of the hold points', 'confirm']];
const INBOUND_CTX_KO = ['당사에서 제작 중인 {T} 관련하여 몇 가지 확인 요청드립니다.', '{T} 외 {N}건 제작 착수를 위해 아래 사항 확인이 필요합니다.', '{V} 측 엔지니어링 진행 중 {T} 관련 미결 사항이 있어 연락드립니다.'];
const INBOUND_CTX_EN = ['We are progressing the engineering for {T} and need a few confirmations from your side.', 'To proceed with manufacturing of {T} and {N} other items, the following points need your input.', 'There are some open points on {T} that are holding our engineering.'];
const DISTRACT_KO = ['첨부와 같이 송부드립니다.', '궁금하신 점 있으시면 언제든 연락 주세요.', '관련 자료는 EDMS 에 업로드되어 있으니 참고 바랍니다.', '업체에는 별도로 요청해 두었습니다.', '검토 결과는 정리되는 대로 공유드리겠습니다.', '참고로 해당 건은 발주처 승인 사항입니다.', '추가로 필요하신 자료 있으시면 말씀 주십시오.', '항상 협조해 주셔서 감사합니다.'];
const DISTRACT_EN = ['Please find attached the relevant documents for your reference.', 'If you need anything else, let me know.', 'Please note that the delivery date remains unchanged.', 'Should you have any questions, please do not hesitate to contact us.', 'Thank you for your cooperation.', 'For your information, the client has already approved the philosophy document.', 'Please be informed that our office will be closed on public holidays as usual.', 'We appreciate your continued support.'];
function commitKo(S) { const d = dueExpr(S, 'ko'); return pick([`저희 쪽 자료는 ${d.ko} 송부드리겠습니다.`, `수정본은 ${d.ko} 제출하겠습니다.`, '회의록은 회의 후 공유드리겠습니다.']); }
function commitEn(S) { const d = dueExpr(S, 'en'); return pick([`We will send the updated documents ${d.en}.`, `Our revised calculation will follow ${d.en}.`, 'We will share the minutes after the meeting.', 'I will check internally and come back to you.']); }

function fill(s, F) { return s.replace(/\{(\w+)\}/g, (m, k) => (F[k] !== undefined ? F[k] : m)); }
function makeCtx(topic) {
  let vendor, cat;
  if (topic.cats) { cat = pick(topic.cats); const vs = VENDORS.filter((v) => v.cats.some((c) => topic.cats.includes(c))); vendor = vs.length ? pick(vs) : pick(VENDORS); }
  else { vendor = pick(VENDORS); cat = pick(vendor.cats); }
  const T1 = mkTag(cat); let T2 = mkTag(cat); if (T2 === T1) T2 = T1.replace(/\d$/, (d) => String((+d + 1) % 10));
  const prj = pick(PROJECTS);
  const F = { T: T1, T2, N: String(ri(2, 18)), R: pick(['A', 'B', 'C', '0', '1', '2']), C: pick(['1', '2', '3', 'A', 'B', 'C']), V: vendor.brand, P: prj.code, PN: prj.name, DOC: `${prj.code.replace('-', '')}-${vendor.brand.slice(0, 3).toUpperCase().replace(/[^A-Z]/g, 'X')}-IC-${pick(['DS', 'CAL', 'DWG', 'PRC', 'RPT'])}-${pad(ri(1, 120), 4)}`, PO: `45002${ri(10000, 99999)}`, Q: String(ri(2, 40)) };
  const cats = topic.key === 'loop' ? ['DCS/SIS', 'Cable/JB', 'Transmitter'] : topic.key === 'pump' ? ['Pump', 'Transmitter'] : [cat];
  return { topic, vendor, cat, cats, F, prj };
}

// ---- request sentence rendering ----
function article(n) { return /^(your|a |an |the )/i.test(n) ? n : 'the ' + n; }
function koReq(obj, verb, d) {
  const dk = d ? d.ko : null; const o = obj; const oj = J(obj, '을/를');
  const withDue = [
    () => `${dk} ${oj} ${verb} 부탁드립니다.`, () => `${oj} ${dk} ${verb}해 주시기 바랍니다.`, () => `${dk} ${o} ${verb} 바랍니다.`, () => `${o} ${verb} 요망 (${dk}).`,
    () => `${oj} ${dk} ${verb}해 주십시오.`, () => `${dk} ${o} ${verb} 가능할까요?`, () => `${dk} ${o} ${verb} 필요합니다.`, () => `번거로우시겠지만 ${dk} ${o} ${verb} 부탁드리겠습니다.`,
    () => `${o} 관련하여 ${dk} ${verb}해 주시면 감사하겠습니다.`, () => `${dk} ${o} ${verb} 요청드립니다.`, () => `${oj} ${dk} ${verb}하시기 바랍니다.`,
  ];
  const noDue = [
    () => `${oj} ${verb} 부탁드립니다.`, () => `${o} ${verb} 요청드립니다.`, () => `${o} ${verb} 진행 부탁드립니다.`, () => `${oj} ${verb}해 주실 수 있을까요?`, () => `${o} ${verb} 바랍니다.`,
    () => `${oj} 조속히 ${verb}해 주시기 바랍니다.`, () => `${o} 빠른 시일 내 ${verb} 부탁드립니다.`, () => `${o} ${verb} 필요합니다.`, () => `${oj} ${verb}하시기 바랍니다.`,
  ];
  const plain = [() => `${oj} ${verb} 부탁드립니다.`, () => `${o} ${verb} 요청드립니다.`, () => `${oj} ${verb}해 주실 수 있을까요?`, () => `${o} ${verb} 바랍니다.`];
  if (d && d.abs && chance(0.25)) return pick(plain)() + '\n' + pick(['기한: ', '회신 기한: ', '- 기한 : ', '※ 기한: ']) + d.dateKo;
  return d ? pick(withDue)() : pick(noDue)();
}
function enReq(obj, verb, d) {
  const o = article(obj); const de = d ? d.en : null; const pp = PP[verb] || verb + 'ed';
  const withDue = [
    () => `Please ${verb} ${o} ${de}.`, () => `Kindly ${verb} ${o} ${de}.`, () => `Could you please ${verb} ${o} ${de}?`, () => `We need you to ${verb} ${o} ${de}.`,
    () => `We would appreciate it if you could ${verb} ${o} ${de}.`, () => `I'd like you to ${verb} ${o} ${de}.`, () => `We request you to ${verb} ${o} ${de}.`,
    () => `It is required that ${o} be ${pp} ${de}.`, () => `Please make sure that ${o} is ${pp} ${de}.`, () => `${capital(de)}, please ${verb} ${o}.`, () => `Would you ${verb} ${o} ${de}?`, () => `Please arrange to ${verb} ${o} ${de}.`,
  ];
  const noDue = [
    () => `Please ${verb} ${o} ASAP.`, () => `Kindly ${verb} ${o} at your earliest convenience.`, () => `Could you please ${verb} ${o}?`, () => `Please ${verb} ${o}.`, () => `We would appreciate it if you could ${verb} ${o}.`,
    () => `Please ${verb} ${o} at the earliest.`, () => `Please ${verb} ${o} as soon as possible.`, () => `Request you to ${verb} ${o} promptly.`,
  ];
  const plain = [() => `Please ${verb} ${o}.`, () => `Could you please ${verb} ${o}?`, () => `Kindly ${verb} ${o}.`, () => `We request you to ${verb} ${o}.`];
  if (d && d.abs && chance(0.25)) return pick(plain)() + '\n' + pick(['Due date: ', 'Required by: ', 'Deadline: ']) + d.dateEn;
  return d ? pick(withDue)() : pick(noDue)();
}
// one request: returns {text, kw, due}
function makeReq(rq, lang, S, F, noRel, mixEnNoun, dGiven) {
  const d = dGiven !== undefined ? dGiven : chance(0.65) ? dueExpr(S, lang, noRel) : null;
  if (d && !d.dateKo) { d.dateKo = koDate(d.due, noRel); d.dateEn = enDate(d.due, noRel); }
  const koN = fill(rq[0], F), enN = fill(rq[2], F);
  let text, kw;
  if (lang === 'en') { text = enReq(enN, rq[3], d); kw = enN; }
  else if (lang === 'mix' && mixEnNoun) { text = koReq(enN, rq[1], d); kw = enN; }
  else if (lang === 'mix' && chance(0.3)) { text = enReq(enN, rq[3], d); kw = enN; }
  else { text = koReq(koN, rq[1], d); kw = koN; }
  return { text, kw, due: d ? d.due : '', rq, d };
}

// ---- events ----
function makeEvent(type, lang, S, noRel) {
  const nm = pick(EVENTS[type] || EVENTS.meeting); const name = lang === 'en' ? nm[1] : nm[0];
  const noTime = type === 'ship' || type === 'loop' || type === 'shutdown' || chance(0.25);
  const tm = noTime ? '' : pick(EVENT_TIMES);
  const w = dow(S); let due, dk, de; const r = noRel ? 9 : ri(0, 9);
  if (r === 0 && w >= 1 && w <= 4) { due = addDays(S, 1); dk = '내일'; de = 'tomorrow'; }
  else if (r === 1 && w >= 1 && w <= 3) { const tw = ri(w + 1, 5); due = thisWeekday(S, tw); dk = `이번 주 ${KO_DOW[tw]}요일`; de = `this ${EN_DOW[tw]}`; }
  else if (r === 2) { const tw = ri(1, 5); due = nextWeekday(S, tw); dk = `${pick(['다음 주', '차주'])} ${KO_DOW[tw]}요일`; de = `next ${EN_DOW[tw]}`; }
  else { due = addDays(S, ri(2, 35)); if (dow(due) === 0) due = addDays(due, 1); if (dow(due) === 6) due = addDays(due, 2); dk = koDate(due, noRel); de = enDate(due, noRel); }
  let text;
  if (lang === 'en') {
    const t = tm ? enTime(tm) : ''; const pl = pick(PLACES_EN); const on = /^(tomorrow|this |next )/.test(de) ? de : 'on ' + de;
    if (type === 'ship') text = pick([`Revised ${name} is ${de}.`, `${capital(name)}: ${de}`, `The ${name} is planned ${on}.`]);
    else if (!tm) text = pick([`The ${name} will start from ${de}.`, `${capital(name)} is planned ${on}.`, `${capital(name)}: ${de} (${pl})`]);
    else text = pick([`The ${name} is scheduled ${on} at ${t}.`, `${capital(name)}: ${de}, ${t} (${pl})`, `We have arranged a ${name} for ${on.replace(/^on /, '')}, ${t}.`, `The ${name} will be held ${on} at ${t} at ${pl}.`, `${capital(name)} - ${de} ${t}`]);
  } else {
    const t = tm ? koTime(tm) : ''; const pl = pick(PLACES_KO);
    if (type === 'ship') text = pick([`${name} 예정일은 ${dk}입니다.`, `${name}: ${dk}`, `${J(name, '은/는')} ${dk}로 계획되어 있습니다.`]);
    else if (!tm) text = pick([`${J(name, '은/는')} ${dk}부터 진행합니다.`, `${name} 예정일: ${dk}`, `${J(name, '은/는')} ${dk}로 예정되어 있습니다.`]);
    else text = pick([`${name}: ${dk} ${t}, ${pl}`, `${dk} ${t}에 ${pl}에서 ${J(name, '이/가')} 예정되어 있습니다.`, `${J(name, '은/는')} ${dk} ${t}로 확정되었습니다.`, `${name} 일정: ${dk} ${t} (${pl})`, `참고로 ${dk} ${t} ${name} 있습니다.`]);
  }
  return { text, due, time: tm };
}

// ---- quoted older message ----
function quoteBlock(style, lang, older, bodyLines) {
  const ko = lang !== 'en';
  const fr = `${older.from.name} <${older.from.email}>`; const to = `${older.to[0].name} <${older.to[0].email}>`;
  const S = older.S, T = older.T; const { y, m, d } = ymd(S); const h = +T.slice(0, 2), mi = +T.slice(2); const w = dow(S);
  const h12 = h > 12 ? h - 12 : h; const apE = h < 12 ? 'AM' : 'PM'; const ap = h < 12 ? '오전' : '오후';
  const body = bodyLines.join('\n');
  const v = style === 'gmail' ? 'gmail' : style === 'knox' || style === 'knox_ocr' ? 'knox' : style === 'outlook_ko' ? 'oko' : pick(['oen', 'oen', 'web', 'gmail']);
  if (v === 'gmail') return (ko && chance(0.5) ? `${y}년 ${m}월 ${d}일 (${KO_DOW[w]}) ${ap} ${h12}:${pad(mi)}, ${older.from.name} <${older.from.email}>님이 작성:` : `On ${EN_DOW3[w]}, ${EN_MON3[m - 1]} ${d}, ${y} at ${h12}:${pad(mi)} ${apE} ${fr} wrote:`) + '\n' + body.split('\n').map((l) => '> ' + l).join('\n');
  if (v === 'knox') return `--------- Original Message ---------\nSender : ${older.from.name}/${older.from.title}/${older.from.dept}/${older.from.co} <${older.from.email}>\nDate : ${y}-${pad(m)}-${pad(d)} ${pad(h)}:${pad(mi)} (GMT+09:00)\nTitle : ${older.subj}\n\n${body}`;
  if (v === 'oko') return `-----원본 메시지-----\n보낸 사람: ${fr}\n보낸 날짜: ${y}년 ${m}월 ${d}일 ${KO_DOW[w]}요일 ${ap} ${h12}:${pad(mi)}\n받는 사람: ${to}\n제목: ${older.subj}\n\n${body}`;
  if (v === 'web') return `________________________________\nFrom: ${fr}\nSent: ${EN_DOW[w]}, ${EN_MON[m - 1]} ${d}, ${y} ${h12}:${pad(mi)} ${apE}\nTo: ${to}\nSubject: ${older.subj}\n\n${body}`;
  return `-----Original Message-----\nFrom: ${fr}\nSent: ${EN_DOW[w]}, ${EN_MON[m - 1]} ${d}, ${y} ${h12}:${pad(mi)} ${apE}\nTo: ${to}\nSubject: ${older.subj}\n\n${body}`;
}

// ---- dates/times of sending ----
const S_START = '2026-09-01', S_DAYS = 113;
function sentDate() { let s = addDays(S_START, ri(0, S_DAYS)); const w = dow(s); if ((w === 0 || w === 6) && chance(0.85)) s = addDays(s, w === 6 ? 2 : 1); return s; }
function sentTime() { const h = wpick([[7, 2], [8, 6], [9, 10], [10, 10], [11, 9], [13, 8], [14, 10], [15, 9], [16, 9], [17, 8], [18, 4], [19, 2], [12, 2], [21, 1], [6, 1]]); return pad(h) + pad(ri(0, 59)); }

// ---- people for a generated mail ----
function vPerson(v, wantKo) {
  if (wantKo && !v.kor) { const s = pick(KO_SURN), g = pick(KO_GIVEN); return { name: s + g, title: pick(['과장', '부장', '차장', '대리']), dept: pick(['프로젝트팀', '기술영업팀', '영업본부']), co: v.ko || v.co, email: `${romanGiven(g)}.${ROMAN[s]}@${v.dom}`, ko: true, vendor: v, en: `${capital(romanGiven(g))} ${capital(ROMAN[s])}`, enTitle: pick(EN_TITLES) }; }
  if (!wantKo && !v.kor) { const n = pick(FOREIGN); return { name: n, title: pick(EN_TITLES), dept: v.brand, co: v.co, email: n.toLowerCase().replace(/[^a-z ]/g, '').replace(/ /g, '.') + '@' + v.dom, ko: false, vendor: v, en: n }; }
  return vendorPerson(v);
}
const NUMFMT = [(i) => `${i}. `, (i) => `${i}) `, (i) => `(${i}) `, () => '- ', () => '• ', (i) => '①②③④⑤⑥'[i - 1] + ' ', (i) => `${i}. `];
const NOTICE_KO = [
  ['[공지] 사내 문서관리시스템(EDMS) 개편 안내', ['EDMS 가 신규 버전으로 개편되었습니다.', '기존 문서번호 체계는 그대로 유지되며, 화면 구성만 일부 변경됩니다.', '사용 매뉴얼은 사내 게시판에 게시되어 있습니다.']],
  ['[안내] 계장ENG그룹 조직 변경 및 담당 업무 안내', ['조직 개편에 따라 프로젝트별 계장 담당자가 일부 변경되었습니다.', '변경된 담당자 명단은 첨부를 참고 바랍니다.', '기존 업무는 인수인계 기간 동안 병행 처리합니다.']],
  ['[공유] 계장 설계 Lessons Learned 자료 공유', ['지난 프로젝트에서 도출된 계장 설계 Lessons Learned 자료를 공유드립니다.', 'Control valve noise 및 thermowell 관련 사례가 포함되어 있습니다.', '신규 프로젝트 착수 시 참고 바랍니다.']],
];
const NOTICE_EN = [
  ['Newsletter: Rosemount product updates - Q4 2026', ['We are pleased to share our latest product updates for Q4 2026.', 'The new firmware release for the 3051S series adds enhanced diagnostics.', 'For more details, please visit our website.']],
  ['Notice: Change of bank account details? - NO CHANGE (fraud warning)', ['Please be aware of fraudulent emails requesting changes to our bank details.', 'Our bank details have NOT changed.', 'Thank you for your attention.']],
  ['Organization announcement - new Key Account Manager for Korea', ['We are pleased to announce that our Korea key account management has been reorganized.', 'All ongoing orders will continue to be handled by the same project team.', 'We look forward to continuing our cooperation.']],
];

function genMail(id, lang, style, fl) {
  const ocr = style.endsWith('_ocr'); const bst = style.replace('_ocr', ''); const nohdr = bst === 'nohdr';
  const S = sentDate(), Tm = sentTime();
  const topic = wpick(TOPICS.map((t) => [t, t.w])); const cx = makeCtx(topic); const F = cx.F; const v = cx.vendor;
  const dir = topic.dir || (fl.noreq && fl.nrType === 'commit' ? 'in' : wpick([['out', 55], ['in', 30], ['int', 15]]));
  const koSide = lang !== 'en';
  const our = koPerson(); const our2 = koPerson(); const ven = vPerson(v, koSide && chance(0.9));
  let from, to; if (dir === 'out') { from = our; to = ven; } else if (dir === 'in') { from = ven; to = our; } else { from = our; to = our2; }
  const cc = []; for (let k = ri(0, 3); k > 0; k--) cc.push(chance(0.6) ? koPerson() : vPerson(v, koSide));
  const useKo = (p) => (lang === 'ko' ? true : lang === 'en' ? false : p);
  const L = []; const reqs = []; const sched = []; const noRel = nohdr; let firstR = null;
  const tx = (ko, en, pKo = 0.75) => (useKo(chance(pKo)) ? ko : en);
  // greeting
  L.push(lang === 'en' ? greetEn(to, from) : greetKo(to, from)); if (chance(0.5)) L.push(lang === 'en' ? pick(['', `This is ${from.ko ? from.en : from.name} from ${from.ours ? OUR.coEn : v.brand}.`]) : `${from.co} ${from.ours ? from.dept + ' ' : ''}${from.name}입니다.`);
  L.push('');
  let items = cx.cats.slice(); let subjBase;
  const sKo = fill(pick(topic.sKo), F), sEn = fill(pick(topic.sEn), F);
  subjBase = lang === 'ko' ? sKo : lang === 'en' ? sEn : pick([sKo, sEn]);
  if (dir === 'in' && !topic.dir && chance(0.6)) { const a = fill(pick(['[{V}] {T} 관련 확인 요청', '{T} 제작 관련 기술 확인 요청 ({V})', '[{P}] {V} Technical Query - {T}']), F), b = fill(pick(['Technical query - {T} ({V})', '[{P}] {V} TQ-{N}: open points on {T}', 'Request for confirmation - {T}']), F); subjBase = lang === 'ko' ? a : lang === 'en' ? b : pick([a, b]); }
  const ctxPool = dir === 'in' && !topic.dir ? [INBOUND_CTX_KO, INBOUND_CTX_EN] : [topic.cKo, topic.cEn];
  const renderList = (arr) => { const nf = pick(NUMFMT); return arr.map((x, i) => '  '.slice(0, ri(0, 2)) + nf(i + 1) + x); };
  if (!fl.noreq) {
    const nc = ri(1, 2); for (const c of pickN(ctxPool[0].map((x, i) => i), nc)) L.push(tx(fill(ctxPool[0][c], F), fill(ctxPool[1][c % ctxPool[1].length], F)));
    let pool = topic.dir ? topic.req.slice() : dir === 'in' ? INBOUND_REQ.concat(topic.req.filter((r) => ['확인', '검토', '회신'].includes(r[1]))) : topic.req.slice();
    if (fl.list && dir !== 'in' && topic.li.length >= 2 && chance(0.6)) {
      // request list: intro (umbrella deadline inherited by items) + items
      const d = chance(0.45) ? dueExpr(S, lang, noRel) : null; const kIntro = useKo(chance(0.8));
      L.push(''); L.push(d ? (kIntro ? pick([`아래 사항 ${d.ko} 회신 바랍니다:`, `아래 코멘트 반영하여 ${d.ko} 회신 부탁드립니다:`, `다음 사항에 대해 ${d.ko} 조치 바랍니다.`.replace(/\.$/, ':')]) : pick([`Please address the following points ${d.en}:`, `Kindly respond to the following comments ${d.en}:`]))
        : (kIntro ? pick(['주요 코멘트는 아래와 같습니다.', '검토 의견은 다음과 같습니다:', '아래 사항 확인 부탁드립니다:', '코멘트 사항:']) : pick(['Our comments are as follows:', 'Please see our comments below:', 'Review comments:'])));
      const its = pickN(topic.li, Math.min(topic.li.length, ri(2, 4))); const out = [];
      for (const it of its) { const k = useKo(chance(0.7)); const t = fill(k ? it[0] : it[1], F); out.push(t); reqs.push({ kw: fill(k ? it[2] : it[3], F), due: d ? d.due : '' }); }
      L.push(...renderList(out));
      if (chance(0.5) && pool.length) { L.push(''); const r = makeReq(pick(pool), lang, S, F, noRel, lang === 'mix' && chance(0.5)); L.push(r.text); reqs.push({ kw: r.kw, due: r.due }); }
    } else {
      if (fl.list && topic.inf.length) {
        L.push(''); L.push(tx(pick(['주요 사양은 아래와 같습니다.', '현재 상태는 다음과 같습니다:', '참고 사항:']), pick(['Key data are as follows:', 'Current status:', 'For reference:'])));
        const inf = pickN(topic.inf, Math.min(topic.inf.length, ri(2, 3))).map((x) => fill(useKo(chance(0.7)) ? x[0] : x[1], F));
        if (chance(0.3)) L.push(...inf.map((x) => x.replace(/: /, '\t'))); else L.push(...renderList(inf));
        L.push('');
      }
      const nr = wpick([[1, 45], [2, 40], [3, 15]]); const chosen = pickN(pool, Math.min(nr, pool.length)); const bullet = chance(0.25) ? pick(['- ', '* ', '▶ ']) : '';
      for (const rq of chosen) { const r = makeReq(rq, lang, S, F, noRel, lang === 'mix' && chance(0.6)); if (!firstR) firstR = r; L.push(bullet + r.text); reqs.push({ kw: r.kw, due: r.due }); }
    }
  } else {
    const t = fl.nrType;
    if (t === 'notice') {
      const n = lang === 'en' ? pick(NOTICE_EN) : pick(NOTICE_KO); subjBase = n[0]; L.push(...n[1]); items = [];
    } else if (t === 'thanks') {
      subjBase = lang === 'en' ? pick(['Thank you - ', 'Thanks for your support - ']) + sEn : pick(['[감사] ', '감사드립니다 - ', 'RE: ']) + (lang === 'ko' ? sKo : sEn);
      L.push(tx(pick(['어제 회의에 참석해 주셔서 감사합니다.', '빠른 회신 감사드립니다.', '자료 송부해 주셔서 감사합니다. 잘 받았습니다.', '검사 기간 동안 지원해 주셔서 감사합니다.']), pick(['Thank you for your prompt reply.', 'Many thanks for attending the meeting yesterday.', 'Thank you for the documents, well received.', 'Thank you for your support during the inspection.'])));
      L.push(lang === 'en' ? commitEn(S) : commitKo(S));
    } else if (t === 'commit') {
      subjBase = (lang === 'en' ? sEn : sKo);
      L.push(tx(pick(['요청하신 건 확인하였습니다.', '네, 말씀하신 내용 확인했습니다.', '메일 잘 받았습니다.']), pick(['Noted with thanks.', 'Well received, thank you.', 'Acknowledged.'])));
      L.push(lang === 'en' ? commitEn(S) : commitKo(S));
      L.push(tx(pick(['내부 검토 후 결과 공유드리겠습니다.', '진행 상황은 수시로 업데이트 드리겠습니다.']), pick(['We will keep you updated on the progress.', 'Our engineering team is already working on it.'])));
    } else { // fyi / attached
      subjBase = (t === 'fyi' ? pick(lang === 'en' ? ['[FYI] ', 'FYI: ', ''] : ['[공유] ', '[참고] ', '']) : '') + subjBase;
      L.push(tx(fill(pick(topic.cKo), F), fill(pick(topic.cEn), F)));
      if (topic.inf.length) { L.push(''); L.push(...renderList(pickN(topic.inf, Math.min(2, topic.inf.length)).map((x) => fill(useKo(chance(0.7)) ? x[0] : x[1], F)))); L.push(''); }
      L.push(t === 'fyi' ? tx(pick(['업무에 참고 바랍니다.', '참고하시기 바랍니다.', '관련 내용 공유드립니다.', '별도 조치 사항은 없습니다.']), pick(['This is for your information only; no action is required.', 'For your information.', 'Sharing for your reference.'])) : tx('첨부와 같이 송부드리니 참고 바랍니다.', 'Please find attached the documents for your reference.'));
    }
  }
  // events
  const nev = fl.noreq && fl.nrType === 'notice' ? 0 : wpick([[0, 55], [1, 35], [2, 10]]);
  if (nev && topic.ev.length) { L.push(''); const used = new Set(); for (let k = 0; k < nev; k++) { const e = makeEvent(pick(topic.ev), lang === 'mix' ? (chance(0.7) ? 'ko' : 'en') : lang, S, noRel); const key = e.due + e.time; if (used.has(key)) continue; used.add(key); L.push(e.text); sched.push({ due: e.due, time: e.time }); } }
  // distractors
  if (chance(0.7)) { L.push(''); const dk = pickN(DISTRACT_KO, 2), de = pickN(DISTRACT_EN, 2); for (let k = ri(1, 2); k > 0; k--) L.push(tx(dk[k - 1], de[k - 1])); }
  // bilingual mix: repeat requests in English
  if (lang === 'mix' && fl.bi && !fl.noreq && firstR) {
    const en = []; en.push('', '(English below)', '', greetEn(to, from));
    const r = makeReq(firstR.rq, 'en', S, F, noRel, false, firstR.d); en.push(fill(pick(topic.cEn), F), r.text); reqs.push({ kw: r.kw, due: r.due });
    L.push(...en);
  }
  L.push(''); L.push(lang === 'en' ? sigEn(from) : (lang === 'mix' && chance(0.4) ? sigEn(from) : sigKo(from)));
  if (fl.disc) { L.push(''); L.push(pick(DISCLAIMERS)); if (chance(0.3)) L.push(pick(DISCLAIMERS)); }
  let body = L.join('\n').replace(/\n{3,}/g, '\n\n');
  // quoted thread
  let quoted = false; let subj = subjBase;
  if (fl.quoted) {
    quoted = true; const oS = addDays(S, -ri(1, 9)); const oT = sentTime();
    const older = { from: to, to: [from], S: oS, T: oT, subj: subjBase };
    const ob = [lang === 'en' ? greetEn(from, to) : greetKo(from, to), ''];
    const opool = topic.req; for (const rq of pickN(opool, ri(1, 2))) ob.push(makeReq(rq, lang === 'en' ? 'en' : 'ko', oS, F, false, false).text);
    if (chance(0.4) && topic.ev.length) ob.push(makeEvent(pick(topic.ev), lang === 'en' ? 'en' : 'ko', oS, false).text);
    ob.push('', lang === 'en' ? `Regards,\n${to.ko ? to.en : to.name}` : `${to.name} 드림`);
    subj = (bst === 'gmail' ? pick(['Re: ', 'RE: ']) : lang === 'en' ? pick(['RE: ', 'RE: ', 'Re: ', 'RE: RE: ', 'FW: ']) : pick(['RE: ', '회신: ', 'RE: ', '답장: ', 'FW: ', '전달: '])) + subjBase;
    body += '\n\n' + quoteBlock(bst, lang, older, ob);
  } else if (fl.noreq && chance(0.3)) subj = subjBase;
  if (!fl.noreq && chance(0.08)) subj = pick(['[긴급] ', '[Urgent] ', 'URGENT: ', '[중요] ']) + subj;
  if (dir === 'in' && chance(0.12)) subj = pick(['[EXT] ', '[External] ', '[외부메일] ']) + subj;
  const msg = { from, to: [to], cc, subj, S, T: Tm, att: chance(0.4) ? [`${F.DOC}_Rev${F.R}.pdf`, `${F.T}_comments.xlsx`].slice(0, ri(1, 2)) : null };
  const text = nohdr ? body : header(bst, lang, msg, ocr) + '\n\n' + body;
  const gold = { subj: nohdr ? '' : subj, from: nohdr ? '' : from.name, date: nohdr ? '' : S, time: nohdr ? '' : Tm, reqs, sched, items: [...new Set(items)], noreq: reqs.length === 0 };
  return { id, lang, style, text, gold, _q: quoted, _list: !!fl.list && !fl.noreq || false, _disc: !!fl.disc };
}

// =====================================================================================
// MAIN
// =====================================================================================
function handRecords() {
  return HAND.map((h, i) => ({ id: 'h' + (i + 1), lang: h.lang, style: h.style, text: h.text,
    gold: { subj: h.subj, from: h.from, date: h.date, time: h.time, reqs: h.r.map(([kw, due]) => ({ kw, due })), sched: h.s.map(([due, time]) => ({ due, time })), items: h.items, noreq: h.r.length === 0 } }));
}
const STYLES = ['knox', 'outlook_ko', 'outlook_en', 'gmail', 'notes', 'nohdr'];
function main() {
  const out = handRecords().slice(0, Math.min(HAND.length, N));
  const left = N - out.length;
  // quotas for generated part (whole set aims at ko 45 / en 40 / mix 15, 12% noreq, 20% quoted, 30% lists, 25% disclaimer)
  const langs = []; const nk = Math.round(left * 0.45), ne = Math.round(left * 0.40); for (let i = 0; i < left; i++) langs.push(i < nk ? 'ko' : i < nk + ne ? 'en' : 'mix');
  const lg = shuffle(langs); const st = shuffle(Array.from({ length: left }, (_, i) => STYLES[i % STYLES.length]));
  for (let i = 0; i < left; i++) {
    let style = st[i]; if ((style === 'knox' || style === 'gmail') && chance(0.25)) style += '_ocr';
    const noreq = chance(0.12); const nrType = noreq ? wpick([['fyi', 35], ['thanks', 20], ['commit', 25], ['notice', 10], ['attached', 10]]) : null;
    const fl = { noreq, nrType, quoted: nrType === 'commit' ? chance(0.8) : chance(0.19), list: chance(0.27), disc: chance(0.25), bi: chance(0.2) };
    out.push(genMail('g' + (out.length + 1), lg[i], style, fl));
  }
  return out;
}

// ---- self checks ----
function quoteStart(t) { const m = t.search(/\n(-----Original Message-----|-----원본 메시지-----|--------- Original Message ---------|________________________________\nFrom:|---------- Forwarded message|On [A-Z][a-z]{2}, [A-Z][a-z]{2} \d+, \d{4} at .* wrote:|\d{4}년 \d+월 \d+일 .*님이 작성:)/); return m < 0 ? t.length : m; }
function checkDows(r) {
  const errs = []; const t = r.text; const yr0 = r.gold.date ? +r.gold.date.slice(0, 4) : 2026; const ko = '일월화수목금토';
  const chk = (y, m, d, w, s) => { if (m < 1 || m > 12 || d < 1 || d > 31) return; let iso2 = `${y}-${pad(m)}-${pad(d)}`; if (r.gold.date && diffDays(iso2, r.gold.date) > 60) iso2 = `${y + 1}-${pad(m)}-${pad(d)}`; if (dow(iso2) !== w) errs.push(s); };
  for (const mm of t.matchAll(/(?:(\d{4})[.\-\/년]\s?)?(\d{1,2})[월.\-\/]\s?(\d{1,2})일?\.?\s?\(([월화수목금토일])\)/g)) chk(mm[1] ? +mm[1] : yr0, +mm[2], +mm[3], ko.indexOf(mm[4]), mm[0]);
  for (const mm of t.matchAll(/(\d{4})년 (\d{1,2})월 (\d{1,2})일 ([월화수목금토일])요일/g)) chk(+mm[1], +mm[2], +mm[3], ko.indexOf(mm[4]), mm[0]);
  for (const mm of t.matchAll(/(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sun|Mon|Tue|Wed|Thu|Fri|Sat),? (\d{1,2})(?:st|nd|rd|th)? (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?(?:,? (20\d{2}))?/g)) chk(mm[4] ? +mm[4] : yr0, EN_MON3.indexOf(mm[3]) + 1, +mm[2], EN_DOW3.indexOf(mm[1].slice(0, 3)), mm[0]);
  for (const mm of t.matchAll(/(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sun|Mon|Tue|Wed|Thu|Fri|Sat),? (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2})(?:st|nd|rd|th)?(?:,? (20\d{2}))?/g)) chk(mm[4] ? +mm[4] : yr0, EN_MON3.indexOf(mm[2]) + 1, +mm[3], EN_DOW3.indexOf(mm[1].slice(0, 3)), mm[0]);
  for (const mm of t.matchAll(/(\d{4})-(\d{2})-(\d{2}) \(([월화수목금토일])\)/g)) chk(+mm[1], +mm[2], +mm[3], ko.indexOf(mm[4]), mm[0]);
  return errs;
}
function selfCheck(recs) {
  let bad = 0;
  for (const r of recs) {
    const qs = quoteStart(r.text); const newest = r.text.slice(0, qs); const probs = [];
    for (const q of r.gold.reqs) { if (!newest.includes(q.kw)) probs.push('kw not in newest: ' + q.kw); if (q.due && r.gold.date && q.due < r.gold.date) probs.push('due before sent: ' + q.due); }
    for (const e of r.gold.sched) { if (!/^\d{4}-\d{2}-\d{2}$/.test(e.due)) probs.push('bad sched date'); if (r.gold.date && e.due < r.gold.date) probs.push('event before sent ' + e.due); }
    if (r.gold.subj && !r.text.includes(r.gold.subj)) probs.push('subj not in text');
    if (r.gold.from && !r.text.slice(0, 800).includes(r.gold.from)) probs.push('from not in header');
    probs.push(...checkDows(r).map((x) => 'dow mismatch: ' + x));
    if (probs.length) { bad++; if (bad <= 15) console.log('[CHECK]', r.id, probs.join(' | ')); }
  }
  console.log(`self-check: ${bad} record(s) with problems`);
}

const recs = main();
selfCheck(recs);
const clean = recs.map(({ id, lang, style, text, gold }) => ({ id, lang, style, text, gold }));
fs.writeFileSync(path.join(__dirname, 'ic_mails.json'), JSON.stringify(clean, null, 1), 'utf8');
// ---- stats ----
const cnt = (f) => { const m = {}; for (const r of recs) { const k = f(r); m[k] = (m[k] || 0) + 1; } return m; };
const isQ = (r) => r._q !== undefined ? r._q : quoteStart(r.text) < r.text.length;
const isL = (r) => /\n\s*(\(?1[.)]|①|- |• )/.test(r.text.slice(0, quoteStart(r.text)));
const isD = (r) => /CONFIDENTIAL|DISCLAIMER|scanned|영업비밀|보안 정책|발신전용|EXTERNAL\]|consider the environment|trademarks/.test(r.text);
console.log(`wrote ${clean.length} mails -> ${path.join(__dirname, 'ic_mails.json')}`);
console.log('by lang :', JSON.stringify(cnt((r) => r.lang)));
console.log('by style:', JSON.stringify(cnt((r) => r.style)));
console.log('noreq   :', recs.filter((r) => r.gold.noreq).length, ' quoted:', recs.filter(isQ).length, ' lists:', recs.filter(isL).length, ' disclaimer:', recs.filter(isD).length,
  ' with sched:', recs.filter((r) => r.gold.sched.length).length, ' reqs total:', recs.reduce((a, r) => a + r.gold.reqs.length, 0), ' reqs w/ due:', recs.reduce((a, r) => a + r.gold.reqs.filter((q) => q.due).length, 0));
if (process.env.SHOW !== '0') {
  for (const lg of ['ko', 'en', 'mix']) { const r = recs.find((x) => x.lang === lg && x.id.startsWith('g') && x.style !== 'nohdr' && x.gold.reqs.length >= 2 && x.gold.sched.length); if (!r) continue; console.log(`\n==================== sample ${r.id} (${r.lang}, ${r.style}) ====================\n${r.text}\n--- gold ---\n${JSON.stringify(r.gold, null, 1)}`); }
}
