/* 브라우저에서 Excel 템플릿을 읽고 쓰는 모듈.
 *
 * 쓰기는 "템플릿을 복사하고 데이터 행만 갈아끼우는" 방식이다. 시트 XML 한 개만
 * 다시 쓰고 나머지 파트(스타일, 병합 헤더, 인쇄 설정, 숨김 시트, 외부 링크)는
 * 원본 바이트 그대로 두기 때문에 서식이 그대로 남는다.
 *
 * 셀 스타일은 템플릿 첫 데이터 행(8행)의 열별 s 인덱스를 그대로 재사용한다.
 * 문자열은 inlineStr로 써서 sharedStrings.xml을 건드리지 않는다.
 *
 * 의존: fflate (unzipSync / zipSync)
 */
'use strict';

const XLSX = (() => {
  // 열 문자 → [키, 값의 출처]. scripts/inspect_template.py 의 COLUMN_PLAN과 같아야 한다.
  const COLUMN_PLAN = {
    A: ['no', 'auto_index'], B: ['unit', 'blank'], C: ['system_code', 'blank'],
    D: ['system_sequence', 'blank'], E: ['tag', 'blank'], F: ['system', 'drawing'],
    G: ['pid_no', 'drawing'], H: ['type', 'drawing'], I: ['qty', 'drawing'],
    J: ['description', 'drawing'], K: ['design_table_no', 'design_table'],
    L: ['op_mass_flow', 'design_table'], M: ['op_pressure', 'design_table'],
    N: ['op_temperature', 'design_table'], O: ['des_mass_flow', 'design_table'],
    P: ['des_pressure', 'design_table'], Q: ['des_temperature', 'design_table'],
    R: ['pipe_material', 'design_table'], S: ['pipe_nb', 'design_table'],
    T: ['pipe_sch', 'design_table'], U: ['rating', 'design_table'],
    V: ['velocity_criteria', 'design_table'], W: ['fluid', 'design_table'],
    X: ['inst_typical_type', 'drawing'], Y: ['sensing_type', 'typical'],
    Z: ['element_type', 'typical'], AA: ['mounting_type', 'typical'],
    AB: ['signal_type', 'typical'], AC: ['calibration_range', 'design_table'],
    AD: ['calibration_unit', 'design_table'], AE: ['element_material', 'design_table'],
    AF: ['connection_type', 'design_table'], AG: ['tw_chamber_spec', 'design_table'],
    AH: ['explosion_proof', 'design_table'], AI: ['base_option', 'typical'],
    AJ: ['body_material', 'blank'], AK: ['scope_of_supply', 'blank'],
    AL: ['maker', 'blank'], AM: ['model', 'blank'], AN: ['status', 'blank'],
    AO: ['remark', 'drawing'], AP: ['note', 'review'],
  };

  const TYPICAL_KEYS = Object.values(COLUMN_PLAN)
    .filter(([, s]) => s === 'typical').map(([k]) => k);

  const dec = new TextDecoder();
  const enc = new TextEncoder();

  const colOf = (ref) => ref.match(/^[A-Z]+/)[0];
  const rowOf = (ref) => parseInt(ref.match(/(\d+)$/)[1], 10);

  function unesc(s) {
    return s.replace(/&#(\d+);/g, (_, d) => String.fromCharCode(+d))
      .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&');
  }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      // 엑셀이 허용하지 않는 제어문자 제거
      .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '');
  }

  /** <si> 안의 텍스트 조각을 모두 이어붙인다 (서식 조각 t 여러 개일 수 있음). */
  function sharedStrings(files) {
    const part = files['xl/sharedStrings.xml'];
    if (!part) return [];
    const xml = dec.decode(part);
    const out = [];
    for (const si of iterTags(xml, 'si')) {
      // 발음 표기(rPh)는 셀 값이 아니므로 뺀다.
      const body = si.inner.replace(/<rPh[\s\S]*?<\/rPh>/g, '');
      let text = '';
      for (const t of iterTags(body, 't')) text += unesc(t.inner);
      out.push(text);
    }
    return out;
  }

  /**
   * XML에서 특정 태그를 훑는다.
   *
   * 정규식 하나로 `<c .../>` 와 `<c ...>값</c>` 를 동시에 다루면, 자기닫힘 태그의
   * 슬래시까지 속성으로 먹어치우고 다음 태그의 닫는 짝을 찾아가 셀 하나가
   * 통째로 사라진다. 그래서 여는 태그만 정규식으로 찾고 닫는 위치는 직접 센다.
   */
  function* iterTags(xml, tag) {
    const open = new RegExp(`<${tag}\\b([^>]*?)(\\/)?>`, 'g');
    const close = `</${tag}>`;
    let m;
    while ((m = open.exec(xml))) {
      const startIdx = m.index;
      if (m[2]) {                                  // 자기닫힘
        yield { attrs: m[1], inner: '', source: m[0] };
        continue;
      }
      const end = xml.indexOf(close, open.lastIndex);
      const stop = end < 0 ? xml.length : end;
      yield { attrs: m[1], inner: xml.slice(open.lastIndex, stop),
              source: xml.slice(startIdx, stop + close.length) };
      open.lastIndex = stop + close.length;
    }
  }

  const attrOf = (attrs, name) => (attrs.match(new RegExp(`\\b${name}="([^"]*)"`)) || [])[1];

  /** 워크북에서 시트 이름 → 시트 XML 경로 */
  function sheetPaths(files) {
    const wb = dec.decode(files['xl/workbook.xml']);
    const rels = dec.decode(files['xl/_rels/workbook.xml.rels']);
    const relMap = {};
    for (const m of rels.matchAll(/<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"/g)) {
      relMap[m[1]] = m[2].replace(/^\//, '');
    }
    const out = {};
    for (const m of wb.matchAll(/<sheet[^>]*name="([^"]+)"[^>]*r:id="([^"]+)"/g)) {
      let t = relMap[m[2]] || '';
      if (t && !t.startsWith('xl/')) t = 'xl/' + t;
      out[unesc(m[1])] = t;
    }
    return out;
  }

  /** 시트 XML을 행 → (열 → {v, s}) 로 훑는다. */
  function scanSheet(xml, sst) {
    const rows = new Map();
    for (const row of iterTags(xml, 'row')) {
      const rn = +attrOf(row.attrs, 'r');
      if (!rn) continue;
      const cells = new Map();
      for (const cell of iterTags(row.inner, 'c')) {
        const ref = attrOf(cell.attrs, 'r');
        if (!ref) continue;
        const s = attrOf(cell.attrs, 's');
        const t = attrOf(cell.attrs, 't');
        let v = '';
        if (t === 'inlineStr') {
          for (const tm of iterTags(cell.inner, 't')) v += unesc(tm.inner);
        } else {
          const iv = (cell.inner.match(/<v[^>]*>([\s\S]*?)<\/v>/) || [])[1];
          if (iv != null) v = t === 's' ? (sst[+iv] ?? '') : unesc(iv);
        }
        cells.set(colOf(ref), { v, s });
      }
      rows.set(rn, cells);
    }
    return rows;
  }

  /**
   * 템플릿을 해부해 컬럼 스펙과 TYPICAL 표, 허용 값 목록을 만든다.
   * scripts/inspect_template.py 와 같은 판단을 브라우저에서 그대로 한다.
   */
  function analyzeTemplate(bytes, opts = {}) {
    const sheetName = opts.sheet || '2.0_Instrument List';
    const headerRow = opts.headerRow || 6;
    const subRow = headerRow + 1;
    const dataStart = opts.dataStart || 8;

    const files = fflate.unzipSync(bytes);
    const paths = sheetPaths(files);
    const sheetPath = paths[sheetName];
    if (!sheetPath) {
      throw new Error(`'${sheetName}' 시트를 찾을 수 없습니다. 이 파일의 시트: ${Object.keys(paths).join(', ')}`);
    }
    const sst = sharedStrings(files);
    const rows = scanSheet(dec.decode(files[sheetPath]), sst);

    const columns = [];
    for (const [col, [key, source]] of Object.entries(COLUMN_PLAN)) {
      const label = (rows.get(headerRow)?.get(col)?.v || '').replace(/\s+/g, ' ').trim();
      const sub = (rows.get(subRow)?.get(col)?.v || '').replace(/\s+/g, ' ').trim();
      columns.push({ col, key, label: label || sub, sub_label: sub, source });
    }

    // 데이터 행 (A열이 숫자인 행)
    const data = [];
    for (const [rn, cells] of [...rows.entries()].sort((a, b) => a[0] - b[0])) {
      if (rn < dataStart) continue;
      const a = cells.get('A')?.v;
      if (!a || !/^\d+$/.test(String(a).trim())) continue;
      const rec = {};
      for (const c of columns) rec[c.key] = (cells.get(c.col)?.v || '').replace(/\s+/g, ' ').trim();
      data.push(rec);
    }

    // TYPICAL TYPE → 사양. X 하나당 값이 하나로 고정되는 컬럼만 남긴다.
    const buckets = {};
    for (const rec of data) {
      const x = rec.inst_typical_type;
      if (!x) continue;
      buckets[x] = buckets[x] || {};
      for (const k of TYPICAL_KEYS) {
        buckets[x][k] = buckets[x][k] || new Map();
        const v = rec[k] || '';
        buckets[x][k].set(v, (buckets[x][k].get(v) || 0) + 1);
      }
    }
    const inconsistent = new Set();
    for (const x of Object.keys(buckets)) {
      for (const k of TYPICAL_KEYS) if (buckets[x][k].size > 1) inconsistent.add(k);
    }
    const typicals = {};
    for (const [x, fields] of Object.entries(buckets)) {
      typicals[x] = {};
      for (const k of TYPICAL_KEYS) {
        if (inconsistent.has(k)) continue;
        typicals[x][k] = [...fields[k].keys()][0] ?? '';
      }
    }
    for (const c of columns) {
      if (c.source === 'typical' && inconsistent.has(c.key)) c.source = 'design_table';
    }

    const uniq = (arr) => [...new Set(arr.filter(Boolean))].sort();
    const typeToTypicals = {};
    /* API 없이 돌릴 때 TYPE만 보고 채울 기본값.
     *
     * TYPE 하나에 TYPICAL이 여럿 붙는다. TIT는 템플릿에서 TIT-3(열전대) 53건과
     * TIT-5(RTD) 46건으로 거의 반반이라 TYPE만 보면 동전 던지기다. 그런데 계통을
     * 함께 보면 갈린다 — 고온 증기는 열전대, 급수는 RTD 쪽이다. 그래서 계통별
     * 최빈값을 먼저 쓰고, 그 계통에 전례가 없을 때만 TYPE 전체 최빈값으로 물러난다. */
    const freq = {};                        // '계통||TYPE' 과 'TYPE' → {TYPICAL: 횟수}
    const bump = (k, v) => { (freq[k] = freq[k] || {})[v] = (freq[k][v] || 0) + 1; };
    for (const rec of data) {
      if (!rec.type || !rec.inst_typical_type) continue;
      (typeToTypicals[rec.type] = typeToTypicals[rec.type] || new Set()).add(rec.inst_typical_type);
      bump(rec.type, rec.inst_typical_type);
      if (rec.system) bump(`${rec.system}||${rec.type}`, rec.inst_typical_type);
    }
    for (const k of Object.keys(typeToTypicals)) typeToTypicals[k] = [...typeToTypicals[k]].sort();
    const typeToTopTypical = {};
    for (const [k, f] of Object.entries(freq)) {
      typeToTopTypical[k] = Object.entries(f).sort((a, b) => b[1] - a[1])[0][0];
    }

    return {
      sheet: sheetName, sheetPath, headerRow, dataStartRow: dataStart,
      columns, typicals,
      instrumentTypes: uniq(data.map((r) => r.type)),
      systems: uniq(data.map((r) => r.system)),
      typeToTypicalTypes: typeToTypicals,
      typeToTopTypical,
      templateRowCount: data.length,
      demotedColumns: [...inconsistent],
    };
  }

  /**
   * 템플릿 바이트 + 판독 결과 → 새 xlsx 바이트.
   * 시트 XML 하나만 다시 쓰고 나머지 파트는 원본 그대로 둔다.
   */
  function buildWorkbook(bytes, records, spec) {
    const files = fflate.unzipSync(bytes);
    const sheetPath = spec.sheetPath;
    let xml = dec.decode(files[sheetPath]);
    const start = spec.dataStartRow;

    // 1) 데이터 행은 잘라내고 헤더 행은 원본 그대로 남긴다.
    //    동시에 템플릿 첫 데이터 행에서 행 속성과 열별 스타일 인덱스를 가져온다.
    const sdOpen = xml.indexOf('<sheetData>');
    const sdClose = xml.indexOf('</sheetData>');
    if (sdOpen < 0 || sdClose < 0) throw new Error('sheetData를 찾지 못했습니다.');
    const head = xml.slice(0, sdOpen + '<sheetData>'.length);
    const body = xml.slice(sdOpen + '<sheetData>'.length, sdClose);
    const tail = xml.slice(sdClose);

    let rowAttrs = ` spans="1:${spec.columns.length}"`;
    const styleOf = {};
    let kept = '';
    for (const row of iterTags(body, 'row')) {
      const rn = +attrOf(row.attrs, 'r');
      if (rn && rn < start) { kept += row.source; continue; }
      if (rn === start) {
        rowAttrs = row.attrs.replace(/\br="\d+"/, '').replace(/\s+/g, ' ').replace(/^ ?/, ' ');
        for (const cell of iterTags(row.inner, 'c')) {
          const ref = attrOf(cell.attrs, 'r');
          const s = attrOf(cell.attrs, 's');
          if (ref && s) styleOf[colOf(ref)] = s;
        }
      }
    }

    // 3) 새 데이터 행을 만든다.
    const out = [];
    records.forEach((rec, i) => {
      const r = start + i;
      let cells = '';
      for (const c of spec.columns) {
        const s = styleOf[c.col];
        const sAttr = s ? ` s="${s}"` : '';
        const value = cellValue(rec, c, i);
        if (value === '' || value == null) {
          cells += `<c r="${c.col}${r}"${sAttr}/>`;
        } else if (typeof value === 'number') {
          cells += `<c r="${c.col}${r}"${sAttr}><v>${value}</v></c>`;
        } else {
          cells += `<c r="${c.col}${r}"${sAttr} t="inlineStr"><is><t xml:space="preserve">${esc(value)}</t></is></c>`;
        }
      }
      out.push(`<row r="${r}"${rowAttrs}>${cells}</row>`);
    });

    xml = head + kept + out.join('') + tail;

    // 4) dimension 갱신 (마지막 열 문자는 템플릿 것을 그대로 쓴다)
    const lastCol = spec.columns[spec.columns.length - 1].col;
    const lastRow = Math.max(start + records.length - 1, start);
    xml = xml.replace(/<dimension ref="[^"]*"\/>/, `<dimension ref="A1:${lastCol}${lastRow}"/>`);

    files[sheetPath] = enc.encode(xml);
    return fflate.zipSync(files, { level: 6 });
  }

  /** 컬럼 출처에 따라 채울 값을 정한다. */
  function cellValue(rec, col, index) {
    switch (col.source) {
      case 'auto_index': return index + 1;
      case 'drawing': {
        const v = rec.values ? rec.values[col.key] : rec[col.key];
        if (col.key === 'qty' && /^\d+$/.test(String(v ?? '').trim())) return +v;
        return v ?? '';
      }
      case 'typical': {
        const v = rec.values ? rec.values[col.key] : rec[col.key];
        return v ?? '';
      }
      case 'review': {
        const v = rec.values ? rec.values[col.key] : rec[col.key];
        return v ?? '';
      }
      default: return '';   // design_table / blank
    }
  }

  return { COLUMN_PLAN, analyzeTemplate, buildWorkbook, sheetPaths, scanSheet, sharedStrings };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = XLSX;
