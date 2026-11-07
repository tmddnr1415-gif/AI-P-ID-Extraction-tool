// 스펙 JSON 을 브라우저 없이 다룬다 (Claude 스킬·CI 용).
//
//   node ic-3d-builder/dev/spec.mjs presets                  프리셋 목록
//   node ic-3d-builder/dev/spec.mjs params [valve|cabinet|hookup]   파라미터 사전 (markdown)
//   node ic-3d-builder/dev/spec.mjs template <preset> [out.json]    빈 스펙 만들기
//   node ic-3d-builder/dev/spec.mjs check <spec.json>        값·출처·점검·외곽치수 출력. 오류면 exit 1
import { createRequire } from 'node:module';
import fs from 'node:fs';

const require = createRequire(import.meta.url);
global.RefData = require('../src/refdata.js');
const Anatomy = require('../src/anatomy.js');

const [cmd, a1, a2] = process.argv.slice(2);
const SRC = { drawing: '도면', user: '입력', standard: '표준', estimate: '추정', default: '기본', none: '-' };

function params(types) {
  const L = [];
  for (const t of types) {
    const T = Anatomy.TYPES[t];
    L.push(`## \`${t}\` — ${T.label}`, '', '| key | 단위 | 선택지 | 의미 |', '|---|---|---|---|');
    for (const p of T.params) {
      L.push(`| \`${p.key}\` | ${p.unit || ''} | ${p.options ? p.options.join(', ') : p.type === 'bool' ? 'true, false' : ''} | ${p.label}${p.desc ? ' — ' + p.desc : ''} |`);
    }
    L.push('');
  }
  return L.join('\n');
}

if (cmd === 'presets') {
  for (const p of Anatomy.PRESETS) console.log(`${p.id.padEnd(10)} ${p.type.padEnd(8)} ${p.label}`);
} else if (cmd === 'params') {
  console.log(params(a1 ? [a1] : Object.keys(Anatomy.TYPES)));
} else if (cmd === 'template') {
  const p = Anatomy.PRESETS.find((x) => x.id === a1);
  if (!p) { console.error(`프리셋 없음: ${a1}. presets 로 목록을 보세요.`); process.exit(1); }
  const inputs = Object.fromEntries(Object.entries(p.set).map(([k, v]) => [k, { value: v, src: 'default' }]));
  const spec = { tool: 'ic-3d-builder', version: 1, type: p.type, preset: p.id, inputs, extraction: null };
  const s = JSON.stringify(spec, null, 2);
  if (a2) { fs.writeFileSync(a2, s); console.log(`→ ${a2}`); } else console.log(s);
} else if (cmd === 'check') {
  const spec = JSON.parse(fs.readFileSync(a1, 'utf8'));
  const T = Anatomy.TYPES[spec.type];
  if (!T) { console.error('type 은 valve / cabinet / hookup 중 하나'); process.exit(1); }
  const keys = new Set(T.params.map((p) => p.key));
  const unknown = Object.keys(spec.inputs || {}).filter((k) => !keys.has(k));
  const m = Anatomy.build(spec);
  const bad = [];
  console.log(`# ${spec.type} / ${spec.preset || '-'}`);
  for (const p of T.params) {
    const meta = m.meta[p.key];
    if (!meta.active) continue;
    const v = m.values[p.key];
    if (p.type === 'num' && v !== undefined && !(Number.isFinite(v))) bad.push(`${p.key} 숫자 아님: ${v}`);
    if (p.type === 'enum' && v !== undefined && !p.options.includes(String(v))) bad.push(`${p.key} 선택지 밖: ${v}`);
    const note = meta.evidence || meta.ref || '';
    console.log(`${p.key.padEnd(14)} ${String(v ?? '').padEnd(12)} ${(SRC[meta.src] || meta.src).padEnd(4)} ${note}`);
  }
  console.log(`\n외곽 L×W×H: ${m.bbox.size.map((x) => Math.round(x)).join(' × ')} mm · 부품 ${m.parts.length}개`);
  const cnt = {};
  for (const x of Object.values(m.meta)) if (x.active) cnt[x.src] = (cnt[x.src] || 0) + 1;
  console.log('출처:', Object.entries(cnt).map(([k, n]) => `${SRC[k] || k} ${n}`).join(' · '));
  for (const w of m.warnings) console.log(`⚠ ${w}`);
  if (unknown.length) console.log(`⚠ 사전에 없는 key (무시됨): ${unknown.join(', ')}`);
  for (const b of bad) console.log(`✗ ${b}`);
  process.exit(bad.length ? 1 : 0);
} else {
  console.log('사용법: spec.mjs presets | params [type] | template <preset> [out] | check <spec.json>');
  process.exit(cmd ? 1 : 0);
}
