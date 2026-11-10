// 사용: node app/build.mjs  → app/index.html (단일 파일 대시보드)
// Ball Valve(ESDV) Anatomy 도해를 anatomy 스킬 kit 으로 만들고, Spec md 체크리스트를 읽어 앱에 주입한다.
import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const LOCAL_KIT = join(ROOT, "anatomy", "kit") + "/";
const KIT = existsSync(LOCAL_KIT + "iso-kit.mjs") ? LOCAL_KIT : "C:/Users/SAMSUNG/.claude/skills/anatomy/kit/";
const k = await import(pathToFileURL(KIT + "iso-kit.mjs").href);
const G = await import(pathToFileURL(KIT + "lathe.mjs").href);

/* ---------------- Ball Valve (ESDV) 도해 ---------------- */
const W = 620, H = 420;
const CZ = 40; // 배관 중심 높이
const P = k.fitProjection(
  [[-80, -30, 0], [80, 30, 0], [-80, -30, 130], [80, 30, 130], [0, 0, 135]],
  W, H, { pad: 30, azimuth: 38 },
);
const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (pts, style) => k.dotsSvg(pts, style);
const at = (p) => k.iso(p, P);
const X = [1, 0, 0], Y = [0, 1, 0];
const part = (id, inner) => `<g data-part="${id}" class="part">${inner}</g>`;

function pipeEnd(sign) {
  // 플랜지 + 배관 스텁 (process-conn)
  const F = G.frameAlong([sign * 38, 0, CZ], X);
  const dir = sign;
  const prof = dir > 0
    ? [[0, 9], [14, 9], [14, 17], [22, 17], [22, 9], [40, 9]]
    : [[0, 9], [-14, 9], [-14, 17], [-22, 17], [-22, 9], [-40, 9]];
  const F2 = G.frameAlong([sign * 38, 0, CZ], [dir, 0, 0]);
  const prof2 = [[0, 9], [14, 9], [14, 17], [22, 17], [22, 9], [40, 9]];
  const out = [S(G.solidOf(prof2, F2, P), { tone: "mid" })];
  // 볼트 원
  const bolts = [];
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    bolts.push(at([sign * 38 + dir * 22, Math.cos(a) * 13, CZ + Math.sin(a) * 13]));
  }
  out.push(D(bolts, { size: 0.5, tone: "lo" }));
  return out.join("");
}

function body() {
  const out = [];
  const Fb = G.frameAlong([0, 0, CZ], X);
  out.push(S(G.solidOf([[-40, 11], [-26, 20], [26, 20], [40, 11]], Fb, P), { tone: "mid" }));
  return out.join("");
}

function neck() {
  const out = [];
  out.push(S(k.cylinder(0, 0, 9, CZ + 16, 14, P, 36), { tone: "mid" }));
  const bonnet = { x: -13, y: -13, w: 26, d: 26, r: 4 };
  out.push(S(k.slabOf(bonnet, CZ + 28, 8, P, 5, 0.6), { tone: "mid" }));
  out.push(D(k.corners(bonnet, 3.2).map(([x, y]) => at([x, y, CZ + 36])), { size: 0.45 }));
  return out.join("");
}

function stem() {
  const out = [];
  out.push(S(k.cylinder(0, 0, 3, CZ + 36, 22, P, 24), { tone: "hi", crease: "none" }));
  return out.join("");
}

function actuator() {
  const out = [];
  const base = CZ + 58;
  const F = G.frameAlong([0, 0, base + 16], Y);
  // 복동/스프링 리턴 실린더 (Y 축)
  out.push(S(G.solidOf([[-46, 15], [-42, 17], [-8, 17], [-4, 15], [4, 15], [8, 17], [42, 17], [46, 15]].map((p) => [p[0], p[1]]), F, P), { tone: "hi" }));
  // 마운팅 브래킷
  out.push(S(k.slabOf({ x: -12, y: -26, w: 24, d: 52, r: 3 }, base - 2, 6, P, 4, 0.5), { tone: "mid" }));
  // 스프링 카트리지 (한쪽 캡)
  out.push(S(G.solidOf([[0, 9], [10, 9], [10, 5], [14, 5]], G.frameAlong([0, 46, base + 16], Y), P), { tone: "mid" }));
  out.push(S(G.solidOf([[0, 9], [10, 9], [10, 5], [14, 5]], G.frameAlong([0, -46, base + 16], [0, -1, 0]), P), { tone: "mid" }));
  return out.join("");
}

function solenoid() {
  const b = { x: 6, y: -9, w: 14, d: 18, r: 2 };
  const z = CZ + 58 + 33;
  const out = [S(k.slabOf(b, z, 12, P, 4, 0.5), { tone: "hi" })];
  out.push(S(k.cylinder(13, 0, 3.4, z + 12, 5, P, 20), { tone: "mid" }));
  out.push(D([at([13, 0, z + 17])], { size: 0.5, tone: "hi" }));
  return out.join("");
}

