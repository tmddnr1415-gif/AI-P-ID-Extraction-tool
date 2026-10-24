// 계장도서검토 검색 품질 시뮬레이션 (개발용 — 배포 zip 에 넣지 않음)
//
// 준비: 대시보드 서버(server.py + books_api.py)를 띄우고 공용 도서관 폴더를 시험 도서 폴더로 정함
//   python server.py --root <운영폴더> --port 8790 --plaza-port 0
//   curl -X PUT -H "Content-Type: application/json" -d "{\"root\":\"<시험 도서 폴더>\"}" http://127.0.0.1:8790/api/books/root
// 실행 (Playwright 의 chromium 필요):
//   node sim.js index          서버 폴더를 색인 (운영자 = localhost 로 접속)
//   node sim.js dev            조정용 질문(queries_dev.json, 라벨 = corpus_manifest.json) 채점
//   node sim.js test           따로 둔 질문(queries_test.json, 라벨 = 파일 이름 일부) 채점
//   node sim.js pp             발전 · 플랜트 계장 질문(queries_pp.json) 채점
//   node sim.js tune [N]       CFG 가중치 N 가지 시험 → 상위 결과 (조정 후 test 로 나빠지지 않았는지 확인할 것)
//   CFG='{"wFrac":5}' node sim.js dev     가중치를 바꿔 채점
// 주소: BOOKS_URL (기본 http://127.0.0.1:8790/apps/books/index.html?embed=1)
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const URL = process.env.BOOKS_URL || 'http://127.0.0.1:8790/apps/books/index.html?embed=1';
const here = f => path.join(__dirname, f);
const [mode = 'dev', arg] = process.argv.slice(2);
const CFG = JSON.parse(process.env.CFG || '{}');

