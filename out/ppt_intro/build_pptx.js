const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/f85dfd51-6ca8-4a99-a266-edae17756b68_a9536842-345c-4a5f-a3f5-e43e63832971/pptx/scripts/apply_theme.js");
const SHOTS = process.env.SHOTS;
const OUT = process.env.OUT || "deck.pptx";

const THEME = { name: "PID Extractor UI", headFontFace: "Malgun Gothic", bodyFontFace: "Malgun Gothic",
  colors: { dk1: "1E2A3F", lt1: "FFFFFF", dk2: "4A3F33", lt2: "F7F2E6", accent1: "1A5FB4", accent2: "2F5BD8",
            accent3: "0F8F80", accent4: "B07614", accent5: "C2453F", accent6: "6B5F4F", hlink: "1A5FB4", folHlink: "6B5F4F" } };
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "P&ID 계기·밸브 추출 프로그램 — 기능 소개";
pres.author = "P&ID Extractor";
const C = pres.SchemeColor;
const NAVY = THEME.colors.dk1, CREAM = THEME.colors.lt2, CARD = "FFFDF6", SUNK = "EFE8D8", LINE = "E3DCCB", CHIP = "E8EEF9", BLUE = THEME.colors.accent1;
const W = 13.333, H = 7.5, SB = 1.7;      // sidebar width
const CX = SB + 0.3, CW = W - CX - 0.35;  // content x / width
const TOTAL = 19;
const MENU = [["홈 (대시보드)", ""], ["전체", "1991"], ["Field", "1628"], ["BFV", "0"], ["MOV", "11"], ["Pneumatic", "3"], ["검토필요", "1782"]];

// ── layouts ───────────────────────────────────────────────────────────────
pres.defineSlideMaster({ title: "dark", background: { color: NAVY }, objects: [] });
pres.defineSlideMaster({ title: "feature", background: { color: CREAM }, objects: [
  { placeholder: { options: { name: "title", type: "title", x: CX, y: 0.32, w: CW - 3.6, h: 0.62, fontSize: 26, bold: true, color: BLUE, margin: 0, valign: "middle" }, text: "" } },
  { placeholder: { options: { name: "sub", type: "body", x: CX, y: 0.92, w: CW - 3.6, h: 0.4, fontSize: 13, color: THEME.colors.accent6, margin: 0, valign: "top" }, text: "" } },
  { line: { x: CX, y: 1.38, w: CW, h: 0, line: { color: LINE, width: 1 } } },
  { text: { text: "P&ID 계기·밸브 추출 프로그램 — 기능별 동작 화면", options: { x: CX, y: 7.05, w: 7, h: 0.3, fontSize: 10, color: THEME.colors.accent6, margin: 0 } } },
], slideNumber: { x: 12.2, y: 7.05, w: 0.8, h: 0.3, fontSize: 10, color: THEME.colors.accent6, align: "right" } });

function sidebar(slide, active) {
  slide.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: SB, h: H, fill: { color: NAVY }, line: { color: NAVY }, objectName: "menu panel" });
  slide.addText("SAMSUNG C&T", { x: 0.15, y: 0.22, w: SB - 0.2, h: 0.32, fontSize: 11, wrap: false, bold: true, color: "FFFFFF", margin: 0, isTextBox: true, objectName: "menu brand" });
  slide.addText("P&ID EXTRACTOR", { x: 0.15, y: 0.58, w: SB - 0.2, h: 0.25, fontSize: 8, wrap: false, color: "B9C4D8", charSpacing: 1, margin: 0, isTextBox: true, objectName: "menu brand 2" });
  slide.addText("MENU", { x: 0.15, y: 1.0, w: 1, h: 0.25, fontSize: 9, color: "8E9BB5", margin: 0, isTextBox: true, objectName: "menu head" });
  let y = 1.3;
  for (const [name, n] of MENU) {
    if (name === active) slide.addShape(pres.ShapeType.roundRect, { x: 0.12, y: y - 0.03, w: SB - 0.24, h: 0.36, rectRadius: 0.06, fill: { color: THEME.colors.accent2 }, line: { color: THEME.colors.accent2 }, objectName: "menu active" });
    slide.addText(name === "홈 (대시보드)" ? "홈" : name, { x: 0.22, y, w: 1.0, h: 0.3, fontSize: 11, wrap: false, color: "FFFFFF", margin: 0, isTextBox: true, valign: "middle", objectName: "menu " + name });
    if (n) slide.addText(n, { x: 1.05, y, w: 0.5, h: 0.3, fontSize: 10, color: "B9C4D8", align: "right", margin: 0, isTextBox: true, valign: "middle", objectName: "menu count " + name });
    y += 0.42;
  }
  slide.addText("프로젝트", { x: 0.15, y: y + 0.15, w: 1, h: 0.25, fontSize: 9, color: "8E9BB5", margin: 0, isTextBox: true, objectName: "menu head 2" });
  slide.addShape(pres.ShapeType.roundRect, { x: 0.12, y: y + 0.45, w: SB - 0.24, h: 0.62, rectRadius: 0.06, fill: { color: "2A3750" }, line: { color: "2A3750" }, objectName: "menu project" });
  slide.addText([{ text: "QF  QFE", options: { bold: true, color: "FFFFFF", fontSize: 11, breakLine: true } }, { text: "자동 · 변경 180", options: { color: "FFD66B", fontSize: 9 } }],
    { x: 0.22, y: y + 0.47, w: SB - 0.4, h: 0.58, margin: 0, isTextBox: true, valign: "middle", objectName: "menu project text" });
  slide.addText([{ text: "사용자: 홍길동", options: { color: "B9C4D8", fontSize: 9, breakLine: true } }, { text: "● 서버 연결됨", options: { color: "7FD1A0", fontSize: 9 } }],
    { x: 0.15, y: H - 0.75, w: SB - 0.3, h: 0.5, margin: 0, isTextBox: true, objectName: "menu user" });
}

