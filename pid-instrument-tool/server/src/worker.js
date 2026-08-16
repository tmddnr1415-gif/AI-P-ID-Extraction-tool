/* P&ID Instrument List — 공유 링크 서버 (Cloudflare Worker)
 *
 * 링크를 받은 사람이 비밀번호만 넣으면 쓸 수 있게 한다.
 * API 키는 서버 비밀값으로만 존재하며 브라우저로 내려가지 않는다.
 *
 *   POST /api/login     비밀번호 확인 → 서명된 세션 쿠키
 *   POST /api/logout    세션 파기
 *   GET  /api/config    로그인 상태와 서버가 정한 판독 설정
 *   GET  /api/template  Excel 템플릿 (로그인 필요)
 *   POST /api/extract   Anthropic API로 중계 (로그인 필요)
 *   그 외               정적 파일
 *
 * 비밀번호를 아는 사람은 누구나 이 배포의 API 사용량을 쓰게 된다. 그래서
 * 중계 요청은 그대로 흘려보내지 않고 모델·토큰·이미지 수를 검사하고,
 * KV가 연결돼 있으면 하루 판독 횟수를 제한한다.
 */

const ALLOWED_MODELS = new Set(['claude-opus-5', 'claude-sonnet-5', 'claude-opus-4-8']);
const MAX_TOKENS_CAP = 64000;
const MAX_IMAGES = 16;
const SESSION_HOURS = 12;
const DEFAULT_DAILY_LIMIT = 200;      // 하루 판독(도면) 횟수 상한

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    try {
      if (url.pathname === '/api/login') return login(request, env);
      if (url.pathname === '/api/logout') return logout();
      if (url.pathname === '/api/config') return config(request, env);
      if (url.pathname === '/api/template') return template(request, env);
      if (url.pathname === '/api/extract') return extract(request, env, ctx);
      return env.ASSETS.fetch(request);
    } catch (err) {
      return json({ error: err.message || '서버 오류' }, 500);
    }
  },
};

/* ── 응답 헬퍼 ─────────────────────────────────────────── */
const json = (obj, status = 200, headers = {}) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...headers },
  });

/* ── 세션 ──────────────────────────────────────────────── */
const encoder = new TextEncoder();

async function hmac(secret, data) {
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(data));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

/** 길이·내용 노출을 줄이기 위해 HMAC으로 비교한다. */
async function safeEqual(secret, a, b) {
  const [ha, hb] = await Promise.all([hmac(secret, a), hmac(secret, b)]);
  if (ha.length !== hb.length) return false;
  let diff = 0;
  for (let i = 0; i < ha.length; i++) diff |= ha.charCodeAt(i) ^ hb.charCodeAt(i);
  return diff === 0;
}

function sessionSecret(env) {
  const s = env.SESSION_SECRET || env.APP_PASSWORD;
  if (!s) throw new Error('SESSION_SECRET(또는 APP_PASSWORD)이 설정되지 않았습니다.');
  return s;
}

async function issueSession(env) {
  const exp = Date.now() + SESSION_HOURS * 3600 * 1000;
  return `${exp}.${await hmac(sessionSecret(env), String(exp))}`;
}

async function validSession(request, env) {
  const cookie = request.headers.get('cookie') || '';
  const token = (cookie.match(/(?:^|;\s*)pid_session=([^;]+)/) || [])[1];
  if (!token) return false;
  const [exp, sig] = decodeURIComponent(token).split('.');
  if (!exp || !sig || Date.now() > +exp) return false;
  return sig === await hmac(sessionSecret(env), exp);
}

