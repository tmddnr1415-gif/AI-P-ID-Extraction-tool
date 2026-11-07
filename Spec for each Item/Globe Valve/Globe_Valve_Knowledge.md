# Globe Valve Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: Globe Control Valve, PRV(자력식 조절밸브), MOV는 어떻게 구분하나요?
A: Control Valve는 DCS 같은 외부 제어기 신호를 받아 Positioner와 Actuator로 개도를 조절합니다. PRV(Self-operated regulator)는 외부 동력 없이 제어 대상 압력 자체의 힘으로 움직이는 자력식 조절밸브입니다. MOV는 전동 Actuator로 주로 On/Off나 느린 조작을 하는 밸브입니다. 여기서 PRV는 안전밸브(PSV)가 아니라 압력 조절밸브라는 점을 꼭 구분하세요.
키워드: control valve, PRV, pressure regulating valve, self-operated regulator, MOV, motor operated valve, 자력식, 조절밸브
부품: body, trim, actuator, positioner
출처: [Introduction to Regulators - Fisher/Emerson](https://www.emerson.com/documents/automation/manual-introduction-to-regulators-fisher-en-140700.pdf)

### Q: 제어용으로 Globe를 Ball/Butterfly보다 많이 쓰는 이유는?
A: Globe는 Plug와 Seat 형상(Trim)을 바꿔 유량 특성을 정밀하게 만들 수 있고, 고차압·고온·고압 조절에 강합니다. 반면 압력손실이 크고 같은 구경 대비 용량(Cv)이 작으며, 무겁고 비쌉니다. V-port Ball은 Rangeability와 차단 성능이 좋다는 비교 자료가 있지만, 정밀 고차압 제어는 Globe가 선호됩니다(출처 기준).
키워드: globe vs ball, globe vs butterfly, throttling, high pressure drop, control valve selection
부품: body, trim
출처: [Globe vs V Port Ball Valves for Flow Control - Assured Automation](https://blog.assuredautomation.com/globe-v-port-valves-flow-control-applications/)

### Q: Balanced Plug와 Unbalanced Plug 차이는?
A: Balanced Plug는 Plug에 관통 구멍(Port)이 있어 Plug 위아래 압력이 같아지므로 Actuator가 이겨야 할 불평형 힘이 작습니다. Unbalanced Plug는 구멍 없는 통 Plug라 차압이 그대로 Stem 힘으로 걸려 Actuator가 커집니다(Fisher 자료 기준). 대신 Balanced는 추가 Seal(Plug seal)이 누설 경로가 될 수 있어 Shut-off 등급과 온도 조건을 함께 봐야 합니다.
키워드: balanced plug, unbalanced plug, cage guided, plug seal, unbalance force, 평형형, 불평형
부품: trim, stem, actuator
출처: [Sliding-Stem Product Guide - Fisher](https://www.emerson.com/is/content/emerson/es/final-control/flow-controls/globe-valves/guide-sliding-stem-product-guide-fisher-en-3661204.pdf)

### Q: Cage-guided와 Post-guided Trim은 어떻게 다르나요?
A: Plug 가이드 방식으로 Cage-guided와 Post-guided가 가장 흔합니다. Cage는 Plug를 둘러싸서 가이드·정렬을 돕고 유량 특성을 만들 수 있으며, Balanced·Unbalanced 둘 다 가능합니다(Fisher 자료 기준). Cage는 작은 구멍 때문에 이물에 막힐 수 있으므로 오염 서비스면 Trim 형식을 신중히 고르세요.
키워드: cage guided, post guided, top guided, trim type, cage, plug guiding
부품: trim, seat
출처: [Control Valve Trim Types - InstrumentationTools](https://instrumentationtools.com/control-valve-trim-types)

### Q: Equal Percentage, Linear, Quick Opening 특성은 어떻게 고르나요?
A: Equal Percentage는 같은 행정 변화에 Cv가 같은 비율로 변하고, Linear는 행정에 Cv가 비례하며, Quick Opening은 저행정에서 Cv가 빠르게 커집니다. Fisher는 Cage나 Plug를 교체해 이 특성을 바꿀 수 있다고 설명합니다. 일반적으로 차압이 부하에 따라 크게 변하는 계통은 Equal Percentage, 차압이 거의 일정하면 Linear를 쓰며, 최종 선택은 설치 특성(Installed characteristic) 검토로 합니다.
키워드: equal percentage, linear, quick opening, inherent characteristic, installed characteristic, 유량특성
부품: trim
출처: [Globe Control Valves - Emerson](https://www.emerson.com/en-ae/automation/valves/controlvalves/globe-valves)

## 설계·사이징
### Q: Control Valve Cv 사이징은 어떤 표준으로 하나요?
A: 액체·기체 사이징 식은 IEC 60534-2-1(ISA 75.01과 대응)이 기본입니다. 실제 차압과 Choked 차압 중 작은 값을 써서 필요 Cv를 구하는 것이 핵심 논리입니다(출처 기준). 최대·정상·최소 유량 케이스별로 계산하고, 배관 Reducer 영향(FP)까지 반영해야 합니다.
키워드: Cv sizing, IEC 60534-2-1, ISA 75.01, choked flow, flow coefficient, 사이징
부품: trim, body
출처: [Control Valve Sizing - What Is Piping](https://whatispiping.com/control-valve-sizing/)

### Q: FL과 xT는 무엇이고 왜 Datasheet에 필요한가요?
A: FL은 액체 압력회복계수로 Choked(캐비테이션) 차압 한계를 정하고, xT는 기체에서 Choked 차압비를 나타냅니다. 같은 Cv라도 Trim 형식에 따라 FL·xT가 달라 Choked 여부가 바뀌므로, 제조사가 선정한 Trim의 값을 받아 재검증해야 합니다. 구체 수치는 제조사·Trim별이라 미확인입니다.
키워드: FL, xT, pressure recovery factor, choked flow, liquid pressure recovery, IEC 60534
부품: trim
출처: [Control Valve Sizing - What Is Piping](https://whatispiping.com/control-valve-sizing/)

### Q: Cavitation과 Flashing은 어떻게 다르고 어떻게 대응하나요?
A: Cavitation은 Vena contracta에서 증기압 아래로 떨어졌다가 하류에서 압력이 회복되며 기포가 붕괴하는 현상으로 Trim을 심하게 손상시킵니다. Flashing은 하류 압력이 증기압 이하로 유지돼 기포가 남는 상태입니다(출처 기준). Cavitation은 다단 감압 Anti-cavitation Trim으로, Flashing은 내마모 재질·Body 형식 변경으로 대응하는 것이 일반적입니다.
키워드: cavitation, flashing, anti-cavitation trim, vena contracta, vapor pressure, 캐비테이션, 플래싱
부품: trim, seat, body
출처: [Control Valve Sizing - What Is Piping](https://whatispiping.com/control-valve-sizing/)

### Q: 밸브 개도는 몇 %에서 운전되도록 사이징하나요?
A: 일반적으로 최대 유량에서 60~80% 개도, 최소 유량에서 20% 이상 개도가 되도록 사이징하라는 경험칙이 있습니다(Fisher·Valve Magazine 출처 기준). 이는 표준이 아니라 업계 관행이므로 프로젝트 Spec 값이 우선입니다. 과대 사이징 밸브는 거의 닫힌 위치에서 운전되어 제어가 예민해지고 마찰 영향이 커집니다.
키워드: valve opening, 개도, 20% 80%, oversized valve, rangeability, sizing rule
부품: trim
출처: [Properly Size Control Valves - Fisher](https://d1-live.emerson.com/documents/automation/article-properly-size-control-valves-fisher-en-38152.pdf)

### Q: Rangeability가 100:1이라고 하면 실제로도 그만큼 되나요?
A: 그렇지 않을 수 있습니다. 이론상 100:1인 밸브도 잡음이 많거나 동적인 실제 공정에서는 30:1 정도의 Turndown밖에 안 나온다는 자료가 있습니다(출처 기준). 제조사 Rangeability는 고유 특성 기준이므로, 설치 조건에서의 최소 제어 가능 유량을 별도로 확인하세요.
키워드: rangeability, turndown, inherent rangeability, installed, minimum controllable flow
부품: trim
출처: [Control Valve Sizing For The Process Performance - Automation Forum](https://automationforum.co/control-valve-sizing-for-the-process-performance/)

### Q: 밸브 Size를 배관보다 얼마나 작게 해도 되나요?
A: 업계에서는 배관 구경의 1/2보다 작거나 배관보다 큰 Control Valve는 좋지 않은 배관 관행으로 보는 경우가 많다고 합니다(Valve Magazine 출처 기준). 너무 작으면 Reducer 손실과 고속 유동으로 소음·침식이 커지고, 크면 저개도 운전이 됩니다. 프로젝트 기준을 확인하세요.
키워드: valve size, line size, reducer, 1/2 line size, body size selection
부품: body, process-conn
출처: [Size Matters: Control Valve Sizing 101 - Valve Magazine](https://www.valvemagazine.com/articles/size-matters-control-valve-sizing-101)

### Q: 소음 한계는 몇 dBA로 보나요?
A: 일반적으로 밸브 하류 1 m, 배관 표면에서 1 m 지점에서 85 dBA를 넘지 않도록 하라는 기준이 소개됩니다(InstrumentationTools 출처 기준). 다만 85 dBA는 사람이 상주하는 위치의 연속 노출 기준이라 무인 구역은 완화될 수 있다고 합니다. 기체 소음 예측은 IEC 60534-8-3 방법을 쓰며, 한계값은 프로젝트 소음 Spec이 우선입니다.
키워드: noise, 85 dBA, IEC 60534-8-3, aerodynamic noise, low noise trim, 소음
부품: trim, body
출처: [Control Valve Noise Testing - InstrumentationTools](https://instrumentationtools.com/control-valve-noise-testing)

### Q: Low-noise / Anti-cavitation Trim을 쓸 때 주의점은?
A: 이런 Trim은 작은 유로가 많아 이물, 특히 Start-up 시 배관 찌꺼기에 막히기 쉽습니다. 그래서 상류 Strainer 설치가 권장됩니다(InstrumentationTools 출처 기준). 또 출구 Mach 수가 높으면 Trim만으로는 소음이 안 줄어 Body Size를 키워야 하는 경우도 있습니다.
키워드: low noise trim, anti-cavitation trim, plugging, strainer, startup debris, outlet Mach
부품: trim, body
출처: [Control Valve Noise Problems - InstrumentationTools](https://instrumentationtools.com/control-valve-noise-problems/amp/)

## Actuator·Accessory
### Q: Spring-diaphragm Actuator 사이징 시 무엇을 확인하나요?
A: Diaphragm은 Positioner 출력압으로 밀고 Spring이 반대로 미는 구조라, Spring range와 공급압으로 나오는 힘이 불평형 힘·Seat 하중·Packing 마찰을 이겨야 합니다. 특히 Fail 방향(Air-to-open/close)에 따라 Spring이 Shut-off 하중을 맡는지 Air가 맡는지가 달라집니다. 기존 Actuator에 Positioner를 바꿀 때도 Spring range와 사이징을 재확인하라는 권고가 있습니다(출처 기준).
키워드: spring diaphragm actuator, spring range, bench set, seat load, actuator sizing, air to open, air to close
부품: actuator, yoke, stem
출처: [Positioner diagnostics document - SAMSON](https://norway.samsongroup.com/document/t83890en.pdf)

### Q: Fail Close / Fail Open은 어떻게 정하나요?
A: Air나 신호가 끊겼을 때 공정이 안전해지는 방향으로 정합니다. 예를 들어 연료 공급 밸브는 보통 FC, 냉각수 밸브는 FO처럼 공정 안전 관점에서 결정하며, Spring-return Actuator로 구현합니다. 일반 Double-acting은 Air 상실 시 제자리(FL)이므로 Fail 위치가 필요하면 별도 장치가 필요합니다(출처 기준). 최종 Fail 위치는 P&ID·공정 담당 확인이 필요합니다.
키워드: fail close, fail open, fail last, FC, FO, FL, air to open, ATO, ATC, fail action
부품: actuator, positioner
출처: [Double-Acting vs Spring Return Actuators - Assured Automation](https://assuredautomation.com/news-and-training/double-acting-vs-spring-return-actuators/)

### Q: Digital(Smart) Positioner의 진단 기능은 무엇을 알려주나요?
A: HART Positioner는 4-20 mA 신호 위에 디지털 통신을 실어 별도 배선 없이 설정·조회가 가능합니다. 운전 중에는 공급압·설정값·개도·공기 소모를, 정지 중에는 Valve Signature(행정 대 Actuator 압력)를 통해 Spring 설정, 마찰, Seat 하중을 추정할 수 있습니다(SAMSON 자료 기준). MR에 통신 방식(HART/FF/Profibus)과 진단 등급 요구를 적으세요.
키워드: smart positioner, digital valve controller, HART, valve signature, diagnostics, friction, DVC
부품: positioner, actuator
출처: [Positioner diagnostics document - SAMSON](https://norway.samsongroup.com/document/t83890en.pdf)

### Q: MOV(Globe) Actuator는 토크가 아니라 Thrust로 사이징한다는데 왜죠?
A: Gate·Globe 같은 Rising stem 밸브는 축방향 Stem Thrust가 지배 변수입니다. 밸브 공급사의 Breakaway·Running·Seating Thrust를 받아 Actuator의 나사·Thrust nut 데이터와 효율로 필요 토크를 환산합니다(출처 기준). Torque switch 설정만 올리면 밸브·Actuator의 기계적 정격은 그대로인데 과도 하중을 줄 수 있어 위험합니다.
키워드: MOV, motor operated valve, stem thrust, rising stem, thrust to torque, torque switch, Rotork
부품: actuator, stem, yoke
출처: [Torque data on motorised valve - eng-tips](https://www.eng-tips.com/threads/torque-data-on-motorised-valve.160633/post-748657)

### Q: MOV의 Torque Switch와 Limit Switch는 각각 무슨 역할인가요?
A: Rotork는 Torque switch를 Actuator 출력 토크를 직접 측정해 설정값과 비교하는 1차 보호 장치로 설명합니다. Limit switch는 행정 끝 위치를 감지해 정지·표시에 씁니다. Globe처럼 Seat에 눌러 닫는 밸브는 닫힘을 Torque로, 열림을 Limit로 끝내는 방식이 흔하지만, 실제 설정 방식은 밸브 제조사 권고를 따르세요.
키워드: torque switch, limit switch, torque seating, position seating, MOV protection, Rotork IQ
부품: actuator
출처: [Rotork actuator publication PUB002-206](https://www.rotork.com/uploads/documents-versions/47220/1/pub002-206-00-0923.pdf)

## PRV(자력식 조절밸브)
### Q: 자력식 PRV(Regulator) 대신 Control Valve를 써야 하는 경우는?
A: Regulator는 비례 동작만 하므로 유량이 늘면 설정값에서 벗어나는 Offset(Droop)이 생깁니다. 유량이 거의 일정하거나 10~20% 편차를 허용할 수 있으면 자력식 Regulator가 적합하다는 지침이 있습니다(Valve Magazine 출처 기준). 정밀 제어가 필요하면 PID 제어기와 Control Valve를 씁니다.
키워드: PRV, regulator, self-operated, droop, offset, proportional, regulator vs control valve
부품: body, trim
출처: [Regulators Versus Control Valves - Valve Magazine](https://valvemagazine.com/articles/regulators-versus-control-valves-what-s-the-best-fit/)

### Q: Direct-operated와 Pilot-operated Regulator 차이는?
A: Pilot형은 작은 Direct형 Regulator(Pilot)를 메인에 붙여 이득을 높여서 Droop을 크게 줄입니다. Emerson 커뮤니티 자료는 Direct형 20~40%, Pilot형 1~5% Offset으로 소개하지만 다른 자료와 수치가 달라 제조사 Catalog로 확인해야 합니다. Pilot형은 대용량·대구경이 가능하지만 Pilot 배관이 막히기 쉬운 오염 서비스에는 주의가 필요합니다.
키워드: direct operated regulator, pilot operated regulator, droop, accuracy, capacity
부품: body, trim, actuator
출처: [Direct-operated Regulators vs Pilot-operated - Emerson Exchange 365](https://emersonexchange365.com/community-hubs/valves-actuators-regulators/f/actuators-regulators-other-final-control/7624/direct-operated-regulators-vs-pilot-operated)

### Q: Regulator 사이징 때 Cv 말고 무엇을 봐야 하나요?
A: Regulator는 Diaphragm 면적, Spring rate, Stroke 길이로 Droop이 결정되므로, 필요 유량에서 허용 Droop 이내인지 제조사 용량표로 확인해야 합니다(출처 기준). Control Valve처럼 Cv만으로 고르면 실제 유량에서 압력이 너무 떨어질 수 있습니다. 또 Sensing line 위치와 하류 과압 보호(PSV) 필요성도 함께 검토하세요.
키워드: regulator sizing, droop, spring rate, diaphragm area, capacity table, sensing line
부품: actuator, trim
출처: [Pressure Valves: Dealing With Droop - Chemical Processing](https://chemicalprocessing.com/processing-equipment/fluid-handling/article/11380815/pressure-valves-dealing-with-droop)

## 누설·Bonnet
### Q: Control Valve Shut-off 등급(FCI 70-2 Class IV/V/VI)은 어떻게 정하나요?
A: FCI 70-2는 제어밸브 Seat 누설을 Class I~VI로 나눕니다. Class IV는 일반 Metal seat 수준으로 정격 용량 대비 비율로 정의되고, Class V는 Metal seat의 실용적 상한, Class VI는 보통 Soft seat가 필요합니다(출처 기준). 등급을 높이면 Actuator Seat 하중과 가격이 커지므로 공정상 꼭 필요한 경우에만 올리세요.
키워드: shut-off class, seat leakage, FCI 70-2, ANSI B16.104, Class IV, Class V, Class VI, 누설등급
부품: seat, trim, actuator
출처: [Valve leakage class - Project Materials](https://blog.projectmaterials.com/quick-answers/valves/valve-leakage-class/)

### Q: Extension Bonnet과 Bellows Seal Bonnet은 언제 쓰나요?
A: Extension Bonnet은 Packing을 공정 유체에서 멀리 떨어뜨려 고온·저온 서비스에서 Packing 온도를 허용 범위로 유지합니다. 저온(Cryogenic)에서는 Body·Bonnet 보온 공간 확보도 목적입니다. Bellows Seal은 Stem 주위를 금속 벨로즈로 완전히 밀봉해 독성 등 누설 불허 서비스에 씁니다(출처 기준). 핀 달린 Extension Bonnet은 보온재로 덮으면 안 됩니다.
키워드: extension bonnet, bellows seal bonnet, cryogenic, high temperature, toxic service, packing temperature
부품: bonnet, stem
출처: [Control Valve Features: Bonnets - GlobalSpec](https://www.globalspec.com/reference/13621/179909/chapter-10-6-control-valve-features-bonnets)

### Q: Stem Packing 누설(Fugitive Emission) 요구는 Globe에 어떤 표준이 적용되나요?
A: Rising stem 밸브에는 API 624, Packing 자체 시험은 API 622, 국제적으로는 ISO 15848-1이 쓰입니다(Valve Magazine 출처 기준). Control Valve는 계속 움직이므로 Packing 마모가 크다는 점에서 저배출 Packing 사양과 내구 등급이 중요합니다. 어떤 표준이 우리 프로젝트에 적용되는지는 미확인이므로 Spec에서 확인하세요.
키워드: fugitive emission, API 624, API 622, ISO 15848-1, low emission packing, stem seal
부품: stem, bonnet
출처: [Fugitive Emissions Standards for Valves - Valve Magazine](https://www.valvemagazine.com:443/articles/fugitive-emissions-standards-for-valves)

## 시험
### Q: Control Valve FAT에서는 무엇을 시험하나요?
A: 일반적으로 Body 내압(Hydro) 시험, Seat 누설 시험, Stroke 시험(전개·전폐, 응답 시간, 부드러움), Positioner 교정이 포함됩니다. Hydro 시험은 ISA 75.19.01, Seat 누설은 FCI 70-2를 근거로 한다는 자료가 있습니다(출처 기준). 합격 기준 수치는 프로젝트 Spec과 시험 절차서로 확인하세요.
키워드: FAT, hydrostatic test, seat leak test, stroke test, ISA 75.19.01, FCI 70-2, calibration
부품: body, seat, actuator, positioner
출처: [Factory Acceptance Test procedure for control valve - Automation Forum](https://automationforum.co/factory-acceptance-test-fat-procedure-for-control-valve/)

### Q: Dead band, Resolution, Step response 시험은 왜 하나요?
A: 제어 성능은 밸브가 작은 신호 변화에 얼마나 정확·빠르게 반응하느냐에 달려 있습니다. ISA 75.25.01은 Baseline, Small step, Response time 시험 절차를 정의하고, Small step으로 Dead band와 Resolution을 구합니다(출처 기준). 중요 제어 Loop 밸브는 MR에 동특성 시험 요구를 넣는 것을 검토하세요.
키워드: dead band, resolution, step response, ISA 75.25.01, dynamic test, hysteresis
부품: positioner, actuator, stem
출처: [ISA SP75.25 Control Valve Dynamic Testing Update - Control Engineering](https://www.controleng.com/isas-sp75-25-control-valve-dynamic-testing-subcommittee-update/)

## MR 작성·Vendor 문서
### Q: Control Valve Datasheet 양식은 어떤 표준을 따르나요?
A: ISA-20 계열 Specification form이 쓰이며, 현재 Control Valve 양식은 ISA-TR20.00.01에 있다고 소개됩니다(ISA 자료 기준). ISA-20 양식은 'Check sheet' 성격이라 모든 엔지니어링 데이터를 담지 못할 수 있어, 회사 Spec으로 보완하는 것이 일반적입니다. 회사 고유 양식이 있으면 그것이 우선입니다.
키워드: datasheet, ISA-20, ISA-TR20.00.01, specification form, control valve datasheet
출처: [ISA75.14 committee / ISA standards](https://www.isa.org/standards-and-publications/isa-standards/isa-standards-committees/isa75-14)

### Q: Control Valve MR에 꼭 넣어야 할 항목은?
A: 공정 조건(최대·정상·최소 유량, 입·출구 압력, 온도, 밀도, 증기압), 계산 Cv와 선정 Cv·개도, FL·xT, 소음 예측값, 유량 특성, Shut-off 등급이 필요합니다. 기계 쪽은 Size·Rating·Body/Trim 재질·Bonnet 형식·Packing, Actuator 형식·Fail 위치·공급압, Positioner·Accessory 사양을 적습니다. PRV는 설정 범위와 허용 Droop, MOV는 전원·Thrust·제어 방식을 추가하세요.
키워드: MR, material requisition, process data, Cv, noise, shut-off class, actuator, positioner, 필수항목
부품: body, trim, seat, bonnet, actuator, positioner
출처: [Control Valve Technical Specification - Scribd](https://www.scribd.com/document/23812409/Control-Valve-Technical-Specification)

### Q: Vendor 사이징 결과를 검토할 때 무엇을 대조하나요?
A: Vendor가 사용한 공정 조건이 Datasheet와 같은지 먼저 봅니다. 그다음 최대 유량 개도와 최소 유량 개도, Choked/Cavitation 판정, 소음 예측값, Actuator 여유력(Shut-off 조건 차압)을 확인합니다. 제조사 FL·xT 값과 소음 계산 방법(IEC 60534-8-3 등) 명시 여부도 체크하세요.
키워드: vendor sizing review, sizing calculation, noise calculation, actuator margin, choked check
부품: trim, actuator
출처: [Properly Size Control Valves - Chemical Processing](https://www.chemicalprocessing.com/automation/control-systems/article/11333308/properly-size-control-valves-chemical-processing)

## 자주 하는 실수
### Q: Control Valve 사양에서 흔한 실수는?
A: 첫째, 여유를 겹겹이 넣어 과대 사이징하는 것입니다. 과대 밸브는 1% 출력 변화에 공정이 3% 이상 움직일 만큼 예민해질 수 있다는 지적이 있습니다(Fisher 출처 기준). 둘째, 최소 유량 케이스를 빠뜨려 저개도 운전이 되는 것입니다. 셋째, Shut-off 차압을 정상 차압으로 써서 Actuator가 부족해지는 경우입니다.
키워드: oversizing, common mistakes, minimum flow, shut-off pressure, actuator undersizing
부품: trim, actuator
출처: [Properly Size Control Valves - Fisher](https://d1-live.emerson.com/documents/automation/article-properly-size-control-valves-fisher-en-38152.pdf)

### Q: 저온 서비스 Globe Valve 사양에서 놓치기 쉬운 점은?
A: 저온 서비스는 Extension Bonnet 길이, 저온용 재질(스테인리스 등), 특수 Seal을 함께 지정해야 합니다. 예를 들어 Fisher의 ET-C 저온 사양은 일반적으로 -198°C까지 정격으로 소개됩니다(제조사 출처 기준). 보온 두께에 맞는 Bonnet 길이와 Actuator 장착 방향도 확인하세요.
키워드: cryogenic, LNG, extension bonnet, low temperature, ET-C, insulation
부품: bonnet, body, trim
출처: [Fisher easy-e ET-C - Emerson](https://www.emerson.com/en-us/catalog/fisher-sku-et-c)
