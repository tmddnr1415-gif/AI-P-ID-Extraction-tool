# I&C 3D Builder — GA / Dimensional Drawing → 3D

계측제어 품목의 GA·치수도를 넣으면 부품 단위(anatomy)로 분해된 파라메트릭 3D 모델을 만듭니다.
배치·간섭·유지보수 공간 검토용입니다. **제작·구매 치수로 쓰지 않습니다.**

| 품목 | 프리셋 |
|---|---|
| System Cabinet | 베이 수, 도어 1/2, 후면 도어, 도어 열림각, 루버·팬·아이볼트, 마운팅 플레이트, I/O 모듈, 전면 유지보수 공간 |
| Instrument Hook-up | PT(스탠드), DP 유량(오리피스, close-coupled), DP 레벨(탱크 노즐) — 루트밸브·튜빙 기울기·매니폴드·드레인 |
| Control Valve | Globe + 다이어프램, Ball / Butterfly + 공압 로터리, 포지셔너·에어셋 |
| MOV | Gate / Globe / Ball / Butterfly + 전동 액추에이터 (모터·핸드휠·로컬 조작부) |
| Manual | Gate(rising stem 핸드휠) / Globe / Ball(레버) / Butterfly(기어) |
| PSV | 앵글형, 입·출구 별도 사이즈·등급, 리프팅 레버 |

## 쓰는 법

1. `index.html` 을 브라우저로 엽니다 (더블클릭). three.js 를 cdnjs 에서 받으므로 인터넷이 필요합니다.
2. 품목 프리셋을 고릅니다.
3. GA 도면(PDF/PNG/JPG)을 넣고, 필요하면 힌트(사이즈·등급·사용할 치수표 행)를 적은 뒤 **도면 읽어 3D 만들기**.
   ⚙ 설정에 Anthropic API 키가 필요합니다. 기본 모델은 `claude-opus-5-5` 입니다.
4. 왼쪽 폼에서 치수를 확인·수정합니다. 각 값 옆 배지가 출처입니다.
   **도면**(판독, 근거 표시) · **입력**(사람이 수정) · **표준**(내장 표준표) · **추정**(비례식).
   배지를 누르면 그 값을 지우고 표준/추정으로 되돌립니다.
5. 뷰어: 좌클릭 드래그 회전, 우클릭/Shift 드래그 이동, 휠 확대. 등각·정면·측면·평면, 분해, 라벨, 외곽치수.
6. 내보내기: **STL**(mm), **OBJ**(부품별 그룹), **PNG**, **JSON**(파라미터 + 출처 + 판독 소견).

API 키 없이도 프리셋과 수동 입력만으로 3D 를 만들 수 있습니다.

## 치수가 정해지는 순서

```
도면 판독값 ─┐
사람 입력값 ─┼─▶ 있으면 사용 (출처: 도면/입력)
            └─▶ 없으면 표준표 (ASME B16.5 / B16.10 / ISA-75.08.01 / API 609 참고값) ─▶ 없으면 비례 추정
```

판독 모델에게는 **도면에 적힌 값만** 달라고 합니다. 빈 칸은 앱이 채우고 출처를 따로 남깁니다.
도면에 전체 높이만 있으면 `overall_h` 에 넣으세요. 추정된 높이 치수들을 그 값에 맞춰 비례 조정합니다.

## 구조

```
ic-3d-builder/
├── index.html          ← 생성 파일 (단일 파일 앱). src/ 를 고치고 dev/build.py 로 다시 만든다
├── src/
│   ├── refdata.js      표준 치수 참고표 (원문 대조 전 — docs/drawing-sources.md 로 검증할 것)
│   ├── anatomy.js      품목별 파라미터 정의 + 부품 분해 + 설계 점검. three.js 비의존
│   ├── viewer.js       three.js 뷰어, STL/OBJ/PNG 내보내기
│   ├── extract.js      Claude 도면 판독 (구조화 출력)
│   └── app.js, index.html, styles.css
├── dev/
│   ├── build.py        src → index.html
│   ├── spec.mjs        presets | params | template | check  (브라우저 없이 스펙 검증)
│   ├── render.mjs      스펙 JSON → PNG (헤드리스)
│   └── shots.mjs       전 프리셋 스크린샷 (회귀 확인)
├── docs/drawing-sources.md   타입별 상세도면·치수표 출처 (웹 검색)
└── samples/                  예시 스펙
```

Claude Code 에서는 스킬 `.claude/skills/ic-ga-to-3d` 가 같은 엔진을 씁니다.
도면을 대화에 붙이고 "3D 로 만들어줘" 라고 하면 spec JSON → 점검 → 렌더 순서로 진행합니다.

## 한계 (정직하게)

- **표준표는 원문과 대조하지 않았습니다.** 작성 환경에서 표준·벤더 PDF 를 내려받을 수 없었습니다.
  `docs/drawing-sources.md` 의 원문으로 검증하기 전까지 '표준' 배지 값은 참고값입니다.
- PSV 중심-면 거리(C-I, C-O)는 API 526 표가 아직 없어 추정값입니다.
- 형상은 기본 도형 조합입니다. 외곽(envelope)·주요 치수는 맞추지만 주조 형상까지 재현하지 않습니다.
- 실제 도면 판독 정확도는 아직 측정하지 않았습니다. 대표 도면 몇 장으로 정답과 대조한 뒤 범위를 넓히세요.
