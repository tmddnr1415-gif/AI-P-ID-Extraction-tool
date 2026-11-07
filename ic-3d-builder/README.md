# I&C 3D Anatomy — GA / Dimensional Drawing → 분해·주석 3D

계측제어 품목의 GA·치수도를 넣으면 **부품 단위로 분해되고, 부품마다 설명과 사이즈·등급 연동
치수가 붙은** 파라메트릭 3D 모델을 만듭니다. 화면 표기는 영어입니다.
배치·간섭·유지보수 공간 검토와 교육용입니다. **제작·구매 치수로 쓰지 않습니다.**

| 품목 | 프리셋 | 분해되는 부품 (예) |
|---|---|---|
| Control Valve | Globe + spring & diaphragm, Ball / Butterfly + pneumatic rotary | Body, Seat ring, Cage, Plug, Stem, Bonnet gasket, Bonnet, Bonnet studs, Packing set, Packing follower/flange, Yoke, Stem connector, Travel indicator, Actuator stem, Lower/Upper casing, Actuator spring, Diaphragm plate, Diaphragm, Casing bolts, Positioner, Air filter regulator, Tubing (28) |
| MOV | Gate / Globe / Ball / Butterfly + 전동 | Thrust base, Drive bush, Main gearcase, Motor, Control unit & display, Declutch lever, Handwheel, Terminal compartment, Stem protection tube |
| Manual | Gate (OS&Y) / Globe / Ball (lever) / Butterfly (gear) | Wedge, Seat rings, Yoke sleeve, Gland, Gland flange & eyebolts, Ball, Seats, Trunnion, Disc, Liner, Shafts, Taper pins, Worm gearbox |
| PSV | 스프링식 앵글형 | Nozzle, Adjusting (blowdown) ring, Disc, Disc holder, Guide, Spindle, Spring washers, Spring, Bonnet, Adjusting screw, Cap / lifting lever |
| System Cabinet | 베이 수, 도어, 유지보수 공간 | Plinth, Frame, Side panels, Roof, Rear door, Front doors, Handles, Louvres, Mounting plate, DIN rails, I/O modules, Gland plate, Eye bolts |
| Instrument Hook-up | PT 스탠드, DP 유량(오리피스), DP 레벨(탱크) | Orifice set, Root valves, Impulse tubing, Manifold (2/3/5V), Transmitter, Stand, U-bolts, Drain/vent, Sunshade |

## 쓰는 법

1. `index.html` 을 브라우저로 엽니다 (더블클릭). three.js 를 cdnjs 에서 받으므로 인터넷이 필요합니다.
2. 품목 프리셋을 고릅니다.
3. GA 도면(PDF/PNG/JPG)을 넣고, 필요하면 힌트(사이즈·등급·치수표 행)를 적은 뒤 **Read drawing → 3D**.
   ⚙ Settings 에 Anthropic API 키가 필요합니다. 기본 모델 `claude-opus-5-5`.
   도면에서 **치수 + 구성 + Parts list(풍선 번호·부품명·재질·수량)** 를 읽어 3D 부품에 연결합니다.
4. 3D 조작
   - **휠 인 → 단계적으로 분해** (액추에이터 → 보닛 → 트림 순). 분해가 끝나면 그다음부터 휠은 커서 쪽으로 줌.
   - **휠 아웃 → 줌 아웃 후 다시 조립.**
   - 분해되면 부품마다 **번호 풍선 + 이름 콜아웃**이 양옆 열로 정렬되어 겹치지 않게 표시됩니다.
   - 부품 클릭 → **정보 카드**: 기능 설명, 재질(도면 값 또는 통상 재질), 수량, **사이즈·등급 연동 치수**(출처 배지 포함).
   - 더블클릭 → 그 부품만 **격리(Isolate)** 해서 확대. 다시 더블클릭하면 복귀.
   - **Cutaway** → 바디·하우징 앞쪽 절반을 잘라 내부(트림·스프링·패킹)를 보여줍니다.
   - 아래 **Parts list** 표: 번호 · 부품 · 그룹 · 수량 · 재질 · 대표 치수. 행 클릭 → 그 부품으로 이동.
