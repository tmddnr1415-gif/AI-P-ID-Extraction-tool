// 대시보드 통합 E2E (헤드리스 크로미움, API 는 가짜 스트림):
//   실물 3D 모드 전환·부품 태그 → 3D 강조, 로컬 검색형 답변, Claude(LLM) 답변(규칙·part 태그·안전 게이트).
//   NODE_PATH=$(npm root -g) node app/test_e2e.mjs [three.min.js 경로]   (CDN 이 막힌 환경이면 경로를 준다)
import { createRequire } from "node:module";
import fs from "node:fs"; import path from "node:path"; import url from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const here = path.dirname(url.fileURLToPath(import.meta.url));
const three = process.argv[2];
const shot = process.env.SHOT;
const sse = (text) => [
  { type: "message_start", message: { usage: { input_tokens: 5 } } },
  { type: "content_block_start", index: 0, content_block: { type: "text", text: "" } },
  { type: "content_block_delta", index: 0, delta: { type: "text_delta", text } },
  { type: "content_block_stop", index: 0 },
  { type: "message_delta", delta: { stop_reason: "end_turn" }, usage: { output_tokens: 9 } },
].map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e)}\n\n`).join("");

const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
const errors = []; page.on("pageerror", (e) => errors.push(String(e)));
if (three) await page.route("**/three.min.js", (r) => r.fulfill({ body: fs.readFileSync(three), contentType: "text/javascript" }));
const bodies = [];
await page.route("https://api.anthropic.com/**", (r) => {
  bodies.push(JSON.parse(r.request().postData()));
  r.fulfill({ status: 200, headers: { "content-type": "text/event-stream", "access-control-allow-origin": "*" },
    body: sse("**초안, 담당자 확인 필수**\n\n**결론**: ESDV 는 Fail-close 스프링 리턴으로 둔다 part:spring\n\n| 항목 | 요점 |\n|---|---|\n| Stroke time | 미확인 part:actuator |\n\n- 후속: 프로젝트 Spec 대조") });
});
const ok = []; const check = (n, c) => { ok.push(!!c); console.log(c ? "✓" : "✗", n); };
await page.goto("file://" + path.join(here, "index.html")); await page.waitForTimeout(800);

// 1) 로컬 검색형 답변 + Anatomy 실물 3D
await page.fill("#q", "ESDV Spec 검토 시 유의사항은?"); await page.click("#go");
await page.waitForFunction(() => !document.getElementById("go").disabled, null, { timeout: 15000 });
check("로컬 검색형 답변 표시", (await page.$$(".m.a")).length >= 1);
await page.evaluate(() => document.querySelector('.tab[data-t="anap"]').click());
await page.waitForTimeout(400);
const real = await page.evaluate(() => ({ on: R3.on, src: document.getElementById("v3real").getAttribute("src"), hidden: document.getElementById("v3real").hidden }));
check("Ball Valve → 실물 3D(esdv_ball) 기본 표시", real.on && /preset=esdv_ball/.test(real.src || "") && !real.hidden);
await page.waitForFunction(() => R3.ready, null, { timeout: 15000 });
const fr = page.frames().find((f) => f.url().includes("viewer-real.html"));
check("실물 3D 프레임 로드(embed)", !!fr && await fr.evaluate(() => document.body.classList.contains("embed") && IC3D.S.presetId === "esdv_ball"));
// 태그 클릭 → 3D 부품 선택
await page.evaluate(() => { const t = document.querySelector('#plist .tag[data-p="solenoid"]'); t.click(); });
await page.waitForTimeout(800);
check("part:solenoid → 3D solenoid 강조", await fr.evaluate(() => IC3D.S.selected === "solenoid"));
// 3D 클릭(pick) → 대시보드 부품 칩 표시
await fr.evaluate(() => IC3D.selectPart("ball", false));
await page.waitForTimeout(300);
check("3D pick ball → 부품 칩 강조", await page.evaluate(() => document.querySelector('#plist .tag[data-p="ball"]').classList.contains("on")));
// 개념 모드 왕복
await page.click("#v3m-c"); await page.waitForTimeout(200);
check("개념·시뮬레이션 모드 복귀(시뮬레이션 패널 표시)", await page.evaluate(() => !R3.on && document.getElementById("v3real").hidden && document.getElementById("simbox").style.display !== "none"));
await page.click("#v3m-r"); await page.waitForTimeout(300);
// 매핑 없는 Item → 개념 모델 안내
await page.selectOption("#v3sel", "mms"); await page.waitForTimeout(300);
check("MMS(실물 3D 없음) → 개념 모델 + 안내", await page.evaluate(() => !R3.on && !document.getElementById("v3note").hidden));
await page.selectOption("#v3sel", "globe-valve"); await page.click("#v3m-r"); await page.waitForTimeout(600);
check("Globe Valve → cv_globe", await fr.evaluate(() => IC3D.S.presetId === "cv_globe"));
if (shot) await page.screenshot({ path: shot.replace(/\.png$/, "_3d.png") });

// 2) Claude(LLM) 답변 엔진
await page.evaluate(() => { localStorage.setItem("ic-llm-key", "sk-test"); localStorage.setItem("ic-llm", "1"); });
await page.fill("#q", "ESDV fail 방향과 stroke time 은?"); await page.click("#go");
await page.waitForFunction(() => [...document.querySelectorAll(".m.a")].some((d) => /Claude\(LLM\)/.test(d.textContent) && /결론/.test(d.textContent)), null, { timeout: 15000 });
const b = bodies.at(-1);
check("LLM 요청: 공통 규칙+보조 KB 캐시 블록", b && b.system.length === 2 && b.system[0].cache_control && /근거 순위/.test(b.system[0].text) && /01-international-codes/.test(b.system[0].text));
check("LLM 요청: Ball Valve Item 문서 포함", /Ball_Valve_Knowledge\.md/.test(b.system[1].text) && /허용 part id: .*spring/.test(b.system[1].text));
const last = await page.$$eval(".m.a", (ds) => ds.at(-1).innerHTML);
check("안전 게이트 표기", /초안, 담당자 확인 필수/.test(last));
check("part:spring → 태그로 변환", /class="tag" data-i="ball-valve" data-p="spring"/.test(last));
check("표 렌더링", /<table class="mt">/.test(last));
check("페이지 오류 없음", errors.length === 0);
if (shot) await page.screenshot({ path: shot });
await browser.close();
if (errors.length) console.log(errors);
process.exit(ok.every(Boolean) ? 0 : 1);
