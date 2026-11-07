# 계장ENG그룹 설계 자동화 플랫폼 — 임원 런칭 영상 제작 가이드 (Higgsfield · Seedance)

> 대상: 임원 보고 / 런칭 · 길이: **약 100초** (오프닝 8초 + 툴 7개 × 10초 + 비전 10초 + 클로징 10초)
> 제작 도구: Higgsfield Agent — `model=seedance_2_5`, `mode=video` (이미지 → 영상)
> **경량판** — Higgsfield 업로드용으로 모든 이미지를 JPG(1920×1080, 장당 200KB 이하)로 줄였습니다.

## ★ 업로드용 파일 (먼저 읽기)

Higgsfield Agent 에는 **zip 을 올리지 말고 `upload/` 안의 JPG 를 컷마다 한두 장씩** 올립니다.

| 컷 | Start frame | End frame |
|---|---|---|
| 0 오프닝 | `upload/00_opening_start.jpg` | `upload/00_opening_end.jpg` |
| 1 Dashboard | `upload/01_dashboard_start.jpg` | `upload/01_dashboard_end.jpg` |
| 2 P&ID | `upload/02_pid_start.jpg` | `upload/02_pid_end.jpg` |
| 3 Logic | `upload/03_logic_start.jpg` | `upload/03_logic_end.jpg` |
| 4 Panel | `upload/04_panel_start.jpg` | `upload/04_panel_end.jpg` |
| 5 도서검토 | `upload/05_books_start.jpg` | `upload/05_books_end.jpg` |
| 6 Datasheet | `upload/06_datasheet_start.jpg` | `upload/06_datasheet_end.jpg` |
| 7 계측기 3D | `upload/07_3d_start.jpg` | `upload/07_3d_end.jpg` |
| 7.5 비전 | `upload/09_vision_start.jpg` | `upload/09_vision_end.jpg` |
| 8 클로징 | `upload/08_closing_start.jpg` | `upload/08_closing_end.jpg` |

- 이 문서 아래쪽의 `NN_xxx/start_frame` · `end_frame` 표기는 위 표의 `upload/NN_xxx_start.jpg` · `_end.jpg` 를 뜻합니다.
- `alt_frame_*` → `edit/alt_frames/NN_xxx_alt_frame_*.jpg`, `title_overlay` → `edit/title_overlays/NN_xxx_title.png`(투명 PNG, 편집용), `reference_ui/` → `edit/reference_ui/`.
- 그래도 올라가지 않으면: 한 번에 올리는 장수를 줄이거나(컷당 Start 1장만), 이미지를 1280×720 으로 줄여 다시 시도하세요.

---

## 0. 먼저 확인할 것 — 외부 업로드 보안

Higgsfield 는 **외부 서비스**입니다. 대시보드 운영 문서(`DASHBOARD_ARCHITECTURE.md`)에 "사내 기밀 데이터. 외부 서비스로 전송 금지" 규정이 있습니다.

| 폴더 | 화면 데이터 | 업로드 판단 |
|---|---|---|
| 01 Dashboard | 시연용 **예시 PJT** (가상) | 업로드 가능 |
| 02 PID | **실제 프로젝트 도면**(QFE) — 파일명 · 프로젝트명 · 타이틀블록 **블러 처리**함 | **보안 승인 후** 사용. 도면 형상 자체는 실제임 |
| 03 Logic | **실제 Logic 도면**(HRSG · 19VA · FG) — 파일명 · 타이틀블록 · 시트 목록 **블러 처리**함 | **보안 승인 후** 사용 |
| 04 Panel | `SAMPLE CCR` 예시 배치 | 업로드 가능 |
| 05 도서검토 | 시연용으로 만든 **가상 기술 도서 8권** | 업로드 가능 |
| 06 Datasheet | 시연용 **가상 밸브 데이터시트** (태그 00XV 921~928) | 업로드 가능 |
| 07 계측기 3D | 프리셋 파라메트릭 모델 (도면 없음) | 업로드 가능 |

승인이 어려우면 02·03 은 **업로드하지 말고** 편집 단계에서 `start_frame.png` → `end_frame.png` 를 정지 화면 + 줌(Ken Burns)으로 직접 넣으세요(§6). 영상 톤은 동일하게 유지됩니다.

---

## 1. 영상 구성 (스토리보드)