async function login(request, env) {
  if (request.method !== 'POST') return json({ error: 'POST만 허용됩니다.' }, 405);
  if (!env.APP_PASSWORD) return json({ error: '서버에 APP_PASSWORD가 설정되지 않았습니다.' }, 500);

  const { password } = await request.json().catch(() => ({}));
  if (typeof password !== 'string' || !password) {
    return json({ error: '비밀번호를 입력하세요.' }, 400);
  }
  if (!await safeEqual(sessionSecret(env), password, env.APP_PASSWORD)) {
    // 무차별 대입을 조금이라도 늦춘다.
    await new Promise((r) => setTimeout(r, 700));
    return json({ error: '비밀번호가 맞지 않습니다.' }, 401);
  }

  const token = await issueSession(env);
  return json({ ok: true }, 200, {
    'set-cookie': `pid_session=${encodeURIComponent(token)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${SESSION_HOURS * 3600}`,
  });
}

const logout = () => json({ ok: true }, 200, {
  'set-cookie': 'pid_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0',
});

async function config(request, env) {
  const authed = await validSession(request, env);
  const body = {
    server: true,
    authed,
    model: env.MODEL || 'claude-opus-5',
    effort: env.EFFORT || 'high',
    maxTokens: Math.min(+(env.MAX_TOKENS || 32000), MAX_TOKENS_CAP),
    tiles: env.TILES || '3x2',
    dpi: +(env.DPI || 200),
    hasTemplate: Boolean(TEMPLATE_B64),
  };
  // 남은 판독 수는 로그인한 사람에게만 알린다.
  if (authed) body.quota = await quota(env);
  return json(body);
}

/* ── 템플릿 ────────────────────────────────────────────── */
import { TEMPLATE_B64, TEMPLATE_NAME } from './template.b64.js';

function b64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function template(request, env) {
  if (!await validSession(request, env)) return json({ error: '로그인이 필요합니다.' }, 401);
  if (!TEMPLATE_B64) return json({ error: '서버에 템플릿이 없습니다.' }, 404);
  return new Response(b64ToBytes(TEMPLATE_B64), {
    headers: {
      'content-type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'content-disposition': `attachment; filename="${TEMPLATE_NAME}"`,
      'cache-control': 'no-store',
    },
  });
}

/* ── 사용량 제한 (KV) ──────────────────────────────────────
 * 판독 한 건마다 키를 하나씩 쓰고, 오늘 것의 개수를 세어 한도와 비교한다.
 *
 * 카운터 하나를 읽어서 +1 해 쓰는 방식이 간단하지만, 도면을 연달아 판독하면
 * 두 요청이 같은 값을 읽고 같은 값을 써서 증가분이 사라진다(lost update).
 * KV에는 원자적 증가가 없으므로 키를 나눠 써서 이 문제를 없앤다.
 *
 * 다만 KV는 최종적 일관성이라 방금 쓴 키가 곧바로 목록에 안 보일 수 있다.
 * 즉 짧은 순간 한도를 몇 건 넘길 수는 있어도, 누적치가 영구히 적게 세어지는
 * 일은 없다. 정확한 과금 통제가 아니라 폭주 방지용 안전장치다.
 */
const dailyLimit = (env) => Math.max(1, +(env.DAILY_LIMIT || DEFAULT_DAILY_LIMIT) || DEFAULT_DAILY_LIMIT);

/** 한도가 초기화되는 시각의 기준 시간대. 기본 +9(한국) — 자정 KST에 초기화된다. */
const tzOffset = (env) => {
  const n = +(env.TZ_OFFSET ?? 9);
  return Number.isFinite(n) ? n : 9;
};
const dayStamp = (env) => new Date(Date.now() + tzOffset(env) * 3600e3).toISOString().slice(0, 10);
const ratePrefix = (env) => `hit:${dayStamp(env)}:`;

/** 자정(기준 시간대)까지 남은 초. 429 응답의 Retry-After 로 쓴다. */
function secondsUntilReset(env) {
  const now = Date.now() + tzOffset(env) * 3600e3;
  return Math.max(60, Math.ceil((86400e3 - (now % 86400e3)) / 1000));
}

