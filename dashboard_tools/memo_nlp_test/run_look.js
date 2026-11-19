// 불러오기 창 '말로 모양 바꾸기'(mmPullLook) 시험 — node run_look.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const h = fs.readFileSync(path.join(__dirname, '..', '..', 'dashboard', 'dashboard.html'), 'utf8');
const a = h.indexOf('const MM_PFF'), b = h.indexOf('async function mmPull2('); const ctx = {}; vm.createContext(ctx); vm.runInContext(h.slice(a, b) + ';this.f = mmPullLook;', ctx);
const T = [['CO2 TBE 일정 컨트롤 밸브 아이템 테이블로 굴림 12pt 머리 파랑 줄무늬', { ff:'u', fs:'16', hc:'#2b44c9', zb:true }, 'CO2 TBE 일정 컨트롤 밸브 아이템 테이블로'], ['글자 크게 해줘', { fs:'16' }, ''], ['굴림체로 바꿔줘', { ff:'u' }, ''], ['맑은 고딕 11px로', { ff:'g', fs:'11' }, ''],
  ['테두리 없이 가운데 정렬', { bd:'n', al:'c' }, ''], ['헤더 색 노랑으로, 가로 꽉 차게', { hc:'#fdecc8', w:true }, ''], ['파란 머리 촘촘하게', { hc:'#2b44c9', cp:true }, ''], ['출처 줄 빼고 제목 굵게', { from:false, tb:true }, ''], ['수행 진행 중인 PJT 표로', {}, '수행 진행 중인 PJT 표로'],
  ['이슈 김철수 담당 미결 할 일로', {}, null], ['MOV 아이템 일정 가져와', {}, null], ['작은 글씨로 가로선만', { fs:'11', bd:'h' }, ''], ['줄무늬 빼고 오른쪽 정렬', { zb:false, al:'r' }, ''], ['고정폭 글꼴 10pt', { ff:'m', fs:'13' }, ''], ['바탕체 명조', { ff:'b' }, ''],
  ['FAT 일정 전망 테이블', {}, null], ['고딕으로 14 px', { ff:'g', fs:'14' }, ''], ['통합 업무 진행 중인 것 목록으로 돋움 15px 제목 굵게', { ff:'d', fs:'15', tb:true }, '통합 업무 진행 중인 것 목록으로'], ['글씨 아주 크게', { fs:'18' }, ''], ['남색 헤더 테두리 굵게', { hc:'#1f2a44', bd:'b' }, '']];
let ok = 0; for (const [q, exp, rest] of T) { const r = ctx.f(q); const pass = Object.keys(exp).every(k => r.lk[k] === exp[k]) && Object.keys(r.lk).length === Object.keys(exp).length && (rest === null || r.rest === rest); ok += pass; if (!pass) console.log('XX', q, '→', JSON.stringify(r.lk), '| 나머지:', r.rest); }
console.log(`말로 모양 바꾸기 ${ok}/${T.length}`); process.exitCode = ok === T.length ? 0 : 1;