| # | 컷 | 길이 | 생성 입력 (Start → End) | 화면에서 일어나는 일 | 타이틀 오버레이 |
|---|---|---|---|---|---|
| 0 | 오프닝 | 8s | `00_opening/start_frame` → `end_frame` | 어두운 블루프린트 공간에 빛줄기가 흐르고, 7개 화면이 떠오르며 벽을 이룸 | `00_opening/title_overlay` |
| 1 | Dashboard | 10s | `01_dashboard/start_frame` → `end_frame` | 기울어진 디스플레이로 천천히 다가가 KPI · 그래프 클로즈업 | `01_dashboard/title_overlay` |
| 2 | P&ID | 10s | `02_pid/start_frame` → `end_frame` | 결과 화면에서 도면 오버레이(색 표시된 계기 버블)로 푸시인 | `02_pid/title_overlay` |
| 3 | Logic | 10s | `03_logic/start_frame` → `end_frame` | Logic 검토 화면 → 게이트 회로 클로즈업, 신호선이 빛나며 흐름 | `03_logic/title_overlay` |
| 4 | Panel | 10s | `04_panel/start_frame` → `end_frame` | **2D 판넬 배치도가 3D 제어실로 솟아오름** (하이라이트 컷) | `04_panel/title_overlay` |
| 5 | 도서검토 | 10s | `05_books/start_frame` → `end_frame` | 검색창 질문 → 근거 문장 · 책 페이지가 강조된 답변으로 이동 | `05_books/title_overlay` |
| 6 | Datasheet | 10s | `06_datasheet/start_frame` → `end_frame` | 데이터시트 뷰어 → 검토 표의 강조 셀(19.6 barg)로 클로즈업 | `06_datasheet/title_overlay` |
| 7 | 계측기 3D | 10s | `07_3d/start_frame` → `end_frame` | 컨트롤 밸브가 천천히 돌며 **부품 단위로 분해** (하이라이트 컷) | `07_3d/title_overlay` |
| 7.5 | **비전 (지속 발전)** | 10s | `09_vision/start_frame` → `end_frame` | 7개 화면이 빛의 선으로 서로 이어지고, 연결망이 빛으로 수렴 | `09_vision/title_overlay` |
| 8 | 클로징 | 10s | `08_closing/start_frame` → `end_frame` | 7개 화면 파노라마가 뒤로 물러나며 빛으로 수렴 → 로고 자리 | `08_closing/title_overlay` |

**대체 컷(alt_frame_*)** — 10초가 단조로우면 툴마다 5초 × 2컷으로 나눠 쓰세요.

| 툴 | 대체 컷 | 내용 |
|---|---|---|
| Dashboard | `alt_frame_sheet_board` | 수행 PJT 보드 |
| P&ID | `alt_frame_evidence` · `alt_frame_rev_compare` | 판정 근거 표 · Rev.A↔B 나란히 대조 |
| Logic | `alt_frame_trace` · `alt_frame_draw_sim` | 동작 시뮬레이션(거슬러 올라가기) · LOGIC 작성 시뮬레이션 |
| Panel | `alt_frame_person_view` · `alt_frame_dcs_room` | 사람 시점 통로 확인 · DCS 룸 3D |
| Datasheet | `alt_frame_dashboard` · `alt_frame_rev_compare` | 검토 대시보드 · Rev 비교 |
| 3D | `alt_frame_lineup` · `alt_frame_ui` | 5개 품목 라인업 · 3D Builder 화면 |

---

## 2. Higgsfield 에서 만드는 순서

1. Higgsfield Agent 에서 모델 **Seedance 2.5 / Video** 선택, 화면비 **16:9**, 해상도 1080p(가능한 최고), 길이 **10초**(또는 5초).
2. 컷마다 **Start frame = `start_frame.png`**, (지원되면) **End frame = `end_frame.png`** 업로드.
   End frame 을 받지 않는 모드면 Start 만 넣고 프롬프트의 카메라 지시로 움직임을 만듭니다.
3. 아래 §4 의 **공통 스타일 + 컷 프롬프트(영문)** 를 붙여 넣습니다. (모델은 영문 프롬프트를 더 정확히 따릅니다.)
4. 컷당 2~3개 생성 → **화면 속 UI 글자가 덜 일그러진 것**을 고릅니다.
5. 9개 컷을 이어 붙이고, `title_overlay.png`(투명 PNG)를 각 컷 위에 2~3초 페이드 인으로 올립니다. 내레이션(§5) · 음악(§7)을 얹어 완성.

