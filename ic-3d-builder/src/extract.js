/* GA / Dimensional Drawing → Anatomy 파라미터. Claude Messages API (브라우저 직접 호출).
 *
 * 원칙: 도면에 적힌 치수만 돌려받는다. 빈 칸을 표준값으로 채우는 일은 앱(RefData)이
 * 하고 출처를 'standard' 로 남긴다. 모델이 채우면 도면값과 추정값이 섞여 구분이 안 된다.
 */
'use strict';

const Extract = (() => {
  const API_URL = 'https://api.anthropic.com/v1/messages';

  const SCHEMA = {
    type: 'object',
    properties: {
      item_type: { type: 'string', enum: ['valve', 'cabinet', 'hookup'], description: '도면 품목 분류' },
      title_block: {
        type: 'object',
        properties: {
          tag: { type: 'string' }, dwg_no: { type: 'string' }, rev: { type: 'string' },
          vendor: { type: 'string' }, model_no: { type: 'string' }, description: { type: 'string' },
        },
        required: ['tag', 'dwg_no', 'rev', 'vendor', 'model_no', 'description'],
        additionalProperties: false,
      },
      size_row: { type: 'string', description: '치수표가 사이즈별일 때 선택한 행과 이유. 해당 없으면 "-"' },
      params: {
        type: 'array',
        description: '도면에서 직접 읽은 값만. 표준·추정으로 채우지 않는다',
        items: {
          type: 'object',
          properties: {
            key: { type: 'string', description: '파라미터 사전의 key' },
            value: { type: 'string', description: '숫자는 mm 로 환산한 숫자만. enum 은 사전의 선택지 문자열' },
            as_drawn: { type: 'string', description: '도면에 적힌 원문 (예: "A = 11.50 in", "Ø 356")' },
            evidence: { type: 'string', description: '어느 뷰/표/주기에서 읽었는지' },
            confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          },
          required: ['key', 'value', 'as_drawn', 'evidence', 'confidence'],
          additionalProperties: false,
        },
      },
      unmapped_dimensions: {
        type: 'array', description: '도면에 있지만 사전 key 로 옮기지 못한 치수 (예: 볼트 길이, 노즐 방위)',
        items: { type: 'string' },
      },
      review_findings: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            severity: { type: 'string', enum: ['high', 'medium', 'low'] },
            finding: { type: 'string' },
          },
          required: ['severity', 'finding'], additionalProperties: false,
        },
      },
      summary: { type: 'string', description: '2~3문장 요약' },
    },
    required: ['item_type', 'title_block', 'size_row', 'params', 'unmapped_dimensions', 'review_findings', 'summary'],
    additionalProperties: false,
  };

  function systemPrompt() {
    const L = [
      '당신은 계측제어(I&C) 품목의 General Arrangement(GA) / Dimensional Drawing 을 읽어',
      '파라메트릭 3D 모델의 치수 파라미터로 옮기는 계장 엔지니어입니다.',
      '',
      '결과는 플랜트 배치·간섭 검토에 쓰입니다. 도면에 없는 치수를 만들어내면 안 됩니다.',
      '도면에 없는 값은 params 에 넣지 마세요. 앱이 표준표로 채우고 출처를 따로 표시합니다.',
      '',
      '# 규칙',
      '1. 길이는 모두 mm 숫자로 환산합니다 (inch × 25.4, 소수 1자리). as_drawn 에는 원문을 그대로 둡니다.',
      '2. 사이즈별 치수표(A, B, C, H … 열)가 있으면 사용자 힌트의 사이즈·등급 행을 고르고 size_row 에 적습니다.',
      '   힌트가 없고 행이 여러 개면 Tag/타이틀블록으로 판단하고, 모르겠으면 review_findings 에 high 로 남깁니다.',
      '3. 도면의 치수 기호(A/B/H 등)를 사전 key 로 옮길 때 뷰에서 치수선이 어디를 재는지 확인합니다.',
      '   예: 밸브 "A" 가 플랜지 면-면이면 ftf, CL 에서 최상단이면 overall_h.',
      '4. "MAX", "APPROX", "REF" 가 붙은 치수는 confidence 를 medium 이하로 둡니다.',
      '5. 조작기 부품(액추에이터, 핸드휠, 포지셔너)도 치수가 있으면 넣습니다.',
      '6. 캐비닛: 플린스 높이를 본체 높이에서 분리합니다. 도면 전체 높이 = h + plinth_h.',
      '7. 훅업: Hook-up drawing 은 대개 치수가 적습니다. 계기 종류, 매니폴드, 유체, 탭 방향 같은 구성값을 우선 읽습니다.',
      '',
      '# 품목별 파라미터 사전',
    ];
    for (const [id, T] of Object.entries(Anatomy.TYPES)) {
      L.push('', `## item_type = ${id} (${T.label})`, Anatomy.describeSchema(id));
    }
    return L.join('\n');
  }

  async function fileBlock(file) {
    const b64 = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(String(r.result).split(',')[1]);
      r.onerror = () => rej(r.error);
      r.readAsDataURL(file);
    });
    if (file.type === 'application/pdf') {
      return { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: b64 } };
    }
    const mt = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type) ? file.type : 'image/png';
    return { type: 'image', source: { type: 'base64', media_type: mt, data: b64 } };
  }

  async function run({ apiKey, model, effort, files, typeHint, hint, signal, onProgress }) {
    if (!apiKey) throw new Error('⚙ 설정에서 Anthropic API 키를 넣으세요.');
    if (!files.length) throw new Error('도면 파일을 먼저 넣으세요.');
    const content = [];
    for (const f of files) {
      content.push({ type: 'text', text: `## 도면 파일: ${f.name}` });
      content.push(await fileBlock(f));
    }
    content.push({
      type: 'text',
      text: [
        `선택한 품목 분류: ${typeHint || '자동 판별'}`,
        `사용자 힌트: ${hint || '(없음)'}`,
        '위 도면에서 파라미터 사전에 해당하는 치수와 구성값을 읽어 주세요.',
      ].join('\n'),
    });

    const body = {
      model,
      max_tokens: 32000,
      stream: true,
      thinking: { type: 'adaptive' },
      system: [{ type: 'text', text: systemPrompt(), cache_control: { type: 'ephemeral' } }],
      output_config: { effort, format: { type: 'json_schema', schema: SCHEMA } },
      fallbacks: 'default',
      messages: [{ role: 'user', content }],
    };
    const res = await fetch(API_URL, {
      method: 'POST', signal, credentials: 'omit',
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-beta': 'server-side-fallback-2026-07-01',
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let msg = '';
      try { const j = await res.json(); msg = j?.error?.message || JSON.stringify(j); } catch { msg = await res.text().catch(() => ''); }
      const hintMsg = { 401: 'API 키를 확인하세요.', 404: '모델 ID를 확인하세요.', 413: '파일이 너무 큽니다.', 429: '요청 한도 — 잠시 후 다시.', 529: 'API 과부하 — 잠시 후 다시.' }[res.status];
      throw new Error(`HTTP ${res.status} — ${msg}${hintMsg ? '\n' + hintMsg : ''}`);
    }
    const { text, usage, stopReason } = await consume(res, signal, onProgress);
    if (stopReason === 'refusal') throw new Error('모델이 이 요청을 거절했습니다 (refusal).');
    if (stopReason === 'max_tokens') throw new Error('응답이 잘렸습니다 (max_tokens).');
    try { return { data: JSON.parse(text), usage }; } catch { throw new Error(`JSON 해석 실패\n${text.slice(0, 300)}`); }
  }

  async function consume(res, signal, onProgress) {
    const reader = res.body.getReader(); const dec = new TextDecoder();
    const textBlocks = new Set(); let buf = ''; let text = ''; let usage = null; let stopReason = null;
    for (;;) {
      if (signal?.aborted) { await reader.cancel(); throw new DOMException('aborted', 'AbortError'); }
      const { done, value } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        const line = chunk.split('\n').find((l) => l.startsWith('data:')); if (!line) continue;
        let ev; try { ev = JSON.parse(line.slice(5).trim()); } catch { continue; }
        if (ev.type === 'message_start') {
          // fallback 으로 다른 모델이 응답하면 새 message_start 가 온다 → 텍스트를 새로 모은다
          text = ''; textBlocks.clear(); usage = { ...(ev.message?.usage || {}) };
        } else if (ev.type === 'content_block_start' && ev.content_block?.type === 'text') textBlocks.add(ev.index);
        else if (ev.type === 'content_block_delta' && ev.delta?.type === 'text_delta' && textBlocks.has(ev.index)) {
          text += ev.delta.text; onProgress?.(text.length);
        } else if (ev.type === 'message_delta') {
          if (ev.delta?.stop_reason) stopReason = ev.delta.stop_reason;
          if (ev.usage) usage = { ...(usage || {}), ...ev.usage };
        } else if (ev.type === 'error') throw new Error(ev.error?.message || '스트리밍 오류');
      }
    }
    return { text, usage, stopReason };
  }

  /** 판독 결과 → resolve() 입력 형식 */
  function toInputs(data, typeId) {
    const keys = new Set(Anatomy.TYPES[typeId].params.map((p) => p.key));
    const inputs = {}; const dropped = [];
    for (const p of data.params || []) {
      if (!keys.has(p.key)) { dropped.push(`${p.key}=${p.value}`); continue; }
      inputs[p.key] = { value: p.value, src: 'drawing', evidence: `${p.as_drawn} · ${p.evidence}`, confidence: p.confidence };
    }
    if (data.title_block?.tag && keys.has('tag') && !inputs.tag) {
      inputs.tag = { value: data.title_block.tag, src: 'drawing', evidence: '타이틀블록' };
    }
    return { inputs, dropped };
  }

  return { run, toInputs, systemPrompt, SCHEMA };
})();
