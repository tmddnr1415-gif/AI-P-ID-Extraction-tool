# 공유 링크 서버

링크를 받은 사람이 **비밀번호만 넣으면** 어느 컴퓨터에서든 브라우저로 쓸 수 있게 배포합니다.
API 키는 서버 비밀값으로만 존재하고 브라우저로 내려가지 않습니다.

```
사용자 브라우저                     Cloudflare Worker              Anthropic
   PDF 드래그앤드롭
   도면 → 이미지·타일 (브라우저)
   판독 요청 ──────────────▶  비밀번호 세션 확인
                              모델·토큰·이미지 수 검사
                              하루 한도 확인
                              API 키 붙여 중계 ──────────▶ 판독
   결과 ◀──────────────────  스트림 그대로 전달 ◀──────────
   Excel 만들기 (브라우저)
```

무거운 일(PDF 렌더링, Excel 생성)은 브라우저가 하므로 서버는 얇습니다. Cloudflare 무료 플랜으로 충분합니다.

## 배포

**1. 준비** — Cloudflare 계정(무료)과 [wrangler](https://developers.cloudflare.com/workers/wrangler/)

```bash
npm install -g wrangler
wrangler login
```

**2. 배포본 만들기** — `inputs/` 에 Excel 템플릿이 있어야 합니다. 서버 코드에 심겨
로그인한 사람에게만 내려갑니다.

```bash
cd pid-instrument-tool
python3 scripts/build_web.py        # 판독 규칙 번들
python3 scripts/build_server.py     # server/public/ 과 템플릿
```

**3. 비밀값 등록**

```bash
cd server
wrangler secret put ANTHROPIC_API_KEY   # Anthropic API 키
wrangler secret put APP_PASSWORD        # 링크를 공유받은 사람이 넣을 비밀번호
wrangler secret put SESSION_SECRET      # 아무 긴 임의 문자열 (예: openssl rand -hex 32)
```

**4. 올리기**

```bash
wrangler deploy
```

`https://pid-instrument-list.<계정>.workers.dev` 주소가 나옵니다. 이 링크와 비밀번호를 공유하면 됩니다.

## 사용량 제한 (권장)

비밀번호를 아는 사람은 누구나 이 배포의 API 사용량을 쓰게 됩니다. 하루 판독 도면 수를
제한하려면 KV를 붙이세요.

```bash
wrangler kv namespace create RATE
```

출력된 `id` 를 `wrangler.toml` 의 `[[kv_namespaces]]` 주석을 풀어 채우고 다시 배포합니다.
한도는 `DAILY_LIMIT`(기본 200장)으로 조정합니다. **KV를 붙이지 않으면 한도가 없습니다.**

## 서버가 정하는 것

`wrangler.toml` 의 `[vars]` 에서 바꿉니다. 브라우저에서는 바꿀 수 없습니다.

| 값 | 기본 | 설명 |
|---|---|---|
| `MODEL` | `claude-opus-5` | 판독 모델 |
| `EFFORT` | `high` | 추론 깊이 |
| `MAX_TOKENS` | `32000` | 도면당 최대 출력 토큰 |
| `TILES` | `3x2` | 도면 확대 타일 분할 |
| `DPI` | `200` | 타일 렌더링 해상도 |
| `DAILY_LIMIT` | `200` | 하루 판독 도면 수 (KV 연결 시) |

## 보안

**하는 것**

- API 키는 Worker 비밀값으로만 존재하고 응답에 실리지 않습니다.
- 비밀번호는 HMAC으로 비교하고, 실패 시 응답을 늦춰 무차별 대입을 늦춥니다.
- 세션은 서명된 쿠키(`HttpOnly`, `Secure`, `SameSite=Strict`, 12시간)입니다.
- 중계 요청은 모델 허용목록·토큰 상한·이미지 수·금지 파라미터를 검사합니다.
  판독 외의 용도로 이 프록시를 쓸 수 없습니다.
- Excel 템플릿은 정적 파일이 아니라 워커 코드 안에 있어 로그인해야만 받을 수 있습니다.

**안 하는 것 — 알고 쓰셔야 합니다**

- 비밀번호는 **하나**이고 사용자 구분이 없습니다. 누가 얼마나 썼는지 추적되지 않습니다.
- 비밀번호가 유출되면 그 사람이 API 사용량을 쓸 수 있습니다. `DAILY_LIMIT`이 유일한 방어선입니다.
- 업로드된 P&ID는 브라우저 안에서만 처리되어 서버에 저장되지 않지만, **도면 이미지는
  판독을 위해 Anthropic API로 전송**됩니다.
- 사내 기밀 도면을 다루신다면 배포 전에 보안 담당자와 상의하세요.

비밀번호를 바꾸려면 `wrangler secret put APP_PASSWORD` 후 재배포합니다.
기존 세션까지 끊으려면 `SESSION_SECRET` 도 함께 바꾸세요.

## 로컬에서 확인

```bash
cd server
cat > .dev.vars <<'EOF'
ANTHROPIC_API_KEY=sk-ant-...
APP_PASSWORD=테스트비밀번호
SESSION_SECRET=아무-긴-문자열
EOF
wrangler dev
```

`http://localhost:8787` 로 접속합니다. `.dev.vars` 는 커밋되지 않습니다.
