# Ball Valve Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: ESDV, SDV, BDV, XV는 다 Ball Valve인데 뭐가 다른가요?
A: 넷 다 On/Off 차단용 자동밸브지만 맡는 기능이 다릅니다. ESDV·SDV는 비상·공정 차단 시 닫히는 차단밸브이고, BDV는 비상 시 열려서 설비 내 가스를 Flare/Vent로 빼내는 감압용 밸브입니다. XV는 보통 일반 공정 On/Off(시퀀스, 전환) 용도로 안전 기능이 없는 경우가 많습니다. 태그 구분은 프로젝트마다 달라서 실제 정의는 프로젝트 Spec·C&E로 확인해야 합니다(초안, 담당자 확인 필수).
키워드: ESDV, SDV, BDV, XV, 차단밸브, 블로우다운, on-off valve, shutdown valve, emergency shutdown
부품: ball, actuator
출처: [Shutdown valve - Wikipedia](https://en.wikipedia.org/wiki/Shutdown_valve)

### Q: Floating Ball과 Trunnion Mounted Ball은 어떻게 고르나요?
A: Floating은 Ball이 Seat에만 지지되어 압력을 받으면 하류 쪽으로 밀리면서 씰링하고, Trunnion은 Ball이 상하 Trunnion에 고정되어 유체 하중을 베어링이 받습니다. 그래서 Trunnion은 운전 토크가 낮고 대구경·고압·자동화에 유리합니다. 일반적으로 소구경·저압은 Floating, 대구경·고압은 Trunnion을 쓰며(출처 기준), API 6D는 두 형식을 모두 다루므로 경계는 프로젝트 Spec과 제조사 Rating으로 확인합니다.
키워드: floating ball, trunnion mounted ball, 트러니언, 플로팅, API 6D, 대구경, 고압, 토크
부품: ball, seat, stem, body
출처: [Floating vs Trunnion Ball Valve - Project Materials](https://blog.projectmaterials.com/quick-answers/valves/floating-vs-trunnion-ball-valve/)

### Q: Ball Valve 기본 구조와 Full bore / Reduced bore 차이는?
A: Ball Valve는 구멍 뚫린 Ball을 90° 회전시켜 여닫는 Quarter-turn 밸브로, Body·Ball·Seat·Stem이 핵심입니다. Full bore는 Ball 구멍이 배관 내경과 비슷해 압력손실이 적고 Pigging이 필요한 라인에 쓰고, Reduced bore는 구멍이 작아 무게·가격이 줄어듭니다. 어느 쪽을 쓸지는 배관 Spec과 Pigging 요건에 따르며 수치는 미확인입니다.
키워드: full bore, reduced bore, full port, quarter-turn, pigging, 볼밸브 구조
부품: body, ball, seat, stem
출처: [Ball Valves Basics - Valve Magazine](https://www.valvemagazine.com/articles/ball-valves-basics)

### Q: Trunnion Ball Valve에 있는 Sealant Injection Port는 왜 있나요?
A: 대부분의 API 6D Trunnion 밸브에는 1차 Seat가 손상됐을 때 비상용 Sealant를 주입할 수 있는 포트가 있습니다(출처 기준). 운전 중 Seat 누설이 생겨도 즉시 정비가 어려운 파이프라인·대형 밸브에서 임시 대응 수단이 됩니다. 다만 Sealant 사용이 공정 유체·Seat 재질과 맞는지 제조사와 확인해야 합니다.
키워드: sealant injection, emergency sealant, trunnion, API 6D, seat leak, 실런트
부품: seat, body
출처: [What is a Trunnion Ball Valve? - Actuation Valve](https://www.actuation.co.uk/guide-to-trunnion-ball-valves)

### Q: DBB와 DIB는 어떻게 다른가요?
A: API 6D 정의상 DBB는 양쪽에서 오는 압력을 각각 Seat 두 개로 막고 중간 Cavity를 Bleed할 수 있는 단일 밸브이고, DIB는 Seat 각각이 한 압력원에 대해 양방향으로 씰링하는 구조입니다. 업계에서는 DIB 밸브를 DBB라고 느슨하게 부르는 경우가 많아 MR에 정확히 명시해야 합니다. DIB-1(양쪽 양방향 Seat)은 Cavity 과압을 외부 Relief로 처리해야 하고, DIB-2는 한쪽이 Self-relieving이라 한 방향으로 자동 해소됩니다.
키워드: DBB, DIB, DIB-1, DIB-2, double block and bleed, double isolation and bleed, cavity relief, API 6D
부품: seat, body
출처: [Differences Between Double Block and Bleed and Double Isolation - Valve Magazine](https://www.valvemagazine.com:443/articles/differences-between-double-block-and-bleed-and-double-isolation)

### Q: Cavity Relief를 왜 꼭 검토해야 하나요?
A: 양방향 Seat가 양쪽 모두 막고 있으면 Body Cavity에 갇힌 액체가 빠져나갈 길이 없습니다. 이때 햇빛 등으로 Body가 가열되면 열팽창으로 압력이 급상승해 Casing이 손상될 수 있습니다(출처 기준). 액체·응축 가능 서비스에서는 Self-relieving Seat나 외부 Relief 중 어느 방식인지 Datasheet에서 반드시 확인하세요. Relief 설정값 관련 수치는 미확인입니다.
키워드: cavity relief, thermal expansion, trapped liquid, 열팽창, self-relieving seat, DPE, SPE
부품: seat, body
출처: [What Is DBB Valve? - Project Materials](https://blog.projectmaterials.com/quick-answers/valves/what-is-dbb-valve/)

### Q: 볼밸브를 제어용(Control)으로 써도 되나요? V-port Ball은?
A: 일반 Ball은 On/Off용이고, 제어용으로는 V-notch(Segmented) Ball을 씁니다. V-notch는 저개도에서 유로가 작고 고개도에서 커져 넓은 유량 범위를 다룰 수 있고, 고형물을 전단하며 막힘이 적습니다. 일반적으로 제조사는 200:1 이상의 Rangeability를 주장하지만(Bray 출처 기준) 이는 제조사 주장이라 실제 설치 조건에서는 낮을 수 있습니다. 고차압 정밀 제어는 Globe가 더 적합한 경우가 많습니다.
키워드: V-port, V-notch, segmented ball, control ball valve, rangeability, slurry, 제어용 볼밸브
부품: ball, seat
출처: [V-Control Ball Valve Closer Look - Bray](https://www.bray.com/valves-actuators-controls/control-valves/ball-valves/v-control-ball-valve/v-control-ball-valve-closer-look)

## 설계·사이징
### Q: Actuator 토크 사이징은 어떤 값을 기준으로 하나요?
A: Ball Valve는 닫힌 상태에서 처음 움직일 때의 Break(Breakaway) 토크가 보통 가장 커서 사이징을 지배합니다. 그러나 Running·Closing(Seating) 토크도 따로 확인해야 합니다. 밸브 제조사가 준 토크 데이터에 서비스 조건(이물, 건조가스 등)을 반영하고, Actuator의 최소 공급압 기준 출력과 비교합니다. 최종 값은 밸브·Actuator 제조사 데이터로 확정합니다.
키워드: break torque, breakaway torque, running torque, seating torque, actuator sizing, 토크 사이징, BTO, ETC
부품: actuator, stem, ball
출처: [How to Size Pneumatic Actuators - Crossco](https://www.crossco.com/resources/technical/how-to-size-pneumatic-actuators/)

### Q: 토크 Safety Factor는 얼마나 잡나요?
A: 출처마다 다릅니다. 많은 고객이 25%를 요구한다는 자료가 있고(Crossco 기준), 최소 20%에 가혹 유체면 높인다는 자료도 있습니다(Assured Automation 기준). 서비스 계수·유체 계수를 이미 넣었다면 추가 여유가 불필요하다는 제조사 의견도 있어 중복 적용 여부를 봐야 합니다. 프로젝트 Spec 값이 우선이며 없으면 미확인으로 두세요.
키워드: safety factor, 토크 여유율, service factor, 25%, 20%, actuator margin, MAST
부품: actuator
출처: [How to Size Pneumatic Actuators - Crossco](https://www.crossco.com/?p=124399)

### Q: Scotch Yoke와 Rack & Pinion 토크 특성 차이가 사이징에 왜 중요하죠?
A: Scotch Yoke는 행정 양 끝에서 토크가 크고 중간에서 작아지는 곡선을 가집니다(출처 기준). Ball Valve는 Break 토크가 끝단에서 크므로 잘 맞지만, 중간 행정 Running 토크가 큰 밸브면 부족할 수 있습니다. 또 Spring-return은 Spring 끝단과 Air 끝단 출력이 다르므로 피크값만 보지 말고 행정별 토크 곡선 전체를 밸브 요구 토크와 겹쳐 확인해야 합니다.
키워드: scotch yoke, rack and pinion, torque curve, spring end, air end, mid-stroke torque
부품: actuator, spring
출처: [Tips on sizing pneumatic actuators - Control Engineering](https://www.controleng.com/tips-on-sizing-pneumatic-actuators)

### Q: Spring-return Actuator에서 Air 공급압이 낮아지면 어떻게 되나요?
A: Air 쪽 출력은 공급압에 비례하므로, 최소 공급압 기준으로 사이징하지 않으면 저압 시 밸브가 끝까지 안 움직일 수 있습니다. 한 제조사 가이드는 저공급압 대비로 공압 Actuator에 추가 계수를 권합니다(Islip 자료 기준, 1.5배). Spring 쪽은 공급압과 무관하지만 Spring 피로가 오면 출력이 떨어집니다. 최소·정상·최대 공급압을 Datasheet에 모두 적으세요.
키워드: minimum supply pressure, 최소 공급압, instrument air, spring return, air failure
부품: actuator, spring
출처: [Ball Valves catalogue - Islip Flow Controls](https://www.islipflowcontrols.com/files/products/ball-valves.pdf)

## Actuator·Accessory
### Q: ESDV에 Spring-return을 주로 쓰고 Double-acting은 잘 안 쓰는 이유는?
A: Spring-return은 Air나 전원이 끊겨도 Spring이 밸브를 정해진 위치로 보내므로 Fail-safe가 단순합니다. Double-acting은 Air를 잃으면 그 자리에 멈추는(Fail-in-place) 특성이 있어 Fail-safe를 만들려면 Volume Tank와 SOV가 추가돼 고장 지점이 늘어납니다(출처 기준). 대형 밸브에서 Spring이 너무 커지면 Double-acting+Tank를 쓰기도 하는데, 이 경우 Tank 용량 계산 근거를 받아야 합니다(초안, 담당자 확인 필수).
키워드: spring return, single acting, double acting, volume tank, fail-safe, fail in place, ESDV actuator
부품: actuator, spring, solenoid
출처: [Double-Acting vs Spring Return Actuators - Assured Automation](https://assuredautomation.com/news-and-training/double-acting-vs-spring-return-actuators/)

### Q: SOV(Solenoid Valve)는 ESDV에서 어떤 역할을 하나요?
A: SOV는 SIS/ESD 신호를 받아 Actuator의 Air를 배기해 밸브를 Fail 위치로 보내는 최종 전환 장치입니다. 평상시 Energized(De-energize to trip) 구성이 일반적이며, 1oo1·1oo2·2oo2 등 배열에 따라 신뢰성과 오작동 특성이 달라집니다. 한 특허 자료는 2oo2 배열을 가장 위험한 쪽으로 평가했으나 이는 해당 특허 맥락이므로, 실제 배열은 SRS와 SIL 계산으로 결정합니다(초안, 담당자 확인 필수).
키워드: SOV, solenoid valve, 1oo1, 1oo2, 2oo2, de-energize to trip, ESD, SIS final element
부품: solenoid, actuator
출처: [Online partial stroke testing system using a modified 2oo4 architecture - Justia Patents](https://patents.justia.com/patent/7828008)

### Q: Limit Switch는 몇 개를 달고 무엇을 확인하나요?
A: 기본은 Open·Close 위치를 확인하는 두 개이며, DCS/SIS가 밸브 실제 위치와 Stroke 시간을 판단하는 근거가 됩니다. TopWorx D-ESD 같은 제품은 Open/Close 스위치 외에 Partial Stroke 확인용 스위치를 따로 둡니다(출처 기준). 스위치 형식(근접식·기계식), 방폭, 접점 정격은 프로젝트 Spec으로 확인하세요.
키워드: limit switch, open close feedback, ZSO, ZSC, position indication, proximity switch, 리밋스위치
부품: limit-switch, bracket
출처: [TopWorx D-ESD Partial Stroke IOM - Emerson](https://emerson.com/documents/automation/manual-topworx-d-esd-partial-stroke-emergency-shut-down-iom-topworx-en-4852782.pdf)

### Q: Actuator와 Accessory 장착 인터페이스는 어떤 표준을 보나요?
A: 밸브와 Quarter-turn Actuator 사이 플랜지는 ISO 5211, Limit Switch Box·Positioner·Pilot Valve 직결 장착은 NAMUR VDI/VDE 3845가 흔히 쓰입니다(출처 기준). Bracket·Coupling을 별도 제작하면 백래시와 정렬 문제로 위치 피드백이 틀어질 수 있습니다. MR에 Mounting 표준과 Bracket 공급 범위를 명시하세요.
키워드: ISO 5211, NAMUR, VDI/VDE 3845, mounting bracket, coupling, actuator interface
부품: bracket, actuator, limit-switch
출처: [Quarter turn actuators for process valves - Festo](https://www.festo.com/ca/en/c/products/actuators-and-drives/pneumatic-drives-for-process-valves/quarter-turn-actuators-for-process-valves-id_pim210/)

### Q: PST(Partial Stroke Test)는 왜 하고 얼마나 움직이나요?
A: ESDV는 평소 거의 움직이지 않아 고착될 가능성이 높으므로, 공정을 멈추지 않고 일부만 움직여 고착 여부를 확인하는 것이 PST입니다. 일반적으로 정상 위치에서 10~20% 정도 움직인다고 소개되며(Project Materials 출처 기준), 다른 자료는 10~30%로 언급합니다. PST 중 ESD 신호가 오면 ESD가 우선해 밸브가 Fail 위치로 가야 합니다(초안, 담당자 확인 필수).
키워드: PST, partial stroke test, partial stroke testing, PVST, 부분행정시험, stuck valve, ESDV
부품: pst, actuator, solenoid
출처: [How to perform stroke test - Project Materials](https://www.blog.projectmaterials.com/quick-answers/epc/how-to-perform-stroke-test/)

### Q: PST를 하면 SIL 계산에 어떤 영향이 있나요?
A: PST는 Full stroke 시험 사이에 위험 고장 일부를 찾아내므로 PFDavg 계산에서 진단 커버리지로 반영됩니다. 실제 한 Actuator 제조사 선언서는 PVST 없이 SIL 1, PVST 사용 시 SIL 3 해당으로 표기합니다(Emerson 선언서 기준). 그러나 PST 커버리지와 시험 주기 가정이 SIL 검증서와 일치해야 하며, PST가 Full stroke 시험을 대체하지는 않습니다(초안, 담당자 확인 필수).
키워드: PST, PVST, SIL, PFDavg, proof test, diagnostic coverage, IEC 61511
부품: pst, actuator
출처: [SIL FQ Fail-Safe Quarter Turn Manufacturer's Declaration - Emerson](https://emerson.com/documents/automation/sil-fq-fail-safe-quarter-turn-model-manufacturer-s-declaration-en-5387920.pdf)

## Fail Action·Stroke Time
### Q: BDV는 왜 Fail-Open인가요? 꼭 그래야 하나요?
A: BDV는 비상 시 설비 압력을 Flare로 빼내 화재·과압 시 용기 파손을 막는 역할이라, 제어계가 고장 나면 열리도록(Fail-open) 설계하는 것이 일반적입니다. 다만 포럼에서는 API 521 문구를 근거로 비상 기간 동안 동작 가능하면 Fail-open이 모든 경우 필수는 아니라는 의견도 있습니다. 실제 Fail 위치는 공정 안전 검토와 C&E로 확정합니다(초안, 담당자 확인 필수).
키워드: BDV, blowdown valve, fail open, FO, depressurization, 감압, flare, API 521
부품: actuator, spring
출처: [eng-tips - BDV fail position discussion](https://www.eng-tips.com/viewthread.cfm?qid=140522)

### Q: Depressurization 시간 기준(15분 등)은 BDV 사양에 어떻게 연결되나요?
A: 업계에서 자주 인용되는 기준은 15분 안에 100 psig 또는 설계압의 50% 중 낮은 값까지 감압하는 것입니다(출처 기준). 하지만 이 15분은 API 521의 예시일 뿐이고 최신판은 내압에 의한 응력을 고려하도록 바뀌었다는 의견도 있어 해당 판을 직접 확인해야 합니다. 감압 속도는 보통 BDV 하류 Restriction Orifice가 정하므로, BDV 자체는 개방 시간과 Fail 동작이 핵심입니다(초안, 담당자 확인 필수).
키워드: depressuring, depressurization time, 15 minutes, restriction orifice, RO, BDV, API 521, 감압시간
부품: actuator
출처: [BDV valve guide - brainbound](https://brainbound.blog/bdv-valve-guide)

### Q: ESDV Stroke Time은 어떻게 정하나요? 빠를수록 좋은가요?
A: 무조건 빠르면 좋지 않습니다. 액체 라인에서 너무 빨리 닫으면 Hydraulic Surge(수격)가 생겨 배관·기기가 손상될 수 있습니다. 포럼에서는 액체 라인에 밸브 인치당 1초를 쓴다는 경험칙이 언급되지만 이를 규정한 표준은 찾지 못했다고 합니다. Stroke Time은 공정 안전 시간(Process Safety Time)과 Surge 해석을 함께 보고 프로젝트에서 정해야 합니다(초안, 담당자 확인 필수).
키워드: stroke time, closing time, ESDV, surge, water hammer, 수격, process safety time, 1 sec per inch
부품: actuator, solenoid
출처: [ESDV closing speed - eng-tips](https://eng-tips.com/threads/esdv-closing-speed.286856)

## 누설·Fire-safe
### Q: Ball Valve 누설 시험은 FCI 70-2인가요 API 598인가요?
A: FCI 70-2는 제어밸브 Seat 누설 등급(Class I~VI) 기준이고, 차단용 Ball Valve는 보통 API 598이나 ISO 5208로 시험합니다. 두 체계는 시험 매체·압력이 달라 서로 1:1로 대응되지 않으므로 환산표를 그대로 믿으면 안 됩니다(출처 기준). ESDV처럼 Tight shut-off가 필요한 밸브는 적용 표준과 Rate(예: ISO 5208 Rate A)를 Datasheet에 명시하세요.
키워드: seat leakage, API 598, ISO 5208, FCI 70-2, Rate A, Class VI, tight shut-off, 누설등급
부품: seat, ball
출처: [Valve leakage class - Project Materials](https://blog.projectmaterials.com/quick-answers/valves/valve-leakage-class/)

### Q: Soft seat와 Metal seat는 어떻게 고르나요?
A: Soft seat(PTFE, PEEK 등)는 기밀성이 좋아 Bubble-tight가 쉽지만 고온·마모·화재에 약합니다. Metal seat는 고온·고형물·고빈도 동작에 강하지만 누설 등급과 토크 면에서 불리할 수 있습니다. 일반적으로 Metal seat의 실용적 상한은 FCI 기준 Class V 수준이라는 자료가 있습니다(출처 기준). 서비스 온도·고형물·Fire-safe 요구를 함께 보세요.
키워드: soft seat, metal seat, PTFE, PEEK, resilient seat, metal seated ball valve, 시트재질
부품: seat, ball
출처: [Valve Leakage - Wermac](https://wermac.org/valves/valve_leakage.html)

### Q: Fire-safe 인증(API 607 / API 6FA)은 무엇을 보증하나요?
A: Fire test는 밸브를 닫고 가압한 상태에서 일정 시간 화염에 노출한 뒤 내부·외부 누설이 허용 한도 이내인지 보는 형식 시험(Type test)입니다. 일반적으로 노출 시간은 30분으로 소개됩니다(출처 기준). API 607은 Quarter-turn·Soft seat 밸브 중심, API 6FA는 API 6D/6A Metal seat 밸브 중심으로 쓰여 왔지만 판에 따라 범위 해석이 달라 프로젝트 요구 판을 확인해야 합니다.
키워드: fire safe, fire test, API 607, API 6FA, ISO 10497, type test, 내화시험
부품: seat, body, stem
출처: [API 607 vs API 6FA - Project Materials](https://blog.projectmaterials.com/quick-answers/epc/api-607-vs-api-6fa/)

### Q: "Fire-safe design"이라고만 적힌 밸브를 받아도 되나요?
A: 권장하지 않습니다. 설계상 Fire-safe라고 해도 실제 시험을 거치지 않았을 수 있으므로, 제3자 기관이 발행한 Fire test 인증서를 요구하라는 것이 공개 자료의 조언입니다. 인증서의 적용 범위(Size·Class·Seat 재질 Family)가 공급 밸브와 일치하는지도 대조하세요. Soft seat 밸브는 보통 2차 Metal 씰 구조로 화재 시 기밀을 유지합니다(출처 기준).
키워드: fire safe certificate, third party, design family, secondary metal seal, 인증서 범위
부품: seat, body
출처: [What is fire safe valve - Project Materials](https://www.blog.projectmaterials.com/quick-answers/valves/what-is-fire-safe-valve/)

### Q: Stem 누설(Fugitive Emission) 요구는 어떤 표준을 쓰나요?
A: Quarter-turn 밸브의 Fugitive emission 형식 시험은 API 641, 국제적으로는 ISO 15848-1이 쓰입니다. API 641은 메탄을 시험 매체로 EPA Method 21을 사용하고 허용 한도는 100 ppm으로 소개됩니다(Valve Magazine 출처 기준). ISO 15848-1은 메탄 또는 헬륨을 쓰며 기밀·내구·온도 등급으로 분류합니다. 프로젝트가 어느 표준·등급을 요구하는지 MR에 적으세요.
키워드: fugitive emission, API 641, ISO 15848-1, stem seal, packing, methane, helium, 탈루배출
부품: stem
출처: [Fugitive Emissions Standards for Valves - Valve Magazine](https://www.valvemagazine.com:443/articles/fugitive-emissions-standards-for-valves)

## 표준·SIL
### Q: ESDV 밸브 SIL 인증서만 있으면 SIL 요건을 만족하나요?
A: 아닙니다. IEC 61508/61511은 인증을 의무로 하지 않으며, 인증서만으로는 충분하지 않다는 것이 공개 자료의 입장입니다. 인증서는 그 장치가 어떤 SIL에 쓰일 수 있는지를 보여줄 뿐이고, 실제 Loop의 HFT, Proof test 주기, PST 가정, SOV·Actuator·밸브 고장률을 합친 SIL 검증이 따로 필요합니다(초안, 담당자 확인 필수).
키워드: SIL certificate, IEC 61508, IEC 61511, HFT, SFF, SIL verification, FMEDA, ESDV
부품: actuator, solenoid, ball
출처: [Emergency Shutdown Valves: Functional Safety Approach - Chemical Engineering](https://www.chemengonline.com/emergency-shutdown-valves-functional-safety-approach-selection/)

### Q: 제조사 고장률 데이터(FIT, λDU)는 어떻게 읽나요?
A: Datasheet는 보통 λSD·λSU·λDD·λDU를 FIT(10⁹시간당 고장 수)로 제시합니다. Actuator와 Solenoid 고장률이 따로 나오거나, 일체형 Solenoid 고장률이 빠져 있는 경우가 있어 합산 범위를 꼭 확인해야 합니다. 근거가 FMEDA인지 Proven-in-use인지도 함께 받으세요(초안, 담당자 확인 필수).
키워드: failure rate, FIT, lambda DU, λDU, FMEDA, proven in use, safety manual
부품: actuator, solenoid
출처: [Failure rates of valves - TÜV NORD](https://www.tuev-nord.de/en/services/audit-and-expertise/product-certification/failure-rates-of-valves/)

### Q: API 6D가 Ball Valve에 요구하는 주요 사항은 무엇인가요?
A: API 6D는 파이프라인·공정용 Ball·Gate·Plug·Check 밸브의 설계·재질·시험을 다루며 Floating과 Trunnion을 모두 포함합니다. DBB/DIB 정의, Cavity relief, 압력 시험 등이 주요 항목으로 소개됩니다. 개별 조항 번호와 수치는 공개 2차 자료 간 차이가 있어 미확인이며 원문으로 대조해야 합니다.
키워드: API 6D, pipeline valve, trunnion, DBB, DIB, pressure test, ISO 14313
부품: body, ball, seat
출처: [API 6D valve standards guide - EPCLand](https://epcland.com/api-6d-valve-standards-guide/)

## 시험
### Q: ESDV Full Stroke Test에서는 무엇을 확인하나요?
A: Full stroke 시험은 밸브를 Fail-safe 위치까지 끝까지 움직여 Stroke Time과 Limit Switch 동작을 확인합니다(출처 기준). 공장 FAT와 현장 Commissioning 모두에서 시행하며, 결과는 SIL 검증의 Proof test 기록이 됩니다. 측정 조건(최소 공급압, Actuator 배관 상태)을 기록해 두어야 나중에 성능 저하를 비교할 수 있습니다(초안, 담당자 확인 필수).
키워드: full stroke test, proof test, stroke time test, limit switch check, FAT, commissioning
부품: actuator, limit-switch, solenoid
출처: [How to perform stroke test - Project Materials](https://www.blog.projectmaterials.com/quick-answers/epc/how-to-perform-stroke-test/)

### Q: SOV도 따로 시험할 수 있나요?
A: 일부 ESD 컨트롤러는 SOV 단독 시험 기능을 제공하며, PST 뒤에 이어서 실행할 수도 있습니다(Val Controls 자료 기준). 1oo1·1oo2·2oo2 구성과 호환된다고 소개됩니다. SOV는 장기간 Energized 상태로 있어 고착 위험이 있으므로 시험 방법과 주기를 SRS와 맞춰 정해야 합니다(초안, 담당자 확인 필수).
키워드: SOV test, solenoid test, online testing, 1oo2, 2oo2, ESD controller
부품: solenoid
출처: [Solenoid Operated Valve (SOV) Testing - Val Controls](https://www.valcontrols.com/pages/sov-testing)

## 사양 검토 유의사항
### Q: Ball Valve Actuator 사양 검토 때 자주 놓치는 점은?
A: 첫째, 최소 공급압 기준으로 토크 여유를 확인하지 않는 경우입니다. 둘째, Spring-end와 Air-end 출력을 각각 Break·Run·End 토크와 비교하지 않는 경우입니다. 셋째, Safety factor를 제조사와 EPC가 중복 적용해 과대 Actuator가 되는 경우입니다. 과대 Actuator는 Stem 비틀림 한계(MAST)를 넘을 수 있으니 Stem 허용 토크도 함께 보세요.
키워드: review checklist, actuator review, MAST, stem torque, oversizing, 사양검토
부품: actuator, stem, spring
출처: [Sizing pneumatic actuators - Assured Automation](https://blog.assuredautomation.com/?p=8903)

## MR 작성·Vendor 문서
### Q: Ball Valve MR / Datasheet에 꼭 들어가야 할 항목은?
A: Tag·서비스·Size·Class·Bore·Floating/Trunnion·Seat 형식(DBB/DIB 포함)·Body/Ball/Seat/Stem 재질, 누설 표준과 등급, Fire-safe·Fugitive emission 요구가 기본입니다. Actuator 쪽은 형식(Spring/Double), Fail 위치, Stroke Time, 공급압 범위, SOV·Limit switch·PST 사양, 방폭·IP 등급이 필요합니다. 안전 밸브는 SIL 요구와 인증서 제출을 명시합니다(초안, 담당자 확인 필수).
키워드: MR, material requisition, datasheet, ball valve datasheet, actuator datasheet, 필수항목
부품: body, ball, seat, stem, actuator, solenoid, limit-switch, pst
출처: [Floating vs Trunnion Ball Valve - Project Materials](https://blog.projectmaterials.com/quick-answers/valves/floating-vs-trunnion-ball-valve/)

### Q: ESDV Vendor 문서로 무엇을 받아야 하나요?
A: GA 도면, Actuator 토크 계산서(밸브 토크 데이터 포함), Air 회로도와 Stroke Time 계산, SOV·Limit switch·PST Datasheet, 누설·Fire test·Fugitive emission 인증서, SIL 인증서와 Safety Manual(FMEDA 고장률 포함)이 핵심입니다. FAT 절차서와 Full stroke 시험 기록도 필요합니다. 문서 목록 최종본은 프로젝트 VDRL로 확인하세요(초안, 담당자 확인 필수).
키워드: vendor document, VDRL, GA drawing, torque calculation, safety manual, SIL certificate, FAT procedure
부품: actuator, solenoid, limit-switch, pst
출처: [Emergency Shutdown Valves: Functional Safety Approach - Chemical Engineering](https://www.chemengonline.com/emergency-shutdown-valves-functional-safety-approach-selection/)

## 자주 하는 실수
### Q: BDV 하류 Restriction Orifice 배치에서 흔한 실수는?
A: 감압 속도는 보통 BDV 하류 RO가 정하는데, RO를 BDV에 너무 붙이면 감압 시 냉각으로 결빙이 생겨 밸브가 고착될 수 있다는 지적이 있습니다. 공개 자료 중에는 BDV와 RO 사이를 일정 거리 띄우라는 제안이 있으나 구체 거리는 미확인입니다. 저온 재질 선정(MDMT)도 함께 검토해야 하며, 최종 배치는 배관·공정 담당과 확인하세요(초안, 담당자 확인 필수).
키워드: BDV, restriction orifice, RO, freezing, low temperature, JT cooling, MDMT, 결빙
부품: process-conn, body
출처: [BDV valve guide - brainbound](https://brainbound.blog/bdv-valve-guide)

### Q: "DBB 밸브"라고만 MR에 적으면 무엇이 문제인가요?
A: 업체마다 DBB를 DIB 의미로 쓰는 경우가 많아, 원하는 Seat 구성(양방향/Self-relieving)과 Cavity relief 방식이 다르게 들어올 수 있습니다. 결과적으로 격리 성능이나 열팽창 대응이 기대와 달라집니다. MR에는 API 6D 용어 기준으로 DBB / DIB-1 / DIB-2와 Seat별 방향성을 명시하세요.
키워드: DBB, DIB-1, DIB-2, MR wording, seat configuration, 용어혼동
부품: seat, body
출처: [Differences Between DBB and DIB - Valve Magazine](https://www.valvemagazine.com:443/articles/differences-between-double-block-and-bleed-and-double-isolation)