async function openApp(b) {
  const p = await b.newPage();
  p.on('pageerror', e => console.error('page error:', String(e)));
  await p.goto(URL);
  // 공용 도서관을 다 불러올 때까지 (도서관이 비어 있으면 색인 모드에서만 계속)
  await p.waitForFunction(m => window.BOOKS && window.BOOKS.SRV.info && (window.BOOKS.LIB.books.length > 0 || (m === 'index' && !window.BOOKS.SRV.info.count)) && document.querySelector('#prog').hidden, mode, { timeout: 600000, polling: 500 });
  return p;
}
// 질문 묶음 → [{q, lab:{rel→등급}, ideal:[등급…]}]
function items(kind) {
  if (kind === 'dev') {
    const man = JSON.parse(fs.readFileSync(here('corpus_manifest.json'), 'utf8')).files, Q = JSON.parse(fs.readFileSync(here('queries_dev.json'), 'utf8'));
    return Object.entries(Q).flatMap(([base, qs]) => qs.map(q => ({ q, base, rules: man.map(e => [e.path, e.labels[base] || 0, e.category || '']).filter(x => x[1] || x[2].startsWith('distractor')), exact: true })));
  }
  const T = JSON.parse(fs.readFileSync(here(kind === 'pp' ? 'queries_pp.json' : 'queries_test.json'), 'utf8'));   // pp = 발전 · 플랜트 질문 (파일 이름 일부 → 등급)
  return Object.entries(T).map(([q, lab]) => ({ q, base: q, rules: Object.entries(lab).map(([k, v]) => [k, v, '']), exact: false, pp: kind === 'pp' }));
}
// 브라우저 안에서 채점 (CFG 만 바꿔 여러 번 돌려도 일치 결과는 앱이 보관해 빠름)
const SCORE = ({ its, cfgs }) => {
  const BK = window.BOOKS, base = { ...BK.CFG }, out = [];
  for (const cfg of cfgs) {
    Object.assign(BK.CFG, base, cfg); let nd = 0, mrr = 0, dis = 0; const per = [];
    for (const it of its) {
      const grade = rel => { for (const [k, v] of it.rules) if (it.exact ? rel.endsWith('/' + k) : rel.includes(k)) return v; return 0; };
      const isDis = rel => it.rules.some(([k, v, c]) => c.startsWith('distractor') && !v && rel.endsWith('/' + k));
      const ideal = it.rules.map(r => r[1]).filter(Boolean).sort((a, b) => b - a), idcg = ideal.slice(0, 10).reduce((a, g, i) => a + (2 ** g - 1) / Math.log2(i + 2), 0);
      const s = BK.search(it.q, {}), top = s.results.filter(R => it.pp || !/\/설계문서\//.test(R.B.rel)).slice(0, 10).map(R => R.B.rel), g = top.map(grade);   // 조정 · 시험 묶음에는 라벨이 없는 설계문서 폴더(xlsx · pptx 시험 파일)를 빼고 채점
      const dcg = g.reduce((a, x, i) => a + (2 ** x - 1) / Math.log2(i + 2), 0), f = g.findIndex(x => x >= Math.min(2, ideal[0] || 0));
      nd += idcg ? dcg / idcg : 0; mrr += f >= 0 ? 1 / (f + 1) : 0; dis += top.slice(0, 5).filter(isDis).length;
      per.push({ q: it.q, nd: idcg ? +(dcg / idcg).toFixed(2) : 0, interp: s.Q.qs.map(x => (x.main ? '' : '~') + x.label), top3: top.slice(0, 3).map((x, i) => g[i] + '|' + x.split('/').pop().slice(0, 34)) });
    }
    const n = its.length; out.push({ cfg, nd: nd / n, mrr: mrr / n, dis: dis / n, obj: nd / n + 0.5 * mrr / n - 0.15 * dis / n, per });
  }
  Object.assign(BK.CFG, base); return out;
};
const fmt = x => `nDCG@10 ${x.nd.toFixed(3)} · MRR ${x.mrr.toFixed(3)} · 상위5 방해도서 ${x.dis.toFixed(2)}`;

(async () => {
  const b = await chromium.launch();
  const p = await openApp(b);
  if (mode === 'index') {
    const t0 = Date.now();
    await p.evaluate(full => { window.BOOKS.srvIndex(full); }, arg === 'full');
    await p.waitForFunction(() => window.BOOKS.RUN.busy, null, { timeout: 60000 }).catch(() => {});
    while (await p.evaluate(() => window.BOOKS.RUN.busy)) { await p.waitForTimeout(3000); process.stdout.write('\r' + await p.textContent('#progText')); }
    console.log(`\n색인 끝: ${(Date.now() - t0) / 1000}초 · ${await p.evaluate(() => window.BOOKS.LIB.books.length)}권`);
  } else if (mode === 'tune') {
    const its = items('dev'), N = +(arg || 200);
    const space = { b: [0.3, 0.5, 0.75], top: [3, 5, 8], wDepth: [0.5, 1, 1.5], wLog: [0, 0.25, 0.55, 1], wFrac: [1.5, 3, 5, 8], wHead: [0.8, 1.6, 2.5], wTitle: [2, 3.2, 5], domA: [0.4, 0.55, 0.75], cover: [0.3, 0.6, 1], miss: [0.3, 0.45, 0.7], aspW: [0.15, 0.3, 0.5], genW: [0.2, 0.35, 0.6], parentW: [0.15, 0.3, 0.5], freeW: [0.3, 0.6, 1], senseA: [0.2, 0.35, 0.5] };
    let seed = 12345; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647, keys = Object.keys(space);
    let best = (await p.evaluate(SCORE, { its, cfgs: [CFG] }))[0]; const all = [best]; console.log('지금 값  ', fmt(best));
    for (let i = 0; i < N; i++) {   // 절반 = 가장 좋은 값 주변(두 개만 바꿈), 절반 = 무작위
      const c = { ...(i % 2 ? best.cfg : {}) };
      if (i % 2) for (let k = 0; k < 2; k++) { const key = keys[Math.floor(rnd() * keys.length)]; c[key] = space[key][Math.floor(rnd() * space[key].length)]; }
      else for (const key of keys) c[key] = space[key][Math.floor(rnd() * space[key].length)];
      const r = (await p.evaluate(SCORE, { its, cfgs: [c] }))[0]; all.push(r); if (r.obj > best.obj) best = r;
    }
    all.sort((a, b) => b.obj - a.obj);
    all.slice(0, 8).forEach(x => console.log('후보     ', fmt(x), JSON.stringify(x.cfg)));
    console.log('\n→ 후보를 CFG=... node sim.js test 로 따로 둔 질문에서도 확인한 뒤 index.html 의 CFG 에 반영');
  } else {
    const r = (await p.evaluate(SCORE, { its: items(mode), cfgs: [CFG] }))[0];
    if (process.env.V) r.per.forEach(x => console.log(x.nd.toFixed(2), x.q.padEnd(28), JSON.stringify(x.interp), x.top3.join(' / ')));
    console.log(`${mode === 'dev' ? '조정용' : mode === 'pp' ? '발전 · 플랜트' : '시험용'} 질문 ${r.per.length}개 — ${fmt(r)}`);
  }
  await b.close();
})();