function limitSwitch() {
  const b = { x: -20, y: -9, w: 12, d: 18, r: 2 };
  const z = CZ + 58 + 33;
  const out = [S(k.slabOf(b, z, 10, P, 4, 0.5), { tone: "hi" })];
  out.push(L(k.planOutline(k.insetPlan(b, 2), z + 10, P, 3), { tone: "faint" }));
  out.push(D([at([-14, 0, z + 10])], { size: 0.5, tone: "hi" }));
  return out.join("");
}

function foot() {
  const plate = { x: -70, y: -28, w: 140, d: 56, r: 5 };
  return S(k.slabOf(plate, -8, 8, P, 6, 0.8), { tone: "lo" }) +
    L(k.planOutline(k.insetPlan(plate, 4), 0, P), { tone: "lo" });
}

const flangeL = pipeEnd(-1), flangeR = pipeEnd(1);
const svg = k.figureSvg({
  width: W, height: H,
  label: "ESDV(트러니언 볼밸브 + 스프링리턴 공압 액추에이터 + 솔레노이드 + 리밋스위치) 개념 도해. 자체 생성 도해이며 제조사 도면이 아님.",
  body: [
    foot(),
    part("process-conn", flangeL),
    part("process-conn", flangeR),
    part("body", body()),
    part("body", neck()),
    part("stem", stem()),
    part("actuator", actuator()),
    part("solenoid", solenoid()),
    part("limit-switch", limitSwitch()),
  ],
});

