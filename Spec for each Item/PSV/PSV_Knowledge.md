# PSV Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: Safety Valve, Relief Valve, Safety Relief Valve는 어떻게 다른가요?
A: 일반적으로 Safety Valve는 설정압에서 한 번에 확 열리는(Pop) 밸브로 기체·증기용이고, Relief Valve는 과압에 비례해 서서히 열리는 액체용입니다. Safety Relief Valve는 유체와 조건에 따라 두 거동을 모두 보일 수 있습니다(출처 기준). ISO 4126처럼 용도와 상관없이 Safety Valve라는 용어만 쓰는 표준도 있어 프로젝트 용어 정의를 확인하세요(초안, 담당자 확인 필수).
키워드: PSV, safety valve, relief valve, safety relief valve, SRV, PRV, pop action, 안전밸브
부품: disc, nozzle, spring
출처: [Safety valve vs relief valve - Project Materials](https://blog.projectmaterials.com/quick-answers/valves/safety-valve-vs-relief-valve/)

### Q: Conventional, Balanced Bellows, Pilot-operated PSV는 언제 각각 쓰나요?
A: 핵심 기준은 배압(Back pressure)입니다. Conventional은 배압 영향을 그대로 받아 Built-up 배압이 일반적으로 설정압의 10% 이하일 때 씁니다(출처 기준). Balanced Bellows는 벨로즈로 Disc를 배압에서 보호하고, Pilot-operated는 배압 영향이 가장 적어 더 높은 배압에 쓰입니다. 허용 배압 한계 수치는 자료마다 달라 제조사 데이터와 API 520 원문으로 확인해야 합니다(초안, 담당자 확인 필수).
키워드: conventional PSV, balanced bellows, pilot operated relief valve, POPRV, back pressure, 배압
부품: disc, bonnet, spring
출처: [Conventional vs balanced bellows relief - Project Materials](https://blog.projectmaterials.com/quick-answers/valves/conventional-vs-balanced-bellows-relief/)

### Q: Superimposed 배압과 Built-up 배압은 무엇이 다른가요?
A: Superimposed 배압은 밸브가 열리기 전부터 출구에 걸려 있는 압력(예: Flare header 압력)이고, Built-up 배압은 밸브가 열려 흐르면서 출구 배관 저항으로 생기는 압력입니다. Conventional 밸브에서는 Superimposed 배압이 열림 압력(설정압)에 영향을 주고, 전체 배압은 Blowdown·재착좌 압력에 영향을 줍니다(출처 기준). 둘을 구분해 Datasheet에 따로 적어야 합니다(초안, 담당자 확인 필수).
키워드: superimposed back pressure, built-up back pressure, constant, variable, total back pressure, flare header
부품: disc, bonnet
출처: [Types of pressure relief valves - EnggCyclopedia](https://enggcyclopedia.com/2011/06/type-pressure-relief-valves)

### Q: Balanced Bellows PSV의 Bonnet Vent는 왜 막으면 안 되나요?
A: 벨로즈 안쪽은 대기압이어야 배압 보상이 되므로 Bonnet은 대기로 Vent됩니다. 벨로즈가 파손되면 밸브가 Conventional처럼 동작하게 되고, Vent로 유체가 새어 나와 파손을 알 수 있습니다(출처 기준). Vent를 막거나 배관으로 잘못 연결하면 보상 기능이 사라지므로 Vent 처리 방법(안전 위치로 배출)을 검토하세요(초안, 담당자 확인 필수).
키워드: bonnet vent, bellows rupture, balanced bellows, vent piping, 벨로즈
부품: bonnet, disc
출처: [Conventional or balanced bellows - eng-tips](https://www.eng-tips.com/threads/conventional-or-balanced-bellows.163111/)

### Q: Pilot-operated PSV의 Pop과 Modulating 동작 차이는?
A: Pop형은 메인 밸브가 스로틀링 없이 완전히 열려, 저온·냉매 서비스에서 결빙을 줄이는 데 유리하다고 소개됩니다. Modulating형은 필요한 만큼만 열어 방출 손실과 배출량을 줄입니다(Anderson Greenwood 자료 기준). 단점으로 Pilot 배관이 수화물·얼음·왁스 등으로 막힐 수 있어, 오염 서비스에는 필터나 다른 형식을 검토해야 합니다(초안, 담당자 확인 필수).
키워드: pilot operated, pop action, modulating, POPRV, pilot filter, hydrate, Anderson Greenwood
부품: disc, body
출처: [Anderson Greenwood Series 200/400/500/700/800 POPRV - Emerson](https://www.emerson.com/en/final-control/products/anderson-greenwood-hpp-series-200-400-500-700-800)

### Q: Pilot PSV에서 Backflow Preventer는 왜 필요한가요?
A: 배압이 입구 압력보다 커지는 경우 메인 밸브가 역으로 열리는 것을 막기 위해 Backflow preventer를 둡니다. 일부 제조사(Taylor Valve)는 이를 표준 사양으로 제시하지만, 다른 제조사 모델은 옵션일 수 있어 확인이 필요합니다(출처 기준). Flare header 공유 계통이면 역류 가능성을 공정 담당과 검토하세요(초안, 담당자 확인 필수).
키워드: backflow preventer, pilot valve, reverse flow, flare header, back pressure
부품: disc, body
출처: [9300 Series Pilot Operated Relief Valve - Taylor Valve](https://taylorvalve.com/wp-content/uploads/2025/02/9300SeriesWEB.pdf)

### Q: PVRV는 일반 PSV와 무엇이 다른가요?
A: PVRV는 저장탱크용으로, 압력이 오르면 증기를 내보내고 진공이 생기면 공기를 들여 탱크 좌굴·파손을 막습니다. 저설정압용은 무게(Weight-loaded)식, 높은 압력은 Spring식이 있습니다(제조사 자료 기준). 호흡(Breathing) 용량은 API 2000/ISO 28300 기준으로 산정하며, 화재 시 용량 산정 기준은 탱크와 용기에 따라 다르다는 지적이 있어 확인이 필요합니다(초안, 담당자 확인 필수).
키워드: PVRV, pressure vacuum relief valve, breather valve, API 2000, ISO 28300, storage tank, vacuum
부품: disc, body
출처: [Pressure vacuum relief valve - DirectIndustry (Hyperr Valves)](https://www.directindustry.com/prod/hyper-valves/product-204729-2849545.html)

## 설정압·과압 정의
### Q: Set Pressure, Overpressure, Accumulation, Blowdown 정의를 정리해 주세요.
A: Set pressure는 밸브가 열리기 시작하는 압력, Overpressure는 방출 중 설정압 위로 오르는 압력 상승분, Accumulation은 MAWP(설계압) 기준으로 허용되는 압력 상승분, Blowdown은 열림과 재착좌 압력의 차이입니다(출처 기준). Overpressure는 설정압 기준, Accumulation은 MAWP 기준이라는 점이 자주 혼동됩니다(초안, 담당자 확인 필수).
키워드: set pressure, overpressure, accumulation, blowdown, MAWP, reseat pressure, 설정압, 축적압력
부품: spring, disc
출처: [PRD Types, Construction and Operating Principles - Open Exam Prep](https://open-exam-prep.com/study-guides/api-510/pressure-relieving-devices-api-576/prd-types-and-construction)

### Q: 허용 Accumulation 10%, 16%, 21%는 어떤 경우인가요?
A: 일반적으로 단일 밸브 비화재는 MAWP의 10%, 복수 밸브는 16%, 화재(Fire) 케이스는 21%까지 Accumulation을 허용한다고 소개됩니다(출처 기준). 화재 케이스 설정압 배치(주 밸브 MAWP 이하, 추가 화재용 밸브 상향 설정 등)는 자료마다 설명이 달라 ASME Section VIII·API 520 원문 대조가 필요합니다. PED 적용 시 한계가 다를 수 있습니다(초안, 담당자 확인 필수).
키워드: accumulation, 10%, 16%, 21%, fire case, multiple valves, MAWP, ASME Section VIII, PED
부품: spring
출처: [Fire case accumulation discussion - eng-tips](https://www.eng-tips.com/viewthread.cfm?qid=213081)

### Q: CDTP(Cold Differential Test Pressure)는 어떻게 정하나요?
A: Conventional 밸브는 (설정압 − 일정 Superimposed 배압) × 온도 보정계수로 CDTP를 구합니다. Bellows·Pilot형은 구조상 배압이 보상되므로 배압을 빼지 않습니다(출처 기준). National Board 예시는 500 psig 설정, 25 psig 배압, 온도계수 1.013으로 약 481 psig를 제시합니다. 온도 보정계수는 제조사·모델별이므로 Vendor 자료를 따릅니다(초안, 담당자 확인 필수).
키워드: CDTP, cold differential test pressure, temperature correction, set pressure, back pressure, nameplate
부품: spring, cap
출처: [Cold differential test pressure - National Board](https://www.nationalboard.org/Index.aspx?pageID=379)

## 설계·사이징
### Q: PSV Orifice Size(D~T)는 어떻게 고르나요?
A: API 520 식으로 필요 유효면적(Effective area)을 계산한 뒤, 그 값 이상인 가장 작은 API 526 Orifice 문자를 고릅니다(출처 기준). 예를 들어 일반적으로 D 0.110, E 0.196, F 0.307, G 0.503, H 0.785, J 1.287, K 1.838 in²로 소개됩니다(Neutrium 등 출처 기준). 이 유효면적은 API 520 식과 함께 쓸 때만 의미가 있으며, 나머지 문자 값은 원문으로 확인하세요(초안, 담당자 확인 필수).
키워드: orifice, API 526, API 520, effective area, D E F G H J K L M N P Q R T, 오리피스
부품: nozzle, body
출처: [Relief valve orifice area to API RP 526 - Neutrium](https://neutrium.net/articles/equipment/relief-valve-orifice-area-to-api-rp-526/)

### Q: Effective Area와 Actual Area는 왜 다르나요?
A: API 유효면적은 모든 제조사가 같은 표준값이고, 실제 Nozzle 면적과 인증 방출계수(Kd)는 제조사마다 다릅니다(출처 기준). 그래서 API 526 문자로 1차 선정하고, 최종 용량은 제조사 실제 면적과 ASME 인증 계수로 다시 확인해야 합니다. 두 체계를 섞어 계산하면 과소·과대 선정이 생길 수 있습니다(초안, 담당자 확인 필수).
키워드: effective area, actual area, ASME certified, Kd, discharge coefficient, API vs ASME area
부품: nozzle
출처: [Actual orifice areas for different manufacturers - Cheresources](https://www.cheresources.com/invision/blog/4/entry-550-actual-orifice-areas-for-different-relief-valve-manufacturers-based-on-api-526-orifice-designations/)

### Q: 사이징에 들어가는 Kb, Kw, Kv 보정계수는 무엇인가요?
A: Kb는 Conventional·Bellows 밸브의 기체 서비스 배압 보정, Kw는 Balanced Bellows 밸브의 액체 서비스 배압 보정, Kv는 액체 점도(Reynolds 수) 보정 계수입니다(출처 기준). 대기 방출이면 Kb=1.0을 쓴다는 Crosby 예시가 있습니다. Crosby는 특정 조건에서 공개 Kb가 실제보다 낙관적일 수 있다는 Bulletin을 냈으므로 최신 제조사 자료를 써야 합니다(초안, 담당자 확인 필수).
키워드: Kb, Kw, Kv, Kd, back pressure correction, viscosity correction, Crosby, TP-V300
부품: nozzle, bonnet
출처: [Crosby J-Series Product Service Bulletin - Emerson](https://emerson.com/documents/automation/crosby-j-series-product-service-bulletin-en-5888256.pdf)

### Q: API 521은 어떤 Relief Scenario를 검토하라고 하나요?
A: API 521은 화재(Fire), Blocked outlet, Tube rupture, 제어 계통 고장, 열팽창 등 과압 원인을 검토하고 가장 큰 방출량을 사이징 기준으로 삼는 지침입니다. 예를 들어 Blocked outlet은 계기 고장 같은 원인에서 생길 수 있고, Tube rupture는 고압측이 저압측 설계압을 넘을 때 검토 대상이 됩니다(출처 기준). Scenario 선정과 방출량은 공정 담당이 결정합니다(초안, 담당자 확인 필수).
키워드: API 521, relief scenario, fire case, blocked outlet, tube rupture, thermal expansion, governing case
부품: body
출처: [Overpressure scenarios overview - SlideShare](https://es.slideshare.net/RajivNatkar/overpressure-scenarios-overview-final)

### Q: 화재(Fire) 케이스 Wetted Area는 어떻게 잡나요?
A: 일반적으로 Pool fire가 가능한 바닥면에서 25 ft(약 7.6 m) 높이 이내의 젖은 표면적만 포함하는 관행이 소개됩니다(출처 기준). 열입력 상관식(예: Φ = 21,000·A^0.82, 미국 단위)도 자료에 인용되지만 조건(배수·소화 설비)에 따라 계수가 달라 원문 확인이 필요합니다. 계산은 공정 담당 소관이며 계측 측은 결과 Datasheet를 대조합니다(초안, 담당자 확인 필수).
키워드: fire case, wetted area, 25 ft, heat input, pool fire, API 521, 화재케이스
부품: body
출처: [Relief Study Guidelines - Scribd](https://www.scribd.com/document/319518607/Relief-Study-Guidelines)

### Q: 2상(Two-phase) 유동 PSV 사이징은 어떻게 하나요?
A: API 520에는 Omega method 등 2상 사이징 방법이 부록으로 수록돼 있다고 소개되지만, 판마다 부록 위치가 다르게 인용됩니다(출처 기준). Omega method는 결과 편차가 크고 비선형 거동에서 과소 사이징될 수 있다는 비판도 있습니다. 2상 케이스는 공정 전문가 검토가 필수입니다(초안, 담당자 확인 필수).
키워드: two-phase, omega method, flashing, HDI, API 520 Annex, 2상유동
부품: nozzle
출처: [Sizing pressure relief valves for two phases - Chemical Engineering](https://chemengonline.com/sizing-pressure-relief-valves-two-phases)

## Interface·설치
### Q: PSV 입구 압력손실 3% 규칙은 무엇인가요?
A: API 520 Part II는 보호 대상 설비에서 PSV 입구까지의 비회복 압력손실을 설정압의 약 3% 이하로 제한하라고 권고합니다(출처 기준). 목적은 밸브가 열렸다 닫혔다를 반복하는 Chattering을 막는 것입니다. 엔지니어링 해석을 수행하면 3%를 넘을 수 있다는 해석도 있어, 적용 기준은 프로젝트 Spec으로 확인하세요(초안, 담당자 확인 필수).
키워드: inlet pressure loss, 3% rule, API 520 Part II, chattering, inlet piping, 입구손실
부품: process-conn, disc
출처: [API 3% guideline - Cheresources](https://www.cheresources.com/invision/topic/1144-api-3-guideline)

### Q: Chattering은 왜 생기고 어떻게 막나요?
A: Chattering은 밸브가 빠르게 개폐를 반복해 Seat·Disc를 두들기는 현상입니다. 입구 손실 과다, Built-up 배압 과다, 과대 사이징(필요 유량 대비 너무 큰 Orifice)이 대표 원인으로 거론됩니다. 액체 서비스에서 Pop 동작도 Chattering을 유발할 수 있습니다(출처 기준). 대책은 원인별로 다르니 공정·배관 담당과 함께 검토하세요(초안, 담당자 확인 필수).
키워드: chattering, chatter, valve instability, oversizing, built-up back pressure, inlet loss
부품: disc, nozzle, spring
출처: [Vibration and chattering of conventional safety relief valve - CETIM](https://www.cetim.fr/mecatheque/content/download/32436/file/Vibration-and-chattering-of-conventional-safety-relief-valve-under-built-up-back-pressure.pdf)

### Q: PSV 입·출구 Isolation Valve는 어떻게 관리하나요?
A: 운전 중인 PSV의 Isolation valve는 보통 CSO(Car Seal Open)로 관리하고, 예비 PSV는 정비 이유로 CSC(Car Seal Closed)로 두는 사례가 있습니다(출처 기준). 예비 PSV로 전환할 때 항상 방출 경로가 확보되도록 Interlock이나 Change-over valve를 씁니다. Car seal은 관리적 통제이므로 절차 준수가 전제입니다(초안, 담당자 확인 필수).
키워드: isolation valve, CSO, CSC, car seal, spare PSV, interlock, change-over valve
부품: process-conn
출처: [Open path vs PSV - eng-tips](https://eng-tips.com/threads/open-path-vs-psv.53966)

### Q: PSV 상류에 Rupture Disc를 같이 쓸 때 주의점은?
A: Disc와 PSV 사이 공간은 핀홀 누설이나 Disc 조기 파열을 감지하도록 압력계·압력 전송기로 감시하는 것이 일반적입니다(출처 기준). Rupture Disc는 격리 장치로 취급하면 안 된다는 지적도 있습니다. 조합 시 용량 보정 등 Code 요구는 2차 자료로는 확인되지 않아 미확인이며 ASME 원문 확인이 필요합니다(초안, 담당자 확인 필수).
키워드: rupture disc, rupture disk, combination, telltale, pressure gauge, PI, PT, 파열판
부품: process-conn
출처: [Rupture Disc and PSV Combination - Industrial Monitor Direct](https://industrialmonitordirect.com/blogs/knowledgebase/rupture-disc-and-psv-combination-set-pressure-requirements)

### Q: Lifting Lever는 언제 필요한가요?
A: ASME Section VIII는 공기, 일정 온도 이상의 온수, 증기 서비스 PSV에 Lifting device를 요구하는 것으로 포럼에서 인용됩니다(출처 기준). UV Stamp 요구가 있을 때 적용되며, Code Case로 생략하려면 관할 기관 허가가 필요하다는 의견이 있습니다. 질소 같은 비독성 가스는 선택 사항이라는 의견도 있으니 프로젝트 Spec으로 확인하세요(초안, 담당자 확인 필수).
키워드: lifting lever, lifting device, ASME Section VIII, UV stamp, steam, air, hot water, Code Case 2203
부품: lever, cap
출처: [Why does ASME VIII require lifting levers - eng-tips](https://eng-tips.com/threads/why-does-asme-viii-require-lifting-levers.479606)

## 시험·검사
### Q: API 527 Seat Tightness 시험은 어떻게 하나요?
A: Pop 시험 후 입구 압력을 설정압의 90%로 유지하고 출구에 연결한 튜브에서 나오는 기포 수를 셉니다(출처 기준). Metal seat는 표준 표의 허용 기포 수 이하, Soft seat는 1분간 누설이 없어야 한다고 소개됩니다. 허용치는 Orifice 크기·설정압별로 다르니 API 527 원문 표를 확인하세요(초안, 담당자 확인 필수).
키워드: API 527, seat tightness, seat leakage test, bubbles per minute, 90% set pressure, metal seat, soft seat
부품: disc, nozzle
출처: [What is PRV Seat leakage (tightness) test? - A Marine Blog](https://amarineblog.com/2019/12/18/what-is-prv-seat-leakage-tightness-test/)

### Q: PSV 검사·시험 주기는 어떻게 정하나요?
A: API 576은 해당 서비스에서 밸브가 보인 성능에 따라 주기를 정하라는 입장이며, 시험 주기 요구는 API 510이 다룬다고 소개됩니다(출처 기준). 부식·오염이 심한 서비스는 주기를 단축합니다. As-received(입고 상태) Pop 시험 결과가 주기 판단의 핵심 데이터이므로 반드시 기록하세요(초안, 담당자 확인 필수).
키워드: inspection interval, API 576, API 510, as-received test, bench test, RBI
부품: disc, spring, nozzle
출처: [PRD Inspection Intervals, Records - Open Exam Prep](https://open-exam-prep.com/study-guides/api-510/pressure-relieving-devices-api-576/prd-intervals-records-rupture-disks)

### Q: Bench Test와 In-situ Test 차이는?
A: Bench test는 밸브를 떼어 정비실에서 분해·검사·재설정하고 API 527 누설 시험까지 할 수 있습니다. In-situ test는 설치된 상태에서 설정압을 확인해 정지·분리 부담이 적지만 Seat 래핑이나 내부 청소는 할 수 없습니다(출처 기준). 어떤 방법을 허용할지는 사업주 검사 기준에 따릅니다(초안, 담당자 확인 필수).
키워드: bench test, in-situ test, online set pressure test, overhaul, seat lapping
부품: disc, nozzle, spring
출처: [PSV testing requirements, procedure and standards - EPCLand](https://epcland.com/psv-testing-requirements-procedure-standards/)

## MR 작성·Datasheet
### Q: PSV Datasheet / MR에 꼭 넣어야 할 항목은?
A: Tag, 보호 대상 설비 MAWP, 설정압, 허용 Overpressure, Governing scenario, 필요 방출량과 유체 물성, Superimposed·Built-up 배압, 형식(Conventional/Bellows/Pilot), 필요·선정 Orifice, 입·출구 Size·Rating, Body·Trim·Spring 재질, Sour service(NACE) 여부가 기본입니다(프로젝트 Spec Sheet 예시 기준). Lever·Cap 형식, 시험 요구(API 527), CDTP도 넣으세요(초안, 담당자 확인 필수).
키워드: PSV datasheet, MR, set pressure, relieving rate, back pressure, orifice, NACE MR0175, ISO 15156
부품: body, nozzle, disc, spring, bonnet, cap, lever, process-conn
출처: [PSV Spec Sheet example - OGDCL tender](https://ogdcl.com/sites/default/files/tender-file/CL-5266-02%20%28Spec%20Sheet%29.pdf)

### Q: PSV 입구와 출구 Flange Rating이 다른 게 정상인가요?
A: 네, 출구는 보통 입구보다 낮은 Rating을 갖는 경우가 많다는 실무 의견이 있으며, 입·출구 Size와 Rating 조합은 API 526 표가 주요 참조입니다(출처 기준). 다만 출구 Rating은 배압과 출구 온도를 견뎌야 하므로 Built-up 배압 계산 결과와 함께 확인하세요(초안, 담당자 확인 필수).
키워드: inlet flange, outlet flange, flange rating, API 526, outlet rating, back pressure
부품: process-conn, body
출처: [PSV flange rating discussion - eng-tips](https://www.eng-tips.com/viewthread.cfm?qid=396600)

### Q: PSV Vendor 문서로 무엇을 받아야 하나요?
A: 사이징 계산서(사용 Kd·Kb·Kw·Kv 명시), GA 도면, 재질 증명서, 설정압·Seat 누설 시험 성적서(API 527), CDTP 근거, ASME UV/NB 인증 관련 자료가 핵심입니다. Pilot형은 Pilot 계통도와 필터·Backflow preventer 사양을 추가로 받습니다. 문서 목록 최종본은 프로젝트 VDRL을 따릅니다(초안, 담당자 확인 필수).
키워드: vendor document, sizing calculation, test certificate, API 527 report, UV stamp, VDRL
부품: body, nozzle, spring
출처: [Safety & Pressure Relief Valves: Types, Sizing & Standards - Project Materials](https://blog.projectmaterials.com/valves/safety-valve-asme-api/)

## 자주 하는 실수
### Q: PSV 사양 검토에서 흔한 실수는?
A: 첫째, 배압 종류(Superimposed/Built-up)를 구분하지 않고 Conventional을 선정하는 것입니다. 둘째, Set pressure와 CDTP를 혼동해 Nameplate에 잘못 반영하는 것입니다. 셋째, API 유효면적과 제조사 실제 면적·Kd를 섞어 계산하는 것입니다. 넷째, 입구 손실 3% 검토를 생략하는 것입니다(각 출처 기준, 초안, 담당자 확인 필수).
키워드: common mistakes, back pressure, CDTP, effective area, inlet loss, 실수
부품: disc, nozzle, process-conn
출처: [How to Size a Relief Valve: API 520 - Project Materials](https://blog.projectmaterials.com/quick-answers/pipes/how-to-size-relief-valve-api-520/)
