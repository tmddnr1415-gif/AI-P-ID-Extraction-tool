// Work with spec JSON without a browser (for the Claude skill and CI).
//
//   node ic-3d-builder/dev/spec.mjs presets                         list presets
//   node ic-3d-builder/dev/spec.mjs params [valve|cabinet|hookup]   parameter dictionary (markdown)
//   node ic-3d-builder/dev/spec.mjs catalog [type]                  part ids (to link a drawing parts list)
//   node ic-3d-builder/dev/spec.mjs template <preset> [out.json]    empty spec
//   node ic-3d-builder/dev/spec.mjs check <spec.json>               values, sources, BOM, checks, envelope; exit 1 on errors
import { createRequire } from 'node:module';
import fs from 'node:fs';

const require = createRequire(import.meta.url);
global.RefData = require('../src/refdata.js');
const Anatomy = require('../src/anatomy.js');

const [cmd, a1, a2] = process.argv.slice(2);
const SRC = { drawing: 'drawing', user: 'user', standard: 'standard', estimate: 'estimate', default: 'default', none: '-' };

function params(types) {
  const L = [];
  for (const t of types) {
    const T = Anatomy.TYPES[t];
    L.push(`## \`${t}\` — ${T.label}`, '', '| key | unit | options | meaning |', '|---|---|---|---|');
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
} else if (cmd === 'catalog') {
  for (const t of a1 ? [a1] : Object.keys(Anatomy.TYPES)) for (const p of Anatomy.partCatalog(t)) console.log(`${t.padEnd(8)} ${p.id.padEnd(20)} ${p.name}`);
} else if (cmd === 'template') {
  const p = Anatomy.PRESETS.find((x) => x.id === a1);
  if (!p) { console.error(`No preset ${a1}. List them with: presets`); process.exit(1); }
  const inputs = Object.fromEntries(Object.entries(p.set).map(([k, v]) => [k, { value: v, src: 'default' }]));
  const spec = { tool: 'ic-3d-builder', version: 2, type: p.type, preset: p.id, inputs, parts_list: [], extraction: null };
  const s = JSON.stringify(spec, null, 2);
  if (a2) { fs.writeFileSync(a2, s); console.log(`→ ${a2}`); } else console.log(s);
} else if (cmd === 'check') {
  const spec = JSON.parse(fs.readFileSync(a1, 'utf8'));
  const T = Anatomy.TYPES[spec.type];
  if (!T) { console.error('type must be valve / cabinet / hookup'); process.exit(1); }
  const keys = new Set(T.params.map((p) => p.key));
  const unknown = Object.keys(spec.inputs || {}).filter((k) => !keys.has(k));
  const m = Anatomy.build(spec);
  const bad = [];
  console.log(`# ${spec.type} / ${spec.preset || '-'}`);
  for (const p of T.params) {
    const meta = m.meta[p.key];
    if (!meta.active) continue;
    const v = m.values[p.key];
    if (p.type === 'num' && v !== undefined && !(Number.isFinite(v))) bad.push(`${p.key} is not a number: ${v}`);
    if (p.type === 'enum' && v !== undefined && !p.options.includes(String(v))) bad.push(`${p.key} not one of the options: ${v}`);
    const note = meta.evidence || meta.ref || '';
    console.log(`${p.key.padEnd(14)} ${String(v ?? '').padEnd(12)} ${(SRC[meta.src] || meta.src).padEnd(4)} ${note}`);
  }
  console.log('\n# Parts (BOM)');
  for (const p of m.parts.filter((x) => x.no != null)) {
    const mat = p.dwgMaterial ? `${p.dwgMaterial} [drawing]` : `${p.material} [typical]`;
    const dims = p.dims.map((d) => `${d.k} ${d.v}${d.unit ? ' ' + d.unit : ''} [${d.src}]`).join('; ');
    console.log(`${String(p.no).padStart(3)}  ${(p.dwgName || p.name).padEnd(36)} ${mat}${dims ? '\n       ' + dims : ''}`);
  }
  const ids = new Set(m.parts.map((x) => x.id));
  const badRows = (spec.parts_list || []).filter((r) => r.part_id && r.part_id !== 'none' && !ids.has(r.part_id));
  for (const r of badRows) console.log(`⚠ parts_list row ${r.item_no} ${r.name}: part_id "${r.part_id}" is not in this model`);
  console.log(`\nEnvelope L×W×H: ${m.bbox.size.map((x) => Math.round(x)).join(' × ')} mm · ${m.parts.length} parts`);
  const cnt = {};
  for (const x of Object.values(m.meta)) if (x.active) cnt[x.src] = (cnt[x.src] || 0) + 1;
  console.log('Sources:', Object.entries(cnt).map(([k, n]) => `${SRC[k] || k} ${n}`).join(' · '));
  for (const w of m.warnings) console.log(`⚠ ${w}`);
  if (unknown.length) console.log(`⚠ unknown keys (ignored): ${unknown.join(', ')}`);
  for (const b of bad) console.log(`✗ ${b}`);
  process.exit(bad.length ? 1 : 0);
} else {
  console.log('usage: spec.mjs presets | params [type] | catalog [type] | template <preset> [out] | check <spec.json>');
  process.exit(cmd ? 1 : 0);
}
