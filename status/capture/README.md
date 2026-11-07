# 미리보기 캡처 — 현황판 · 시연의 실제 화면 다시 찍기

오케스트레이터가 각 세션의 **최신 코드를 실제로 띄워** 찍는다. 결과는 `status/previews/<SID>_<n>.jpg` (현황판)과 시연 빌드 폴더(`build_demo.py` 의 IMAGES 표)에 쓴다.
외부 서비스 없음 · Chromium + Playwright (이 세션 환경에 있음).

```
S=<작업 폴더>   # 예: 세션 scratchpad
```

## 1. DASHBOARD (S1) — 표준 라이브러리 서버

```bash
mkdir -p $S/s1src $S/s1root
git archive origin/ccr-248a5c4d-3dji7g dashboard | tar -x -C $S/s1src && cp -r $S/s1src/dashboard/. $S/s1root/
python3 status/capture/seed_s1.py $S/s1root          # 예시 PJT 7행 (화면 채우기용)
(cd $S/s1root && python3 server.py --root . --port 8777 --plaza-port 0 --allow-sleep &)
curl -s -X POST http://127.0.0.1:8777/api/auth/register -H 'Content-Type: application/json' -d '{"id":"demo","name":"시연자","password":"demo-pass-1234","email":"demo@example.com","birth":"1990-01-01"}'
TOK=$(curl -s -X POST http://127.0.0.1:8777/api/auth/login -H 'Content-Type: application/json' -d '{"id":"demo","password":"demo-pass-1234"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
(cd $S && node /path/to/status/capture/shot_s1.js $TOK home perform bid pid logic logicdraw space books)   # → $S/shots/s1_*.png
```

## 2. PID 서버 (S2 기준 + S6 Valve 덮어쓰기) — P&ID · LOGIC · ROOM SIZE · 도서 · Valve 화면

```bash
mkdir -p $S/s2src $S/s2data
git archive origin/claude/gracious-ride-26nqrf app config requirements.txt | tar -x -C $S/s2src
git archive origin/ccr-efbe7e75-n915ze app/valve app/static/valve | tar -x -C $S/s2src      # 회사 적용 순서대로
(cd $S/s2src && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt)
(cd $S/s2src && PID_DATA_DIR=$S/s2data PID_STARTUP_TASKS=0 .venv/bin/python -m uvicorn app.main:app --port 8000 &)
(cd $S && node /path/to/status/capture/shot_direct.js)                                      # valve · signal · pid 직접
(cd $S && node /path/to/status/capture/shot_more.js)                                        # S7 개념 화면 + LOGIC 작도 AMIRAL 장
# 실제 P&ID 판독을 돌리려면 (글자 있는 PDF): git show origin/claude/gracious-ride-26nqrf:out/round41/verify/08b_tagged_same_size.pdf > $S/samples/sample_pid2.pdf
(cd $S && node /path/to/status/capture/run_pid.js)
```

## 3. 3D 계측제어 (S7) — file:// 로 열림 (실물 3D 는 CDN 막히면 실패 화면 — 그것도 실제 결과)

```bash
mkdir -p $S/s7src && git archive origin/claude/practical-newton-n6bt58 app output | tar -x -C $S/s7src
(cd $S && node /path/to/status/capture/shot_s7.js)      # → s7_org · s7_mr · s7_anatomy
```

## 4. 세션이 남긴 캡처 · 시연 영상 캡처 (그대로 씀)

- S3: `origin/ccr-cc45909d-fjjmrb:out/l70/shot4_done.png` · `out/l64/ui/3_main_sim.png` · `out/l72/sp_from_drawing.png`
- S4: `origin/ccr-d82d97fa-bb3ty3:reports/2026-10-22_판넬공간확보/img/*.png` (48_1 첫화면 · 14_1 3D · 44_1 작업자 · 46_11 Phase2)
- 시연 영상: `origin/ccr-ee7fd745-5z06vs:launch_video/upload/*.jpg`

## 5. 현황판 · 시연에 넣기

```bash
# 현황판: previews/<SID>_<n>.jpg 로 저장 (1280px · JPEG 72) → python3 status/build_status.py
# 시연:   python3 company-pc-update/demo_build/build_demo.py $S   (IMAGES 표의 상대 경로 기준)
```

서버는 끝나면 내린다: `pkill -f "server.py --root . --port 8777"; pkill -f "uvicorn app.main:app --port 8000"`.
