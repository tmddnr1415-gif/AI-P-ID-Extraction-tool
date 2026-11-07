# 타입별 상세도면 · 치수표 출처

웹 검색으로 찾은 GA / Dimensional Drawing과 치수표 출처를 타입별로 모았습니다 (2026-11 검색).
**이 목록은 링크만 담고 있습니다.** 이 세션의 네트워크에서는 PDF 원문을 내려받지 못했으므로,
`src/refdata.js`의 표준 치수는 원문과 대조하지 않은 참고값입니다. 아래 원문을 받으면 표를 검증하고,
틀린 값은 고친 뒤 커밋 메시지에 출처를 남기세요.

벤더 도면은 저작권 문서입니다. 저장소에는 PDF를 커밋하지 말고, 링크와 읽어 낸 치수만 남깁니다.

## 공통 — 플랜지 · 면간거리 표준

| 대상 | 출처 | 비고 |
|---|---|---|
| 밸브 면간거리 (gate/globe/ball/check) | ASME B16.10 — [Accuris 미리보기](https://store.accuristech.com/cii/products/preview/2257369), [Wermac CL150 표](https://wermac.org/valves/dim_valves_ff.html), [Wermac CL300 표](https://www.wermac.org/valves/dim_valves_ff_300.html), [Project Materials 요약](https://blog.projectmaterials.com/valves/asme-b16-10-valve-face-to-face) | 원문은 유료. Wermac 표로 1차 검증 |
| 주강 Gate/Globe/Check 카탈로그 | [Milwaukee Valve Cast Steel](https://www.milwaukeevalve.com/wp-content/uploads/literature-newsletters/CastSteelGateGlobeCheck.pdf) | 높이·핸드휠 지름까지 있음 |

## Control Valve (Globe)

| 출처 | 비고 |
|---|---|
| ANSI/ISA-75.08.01 일체형 플랜지 글로브 면간거리 — [ANSI 미리보기](https://webstore.ansi.org/preview-pages/ISA/preview_ANSI+ISA+75.08.01-2016.pdf) | `control_globe` 면간거리 표의 근거 |
| ANSI/ISA-75.08.07 분리형 플랜지 — [ISA](https://www.isa.org/products/ansi-isa-75-08-07-2001-r2026-face-to-face-dimensio) | |
| [Fisher Sliding Stem Valve Selection Guide](https://www.heatingandprocess.com/wp-content/uploads/2016/07/Fisher-Sliding-Stem-Valve-Selection-Guide.pdf) | 바디·액추에이터 조합. 실제 치수는 각 제품 Bulletin |

## MOV (전동 액추에이터)

| 출처 | 비고 |
|---|---|
| [Rotork IQ3 제품 페이지](https://www.rotork.com/products/electric-actuators/iq3) · [IQ3 Pro](https://www.rotork.com/products/electric-intelligent-actuators/iq3-pro) | Multi-turn / Part-turn 치수도 PDF·DXF |
| [Rotork IQT1000~3000 치수도](https://rotork.com/nl/documents/engineering/29833) | Part-turn (Ball/Butterfly MOV) |
| Rotork 2D 치수도 예: [ii1shwiwd3std](https://rotork.com/uploads/documents-engineering-versions/52513/1/ii1shwiwd3std-1_2d_.pdf), [ii1thwiwd3std](https://rotork.com/uploads/documents-engineering-versions/52603/1/ii1thwiwd3std-1_2d_.pdf) | |
| [Rotork IQ3 Pro 3D 모델](https://rotork.com/ZH/products-and-services/electric-actuators/iq3-pro-range/iq3-pro-resources/iq3-pro-range-3d-models) | 외곽 envelope CAD — 3D 비교 검증용 |

## Butterfly

| 출처 | 비고 |
|---|---|
| API 609 — [API 발췌](https://www.api.org/~/media/files/publications/whats%20new/609_e8%20pa.pdf) | wafer/lug/double-flanged 면간거리 |
| [Keystone Series 60 데이터시트](https://www.emerson.com/documents/automation/data-sheets-series-60-resilient-seated-butterfly-valve-discontinued-keystone-en-en-6634662.pdf) | wafer·lug 치수표 (mm/inch) |
| [Bray Triple Offset 기술 매뉴얼](https://catalog.jamiesonequipment.com/Asset/Bray%20Triple%20Offset%20Butterfly%20Valves%20Technical%20Manual%20JEC.pdf) | 기어 조작기 포함 전체 치수 |
| [Crane FLOWSEAL 사양서](https://www.cooneybrothers.com/userfiles/ad/documents/Crane_ChemPharma_021DA22DRTGHOJ_Specification_Sheet.pdf) | 등급별 wafer/lug |

## Ball

| 출처 | 비고 |
|---|---|
| ASME B16.10 ball (위 공통) | short/long pattern 구분 주의 |
| Trunnion ball GA 도면 | 검색으로 찾지 못함 — 벤더 Certified Drawing 요청 |

## PSV

| 출처 | 비고 |
|---|---|
| API 526 — [표준 정보](https://shop.standards.ie/en-ie/standards/api-526-2017-96976_saig_api_api_203145/) | 오리피스(D~T)별 입·출구 사이즈와 중심-면 거리 |
| [LESER Type 526 데이터시트](https://www.unitecd.com/ecatalog-files/leser-5262-6594-api-series-data-sheet-2.pdf) | 치수 a, b, H max. 플랜지가 B16.5보다 두꺼울 수 있음 |
| [Emerson Birkett 기술자료](https://d1-live.emerson.com/documents/automation/data-sheets-safety-relief-valves-technical-data-birkett-en-en-5198004.pdf) | API 526 치수 준수 |
| [Valve IT ANSI PSV](https://www.valveit.com/wp-content/uploads/2023/09/VIT-SFST-Ansi-Pressure-Safety-Valves-ENGLISH.pdf) | CL150 노즐형 치수 예 |

PSV의 `cti`·`cto`는 아직 표가 없어 **추정값**입니다. API 526 표를 확보하면 `refdata.js`에 오리피스별 표를 추가하세요.

## System Cabinet

| 출처 | 비고 |
|---|---|
| [Rittal TS 8808.500 (800×2000×800)](https://www.rittal.com/pdf-creator/variant/us-en/8808500) | 마운팅 플레이트 699×1896 |
| [Rittal TS 8808.750 (EMC)](https://www.rittal.com/pdf-creator/variant/ca-en/8808750) | |
| [Rittal TS 8806.580 (800×2000×600)](https://www.rittal.com/pdf-creator/variant/ca-en/8806580) | |

플린스 높이(100/200)는 별도 부품이라 사양서에 없습니다. 도면의 base frame 표기를 따르세요.

## Instrument Hook-up

| 출처 | 비고 |
|---|---|
| [Hook-up 도면 읽는 법 (Automation Forum)](https://automationforum.co/?p=20997) | 2" pipe stand, 스팀 condensate pot 예 |
| [Pressure transmitter 설치 팁](https://instrumentationtools.com/pressure-transmitters-installation-tips) | 가스: 탭 쪽 하향, 액체: 계기 쪽 하향 |
| [Control.com — 매니폴드](https://control.com/textbook/continuous-pressure-measurement/pressure-sensor-accessories/) | 2/3/5 밸브 매니폴드 동작 |
| [Rosemount 2088 2D 도면](https://s1-live.emerson.com/documents/automation/type-1-drawing-rosemount-2088-absolute-gage-pressure-transmitter-2d-pdf-en-73862.pdf) · [Rosemount 4088 2D](https://d1-live.emerson.com/documents/automation/type-1-drawing-rosemount-4088-in-line-pressure-transmitter-2d-pdf-en-78554.pdf) | 트랜스미터 외곽 |
| [Yokogawa EJA IM](https://web-material3.yokogawa.com/IM01C25C01-01EN_012.pdf) · [ABB 266 매뉴얼](https://library.e.abb.com/public/6e899e08c167764bc1257b0c0054738d/OI_266HART-EN-E-03_2011.pdf) | 임펄스 배관 연결 예 |
| [Rosemount Hook-ups 카탈로그](https://issuu.com/lupposrv/docs/hookups) | 표준 훅업 모음 |

현장 훅업은 프로젝트 표준(STD-xxx) 도면이 우선입니다. 그 도면을 이 툴에 넣으면 됩니다.

## 부품 명칭·기능 근거 (anatomy 설명용)

엔진(`src/anatomy.js`)의 부품 이름·기능 설명·통상 재질은 아래 공개 자료와 엔지니어링 지식으로 썼습니다.
원문 PDF 는 이 환경에서 받지 못했으므로 문구는 직접 썼고, 벤더별 명칭과 다를 수 있습니다.

| 품목 | 출처 |
|---|---|
| Control valve (body, bonnet, cage, plug, seat ring, packing, yoke, diaphragm actuator, spring) | [Globe valve — Wikipedia (Fisher Control Valve Handbook 링크)](https://en.wikipedia.org/wiki/Globe_valve) · [Control.com — sliding stem valve 분해](https://control.com/textbook/disassembly-of-a-sliding-stem-control-valve/) · [Control.com — sliding stem valves](https://control.com/textbook/control-valves/sliding-stem-valves/) · [Automation Forum — basic parts of control valves](https://automationforum.co/?p=1595) · [Fisher CAV4 manual](https://d1-live.emerson.com/documents/automation/instruction-manual-fisher-cav4-control-valve-en-8640910.pdf) · [Valtek Mark One](https://alphagroup.co.th/wp-content/uploads/2018/09/Control-valve-_Mark-One.pdf) |
| PSV (nozzle, adjusting ring, disc, disc holder, guide, spindle, spring washers, adjusting screw, bonnet, cap) | [Baker Hughes — PRV Basics (Valve Magazine)](https://dam.bakerhughes.com/m/297f2f644411c808/original/PRV-Basics-1-Valve-Magazine-2023-Fall-Issue.pdf) · ASME PTC 25 용어 · 미국 특허 [8607818](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8607818) |
| Gate (API 600: body, bonnet, wedge, seat rings, stem, gland, yoke) | [Project Materials — gate valve](https://blog.projectmaterials.com/valves/gate-valve) · [IOGP S-611 (API 600 보충)](https://www.iogp.org/bookstore/wp-content/uploads/sites/2/2023/03/Supplementary-Reqs-to-API-600-Steel-Gate-Valves-and-to-API-603-CRA-Gate-Valves-S-611v19-05.pdf) · [Bonney Forge 6" gate 2D sales drawing](https://cad.bonneyforge.com/Asset/8_-6-11-RF-WCB-GATE-LE_2D-Sales-Drawing.pdf) |
| MOV (motor, worm gear, handwheel, declutch, thrust base, drive bush, torque switch, terminal compartment) | [Rotork 사양서 PUB002-138](https://www.rotork.com/uploads/documents-versions/44326/1/pub002-138-00-0119.pdf) · [Bettis XTE3000 데이터시트](https://emerson.com/documents/automation/data-sheet-bettis-xte3000-en-en-6002142.pdf) · [InstrumentationTools — electric actuator parts](https://instrumentationtools.com/electric-motor-actuator-parts) |

## 사용자가 준 참고 링크

| 링크 | 반영 |
|---|---|
| [thebuggeddev/anatomy](https://github.com/thebuggeddev/anatomy) | 클론해서 구조 확인. 핫스팟 점 + 콜아웃 카드 + 부품 설명 데이터 구조(id·위치·라벨·설명), 줌·단면 상호작용을 참고 (코드 복사 없음) |
| [PyTorch KR — Image Blaster 3D](https://discuss.pytorch.kr/t/image-blaster-3d-claude/11500) | 이 환경에서 접속 불가. 검색으로 확인: World Labs Marble + fal Hunyuan3D 유료 API 로 이미지→메쉬. 치수 정확도가 없어 채택하지 않음 |
| [Scribd — Control Valve General Arrangement Drawings](https://www.scribd.com/document/799983491/Control-Valve-General-Arrangement-Drawings) | 이 환경에서 접속 불가. 내용 미확인 — GA 도면의 Parts list(풍선 번호·부품명·재질)를 읽어 3D 부품에 연결하는 기능으로 대응 |
