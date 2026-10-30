# 시연 영상 (3분) — Dashboard · PID · Logic · Panel

- `PID_Extractor_시연_3분.mp4` — 1920×1080 · 30fps · 3:00. 자막이 영상에 들어가 있고, 음성은 없습니다.
- `PID_Extractor_시연_3분.srt` — 장면별 자막을 내레이션 대본처럼 쓸 수 있게 뽑은 파일입니다 (녹음할 때 사용).

| 시간 | 장 | 소재 |
| --- | --- | --- |
| 0:00 | 인트로 | — |
| 0:09 | 01 Dashboard | 홈 화면 (`out/ppt_intro/shots/01_home.png`) |
| 0:40 | 02 PID | 결과 · 근거 · Rev 대조 (`out/ppt_intro/shots/02·03·09`) |
| 1:28 | 03 Logic | LOGIC 검토 · 동작 시뮬레이션 · 작도 (`out/l51` · `l70` · `l61`) + **신호 처리 화면 실제 녹화** |
| 2:20 | 04 Panel | **HMI 그래픽 실제 녹화** (예시 Compressor Train) + `out/hmi1` |
| 2:52 | 마무리 | — |

## 다시 만들기

브랜치 `claude/logic-symbol-visualization-sim-2oqbxh` 의 앱을 `127.0.0.1:8000` 에 띄운 뒤:

```bash
npm i @fontsource/noto-sans-kr@5          # player.html 이 ../fonts/node_modules 에서 글꼴을 읽음
node scripts/record.js $PWD/player.html out.mp4   # 프레임 단위 렌더 → ffmpeg (약 5분)
node scripts/srt.js    $PWD/player.html out.srt
```

장면 · 자막 · 확대 위치는 `player.html` 의 `S` 배열 하나에 모여 있습니다.