> **타이틀은 영상 생성에 넣지 마세요.** AI 영상은 한글을 뭉개므로, 글자는 전부 편집에서 오버레이 PNG 로 올립니다. 생성 프레임에는 글자 영역을 일부러 비워 두었습니다(화면 왼쪽 아래).

---

## 3. 이미지 목록

```
images/
├── 00_opening/   start_frame · end_frame · title_overlay
├── 01_dashboard/ start_frame · end_frame · alt_frame_sheet_board · title_overlay · reference_ui/
├── 02_pid/       start_frame · end_frame · alt_frame_evidence · alt_frame_rev_compare · title_overlay · reference_ui/
├── 03_logic/     start_frame · end_frame · alt_frame_trace · alt_frame_draw_sim · title_overlay · reference_ui/
├── 04_panel/     start_frame · end_frame · alt_frame_person_view · alt_frame_dcs_room · title_overlay · reference_ui/
├── 05_books/     start_frame · end_frame · title_overlay · reference_ui/
├── 06_datasheet/ start_frame · end_frame · alt_frame_dashboard · alt_frame_rev_compare · title_overlay · reference_ui/
├── 07_3d/        start_frame · end_frame · alt_frame_lineup · alt_frame_ui · title_overlay · reference_ui/ · cutouts_png/
├── 08_closing/   start_frame · end_frame · title_overlay
└── 09_vision/    start_frame · end_frame · title_overlay   (7번과 클로징 사이에 넣는 비전 컷)
```

- `start_frame` / `end_frame` / `alt_frame_*` — **1920×1080 PNG, 생성 입력용.** 남색 스튜디오 배경 위 떠 있는 디스플레이 연출, 글자 없음.
- `title_overlay` — **1920×1080 투명 PNG**, 편집에서 위에 얹는 한글 타이틀.
- `reference_ui/` — 실제 프로그램 화면 원본(블러 처리 포함). Higgsfield 의 *reference image* 칸이나 편집 인서트용.
- `07_3d/cutouts_png/` — 배경을 뺀 3D 모델(투명 PNG). 편집에서 자유롭게 배치 가능.
- `contact_sheet.jpg` — 전체 프레임 한눈에 보기.

---

## 4. 프롬프트

### 4-1. 공통 스타일 (모든 컷 앞에 붙이기)

```
Cinematic corporate product launch film for an engineering software platform.
Deep navy studio with a subtle blueprint grid, soft volumetric blue light, glossy reflections,
premium tech keynote look, smooth slow camera, shallow depth of field, 24fps, high detail.
Keep the software screen content exactly as in the input image — do not invent, rewrite or
animate any on-screen text, numbers or UI elements. No people, no logos, no added text.
```

**Negative (지원 시):** `distorted text, warped UI, flicker, morphing screen content, extra hands, people, watermark, logo, cartoon, low resolution`

### 4-2. 컷별 프롬프트

**00 오프닝 (8s)** — start → end
```
Darkness with a faint blueprint grid. Thin cyan light lines trace like piping and signal
lines across the floor, then seven floating glass displays rise from the light and settle
into a gently curved wall. Slow dolly back, light bloom, anticipation.
```

**01 Dashboard (10s)**
```
Slow push-in toward a single floating display showing a business dashboard with KPI cards
and bar charts. The display gradually turns to face the camera and fills the frame.
Gentle light sweep across the glass. Calm, confident pacing.
```

**02 P&ID (10s)**
```
A floating display shows an engineering drawing review screen: drawing on the left,
instrument list on the right. Camera pushes into the drawing area; the highlighted
instrument symbols softly glow one after another, as if being detected. Precise, analytical mood.
```

**03 Logic (10s)**
```
A floating display shows a logic diagram review tool. Camera pushes into the logic circuit;
thin blue signal pulses travel along the wires from gate to gate, illustrating signal tracing.
Slow, deliberate, technical.
```

**04 Panel (10s) — 하이라이트**
```
A floating display shows a 2D top-view floor plan of a control room with colored cabinet
blocks. The plan smoothly extrudes into a 3D isometric room: cabinets rise from the floor,
walls grow up, the camera orbits slightly to a three-quarter view. Satisfying, architectural transformation.
```

