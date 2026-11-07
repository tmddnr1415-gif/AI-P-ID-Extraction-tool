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
   - **휠 인 → 단계적으로 분해** (액추에이터 → 보닛 → 트림 순, 약 5칸). 분해가 끝나면 그다음부터 휠은 **커서 아래 표면**으로
     한 칸에 약 30 %씩 다가가며, 너트·이름판이 화면을 채울 만큼(보이는 높이 3 mm) 가까이 갈 수 있습니다.
     분해 없이 바로 줌하려면 툴바의 **Scroll to explode** 를 끄세요.
   - **휠 아웃 → 줌 아웃 후 다시 조립.**
   - 분해되면 부품마다 **번호 풍선 + 이름 콜아웃**이 양옆 열로 정렬되어 겹치지 않게 표시됩니다.
   - 부품 클릭 → **정보 카드**: 기능 설명, 재질(도면 값 또는 통상 재질), 수량, **사이즈·등급 연동 치수**(출처 배지 포함).
   - 더블클릭 → 그 부품만 **격리(Isolate)** 해서 확대. 다시 더블클릭하면 복귀.
   - **Cutaway** → 바디·하우징 앞쪽 절반을 잘라 내부(트림·스프링·패킹)를 보여줍니다.
   - 아래 **Parts list** 표: 번호 · 부품 · 그룹 · 수량 · 재질 · 대표 치수. 행 클릭 → 그 부품으로 이동.
5. 내보내기: **STL**(mm), **OBJ**(부품별 그룹, 번호 포함), **PNG**, **JSON**(파라미터 + 출처 + BOM).

API 키 없이도 프리셋과 수동 입력만으로 3D 를 만들 수 있습니다.

## 실물처럼 보이게 (Realistic 스타일, 기본)

[anatomy 스킬](https://github.com/wheresryan22/anatomy)의 원칙을 3D 에 옮겼습니다 — "부품은 실제로 만들 수 있는 모양으로,
작은 실제 부품까지, 곡면은 계단 없이 매끄럽게, 물체 아래에는 부드러운 그림자".

- **선반 가공 프로파일(lathe)**: 플랜지(허브 필렛·모따기·1.6 mm raised face·보어), 보닛, 다이어프램 케이스(림 플랜지·돔),
  MOV 기어케이스, PSV 보닛·캡, 트랜스미터 하우징을 반단면 프로파일을 회전시켜 만듭니다. 곡면은 부드럽게, 단차는 각지게.
- **실제 작은 부품**: 육각 너트·와셔가 달린 스터드 볼트, 볼트 서클, 플랜지 개스킷, 이름판(Tag·사이즈·등급이 실제 값으로 새겨짐),
  주물 흐름 화살표, 포지셔너·에어셋 압력계, MOV LCD 표시창·셀렉터 노브·단자함 볼트, 모터 냉각 핀, 캐비닛 경첩·루버.
- **재질**: 도장 주물(오렌지필 범프), 가공·연마 스틸(브러시드 거칠기), 스테인리스 트림, 청동 너트, PTFE, 고무, 도장 액추에이터.
  물리 기반 재질 + 스튜디오 환경맵 반사 + ACES 톤매핑.
- **촬영 무대**: 원근 카메라, 받침대, 부드러운 그림자와 접지 그림자(halo). 그림자는 받침대 위에만 떨어집니다.
- 툴바 **Style → Technical** 로 이전의 평면 톤 + 윤곽선 + 정사영 스타일로 바꿀 수 있습니다 (도면 대조용).

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

- [thebuggeddev/anatomy](https://github.com/thebuggeddev/anatomy) — 핫스팟 점 + 콜아웃 + 부품 설명 구조, 분해/단면 상호작용,
  렌더 설정(ACES 톤매핑, PMREM 환경맵, 키·필·림 조명, 받침대와 접지 그림자). 코드는 가져오지 않았습니다.
- [wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) (Claude Code 스킬) — craft 규칙: lathe 프로파일(스텝은 각지게, 곡선은 smooth),
  작은 실제 부품(볼트·이름판·리브), 부드러운 곡면 음영, 물체 아래 halo, 재질은 주제에·바닥은 무채색. 코드는 가져오지 않았습니다.
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
