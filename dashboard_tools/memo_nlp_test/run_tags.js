// 메일 · 메모의 계기 태그 · 표준 번호 찾기(mmMailTags · mmMailCodes) 시험 — node run_tags.js
const { mmMailTags, mmMailCodes } = require('./nlp.js');
const T = [['FT-1201, PT 3105A, LT-210 and TT-4501', ['FT-1201:Flow Meter', 'PT-3105A:Transmitter', 'LT-210:Level', 'TT-4501:Transmitter']],
  ['FCV-1101 / XV-2003 / MOV-5101 / PSV-7701 / AT-901 / GD-1203 / JB-105', ['FCV-1101:Control Valve', 'XV-2003:On/Off Valve', 'MOV-5101:MOV', 'PSV-7701:PSV', 'AT-901:Analyzer', 'GD-1203:F&G', 'JB-105:Cable/JB']],
  ['98FV-100, 98FV100, 00XV921, ESDV-3001', ['98FV-100:Control Valve', '00XV-921:On/Off Valve', 'ESDV-3001:On/Off Valve']],
  ['PO 4500012345, CL 300, DN 50, SCH 40, TEL 02-1234, ITEM 10, Rev.0, CO2 PJT, 2026-11-18, ISO 9001', []],
  ['per ASME PTC 19.3 TW-2016 for TW-4501', ['TW-4501:Transmitter']], ['FAT-01 PJT-2 RFQ-1234 VDR-001', []], ['HV-101 FIT-200 PDT-300 TE-101 PG-501', ['HV-101:On/Off Valve', 'FIT-200:Flow Meter', 'PDT-300:Transmitter', 'TE-101:Transmitter', 'PG-501:Transmitter']]];
const C = [['API 6D, ISO 9001, IEC 61511-1, ASME B16.34, EN 10204 3.1, NAMUR NE43', ['API 6D', 'ISO 9001', 'IEC 61511-1', 'ASME B16.34', 'EN 10204', 'NAMUR NE43']], ['ANSI/FCI 70-2 Class V, ASME PTC 19.3 TW-2016', ['FCI 70-2', 'ASME PTC 19.3']], ['EN 2026 ISO 9 BS 2026', []]];
let ok = 0, n = 0; for (const [q, e] of T) { n++; const g = mmMailTags(q).map(x => x.tag + ':' + x.cat); if (JSON.stringify(g) === JSON.stringify(e)) ok++; else console.log('XX 태그', q, '→', g); }
for (const [q, e] of C) { n++; const g = mmMailCodes(q); if (JSON.stringify(g) === JSON.stringify(e)) ok++; else console.log('XX 표준', q, '→', g); }
console.log(`태그 · 표준 찾기 ${ok}/${n}`); process.exitCode = ok === n ? 0 : 1;