/** 오늘 쓴 건수. limit 을 넘기면 더 세지 않고 멈춘다. */
async function countToday(env, limit) {
  let count = 0;
  let cursor;
  for (let page = 0; page < 5; page++) {
    const res = await env.RATE.list({ prefix: ratePrefix(env), limit: 1000, cursor });
    count += res.keys.length;
    if (res.list_complete || !res.cursor || count >= limit) break;
    cursor = res.cursor;
  }
  return count;
}

/** 로그인 화면 이후 남은 판독 수를 보여주기 위한 현재 상태. */
async function quota(env) {
  if (!env.RATE) return { enabled: false, limit: dailyLimit(env) };
  const limit = dailyLimit(env);
  const used = await countToday(env, limit);
  return { enabled: true, limit, used, remaining: Math.max(0, limit - used), resetsIn: secondsUntilReset(env) };
}

async function checkRate(env, ctx) {
  if (!env.RATE) return null;                      // KV 미연결이면 제한 없음
  const limit = dailyLimit(env);
  const used = await countToday(env, limit);
  if (used >= limit) {
    return json(
      { error: `오늘 판독 한도(${limit}장)를 모두 썼습니다. 자정 이후 다시 시도하세요.`, used, limit },
      429, { 'retry-after': String(secondsUntilReset(env)) });
  }
  ctx.waitUntil(env.RATE.put(ratePrefix(env) + crypto.randomUUID(), '1', { expirationTtl: 172800 }));
  return null;
}

/* ── 판독 중계 ─────────────────────────────────────────── */
function validate(body, env) {
  if (!body || typeof body !== 'object') return '요청 본문이 없습니다.';
  if (!ALLOWED_MODELS.has(body.model)) return `허용되지 않은 모델입니다: ${body.model}`;
  if (body.stream !== true) return '스트리밍 요청만 허용됩니다.';
  if (!(body.max_tokens > 0) || body.max_tokens > MAX_TOKENS_CAP) {
    return `max_tokens는 1~${MAX_TOKENS_CAP} 사이여야 합니다.`;
  }
  if (!body.output_config?.format) return '이 서버는 구조화 출력 요청만 중계합니다.';
  if (body.tools || body.mcp_servers || body.container) return '허용되지 않은 파라미터가 있습니다.';
  if (!Array.isArray(body.messages) || body.messages.length !== 1) return 'messages는 1개여야 합니다.';
  const content = body.messages[0]?.content;
  if (!Array.isArray(content)) return 'messages[0].content 형식이 올바르지 않습니다.';
  const images = content.filter((c) => c?.type === 'image').length;
  if (images > MAX_IMAGES) return `이미지는 최대 ${MAX_IMAGES}장까지 보낼 수 있습니다 (요청 ${images}장).`;
  return null;
}

async function extract(request, env, ctx) {
  if (request.method !== 'POST') return json({ error: 'POST만 허용됩니다.' }, 405);
  if (!await validSession(request, env)) return json({ error: '로그인이 필요합니다.' }, 401);
  if (!env.ANTHROPIC_API_KEY) return json({ error: '서버에 ANTHROPIC_API_KEY가 없습니다.' }, 500);

  const body = await request.json().catch(() => null);
  const bad = validate(body, env);
  if (bad) return json({ error: bad }, 400);

  const limited = await checkRate(env, ctx);
  if (limited) return limited;

  // 서버가 모델과 상한을 최종 결정한다.
  body.model = env.MODEL || body.model;
  body.max_tokens = Math.min(body.max_tokens, MAX_TOKENS_CAP);

  const upstream = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify(body),
  });

  if (!upstream.ok) {
    const text = await upstream.text().catch(() => '');
    return json({ error: `Anthropic API 오류 (HTTP ${upstream.status})`, detail: text.slice(0, 800) },
                upstream.status === 401 ? 502 : upstream.status);
  }

  return new Response(upstream.body, {
    headers: {
      'content-type': 'text/event-stream; charset=utf-8',
      'cache-control': 'no-store',
      'x-accel-buffering': 'no',
    },
  });
}
