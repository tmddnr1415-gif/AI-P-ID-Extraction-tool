# FGS Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: FGS 는 ESD/SIS 와 뭐가 다른가요?
A: FGS(Fire & Gas System)는 화재·가스 누출을 감지해 경보하고 차단·소화·환기 정지 같은 완화(Mitigation) 동작을 하는 계통이고, ESD/SIS 는 공정 이상을 미리 막는 예방 계통입니다. 한 교육 자료는 F&G 가 ESD 와 기능적으로 분리된다고 설명합니다. FGS 는 사고를 막는 게 아니라 피해를 줄이는 것이어서, IEC 61511 의 SIL 지표만으로는 성능을 다 표현하기 어렵다는 것이 ISA TR84.00.07 이 나온 배경입니다. 안전 계통이므로 답변은 초안이며 담당자 확인이 필수입니다.
키워드: FGS, fire and gas system, F&G, ESD, SIS, mitigation, 완화, 화재가스
부품: fgs-panel
출처: [ISA 84.00.07 (Wikipedia)](https://en.wikipedia.org/wiki/ISA_84.00.07), [Fire and gas detection system part 2 (SlideShare)](https://www.slideshare.net/GanChet/fire-and-gas-detection-system-part-2block-diagramphilosophy-signal-types-and-redundant-failureppt)

### Q: FGS 를 SIS 로 봐야 하나요?
A: 업계에서 논쟁이 있는 주제입니다. MSA 는 FGS 가 자동으로 공정 동작을 일으켜 위험을 막거나 완화한다면 적절한 Logic solver·센서·최종요소를 갖춘 SIF/SIS 로 볼 수 있다는 입장입니다. 반면 감지기 배치가 나쁘면 SIL 2 부품을 써도 위험을 감지하지 못해 목표를 달성할 수 없다는 비판도 같이 소개됩니다. 실무에서는 프로젝트 FGS 철학서에서 어떤 기능을 SIF 로 다룰지 먼저 정해야 합니다.
키워드: SIF, SIS, IEC 61511, IEC 61508, SIL, FGS 분류, functional safety
부품: fgs-panel
출처: [Can a Fire and Gas System Be Considered a Safety Instrumented System? (MSA)](https://blog.msasafety.com/can-a-fire-and-gas-system-be-considered-a-safety-instrumented-system/)

### Q: ISA TR84.00.07 은 어떤 문서인가요?
A: 공정 산업에서 화재·가연성 가스·독성 가스 감지기의 배치와 FGS 효과성 평가를 다루는 ISA 기술 보고서입니다. 2010년에 처음 나왔고 2018년 2판이 발행되었다고 소개됩니다. 경보 장치·스프링클러·화학 소화 설비 자체는 범위에서 제외됩니다. 기술 보고서(TR)이므로 규범적 요구라기보다 지침이며, 프로젝트가 어느 판을 적용하는지 확인해야 합니다.
키워드: ISA TR84.00.07, TR 84.00.07-2018, FGS effectiveness, performance-based, 기술보고서
부품: gas-detector, flame-detector
출처: [ISA 84.00.07 (Wikipedia)](https://en.wikipedia.org/wiki/ISA_84.00.07), [Performance-Based Fire & Gas System Engineering (Kenexis)](https://www.kenexis.com/performance-based-fire-gas-system-fgs-engineering/)

### Q: Geographic coverage 와 Scenario coverage 는 무슨 차이인가요?
A: Geographic coverage 는 특정 높이에서 그 위치를 중심으로 화재·누출이 났을 때 감지기 배열이 감지할 수 있는 면적 비율입니다. Scenario coverage 는 발생 위치·빈도·규모까지 고려해, 현실적인 누출·화재 시나리오 중 감지되는 비율입니다. Scenario coverage 가 더 실제에 가깝지만 계산 부담이 큽니다. 목표 커버리지 수치는 프로젝트 FGS 철학서 기준이며 공개 자료로는 '미확인'입니다.
키워드: geographic coverage, scenario coverage, 커버리지, detector mapping, 3D mapping, 감지 범위
부품: gas-detector, flame-detector
출처: [ISA 84.00.07 (Wikipedia)](https://en.wikipedia.org/wiki/ISA_84.00.07), [Understanding Fire and Gas Mapping (Kenexis)](https://www.kenexis.com/wp-content/uploads/2014/05/UnderstandingFireAndGasMapping.pdf)

### Q: Prescriptive 설계와 Performance-based 설계는 어떻게 다른가요?
A: Prescriptive 는 "장비 몇 개당 감지기 몇 개" 같은 고정 규칙으로 배치하는 방식이고, Performance-based 는 위험 분석으로 커버리지·Safety availability·완화 효과 목표를 정한 뒤 맵핑으로 검증하는 방식입니다. Kenexis 는 영국 HSE 8년 자료에서 실제 감지 성공률이 약 60% 에 그쳤다며 성능 기반 방식을 권합니다(출처 기준). 성능 목표는 위험 정도에 따라 차등을 둡니다.
키워드: performance-based, prescriptive, 성능기반, HSE, detection rate, safety availability
부품: gas-detector, flame-detector
출처: [Performance-Based Fire & Gas System Engineering (Kenexis)](https://www.kenexis.com/performance-based-fire-gas-system-fgs-engineering/)

## 설계
### Q: FGS 설계는 어떤 순서로 진행하나요?
A: Kenexis 가 소개하는 흐름은 ① FGS 철학서 작성 ② 위험·리스크 분석으로 성능 목표 설정 ③ FEED 에서 예비 감지기 배치·수량 산정 ④ 상세설계에서 3D 모델 기반 맵핑·재검증 ⑤ 유지보수·시험 사양 수립입니다. 모든 위험을 다 감지하는 건 비현실적이므로 철학서에서 감지 대상 규모와 동작을 먼저 정합니다. 각 단계 산출물을 문서로 남겨야 이후 변경 관리가 됩니다.
키워드: FGS lifecycle, philosophy, FEED, detailed design, mapping, 설계절차, F&G philosophy
부품: gas-detector, flame-detector, fgs-panel
출처: [Performance-Based Fire & Gas System Engineering (Kenexis)](https://www.kenexis.com/performance-based-fire-gas-system-fgs-engineering/)

### Q: F&G 맵핑은 언제 하는 게 좋나요?
A: Kenexis 는 상세설계에서 3D 모델이 약 60% 완성되었을 때 첫 맵핑을 하라고 권합니다(출처 기준). 이후 배관·구조물이 바뀌면 감지 시야가 가려지므로 배치를 다시 분석하고 커버리지를 재검증해야 합니다. 맵핑은 감지기 종류·위치·방향·설정값을 모두 반영해야 의미가 있습니다.
키워드: F&G mapping, 3D model 60%, 맵핑 시점, re-mapping, obstruction, 재검증
부품: gas-detector, flame-detector
출처: [Performance-Based Fire & Gas System Engineering (Kenexis)](https://www.kenexis.com/performance-based-fire-gas-system-fgs-engineering/)

### Q: 가스 감지기 설치 높이는 어떻게 정하나요?
A: 기본은 가스 밀도입니다. 수소·메탄처럼 공기보다 가벼운 가스는 높게, 중질 탄화수소처럼 무거운 가스는 바닥 가까이(한 자료는 바닥에서 약 30 cm) 둡니다(출처 기준). 독성 가스는 사람이 마시는 호흡 높이 기준으로 두라는 권고도 있습니다. 다만 고온·고압 누출은 무거운 가스도 위로 올라갈 수 있어 밀도만으로 정하면 안 되고, 공정·장비 배치와 기류를 같이 봐야 합니다.
키워드: detector height, 설치높이, lighter than air, heavier than air, breathing zone, 가스밀도, methane, hydrogen
부품: gas-detector
출처: [How to Place Gas Detectors (gasdetection.com)](https://gasdetection.com/articles/how-to-place-gas-detectors-for-optimal-safety-and-accuracy/), [Gas Detector Location Standards (Industrial Monitor Direct)](https://industrialmonitordirect.com/blogs/knowledgebase/gas-detector-location-standards-flammable-toxic-gas-placement-guide)

### Q: H2S 감지기는 낮게 다나요, 호흡 높이로 다나요?
A: 자료마다 다릅니다. 여러 자료는 H2S 비중을 약 1.19 로 보고 바닥 가까이 낮게(약 0.3~0.6 m) 두라고 하고, 어떤 벤더 표는 호흡 높이(Breathing level)를 권합니다(출처 기준). 일부 자료는 H2S 를 가벼운 가스로 분류하는 오류도 보입니다. 이렇게 충돌하므로 사이트 가스 데이터와 프로젝트 철학서로 확정해야 하며, 현재는 '미확인'입니다.
키워드: H2S, hydrogen sulfide, 황화수소, toxic gas, 독성가스, mounting height, 충돌
부품: gas-detector
출처: [LEL and H2S Gas Detector Placement in Petroleum Refining (Industrial Monitor Direct)](https://industrialmonitordirect.com/blogs/knowledgebase/lel-and-h2s-gas-detector-placement-in-petroleum-refining-applications), [How to Place Gas Detectors (gasdetection.com)](https://gasdetection.com/articles/how-to-place-gas-detectors-for-optimal-safety-and-accuracy/)

### Q: 가스 감지기 위치를 잡을 때 밀도 말고 무엇을 보나요?
A: 플랜지·밸브·피팅 같은 누출원 가까이, 기류 방향을 고려해 배치하고, 문·창문처럼 신선 공기로 희석되는 곳은 피합니다. 큰 장비 뒤처럼 가려지는 곳(특히 IR·Open path)은 피하고, 기류가 정체된 Dead air 구역도 주의해야 합니다. 범프 테스트·교정을 위해 큰 해체 없이 접근할 수 있어야 하고, 햇빛·비 보호 커버도 고려합니다. 한 자료는 약 95% 시스템의 감지기 수·간격에 대한 국가·국제 지침이 없다고 언급합니다(출처 기준).
키워드: leak source, airflow, 누출원, 기류, dead air, access, sunshade, weather protection
부품: gas-detector
출처: [How to Place Gas Detectors (gasdetection.com)](https://gasdetection.com/articles/how-to-place-gas-detectors-for-optimal-safety-and-accuracy/)

### Q: 가연성 가스 감지기는 촉매식과 적외선(IR) 중 무엇을 고르나요?
A: 촉매식(Catalytic bead)은 수소를 감지할 수 있고 값이 싸지만, 실리콘·황·인·납 화합물에 피독되어 영구 감도 저하가 오고, 산소가 부족하면 낮게 지시하며, 고장 시 조용히 낮게 나올 수 있습니다. IR 은 피독이 없고 광학 고장을 자기진단으로 알리지만 수소는 감지하지 못합니다. 그래서 수소 위험이 있으면 촉매식이나 다른 방식, 피독·저산소 환경이면 IR 이 일반적인 선택입니다.
키워드: catalytic bead, infrared, IR, NDIR, poisoning, 피독, hydrogen, 수소, LEL, 가연성가스
부품: gas-detector
출처: [Catalytic Bead vs Infrared LEL Sensors (WCSafety)](https://wcsafety.com/blogs/reference/catalytic-bead-vs-infrared-lel-sensors), [Infrared vs. Catalytic Bead Technology (WWD)](https://www.wwdmag.com/utility-management/article/10927991/oldham-fixed-gas-detection-infrared-vs-catalytic-bead-technology-pros-and-cons)

### Q: Open path 가스 감지기는 언제 쓰고 설정값은 어떻게 표시하나요?
A: Open path 는 송신기와 수신기 사이 빔 경로 전체에서 가스 구름을 감지하므로 넓은 지역·경계선 감시에 씁니다. 단위는 농도×거리인 LEL·m 이며, Honeywell Searchline Excel Plus 예시는 측정 범위 0~5 LEL·m, Low 1 LEL·m, High 3 LEL·m 입니다(출처 기준). 성능 요구는 IEC 60079-29-4 가 다룹니다. 프로젝트 설정값은 철학서 기준이며 '미확인'입니다.
키워드: open path, OPGD, LEL.m, LEL·m, Searchline, beam, IEC 60079-29-4, 개방경로
부품: op-gas
출처: [Searchline Excel Plus Open Path Gas Detector (Honeywell)](https://automation.honeywell.com/gb/en/products/gas-and-flame-detection/fixed-gas-and-flame-detection/fixed-gas-detectors/searchline-excel-plus-open-path-gas-detector), [IEC 60079-29-4 preview (ANSI)](https://webstore.ansi.org/preview-pages/IEC/preview_iec60079-29-4%7Bed1.0%7Db.pdf)

### Q: Open path 감지기의 빔 차단(Beam block)은 어떻게 처리하나요?
A: 빔이 가려지면 가스가 없어도 감지 불능 상태이므로 별도 상태 신호로 알려야 합니다. 한 제품(SafEye) 예시는 4-20 mA 출력에서 빔 차단 2 mA, 유지보수 3 mA, Zero 교정 1 mA, 고장 0 mA 처럼 상태를 구분합니다(출처 기준). FGS 패널이 이 저전류 대역을 가스 0 이 아니라 Fault 로 인식하도록 설정했는지 확인해야 합니다.
키워드: beam block, obscuration, fault current, 2mA, 빔 차단, 저전류, mA status
부품: op-gas, fgs-panel, signal
출처: [SafEye series 700 datasheet](https://www.heatingandprocess.com/wp-content/uploads/2016/03/SafEye-series-700-min.pdf)

### Q: 화염 감지기는 UV, UV/IR, IR3 중 무엇을 고르나요?
A: UV 단독은 아크 용접·할로겐 램프·낙뢰에 오동작하기 쉽고 짙은 그을음에 감도가 떨어져 주로 실내용입니다. UV/IR 은 오경보 내성이 개선되어 실내외 겸용이고, IR3(다파장 IR)는 오경보 내성과 감지 거리가 가장 좋은 편으로 평가됩니다. 선정 기준은 감지 거리, 시야각(Cone of vision), 응답 시간, 특정 오경보원에 대한 내성입니다.
키워드: flame detector, UV, UV/IR, IR3, multi-spectrum IR, false alarm, 오경보, cone of vision, 화염감지기
부품: flame-detector
출처: [Selecting the Right Flame Detector (MSA, Chromatography Today)](https://www.chromatographytoday.com/article/safety/15/msa-general-monitors/selecting-the-right-flame-detector/1518), [Protection by detection – industrial flame detectors (Spectrex)](https://envirotech-online.com/article/gas-detection/8/spectrex-inc/protection-by-detection-ndash-industrial-flame-detectors/541/download)

### Q: 화염 감지기 감지 거리는 어떻게 이해해야 하나요?
A: 감지 거리는 시험 연료와 화재 크기를 전제로 한 값이라서, 같은 감지기라도 연료와 화재 규모가 달라지면 거리가 바뀝니다. 예를 들어 Det-Tronics X3301 데이터시트는 n-Heptane 기준 약 210 ft, 메탄 기준 약 100 ft 를 제시합니다(출처 기준, 2008년 자료라 최신판 확인 필요). 또 시야각 가장자리로 갈수록 감도가 떨어지므로 맵핑에서 원뿔형 시야를 반영해야 합니다.
키워드: detection range, 감지거리, n-heptane, methane, fire size, X3301, Det-Tronics, field of view
부품: flame-detector
출처: [X3301 Multispectrum IR Flame Detector datasheet](https://www.orrprotection.com/hubfs/Orrprotection_Docs_Feb2016/90-1144-4.1_X3301_Pulse-Multispectrum_IR_Flame_Det.pdf), [Protection by detection – industrial flame detectors (Spectrex)](https://envirotech-online.com/article/gas-detection/8/spectrex-inc/protection-by-detection-ndash-industrial-flame-detectors/541/download)

### Q: 감지기 Voting 은 1ooN 과 2ooN 중 무엇을 쓰나요?
A: 경보는 1ooN, 소화(Deluge)나 ESD 같은 실행 동작은 오동작 영향이 크므로 2ooN 확인(Confirmed) 신호로 거는 경우가 많습니다. 한 교육 자료는 가연성 가스 2ooN, 50% LEL 에서 실행 동작을 예로 들고, 한 해양 철학서 예시는 전기실 확정 화재·실내 확정 가스에서 HVAC 트립과 방화댐퍼 닫힘을 2ooN 으로 둡니다(출처 기준). 이는 사례일 뿐 표준이 아니므로 프로젝트 C&E 로 확정('미확인')하세요. 맵핑 도구는 Voting 별 커버리지를 따로 계산하므로 Voting 을 바꾸면 커버리지도 다시 봐야 합니다.
키워드: voting, 1ooN, 2ooN, 1oo2, 2oo3, confirmed fire, confirmed gas, deluge, 실행동작
부품: fgs-panel, gas-detector, flame-detector
출처: [Fire and gas detection system part 2 (SlideShare)](https://www.slideshare.net/GanChet/fire-and-gas-detection-system-part-2block-diagramphilosophy-signal-types-and-redundant-failureppt), [ISA TR84 FGS (Scribd, Rockwell)](https://www.scribd.com/document/371042998/141023-Rockwell-ISATR84-pdf)

### Q: 오동작(Spurious trip)이 FGS 에서 특히 문제인 이유는?
A: 오경보로 소화 설비가 작동하면 장비 손상과 인명 위험이 생길 수 있기 때문입니다. 그래서 실행 동작에는 Voting 을 걸고, 감지기 자체도 오경보 내성이 좋은 기종을 고릅니다. 반대로 Voting 을 과하게 걸면 커버리지가 줄어 감지 실패 위험이 커지므로 두 위험의 균형을 맞춰야 합니다.
키워드: spurious trip, 오동작, false alarm, deluge damage, voting trade-off, 오경보
부품: fgs-panel, flame-detector
출처: [DeltaV SIS Fire & Gas capabilities white paper (Emerson)](https://www.emerson.com/documents/automation/white-paper-deltav-sis-fire-gas-capabilities-en-5292184.pdf), [Cause and Effect Drawings (Automation Forum)](https://automationforum.co/cause-and-effect-drawings/)

## Interface
### Q: FGS Cause & Effect 매트릭스는 어떻게 읽나요?
A: 행에는 원인(감지기 그룹·Voting), 열에는 결과(경보, ESD, HVAC 정지, 댐퍼, Deluge 등)를 두고 교차점에 표시를 합니다. 한 자료는 "X" 는 결과 작동, "T" 는 시간 지연 후 작동, "P" 는 원인이 결과를 허용(Permissive)함을 뜻한다고 설명합니다. 기호 체계는 프로젝트마다 다를 수 있으므로 범례를 먼저 확인하세요.
키워드: cause and effect, C&E, matrix, 원인결과표, time delay, permissive, 범례
부품: fgs-panel
출처: [Cause and Effect Drawings (Automation Forum)](https://automationforum.co/cause-and-effect-drawings/)

### Q: FGS 가 다른 계통과 주고받는 대표 신호는 무엇인가요?
A: 일반적으로 ESD 로의 Trip 요청, HVAC 정지·방화 댐퍼 닫기, 소화 설비(Deluge) 기동, 경광등·사이렌·PA 경보, DCS 로의 상태·경보 전송이 있습니다. 한 압축기 스테이션 사례는 확정 가스·화재 시 사이트 전체 ESD 와 대피 경보를 요구했습니다(출처 기준). 각 신호가 하드와이어인지 통신인지, Fail-safe 방향(De-energize/Energize to trip)은 프로젝트 Spec 으로 확인('미확인')해야 합니다.
키워드: interface, ESD, HVAC, damper, deluge, PA/GA, DCS, hardwired, 인터페이스
부품: fgs-panel, beacon, signal
출처: [Fire and Gas Protection in Natural Gas Compressor Stations (Moore Industries)](https://mimpage.miinet.com/sla-fire-gas-protection-control)

### Q: 수동 발신기(MAC)는 어떤 기준으로 보나요?
A: MAC(Manual Alarm Call point)는 사람이 직접 화재 경보를 발신하는 장치로, 유럽 기준은 EN 54-11 이 요구사항과 시험 방법을 다룹니다. 재래식(Conventional)과 주소형(Addressable)이 있어 FGS 패널 방식과 맞춰야 합니다. 위험지역에 설치되면 방폭 인증도 따로 확인해야 합니다. 설치 간격·높이는 공개 자료로 확인하지 못해 '미확인'입니다.
키워드: MAC, manual call point, 수동발신기, EN 54-11, conventional, addressable, break glass
부품: mac
출처: [BS EN 54-11 Manual call points (BSI)](https://knowledge.bsigroup.com/products/fire-detection-and-fire-alarm-systems-manual-call-points), [Manual call point EN54 (Honeywell)](https://buildings.honeywell.com/de/de/products/by-category/fire-life-safety/manual-call-points-pull-stations-and-panic-buttons/manual-call-point-pull-station-parts/manual-call-point-en54)

### Q: 경광등·사운더(Beacon/Sounder)는 무엇을 확인하나요?
A: 유럽 기준에서 사운더는 EN 54-3 이 다룹니다. 일반적으로 경보 종류(화재·가스·대피)별 색상과 음색을 철학서에서 구분하고, 소음이 큰 구역은 시각 경보를 보강합니다. 가청·시인 레벨, 색상 규칙은 이번 조사에서 확인하지 못했으므로 '미확인'이며 NFPA 72 나 프로젝트 기준으로 확정해야 합니다.
키워드: beacon, sounder, 경광등, 사이렌, EN 54-3, NFPA 72, visual alarm, audible alarm
부품: beacon
출처: [Search: EN 54 call point / sounder (Apollo AlarmSense)](https://apollo-fire.co.uk/products/alarmsense/mcp/55100-894apo-alarmsense-manual-call-point/)

### Q: 감지기 4-20 mA 신호에서 특수 전류값은 왜 중요한가요?
A: 많은 감지기는 4-20 mA 아래·위 대역으로 고장·교정·빔 차단 상태를 표현하고, 일부는 확정 화재를 특정 전류로 알리기도 합니다. 한 사례는 확정 화재를 19 mA 로 표현했습니다(출처 기준). FGS 패널 입력 설정이 이 대역을 정확히 구분하지 못하면 고장을 정상으로, 또는 교정을 경보로 오인할 수 있습니다. 기종별 전류표를 벤더 매뉴얼로 받아 패널 설정과 대조하세요.
키워드: 4-20mA, fault current, 19mA, 특수전류, status current, HART, 입력설정
부품: signal, fgs-panel, gas-detector, flame-detector
출처: [Moore Industries SLA Natural Gas Compressor Stations Case Study](https://www.miinet.com/images/pdf/casestudies/Moore_Industries_SLA_Natural_Gas_Compressor_Stations_Case_Study.pdf), [SafEye series 700 datasheet](https://www.heatingandprocess.com/wp-content/uploads/2016/03/SafEye-series-700-min.pdf)

## 표준
### Q: 가스 감지기 선정·설치에 참고하는 표준은 무엇인가요?
A: 자료들은 IEC 60079-29-2(가스 감지기 선정·설치·사용·유지보수), Open path 성능은 IEC 60079-29-4 를 언급합니다. 배치 판단에는 위험지역 구분(API 500, IEC 60079-10-1) 정보도 같이 씁니다. 표준 조항 번호와 세부 요구는 원문 확인 전까지 '미확인'입니다.
키워드: IEC 60079-29-2, IEC 60079-29-4, API 500, IEC 60079-10-1, 표준, standard, hazardous area
부품: gas-detector, op-gas
출처: [Gas Detector Location Standards (Industrial Monitor Direct)](https://industrialmonitordirect.com/blogs/knowledgebase/gas-detector-location-standards-flammable-toxic-gas-placement-guide), [IEC 60079-29-4 preview (ANSI)](https://webstore.ansi.org/preview-pages/IEC/preview_iec60079-29-4%7Bed1.0%7Db.pdf)

### Q: SIL 인증 부품을 쓰면 FGS 도 SIL 을 만족하나요?
A: 아닙니다. MSA 는 SIL 2 Logic solver·센서·최종요소를 사는 것만으로 SIL 2 시스템이 보장되지 않는다고 설명합니다. Emerson 도 감지기 배치가 잘못되면 하드웨어 SIL 과 관계없이 감지·대응 능력이 떨어진다고 지적합니다. 그래서 FGS 는 하드웨어 SIL 검증과 커버리지 검증을 함께 해야 합니다.
키워드: SIL certified, SIL 2, logic solver, PFD, coverage, SIL 검증, 인증부품
부품: fgs-panel, gas-detector, flame-detector
출처: [Can a Fire and Gas System Be Considered a SIS? (MSA)](https://blog.msasafety.com/can-a-fire-and-gas-system-be-considered-a-safety-instrumented-system/), [DeltaV SIS Fire & Gas capabilities white paper (Emerson)](https://www.emerson.com/documents/automation/white-paper-deltav-sis-fire-gas-capabilities-en-5292184.pdf)

## 시험
### Q: 가스 감지기 범프 테스트와 교정은 어떻게 다른가요?
A: 범프 테스트는 시험 가스를 짧게 흘려 감지기가 반응하고 경보가 나는지 확인하는 기능 점검이고, 교정은 기준 가스로 지시값을 맞추는 작업입니다. 촉매식은 피독되면 조용히 낮게 지시할 수 있어 범프 테스트로만 발견되는 경우가 있습니다. 두 방식 모두 교정 가스 외 가스에는 보정 계수가 필요합니다. 점검 주기는 제조사 매뉴얼·프로젝트 기준으로 확인('미확인')하세요.
키워드: bump test, calibration, 범프테스트, 교정, calibration gas, correlation factor, 점검주기
부품: gas-detector
출처: [Catalytic Bead vs Infrared LEL Sensors (WCSafety)](https://wcsafety.com/blogs/reference/catalytic-bead-vs-infrared-lel-sensors), [Sensor poisons and inhibitors (Industrial Scientific)](https://indsci.com/en/blog/what-you-need-to-know-about-sensor-poisons-and-inhibitors?hsLang=en)

### Q: FGS 시험·유지보수 사양은 언제 정하나요?
A: Kenexis 는 상세설계 단계에서 Safety availability 목표에 맞춰 유지보수·시험 사양을 같이 만들라고 권합니다. 시험 주기가 길어지면 Safety availability 가 떨어지기 때문입니다. 또 시험·교정 접근성이 설계에 반영되어야 하므로(높은 곳, 장비 뒤 등) 시공성·유지보수성 검토도 같은 시점에 합니다.
키워드: proof test, maintenance, safety availability, 시험주기, 유지보수, accessibility
부품: gas-detector, flame-detector, fgs-panel
출처: [Performance-Based Fire & Gas System Engineering (Kenexis)](https://www.kenexis.com/performance-based-fire-gas-system-fgs-engineering/)

## 자주 하는 실수
### Q: FGS 사양 검토 때 자주 놓치는 것은 무엇인가요?
A: ① 3D 모델 변경 후 맵핑 미갱신, ② 수소가 있는데 IR 가연성 감지기만 선정, ③ 실리콘·H2S 환경에 촉매식 사용, ④ Open path 빔 차단·저전류 상태 미처리, ⑤ 접근 불가 위치에 감지기 배치가 자주 지적됩니다. 커버리지 부족이 FGS 의 가장 큰 역사적 문제로 꼽힌다는 점을 기억하세요. 모두 프로젝트 Spec 대조 전 '미확인' 체크리스트입니다.
키워드: review checklist, 자주 하는 실수, coverage, hydrogen, poisoning, beam block, access
부품: gas-detector, op-gas, flame-detector
출처: [Performance-Based Fire & Gas System Engineering (Kenexis)](https://www.kenexis.com/performance-based-fire-gas-system-fgs-engineering/), [Catalytic Bead vs Infrared LEL Sensors (WCSafety)](https://wcsafety.com/blogs/reference/catalytic-bead-vs-infrared-lel-sensors)

### Q: 감지기 케이블과 설치 환경에서 주의할 점은?
A: 감지기는 열·습기·진동·기계적 스트레스로 성능과 수명이 줄어들므로 햇빛 차양·우천 보호를 하거나 그런 조건을 피해 설치하라는 권고가 있습니다. 제어 유닛(패널)은 위험지역 밖 안전한 곳에 두는 것이 권장됩니다. 케이블 사양(내화 케이블 여부 등)은 이번 조사에서 확인하지 못해 '미확인'이며 프로젝트 Spec 으로 확인해야 합니다.
키워드: cable, 케이블, environment, sunshade, weather, fire resistant cable, 패널 위치, safe area
부품: cable, gas-detector, fgs-panel
출처: [How to Place Gas Detectors (gasdetection.com)](https://gasdetection.com/articles/how-to-place-gas-detectors-for-optimal-safety-and-accuracy/)

### Q: 밀폐 공간이나 용기(Vessel) 주변은 어떻게 감지하나요?
A: 가스가 고일 수 있는 밀폐 공간 입구 근처에 감지기를 두라는 권고가 있습니다. 용기·장비 주변은 플랜지·노즐 같은 누출원 가까이, 기류 하류 쪽에 두고, 큰 장비 뒤 사각지대를 피해야 합니다. 구체 거리 기준은 공개 자료로 확인하지 못했으므로 '미확인'입니다.
키워드: confined space, vessel, 밀폐공간, 용기, nozzle, flange, blind spot, 사각지대
부품: vessel, gas-detector
출처: [How to Place Gas Detectors (gasdetection.com)](https://gasdetection.com/articles/how-to-place-gas-detectors-for-optimal-safety-and-accuracy/)

## MR 작성
### Q: 가스·화염 감지기 MR 에 넣어야 할 항목은 무엇인가요?
A: 감지 원리(촉매식/IR/Open path, UV/IR/IR3), 대상 가스와 교정 가스, 측정 범위, 출력(4-20 mA·HART·특수 전류표), 방폭·IP 등급, SIL 인증 여부, 감지 거리·시야각(화염), 교정·시험 키트와 액세서리(차양, 교정 캡)를 넣는 것이 일반적입니다. 경보 설정값과 Voting 은 FGS 철학서·C&E 를 참조하도록 하고, 확정 전에는 '미확인'으로 둡니다. 안전 계통 MR 이므로 초안이며 담당자 승인이 필요합니다.
키워드: MR, datasheet, detector specification, 교정가스, HART, Ex rating, SIL certificate, accessories
부품: gas-detector, op-gas, flame-detector
출처: [Searchline Excel Plus Open Path Gas Detector (Honeywell)](https://automation.honeywell.com/gb/en/products/gas-and-flame-detection/fixed-gas-and-flame-detection/fixed-gas-detectors/searchline-excel-plus-open-path-gas-detector), [X3301 Multispectrum IR Flame Detector datasheet](https://www.orrprotection.com/hubfs/Orrprotection_Docs_Feb2016/90-1144-4.1_X3301_Pulse-Multispectrum_IR_Flame_Det.pdf)

### Q: FGS 패널(Logic solver) MR 에서 확인할 것은?
A: Logic solver 의 SIL 능력, 인증(IEC 61508 등), 이중화, 입력 채널의 특수 전류 해석 기능, C&E 구현 방식, DCS·ESD 통신, 경보·이벤트 기록, FAT 범위를 확인합니다. 한 산업 블로그는 기능별 목표 SIL·PFD 범위를 제시하지만 출처 신뢰도가 낮아 IEC 61511 원문으로 검증해야 합니다. 화재경보 관련 인증(NFPA 72·EN 54) 필요 여부는 프로젝트 기준으로 확인('미확인')하세요.
키워드: FGS panel, logic solver, SIL capability, redundancy, 이중화, C&E, NFPA 72, EN 54, FAT
부품: fgs-panel
출처: [SIL-Rated vs Standard Fire Panels (Industrial Monitor Direct)](https://industrialmonitordirect.com/blogs/knowledgebase/sil-rated-vs-standard-fire-panels-pfd-sil-levels-differences), [DeltaV SIS Fire & Gas capabilities white paper (Emerson)](https://www.emerson.com/documents/automation/white-paper-deltav-sis-fire-gas-capabilities-en-5292184.pdf)

## 벤더 문서
### Q: FGS 관련 벤더·엔지니어링 문서는 무엇을 받아야 하나요?
A: 일반적으로 FGS 철학서, F&G 맵핑 보고서(Geographic/Scenario coverage), 감지기 배치도, C&E, 감지기 데이터시트·인증서(방폭·SIL), 설치·교정 매뉴얼, FAT/SAT 절차서가 필요합니다. 맵핑 보고서는 3D 모델 변경 시 개정되어야 하므로 Rev 관리가 중요합니다. 구체 목록은 프로젝트 VDRL 로 확정('미확인')하세요.
키워드: vendor document, VDRL, mapping report, C&E, certificate, manual, FAT, 벤더문서
부품: fgs-panel, gas-detector, flame-detector
출처: [Performance-Based Fire & Gas System Engineering (Kenexis)](https://www.kenexis.com/performance-based-fire-gas-system-fgs-engineering/), [Understanding Fire and Gas Mapping (Kenexis)](https://www.kenexis.com/wp-content/uploads/2014/05/UnderstandingFireAndGasMapping.pdf)