function chips(slide, items, y = 0.42) {
  let x = W - 0.35;
  for (const c of [...items].reverse()) {
    const w = 0.22 + c.length * 0.1;
    x -= w + 0.1;
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h: 0.32, rectRadius: 0.16, fill: { color: CHIP }, line: { color: "C9D7F0", width: 0.75 }, objectName: "chip " + c });
    slide.addText(c, { x, y, w, h: 0.32, fontSize: 10, color: BLUE, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "chip text " + c });
  }
}

function shot(slide, file, x, y, w, h, iw, ih, alt) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: SUNK }, line: { color: LINE, width: 0.75 }, objectName: "shot frame " + alt });
  const pad = 0.08, bw = w - 2 * pad, bh = h - 2 * pad;
  const s = Math.min(bw / iw, bh / ih);
  const dw = iw * s, dh = ih * s;
  slide.addImage({ path: `${SHOTS}/${file}`, x: x + (w - dw) / 2, y: y + (h - dh) / 2, w: dw, h: dh, altText: alt, objectName: "shot " + alt });
}

function runs(s) {  // "**bold**" → runs
  const out = []; const parts = s.split("**");
  parts.forEach((p, i) => { if (p) out.push({ text: p, options: { bold: i % 2 === 1 } }); });
  return out;
}
function card(slide, title, items, x, y, w, h, fs = 11.5) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, objectName: "card " + title });
  slide.addText(title, { x: x + 0.2, y: y + 0.15, w: w - 0.4, h: 0.35, fontSize: 14, bold: true, color: BLUE, margin: 0, isTextBox: true, objectName: "card title " + title });
  const paras = [];
  items.forEach((it, i) => {
    const r = runs(it);
    r[0].options = Object.assign({}, r[0].options, { bullet: { indent: 12 }, paraSpaceAfter: 5 });
    if (i < items.length - 1) r[r.length - 1].options = Object.assign({}, r[r.length - 1].options, { breakLine: true });
    paras.push(...r);
  });
  slide.addText(paras, { x: x + 0.2, y: y + 0.55, w: w - 0.4, h: h - 0.7, fontSize: fs, color: THEME.colors.dk2, valign: "top", margin: 0, isTextBox: true, lineSpacingMultiple: 1.15, objectName: "card body " + title });
}

function base(active, title, sub, chipList, section) {
  const slide = pres.addSlide({ masterName: "feature", sectionTitle: section });
  sidebar(slide, active);
  slide.addText(title, { placeholder: "title" });
  slide.addText(sub, { placeholder: "sub" });
  chips(slide, chipList);
  return slide;
}
const IMG = { home: ["01_home.png", 1920, 1080], result: ["02_result.png", 1920, 1080], evidence: ["03_evidence.png", 1920, 1080], evcrop: ["03b_evidence_crop.png", 836, 96],
  range: ["04_cells_range.png", 838, 930], celledit: ["04b_cell_edit.png", 838, 930], savestate: ["04c_savestate.png", 753, 70], scopepop: ["05_scopepop.png", 760, 460],
  qty: ["06_qty_labels.png", 836, 818], mult: ["07_mult_panel.png", 836, 170], markup: ["08_markup_dialog.png", 1920, 1080], side: ["09_side_by_side.png", 1920, 1080],
  memo: ["10_memo.png", 836, 240], pin: ["11b_pin_on_drawing.png", 1920, 1080], review: ["12_review_tab.png", 1920, 1080], full: ["13_fullscreen_edit.png", 1920, 1080],
  keys: ["14_shortcuts.png", 1920, 1080], voc: ["15_voc.png", 1920, 1080], popd: ["16_popout_drawing.png", 1920, 1080], popl: ["16b_popout_list.png", 1920, 1080],
  running: ["17_home_running.png", 1920, 1080], progress: ["17b_progress.png", 1920, 1080] };
function img(slide, key, x, y, w, h) { const [f, iw, ih] = IMG[key]; shot(slide, f, x, y, w, h, iw, ih, key); }

