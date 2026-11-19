// OCR 오류 흉내: 수준 1~3
let seed = 17; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
module.exports = (t, lv) => t.split('\n').map(l => { let s = l;
  if (rnd() < .25 * lv) s = s.replace(/([가-힣])\s([가-힣])/g, (q, a, b) => rnd() < .3 ? a + b : q);          // 한글 사이 띄어쓰기 빠짐
  if (rnd() < .15 * lv) s = s.replace(/([가-힣]{2})([가-힣]{2})/, (q, a, b) => rnd() < .3 ? a + ' ' + b : q);  // 띄어쓰기 생김
  if (rnd() < .2 * lv) s = s.replace(/:/, () => pick([' ', ';', ':', '.']));                                      // 쌍점
  if (rnd() < .1 * lv) s = s.replace(/(?<=[A-Za-z])l(?=[a-z])/, 'I');
  if (rnd() < .08 * lv) s = s.replace(/(?<=[A-Za-z])O/, '0');
  if (rnd() < .06 * lv) s = s.replace(/\.$/, ',');
  if (rnd() < .05 * lv) s = s.replace(/\(([월화수목금토일])\)/, '($1');
  if (rnd() < .05 * lv) s = ' ' + s + ' ';
  return s; }).join('\n');
function pick(a) { return a[Math.floor(rnd() * a.length)]; }