**05 도서검토 (10s)**
```
A floating display shows a document search screen. The search bar gently pulses, then the
camera glides down to the answer panel where highlighted source passages softly glow,
like knowledge being retrieved from a library. Warm, helpful mood.
```

**06 Datasheet (10s)**
```
A floating display shows a valve datasheet review tool with a document viewer and checklist.
Camera pushes into the datasheet table; one highlighted cell pulses amber, indicating a
detected change. Precise quality-control mood.
```

**07 계측기 3D (10s) — 하이라이트**
```
A studio product shot of an industrial control valve on a glowing blue pedestal. The valve
slowly rotates, then separates into its components — actuator, yoke, bonnet, body, flanges —
floating apart in an exploded view, each part catching the light. Premium industrial product reveal.
```

**09 비전 — 지속 발전 (10s)** · 7번(3D)과 클로징 사이
```
Seven floating software displays arranged in two rows. Thin glowing light lines begin to
connect the displays to each other, forming a growing network; data pulses travel along the
links. The camera slowly pulls back as the network brightens and gathers into a soft central
glow, leaving clean dark space for the title. Hopeful, forward-looking mood.
```

**08 클로징 (10s)**
```
A curved panorama of seven glowing software displays slowly recedes into the distance and
converges into a single point of soft blue light at the center, leaving a clean dark space
for the final title. Elegant, inspiring finish.
```

### 4-3. 대체 컷 프롬프트 (5초용, 필요할 때)

| 이미지 | 프롬프트 |
|---|---|
| `01/alt_frame_sheet_board` | `Slow lateral glide across a floating project status board display, subtle light sweep.` |
| `02/alt_frame_rev_compare` | `Two drawing revisions side by side on a floating display; camera slowly slides from left to right.` |
| `03/alt_frame_trace` | `Close-up of a logic simulation panel; a highlighted path glows step by step upward.` |
| `04/alt_frame_person_view` | `First-person walk down a narrow aisle between control cabinets, steady slow forward motion.` |
| `04/alt_frame_dcs_room` | `Slow orbit around a 3D control room model with labeled cabinets and columns.` |
| `06/alt_frame_rev_compare` | `Two datasheet revisions side by side; a changed row softly highlights.` |
| `07/alt_frame_lineup` | `Product lineup of a cabinet and several industrial valves on a glowing stage, slow dolly across.` |

---

## 5. 내레이션 대본 (한국어, 약 85초)

| 컷 | 내레이션 | 자막/숫자 강조 |
|---|---|---|
| 0 | 도면 한 장에서 수천 개의 계기를 찾고, 로직을 따라가고, 판넬 자리를 계산하는 일. 지금까지는 사람의 시간이었습니다. 계장ENG그룹이 그 시간을 되찾는 설계 자동화 플랫폼을 시작합니다. | 계장 설계 자동화 플랫폼 |
| 1 | 모든 것은 하나의 Dashboard 에서 시작합니다. 주간업무와 프로젝트 현황, 그리고 일곱 개의 도구가 한 화면에 있습니다. | 7개 도구 · 한 화면 |
| 2 | P&ID 도면을 넣으면 계기·밸브 리스트가 발주처 양식 그대로 나옵니다. 도면 58장에 약 5분. 모든 행에는 도면 위 판정 근거가 남습니다. | 58장 → 약 5분 |
| 3 | Logic Diagram 50장을 1분 안팎에 읽고, 시트 사이 신호를 잇습니다. 최종 명령에서 최초 입력까지 동작을 거슬러 올라가고, 같은 양식으로 새 로직도 그립니다. | 식별률 99.5% |
| 4 | 판넬을 배치하면 필요 면적과 권장 실 크기가 바로 계산됩니다. 2D 배치는 그대로 3D 제어실이 되고, 통로와 유지보수 공간을 사람 시점에서 확인합니다. | 필요 면적 · 권장 실 크기 |
| 5 | 부서의 기술 도서를 본문까지 찾습니다. 말하듯 물으면 어느 책 몇 쪽인지, 근거와 함께 답합니다. | 근거와 함께 답하는 검색 |
| 6 | 밸브 데이터시트는 자동으로 검토됩니다. 리비전 변경, 공정 데이터, 배관 사양 적합성까지 — 사람은 확인이 필요한 곳만 봅니다. | Rev · Process · PMS |
| 7 | GA 도면은 부품 단위 3D 모델이 됩니다. 컨트롤 밸브부터 MOV, PSV, 시스템 캐비닛까지 열여섯 품목. 배치와 간섭, 유지보수 공간을 미리 봅니다. | 16개 품목 · STL / OBJ |
| 7.5 | 이 도구들은 쓸수록 정확해집니다. 사람이 검토한 내용은 규칙으로 쌓이고, 일곱 개의 도구는 하나의 데이터로 이어집니다. 반복 작업은 줄고, 품질은 높아지고, 개인의 노하우는 조직의 자산이 됩니다. | 쓸수록 더 정확해지는 플랫폼 |
| 8 | 근거는 도면에, 판단은 사람에게. 계장ENG그룹 설계 자동화 플랫폼 — 도면에서 결정까지, 더 빠르게. | 도면에서 결정까지, 더 빠르게 |

