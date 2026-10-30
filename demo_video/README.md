# 시연 영상 — 계장ENG그룹 Dashboard (Dashboard · PID · Logic · Panel)

- `계장ENG_Dashboard_시연.mp4` — 1920×1080 · 30fps · 3분 35초. 자막이 영상에 들어가 있고, 음성은 없습니다.
- `계장ENG_Dashboard_시연.srt` — 장면별 자막을 실제 타이밍으로 뽑은 파일입니다 (내레이션 녹음용 대본).

| 시간 | 장 | 무엇을 보여주나 | 방식 |
| --- | --- | --- | --- |
| 0:00 | 인트로 | — | 카드 |
| 0:06 | 01 Dashboard | 로그인 → 내 업무 팝업 → 현황판 → 수행 PJT 보드 → 분석 메뉴 | **실제 조작** |
| 0:44 | 02 PID | 메뉴에서 P&ID 분석 열기 | **실제 조작** |
| | | 결과 화면 · 판정 근거 · Rev 대조 | 저장된 실제 분석 화면 (`out/ppt_intro/shots`) |
| 1:28 | 03 Logic | 메뉴에서 LOGIC 분석 열기 | **실제 조작** |
| | | 식별률 · 게이트 근거 · 동작 시뮬레이션 | 저장된 실제 분석 화면 (`out/l51` · `out/l70`) |
| | | LOGIC 작성: 새 시트 → 기호 배치 · 확대 · 끌기 | **실제 조작** |
| | | 작성한 로직 시뮬레이션 | 저장된 화면 (`out/l61`) |
| 2:28 | 04 Panel | ROOM SIZE 계산: 새 프로젝트 → 예시 배치 → 판넬 3 EA 추가 → 검토 결과 → 유지보수 공간 → 실 치수 변경 → 서버 저장 → 출력 | **실제 조작** |
| 3:28 | 마무리 | — | 카드 |

## 다시 만들기

1. 대시보드(`ccr-248a5c4d-3dji7g` 의 `dashboard/`)를 8080 에, P&ID 도구
   (`claude/logic-symbol-visualization-sim-2oqbxh`)를 8000 에 띄웁니다.
   - 녹화용 사본에서만 두 줄을 고쳤습니다: `PID_ROUTES.space` 를 `port:8080, path:'/apps/space/'` 로,
     `/version` 확인을 8000 으로 (판넬 툴을 대시보드 서버의 `apps/space` 에서 열기 위해).
2. 시연 계정 `demo / demo1234!` (홍길동) 을 `/api/auth/register` 로 만들고,
   `python3 scripts/seed.py <대시보드 운영 폴더>` 로 예시 PJT 9행을 넣습니다 (모두 "예시" 데이터).
3. 글꼴: `npm i @fontsource/noto-sans-kr@5` 뒤 `korean/latin-{400,700,900}` woff2 를 `f/k400.woff2` · `f/l400.woff2` … 로 복사.
4. `node director.js out.mp4` — 실제 조작 구간은 실시간, 카드·저장 화면은 프레임 단위로 렌더 (약 6분).
   `node director.js out.mp4 panel` 처럼 장 하나만 찍을 수도 있습니다.

연출(커서 이동 · 자막 · 장 구성)은 `director.js`, 화면 위 덧씌움(카드 · 자막 · 커서 · 진행 막대)은 `overlay.js` 에 있습니다.