// standard feature slide: big screenshot left (16:9) + card right
function feature(active, title, sub, chipList, key, cardTitle, items, section, notes) {
  const s = base(active, title, sub, chipList, section);
  const y = 1.6, iw = 7.1, ih = iw * 9 / 16;
  img(s, key, CX, y, iw, ih);
  card(s, cardTitle, items, CX + iw + 0.25, y, CW - iw - 0.25, 5.2);
  if (notes) s.addNotes(notes);
  return s;
}

const S1 = "프로그램 한눈에", S2 = "기본 흐름", S3 = "검토 · 편집 · 개정 대조", S4 = "출력 · 협업 · 운영";

// 1 cover
pres.addSection({ title: S1 });
{
  const s = pres.addSlide({ masterName: "dark", sectionTitle: S1 });
  s.addText("SAMSUNG C&T · P&ID EXTRACTOR", { x: 0.9, y: 1.3, w: 11, h: 0.4, fontSize: 13, color: "B9C4D8", charSpacing: 3, margin: 0, isTextBox: true, objectName: "cover kicker" });
  s.addText("P&ID 계기·밸브 추출 프로그램", { x: 0.9, y: 1.9, w: 11.5, h: 1.3, fontSize: 48, bold: true, color: "FFFFFF", margin: 0, isTextBox: true, objectName: "cover title" });
  s.addText("기능별 실제 동작 화면과 함께 보는 소개", { x: 0.9, y: 3.2, w: 11, h: 0.6, fontSize: 22, color: "DFE6F3", margin: 0, isTextBox: true, objectName: "cover sub" });
  let x = 0.9;
  for (const c of ["PDF · DXF 입력", "범례에서 규칙을 읽는 엔진", "도면 위 검토·편집", "Excel 출력 · 개정 대조"]) {
    const w = 0.5 + c.length * 0.17;
    s.addShape(pres.ShapeType.roundRect, { x, y: 4.4, w, h: 0.5, rectRadius: 0.25, fill: { color: "2A3750" }, line: { color: "3D4B66", width: 0.75 }, objectName: "cover chip " + c });
    s.addText(c, { x, y: 4.4, w, h: 0.5, fontSize: 13, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "cover chip text " + c });
    x += w + 0.15;
  }
  s.addText("화면은 QFE 프로젝트 Rev.B 분석 결과 (QFE_260326.pdf · 93장)", { x: 0.9, y: 6.6, w: 8, h: 0.35, fontSize: 12, color: "B9C4D8", margin: 0, isTextBox: true, objectName: "cover note" });
  s.addText("2026-10-10 · hotfix80 기준", { x: 9.3, y: 6.6, w: 3.4, h: 0.35, fontSize: 12, color: "B9C4D8", align: "right", margin: 0, isTextBox: true, objectName: "cover date" });
  s.addNotes("프로그램 소개 덱. 모든 화면은 실제 서버에서 찍은 동작 화면입니다.");
}

// 2 overview
{
  const s = base("홈 (대시보드)", "프로그램 한눈에", "P&ID 도면을 넣으면 계기·밸브 목록을 발주처 양식으로 내보냅니다", ["4단계"], S1);
  const steps = [["입력", BLUE, ["PDF (A1·A3 · 회전 섞임) 또는 DXF 묶음(zip)", "프로젝트 · 입찰/실행 종류 · 이전 Rev 선택", "암호·손상·스캔 PDF 는 원인을 말하며 거절"]],
    ["엔진 분석", THEME.colors.accent3, ["Symbol & Legend 에서 치수·ISA 문자표·승수 유도", "계기 버블 · 밸브 몸체·액추에이터 · 별표(공급 주체)", "태그 · 라인 번호 · Description · Typical · NOTES 승수"]],
    ["검토 화면", THEME.colors.accent4, ["도면 오버레이 + 엑셀식 목록 + 근거 패널", "마크업 · 수량 승수 · 메모·핀 · 듀얼 모니터", "이전 Rev 와 나란히 대조 (추가·수정·삭제)"]],
    ["출력", THEME.colors.accent5, ["발주처 양식 Excel (FIELD · MOV · BFV)", "변경 내역 Excel · 피드백 zip · 진단 zip", "VOC 함 → 개발 반영 (중복 반영 방지)"]]];
  const gw = (CW - 0.6) / 4;
  steps.forEach(([t, col, lines], i) => {
    const x = CX + i * (gw + 0.2), y = 1.65, h = 3.5;
    s.addShape(pres.ShapeType.roundRect, { x, y, w: gw, h, rectRadius: 0.08, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, objectName: "step card " + t });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.2, y: y + 0.2, w: 0.5, h: 0.5, fill: { color: col }, line: { color: col }, objectName: "step circle " + t });
    s.addText(String(i + 1), { x: x + 0.2, y: y + 0.2, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "step no " + t });
    s.addText(t, { x: x + 0.85, y: y + 0.2, w: gw - 1.0, h: 0.5, fontSize: 18, bold: true, color: col, valign: "middle", margin: 0, isTextBox: true, objectName: "step title " + t });
    const paras = lines.map((l, j) => ({ text: l, options: { bullet: { indent: 12 }, paraSpaceAfter: 6, breakLine: j < lines.length - 1 } }));
    s.addText(paras, { x: x + 0.2, y: y + 0.9, w: gw - 0.4, h: h - 1.1, fontSize: 12, color: THEME.colors.dk2, valign: "top", margin: 0, isTextBox: true, lineSpacingMultiple: 1.15, objectName: "step body " + t });
  });
  s.addShape(pres.ShapeType.roundRect, { x: CX, y: 5.4, w: CW, h: 1.35, rectRadius: 0.08, fill: { color: CHIP }, line: { color: "C9D7F0", width: 0.75 }, objectName: "principle box" });
  s.addText([{ text: "원칙  ", options: { bold: true, color: BLUE } }, { text: "도면이 말하는 것은 도면에서 읽고 외워두지 않는다 · 도면이 말하지 않으면 사람에게 묻는다 · 검출에 LLM 을 쓰지 않는다 · 네 프로젝트(AL NOUF1 · TC2 · QFE · UAD-DXF) 회귀 기준선이 모든 변경을 지킨다", options: { color: THEME.colors.dk2 } }],
    { x: CX + 0.25, y: 5.5, w: CW - 0.5, h: 1.15, fontSize: 13, valign: "middle", margin: 0, isTextBox: true, lineSpacingMultiple: 1.2, objectName: "principle text" });
}

