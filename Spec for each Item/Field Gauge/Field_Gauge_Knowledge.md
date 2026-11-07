# Field Gauge Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: 현장 압력계(Pressure Gauge)는 어떤 원리로 지시하나요?
A: 가장 흔한 형식은 Bourdon tube 방식으로, 압력이 걸리면 휘어진 튜브가 펴지려는 변위를 링크와 기어(movement)가 바늘 회전으로 바꿔 줍니다. 저압이나 부식성·점성 유체에는 diaphragm 또는 bellows 형식이 쓰이기도 합니다. 형식에 따라 적용 압력 범위와 내과압 특성이 달라지므로 형식 선정을 먼저 하고 Range·정확도를 정하는 것이 순서입니다.
키워드: 압력계, Pressure Gauge, PG, PI, Bourdon tube, 부르동관, diaphragm gauge, bellows, movement
부품: case, dial, needle, socket
출처: [Ashcroft - Seven steps pressure gauge selection guide](https://www.ashcroft.com/wp-content/uploads/2020/07/selection-guide-seven-steps-pressure-gauge.pdf)

### Q: ASME B40.100 은 어떤 표준이고 최신판은 무엇인가요?
A: ASME B40.100 은 압력계와 그 부속품(gauge attachments)을 다루는 미국 표준으로, 정확도 등급·구조·시험 같은 내용을 담고 있습니다. ASME 공개 목차 기준으로 현행판은 2022년판이며, 표준 판매처 정보에 따르면 2013년판은 철회(withdrawn) 상태로 표시됩니다. 프로젝트 Spec 이 어느 Rev 를 인용하는지 먼저 확인해야 하며, 조항 번호는 원문 확인 전까지 '미확인'으로 둡니다.
키워드: ASME B40.100, B40.100-2022, pressure gauge standard, gauge attachments, 압력계 표준
출처: [ASME B40.100-2022 Table of Contents](https://www.asme.org/getmedia/e36d3d8e-8d61-4380-869f-e47dc907dd82/B40-100_2022_ToC.pdf), [SFS Store - ASME B40.100-2013](https://store.sfs.fi/en/asme-b40100-2013)

### Q: 압력계 정확도 Grade A, 1A, 2A, 3A 는 무슨 뜻인가요?
A: ASME B40.100 의 정확도 등급 표기로, 숫자가 클수록 정밀합니다. WIKA 데이터시트 예시로는 일반적으로 Grade B 가 ±3/2/3% of span, Grade A 가 ±2/1/2% of span, Grade 1A 가 ±1% of span, Grade 2A 가 ±0.5% of span, Grade 3A 가 ±0.25% of span 으로 표기됩니다(WIKA 출처 기준). '3/2/3' 은 눈금 하단·중간·상단 구간별 허용오차라는 의미이므로 공정 운전점이 어느 구간에 오는지도 함께 봐야 합니다.
키워드: accuracy grade, Grade A, Grade 1A, Grade 2A, Grade 3A, % of span, 정확도 등급, ASME B40.100
부품: dial, needle
출처: [WIKA 232.53/233.53](https://www.wika.com/en-us/232_53_233_53.WIKA), [WIKA 332.54](https://www.wika.com/en-us/332_54.WIKA), [WIKA 262.34/263.34](https://www.wika.com/en-us/262_34_263_34.WIKA)

### Q: 온도계는 Bimetal 과 Gas-actuated(가스 충전식) 중 무엇을 써야 하나요?
A: Bimetal 은 저렴하고 주변온도 변화 영향을 거의 받지 않아 일반 현장 지시용으로 많이 쓰입니다. Gas-actuated 는 헬륨 등 가스 충전 시스템이라 응답이 빠르고 capillary 로 원격 지시가 가능하지만, 주변온도 변화에 따른 오차가 단점입니다. 응답속도·원격 지시·극한 온도가 필요하면 Gas-actuated, 그 외 일반 국부 지시는 Bimetal 이 무난하다는 것이 WIKA 의 설명입니다.
키워드: bimetal thermometer, gas-actuated thermometer, 바이메탈 온도계, 가스 충전식, TG, TI, capillary, 원격 지시
부품: case, dial, socket
출처: [WIKA blog - Selection criteria for dial thermometers (process temperature)](https://blog.wika.com/en/knowhow/selection-criteria-for-dial-thermometers-2-process-temperature/), [WIKA Bimetal thermometer](https://www.wika.com/en-gb/lp_bimetal_thermometer.WIKA)

### Q: Reflex, Transparent, Magnetic 레벨 게이지는 어떻게 다른가요?
A: Reflex 는 프리즘 홈이 있는 유리 한 장으로 빛의 굴절·반사를 이용해 액체 부분이 어둡게 보이고, Transparent 는 유리 두 장 사이로 액체를 직접 비춰 봅니다. Magnetic 은 유리 없이 챔버 안 float 의 자석이 외부 플랩/셔틀 지시를 돌리는 방식입니다. 무색 액체에는 Reflex, 유색 액체나 계면(interface) 측정에는 Transparent, 고압·부식성·유리 파손이 문제인 곳에는 Magnetic 이 흔히 거론됩니다.
키워드: level gauge, LG, reflex level gauge, transparent level gauge, magnetic level gauge, MLG, sight glass, 레벨 게이지, 계면
부품: case, process-conn
출처: [Instrumentation Tools - Transparent and Reflex level gauge](https://instrumentationtools.com/transparent-and-reflex-level-gauge), [DirectIndustry - Choosing the right level gauge](https://guide.directindustry.com/choosing-the-right-level-gauge/)

### Q: 현장 Flow Indicator 로 쓰는 Rotameter(가변면적 유량계)는 어떤 원리인가요?
A: 테이퍼진 튜브 안에서 유량이 늘면 float 가 올라가 통과 면적이 커지고, float 높이로 유량을 직접 읽는 방식입니다. 전원 없이 국부 지시가 가능하고 압력손실이 작은 편이라 퍼지·소유량 라인에 많이 쓰입니다. 다만 유체 밀도·점도가 바뀌면 눈금이 달라지므로 교정 조건과 실제 운전 조건이 같은지 확인해야 합니다.
키워드: rotameter, variable area flowmeter, VA meter, flow indicator, FI, 가변면적 유량계, float
부품: case, process-conn
출처: [DwyerOmega - Variable area flow meter](https://www.dwyeromega.com/en-ca/resources/variable-area-flow-meter), [Omega - Rotameters](https://www.omega.com/en/resources/rotameters)

### Q: Thermowell 은 왜 쓰나요?
A: Thermowell 은 온도 센서(온도계 stem, RTD, TC)를 공정 유체의 압력·유속·부식으로부터 보호하는 압력 경계 부품입니다. Thermowell 이 있으면 공정을 멈추지 않고 센서를 교체·점검할 수 있습니다. 대신 유체 속에 돌출되므로 와류 진동(wake frequency)과 응답 지연을 함께 검토해야 합니다.
키워드: thermowell, TW, 보호관, temperature well, 압력 경계, sensor replacement
부품: process-conn, socket
출처: [Brannan - What is a thermowell?](https://www.brannan.co.uk/?p=51713), [Control Engineering - Taking the mystery out of thermowell selection](https://www.controleng.com/single-article/taking-the-mystery-out-of-thermowell-selection/ca7d8298fa72c0ccee515e2dfd413a31.html)

## 선정·사이징
### Q: 압력계 Range 는 운전압력 대비 어떻게 정하나요?
A: Ashcroft 는 일반적으로 운전압력이 눈금의 25~75% 안에 오도록 하고, Full scale 을 운전압력의 약 2배로 잡는 것을 권장합니다(Ashcroft 출처 기준). 눈금 끝 근처에서 계속 쓰면 Bourdon tube 피로가 빨라지고, 너무 크게 잡으면 읽기 분해능이 떨어지기 때문입니다. 프로젝트 Spec 에 별도 기준(예: 설계압력 포함 여부)이 있으면 그것이 우선입니다.
키워드: range selection, full scale, 운전압력, operating pressure, 25~75%, 2배, gauge range, 눈금 선정
부품: dial
출처: [Ashcroft blog - Select pressure gauge range](https://blog.ashcroft.com/select-pressure-gauge-range)

### Q: 맥동(pulsation)이 있는 라인은 Range 를 다르게 잡나요?
A: Ashcroft 선정 가이드는 일반적으로 맥동 압력에서는 최대 운전압력이 Full scale 의 50% 를 넘지 않도록 권합니다(Ashcroft 출처 기준). 맥동은 movement 마모와 바늘 떨림을 키우므로 Range 여유와 함께 snubber 나 liquid fill 을 같이 검토합니다. 펌프·압축기 토출측이 대표적인 적용처입니다.
키워드: pulsation, 맥동, pulsating pressure, 50% full scale, pump discharge, compressor, 펌프 토출
부품: dial, needle
출처: [Ashcroft - Seven steps pressure gauge selection guide](https://www.ashcroft.com/wp-content/uploads/2020/07/selection-guide-seven-steps-pressure-gauge.pdf)

### Q: 다이얼 크기(Dial size)는 정확도와 어떤 관계가 있나요?
A: 정밀 등급일수록 눈금이 촘촘해야 하므로 다이얼이 커야 합니다. 공개 가이드에는 0.25% 나 0.5% 급은 일반적으로 4½" 이상, ±0.5% 이상 정확도에서는 100 mm 미만 다이얼은 권장하지 않는다는 설명이 있습니다(해당 출처 기준). 그 외에는 판독 거리, 설치 공간, 요구 정확도로 크기를 정합니다.
키워드: dial size, 다이얼 크기, 4-1/2 inch, 100 mm, 150 mm, readability, 가독성, accuracy
부품: dial, case, bezel
출처: [Ashcroft - Seven steps pressure gauge selection guide](https://www.ashcroft.com/wp-content/uploads/2020/07/selection-guide-seven-steps-pressure-gauge.pdf), [Pressure gauge selection guide (PDF)](https://www.gotbigwater.com/files/news/594/selection-guide-pressure-gauge-42015.pdf)

### Q: 접액부(wetted part) 재질로 Monel 은 언제 쓰나요?
A: Monel 400 은 니켈-구리 합금으로, 스테인리스가 견디기 어려운 부식 환경에서 선택됩니다. WIKA 데이터시트에는 Bourdon tube 와 process connection 을 모두 Monel 400 으로 한 모델이 있습니다. 재질은 Bourdon tube·socket·diaphragm 등 접액부 전체를 공정 Piping Class·부식 데이터와 맞춰야 하며, 프로젝트 재질표가 우선입니다.
키워드: wetted material, 접액부 재질, Monel 400, SS316, Bourdon tube material, corrosion, 부식
부품: socket, process-conn
출처: [WIKA DS PM26X (Monel)](https://newsletter.wika.com/upload/DS_PM26X_34_en_us_15636.pdf), [A complete guide to Monel pressure gauges](https://shop.machinemfg.com/a-complete-guide-to-monel-pressure-gauges)

### Q: 액체 충전(Liquid filled, Glycerine) 압력계는 왜 쓰고 한계는 무엇인가요?
A: 케이스 안 충전액이 진동과 맥동을 감쇠시켜 바늘이 안정되고 movement 마모가 줄어듭니다. Glycerine 이 가격과 상온 감쇠 성능 때문에 가장 흔하며, 일반적으로 -20~60 °C 범위에서 잘 동작한다고 설명됩니다(Tameson 출처 기준). 저온이나 고온 환경에서는 silicone 등 다른 충전액을 검토하고, 충전액 사용 온도를 데이터시트에 명시해야 합니다.
키워드: liquid filled gauge, glycerine fill, silicone fill, 충전액, 진동 감쇠, vibration, damping
부품: case, needle
출처: [Tameson - Liquid filled pressure gauge](https://tameson.com/pages/liquid-filled-pressure-gauge)

### Q: Bimetal 온도계의 사용 온도 범위와 충전 시 제약은?
A: WIKA 설명으로는 일반적으로 무충전 Bimetal 은 -70~+600 °C 눈금 범위로 설계됩니다(WIKA 출처 기준). 진동 대응을 위해 silicone 충전을 하면 공정 상한이 약 +250 °C 로 제한된다고 합니다(같은 출처 기준). 압축기·펌프 근처처럼 진동이 큰 곳은 충전형을 쓰되 온도 상한을 꼭 대조하세요.
키워드: bimetal range, -70~600 °C, silicone filled, 250 °C, vibration, 진동, 바이메탈
부품: case, dial
출처: [WIKA blog - Selection criteria for dial thermometers](https://blog.wika.com/en/knowhow/selection-criteria-for-dial-thermometers-2-process-temperature/), [Centro MRO - Bimetal thermometer guide](https://www.centromrosupply.com/resources/centroblog/bimetal-thermometer-guide)

### Q: Gas-actuated 온도계로 원격 지시를 할 때 capillary 길이는 얼마까지 되나요?
A: WIKA 는 capillary 를 사용해 측정 지점에서 최대 60 m 떨어진 곳에 설치할 수 있다고 설명합니다(WIKA 출처 기준). 다만 capillary 와 케이스가 주변온도에 노출되므로 길수록 주변온도 오차 관리가 중요합니다. 또한 WIKA 는 stem 직경 8 mm 이상, 가스 충전 센서 길이 100 mm 이상을 권장합니다(같은 출처 기준).
키워드: gas-actuated, capillary, 원격 지시, remote reading, 60 m, ambient temperature effect, stem diameter
부품: case, socket
출처: [WIKA blog - Selection criteria for dial thermometers](https://blog.wika.com/en/knowhow/selection-criteria-for-dial-thermometers-2-process-temperature/)

### Q: 계면(interface) 측정에 Reflex 레벨 게이지를 써도 되나요?
A: 권장되지 않습니다. Reflex 는 액체가 차면 어둡게만 보이므로 두 액체의 경계를 구분하지 못합니다. 계면이나 유색 액체에는 Transparent 를 쓰며, 한 공개 자료는 Transparent 가 Reflex 기능을 대신할 수 있지만 반대는 안 된다고 정리합니다.
키워드: interface level, 계면, reflex, transparent, oil water interface, 유색 액체, colorless
부품: case
출처: [Instrumentation Tools - Transparent and Reflex level gauge](https://instrumentationtools.com/transparent-and-reflex-level-gauge)

### Q: Magnetic 레벨 게이지 float 은 무엇을 기준으로 설계되나요?
A: Float 은 공정 액체의 비중(SG), 설계압력, 설계온도에 맞춰 설계되며, 비중이 기준보다 낮으면 float 이 더 가라앉아 지시가 틀어집니다. Penberthy 자료에는 재질별 최소 적용 비중(예: 316 SS 0.49, Titanium 0.37)이 나와 있습니다(Penberthy 출처 기준). 그래서 데이터시트에 운전 비중 범위를 꼭 적어 보내야 벤더가 float 을 맞출 수 있습니다.
키워드: magnetic level gauge, float, specific gravity, SG, 비중, design pressure, float collapse, chamber
부품: case, process-conn
출처: [Instrumentation Tools - Magnetic level gauge float design](https://instrumentationtools.com/magnetic-level-gauge-float-design), [Penberthy Magnetic Liquid Level Gages](https://www.acomee.com.mx/catalogos/catalogosp/PENBERTHY%20MAGNETIC%20LIQUID%20LEVEL%20GAGES.pdf), [ABB LMG100 manual](https://library.e.abb.com/public/effb23804c5da7b185257cd300671aaf/OI_LMG100-EN.pdf)

### Q: Magnetic 레벨 게이지로 계면을 잴 때 조건이 있나요?
A: 계면용 float 은 상·하부 두 액체의 비중 차이가 있어야 동작합니다. Penberthy 자료는 일반적으로 두 액체의 비중 차가 최소 0.2 이상이어야 한다고 제시합니다(Penberthy 출처 기준). 비중 차가 작으면 다른 측정 원리(예: GWR)를 검토하는 것이 낫습니다.
키워드: interface float, 계면 float, SG difference, 비중 차, 0.2, magnetic level gauge
부품: case
출처: [Penberthy Magnetic Liquid Level Gages](https://www.acomee.com.mx/catalogos/catalogosp/PENBERTHY%20MAGNETIC%20LIQUID%20LEVEL%20GAGES.pdf)

### Q: Magnetic 레벨 게이지에 스위치나 트랜스미터를 붙일 수 있나요?
A: 가능합니다. 챔버 외부 레일에 reed 스위치나 magnetic 스위치를 달아 고·저 레벨 접점을 만들고, 측면에 레벨 트랜스미터를 부착하는 구성이 흔합니다. 다만 스위치 위치가 float 자석 위치와 맞지 않으면 자기장이 약해 동작하지 않을 수 있다는 주의가 있습니다.
키워드: magnetic level gauge switch, reed switch, level transmitter attachment, LSH, LSL, 레벨 스위치
부품: case
출처: [Klinger Magnetic Level Gauges](https://www.alphagroup.co.th/wp-content/uploads/2023/10/Klinger_Magnetic-Level-Gauges.pdf), [Penberthy Magnetic Liquid Level Gages](https://www.acomee.com.mx/catalogos/catalogosp/PENBERTHY%20MAGNETIC%20LIQUID%20LEVEL%20GAGES.pdf)

### Q: Rotameter 는 유리관과 금속관 중 어떤 걸 고르나요?
A: 유리관은 저가로 유체를 직접 볼 수 있지만 고압·고온·위험지역에는 적합하지 않습니다. 금속관은 튼튼해서 고압·고온·위험 서비스에 쓰이고, 지시는 자기 커플링으로 외부에 나타냅니다. 플랜트 탄화수소 서비스라면 금속관을 기본으로 보고 프로젝트 Spec 을 확인하세요.
키워드: glass tube rotameter, metal tube rotameter, armored, 금속관, 유리관, hazardous, 고압
부품: case, process-conn
출처: [Instrumart - Variable area flow meters](https://www.instrumart.com/categories/6207/variable-area-flow-meters), [Silver Instruments - VA flow meter selection guide](https://www.silverinstruments.com/industrial-variable-area-flow-meter-selection-and-application-guide)

### Q: Thermowell 공정 연결 형식은 어떤 것이 있나요?
A: 일반적으로 Threaded, Socket weld, Flanged 가 가장 흔하고, WIKA 카탈로그는 Weld-in, Sanitary 형식도 구분합니다. 플랜트 탄화수소 라인은 Piping Class 에 맞춘 Flanged 가 많이 쓰이지만, 이는 프로젝트 Spec 으로 확인할 사항입니다. Flanged 는 플랜지 Rating·면(face) 형상을 배관과 일치시켜야 합니다.
키워드: thermowell connection, flanged thermowell, threaded, socket weld, weld-in, TW10, TW15, TW20
부품: process-conn
출처: [Control Engineering - Thermowell selection](https://www.controleng.com/single-article/taking-the-mystery-out-of-thermowell-selection/ca7d8298fa72c0ccee515e2dfd413a31.html), [WIKA TW Catalog](https://www.rg-group.com/images/document/WIKA/Wika-TW-Catalog.pdf)

### Q: Thermowell stem 형상(Tapered, Straight, Stepped)은 어떻게 고르나요?
A: Tapered 는 뿌리 쪽이 굵어 강성이 높아 wake frequency 영향을 줄이는 데 유리하다고 설명됩니다. Stepped 는 끝단 질량을 줄여 응답을 빠르게 하면서 연결부 강도를 유지합니다. 최종 형상은 유속 조건에서 wake frequency 계산을 통과하는지로 판단합니다.
키워드: tapered, straight, stepped, thermowell stem, shank, 응답속도, 강성, wake frequency
부품: process-conn
출처: [Thermometrics - Thermowells & Flanges](https://thermometricscorp.com/thermowells.html), [WIKA DS TW9530](https://kz.wika.com/upload/DS_TW9530_en_co_732.pdf)

### Q: Van Stone 형 Thermowell 은 어떤 장점이 있나요?
A: Van Stone 은 lap joint 플랜지를 쓰는 형식으로, Emerson 은 플랜지 재질을 stem 과 다르게 할 수 있어 비용 효율적이라고 설명합니다. 플랜지 규격을 따르면서 정비 접근이 반복적으로 필요할 때 선택된다는 설명도 있습니다. 접액부(stem)와 플랜지 재질을 각각 데이터시트에 명시해야 합니다.
키워드: Van Stone thermowell, lap joint flange, 반스톤, flange material, Rosemount 114C
부품: process-conn
출처: [Emerson Rosemount 114C thermowell family](https://www.emerson.com/en/measurement-instrumentation/products/rosemount-114c-thermowell-family), [Thermometrics - Thermowells](https://thermometricscorp.com/thermowells.html)

## 설치
### Q: Snubber 는 무엇이고 언제 쓰나요?
A: Snubber 는 공정과 게이지 사이에 넣는 유로 제한 장치로, 공정 압력 자체는 바꾸지 않고 맥동·급변을 완화합니다. 가장 단순한 형태는 반쯤 열어 둔 needle valve 입니다. 맥동이 심한 곳은 liquid fill 게이지와 snubber 를 함께 쓰기도 합니다.
키워드: snubber, 스너버, pulsation dampener, restrictor, needle valve, 맥동 완화
부품: socket, process-conn
출처: [Instrumentation Tools - Pressure gauge snubbers](https://instrumentationtools.com/pressure-gauge-snubbers)

### Q: 압력계 Hook-up 에서 부속품 설치 순서는 어떻게 되나요?
A: 한 벤더 자료는 공정 → 차단밸브(gauge cock) → 과압 보호기 → snubber/siphon/냉각 엘리먼트 → 게이지 순서를 제시합니다. 차단밸브가 가장 공정 쪽에 있어야 부속품과 게이지를 운전 중 분리할 수 있습니다. 실제 순서는 회사 Hook-up 표준도와 대조하세요.
키워드: hook-up, 설치 순서, gauge cock, isolation valve, overpressure protector, 과압 보호기, snubber, siphon
부품: process-conn, socket
출처: [ICS Schneider - Overpressure limiting device](https://www.ics-schneider.de/produkt-kategorie/pressure/pressure-gauge/accessory-parts/overpressure-limiting-device/?lang=en)

### Q: 부식성·고점도·응고성 유체는 압력계를 어떻게 보호하나요?
A: Diaphragm seal 을 달아 공정 유체와 Bourdon tube 를 격리하고, 그 사이를 충전액으로 채워 압력을 전달합니다. 일부 welded diaphragm seal 은 계기가 파손돼도 diaphragm 이 터지지 않도록 backing plate 를 둡니다. 충전액 종류와 사용 온도는 데이터시트에 명시해야 합니다.
키워드: diaphragm seal, chemical seal, 격막, 다이어프램 씰, backing plate, fill fluid, 충전액
부품: process-conn, socket
출처: [Instrumentation Tools - Pressure gauge pulsation damping](https://instrumentationtools.com/pressure-gauge-pulsation-damping), [Winters D44 flanged diaphragm seal](https://www.yodify.com/Products/XwLRrZ/D44-Flanged-Diaphragm-Seal-Welded)

### Q: Rotameter 설치 시 주의할 점은?
A: 중력식 rotameter 는 반드시 수직으로 설치해야 하고, 스프링식은 다른 방향 설치가 가능한 제품도 있습니다. 이물질이 float 동작을 방해하므로 상류에 필터를 권장합니다. 운전 압력이 교정 조건과 다르면 지시값 보정이 필요하다는 점도 유의합니다.
키워드: rotameter installation, vertical mounting, 수직 설치, filter, strainer, 필터, 보정
부품: process-conn
출처: [DwyerOmega - Variable area flow meter](https://www.dwyeromega.com/en-ca/resources/variable-area-flow-meter), [Silver Instruments - VA flow meter guide](https://www.silverinstruments.com/industrial-variable-area-flow-meter-selection-and-application-guide)

### Q: Thermowell Wake frequency 계산은 왜 해야 하나요?
A: 유체가 thermowell 을 지나면서 생기는 와류(Karman vortex) 주파수가 thermowell 고유진동수에 가까워지면 공진으로 피로 파손이 날 수 있습니다. 파손되면 압력 경계가 깨져 누출로 이어지므로 안전 측면에서도 중요합니다. 그래서 ASME PTC 19.3 TW 에 따라 진동·응력 검토를 하고, 통과하지 못하면 길이·형상·직경을 바꿉니다.
키워드: wake frequency, 와류, vortex shedding, natural frequency, 고유진동수, resonance, 공진, ASME PTC 19.3 TW
부품: process-conn
출처: [WIKA - Thermowell calculation software (ASME PTC 19.3 TW-2016)](https://www-prod.wika.com/en-us/software_thermowell_5.WIKA), [Pyromation - Wake frequency (ASME PTC 19.3 TW-2016)](https://pyromation.com/TechInfo/WakeFreq.aspx)

### Q: ASME PTC 19.3 TW-2016 은 이전판(1974) 대비 무엇이 바뀌었나요?
A: 공개 해설에 따르면 가장 큰 변화는 가변 Strouhal 수와 함께 in-line 공진을 계산에 포함한 것입니다. 또한 stem 끝단 최소 두께를 3.0 mm 이상으로 규정했다고 설명됩니다(해설 출처 기준). 엘보 설치·경사 설치 안내도 보완됐다고 하니, 구판 기준 계산서를 받으면 판(Rev) 부터 확인하세요.
키워드: PTC 19.3 TW-2016, 1974 edition, in-line resonance, Strouhal number, tip thickness, 3.0 mm, 개정
부품: process-conn
출처: [Process Worldwide - What has changed with the 2016 revision of ASME PTC 19.3 TW](https://www.process-worldwide.com/what-has-changed-with-the-2016-revision-of-the-asme-ptc-193-tw-standard-a-589267/), [WIKA TA 0317 article](https://kz.wika.com/upload/TA_0317_PROCWW_en_co_81382.pdf)

### Q: 용접 튜브형(fabricated) thermowell 도 PTC 19.3 TW 로 계산하나요?
A: WIKA 데이터시트에 따르면 PTC 19.3 TW-2016 은 bar stock 을 드릴링한 일체형(tapered, straight, stepped)에 적용되며, 용접 튜브형에는 적용되지 않습니다. 따라서 fabricated 형식을 쓰면 별도 검토 근거가 필요합니다. 고유속 라인이라면 bar stock 형식을 기본으로 고려하는 편이 검토가 명확합니다.
키워드: fabricated thermowell, welded tube, bar stock, solid drilled, PTC 19.3 TW scope, 적용 범위
부품: process-conn
출처: [WIKA DS IN0015](https://cn.shop.wika.com/upload/DS_IN0015_en_co_1353.pdf)

### Q: Wake frequency 계산에 벤더가 어떤 입력값을 필요로 하나요?
A: 벤더 계산 툴 기준으로 비지지 길이(unsupported length), bore 직경, tip 두께 같은 thermowell 치수와 유속, 유체 밀도 같은 공정 조건이 들어갑니다. 공정 조건이 빠지면 벤더가 임의 가정으로 계산하므로 결과를 신뢰하기 어렵습니다. 데이터시트에 최대 유속·밀도·점도·설계 압력/온도를 명시해 보내세요.
키워드: wake frequency input, unsupported length, bore diameter, tip thickness, fluid velocity, density, 유속, 밀도
부품: process-conn
출처: [WIKA - Thermowell calculation software](https://www-prod.wika.com/en-en/thermowell_calculation_software.WIKA), [Electronic Specifier - Thermowell wake frequency calculation](https://electronicspecifier.com/news/analysis/thermowell-wake-frequency-calculation-in-accordance-with-latest-asme-standard)

## 안전·구조
### Q: Solid front / Blowout back(안전형) 압력계는 왜 쓰나요?
A: Bourdon tube 가 파열되면 내부 압력이 앞 유리 쪽이 아니라 뒤쪽 blowout 판으로 빠지도록 해서 작업자를 보호하는 구조입니다. 앞면과 movement 사이에 칸막이(solid front)가 있어 파편이 앞쪽으로 튀지 않게 합니다. 모든 모델에 기본 적용되는 것은 아니므로 고압·가스 서비스는 데이터시트에 명시해야 합니다.
키워드: solid front, blowout back, safety pattern, 안전형 압력계, blow-out plug, operator protection
부품: blowout, case, bezel
출처: [Alpha Controls - PSC safety case pressure gauge](https://www.alphacontrols.com/products/psc-safety-case-pres-gauge), [Budenberg Safety pattern Monel gauge](https://store.ttech.vn/process-gauge-supasafe-safety-pattern---monel-wetted-parts-966mgp-budenberg-p61382)

### Q: 과압 보호기(Overpressure protector)는 어떤 역할인가요?
A: 설정 압력 이상이 들어오면 내부 밸브가 닫혀 게이지로 가는 압력을 차단해 Bourdon tube 를 보호합니다. Range 를 작게 잡아야 하는데 간헐적 고압이 걸리는 곳에 쓰입니다. 설치 위치는 차단밸브 다음, snubber/siphon 앞이 한 벤더의 권장 순서입니다.
키워드: overpressure protector, gauge saver, 과압 보호기, overpressure limiting device, 과압
부품: process-conn, socket
출처: [ICS Schneider - Overpressure limiting device](https://www.ics-schneider.de/produkt-kategorie/pressure/pressure-gauge/accessory-parts/overpressure-limiting-device/?lang=en), [Chemical Engineering - Pressure gages feature overpressure mechanism](https://www.chemengonline.com/pressure-gages-feature-overpressure-mechanism/)

## 시험·교정
### Q: 압력계는 어떻게 교정하나요?
A: 일반적으로 Dead weight tester 로 피스톤 위에 정해진 추를 얹어 기준 압력을 만들고, 게이지 지시와 비교합니다. 여러 점에서 상승·하강 방향으로 읽어 오차를 기록합니다. 읽기를 쉽게 하려면 바늘이 주요 눈금선에 오도록 입력 압력을 맞추는 방법이 쓰입니다.
키워드: calibration, 교정, dead weight tester, DWT, 기준 압력, 상승 하강, test point
부품: needle, dial
출처: [Virtual Labs - Calibration of pressure gauge using dead-weight tester](https://ic-coep.vlabs.ac.in/exp/dead-weight-tester/procedure.html), [Tameson - Pressure gauge calibration](https://tameson.co.uk/pages/pressure-gauge-calibration)

### Q: 교정 시 Hysteresis 는 어떻게 확인하나요?
A: 같은 압력점을 상승할 때와 하강할 때 읽은 값의 차이가 hysteresis 입니다. 기계적 마모, 온도 변화, 구조 등이 원인이 될 수 있습니다. 한 교정 업체는 교정 전 게이지를 실제 설치 방향으로 장착하고 Full range 까지 한 번 올려 hysteresis loop 와 누설을 먼저 확인한다고 설명합니다.
키워드: hysteresis, 히스테리시스, upscale, downscale, 상승 하강 차이, exercise, 누설
부품: needle
출처: [Brannan - About pressure calibrations](https://www.brannan.co.uk/?p=1983), [Virtual Labs - Dead-weight tester theory](https://ic-coep.vlabs.ac.in/exp/dead-weight-tester/theory.html)

## 사양 검토 유의사항
### Q: 데이터시트에 Grade 3A 를 요구했는데 다이얼이 2½" 이면 문제가 되나요?
A: 문제가 될 가능성이 큽니다. 공개 WIKA 데이터시트 예시에서는 Grade 3A(±0.25%) 가 4" 이상 정밀 게이지에 붙어 있고, 2"·2½" 소형은 Grade A 수준으로 표기됩니다(WIKA 출처 기준). 정확도 등급과 다이얼 크기가 해당 모델 카탈로그에서 같이 제공되는 조합인지 확인하세요.
키워드: grade 3A, dial size mismatch, 2-1/2 inch, 정확도 불일치, datasheet review, 사양 검토
부품: dial
출처: [WIKA 332.54](https://www.wika.com/en-us/332_54.WIKA), [WIKA 232.53/233.53](https://www.wika.com/en-us/232_53_233_53.WIKA)

### Q: Rotameter 데이터시트 검토에서 자주 빠지는 정보는?
A: 운전 밀도·점도·압력·온도와 정상 유량이 빠지는 경우가 많은데, rotameter 는 이 값들로 사이징되므로 빠지면 눈금이 틀어집니다. 한 가이드는 정상 유량이 눈금 상부 절반에 오도록 사양을 정하라고 권합니다. 저유량 영역 정확도가 떨어지는 특성도 고려해야 합니다.
키워드: rotameter sizing, 밀도, 점도, normal flow, 정상 유량, scale, 저유량, datasheet
부품: dial
출처: [Silver Instruments - VA flow meter selection guide](https://www.silverinstruments.com/industrial-variable-area-flow-meter-selection-and-application-guide), [Cole-Parmer - When to choose variable-area flowmeters](https://www.coleparmer.com.cn/tech-article/variable-area-flowmeters)

## MR 작성
### Q: 압력계 MR/데이터시트에 꼭 넣어야 할 항목은?
A: Ashcroft 선정 가이드의 단계를 기준으로 보면 공정 매체, 압력 Range, 정확도, 다이얼 크기, 공정 연결·장착 방식, 옵션(충전액·snubber·siphon·seal 등)이 핵심입니다. 여기에 접액부 재질과 안전형(solid front/blowout back) 여부를 명시하면 벤더 질의가 줄어듭니다. 구체 값과 회사 MR 양식 항목은 프로젝트 Spec 대조 전까지 '미확인'입니다.
키워드: MR, material requisition, datasheet, 압력계 사양, range, accuracy, dial size, connection, mounting, options
부품: case, dial, socket, process-conn, blowout
출처: [Ashcroft - Seven steps pressure gauge selection guide](https://www.ashcroft.com/wp-content/uploads/2020/07/selection-guide-seven-steps-pressure-gauge.pdf)

### Q: Thermowell MR 에 포함할 항목과 벤더 제출 문서는?
A: 연결 형식(flanged/threaded 등)과 Rating, stem 형상, 삽입 길이, 재질, bore 직경을 명시하고 wake frequency 계산에 필요한 유속·밀도 등 공정 조건을 함께 줍니다. 벤더 제출 문서로 ASME PTC 19.3 TW 기준 계산서를 요구하는 것이 일반적이며, 계산서의 표준 Rev(2016 여부)를 확인합니다. 회사 VDRL 항목은 '미확인'입니다.
키워드: thermowell MR, wake frequency report, 계산서, VDRL, vendor document, bore, insertion length, flange rating
부품: process-conn
출처: [WIKA - Thermowell calculation software](https://www-prod.wika.com/en-us/software_thermowell_5.WIKA), [WIKA DS IN0015](https://cn.shop.wika.com/upload/DS_IN0015_en_co_1353.pdf)

### Q: Magnetic 레벨 게이지 MR 에는 무엇을 적어야 하나요?
A: 운전 비중 범위(계면이면 상·하부 각각), 설계 압력·온도, 챔버·float 재질, 공정 연결 간격(center-to-center), 부착 스위치·트랜스미터 유무를 적습니다. float 은 이 조건으로 설계되므로 비중·압력이 빠지면 float 붕괴나 지시 오차 위험이 있습니다. 챔버 압력 설계 기준(예: ASME Sec. VIII 적용 여부)은 벤더·프로젝트 Spec 으로 확인합니다.
키워드: magnetic level gauge MR, specific gravity, center to center, C-C, chamber, float material, ASME Section VIII
부품: case, process-conn
출처: [Penberthy Magnetic Liquid Level Gages](https://www.acomee.com.mx/catalogos/catalogosp/PENBERTHY%20MAGNETIC%20LIQUID%20LEVEL%20GAGES.pdf), [Klinger Magnetic Level Gauges](https://www.alphagroup.co.th/wp-content/uploads/2023/10/Klinger_Magnetic-Level-Gauges.pdf)

## 자주 하는 실수
### Q: 스팀 압력계에 siphon 없이 게이지를 바로 다는 경우 무엇이 문제인가요?
A: 고온 스팀이 Bourdon tube 와 movement 에 직접 닿아 손상·오차가 생깁니다. Siphon 에 응축수가 고여야 보호가 되므로 첫 운전 전 물을 채워 두는 것이 안내되어 있습니다. 동결 우려가 있으면 siphon 대신 diaphragm seal 이 대안입니다.
키워드: steam gauge mistake, siphon missing, 사이폰 누락, condensate, 고온 손상
부품: socket, process-conn
출처: [Instrumentation Tools - Pressure gauge pulsation damping](https://instrumentationtools.com/pressure-gauge-pulsation-damping)

