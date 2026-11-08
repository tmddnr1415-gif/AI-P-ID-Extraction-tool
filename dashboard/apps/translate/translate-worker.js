/* 대시보드 클로드 비서 번역 워커 (2026-11-08) — 브라우저 안에서만 동작, 서버 · 인터넷으로 글을 보내지 않음
 *  엔진: fxtranslate 0.5.0 wasm(MPL-2.0)  ·  모델: Mozilla Firefox Translations (ko-en · en-ko, base-memory)
 *  받는 메시지: {id, type:'load', dir:'enko'|'koen'}  ·  {id, type:'translate', dir, text}
 *  보내는 메시지: {id, ok, result} · {id, progress:{step, pct}} · {id, ok:false, error} */
importScripts('fx/fxtranslate_wasm.js');
const BASE = self.location.href.replace(/[^/]*$/, '');
const FILES = { enko:{ model:'model.enko.intgemm.alphas.bin.gz', src:'srcvocab.enko.spm.gz', trg:'trgvocab.enko.spm.gz', lex:'lex.50.50.enko.s2t.bin.gz' },
                koen:{ model:'model.koen.intgemm.alphas.bin.gz', src:'vocab.koen.spm.gz', trg:'vocab.koen.spm.gz', lex:'lex.50.50.koen.s2t.bin.gz' } };
const T = {}; let inited = null;
async function getGz(url, onPct) {                           // .gz 받아서 브라우저 내장 해제
  const r = await fetch(url, { cache:'force-cache' }); if (!r.ok) throw new Error(url.split('/').pop() + ' ' + r.status);
  const total = +r.headers.get('content-length') || 0; let got = 0; const chunks = [];
  const reader = r.body.pipeThrough(new DecompressionStream('gzip')).getReader();
  for (;;) { const { done, value } = await reader.read(); if (done) break; chunks.push(value); got += value.length; if (onPct) onPct(total ? Math.min(99, Math.round(got / (total * 1.1) * 100)) : 0); }
  const out = new Uint8Array(got); let o = 0; for (const c of chunks) { out.set(c, o); o += c.length; } return out;
}
async function load(dir, id) {
  if (T[dir]) return true; const f = FILES[dir]; if (!f) throw new Error('방향 ' + dir);
  if (!inited) inited = FxTranslate.init(BASE + 'fx/fxtranslate_wasm_bg.wasm'); await inited;
  const prog = (step, pct) => postMessage({ id, progress:{ step, pct } });
  const model = await getGz(`${BASE}models/${dir}/${f.model}`, p => prog('모델', p));
  const src = await getGz(`${BASE}models/${dir}/${f.src}`), trg = f.trg === f.src ? src : await getGz(`${BASE}models/${dir}/${f.trg}`), lex = await getGz(`${BASE}models/${dir}/${f.lex}`, p => prog('사전', p));
  T[dir] = new FxTranslate.Translator(model, src, trg, lex); return true;
}
onmessage = async e => { const d = e.data || {};
  try {
    if (d.type === 'load') { await load(d.dir, d.id); return postMessage({ id:d.id, ok:true, result:true }); }
    if (d.type === 'translate') { await load(d.dir, d.id); const t = T[d.dir];
      const paras = String(d.text).split(/\n{2,}/), out = paras.map(p => p.split('\n').map(line => line.trim() ? t.translate_long(line.trim()) : '').join('\n'));
      return postMessage({ id:d.id, ok:true, result:out.join('\n\n') }); }
    postMessage({ id:d.id, ok:false, error:'unknown ' + d.type });
  } catch (err) { postMessage({ id:d.id, ok:false, error:String(err && err.message || err) }); } };