pres.addSection({ title: S2 });
feature("홈 (대시보드)", "첫 화면 — 대시보드", "왼쪽 메뉴 · 프로젝트 카드 · 리비전 타임라인 · 업로드", ["홈"], "home", "무엇이 보이나", [
  "프로젝트 카드에 **PDF 가 인쇄한 프로젝트 제목** · 최상위 Rev 와 날짜 · 양식에 나가는 계기 수량",
  "리비전 타임라인 — 분석 상태 · 개정 판정 배지 · 행·장·수정 칸 · 누르면 결과 열림",
  "업로드 카드에서 프로젝트와 **입찰 / 실행** 종류를 고르고 PDF·DXF 를 넣는다",
  "그래프 셋 — 프로젝트별 · 리비전별 산출 행 · 개정 변경 도넛 (서버가 이미 내던 값만)",
  "알림 알약 — 데이터 위생 · 실패 · 분석 중 · 개정 변경"], S2);

// 4 progress — two shots + two cards
{
  const s = base("홈 (대시보드)", "분석 진행", "분석은 별도 프로세스에서 돌고, 화면은 어디서든 현황을 본다", ["분석 중"], S2);
  const iw = (CW - 0.25) / 2, ih = iw * 9 / 16;
  img(s, "running", CX, 1.6, iw, ih); img(s, "progress", CX + iw + 0.25, 1.6, iw, ih);
  const cy = 1.6 + ih + 0.25, ch = 6.85 - cy;
  card(s, "진행 현황", ["최근 분석 이력 맨 위에 **진행 막대 · % · 남은 시간 · 지금 단계** (도면 치수 재는 중 — 37/60쪽)", "남은 시간은 이 서버에서 끝난 분석의 **장당 시간 중앙값 × 장수** — 근거를 함께 적고, 없으면 '예상할 수 없음'"], CX, cy, iw, ch);
  card(s, "안전하게", ["분석은 자식 프로세스 — 메모리 부족으로 죽어도 서버는 살고 그 분석만 실패로 적힌다", "다른 메뉴로 갔다 와도 분석은 계속 · 취소는 즉시 · 실패하면 멈춘 단계와 사유를 말한다"], CX + iw + 0.25, cy, iw, ch);
}

feature("전체", "결과 화면 — 도면 오버레이와 목록", "왼쪽 도면 위 판정 상자 · 오른쪽 엑셀식 목록 · 탭은 산출물 단위", ["1,991행", "93장"], "result", "화면 구성", [
  "상자 색 = **공급 주체** (SCT 파랑 · VENDOR 주황 · 판정 없음 보라) · 모서리 ● 는 검토 필요 · **x N** 은 Q'ty",
  "탭 전체 · Field · BFV · MOV · Pneumatic — 발주처 양식 단위와 같다",
  "머리줄 띠 — 범례 재사용 · 프로필 · 실행(1급+2급) 판정 · 저장됨 시각 · 수정 이력",
  "목록 열 — PAGE · P&ID NO. · 귀속 · 개정 · TYPE · TAG NO. · LINE NO. · LINE SIZE · Q'ty · SCOPE …",
  "장 목록에 장마다 ＋추가 ≠수정 －삭제 수 · 범례 판은 끌 수 있다"], S2);

