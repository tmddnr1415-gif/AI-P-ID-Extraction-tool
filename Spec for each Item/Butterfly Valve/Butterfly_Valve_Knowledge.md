# Butterfly Valve Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: Concentric, Double Offset, Triple Offset Butterfly Valve는 뭐가 다른가요?
A: Concentric(Zero offset)은 Disc를 고무 등 Resilient Seat에 눌러 씰링하며 회전 내내 Seat와 접촉해 마찰이 큽니다. Double offset은 Shaft를 Disc 뒤쪽과 배관 중심에서 비켜 놓아 열릴 때 Disc가 Seat에서 일찍 떨어져 마모가 줄어듭니다. Triple offset은 여기에 원뿔(Cone) 축 Offset을 더해 회전 중 Seat와 마찰이 없고 보통 Metal-to-metal로 씰링합니다(출처 기준).
키워드: concentric, zero offset, double offset, high performance butterfly valve, HPBV, triple offset, TOV, TOBV
부품: disc, shaft, body
출처: [The Ultimate Guide to Butterfly Valve Selection - Bray](https://www.bray.com/valves-actuators-controls/butterfly-valves/the-ultimate-guide-to-butterfly-valve-selection)

### Q: Triple Offset이면 무조건 Zero Leakage인가요?
A: 아닙니다. Triple offset Metal seat가 Zero leakage로 가장 많이 홍보되긴 하지만, "Zero leakage"는 제조사·시험 표준(API 598, ISO 5208 등)마다 정의가 다릅니다. 한 엔지니어링 글은 Triple offset과 Zero leakage를 같은 말로 보면 안 된다고 지적합니다. 반드시 해당 제품의 시험 표준과 인증서로 확인하세요.
키워드: zero leakage, triple offset, metal seat, bubble tight, API 598, ISO 5208, 누설
부품: disc, body
출처: [Triple-Offset Valve: Critical-Service, Not Default - Industrial Monitor Direct](https://industrialmonitordirect.com/blogs/knowledgebase/triple-offset-valve-critical-service-not-default)

### Q: 깨끗한 물 서비스에도 Triple Offset을 써야 하나요?
A: 꼭 그렇지 않습니다. 깨끗한 물 계통은 Concentric이나 Double offset으로도 필요한 누설 성능을 더 싼 값에 얻는 경우가 흔하다는 의견이 있습니다(출처 기준). Triple offset은 고온·고압·Metal seat 요구·Fire-safe 등 까다로운 서비스에 쓰는 것이 일반적입니다. 선정 근거는 프로젝트 Valve Spec으로 확인하세요.
키워드: valve selection, triple offset, cost, water service, critical service
부품: disc, body
출처: [Triple-Offset Valve: Critical-Service, Not Default - Industrial Monitor Direct](https://industrialmonitordirect.com/blogs/knowledgebase/triple-offset-valve-critical-service-not-default)

### Q: Butterfly Valve 작동 원리와 장단점은?
A: Butterfly는 Shaft에 붙은 원판(Disc)을 90° 회전시켜 여닫는 Quarter-turn 밸브입니다. 같은 구경 대비 가볍고 짧으며 대구경에서 경제적인 것이 장점입니다. 반면 Disc가 항상 유로에 남아 압력손실이 있고, 고차압 제어에서는 Cavitation·토크 불안정이 생길 수 있습니다(출처 기준).
키워드: butterfly valve basics, quarter turn, disc, large diameter, 버터플라이밸브
부품: disc, shaft, body
출처: [How It Works: Butterfly Valves - SLB](https://www.slb.com/zh-cn/resource-library/article/valve-insights/how-it-works-butterfly-valves)

### Q: Wafer, Lug, Double-flanged Body는 어떻게 다른가요?
A: API 609는 Double-flanged, Lug, Wafer 세 가지 Body 형식을 다룹니다. Wafer는 두 플랜지 사이에 끼워 볼트로 조이는 형식이고, Lug는 Body의 나사 구멍에 볼트를 체결해 한쪽 배관을 떼어도 밸브가 남을 수 있습니다. Double-flanged는 Long/Short pattern을 MR에 지정해야 합니다(API 609 구매 지침 기준).
키워드: wafer, lug, double flanged, long pattern, short pattern, API 609, body style
부품: body, process-conn
출처: [How to Order Butterfly Valves - Project Materials](https://blog.projectmaterials.com/how-to-order/butterfly-valves/)

## 표준
### Q: API 609 Category A와 Category B 차이는?
A: Category A는 제조사가 정한 상온 사용압력(CWP) 기준 밸브로 보통 Concentric 구조입니다. Category B는 ASME Class 압력-온도 정격을 갖고 Offset Seat를 가진 밸브입니다(API 609 기준). 공정 배관(ASME Class 지정)에는 보통 Category B를 쓰며, MR에 Category를 반드시 명시해야 합니다.
키워드: API 609, Category A, Category B, CWP, ASME class, pressure-temperature rating
부품: body
출처: [API 609 8th edition purchase info - API](https://www.api.org/~/media/files/publications/whats%20new/609_e8%20pa.pdf)

### Q: API 609 적용 Size 범위는 어떻게 되나요?
A: 판(Edition)에 따라 범위가 달라 자료마다 다르게 나옵니다. 한 목록은 Lug·Wafer Class 150~600을 NPS 3~24로, 다른 판은 더 넓게 제시합니다(출처 기준). 프로젝트가 지정한 API 609 판의 원문으로 확인해야 하며, 여기서는 미확인으로 둡니다.
키워드: API 609 size range, edition, NPS, Class 150, Class 300, Class 600
부품: body
출처: [API STD 609 - Standard Norge](https://online.standard.no/en/api-std-609)

### Q: Butterfly Valve 누설 시험은 어떤 표준으로 하나요?
A: 차단용은 API 598이나 ISO 5208/EN 12266-1, 제어용은 FCI 70-2 Class로 지정하는 경우가 많습니다. Metal seat Double offset은 "Bubble-tight", Triple offset은 "Zero leakage"로 표기되는 등 용어가 제조사마다 달라 표준과 Rate/Class로 명확히 써야 합니다(출처 기준). 구체 허용량은 표준 원문 확인이 필요합니다.
키워드: leakage test, API 598, ISO 5208, EN 12266-1, FCI 70-2, bubble tight, zero leakage
부품: disc, body
출처: [Butterfly Valve Leakage Standards - Industrial Monitor Direct](https://industrialmonitordirect.com/blogs/knowledgebase/butterfly-valve-leakage-standards-api-609-vs-api-598-vs-en-12266-1)

### Q: Fire-safe 요구가 있으면 어떤 Butterfly Valve를 고르나요?
A: Fire test는 API 607 등으로 하는 형식 시험이며 Soft seat Quarter-turn 밸브가 주된 대상입니다(출처 기준). Resilient seat Concentric은 화재 시 Seat가 손상되므로, Fire-safe 요구가 있으면 Fire-tested Double offset이나 Metal seat Triple offset을 검토합니다. 제3자 Fire test 인증서와 적용 범위를 확인하세요.
키워드: fire safe, API 607, fire test, metal seat, triple offset, 내화
부품: disc, body, shaft
출처: [API 607 vs API 6FA - Project Materials](https://blog.projectmaterials.com/quick-answers/epc/api-607-vs-api-6fa/)

### Q: Shaft 누설(Fugitive Emission) 요구는?
A: Quarter-turn 밸브는 API 641이나 ISO 15848-1로 Stem/Shaft 씰 형식 시험을 요구할 수 있습니다. API 641은 메탄 기준 100 ppm 한도로 소개되고, ISO 15848-1은 메탄 또는 헬륨으로 등급을 나눕니다(Valve Magazine 출처 기준). 프로젝트 요구 표준·등급은 미확인이므로 Spec 확인이 필요합니다.
키워드: fugitive emission, API 641, ISO 15848-1, shaft seal, packing
부품: shaft
출처: [Fugitive Emissions Standards for Valves - Valve Magazine](https://www.valvemagazine.com:443/articles/fugitive-emissions-standards-for-valves)

## 설계·사이징
### Q: Butterfly Control Valve는 몇 도까지 제어 범위로 쓰나요?
A: 일반 Disc는 약 60° 이상에서 Dynamic 토크가 급변하고 Cv 변화가 빨라 제어가 어려워집니다. 그래서 전통적으로 제어용은 행정을 60° 정도로 제한하며, Bray도 계산 Cv가 0~60° 범위에 들어오는 밸브를 고르라고 권합니다(출처 기준). Fishtail 같은 특수 Disc는 90°까지 제어가 가능하다고 소개됩니다.
키워드: butterfly control valve, 60 degree, throttling range, dynamic torque, fishtail disc, 개도범위
부품: disc, shaft, actuator
출처: [Navigating the World of Butterfly Valves - Emerson White Paper](https://www.emerson.com/is/content/emerson/en/final-control/flow-controls/documents/white-paper-navigating-the-world-of-butterfly-valves.pdf)

### Q: Butterfly Valve의 Dynamic Torque는 왜 문제가 되나요?
A: 유체가 Disc를 지나면서 Disc를 닫는 방향으로 미는 힘이 생기는데, 특정 개도(대략 50~75°)에서 토크 기울기가 급하게 변하거나 방향이 바뀝니다(특허 자료 기준). 이 때문에 위치 제어 오차가 커지고 Actuator가 흔들릴 수 있습니다. Actuator 사이징 때 Seating·Breakaway 토크뿐 아니라 Dynamic 토크 곡선을 제조사에서 받아야 합니다.
키워드: dynamic torque, hydrodynamic torque, torque reversal, butterfly actuator sizing
부품: disc, shaft, actuator
출처: [Butterfly valve having a split vane - US Patent 3934851](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/3934851)

### Q: Butterfly Valve에서 Cavitation은 어떻게 판단하나요?
A: 일반 Butterfly는 FL이 낮아(대표 예로 0.65, ISA 기사 기준) 압력회복이 커서 Globe보다 Cavitation이 쉽게 생깁니다. 보통 Cavitation 지수(Xfz 등)로 허용 차압을 제한하는 방식으로 판단합니다. 가장 정확한 방법은 해당 밸브 형식·Size의 실제 시험 데이터를 쓰는 것이라는 연구 결과가 있습니다.
키워드: cavitation, FL, Xfz, pressure recovery, butterfly cavitation limit, 캐비테이션
부품: disc, body
출처: [A fluidic phenomenon fighting cavitation in butterfly valves - ISA InTech](https://www.isa.org/intech-home/2016/november-december/departments/a-fluidic-phenomenon-fighting-cavitation-in-butter)

### Q: 고차압 Throttling에 Butterfly를 써도 되나요?
A: 고차압에서는 보통 30~80° 개도 범위에서만 Throttling하라는 실무 자료가 있습니다(EPCLand 출처 기준). 고유속에서는 Disc 뒤 난류로 Cavitation과 소음이 생길 수 있습니다. 차압이 크면 Globe나 특수 Trim 밸브로 바꾸거나 2단 감압을 검토하세요.
키워드: high pressure drop, throttling, butterfly limitations, 30-80 degree, turbulence
부품: disc
출처: [Butterfly Valve: 10 Essential Questions - EPCLand](https://blog.epcland.com/butterfly-valve-applications/)

### Q: Butterfly Valve Actuator 토크 사이징 순서는?
A: 제조사 데이터에서 Seating/Unseating(Breakaway) 토크, Dynamic 토크, Bearing 마찰 토크를 받아 최대 요구 토크를 구합니다. 여기에 프로젝트 Safety factor를 적용하고, Actuator의 최소 공급압(공압) 또는 전압(전동) 기준 출력과 비교합니다. Safety factor는 출처마다 20~25% 등으로 다르니 프로젝트 Spec 값을 쓰세요(Crossco 출처 기준).
키워드: actuator sizing, seating torque, unseating torque, dynamic torque, safety factor
부품: actuator, shaft, disc
출처: [How to Size Pneumatic Actuators - Crossco](https://www.crossco.com/resources/technical/how-to-size-pneumatic-actuators/)

### Q: Butterfly Control Valve의 유량 특성은?
A: Butterfly는 고유 특성이 대략 Equal percentage에 가깝지만 고개도 구간에서 Cv가 빠르게 증가합니다. 그래서 정밀 제어가 필요하면 Characterized disc나 Positioner의 특성 보정 기능을 쓰기도 합니다. 정확한 곡선은 제조사 Cv 표로 확인하세요(구체 수치 미확인).
키워드: flow characteristic, equal percentage, butterfly Cv curve, characterized disc
부품: disc, positioner
출처: [The Ultimate Guide to Butterfly Valve Selection - Bray](https://www.bray.com/valves-actuators-controls/butterfly-valves/the-ultimate-guide-to-butterfly-valve-selection)

## Triple Offset 특성
### Q: Triple Offset Valve의 "Preferred Direction"이란?
A: 비대칭 구조라서 선호 방향으로 설치하면 Actuator 토크가 없어도 밸브가 닫힌 상태로 기밀을 유지하고, 더 적은 토크로 기밀이 된다는 것이 Emerson Vanessa 자료의 설명입니다. 반대로 비선호 방향은 더 큰 Seating 토크가 필요할 수 있습니다. 양방향 Zero leakage를 주장하는 제품도 있으니, 설치 방향과 방향별 누설·토크 데이터를 받으세요.
키워드: preferred direction, triple offset, Vanessa, bidirectional, seating torque, 설치방향
부품: disc, body, actuator
출처: [Triple Offset Valve Technology - Emerson Vanessa](https://d1-live.emerson.com/en-ca/automation/brands/vanessa/triple-offset-valve)

### Q: Triple Offset은 왜 Torque Seated라고 하나요?
A: Triple offset은 기계적 간섭(Interference)이 아니라 외부에서 가한 토크로 Metal Seal Ring을 Seat에 눌러 기밀을 만듭니다(출처 기준). 반면 Concentric 등은 위치(Position)로 Seat 간섭을 만드는 방식입니다. 그래서 Triple offset은 Actuator 닫힘 끝단 토크와 Stop 설정이 기밀 성능을 좌우합니다.
키워드: torque seated, position seated, metal seal ring, laminated seal, triple offset
부품: disc, shaft, actuator
출처: [Triple Offset Valves 2.0 - Velan](https://www.velan.com/en/products/1/53?id=116)

### Q: Triple Offset을 Double Positive Isolation(DPI)에 쓸 수 있나요?
A: Emerson은 Triple offset 밸브를 Double positive isolation 용도로 적용하는 Bulletin을 냈습니다. 다만 격리 요건(정비 시 인원 보호 등)은 회사 Isolation 기준이 결정하므로 적용 가능 여부는 프로젝트 안전 기준으로 확인해야 합니다. 구체 조건은 미확인입니다.
키워드: double positive isolation, DPI, triple offset, isolation, maintenance isolation
부품: disc, body
출처: [Double Positive Isolation using Triple Offset Valves - Emerson Bulletin](https://emerson.com/documents/automation/bulletin-double-positive-isolation-application-using-triple-offset-valves-en-10746076.pdf)

## Actuator·Interface
### Q: Butterfly MOV(전동 Actuator)는 어떻게 구성하나요?
A: Quarter-turn 전동 Actuator를 직결하거나 다회전 Actuator에 Worm Gearbox를 붙입니다. Rotork 자료는 Gearbox 입·출력 플랜지가 ISO 5211을 따른다고 하며, Gearbox Stop bolt를 90°로 공장 설정한다고 언급합니다(출처 기준). Stall 토크가 정격보다 클 수 있으므로 Shaft 허용 토크와 비교하세요.
키워드: MOV, electric actuator, quarter turn, worm gearbox, ISO 5211, Rotork IQT, stop bolt
부품: actuator, shaft
출처: [Electric actuators - Process Online](https://www.processonline.com.au/content/unknown/product/electric-actuators-842978568)

### Q: MOV Torque Switch는 Butterfly에서 왜 중요하죠?
A: Rotork는 Torque switch를 출력 토크를 직접 측정해 설정값과 비교하는 1차 보호 장치로 설명합니다. Butterfly에서 Torque 설정이 너무 높으면 Shaft·Disc 연결부가 손상될 수 있고, 너무 낮으면 Triple offset 같은 Torque seated 밸브가 기밀을 못 냅니다. 닫힘 끝단을 Torque로 끝낼지 Limit로 끝낼지는 밸브 형식과 제조사 권고를 따르세요.
키워드: torque switch, limit switch, MOV protection, torque seating, position seating
부품: actuator, shaft
출처: [Rotork actuator publication PUB002-206](https://www.rotork.com/uploads/documents-versions/47220/1/pub002-206-00-0923.pdf)

### Q: Butterfly Control Valve의 Positioner 선정 시 유의점은?
A: Quarter-turn용 Positioner는 회전 각도를 피드백 받으므로 Linkage나 NAMUR 직결 방식, 백래시를 확인해야 합니다. Smart Positioner는 Valve signature로 마찰·Spring 설정을 진단할 수 있고, 특성 보정(Characterization) 기능으로 Butterfly 특성을 보완할 수 있습니다(SAMSON 자료 기준). 통신 방식과 방폭 등급을 MR에 적으세요.
키워드: positioner, rotary positioner, smart positioner, characterization, NAMUR, HART
부품: positioner, actuator
출처: [Positioner diagnostics document - SAMSON](https://norway.samsongroup.com/document/t83890en.pdf)

## 설치·사양 검토 유의사항
### Q: Disc가 배관과 간섭(Clearance)하는 문제는 어떻게 확인하나요?
A: Butterfly Disc는 열릴 때 Body 면 밖으로 튀어나오므로, 배관 내경이 작으면(두꺼운 Schedule, Lining, 주조 플랜지, Reducing 플랜지) Disc가 부딪힙니다. Bray 매뉴얼은 일반적으로 Class 150은 Sch 40, Class 300은 Sch 80 배관과 간섭이 없다고 안내합니다(출처 기준). 정확한 판단은 제조사 최소 배관 내경표나 Chord diameter와 실제 배관 내경을 비교하세요.
키워드: disc clearance, pipe ID, schedule, lined pipe, chord diameter, interference, 간섭
부품: disc, process-conn, body
출처: [Butterfly valves and chord diameter - Milwaukee Valve](https://www.milwaukeevalve.com/wp-content/uploads/01-19-23-butterfly-valves-and-chord-diameter.pdf)

### Q: Wafer/Lug 설치 시 주의할 점은?
A: Schedule 80 같은 두꺼운 배관에서는 밸브 중심을 잘 맞추지 않으면 개폐 시 Disc 가장자리가 손상될 수 있습니다(Crane 매뉴얼 기준). 설치 후 천천히 열어 Disc가 자유롭게 움직이는지 확인하라는 것이 제조사들의 공통 권고입니다. 고무 Seat 밸브는 별도 Gasket 사용 여부도 매뉴얼로 확인하세요.
키워드: installation, centering, wafer installation, lug, gasket, disc damage
부품: disc, body, process-conn
출처: [Center Line Butterfly Valve IOM - Crane](https://cranecpe.com/wp-content/uploads/13092_CPE-CENTER-LINE-IM-EN-LT-2020_11_16.pdf)

### Q: 배관 끝(Dead-end) 서비스에 Wafer를 써도 되나요?
A: Wafer는 양쪽 플랜지 사이에 끼워 볼트로 고정하므로 하류 배관을 떼면 밸브를 붙잡아 줄 것이 없습니다. 그래서 Dead-end나 정비 시 한쪽 분리가 필요하면 Lug나 Double-flanged를 고르는 것이 일반적입니다. Lug 밸브의 Dead-end 정격 압력은 제조사마다 다르니 미확인으로 두고 확인하세요.
키워드: dead end service, wafer, lug, end of line, double flanged
부품: body, process-conn
출처: [How to Order Butterfly Valves - Project Materials](https://blog.projectmaterials.com/how-to-order/butterfly-valves/)

## MR 작성·Vendor 문서
### Q: Butterfly Valve MR에 꼭 넣어야 할 항목은?
A: API 609 Category, Body 형식(Wafer/Lug/Double-flanged, Long/Short pattern), Offset 형식, Size·Class, Disc·Shaft·Seat 재질, 누설 표준과 등급, Fire-safe·Fugitive emission 요구가 기본입니다(API 609 구매 지침 기준). Actuator는 형식·Fail 위치·Stroke Time·공급압 또는 전원, 제어용이면 Positioner와 공정 조건·Cv 계산을 추가하세요. Triple offset이면 설치 방향 요구를 명시합니다.
키워드: MR, datasheet, API 609, body style, offset type, actuator, positioner, 필수항목
부품: body, disc, shaft, actuator, positioner
출처: [API 609 8th edition purchase info - API](https://www.api.org/~/media/files/publications/whats%20new/609_e8%20pa.pdf)

### Q: Butterfly Valve Vendor 문서로 무엇을 받아야 하나요?
A: GA 도면(Disc 돌출 치수·Chord diameter 포함), 토크 데이터(Seating·Dynamic)와 Actuator 사이징 계산서, Cv·특성 곡선, 누설·Fire test·Fugitive emission 인증서가 핵심입니다. 설치·운전 매뉴얼(IOM)에서 최소 배관 내경과 설치 방향을 확인하세요. 문서 목록 최종본은 프로젝트 VDRL을 따릅니다.
키워드: vendor document, GA drawing, torque data, Cv curve, IOM, certificate, VDRL
부품: disc, actuator, body
출처: [Butterfly valve IOM guide - API International](https://apiint.com/wp-content/uploads/2023/03/butterfly-valve-iom-guide.pdf)

## 자주 하는 실수
### Q: Butterfly 제어밸브 사양에서 흔한 실수는?
A: 첫째, 필요 Cv가 60° 이상 개도에서 나오도록 작은 밸브를 고르는 것입니다. 둘째, Actuator 사이징에 Dynamic 토크를 빠뜨리는 것입니다. 셋째, 낮은 FL을 무시해 Cavitation 검토를 생략하는 것입니다. 넷째, Lined pipe나 두꺼운 Schedule과의 Disc 간섭을 확인하지 않는 것입니다(각 출처 기준).
키워드: common mistakes, 60 degree, dynamic torque, cavitation, disc clearance, 실수
부품: disc, actuator, shaft
출처: [How to prevent cavitation in butterfly control valves - Automation.com](https://www.automation.com/article/how-to-prevent-cavitation-butterfly-control-valves)