5. 내보내기: **STL**(mm), **OBJ**(부품별 그룹, 번호 포함), **PNG**, **JSON**(파라미터 + 출처 + BOM).

API 키 없이도 프리셋과 수동 입력만으로 3D 를 만들 수 있습니다.

## 사이즈·등급 연동

NPS 와 압력등급(ASME Class)을 바꾸면 부품 치수가 함께 바뀝니다.

```
도면 판독값 ─┐
사람 입력값 ─┼─▶ 있으면 사용 (Drawing / User)
            └─▶ 없으면 표준표 (ASME B16.5 플랜지, B16.10 / ISA-75.08.01 / API 609 면간거리 — 참고값)
                          └─▶ 없으면 비례 추정 (Estimate)
```

정보 카드와 Parts list 의 치수에는 출처 배지가 붙습니다. 예: Body → `Size / rating 4" ASME CL300 RF [Drawing]`,
`Face-to-face 368 mm [Drawing]`, `End flange OD × thk 254 × 30.2 [Standard]`, `Port 77 mm [Estimate]`.
도면 Parts list 를 읽으면 풍선 번호·부품명·재질이 도면 것으로 바뀌고, 도면에 없는 부품은 그 뒤 번호로 이어집니다.

## 구조

```
ic-3d-builder/
├── index.html          ← 생성 파일 (단일 파일 앱). src/ 를 고치고 dev/build.py 로 다시 만든다
├── src/
│   ├── refdata.js      표준 치수 참고표 (원문 대조 전)
│   ├── anatomy.js      품목별 파라미터 + 부품 분해(기능·재질·치수·분해 경로) + 설계 점검. three.js 비의존
│   ├── viewer.js       three.js 뷰어: 휠 분해, 콜아웃, 컷어웨이, 격리, STL/OBJ/PNG
│   ├── extract.js      Claude 도면 판독 (치수 + Parts list, 구조화 출력)
│   └── app.js, index.html, styles.css
├── dev/
│   ├── build.py        src → index.html
│   ├── spec.mjs        presets | params | catalog | template | check  (브라우저 없이 스펙·BOM 검증)
│   ├── render.mjs      스펙 JSON → PNG (헤드리스, --explode --section)
│   └── shots.mjs       전 프리셋 조립/분해 + 상호작용 회귀 스크린샷
├── docs/drawing-sources.md   타입별 상세도면·치수표·부품 명칭 출처
└── samples/                  예시 스펙 (Parts list 포함)
```

Claude Code 에서는 스킬 `.claude/skills/ic-ga-to-3d` 가 같은 엔진을 씁니다.

## 참고한 것

- [thebuggeddev/anatomy](https://github.com/thebuggeddev/anatomy) — 핫스팟 점 + 콜아웃 + 부품 설명 구조, 분해/단면 상호작용.
  코드는 가져오지 않았고 상호작용 방식만 참고했습니다.
- Image Blaster 3D (World Labs) — 단일 이미지를 메쉬로 만드는 도구지만 유료 외부 API(World Labs, fal) 의존이고
  치수 정확도가 없어 쓰지 않았습니다. 이 툴은 도면 치수로 만드는 파라메트릭 방식입니다.
- 부품 명칭·기능: Fisher Control Valve Handbook 정의, ASME PTC 25 용어, API 600 / API 6D / API 609 / API 526,
  Rotork·Bettis 액추에이터 문헌 — `docs/drawing-sources.md`.

## 한계 (정직하게)

- **표준표는 원문과 대조하지 않았습니다.** 작성 환경에서 표준·벤더 PDF 를 내려받을 수 없었습니다.
- 부품 치수 중 포트·스템·패킹 등 상당수는 **비례 추정**입니다. 도면에 있으면 도면 값이 우선합니다.
- 부품 설명과 통상 재질은 일반적인 설계 기준이며 특정 벤더 제품과 다를 수 있습니다.
- 형상은 기본 도형 조합입니다. 외곽·주요 치수는 맞추지만 주조 형상까지 재현하지 않습니다.
- 실제 도면 판독 정확도는 아직 측정하지 않았습니다. 대표 도면 몇 장으로 정답과 대조한 뒤 범위를 넓히세요.