// 6 evidence — shot + card + crop row
{
  const s = base("전체", "근거 패널 — 왜 그렇게 판정했나", "행을 누르면 그 행의 판정 근거가 그대로 보인다", ["근거"], S2);
  const iw = 7.1, ih = iw * 9 / 16;
  img(s, "evidence", CX, 1.6, iw, ih);
  card(s, "패널이 말하는 것", ["**공급 주체** — 별표·NOTES 정의줄·패키지 상자 중 무엇이 가렸나, 발주처 양식에 나가는가", "**수량 근거** — 1 symbol x 2 (NOTES: …) · 범례 승수표 · 사람 지정이면 누가·언제", "**Description · Line No.** — 어느 런을 탭했고 깃발을 어디서 읽었나", "**태그** — 지시선이 가리킨 밸브 · 태그 문법 교차 검증 · 개정 판정", "사람이 고친 칸은 ✎ 와 이름 — 도면 근거는 옆에 그대로 남는다"], CX + iw + 0.25, 1.6, CW - iw - 0.25, ih);
  img(s, "evcrop", CX, 5.85, 7.1, 0.95);
  s.addText("검토 사유는 다섯 축(스코프 · 수량 · Description · 검출 · 입력 자료)으로 묶여 검토 탭에 집계된다", { x: CX + 7.35, y: 5.85, w: CW - 7.35, h: 0.95, fontSize: 11.5, color: THEME.colors.accent6, valign: "middle", margin: 0, isTextBox: true, objectName: "evidence note" });
}

pres.addSection({ title: S3 });
// 7 list editing — two portrait shots + card + save-state row
{
  const s = base("전체", "목록 편집 — 엑셀처럼", "칸을 골라 바로 치고, 범위를 잡고, 되돌린다", ["Ctrl+Z", "Shift+↑↓", "Ctrl+F"], S3);
  const ih = 4.2, iw = ih * 838 / 930;
  img(s, "range", CX, 1.6, iw, ih); img(s, "celledit", CX + iw + 0.2, 1.6, iw, ih);
  const cx = CX + 2 * iw + 0.45;
  card(s, "동작", ["한 번 누르면 칸이 골라지고 **두 번 누름 · F2 · 바로 타자**로 편집이 열린다", "Enter 저장 후 아래 · Tab 오른쪽 · Esc 되돌림 · 화살표로 칸 이동", "**Shift+↑↓** 한 열 범위 · Ctrl+C/V · 여러 줄 붙이기는 위에서 한 줄씩 · Ctrl+Enter 범위 채우기 · Delete = 도면 값", "**Ctrl+Z / Ctrl+Y** — 서버에 쓰는 길 넷 전부 되돌린다 (기록은 지우지 않고 한 줄 더 쌓임)", "저장 상태 칩 — 저장 중 · 저장됨 시각 · 실패하면 붉게"], cx, 1.6, W - 0.35 - cx, ih, 11);
  img(s, "savestate", CX, 6.0, 5.5, 0.75);
  s.addText("고친 값은 사람 값(✎)으로 남고 엔진 값은 그대로 — 다음 리비전에 안정 ID 로 승계된다", { x: CX + 5.7, y: 6.0, w: CW - 5.7, h: 0.75, fontSize: 11.5, color: THEME.colors.accent6, valign: "middle", margin: 0, isTextBox: true, objectName: "edit note" });
}

// 8 drawing edit
{
  const s = base("전체", "도면에서 바로 고치기", "상자를 누르면 공급 주체, 라벨을 누르면 수량", ["SCOPE", "x N"], S3);
  const w1 = 3.7, h1 = w1 * 460 / 760, w2 = 3.7, h2 = w2 * 818 / 836;
  img(s, "scopepop", CX, 1.6, w1, h1); img(s, "qty", CX + w1 + 0.2, 1.6, w2, h2);
  s.addText("상자를 누르면 뜨는 공급 주체 판", { x: CX, y: 1.6 + h1 + 0.1, w: w1, h: 0.3, fontSize: 10.5, color: THEME.colors.accent6, margin: 0, isTextBox: true, objectName: "cap scopepop" });
  const cx = CX + w1 + w2 + 0.45;
  card(s, "동작", ["상자 → **SCT 공급 · VENDOR(이 도면에서 읽은 공급자 이름) · 둘 다 아님(식별 지우기)**", "지운 상자는 붉은 ✕ · 목록 취소선 · Excel 에서 빠짐 · 다시 누르면 되돌리기", "**x N** 라벨 → 이 태그만 · 이 페이지 전체 · Shift 범위 — 저장은 한 곳, 목록·라벨이 같은 값", "Shift 끌기로 띠 선택 → 묶음 판에서 공급 주체·승수 일괄 변경 (요청 하나)", "작성자는 대시보드 로그인 이름으로 자동 기록"], cx, 1.6, W - 0.35 - cx, h2, 11);
}

feature("전체", "도면 전체화면에서도 편집", "⛶ 전체화면 · 도면 위 편집 카드 · 목록에 저절로 반영", ["⛶"], "full", "동작", [
  "⛶ 를 누르면 도면 창이 화면 전체 — 대시보드 iframe 안이면 화면 안 전체화면",
  "상자를 누르면 오른쪽 위에 **편집 카드** (목록 머리글과 같은 칸 · Enter 저장 · ◀ ▶ 다음 항목)",
  "저장 길은 목록 칸과 같은 하나 — 어디서 고쳤든 목록이 같은 값으로 선다",
  "목록을 끝까지 접어 안 보일 때도 같은 카드가 뜬다 · Esc 는 선택 풀기 → 전체화면 끝"], S3);