숫자 출처: P&ID "도면 58장 기준 5분 남짓"(프로그램 첫 화면 안내), Logic "50장 기준 약 40초~1분"(LOGIC 분석 안내) · "식별률 99.5%"(HRSG Logic 50장 실측 화면), 3D "16개 품목"(I&C 3D Builder 프리셋 수). 그 밖의 효과 수치는 넣지 않았습니다 — 임원 보고용 정량 효과(시간 절감 등)는 부서 실측치로 채워 넣으세요.

---

## 6. 편집 가이드

- **타이틀:** 각 컷 시작 0.5초 후 `title_overlay.png` 를 0.6초 페이드 인, 컷 끝 1초 전 페이드 아웃. 오프닝 · 클로징은 가운데 정렬 타이틀이라 생성 영상 마지막 3초에 얹습니다.
- **컷 연결:** 툴 컷 사이는 0.4초 크로스 디졸브 또는 빛 번짐(light leak) 전환.
- **AI 생성이 어려운 컷(02·03 보안 미승인 등):** `start_frame` 을 5초 정지 + 105%→115% 줌, 이어서 `end_frame` 5초 정지 + 100%→108% 줌. 남색 배경 · 디스플레이 연출이 같아 생성 컷과 자연스럽게 섞입니다.
- **로고:** 클로징 `end_frame` 가운데 빈 공간에 회사/그룹 로고를 올리세요 (이 kit 에는 회사 로고를 넣지 않았습니다).

## 7. 음악 · 사운드

- 테크 키노트 계열 시네마틱 앰비언트 → 4번(Panel 3D) · 7번(3D 분해)에서 비트 상승 → 클로징에서 해소. BPM 90~100.
- 효과음: 컷 전환 whoosh(작게), Panel 3D 솟아오름 · 밸브 분해 시 금속성 click.

## 8. 체크리스트

- [ ] 02 PID · 03 Logic 이미지 외부 업로드 보안 승인 (또는 §6 정지 화면 방식)
- [ ] 컷별 2~3개 생성 후 UI 글자 일그러짐 적은 것 선택
- [ ] 타이틀 오버레이 · 내레이션 · 음악 합성
- [ ] 정량 효과 수치(시간 절감 등)는 부서 실측으로 확인 후 삽입
- [ ] 최종본 길이 95~105초, 1080p

---

## 9. 지속 발전 시 기대 결과와 이점

> 임원 보고용 요약 자료입니다. 영상 비전 컷(§1 7.5번)의 근거이며, 보고서·발표 자료에 그대로 옮겨 써도 됩니다.
> 효과 수치는 **추정하지 않았습니다** — §9-4 의 지표로 실측해 채우는 것을 전제로 합니다.

### 9-1. 왜 "쓸수록" 좋아지는가 — 구조적 이유

| 이미 들어 있는 구조 | 지속 발전 시 결과 |
|---|---|
| 사람이 고친 값과 사유가 남고, 검토 지적이 **판독 규칙으로 누적**됨 (P&ID · Logic "가르치기", Datasheet Rule Performance) | 프로젝트를 거칠수록 자동 판정 범위가 넓어지고, 사람이 볼 곳이 줄어듦 |
| 판정 규칙을 **그 도면의 범례 · NOTES 에서 런타임에 읽음** (외워 둔 상수를 줄여 가는 방식) | 새 프로젝트 · 새 발주처 양식에도 처음부터 적용 가능 — 확장 비용이 프로젝트마다 줄어듦 |
| 모든 결과에 **도면 위 근거**가 행마다 남음 | 자동화 범위가 넓어져도 검증 가능성이 유지됨 — 품질 감사 · 클레임 대응 근거 |
| 7개 도구가 **하나의 Dashboard · 같은 서버**에 있음 | 도구 간 데이터 연결(§9-2 중기)이 추가 인프라 없이 가능 |

