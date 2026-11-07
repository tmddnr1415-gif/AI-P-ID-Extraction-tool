# Anatomy 파라미터 사전

생성 파일 — `node ic-3d-builder/dev/spec.mjs params` 로 다시 만든다. 원본은 `ic-3d-builder/src/anatomy.js`.

## `valve` — 밸브 (CV · MOV · Manual · PSV)

| key | 단위 | 선택지 | 의미 |
|---|---|---|---|
| `tag` |  |  | Tag No. |
| `body` |  | globe, gate, ball, butterfly, psv | 바디 형식 — globe / gate / ball / butterfly / psv(앵글형 안전밸브) |
| `operator` |  | handwheel, lever, gear, pneumatic_diaphragm, pneumatic_rotary, electric, spring | 조작기 — handwheel, lever, gear(웜기어), pneumatic_diaphragm(CV), pneumatic_rotary(랙피니언/스카치요크), electric(MOV), spring(PSV) |
| `service` |  | control, on_off | 용도 — control 이면 글로브 면간거리를 ISA-75.08.01 로 잡는다 |
| `nps` | in |  | 호칭경 (inlet) |
| `cls` |  | 150, 300 | 압력등급 (inlet) |
| `outlet_nps` | in |  | 출구 호칭경 |
| `outlet_cls` |  | 150, 300 | 출구 등급 |
| `ftf` | mm |  | 면간거리 F-F — 플랜지 면과 면 사이 거리 |
| `cti` | mm |  | 중심-입구면 (C-I) — 밸브 중심(출구 축)에서 입구 플랜지 면까지 수직거리 |
| `cto` | mm |  | 중심-출구면 (C-O) — 밸브 중심(입구 축)에서 출구 플랜지 면까지 수평거리 |
| `body_h` | mm |  | 바디 높이 (CL→보닛 플랜지) |
| `body_w` | mm |  | 바디 최대폭 |
| `bonnet_h` | mm |  | 보닛/넥 높이 — 보닛 플랜지 위 ~ 요크/조작기 장착면 (PSV 는 스프링 하우징 높이) |
| `pipe_stub` | mm |  | 참조 배관 길이 — 0 이면 표시 안 함 |
| `yoke_h` | mm |  | 요크/브래킷 높이 |
| `act_d` | mm |  | 액추에이터 지름/폭 |
| `act_h` | mm |  | 액추에이터 높이 |
| `act_l` | mm |  | 실린더 길이 (로터리) |
| `hw_d` | mm |  | 핸드휠 지름 |
| `lever_l` | mm |  | 레버 길이 |
| `stem_ext` | mm |  | 스템 노출 (Rising stem 열림) |
| `positioner` |  | true, false | 포지셔너 |
| `cv_handwheel` |  | true, false | 상부 수동 핸드휠 |
| `psv_lever` |  | true, false | 리프팅 레버 |
| `overall_h` | mm |  | 전체 높이 (CL→최상단) — 도면에 전체 높이만 있으면 여기 넣는다. 추정 높이 치수들을 이 값에 맞춰 비례 조정한다 |

## `cabinet` — System Cabinet

| key | 단위 | 선택지 | 의미 |
|---|---|---|---|
| `tag` |  |  | Cabinet No. |
| `bays` |  |  | 연결 베이 수 |
| `w` | mm |  | 폭 W (베이당) |
| `h` | mm |  | 높이 H (플린스 제외) |
| `d` | mm |  | 깊이 D |
| `plinth_h` | mm |  | 플린스(베이스) 높이 |
| `doors` |  | 1, 2 | 전면 도어 수 |
| `rear_door` |  | true, false | 후면 도어 |
| `door_open` | ° |  | 도어 열림각 (간섭검토) |
| `louvers` |  | true, false | 도어 루버 |
| `fan` |  | true, false | 루프 팬 |
| `lifting_eyes` |  | true, false | 리프팅 아이볼트 |
| `mounting_plate` |  | true, false | 마운팅 플레이트 |
| `modules` |  |  | I/O·DIN 모듈 행 |
| `gland_plate` |  | true, false | 하부 케이블 글랜드 플레이트 |
| `clearance` | mm |  | 전면 유지보수 공간 표시 — 0 이면 표시 안 함 |

## `hookup` — Instrument Hook-up

| key | 단위 | 선택지 | 의미 |
|---|---|---|---|
| `tag` |  |  | Tag No. |
| `inst` |  | PT, DPT, LT_DP, FT_DP | 계기 — PT=압력, DPT=차압(오리피스), LT_DP=차압식 레벨(탱크 노즐 2개), FT_DP=유량(오리피스 탭) |
| `service` |  | gas, liquid, steam | 유체 — gas=계기 위(탭 상부), liquid/steam=계기 아래(탭 측면/하부). 튜빙 기울기 방향이 바뀐다 |
| `proc_nps` | in |  | 공정배관 호칭경 |
| `pipe_el` | mm |  | 배관 중심 높이 (바닥 기준) |
| `tap` |  | top, side, bottom, side45 | 탭 방향 |
| `tap_sep` | mm |  | HP-LP 탭 간격 — DP: 오리피스 플랜지 탭 간격, LT_DP: 상·하부 노즐 고저차 |
| `mount` |  | stand, close_coupled | 설치 |
| `stand_h` | mm |  | 스탠드 높이 |
| `stand_dx` | mm |  | 스탠드 위치 X (배관 축 방향) |
| `stand_dz` | mm |  | 스탠드 위치 Z (배관에서 이격) |
| `tube_od` | mm |  | 임펄스 튜브 OD |
| `slope` | 1:x |  | 튜빙 기울기 — 수평 구간 최소 기울기. 1:12 가 일반적 |
| `root_valve` |  | true, false | 루트밸브 |
| `manifold` |  | none, 2V, 3V, 5V | 매니폴드 |
| `drain` |  | true, false | 드레인/벤트 밸브 |
| `sunshade` |  | true, false | 선쉐이드 |


프리셋:
```
cv_globe   valve    Control Valve — Globe (공압 다이어프램)
cv_ball    valve    Control Valve — Ball (공압 로터리)
cv_bfv     valve    Control Valve — Butterfly (공압 로터리)
mov_gate   valve    MOV — Gate
mov_globe  valve    MOV — Globe
mov_ball   valve    MOV — Ball
mov_bfv    valve    MOV — Butterfly
man_gate   valve    Manual — Gate (핸드휠, Rising stem)
man_globe  valve    Manual — Globe (핸드휠)
man_ball   valve    Manual — Ball (레버)
man_bfv    valve    Manual — Butterfly (기어)
psv        valve    PSV — Spring Loaded (앵글)
cabinet    cabinet  System Cabinet
hook_pt    hookup   Hook-up — PT (스탠드)
hook_dpt   hookup   Hook-up — DP 유량 (오리피스)
hook_lt    hookup   Hook-up — DP 레벨 (탱크)
```