// 10 mult
{
  const s = base("전체", "수량 승수 판", "여러 장을 골라 장마다 승수를 적으면 Q'ty 가 바로 바뀐다", ["Q'ty"], S3);
  const iw = CW, ih = iw * 170 / 836;
  img(s, "mult", CX, 1.6, iw, ih + 0.16);
  const cy = 1.6 + ih + 0.45, cw = (CW - 0.25) / 2;
  card(s, "페이지별 승수 (지금 결과)", ["행이 있는 장마다 한 줄 — 도면번호 · 행 수 · **지금 xN** · 승수 칸 · Q'ty 전→후", "칸에 적으면 저절로 골라지고 Shift 로 사이 장까지 · '선택한 장에 같은 승수'", "새 Q'ty = 기본 개수 × 승수 — 사람이 고친 Q'ty(✎)로 저장 · 다음 Rev 에 승계"], CX, cy, cw, 6.85 - cy);
  card(s, "유닛코드 승수 (다음 분석부터)", ["범례 승수표가 없는 문서는 유닛코드로 묶어 **세 번의 답**으로 수백 행을 덮는다", "읽는 순서 — 범례 → 그 장 NOTES → 사람 → 설정 폴백 → 빈칸 · 사람은 도면을 이기지 않는다", "지정한 값은 다음 분석부터 적용 — 판에 상주하는 줄이 그렇게 말한다"], CX + cw + 0.25, cy, cw, 6.85 - cy);
}

feature("전체", "마크업 — 누락 행 추가 · 오검출 표시", "사각형을 그리면 도면을 먼저 읽어 값을 제안한다", ["＋행", "✕"], "markup", "동작", [
  "마크업 모드에서 사각형을 끌면 그 자리의 **별표 · NOTES · 같은 장 수량 · TYPE** 을 읽어 제안",
  "제안을 그대로 두면 출처 DRAWING, 바꾸거나 채우면 USER — 근거 패널이 그대로 말한다",
  "추가 행은 녹색 음영 · 안정 ID 는 같은 장부에서 · 다음 리비전에 엔진이 그 자리를 찾으면 잇는다",
  "기존 상자 ✕ — 오검출 · 값 틀림 · 미지정 심볼 분류 + 사유 · 행은 지우지 않고 표시만",
  "'개발팀에 VOC 로 신고' 가 기본 켜짐 — 사유를 적어야 저장된다"], S3);

feature("전체", "개정 대조 — 나란히 보기", "왼쪽 최신 Rev.B · 오른쪽 직전 Rev.A · 태그로만 대조", ["ADD", "MOD", "DEL?"], "side", "동작", [
  "실행 프로젝트는 **(TYPE, 태그)** 로 짝을 짓는다 — 위치 좌표로는 비교하지 않는다",
  "같은 도면에 새 태그와 사라진 태그가 함께 남으면 전부 **수정(MOD)** · 한쪽만이면 추가 / 삭제 후보",
  "도면번호가 바뀐 장은 공유 태그로 알아보고 옛 번호 장을 오른쪽에 띄운다",
  "오른쪽 도면 아래 **이 장 변경 목록** · ◀ ▶ 로 두 창이 그 자리로 · 확대·스크롤이 함께 움직인다",
  "'대조 다시' — 재분석 없이 새 규칙으로 다시 대조 · 변경 내역 Excel 로 내보내기"], S3);

// 13 memo & pin
{
  const s = base("전체", "장별 메모 · 핀 메모", "도면번호를 열쇠로 같은 프로젝트의 모든 Rev 에서 보인다", ["📌"], S3);
  const iw = 6.6, ih = iw * 9 / 16;
  img(s, "pin", CX, 1.6, iw, ih);
  card(s, "동작", ["도면 아래 **장별 메모장** — 저장 한 번이 판 하나, 지우지 않고 쌓인다 · 다른 Rev 에서 쓴 판은 표식과 함께", "**📌 핀 메모 달기** → 도면을 누르면 압정이 꽂히고 작성칸에 날짜·작성자(로그인)가 자동", "메모장의 메모를 누르면 도면이 그 자리로 가서 압정이 두 번 깜박임 · 압정을 누르면 메모장이 그 메모로", "완료 · 숨김은 표시뿐 — 고친 글은 이력으로 남는다", "도면번호가 바뀐 장도 옛 번호의 메모를 함께 보인다"], CX + iw + 0.25, 1.6, CW - iw - 0.25, ih, 11);
  img(s, "memo", CX, 5.55, 4.5, 1.3);
  s.addText("장별 메모장 — 지금 메모 · 이력 판 · '다른 Rev 에서' 표식. 저장은 프로젝트 폴더의 sheet_notes.json 한 곳", { x: CX + 4.7, y: 5.55, w: CW - 4.7, h: 1.3, fontSize: 11.5, color: THEME.colors.accent6, valign: "middle", margin: 0, isTextBox: true, objectName: "memo note" });
}