### 9-2. 단계별 발전 방향

| 단계 | 내용 | 기대 결과 |
|---|---|---|
| **단기 — 정착** (현 단계) | 실 프로젝트 적용 확대 · 사람 검토 → 규칙 누적 · 프로젝트별 정확도 측정 | 툴별 처리 시간 단축 실측, 사용 부서원 · 프로젝트 확대 |
| **중기 — 연결** | ① P&ID 계기 리스트 ↔ Datasheet 검토 태그 대조 ② Logic IO List ↔ P&ID 태그 교차 검증 ③ IO 수량 → 판넬 수 · ROOM SIZE 자동 산정 ④ Datasheet 치수 → 3D 모델 ⑤ 검토 근거 ↔ 도서검토 표준 · 매뉴얼 연결 | 도구 사이 **불일치를 자동 발견** — 문서 간 누락 · 오기가 설계 단계에서 걸러짐 |
| **장기 — 플랫폼** | 프로젝트 이력 기반 지식 자산 · 입찰 물량 산출 자동화 · 신규 프로젝트 초기 설계 템플릿 · 타 그룹(배관 · 전기 등) 확장 | 입찰 대응 속도 · 정확도 향상, 설계 표준이 데이터로 축적 |

### 9-3. 이점 (임원 관점)

1. **시간 · 원가** — 도면 판독 · 리스트 작성 · 리비전 대조 같은 반복 업무가 자동화되어, 엔지니어가 판단 · 조율 같은 고부가 업무에 집중. 입찰 기간 내 물량 산출 · 검토 대응이 빨라짐.
2. **품질 · 리스크** — Rev 변경, Process Data 불일치, PMS 부적합, 판넬 공간 부족을 **설계 단계에서 조기 발견** → 현장 재작업 · 설계 변경 · 클레임 위험 감소. 결과마다 근거가 남아 검증 · 감사가 쉬움.
3. **지식 자산화** — 숙련자의 검토 노하우가 규칙 · 이력 · 도서 색인으로 남아 **개인이 아닌 조직의 역량**이 됨. 인력 이동 · 신입 온보딩 부담 감소.
4. **표준화 · 일관성** — 같은 도면은 누가 돌려도 같은 결과(재분석 결과 동일성 보장). 프로젝트 · 담당자에 따른 품질 편차 축소.
5. **가시성 · 협업** — 주간업무 · 프로젝트 현황 · 분석 결과가 한 Dashboard 에 모여 관리자가 진행 상황을 즉시 파악.
6. **보안 · 통제** — 사내 서버에서 운영, P&ID 검출은 외부 AI 를 쓰지 않음 → 도면 데이터 외부 유출 없이 확장 가능.
7. **확장성** — 범례 · 양식을 도면에서 읽는 구조라 새 발주처 · 새 프로젝트 · 다른 공종으로 넓힐 때 추가 비용이 작음.

### 9-4. 성과 측정 지표 (제안)

| 지표 | 측정 방법 |
|---|---|
| 툴별 처리 시간 (전 → 후) | 동일 도면 세트로 수작업 대비 소요 시간 비교 |
| 사람 수정률 | 자동 결과 중 사람이 고친 칸 비율 — 프로젝트를 거치며 감소 추이 |
| 조기 발견 건수 | Rev 변경 · 불일치 · 부적합 · 공간 부족을 설계 단계에서 잡은 건수 |
| 재작업 · 설계 변경 건수 | 적용 프로젝트 vs 미적용 프로젝트 비교 |
| 활용도 | 사용 부서원 수 · 적용 프로젝트 수 · 누적 규칙 수 |

> 영상 내레이션(§5, 7.5번)은 위 내용을 15초 분량으로 줄인 것입니다. 실측치가 나오면 비전 컷 자막에 숫자 1~2개(예: "리스트 작성 시간 ○○% 단축")를 넣으면 임원 설득력이 크게 올라갑니다.
