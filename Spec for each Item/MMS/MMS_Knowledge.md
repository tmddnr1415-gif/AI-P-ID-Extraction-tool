# MMS Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: MMS(Machinery Monitoring System)는 뭘 하는 시스템인가요?
A: MMS는 터빈·압축기·대형 펌프 같은 회전기계의 축 진동, 축 변위(Thrust), 회전수, 베어링 온도 등을 감시해 위험 수준이면 기계를 Trip시키는 보호 시스템입니다. API 670이 이런 Machinery protection system의 최소 요구사항을 정합니다. 초안이며 적용 범위는 담당자 확인이 필요합니다(초안, 담당자 확인 필수).
키워드: MMS, machinery monitoring system, machinery protection system, MPS, API 670, 진동 감시, VMS
부품: shaft, probe, monitor-rack
출처: [Meggitt Sensing - General API 670 requirements](https://meggittsensing.com/?p=90376), [Fabrico - API 670 machinery protection](https://www.fabrico.io/blog/api-670-machinery-protection/)

### Q: Machinery protection과 Condition monitoring은 뭐가 다른가요?
A: Protection은 위험할 때 기계를 Trip시키는 기능이고, Condition monitoring은 추세를 분석해 문제를 미리 예측하는 기능입니다. 중요 기계는 보통 둘 다 쓰며, Condition monitoring 소프트웨어(예: System 1)는 보호 Rack과 같은 공급사 제품으로 따로 붙는 경우가 많습니다. API 670 범위는 Protection 쪽입니다(초안, 담당자 확인 필수).
키워드: protection, condition monitoring, CMS, System 1, 예지보전, trend, 진단
부품: monitor-rack
출처: [Fabrico - API 670 machinery protection](https://www.fabrico.io/blog/api-670-machinery-protection/), [Meggitt Sensing - Integrating a machinery protection platform](https://meggittsensing.com/energy/expert-articles/integrating-a-machinery-protection-platform-into-your-plantwide-ecosystem/)

### Q: MMS는 어떤 측정을 하나요?
A: 일반적으로 Eddy-current Proximity probe로 Radial 축 진동과 Axial 위치를 재고, 베어링 온도(RTD), 회전수·Overspeed, Keyphasor(위상 기준)를 측정합니다. 경우에 따라 Casing 진동(가속도·속도 센서)도 추가합니다. 실제 측정점은 기계 OEM의 Datasheet로 확정해야 합니다(초안, 담당자 확인 필수).
키워드: radial vibration, axial position, thrust, bearing temperature, speed, overspeed, keyphasor, casing vibration
부품: probe, probe-axial, keyphasor, rtd, bearing
출처: [Oxmaint - API 670 Vibration Monitoring](https://oxmaint.com/industries/steel-plant/api-670-vibration-monitoring-steel-plants), [Meggitt Sensing - General API 670 requirements](https://meggittsensing.com/?p=90376)

## 설계
### Q: Radial 진동 Probe는 왜 두 개를 90도로 다나요?
A: X·Y 두 Probe가 서로 직각이어야 축 궤적(Orbit)을 그리고 실제 최대 진폭(Smax)을 계산할 수 있기 때문입니다. 유막 베어링을 쓰는 중요 기계는 베어링마다 XY Probe가 필요하다는 것이 Bently Nevada ORBIT의 설명입니다. 직각이 아니면 X·Y 측정이 독립되지 않아 Orbit이 왜곡됩니다(초안, 담당자 확인 필수).
키워드: XY probe, 90 degree, orbit, Smax, radial vibration, fluid film bearing, 직각 설치
부품: probe, bearing, shaft
출처: [Turbomachinery Magazine - Single plane or XY probes](https://turbomachinerymag.com/view/should-i-install-single-plane-or-xy-proximity-probes), [Baker Hughes ORBIT v30n1](https://bakerhughes.com/sites/bakerhughes/files/2022-01/orbit_v30n1_2010_q4.pdf)

### Q: Probe를 수직·수평이 아니라 45도로 다는 이유는?
A: 베어링 케이스가 수평 분할돼 있거나 배관 간섭 때문에 진짜 수직·수평 위치를 못 쓰는 경우가 많아서 상단 또는 하단 기준 45도에 답니다. 이때도 두 Probe 간격은 90도를 유지해야 하고, 화면에서 회전 보정해 수직·수평으로 볼 수 있습니다. 설치 각도와 방향(회전 방향 기준 X/Y 명명)은 도면에 명시하세요(초안, 담당자 확인 필수).
키워드: 45 degree, probe orientation, split bearing, rotation correction, 설치 각도
부품: probe, bearing
출처: [Prosig - Importance of Transducer Orientation](https://blog.prosig.com/2012/03/20/understanding-the-importance-of-transducer-orientation/), [Turbomachinery Magazine - Single plane or XY probes](https://turbomachinerymag.com/view/should-i-install-single-plane-or-xy-proximity-probes)

### Q: Axial(Thrust) 위치 감시는 왜 중요한가요?
A: Thrust 베어링이 마모되면 축이 축 방향으로 밀려 금속끼리 접촉하기 전에 잡아야 하기 때문입니다. Emerson 자료는 Overspeed 다음으로 Thrust가 가장 중요한 보호 측정이라고 설명합니다. Probe 수와 위치는 공개 자료에서 일반 규칙을 확인하지 못해 미확인이며 OEM 문서로 확인해야 합니다(초안, 담당자 확인 필수).
키워드: axial position, thrust position, thrust bearing wear, 축 변위, probe-axial
부품: probe-axial, bearing, shaft
출처: [Fabrico - API 670 machinery protection](https://www.fabrico.io/blog/api-670-machinery-protection/), [Reliabilityweb - Emerson CSI 6500](https://reliabilityweb.com/news/article/emersons_csi_6500_machinery_health_monitor_combines_vibration_and_temperatu)

### Q: Trip Voting은 보통 어떻게 하나요?
A: 센서 하나 고장으로 기계가 불필요하게 서지 않도록 여러 채널이 동의해야 Trip하는 Voting을 쓰며, 2oo3가 흔하다고 공개 자료는 설명합니다. 2개 Probe만 있는 측정(예: Thrust 2점)은 2oo2나 Thrust 베어링 온도를 보조로 써서 신뢰도를 높이는 방법이 소개됩니다. 최종 Voting은 기계 보호 철학과 C&E로 확정합니다(초안, 담당자 확인 필수).
키워드: voting, 2oo3, 2oo2, trip logic, spurious trip, 오동작
부품: probe, probe-axial, monitor-rack
출처: [Fabrico - API 670 machinery protection](https://www.fabrico.io/blog/api-670-machinery-protection/), [Reliabilityweb - Emerson CSI 6500](https://reliabilityweb.com/news/article/emersons_csi_6500_machinery_health_monitor_combines_vibration_and_temperatu)

### Q: Alert와 Danger 설정값은 어떻게 구분하나요?
A: 각 측정 Tag에 Alert(경보, High)와 Danger(Trip, High-High) 두 단계 설정값을 두고, Danger는 Relay를 통해 Trip을 냅니다. 한 벤더 페이지는 별도 Alarm·Danger 설정과 Time delay를 요구한다고 쓰지만, 구체 수치(Time delay 등)는 단일 2차 출처라 미확인으로 둡니다. 설정값은 기계 OEM 권고값을 따릅니다(초안, 담당자 확인 필수).
키워드: alert, danger, setpoint, time delay, high high, 경보, 트립 설정
부품: monitor-rack
출처: [instrumentationtools - Bently Nevada 3500 Hardware Modules](https://instrumentationtools.com/bently-nevada-3500-machinery-protection-systems-hardware-modules/amp/), [Oxmaint - API 670 Vibration Monitoring](https://oxmaint.com/industries/steel-plant/api-670-vibration-monitoring-steel-plants)

### Q: Keyphasor는 뭘 하는 센서인가요?
A: Keyphasor는 축의 Notch나 Key를 1회전에 1번 감지하는 Proximity probe로, 회전수를 계산하고 진동 신호의 위상 기준을 줍니다. 3500 Rack에서는 Keyphasor 모듈이 이 신호를 받아 Backplane으로 각 Monitor 모듈에 보냅니다. 회전당 펄스 수는 회전체의 Notch 수에 따릅니다(초안, 담당자 확인 필수).
키워드: keyphasor, phase reference, once per turn, notch, speed, 위상
부품: keyphasor, shaft, monitor-rack
출처: [instrumentationtools - Bently Nevada 3500 Hardware Modules](https://instrumentationtools.com/bently-nevada-3500-machinery-protection-systems-hardware-modules/amp/), [Instrumart - 3500 System Datasheet](https://core.instrumart.com/assets/3500-System-Datasheet.pdf)

### Q: 베어링 온도는 RTD와 열전대 중 뭘 쓰나요?
A: 한 센서 공급사는 정확도와 장기 안정성 때문에 베어링 온도에 Pt100 Class A RTD를 선호한다고 설명합니다(벤더 선호이며 표준 요구는 미확인). 저널 베어링 온도는 Radial 진동이 보여주는 Rub·윤활 문제를 확인하는 보조 지표로 쓰입니다. 2oo3 온도 Trip을 쓰면 세 Tag를 서로 다른 모듈에 넣는 사례가 있습니다(초안, 담당자 확인 필수).
키워드: bearing temperature, RTD, Pt100, thermocouple, journal bearing, thrust pad, 베어링 온도
부품: rtd, bearing, monitor-rack
출처: [Thermometrics - Bearing RTD](https://thermometricscorp.com/brtd-bearing-rtd.html), [Reliabilityweb - Emerson CSI 6500](https://reliabilityweb.com/news/article/emersons_csi_6500_machinery_health_monitor_combines_vibration_and_temperatu), [instrumentationtools - Bently Nevada 3500 Hardware Modules](https://instrumentationtools.com/bently-nevada-3500-machinery-protection-systems-hardware-modules/amp/)

### Q: Overspeed 보호는 진동 Rack과 같이 써도 되나요?
A: 공개 요약에 따르면 API 670의 전자식 Overspeed 검출 시스템은 3개의 독립 측정 회로와 2oo3 Voting으로 구성하고, 다른 감시·보호 시스템과 격리되어 부품을 공유하지 않아야 합니다(출처 기준). 따라서 일반 진동 Rack과 별도 Overspeed 전용 장치를 두는 경우가 많습니다. 원문 조항은 미확인이며 API 670 현행판으로 확인해야 합니다(초안, 담당자 확인 필수).
키워드: overspeed, ODS, overspeed detection system, 2oo3, independent, 과속 보호
부품: keyphasor, shaft, monitor-rack
출처: [Istec - API 670 overspeed detection systems](https://istec.com/what-does-api-standard-670-state-about-overspeed-protection-systems/), [Meggitt - ODS301 product overview](https://meggittsensing.com/wp-content/uploads/ODS301_product_overview.pdf)

### Q: Overspeed 응답 시간은 얼마로 보나요?
A: 공개 요약은 API 670이 Overspeed 검출부터 Relay 출력 전환까지 최대 40 ms를 허용한다고 설명합니다(출처 기준). 다만 이 시간은 검출과 Relay만이고, 실제 전체 응답에는 유압 계통과 Trip valve 닫힘 시간이 더해집니다. 회전체 가속이 빠르면 40 ms로도 부족할 수 있다는 지적이 있어 전체 응답 시간을 계산해야 합니다(초안, 담당자 확인 필수).
키워드: overspeed response time, 40 ms, trip valve, hydraulic, 응답시간
부품: monitor-rack
출처: [Istec - API 670 overspeed detection systems](https://istec.com/what-does-api-standard-670-state-about-overspeed-protection-systems/), [Operations Engineer - Preventing overspeeds](https://www.operationsengineer.org.uk/content/news/preventing-overspeeds)

### Q: Overspeed Trip 설정은 보통 어디쯤인가요?
A: 한 공개 자료는 일반 지침으로 정격 속도 110~112% 이전 검출, 120% 미만으로 속도 제한을 제시하지만 설정값은 터빈 제조사·모델별이라고 명시합니다(출처 기준). 그래서 MMS 측에서 임의로 정하지 말고 터빈 OEM 값을 받아야 합니다. 프로젝트 값은 미확인입니다(초안, 담당자 확인 필수).
키워드: overspeed setpoint, 110%, rated speed, turbine OEM, 과속 설정
부품: shaft
출처: [Operations Engineer - Preventing overspeeds](https://www.operationsengineer.org.uk/content/news/preventing-overspeeds)

## 센서·케이블
### Q: Proximity probe 시스템은 어떻게 구성되나요?
A: Probe(팁+일체형 케이블), Extension cable, Proximitor(Driver)로 이루어진 하나의 Transducer system입니다. Probe 길이와 Extension cable 길이 합이 Driver 정격 시스템 길이(일반적으로 5 m 또는 9 m)와 맞아야 합니다(출처 기준). 맞게 구성되면 커넥터 양쪽 색 띠가 일치한다고 Rockwell 자료는 설명합니다(초안, 담당자 확인 필수).
키워드: proximity probe, proximitor, driver, extension cable, system length, 5 m, 9 m, transducer system
부품: probe, cable
출처: [Rockwell - 1442 Series datasheet](https://literature.rockwellautomation.com/idc/groups/literature/documents/td/1442-td001_-en-p.pdf), [Metrix - Extension cables](https://www.metrixvibration.com/products/proximity/cables/)

### Q: Extension cable 길이를 현장에서 잘라 맞춰도 되나요?
A: 안 됩니다. 시스템 길이는 전기적 길이로 맞춰진 것이라 Probe와 Extension cable의 전기적 길이 합이 Proximitor 전기적 길이와 같아야 합니다. 임의로 자르거나 다른 계열 부품을 섞으면 정확도가 떨어지는데, Bently는 XL과 비XL 부품을 섞으면 성능이 비XL 사양으로 제한된다고 안내합니다(초안, 담당자 확인 필수).
키워드: cable length, electrical length, mixing components, 3300 XL, 케이블 절단
부품: cable, probe
출처: [Instrumart - Bently Nevada 3300 5mm Proximity Probe](https://www.instrumart.com/products/47013/bently-nevada-3300-5mm-proximity-probe), [Metrix - Extension cables](https://www.metrixvibration.com/products/proximity/cables/)

### Q: Probe Scale factor는 얼마인가요?
A: 3300 XL 8 mm 시스템 Datasheet는 7.87 V/mm(200 mV/mil) ±5%(5 m 시스템)를 제시합니다(출처 기준). 3500/40M Monitor는 100 mV/mil 또는 200 mV/mil 감도를 선택하도록 되어 있어 Probe 시스템과 Monitor 설정이 일치해야 합니다(출처 기준). 다른 제조사·모델은 값이 다르므로 Datasheet 확인이 필요합니다(초안, 담당자 확인 필수).
키워드: scale factor, sensitivity, 200 mV/mil, 7.87 V/mm, 3300 XL, 3500/40M, 감도
부품: probe, monitor-rack
출처: [Scribd - 3300 XL 8mm datasheet](https://www.scribd.com/document/384673119/3300xl-8mm-pdf), [ManualMachine - 3500/40M specifications](https://manualmachine.com/ge/350040m/21362638-specifications)

### Q: Gap voltage는 어떻게 맞추나요?
A: Probe는 선형 구간 안에서만 유효하므로 설치 시 선형 구간 중앙 근처의 Gap voltage로 맞춥니다. 포럼·실무 자료는 -24 V 공급 기준 약 -10~-11 V, 또는 -8~-12 V 범위를 경험칙으로 제시합니다(출처 기준, 비공식). 3300 XL 8 mm는 선형 범위 0.25~2.0 mm로 소개되며, 정확한 값은 기계 설치 절차서를 따릅니다(초안, 담당자 확인 필수).
키워드: gap voltage, linear range, -10 V, probe gap, 설치 간극, -24 V
부품: probe, probe-axial
출처: [CR4 GlobalSpec - Vibration Gap Voltage](https://cr4.globalspec.com/thread/126832/Vibration-Gap-Voltage), [automationforum - Functional testing of Bently Nevada probes](https://automationforum.co/functional-testing-of-bently-nevada-vibration-probes/)

### Q: Proximitor 공급 전압은 얼마인가요?
A: 3300 5 mm 시스템 Datasheet는 -17.5~-26 VDC, 최대 12 mA를 제시하고, -23.5 VDC보다 양(+)쪽 전압에서는 선형 범위가 줄 수 있다고 경고합니다(출처 기준). 그래서 Monitor Rack이 공급하는 -24 V 계통을 그대로 쓰는 것이 일반적입니다. 다른 모델 값은 미확인입니다(초안, 담당자 확인 필수).
키워드: supply voltage, -24 VDC, proximitor power, 공급 전압
부품: probe, monitor-rack
출처: [Protective Supplies - 3300 5mm transducer datasheet](https://www.protectivesupplies.com/datasheets/0_3300_5mm_transducer_system_datasheet_english.pdf)

## Monitor Rack
### Q: 3500 같은 Monitor Rack은 어떤 모듈로 구성되나요?
A: 전원 모듈, Rack Interface(TDI), Keyphasor 모듈, Proximitor Monitor(4채널), 온도 Monitor, Relay 모듈, 통신 Gateway로 구성됩니다. TDI는 전원 옆 전용 슬롯에 들어가 Rack 설정과 데이터 수집을 담당하고, 나머지 슬롯에 Monitor·Relay·Keyphasor·Gateway를 넣습니다. 슬롯 수와 배치는 제조사 매뉴얼로 확인하세요(초안, 담당자 확인 필수).
키워드: 3500 rack, TDI, rack interface, proximitor monitor, relay module, gateway, monitor rack
부품: monitor-rack
출처: [instrumentationtools - Bently Nevada 3500 Hardware Modules](https://instrumentationtools.com/bently-nevada-3500-machinery-protection-systems-hardware-modules/amp/), [Instrumart - 3500 System Datasheet](https://core.instrumart.com/assets/3500-System-Datasheet.pdf)

### Q: Monitor Rack 전원은 이중화하나요?
A: 일반적으로 이중화합니다. 3500/15 전원은 반높이 모듈 두 개를 위아래로 꽂아 하나만으로도 Rack 전체를 구동할 수 있고, 하나를 교체하는 동안 다른 하나가 운전을 유지합니다. 입력은 AC 85~264 V, 고전압 DC 88~140 V, 저전압 DC 20~30 V 옵션이 소개됩니다(출처 기준). 공급 Feeder도 A/B로 분리되는지 확인하세요(초안, 담당자 확인 필수).
키워드: rack power supply, redundant PSU, 3500/15, 이중화 전원, AC/DC input
부품: monitor-rack
출처: [instrumentationtools - Bently Nevada 3500 Hardware Modules](https://instrumentationtools.com/bently-nevada-3500-machinery-protection-systems-hardware-modules/amp/), [Meggitt Sensing - General API 670 requirements](https://meggittsensing.com/?p=90376)

### Q: Rack OK(System fault) Relay는 뭔가요?
A: Rack 내 모듈이나 Transducer에 Not OK 상태가 생기면 동작하는 공통 고장 Relay입니다. 3500에서는 TDI I/O 모듈에 있고 다른 모듈의 Not OK 조건이 함께 구동합니다. 공개 요약상 API 670은 Monitor마다 공통 회로 고장 Relay를 언급하며, 이 신호는 DCS 알람으로 보내는 게 일반적입니다(초안, 담당자 확인 필수).
키워드: rack OK relay, not OK, circuit fault relay, system fault, 고장 경보
부품: monitor-rack
출처: [Instrumart - 3500 System Datasheet](https://core.instrumart.com/assets/3500-System-Datasheet.pdf), [Vibsens - API 670 compliance](https://vibsens.com/index.php/knowledge-base/api670-compliance)

## Interface
### Q: MMS Trip 신호는 ESD·CCS로 어떻게 보내나요?
A: Trip 신호는 통신이 아니라 Hardwired Relay 접점으로 보내는 것이 여전히 좋은 엔지니어링 관행으로 여겨집니다. Relay는 평상시 여자(Energized)되어 있다가 Trip이나 전원 상실 시 소자되는 Fail-safe 배선이 소개됩니다. 디지털 Trip 경로는 Gateway가 고장점이 될 수 있다는 점이 지적됩니다(초안, 담당자 확인 필수).
키워드: trip relay, hardwired trip, fail-safe relay, MMS ESD interface, CCS, de-energize
부품: monitor-rack, cable
출처: [Meggitt Sensing - Integrating a machinery protection platform](https://meggittsensing.com/energy/expert-articles/integrating-a-machinery-protection-platform-into-your-plantwide-ecosystem/)

### Q: MMS 값을 DCS에 보여주려면 어떻게 하나요?
A: 운전원 감시용 데이터는 Modbus(Serial/TCP)나 Profibus 통신, 또는 측정값별 4-20 mA 출력으로 DCS에 보냅니다. 이 통신은 자동 정지에는 쓰지 않는다는 전제입니다. 3500 Gateway는 Modbus RTU·Modbus/TCP와 제조사 프로토콜을 지원하는 것으로 소개됩니다(초안, 담당자 확인 필수).
키워드: Modbus, 4-20 mA, recorder output, DCS interface, gateway, Profibus
부품: monitor-rack, network
출처: [Meggitt Sensing - Integrating a machinery protection platform](https://meggittsensing.com/energy/expert-articles/integrating-a-machinery-protection-platform-into-your-plantwide-ecosystem/), [instrumentationtools - Bently Nevada 3500 Hardware Modules](https://instrumentationtools.com/bently-nevada-3500-machinery-protection-systems-hardware-modules/amp/)

### Q: Condition monitoring 소프트웨어는 어떻게 연결하나요?
A: 3500 TDI는 동선·광 Ethernet으로 Condition monitoring 소프트웨어(System 1)와 Rack 설정 소프트웨어에 연결됩니다. TDI의 RUN/PROGRAM 키로 설정 변경 가능 여부를 통제하므로 운전 중 설정 변경 권한을 관리할 수 있습니다. 서버·라이선스 범위는 MR에서 정해야 하며 현재 미확인입니다(초안, 담당자 확인 필수).
키워드: System 1, condition monitoring, TDI, Ethernet, configuration software, RUN PROGRAM key
부품: monitor-rack, network
출처: [instrumentationtools - Bently Nevada 3500 Hardware Modules](https://instrumentationtools.com/bently-nevada-3500-machinery-protection-systems-hardware-modules/amp/)

### Q: MMS는 기계 Package 범위인가요, I&C 범위인가요?
A: 프로젝트마다 다르며 공개 자료로는 확정할 수 없습니다(미확인). 다만 Probe·Proximitor는 기계 OEM이 설치하고 Monitor rack은 Package 또는 별도 MMS 공급사가 공급하는 형태가 흔하므로, Scope split과 Interface 책임을 Interface 매트릭스에 명확히 적어야 합니다. 보호 루프는 Hardwired, 제어·감시 시스템과 분리가 원칙이라는 점은 공통입니다(초안, 담당자 확인 필수).
키워드: scope split, package, OEM, interface responsibility, 범위 분담
부품: probe, monitor-rack, cable
출처: [Meggitt Sensing - General API 670 requirements](https://meggittsensing.com/?p=90376), [Meggitt Sensing - Integrating a machinery protection platform](https://meggittsensing.com/energy/expert-articles/integrating-a-machinery-protection-platform-into-your-plantwide-ecosystem/)

## 시험
### Q: Proximity probe 기능 시험은 어떻게 하나요?
A: 일반적으로 교정 장치에 Probe와 대상 재질을 고정하고 간극을 단계별로 바꿔가며 출력 전압을 재 Scale factor와 선형성을 확인합니다(장치 종류는 미확인). 설치 후에는 Gap voltage와 Monitor 지시를 확인하고, 설정값으로 Alert·Danger Relay 동작을 시험합니다. 시험 절차 세부는 제조사 매뉴얼을 따릅니다(초안, 담당자 확인 필수).
키워드: probe calibration, functional test, scale factor test, linearity, relay test, loop test
부품: probe, monitor-rack
출처: [automationforum - Functional testing of Bently Nevada probes](https://automationforum.co/functional-testing-of-bently-nevada-vibration-probes/)

### Q: 한 Probe의 Gap voltage가 계속 변하면 뭘 의심하나요?
A: Gap이 서서히 변하면 실제 축 위치 변화(베어링 마모, 열팽창)일 수도 있고 Probe·케이블·커넥터 문제일 수도 있어 둘을 구분해야 합니다. 같은 베어링의 다른 Probe, 베어링 온도, Thrust 위치와 비교하면 판단에 도움이 됩니다. 원인 판정은 기계 담당자와 함께 하세요(초안, 담당자 확인 필수).
키워드: gap voltage drift, probe fault, bearing wear, 진단, troubleshooting
부품: probe, cable, bearing
출처: [Control.com - DC gap voltage increase of radial probe](https://control.com/forums/threads/steady-increase-in-dc-gap-voltage-of-one-of-two-radial-vibration-probes.37907/)

## 사양 검토 유의사항
### Q: MMS 사양 검토 때 중점 항목은?
A: API 670 적용판과 준수 범위, 측정점 목록(Radial XY·Axial·Keyphasor·RTD·Speed), Probe 시스템 길이·모델 통일, Voting과 Alert/Danger·Time delay, Overspeed 독립성, 전원 이중화, Relay Fail-safe, DCS 통신·4-20 mA, Condition monitoring 범위를 봅니다. 3300 XL 8 mm 5 m 시스템처럼 벤더가 API 670 준수를 주장하면 해당 판(Edition)과 항목을 확인하세요(초안, 담당자 확인 필수).
키워드: MMS review, API 670 compliance, checklist, 검토 항목, edition
부품: probe, probe-axial, keyphasor, rtd, cable, monitor-rack
출처: [Instrumart - Bently Nevada 3300 5mm Proximity Probe](https://www.instrumart.com/products/47013/bently-nevada-3300-5mm-proximity-probe), [Meggitt Sensing - General API 670 requirements](https://meggittsensing.com/?p=90376)

## MR 작성
### Q: MMS MR에는 무엇을 적나요?
A: 기계별 측정점 목록과 Probe·Proximitor·Extension cable 모델·시스템 길이, Monitor rack 구성(채널 수, Spare 슬롯), 전원 입력·이중화, Relay 수와 Fail-safe 방식, Overspeed 장치, 통신(Modbus 등)·4-20 mA, Condition monitoring 소프트웨어·서버 범위, FAT 범위를 적습니다. 수치는 기계 OEM Datasheet와 프로젝트 Spec 대조 전까지 미확인입니다(초안, 담당자 확인 필수).
키워드: MMS MR, material requisition, measurement list, probe model, rack configuration, 자재 구매
부품: probe, probe-axial, keyphasor, rtd, cable, monitor-rack
출처: [Instrumart - 3500 System Datasheet](https://core.instrumart.com/assets/3500-System-Datasheet.pdf), [Rockwell - 1442 Series datasheet](https://literature.rockwellautomation.com/idc/groups/literature/documents/td/1442-td001_-en-p.pdf)

## 자주 하는 실수
### Q: MMS 검토에서 자주 하는 실수는?
A: (1) Probe·Extension cable·Proximitor 길이·계열 불일치, (2) Monitor 감도 설정과 Probe Scale factor 불일치, (3) Overspeed를 일반 진동 Rack과 공유, (4) Trip을 통신으로만 전달, (5) XY Probe 직각·방향 표기 누락이 흔합니다. 각 항목은 위 출처의 일반 권고 기준입니다(초안, 담당자 확인 필수).
키워드: 자주 하는 실수, pitfall, cable length mismatch, scale factor mismatch, overspeed sharing, comm trip
부품: probe, cable, keyphasor, monitor-rack
출처: [Metrix - Extension cables](https://www.metrixvibration.com/products/proximity/cables/), [Istec - API 670 overspeed detection systems](https://istec.com/what-does-api-standard-670-state-about-overspeed-protection-systems/), [Meggitt Sensing - Integrating a machinery protection platform](https://meggittsensing.com/energy/expert-articles/integrating-a-machinery-protection-platform-into-your-plantwide-ecosystem/)