/* ---------------- Spec md 체크리스트 추출 ---------------- */
const SPEC = join(ROOT, "Spec for each Item");
const FOLDERS = ["DCS", "IPS", "MMS", "CCS", "FGS", "Ball Valve", "Globe Valve", "Butterfly Valve", "PSV", "Field Gauge", "Transmitter", "Bulk Material"];
const specs = {};
for (const f of FOLDERS) {
  const dir = join(SPEC, f);
  if (!existsSync(dir)) continue;
  const file = readdirSync(dir).find((n) => n.endsWith("_Integration_Spec.md"));
  if (!file) continue;
  const text = readFileSync(join(dir, file), "utf8");
  const m = text.match(/^##\s+\d+\.\s*Integration Checklist[^\n]*\n([\s\S]*?)(?=\n##\s|\n>|$)/m);
  const sec = m ? text.slice(0, m.index).split("\n").filter((l) => /^##\s/.test(l)).length + 1 : null;
  const items = m ? m[1].split("\n").filter((l) => /^- \[ \]/.test(l)).map((l) => l.replace(/^- \[ \]\s*/, "").trim()) : [];
  specs[f] = { file, section: m ? m[0].split("\n")[0].replace(/^##\s*/, "") : null, items };
}

/* ---------------- 지식 베이스(웹 조사 Q&A) + Spec 조항 색인 ---------------- */
const KB = {};
const NL = new RegExp("\\r?\\n");
for (const f of FOLDERS) {
  const dir = join(SPEC, f); if (!existsSync(dir)) continue;
  const rows = [];
  const kf = readdirSync(dir).find((n) => n.endsWith("_Knowledge.md"));
  if (kf) {
    const t = readFileSync(join(dir, kf), "utf8"); let topic = "";
    const lines = t.split(NL); let cur = null;
    const push = () => { if (cur && cur.a) rows.push(cur); cur = null; };
    for (const l of lines) {
      let m;
      if ((m = l.match(/^##\s+(.*)/)) && !/^###/.test(l)) { push(); topic = m[1].trim(); continue; }
      if ((m = l.match(/^###\s*Q[:：]\s*(.*)/))) { push(); cur = { k: "kb", topic, q: m[1].trim(), a: "", kw: "", parts: [], src: [], file: kf }; continue; }
      if (!cur) continue;
      if ((m = l.match(/^A[:：]\s*(.*)/))) cur.a = m[1].trim();
      else if ((m = l.match(/^키워드[:：]\s*(.*)/))) cur.kw = m[1].trim();
      else if ((m = l.match(/^부품[:：]\s*(.*)/))) cur.parts = m[1].split(/[,，]/).map((x) => x.trim()).filter(Boolean);
      else if ((m = l.match(/^출처[:：]\s*(.*)/))) { for (const x of m[1].matchAll(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g)) cur.src.push({ t: x[1], u: x[2] }); }
      else if (cur.a && l.trim() && !/^[#>]/.test(l)) cur.a += " " + l.trim();
    }
    push();
  }
  const sf = specs[f] && specs[f].file;
  if (sf) {
    const t = readFileSync(join(dir, sf), "utf8"); let sec = ""; let hdr = null;
    for (const l of t.split(NL)) {
      let m;
      if ((m = l.match(/^#{2,3}\s+(.*)/))) { sec = m[1].trim(); hdr = null; continue; }
      if ((m = l.match(/^\s*- (?:\[ \]\s*)?(.*)/)) && m[1].trim().length > 6) rows.push({ k: "spec", topic: sec, q: sec, a: m[1].replace(/\*\*/g, "").trim(), kw: "", parts: [], src: [], file: sf });
      else if (/^\|/.test(l) && !/^\|\s*-/.test(l)) { const cells = l.split("|").slice(1, -1).map((c) => c.replace(/\*\*/g, "").trim()); if (!hdr) { hdr = cells; continue; } rows.push({ k: "spec", topic: sec, q: sec, a: cells.map((c, i) => (hdr[i] ? hdr[i] + ": " : "") + c).join(" · "), kw: "", parts: [], src: [], file: sf }); }
    }
  }
  KB[f] = rows;
}

/* ---------------- LLM 답변 엔진용 원문(Item 문서) + ic-expert 보조 지식베이스 ---------------- */
const RAW = {};
for (const f of FOLDERS) {
  const dir = join(SPEC, f); if (!existsSync(dir)) continue;
  const kf = readdirSync(dir).find((n) => n.endsWith("_Knowledge.md"));
  const sf = readdirSync(dir).find((n) => n.endsWith("_Integration_Spec.md"));
  RAW[f] = { kfile: kf || null, sfile: sf || null,
    knowledge: kf ? readFileSync(join(dir, kf), "utf8") : "", spec: sf ? readFileSync(join(dir, sf), "utf8") : "" };
}
// 국제 코드 + 아이템별 선정 파일만(모든 질의 공통, 캐시). 발주처·벤더 파일은 필요하면 EXPERT_FILES 에 추가.
const EXPERT_DIR = join(ROOT, "ic-expert", "knowledge");
const EXPERT_FILES = ["01-international-codes.md", "06-instrument-items-selection.md"];
const EXPERT = existsSync(EXPERT_DIR) ? EXPERT_FILES.filter((n) => existsSync(join(EXPERT_DIR, n)))
  .map((n) => ({ file: n, text: readFileSync(join(EXPERT_DIR, n), "utf8") })) : [];
const safeJson = (o) => JSON.stringify(o).split("</").join("<\\/");
const llmSrc = readFileSync(join(HERE, "llm.js"), "utf8")
  .replace("/*__RAW__*/null", () => safeJson(RAW))
  .replace("/*__EXPERT__*/null", () => safeJson(EXPERT));

/* ---------------- 실물 3D 엔진(ic-3d-builder) 복사 + 부품 매핑 ---------------- */
const REAL = join(ROOT, "ic-3d-builder", "index.html");
if (existsSync(REAL)) writeFileSync(join(HERE, "viewer-real.html"), readFileSync(REAL));
const MAP3D_FILE = join(ROOT, "data", "parts", "Map_3d.json");
const MAP3D = existsSync(MAP3D_FILE) ? readFileSync(MAP3D_FILE, "utf8") : "null";

const template = readFileSync(join(HERE, "template.html"), "utf8");
const html = template
  .replace("/*__ISO_CSS__*/", k.ISO_CSS)
  .replace("<!--__FIGURE__-->", svg)
  .replace("/*__MAP3D__*/null", () => MAP3D)
  .replace("/*__VIEWER__*/null", () => existsSync(REAL) ? safeJson(readFileSync(REAL, "utf8")).split("<!--").join("<\\!--") : "null")
  .replace("/*__LLM__*/", () => llmSrc)
  .replace("/*__APP__*/", () => readFileSync(join(HERE, "app.js"), "utf8"))
  .replace("/*__SPECS__*/null", () => JSON.stringify(specs))
  .replace("/*__KB__*/null", () => JSON.stringify(KB).split("</").join("<\\/"))
  .replace("/*__V3D__*/", () => readFileSync(join(HERE, "viewer3d.js"), "utf8") + ";" + readFileSync(join(HERE, "sims.js"), "utf8"))
writeFileSync(join(HERE, "index.html"), html);
console.log("real 3D:", existsSync(REAL) ? "app/viewer-real.html" : "없음(ic-3d-builder 미발견)", "· LLM KB:", EXPERT.map((e) => e.file).join(", ") || "없음");
console.log("wrote app/index.html", Object.keys(specs).length, "specs, svg", svg.length, "KB", Object.entries(KB).map(([k, v]) => k + ":" + v.filter((r) => r.k === "kb").length + "/" + v.length).join(" "));