feature("검토필요", "검토 탭 — 사유별로 묶어 처리", "검토 축 다섯 · 필터 · 검색 · 개정 필터", ["검토필요"], "review", "동작", [
  "검토 축 — **스코프 판정 · 수량 · Description · 검출 · 입력 자료** (등록 안 된 사유는 OTHER 로 보이고 숨기지 않음)",
  "행마다 미처리 · 확인함 · 수정함 · 보류 — 한 일만 저장",
  "검색(Ctrl+F) · 귀속 · 검토 필요만 · 개정 필터(추가만 · 수정만 · 삭제만) · 열별 필터",
  "Description 일괄 적용 — 같은 도면 · 같은 TYPE · 같은 문장인 묶음에 한 번에",
  "이름표(접미) · 사용자 입력 사유는 근거 패널에 SUFFIX: 로 남는다"], S3);

pres.addSection({ title: S4 });
feature("전체", "출력과 신고", "최종 저장 · Excel 출력 · 변경 내역 Excel · VOC", ["Excel", "VOC"], "voc", "출력", [
  "**최종 저장** — 편집·삭제·마크업을 스냅샷으로 굳히고 첫 화면 저장 이력에",
  "**Excel 출력** — 발주처 양식 FIELD · MOV · BFV 에 그대로 (REMARK 앞머리에 개정·사용자 추가·오검출 표시)",
  "**변경 내역 Excel** — 요약 · 추가 · 수정 · 삭제 · 장",
  "**VOC** — 못 읽은 것·틀린 것·바라는 기능을 분류 + 사유 + 이름만 적으면 서버가 분석·장·행·엔진 값·도면 조각을 담아 VOC 함에 쌓는다",
  "반영된 VOC 는 '반영됨 — hotfixNN' 으로 표시되고 다시 반영되지 않는다"], S4);

// 16 dual
{
  const s = base("전체", "듀얼 모니터 — 도면 · 목록을 새 창으로", "두 창이 같은 결과를 보며 서로 연동된다", ["⧉"], S4);
  const iw = (CW - 0.25) / 2, ih = iw * 9 / 16;
  img(s, "popd", CX, 1.6, iw, ih); img(s, "popl", CX + iw + 0.25, 1.6, iw, ih);
  const cy = 1.6 + ih + 0.25, ch = 6.85 - cy;
  card(s, "동작", ["⧉ 도면 새 창 · ⧉ 목록 새 창 — 각 모니터에 하나씩 전체화면", "목록에서 행을 누르면 도면 창이 그 장·그 상자로 · 도면에서 상자를 누르면 목록 창이 그 행·근거로"], CX, cy, iw, ch);
  card(s, "연동", ["저장은 쓰기 요청이 끝난 것을 보고 알린다 — 받은 창은 **그 행만** 다시 받는다", "장 · 고른 행 · Shift 묶음 · 메모 · 결과 전환이 같이 움직인다 · ⇆ 한 창으로 합치기"], CX + iw + 0.25, cy, iw, ch);
}

feature("전체", "단축키", "이 화면이 실제로 받는 키만 적는다 — ⌨ 단추 또는 도면에서 ?", ["⌨"], "keys", "자주 쓰는 키", [
  "**Ctrl+F** 검색 · **F2** 편집 · Enter / Tab 저장 후 이동 · Esc 되돌림",
  "**Shift+↑↓** 범위 · Ctrl+C / Ctrl+V · **Ctrl+Enter** 범위 채우기 · Delete 도면 값",
  "**Ctrl+Z / Ctrl+Y** 되돌리기 · 다시",
  "Shift+클릭 · Shift+끌기 묶음 선택 · Ctrl+휠 확대 · Alt+← → 변경 이동",
  "메모 Ctrl+Enter 저장 · ⛶ 전체화면 · ? 도움말"], S4);

