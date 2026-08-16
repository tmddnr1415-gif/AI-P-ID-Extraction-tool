/* 브라우저에서 P&ID PDF를 도면 단위로 훑는 모듈.
 *
 * 파이썬 scripts/pdf_to_images.py 와 같은 일을 한다:
 *   - 타이틀블록에서 도면번호와 도면명을 읽는다
 *   - 1쪽 DRAWING LIST와 대조해 번호 충돌을 찾아낸다
 *   - 텍스트 레이어에서 계기 문자를 좌표와 함께 뽑는다 (판독 기준선)
 *   - 전체 도면 1장 + 겹침 타일 N장을 이미지로 만든다
 *
 * 대형 도면(33"×23")을 통째로 모델 최대 해상도에 밀어넣으면 계기 버블 글자가
 * 뭉개지므로, 맥락용 전체 이미지와 판독용 확대 타일을 함께 만든다.
 *
 * 의존: pdfjsLib (vendor/pdf.min.js)
 */
'use strict';

const PDFScan = (() => {
  const MAX_EDGE = 2576;              // 모델이 지원하는 이미지 최대 장변(px)
  const DRAWING_NO = /D00P-[0-9A-Z]{5,9}-M\d{2}-\d{4}/g;

  // 텍스트 레이어에서 계기로 볼 문자. 긴 것부터 본다.
  const TOKENS = [
    'LSHH', 'LSLL', 'PDIT', 'PDSH', 'LSH', 'LSL', 'PSH', 'PSL', 'TSH', 'TSL',
    'PIT', 'TIT', 'LIT', 'FIT', 'AIT', 'PDI', 'PDT', 'FQI',
    'PI', 'TI', 'LI', 'FI', 'AI', 'PT', 'TT', 'LT', 'FT', 'AT',
    'PS', 'TS', 'LS', 'FS', 'ZS', 'FE', 'RO', 'TE', 'PE', 'LE', 'AE',
  ];
  const TOKEN_SET = new Set(TOKENS);

  /** 도면명을 비교 가능한 토큰 집합으로 정규화한다 ('&'→'AND', 번호/괄호 무시). */
  function normTitle(s) {
    const up = (s || '').toUpperCase().replace(/&/g, ' AND ');
    const drop = new Set(['P', 'ID', 'FOR', 'AND', 'OF', 'THE', 'GROUP', 'UNIT']);
    return new Set((up.match(/[A-Z]+/g) || []).filter((t) => t.length > 1 && !drop.has(t)));
  }
  function titlesAgree(a, b) {
    const ta = normTitle(a); const tb = normTitle(b);
    if (!ta.size || !tb.size) return true;
    let n = 0;
    for (const t of ta) if (tb.has(t)) n++;
    return n / Math.min(ta.size, tb.size) >= 0.6;
  }

  /** 텍스트 아이템을 0~1 정규화 좌표와 함께 뽑는다. */
  async function textItems(page, viewportSize) {
    const content = await page.getTextContent();
    const { width: W, height: H } = viewportSize;
    return content.items
      .filter((it) => it.str && it.str.trim())
      .map((it) => {
        const [, , , , x, y] = it.transform;
        return { str: it.str.trim(), x: x / W, y: 1 - y / H };   // PDF 원점은 좌하단
      });
  }

  function joinRegion(items, pred) {
    return items.filter(pred).sort((a, b) => a.y - b.y || a.x - b.x).map((i) => i.str).join('\n');
  }

  /* GENERAL NOTES / NOTES 블록.
   *
   * 이 블록이 판독의 절반이다. `* DENOTES ... SUPPLIED BY HRSG` 같은 공급 범위 각주와
   * `CONFIGURATION IS IDENTICAL FOR GROUP#20` 이 여기 있고, 각각 어느 계기를 뺄지와
   * Q'ty를 정한다. 위치를 놓치면 모델이 그 판단 근거를 아예 못 본다.
   *
   * 좌표를 고정하지 않고 `GENERAL NOTES` / `NOTES :` 글자를 찾아 그 아래·오른쪽을 딸려
   * 온다. 도면 양식이 달라도 따라간다. 못 찾으면 우상단을 넓게 훑는다.
   */
  function findNotes(items) {
    const anchors = items.filter((i) => /^(GENERAL\s+)?NOTES?\s*:?$/i.test(i.str));
    if (anchors.length) {
      const x0 = Math.min(...anchors.map((a) => a.x)) - 0.03;
      const y0 = Math.min(...anchors.map((a) => a.y)) - 0.01;
      const block = joinRegion(items, (i) => i.x >= x0 && i.y >= y0 && i.y < y0 + 0.55);
      if (block.length > 40) return block.slice(0, 4000);
    }
    return joinRegion(items, (i) => i.x > 0.72 && i.y < 0.60).slice(0, 4000);
  }

  function scanPage(items) {
    // 타이틀블록: 우하단
    const tb = joinRegion(items, (i) => i.x > 0.55 && i.y > 0.78);
    const nums = tb.match(DRAWING_NO) || [];
    let title = null;
    for (const line of tb.split('\n')) {
      if (line.toUpperCase().includes('P&ID FOR')) { title = line.replace(/\s+/g, ' ').trim(); break; }
    }
    if (!title) {
      const i = tb.toUpperCase().indexOf('P&ID FOR');
      if (i >= 0) title = tb.slice(i, i + 90).replace(/\s+/g, ' ').trim();
    }
    const notes = findNotes(items);
    // 계기 문자 후보
    const candidates = items
      .filter((i) => TOKEN_SET.has(i.str.replace(/[.,;:()[\]]/g, '')))
      .map((i) => ({ token: i.str.replace(/[.,;:()[\]]/g, ''), x: +i.x.toFixed(4), y: +i.y.toFixed(4) }))
      .sort((a, b) => a.y - b.y || a.x - b.x);

    return { drawing_no: nums.length ? nums[nums.length - 1] : null, title, notes, candidates,
             labels: sheetLabels(items) };
  }

  /* 도면 안쪽 글자 라벨 — 설비 박스 이름과 배관 행선지.
   *
   * DESCRIPTION 을 이걸로 자동 조립해 보았으나 시험 3장에서 69행 중 6행만 맞았다.
   * 어느 라벨을 고를지와 어떻게 부를지가 곧 판독이라 좌표만으로는 안 된다.
   * 그래서 문장을 지어내지 않고, 계기마다 가장 가까운 라벨을 근거로 붙여 준다.
   * 사람이 DESCRIPTION 을 쓸 때 도면을 뒤지지 않아도 되게 하는 용도다.
   */
  const EQUIP_HINT = /\b(COOLER|COOLERS|PUMP|TANK|DRUM|SYSTEM|TURBINE|BOILER|HEATER|ECONOMIZER|VESSEL|FAN|COMPRESSOR|FILTER|HEADER)\b/i;
  const SECTION = /\b(SUPPLY|RETURN|DRAIN|DISCHARGE|SUCTION|INLET|OUTLET|BYPASS|VENT)\b/i;
  const LABEL_NOISE = /SAMSUNG|PROJECT|DRAWING|SHEET|SCALE|PROPERTY|INTERNAL USE|AL NOUF|EMPLOYER|TENDERER|PREPARED|REFER TO|DENOTES|CONFIGURATION|THIS DRAWING|MARKED ITEM|NOTES|SHALL BE|IDENTICAL/i;

  function sheetLabels(items) {
    const out = [];
    for (const i of items) {
      const t = i.str;
      if (i.x > 0.78 || (i.x > 0.55 && i.y > 0.78)) continue;   // 노트·타이틀블록
      if (t.length < 6 || DRAWING_NO.test(t) || LABEL_NOISE.test(t)) continue;
      if (!/[A-Z]{3,}/.test(t)) continue;
      // 'TO HRSG#12 BD TANK' 은 설비명이 아니라 행선지다. 설비 후보에서 뺀다.
      const line = /^(TO|FROM)\b/i.test(t) || SECTION.test(t);
      const equip = !/^(TO|FROM)\b/i.test(t) && EQUIP_HINT.test(t);
      if (!line && !equip) continue;
      out.push({ t, x: +i.x.toFixed(4), y: +i.y.toFixed(4), kind: equip ? 'equip' : 'line' });
    }
    return out.slice(0, 80);
  }

  /** 1쪽 DRAWING LIST에서 도면번호 → 도면명 대조표 */
  function drawingList(items) {
    const lines = new Map();
    for (const it of items) {
      const k = Math.round(it.y * 400);            // 같은 행끼리 묶기
      if (!lines.has(k)) lines.set(k, []);
      lines.get(k).push(it);
    }
    const out = {};
    for (const arr of lines.values()) {
      arr.sort((a, b) => a.x - b.x);
      const joined = arr.map((i) => i.str).join(' ');
      const m = joined.match(/D00P-[0-9A-Z]{5,9}-M\d{2}-\d{4}/);
      if (!m) continue;
      const rest = joined.slice(joined.indexOf(m[0]) + m[0].length).replace(/^[\s\-–—]+/, '').trim();
      if (rest) out[m[0]] = rest.replace(/\s+/g, ' ');
    }
    return out;
  }

  function canvasToBase64(canvas) {
    return canvas.toDataURL('image/png').split(',')[1];
  }

  async function renderRegion(page, region, maxEdge, dpiScale) {
    const base = page.getViewport({ scale: 1 });
    const [x0, y0, x1, y1] = region;
    const wPt = base.width * (x1 - x0);
    const hPt = base.height * (y1 - y0);
    const scale = Math.min(dpiScale, maxEdge / Math.max(wPt, hPt));

    const viewport = page.getViewport({ scale });
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(wPt * scale);
    canvas.height = Math.round(hPt * scale);
    const ctx = canvas.getContext('2d', { willReadFrequently: false });
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    await page.render({
      canvasContext: ctx,
      viewport,
      transform: [1, 0, 0, 1, -x0 * base.width * scale, -y0 * base.height * scale],
    }).promise;
    const b64 = canvasToBase64(canvas);
    const size = [canvas.width, canvas.height];
    canvas.width = canvas.height = 0;             // 메모리 반환
    return { b64, size };
  }

  /**
   * PDF 전체를 훑어 페이지 목록을 만든다. 이미지는 아직 만들지 않는다(무겁다).
   * onProgress(done, total)
   */
  async function scan(arrayBuffer, onProgress) {
    const doc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    const pages = [];
    let listing = {};

    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      const vp = page.getViewport({ scale: 1 });
      const items = await textItems(page, vp);
      if (n === 1) listing = drawingList(items);
      const info = scanPage(items);
      pages.push({
        page: n,
        drawing_no: info.drawing_no,
        title: info.title,
        notes: info.notes,
        candidates: info.candidates,
        labels: info.labels,
        page_size_pt: [Math.round(vp.width), Math.round(vp.height)],
        conflicts: [],
        is_legend: /GEN00/.test(info.drawing_no || '')
          || /SYMBOL|LEGEND|DRAWING LIST/i.test(info.title || ''),
      });
      page.cleanup();
      if (onProgress) onProgress(n, doc.numPages);
    }

    for (const p of pages) {
      const listed = listing[p.drawing_no];
      if (listed && p.title && !titlesAgree(p.title, listed)) {
        p.conflicts.push(`타이틀블록 제목('${p.title}')과 DRAWING LIST('${listed}')가 다릅니다`);
      }
    }
    const seen = new Map();
    for (const p of pages) {
      if (!p.drawing_no) { p.conflicts.push('타이틀블록에서 도면번호를 읽지 못했습니다'); continue; }
      if (seen.has(p.drawing_no)) {
        p.conflicts.push(`도면번호가 ${seen.get(p.drawing_no)}쪽과 중복입니다`);
      } else seen.set(p.drawing_no, p.page);
    }

    return { doc, pages, drawingList: listing, pageCount: doc.numPages };
  }

  /** 한 페이지의 이미지(전체 1장 + 타일)를 만든다. */
  async function renderPage(doc, pageNo, { cols = 3, rows = 2, overlap = 0.08, dpi = 200 } = {}) {
    const page = await doc.getPage(pageNo);
    const dpiScale = dpi / 72;
    const full = await renderRegion(page, [0, 0, 1, 1], MAX_EDGE, dpiScale);
    const tiles = [];
    if (cols > 0 && rows > 0) {
      for (let j = 0; j < rows; j++) {
        for (let i = 0; i < cols; i++) {
          const region = [
            Math.max(0, i / cols - overlap / cols),
            Math.max(0, j / rows - overlap / rows),
            Math.min(1, (i + 1) / cols + overlap / cols),
            Math.min(1, (j + 1) / rows + overlap / rows),
          ];
          const img = await renderRegion(page, region, MAX_EDGE, dpiScale);
          tiles.push({ row: j, col: i, region: region.map((v) => +v.toFixed(4)), ...img });
        }
      }
    }
    page.cleanup();
    return { full, tiles };
  }

  return { scan, renderPage, MAX_EDGE, TOKENS, titlesAgree };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = PDFScan;
