#!/usr/bin/env bash
# 공유 링크 서버를 한 번에 배포한다.
#
#   ./deploy.sh
#
# 하는 일
#   1. 판독 규칙 번들 + 배포본(public/, 템플릿) 생성
#   2. 사용량 제한용 KV 네임스페이스 생성 후 wrangler.toml 에 연결
#   3. 없는 비밀값만 물어봐서 등록
#   4. 배포하고 접속 주소 출력
#
# 여러 번 실행해도 됩니다. 이미 있는 것은 건너뜁니다.
set -euo pipefail

cd "$(dirname "$0")"
TOML=wrangler.toml

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()  { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ── 0. 준비물 확인 ───────────────────────────────────────────────
command -v wrangler >/dev/null || die "wrangler 가 없습니다.  npm install -g wrangler"
command -v python3  >/dev/null || die "python3 가 없습니다."

say "0. 계정 확인"
if ! wrangler whoami >/dev/null 2>&1; then
  warn "Cloudflare 로그인이 필요합니다. 브라우저가 열립니다."
  wrangler login
fi
ok "$(wrangler whoami 2>/dev/null | grep -oE '[^ ]+@[^ ]+' | head -1 || echo '로그인됨')"

# ── 1. 배포본 만들기 ─────────────────────────────────────────────
say "1. 배포본 만들기"
python3 ../scripts/build_web.py
python3 ../scripts/build_server.py
[ -s src/template.b64.js ] || die "src/template.b64.js 가 비었습니다."
grep -q 'TEMPLATE_B64 = ""' src/template.b64.js &&
  warn "Excel 템플릿을 못 찾았습니다. 접속한 사람이 직접 올려야 합니다."

# ── 2. 사용량 제한 (KV) ──────────────────────────────────────────
say "2. 사용량 제한 (KV)"
if grep -q '^\[\[kv_namespaces\]\]' "$TOML"; then
  ok "이미 연결돼 있습니다 — id $(grep -A2 '^\[\[kv_namespaces\]\]' "$TOML" | grep '^id' | cut -d'"' -f2)"
else
  # 이미 같은 이름의 네임스페이스가 있으면 그것을 쓰고, 없으면 만든다.
  TITLE="pid-instrument-list-RATE"
  KV_ID=$(wrangler kv namespace list 2>/dev/null | python3 -c "
import json,sys
try: ns = json.load(sys.stdin)
except Exception: sys.exit()
print(next((n['id'] for n in ns if n.get('title','').endswith('RATE')), ''))
" || true)

  if [ -z "${KV_ID:-}" ]; then
    echo "  네임스페이스를 만드는 중…"
    CREATE_OUT=$(wrangler kv namespace create RATE 2>&1) || { echo "$CREATE_OUT"; die "KV 생성 실패"; }
    KV_ID=$(printf '%s' "$CREATE_OUT" | grep -oE '[0-9a-f]{32}' | head -1)
    [ -n "$KV_ID" ] || { echo "$CREATE_OUT"; die "만들어진 KV id를 읽지 못했습니다. README 의 '직접 배포'를 보세요."; }
    ok "네임스페이스 생성 ($TITLE)"
  else
    ok "기존 네임스페이스를 씁니다"
  fi

  # wrangler.toml 의 KV_BLOCK 주석을 풀고 id를 채운다.
  python3 - "$TOML" "$KV_ID" <<'PY'
import re, sys
path, kv_id = sys.argv[1], sys.argv[2]
src = open(path, encoding='utf-8').read()
m = re.search(r'# KV_BLOCK_START\n(.*?)# KV_BLOCK_END\n', src, re.S)
if not m:
    sys.exit('wrangler.toml 에서 KV_BLOCK 표시를 찾지 못했습니다.')
body = '\n'.join(re.sub(r'^# ?', '', ln) for ln in m.group(1).splitlines())
body = body.replace('PASTE_KV_ID_HERE', kv_id)
open(path, 'w', encoding='utf-8').write(src[:m.start()] + body + '\n' + src[m.end():])
PY
  ok "wrangler.toml 에 연결 — id $KV_ID"
fi
LIMIT=$(grep -E '^DAILY_LIMIT' "$TOML" | cut -d'"' -f2)
ok "하루 한도 ${LIMIT:-200}장 (바꾸려면 wrangler.toml 의 DAILY_LIMIT)"

# ── 3. 비밀값 ────────────────────────────────────────────────────
say "3. 비밀값"
EXISTING=$(wrangler secret list 2>/dev/null || echo '[]')
need() { ! printf '%s' "$EXISTING" | grep -q "\"$1\""; }

if need ANTHROPIC_API_KEY; then
  echo "  Anthropic API 키를 붙여넣으세요 (화면에 안 보입니다):"
  wrangler secret put ANTHROPIC_API_KEY
else ok "ANTHROPIC_API_KEY 등록돼 있음"; fi

if need APP_PASSWORD; then
  echo "  링크를 공유받은 사람이 넣을 비밀번호를 정하세요:"
  wrangler secret put APP_PASSWORD
else ok "APP_PASSWORD 등록돼 있음"; fi

if need SESSION_SECRET; then
  # 사람이 정할 이유가 없는 값이라 임의로 만들어 넣는다.
  SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets;print(secrets.token_hex(32))")
  printf '%s' "$SECRET" | wrangler secret put SESSION_SECRET
  ok "SESSION_SECRET 자동 생성"
else ok "SESSION_SECRET 등록돼 있음"; fi

# ── 4. 배포 ──────────────────────────────────────────────────────
say "4. 배포"
OUT=$(wrangler deploy 2>&1) || { echo "$OUT"; die "배포 실패"; }
echo "$OUT" | tail -20
URL=$(printf '%s' "$OUT" | grep -oE 'https://[a-z0-9.-]+\.workers\.dev' | head -1)

say "끝났습니다"
if [ -n "${URL:-}" ]; then
  printf '  접속 링크   \033[1;36m%s\033[0m\n' "$URL"
else
  printf '  접속 링크   위 출력의 https://... workers.dev 주소\n'
fi
printf '  비밀번호    방금 정한 APP_PASSWORD\n\n'
printf '  이 둘만 공유하면 상대는 브라우저로 접속 → 비밀번호 → PDF 드래그앤드롭 → Excel 다운로드.\n'
printf '  비밀번호를 바꾸려면:  wrangler secret put APP_PASSWORD && wrangler deploy\n'