// 18 speed — tables + stat cards
{
  const s = base("홈 (대시보드)", "속도와 검증", "여러 번 시뮬레이션하며 고친 결과 — 답은 그대로, 시간만 줄었다", ["hotfix69~80"], S4);
  const hdr = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: BLUE }, fontSize: 11.5 } });
  const cell = (t, b) => ({ text: t, options: { color: THEME.colors.dk2, fontSize: 11.5, bold: !!b } });
  const t1 = [[hdr("화면 동작 (QFE 1,991행)"), hdr("이전"), hdr("지금")],
    ...[["결과 열기", "6.3초", "1.9초"], ["장 넘기기", "840ms", "249ms"], ["검색 한 글자", "1,065ms", "148ms"], ["목록 끝까지 굴리기", "2.4초", "1.1초"], ["묶은 73행 공급 주체 바꾸기", "847ms (요청 73)", "215ms (요청 1)"], ["묶은 20행 식별 지우기", "10.9초", "0.42초"]].map(r => [cell(r[0]), cell(r[1]), cell(r[2], true)])];
  const t2 = [[hdr("분석 시간 (같은 답)"), hdr("이전"), hdr("지금")],
    ...[["AL NOUF1 · 58장", "830초", "366초"], ["TC2 · 60장 (270° 회전)", "632초", "308초"], ["QFE · 93장", "984초", "554초"], ["UAD · DXF 32장", "—", "67초"]].map(r => [cell(r[0]), cell(r[1]), cell(r[2], true)])];
  const tw1 = 6.3, tw2 = CW - tw1 - 0.3;
  s.addTable(t1, { x: CX, y: 1.6, w: tw1, colW: [2.9, 1.7, 1.7], border: { type: "solid", color: LINE, pt: 0.75 }, fill: { color: CARD }, rowH: 0.36, margin: 0.06, objectName: "table ui speed" });
  s.addTable(t2, { x: CX + tw1 + 0.3, y: 1.6, w: tw2, colW: [tw2 - 2.4, 1.2, 1.2], border: { type: "solid", color: LINE, pt: 0.75 }, fill: { color: CARD }, rowH: 0.36, margin: 0.06, objectName: "table analysis speed" });
  const stats = [["1,060", "빠른 시험 통과 (18 건너뜀)"], ["5xx 0", "API 퍼징 · 모든 경로 × 본문 14종"], ["0 결함", "화면 전수 클릭 · 전 흐름 QA 시뮬레이션"], ["4 프로젝트", "회귀 기준선 — 지문·행·Q'ty·축3 불변"]];
  const sw = (CW - 0.6) / 4;
  stats.forEach(([a, b], i) => {
    const x = CX + i * (sw + 0.2), y = 4.75, h = 1.5;
    s.addShape(pres.ShapeType.roundRect, { x, y, w: sw, h, rectRadius: 0.08, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, objectName: "stat card " + a });
    s.addText(a, { x: x + 0.2, y: y + 0.15, w: sw - 0.4, h: 0.7, fontSize: 24, bold: true, color: BLUE, margin: 0, isTextBox: true, valign: "middle", wrap: false, objectName: "stat value " + a });
    s.addText(b, { x: x + 0.2, y: y + 0.85, w: sw - 0.4, h: 0.55, fontSize: 11, color: THEME.colors.accent6, margin: 0, isTextBox: true, valign: "top", objectName: "stat label " + a });
  });
  s.addText("측정은 같은 기계에서 옛 코드와 새 코드를 번갈아 재는 A/B 자(spike/perf_ab.py · perf_sim.py)로 했고, 분석 시간은 네 프로젝트 지문이 같은 채로 줄었습니다.", { x: CX, y: 6.4, w: CW, h: 0.45, fontSize: 11, color: THEME.colors.accent6, margin: 0, isTextBox: true, objectName: "speed note" });
}

// 19 closing
{
  const s = pres.addSlide({ masterName: "dark", sectionTitle: S4 });
  s.addText("운영", { x: 0.9, y: 0.7, w: 5, h: 0.4, fontSize: 13, color: "B9C4D8", charSpacing: 3, margin: 0, isTextBox: true, objectName: "closing kicker" });
  s.addText("부서 대시보드 안에서 그대로 쓴다", { x: 0.9, y: 1.15, w: 11.5, h: 0.9, fontSize: 36, bold: true, color: "FFFFFF", margin: 0, isTextBox: true, objectName: "closing title" });
  const items = [["사내망 서버", "run_lan_service.bat 하나로 포트 8000 · 사내망 주소만 받는 문지기 · 멈추면 10초 뒤 다시"],
    ["대시보드 임베드", "입찰/실행 메뉴 → P&ID 분석 iframe · 로그인 이름이 작성자로 자동 · ?embed=1&mode=&user="],
    ["업데이트", "변경분 꾸러미(apply_to_PID_dev · ops) · 첫 화면 오른쪽 아래 업데이트 딱지 · 옛 탭이면 새로고침 띠"],
    ["VOC → 개발", "부서원 신고가 voc/inbox 에 쌓이고 개발 PC 의 Claude Code 가 읽어 반영 · 장부로 중복 반영 방지"]];
  const cw = (W - 1.8 - 0.6) / 4;
  items.forEach(([t, d], i) => {
    const x = 0.9 + i * (cw + 0.2), y = 2.5, h = 2.9;
    s.addShape(pres.ShapeType.roundRect, { x, y, w: cw, h, rectRadius: 0.08, fill: { color: "2A3750" }, line: { color: "3D4B66", width: 0.75 }, objectName: "closing card " + t });
    s.addText(t, { x: x + 0.2, y: y + 0.2, w: cw - 0.4, h: 0.45, fontSize: 16, bold: true, color: "FFD66B", margin: 0, isTextBox: true, objectName: "closing card title " + t });
    s.addText(d, { x: x + 0.2, y: y + 0.75, w: cw - 0.4, h: h - 0.95, fontSize: 12.5, color: "DFE6F3", margin: 0, isTextBox: true, valign: "top", lineSpacingMultiple: 1.2, objectName: "closing card body " + t });
  });
  s.addText("문의 · VOC 는 화면 머리줄 [VOC] 단추로 — 분류 · 사유 · 이름만 적으면 나머지는 서버가 담습니다", { x: 0.9, y: 6.3, w: 11.5, h: 0.4, fontSize: 13, color: "B9C4D8", margin: 0, isTextBox: true, objectName: "closing note" });
  s.addNotes("운영 절차는 docs/dashboard_embed.md · docs/voc.md 에 있습니다.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
