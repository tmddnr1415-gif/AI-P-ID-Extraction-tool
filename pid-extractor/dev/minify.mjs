/* index.html → dist/index.min.html — **claude.ai 대화창에 붙일 배포본.**
 *
 * 왜 필요한가: 그 경로는 대화창의 Claude 가 파일을 **통째로 다시 써야** 아티팩트가
 * 된다. 74KB 를 한 글자도 안 틀리고 옮겨 적는 것은 느리고 잘 깨진다. 크기가 곧
 * 성공률이다. 주석과 들여쓰기가 대부분을 차지하고, 한글 주석은 글자당 3바이트다.
 *
 * 무엇을 하지 않는가: **이름은 안 바꾼다.** 최상위 function 선언이 그대로
 * window 에 올라야 회귀 시험이 앱을 몰 수 있고, 나중에 사람이 읽고 고칠 수도 있다.
 * 공백·주석·구문만 줄인다. 원본 index.html 이 계속 원본이다.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { transformSync } from '../../pid-extractor/dev/node_modules/esbuild/lib/main.js';

const ROOT = new URL('..', import.meta.url).pathname;
const src = readFileSync(ROOT + 'index.html', 'utf8');

const one = (re, what) => {
  const m = src.match(re);
  if (!m) throw new Error(`${what} 를 못 찾음`);
  return m;
};
const css = one(/<style>([\s\S]*?)<\/style>/, '<style>');
const js = one(/<script>\n?'use strict';([\s\S]*?)<\/script>/, '<script>');

// charset:'utf8' 이 중요하다 — 기본값(ascii)은 한글을 \uXXXX 로 바꿔 글자당
// 3바이트를 6바이트로 늘린다. 그러면 줄이려던 것이 오히려 커진다.
const minCss = transformSync(css[1], { loader: 'css', minify: true, charset: 'utf8' }).code.trim();
const minJs = transformSync(js[1], {
  loader: 'js',
  minifyWhitespace: true,
  minifySyntax: true,
  minifyIdentifiers: false,   // 최상위 이름을 유지한다 — 회귀 시험과 사람이 쓴다
  charset: 'utf8',
}).code.trim();

/* replace 의 두 번째 인자를 **함수로** 준다. 문자열로 주면 $& $' $1 같은 패턴이
   치환돼 버리는데, 압축된 JS 에는 $ 가 잔뜩 있어($ 헬퍼, 템플릿 리터럴) 파일 꼬리가
   통째로 복제된다. 실제로 74KB 가 101KB 로 불어났다. */
let out = src
  .replace(css[0], () => `<style>${minCss}</style>`)
  .replace(js[0], () => `<script>\n'use strict';\n${minJs}\n</script>`)
  // HTML 주석은 지우되 PDFJS_INJECT 자리는 남긴다 — 빌드와 개발 서버가 여기에 심는다.
  .replace(/<!--(?!\s*PDFJS_INJECT)[\s\S]*?-->/g, '')
  .replace(/<!--\s*PDFJS_INJECT[\s\S]*?-->/, () => '<!-- PDFJS_INJECT -->')
  .replace(/^[ \t]+/gm, '')                 // 들여쓰기
  .replace(/\n{2,}/g, '\n')                 // 빈 줄
  .trim() + '\n';

mkdirSync(ROOT + 'dist', { recursive: true });
writeFileSync(ROOT + 'dist/index.min.html', out);
const kb = (s) => (Buffer.byteLength(s) / 1024).toFixed(0) + ' KB';
console.log(`${kb(src)} → ${kb(out)}  (${(100 - Buffer.byteLength(out) / Buffer.byteLength(src) * 100).toFixed(0)}% 줄임)`);
