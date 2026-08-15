/* Claude Messages API 호출 — 도면 한 장당 한 번.
 *
 * 파이썬 scripts/extract_instruments.py 와 같은 프롬프트 구성을 쓴다:
 *   시스템 = 규칙 문서 3종 + 컬럼 정의 + 허용 TYPE/TYPICAL/SYSTEM  (프롬프트 캐시 대상)
 *   사용자 = 전체 도면 이미지 + 확대 타일 + 텍스트 레이어 계기 후보 + 도면 NOTES
 *
 * 규칙 문서는 도면마다 같으므로 cache_control을 걸어 도면 수십 장을 연속 판독해도
 * 규칙 토큰을 반복해서 물지 않는다.
 */
'use strict';

const ClaudeAPI = (() => {
  const API_URL = 'https://api.anthropic.com/v1/messages';
  const API_VERSION = '2023-06-01';

  const COL_HINT = {
    system: '계통명. 도면 제목과 아래 SYSTEM 목록에서 고른다 (예: HP Steam System)',
    pid_no: '이 도면의 P&ID 도면번호. 타이틀블록 값을 그대로 쓴다',
    type: '계기 타입 약어',
    qty: '같은 사양·같은 용도로 중복 설치되는 수량. 숫자만',
    description: "UNIT 번호 + 설비/계통 + 측정 대상 + 서브 식별자. 예: 'UNIT #11 HP STEAM PRESSURE A'",
    inst_typical_type: 'INST. TYPICAL TYPE (예: PIT-1, TIT-3). 허용 목록에서만 고른다',
    remark: 'ADD / DEL 등 개정 표기나 Vendor Scope 등 특기사항. 없으면 "-"',
  };

  function drawingColumns(spec) {
    return spec.columns.filter((c) => c.source === 'drawing');
  }

  function buildSchema(spec) {
    const props = {};
    for (const c of drawingColumns(spec)) {
      props[c.key] = { type: 'string', description: COL_HINT[c.key] || c.label };
    }
    props.source_tokens = {
      type: 'string',
      description: "이 행의 근거가 된 도면상 계기 문자와 대략 위치. 예: 'PT ×2 @ 좌상단 HP스팀 헤더'",
    };
    props.confidence = {
      type: 'string', enum: ['high', 'medium', 'low'],
      description: '판독 확신도. 글자가 흐리거나 맥락 추정이 섞였으면 low',
    };
    const required = [...drawingColumns(spec).map((c) => c.key), 'source_tokens', 'confidence'];

    return {
      type: 'object',
      properties: {
        instruments: {
          type: 'array',
          description: '이 도면에서 판독한 Field Instrument. 도면 위→아래, 좌→우 순서.',
          items: { type: 'object', properties: props, required, additionalProperties: false },
        },
        excluded: {
          type: 'array',
          description: '계기 문자로 보였지만 목록에서 제외한 것과 그 이유. 누락 추적용이므로 반드시 남긴다.',
          items: {
            type: 'object',
            properties: {
              token: { type: 'string' },
              location: { type: 'string' },
              reason: { type: 'string' },
            },
            required: ['token', 'location', 'reason'], additionalProperties: false,
          },
        },
        review_findings: {
          type: 'array',
          description: '사람이 확인해야 할 사항(판독 불가, 태그 불일치, 규칙 충돌 등)',
          items: {
            type: 'object',
            properties: {
              severity: { type: 'string', enum: ['high', 'medium', 'low'] },
              location: { type: 'string' },
              finding: { type: 'string' },
              recommendation: { type: 'string' },
            },
            required: ['severity', 'location', 'finding', 'recommendation'], additionalProperties: false,
          },
        },
        page_summary: { type: 'string', description: '이 도면에서 무엇을 몇 건 뽑았는지 2~3문장' },
      },
      required: ['instruments', 'excluded', 'review_findings', 'page_summary'],
      additionalProperties: false,
    };
  }

  function systemPrompt(spec, rules) {
    const L = [
      '당신은 P&ID 도면에서 Field Instrument 목록을 뽑아 표준 Instrument List로 옮기는 계장 엔지니어입니다.',
      '이 결과물은 실제 플랜트 설계에 쓰이는 안전 관련 문서입니다. 도면에 없는 것을 만들어내는 것이',
      '빠뜨리는 것보다 훨씬 위험합니다. 확신이 없으면 confidence를 low로 두고 review_findings에 남기세요.',
    ];
    for (const [name, text] of Object.entries(rules)) {
      if (!text || !text.trim()) continue;
      L.push('', '='.repeat(70), `# 규칙 문서: ${name}`, '='.repeat(70), text.trim());
    }

    L.push('', '='.repeat(70), '# 출력 대상 컬럼', '='.repeat(70));
    for (const c of drawingColumns(spec)) L.push(`- ${c.key} (${c.label}): ${COL_HINT[c.key] || ''}`);

    L.push('', `허용 TYPE: ${spec.instrumentTypes.join(', ')}`, '', 'TYPE별 허용 INST. TYPICAL TYPE:');
    for (const [t, xs] of Object.entries(spec.typeToTypicalTypes)) {
      const desc = xs.map((x) => {
        const e = spec.typicals[x] || {};
        return `${x}(${e.element_type || '?'}/${e.mounting_type || '?'})`;
      });
      L.push(`  ${t}: ${desc.join(', ')}`);
    }
    L.push('', `허용 SYSTEM(계통명): ${spec.systems.join(', ')}`);

    L.push('', '='.repeat(70), '# 작업 방식', '='.repeat(70),
      "1. 첨부된 '텍스트 레이어 계기 문자 후보'는 PDF에서 결정적으로 추출한 것이라 위치와 개수가 정확합니다.",
      '   이 목록을 기준선으로 삼되, 그대로 옮기지는 마세요. 후보 하나하나가 Field Instrument인지',
      '   도면 이미지에서 확인하고, 아니면 excluded에 이유와 함께 넣습니다.',
      '2. 후보에 없더라도 이미지에서 계기를 발견하면 추가하고 source_tokens에 그 사실을 적습니다.',
      '3. 같은 사양·같은 용도로 나란히 설치된 계기는 한 행으로 합치고 qty에 개수를 적습니다.',
      '   서로 다른 측정점(A/B 계열 등 식별자가 다른 것)은 별도 행으로 둡니다.',
      '4. DESCRIPTION은 도면의 From/To 라벨과 설비 이름을 근거로 작성합니다. 영문 대문자로 씁니다.',
      '5. 밸브 리밋스위치(ZS), 밸브 액추에이터, 벤더 패키지 내부 계기는 이번 범위가 아니므로',
      '   excluded에 넣습니다.');
    return L.join('\n');
  }

  function imageBlock(b64) {
    return { type: 'image', source: { type: 'base64', media_type: 'image/png', data: b64 } };
  }

  function userContent(page, images) {
    const content = [{
      type: 'text',
      text: `# 판독 대상 도면\n- 도면번호: ${page.drawing_no}\n- 도면명: ${page.title}\n- PDF 페이지: ${page.page}\n`,
    }];
    content.push({ type: 'text', text: '## 전체 도면' });
    content.push(imageBlock(images.full.b64));
    for (const t of images.tiles) {
      content.push({
        type: 'text',
        text: `## 확대 타일 r${t.row}c${t.col} (도면 내 영역 x ${t.region[0]}~${t.region[2]}, y ${t.region[1]}~${t.region[3]})`,
      });
      content.push(imageBlock(t.b64));
    }
    const lines = page.candidates.map((c) => `${c.token} @ (x=${c.x}, y=${c.y})`);
    content.push({
      type: 'text',
      text: `## 텍스트 레이어 계기 문자 후보 (${page.candidates.length}건, 좌표는 도면 대비 0~1 정규화, 위→아래 순)\n${lines.join('\n')}`,
    });
    if (page.notes) content.push({ type: 'text', text: `## 도면 GENERAL NOTES / NOTES\n${page.notes}` });
    content.push({
      type: 'text',
      text: '이 도면의 Field Instrument 목록을 만드세요. 제외한 후보는 반드시 excluded에 이유를 남기세요.',
    });
    return content;
  }

  /** 도면 한 장을 판독한다. onDelta(누적문자수)로 진행 상황을 알린다. */
  async function extractDrawing({ apiKey, model, effort, maxTokens, system, schema, page, images,
                                  signal, onDelta }) {
    const body = {
      model,
      max_tokens: maxTokens,
      stream: true,
      thinking: { type: 'adaptive' },
      system: [{ type: 'text', text: system, cache_control: { type: 'ephemeral' } }],
      output_config: { effort, format: { type: 'json_schema', schema } },
      messages: [{ role: 'user', content: userContent(page, images) }],
    };

    const res = await fetch(API_URL, {
      method: 'POST',
      signal,
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': API_VERSION,
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await describeError(res));

    const { text, usage, stopReason } = await consumeStream(res, signal, onDelta);
    if (stopReason === 'refusal') throw new Error('모델이 이 도면 판독을 거절했습니다 (stop_reason: refusal).');
    if (stopReason === 'max_tokens') {
      throw new Error('최대 출력 토큰에 도달해 응답이 잘렸습니다. 설정에서 최대 출력 토큰을 늘리세요.');
    }
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(`응답을 JSON으로 해석하지 못했습니다.\n${text.slice(0, 400)}`);
    }
    return { data, usage };
  }

  async function describeError(res) {
    let detail = '';
    try {
      const j = await res.json();
      detail = j?.error?.message || JSON.stringify(j);
    } catch {
      detail = await res.text().catch(() => '');
    }
    const hint = {
      401: 'API 키를 확인하세요.',
      403: '이 키에 해당 모델 권한이 없을 수 있습니다.',
      404: '모델 ID를 확인하세요.',
      413: '요청이 너무 큽니다. 타일 수를 줄이세요.',
      429: '요청 한도에 걸렸습니다. 잠시 후 다시 시도하세요.',
      529: 'API가 일시적으로 과부하 상태입니다.',
    }[res.status];
    return `HTTP ${res.status} — ${detail}${hint ? `\n${hint}` : ''}`;
  }

  async function consumeStream(res, signal, onDelta) {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    const textBlocks = new Set();
    let buffer = ''; let text = ''; let usage = null; let stopReason = null;

    for (;;) {
      if (signal?.aborted) { await reader.cancel(); throw new DOMException('aborted', 'AbortError'); }
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep;
      while ((sep = buffer.indexOf('\n\n')) >= 0) {
        const chunk = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const line = chunk.split('\n').find((l) => l.startsWith('data:'));
        if (!line) continue;
        let ev;
        try { ev = JSON.parse(line.slice(5).trim()); } catch { continue; }
        switch (ev.type) {
          case 'content_block_start':
            if (ev.content_block?.type === 'text') textBlocks.add(ev.index);
            break;
          case 'content_block_delta':
            if (ev.delta?.type === 'text_delta' && textBlocks.has(ev.index)) {
              text += ev.delta.text;
              if (onDelta) onDelta(text.length);
            }
            break;
          case 'message_start':
            if (ev.message?.usage) usage = { ...ev.message.usage };
            break;
          case 'message_delta':
            if (ev.delta?.stop_reason) stopReason = ev.delta.stop_reason;
            if (ev.usage) usage = { ...(usage || {}), ...ev.usage };
            break;
          case 'error':
            throw new Error(ev.error?.message || '스트리밍 중 오류가 발생했습니다.');
        }
      }
    }
    return { text, usage, stopReason };
  }

  return { buildSchema, systemPrompt, extractDrawing, COL_HINT };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = ClaudeAPI;
