// 비서 의도 분류기 — 글자 1~3 조각 + 낱말 + 낱말 둘 → 해시 칸 → 소프트맥스 회귀 (Adagrad). 브라우저 쪽과 같은 특징 함수.
const CLS = ['add', 'query', 'done', 'move', 'cancel', 'sticky', 'note', 'find', 'open', 'new', 'summary', 'pull', 'mail', 'null'];
function fnv(s) { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
function norm(s) { return String(s || '').toLowerCase().replace(/\r/g, '').replace(/[0-9]+/g, '0').replace(/[ \t]+/g, ' ').trim(); }
const feats = (t, B) => require('../nlp.js').mmMLfeats(t, B);   // dashboard.html 안의 특징 함수를 그대로 (브라우저와 같게)
function train(data, { B = 8192, epochs = 25, lr = .5, l2 = 3e-4, seed = 1 } = {}) {
  const K = CLS.length, W = Array.from({ length:K }, () => new Float64Array(B)), G = Array.from({ length:K }, () => new Float64Array(B).fill(1e-8)), bias = new Float64Array(K);
  const X = data.map(([t, y]) => [feats(t, B), CLS.indexOf(y === null ? 'null' : y)]).filter(x => x[1] >= 0); let r = seed;
  const rnd = () => (r = (r * 1103515245 + 12345) % 2147483648) / 2147483648;
  for (let ep = 0; ep < epochs; ep++) { for (let i = X.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [X[i], X[j]] = [X[j], X[i]]; }
    for (const [fx, y] of X) { const z = new Float64Array(K); for (let c = 0; c < K; c++) { let a = bias[c]; for (const [k, v] of fx) a += W[c][k] * v; z[c] = a; } const m = Math.max(...z); let sum = 0; for (let c = 0; c < K; c++) { z[c] = Math.exp(z[c] - m); sum += z[c]; }
      for (let c = 0; c < K; c++) { const g = z[c] / sum - (c === y ? 1 : 0); bias[c] -= lr * .1 * g; for (const [k, v] of fx) { const gg = g * v + l2 * W[c][k]; G[c][k] += gg * gg; W[c][k] -= lr * gg / Math.sqrt(G[c][k]); } } } }
  return { B, W, bias };
}
function predict(m, t) { const fx = feats(t, m.B), K = CLS.length, z = []; for (let c = 0; c < K; c++) { let a = m.bias[c]; for (const [k, v] of fx) a += m.W[c][k] * v; z.push(a); } const mx = Math.max(...z), e = z.map(x => Math.exp(x - mx)), s = e.reduce((a, b) => a + b, 0); const p = e.map(x => x / s); const i = p.indexOf(Math.max(...p)); return { intent:CLS[i] === 'null' ? null : CLS[i], p:p[i], probs:p }; }
function quant(m) {   // 칸마다 4비트(−7~7) 두 개를 한 바이트에 + 부류마다 배율 → base64
  const K = CLS.length, scale = [], u8 = new Uint8Array(K * m.B / 2);
  for (let c = 0; c < K; c++) { let mx = 0; for (let k = 0; k < m.B; k++) mx = Math.max(mx, Math.abs(m.W[c][k])); const sc = mx / 7 || 1; scale.push(+sc.toPrecision(6));
    for (let k = 0; k < m.B; k++) { const v = Math.max(-7, Math.min(7, Math.round(m.W[c][k] / sc))) + 8, o = (c * m.B + k) >> 1; u8[o] |= k & 1 ? v << 4 : v; } }
  return { B:m.B, q:4, scale, bias:[...m.bias].map(x => +x.toFixed(4)), w:Buffer.from(u8).toString('base64') };
}
function dequant(q) { const K = CLS.length, b = Buffer.from(q.w, 'base64'), W = []; for (let c = 0; c < K; c++) { const a = new Float64Array(q.B); for (let k = 0; k < q.B; k++) { const x = b[(c * q.B + k) >> 1]; a[k] = (((k & 1 ? x >> 4 : x) & 15) - 8) * q.scale[c]; } W.push(a); } return { B:q.B, W, bias:Float64Array.from(q.bias) }; }
module.exports = { CLS, fnv, norm, feats, train, predict, quant, dequant };
