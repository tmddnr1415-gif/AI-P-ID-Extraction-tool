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

Cloudflare 계정(무료)과 [wrangler](https://developers.cloudflare.com/workers/wrangler/) 가 필요합니다.

```bash
npm install -g wrangler

cd pid-instrument-tool/server
./deploy.sh
```

`deploy.sh` 가 순서대로 합니다.

1. Cloudflare 로그인 (안 돼 있으면 브라우저를 엽니다)
2. 배포본 만들기 — 판독 규칙 번들, `public/`, Excel 템플릿
3. **사용량 제한용 KV 네임스페이스 생성 후 `wrangler.toml` 에 연결**
4. 비밀값 등록 — API 키와 비밀번호를 물어봅니다 (`SESSION_SECRET` 은 자동 생성)
5. 배포하고 접속 주소 출력

끝나면 이런 줄이 나옵니다.

```
접속 링크   https://pid-instrument-list.<계정>.workers.dev
비밀번호    방금 정한 APP_PASSWORD
```

**이 둘만 공유하면 됩니다.** 받은 사람은 브라우저로 접속 → 비밀번호 → PDF 드래그앤드롭 → Excel 다운로드.

여러 번 실행해도 됩니다. 이미 만들어진 KV와 등록된 비밀값은 건너뜁니다. 코드를 고친 뒤
다시 올릴 때도 `./deploy.sh` 하나면 됩니다.

`inputs/` 에 Excel 템플릿이 있어야 합니다. 템플릿은 서버 코드에 심겨 로그인한 사람에게만
내려갑니다. 없으면 접속한 사람이 직접 올려야 합니다.

### 직접 배포

`deploy.sh` 가 안 맞으면 손으로 해도 됩니다.

```bash
cd pid-instrument-tool
python3 scripts/build_web.py        # 판독 규칙 번들
python3 scripts/build_server.py     # server/public/ 과 템플릿

cd server
wrangler kv namespace create RATE   # 출력된 id 를 wrangler.toml 의
                                    # KV_BLOCK 주석을 풀어 채웁니다
wrangler secret put ANTHROPIC_API_KEY   # Anthropic API 키
wrangler secret put APP_PASSWORD        # 링크를 공유받은 사람이 넣을 비밀번호
wrangler secret put SESSION_SECRET      # openssl rand -hex 32
wrangler deploy
```

## 사용량 제한

비밀번호를 아는 사람은 누구나 이 배포의 API 사용량을 씁니다. 그래서 하루에 판독할 수 있는
도면 수를 KV로 셉니다. `deploy.sh` 가 자동으로 붙이므로 따로 할 일은 없습니다.

한도는 `wrangler.toml` 의 `DAILY_LIMIT`(기본 200장)으로 바꿉니다. 초기화 시각은
`TZ_OFFSET`(기본 9 = 자정 KST) 기준입니다. 남은 수는 접속한 사람 화면 위쪽에
`오늘 남은 판독 12/200장` 처럼 나오고, 한도를 넘겨 선택하면 시작 전에 알려줍니다.

`wrangler.toml` 의 `[[kv_namespaces]]` 가 주석인 채로 배포하면 **한도가 없습니다.**
`deploy.sh` 를 쓰지 않고 직접 배포한다면 이 블록이 살아 있는지 확인하세요.

세는 방식은 판독 한 건마다 키를 하나씩 쓰고 그날 것의 개수를 세는 것입니다. 카운터
하나를 읽어 +1 해 쓰면 도면을 연달아 판독할 때 증가분이 사라지는데(KV에는 원자적 증가가
없습니다) 키를 나눠 써서 이 문제를 없앴습니다. 다만 KV는 최종적 일관성이라 **여러 사람이
같은 순간에 요청하면 한도를 몇 건 넘길 수 있습니다.** 정확한 과금 통제가 아니라 폭주를
막는 안전장치로 보세요. 실제 비용은 Anthropic Console에서 확인하시고, 필요하면 그쪽
지출 한도도 같이 걸어두세요.

## 서버가 정하는 것

`wrangler.toml` 의 `[vars]` 에서 바꿉니다. 브라우저에서는 바꿀 수 없습니다.

| 값 | 기본 | 설명 |
|---|---|---|
| `MODEL` | `claude-opus-5` | 판독 모델 |
| `EFFORT` | `high` | 추론 깊이 |
| `MAX_TOKENS` | `32000` | 도면당 최대 출력 토큰 |
| `TILES` | `3x2` | 도면 확대 타일 분할 |
| `DPI` | `200` | 타일 렌더링 해상도 |
| `DAILY_LIMIT` | `200` | 하루 판독 도면 수 |
| `TZ_OFFSET` | `9` | 한도 초기화 시각 기준 (9 = 자정 KST) |

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
- 비밀번호가 유출되면 그 사람이 API 사용량을 쓸 수 있습니다. `DAILY_LIMIT`이 유일한
  방어선이고, 그마저도 동시 요청에는 몇 건 새어 나갈 수 있는 근사치입니다.
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
