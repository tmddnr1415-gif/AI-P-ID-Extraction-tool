# IPS Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: IPS는 SIS, ESD랑 같은 건가요?
A: IPS(Instrumented Protective System)는 회사마다 부르는 이름이 다를 뿐 SIS(Safety Instrumented System)와 같은 계층이고, ESD·PSD는 그 안에서 차단 범위에 따라 나눈 기능입니다. 즉 센서 → Logic solver → Final element(차단밸브·Motor trip)로 이루어진 SIF(Safety Instrumented Function)들의 집합입니다. 초안이며 회사 정의는 담당자 확인이 필요합니다.
키워드: IPS, SIS, ESD, PSD, SIF, safety instrumented system, emergency shutdown
부품: controller, io, esd-pb
출처: [Skill-Lync - Emergency Shutdown System](https://resources.skill-lync.com/branches/chemical-engineering/questions/process-design/emergency-shutdown-system), [Industrial Monitor Direct - Configuring ESD and PSD](https://industrialmonitordirect.com/blogs/knowledgebase/configuring-esd-and-psd-functions-for-process-safety)

### Q: SIL은 뭐고 IPS 설계에 어떻게 반영되나요?
A: SIL(Safety Integrity Level)은 SIF가 요구되는 위험 감소를 얼마나 신뢰성 있게 해내야 하는지를 나타내는 등급입니다. SIL 검증은 PFDavg(저요구 모드) 계산 하나만이 아니라 Systematic capability와 하드웨어 고장 허용도(HFT, 구조 제약)까지 세 가지를 만족해야 한다고 exida는 설명합니다. 초안이며 SIL 목표값은 프로젝트 SIL study 결과로 확인해야 합니다.
키워드: SIL, safety integrity level, PFDavg, PFH, systematic capability, HFT, SIL verification
부품: controller
출처: [exida - SIL verification beyond PFDavg/PFH](https://www.exida.com/Blog/sil-verification-beyond-pfdavg-pfh), [Consiltant - SIL verification](https://www.consiltant.com/?p=251)

### Q: PFDavg는 어떻게 계산하나요?
A: SIF를 센서, Logic solver, Final element 서브시스템으로 나눠 각각 PFDavg를 구하고 합산합니다. 센서와 Final element의 공통원인고장(CCF)도 계산에 넣어야 합니다. 대개 Final element가 가장 큰 비중을 차지하므로 Logic solver만 SIL 3 인증받았다고 SIF 전체가 SIL 3가 되는 건 아닙니다(초안, 담당자 확인 필수).
키워드: PFDavg, PFD calculation, common cause failure, CCF, beta factor, 서브시스템
부품: controller, io
출처: [Consiltant - SIL verification](https://www.consiltant.com/?p=251), [exida - SIF Verification Three Barriers](https://www.exida.com/Resources/Whitepapers/safety-instrumented-function-verification-the-three-barriers)

### Q: HFT(하드웨어 고장 허용도)는 무엇인가요?
A: HFT는 서브시스템이 몇 개의 고장까지 견디고도 안전 기능을 수행하는지입니다. HFT 0은 단일 채널, HFT 1은 1oo2나 2oo3처럼 한 채널이 고장나도 기능이 유지되는 구조입니다. 한 학습 자료는 IEC 61511-1:2018 기준 SIL 1·SIL 2(저요구)는 HFT 0, SIL 2 고요구·연속은 HFT 1로 요약하지만 2차 자료이므로 원문 대조가 필요합니다(초안, 담당자 확인 필수).
키워드: HFT, hardware fault tolerance, 1oo2, 2oo3, architectural constraint, 구조 제약
부품: controller, io
출처: [instrumentationtools - SIS Hardware Fault Tolerance](https://instrumentationtools.com/sis-hardware-fault-tolerance), [Open Exam Prep - SIS Design Constraints](https://open-exam-prep.com/study-guides/pe-control-systems/sis-design-sil/sis-design-constraints), [NTNU - SIS Book Ch2](https://jvatn.folk.ntnu.no/eLearning/PK6032/pdf/Ch2-SISBook.pdf)

## 설계
### Q: 1oo2, 2oo2, 2oo3 Voting은 뭘 기준으로 고르나요?
A: 1oo2는 둘 중 하나만 Trip해도 동작해 안전성 쪽, 2oo2는 둘 다 Trip해야 동작해 오동작(Spurious trip) 방지 쪽이고, 2oo3는 그 중간으로 안전성과 가용성을 함께 챙깁니다. 그래서 Trip 손실이 큰 대형 설비 센서는 2oo3를 많이 씁니다. 최종 Voting은 SIL 계산과 공정 가용성 요구로 정해야 합니다(초안, 담당자 확인 필수).
키워드: voting, 1oo2, 2oo2, 2oo3, spurious trip, 오동작, availability
부품: io, controller
출처: [Control.com - TMR and 2oo3](https://control.com/forums/threads/tmr-and-2oo3.31106/post-31106), [instrumentationtools - Voting Logic in SIS](https://instrumentationtools.com/voting-logic-safety-instrumented-system)

### Q: TMR Logic solver는 어떤 구조인가요?
A: TMR(Triple Modular Redundant)은 서로 격리된 3개 채널이 병렬로 연산하고 2oo3로 출력을 결정해 단일 고장점이 없게 한 구조입니다. Schneider(Triconex)는 TMR을 특정 기술이 아니라 아키텍처라고 설명합니다. 대신 3중 처리로 일반 PLC보다 Scan time이 느릴 수 있다는 지적이 있습니다.
키워드: TMR, triple modular redundant, Triconex, 2oo3, logic solver, scan time
부품: controller, io
출처: [Schneider Electric Blog - Why 3 is safety's magic number](https://blog.se.com/industry/machine-and-process-management/2022/09/13/why-the-number-3-is-safetys-magic-number/), [automationforum - What is a Triconex PLC](https://automationforum.co/difference-between-triconex-plc-and-other-plcs/)

### Q: IPS Logic solver의 이중화·I/O 요구는 보통 어떻게 쓰나요?
A: 한 DCS/ESD 기술평가 기준 예시는 ESD를 DCS와 독립된 SIL 3 이상 시스템으로 두고, Controller·전원·통신·I/O 모두 이중화, I/O 카드 Hot-swap을 요구합니다(출처 기준). 같은 자료는 ESD Scan time을 TMR 약 100 ms, QMR 약 250 ms로 둡니다(출처 기준). 프로젝트 Spec 값은 미확인입니다(초안, 담당자 확인 필수).
키워드: ESD redundancy, SIL 3, hot swap, scan time, QMR, TMR, I/O redundancy
부품: controller, io, psu, network
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system)

### Q: De-energize to trip(DET)과 Energize to trip(ETT)은 어떻게 선택하나요?
A: 전통적으로 SIF는 DET가 기본이고, 실제 ESD·PSD 대부분이 DET로 구현된다는 실무 의견이 많습니다. DET는 스프링 같은 저장 에너지로 안전 상태로 가므로 전원 상실 시에도 안전하지만 오동작이 늘 수 있습니다. ETT는 불필요한 정지가 매우 해로운 경우 쓰이며, 이때는 전원 상실 알람과 회로 감시가 필요하고 SRS에 장치별 DET/ETT를 기록해야 합니다(초안, 담당자 확인 필수).
키워드: de-energize to trip, DET, energize to trip, ETT, fail-safe, line monitoring, 전원상실
부품: io, psu
출처: [Kenexis - DET vs ETT](https://www.kenexis.com/?p=24577), [Emerson Exchange - Energize to Trip SIFs](https://emersonexchange365.com/products/control-safety-systems/f/deltav-discussions-questions/5359/energize-to-trip-ett-sifs)

### Q: IPS는 왜 DCS와 독립돼야 하나요?
A: BPCS 고장이 동시에 SIS를 무력화하면 보호층 두 개가 한 번에 사라지기 때문입니다. 공개 자료가 인용하는 IEC 61511-1 문구는 BPCS를 SIS 기능 무결성이 손상되지 않을 정도로 분리·독립하도록 요구합니다(조항 번호는 원문 대조 필요). 통합 플랫폼도 가능하다는 벤더 입장이 있지만, 공통원인 분석·런타임 분리·조직 분리 근거를 문서로 남겨야 합니다(초안, 담당자 확인 필수).
키워드: independence, BPCS SIS separation, 독립성, common cause, integrated platform, IPL
부품: controller, network
출처: [ProcessOnline - Integrating control and safety](https://www.processonline.com.au/content/safety/article/integrating-control-and-safety-where-to-draw-the-line-608324800), [exida - Common Cause for BPCS Shared Components](https://www.exida.com/Webinars/Recordings/assessing-common-cause-for-bpcs-shared-components), [61508 Association - Combined BPCS/SIS](https://61508.org/wp-content/uploads/2023/11/Intro-Combined-BPCS-SIS-V2_.pdf)

### Q: 센서를 DCS와 IPS가 같이 써도 되나요?
A: 공유하면 그 센서 고장이 제어 이상(초기 사건)과 보호 실패를 동시에 일으킬 수 있어 독립 보호층으로 인정받기 어렵습니다. 그래서 일반적으로 IPS 전용 트랜스미터를 따로 두고, 공유가 불가피하면 공통원인 평가로 근거를 남깁니다. 초안이며 프로젝트 SIL study 결론을 확인해야 합니다(초안, 담당자 확인 필수).
키워드: shared sensor, 센서 공유, IPL, common cause, independent protection layer, LOPA
부품: io
출처: [Control Global - Independent protection layer issues](https://www.controlglobal.com/protect/safety-instrumented-systems/article/11382841/independent-protection-layer-issues-offer-second-front), [exida - Common Cause for BPCS Shared Components](https://www.exida.com/Webinars/Recordings/assessing-common-cause-for-bpcs-shared-components)

### Q: ESD Push Button은 어떻게 배선하나요?
A: 수동 ESD 스위치는 Logic solver 입력으로 넣거나 Logic solver와 병렬로 Hardwired 차단 회로를 구성하며, 24 VDC NC 접점을 흔히 씁니다(출처 기준). Logic solver가 멈춰도 동작하도록 Hardwired 백업을 두라는 실무 권고가 많습니다. 한 IEEE 연구는 수동 ESD는 기술과 무관하게 SIL 1 수준이라고 보고합니다(초안, 담당자 확인 필수).
키워드: ESD push button, manual shutdown, hardwired, NC contact, 24VDC, 수동 정지, ESD PB
부품: esd-pb, io
출처: [Control.com - Safety systems manual shutdown](https://control.com/forums/threads/safety-systems-manual-shutdown.4369/), [IEEE - Manual ESD SIL study](https://ieeexplore.ieee.org/document/1518312)

### Q: 운전원 수동 Trip을 보호층으로 인정할 수 있나요?
A: 일반적으로 LOPA에서 운전원 조치는 PFD 0.1 수준 이상으로 보며 단독 SIS로 쓰기엔 부족하다는 설명이 있습니다(출처 기준). 그래서 ESD PB는 자동 SIF를 보완하는 수단으로 보고, SIL 목표가 높으면 자동 계통을 따로 둡니다. 최종 판단은 LOPA 결과를 따르세요(초안, 담당자 확인 필수).
키워드: operator action, LOPA, manual trip, PFD 0.1, ESD PB credit
부품: esd-pb
출처: [Industrial Monitor Direct - E-Stop hardwired vs software](https://industrialmonitordirect.com/blogs/knowledgebase/emergency-stop-pushbutton-design-hardwired-vs-software-implementation-requirements), [IEEE - Manual ESD SIL study](https://ieeexplore.ieee.org/document/1518312)

### Q: Bypass 관리는 어떻게 설계해야 하나요?
A: Bypass는 의도적이고, 운전원에게 보이고, 시간 제한이 있어야 합니다. 권한자만 키스위치·암호로 걸 수 있게 하고, Bypass 중에는 쉽게 끌 수 없는 별도 알람과 HMI 상태 표시, 자동 기록(사용자·시각·사유·만료)을 남깁니다. 시간 초과 시 재승인 받도록 설계합니다(초안, 담당자 확인 필수).
키워드: bypass, override, MOS, keyswitch, bypass alarm, time limit, 바이패스
부품: bypass-panel, controller
출처: [automationforum - IEC 61511 Safety Bypass and Override](https://automationforum.co/iec-61511-safety-bypass-override-sis-maintenance/)

### Q: Bypass 중에 운전을 계속해도 되나요?
A: 위험성 분석에서 보상 조치(Compensating measures)가 충분한 위험 감소를 준다고 확인된 경우에만 허용된다고 공개 자료는 정리합니다. 보상 조치 예로는 운전원 수동 감시, 처리량 감소, 추가 알람, 현장 인원 배치, 다른 독립 보호층 확인이 있습니다. 보상 조치에는 기간·공정 조건 한계가 붙어야 합니다(초안, 담당자 확인 필수).
키워드: compensating measures, 보상 조치, bypass operation, hazard analysis, 운전 지속
부품: bypass-panel
출처: [Open Exam Prep - Proof Testing, Demands, and Bypasses](https://open-exam-prep.com/study-guides/pe-control-systems/sis-operations/proof-testing-bypass), [automationforum - IEC 61511 Safety Bypass and Override](https://automationforum.co/iec-61511-safety-bypass-override-sis-maintenance/)

### Q: Startup override는 Maintenance bypass와 뭐가 다른가요?
A: Maintenance bypass는 교정·Stroke test 같은 정해진 작업 동안만 거는 임시 Bypass이고, Startup override는 승인된 운전 절차가 허용하는 기동 구간에서 제한 시간 동안만 거는 것입니다. 영구 Override는 설계 변경으로 보고 안전 분석과 MOC를 거쳐야 합니다. 둘을 같은 키스위치로 섞어 쓰지 않도록 구분하세요(초안, 담당자 확인 필수).
키워드: startup override, maintenance bypass, permanent override, MOC, 기동 오버라이드
부품: bypass-panel
출처: [automationforum - IEC 61511 Safety Bypass and Override](https://automationforum.co/iec-61511-safety-bypass-override-sis-maintenance/)

## Interface
### Q: ESD 밸브의 Partial Stroke Test(PST)는 어디서 하나요?
A: Logic solver에서 직접, 스마트 포지셔너에서, 또는 SOV를 이용한 방식으로 할 수 있습니다. Logic solver 방식은 ESD I/O와 배선이 늘어 비용이 높고, 포지셔너 방식은 SOV를 시험하지 못해 공통원인 경로가 남는다는 지적이 있습니다. PST는 Full proof test를 대체하지 않습니다(초안, 담당자 확인 필수).
키워드: PST, partial stroke test, SOV, positioner, final element, proof test, ESDV
부품: io, controller
출처: [ask.instrumentationtools - How to do PST](https://ask.instrumentationtools.com/t/how-to-do-valve-partial-stroke-testing-pst/6450), [Val Controls - Positioner vs Solenoid PST](https://valcontrols.com/blogs/insights/positioner-vs-solenoid-based-control-for-pst), [Wikipedia - Partial stroke testing](https://www.wikipedia.com/wiki/Partial_stroke_testing)

### Q: IPS와 DCS 사이 신호는 어떻게 주고받나요?
A: 일반적으로 상태·알람·Bypass 상태·SOE는 통신으로 DCS HMI에 보내고, DCS가 IPS 안전 로직에 쓰기(Write)하는 것은 제한합니다. 통신 고장이 안전 기능에 영향을 주면 안 되므로 IPS는 별도 보안 Zone으로 두고 연결을 최소화하라는 권고가 있습니다. Reset·Bypass 요청처럼 DCS에서 오는 명령은 IPS 측 허가 로직을 거치게 하세요(초안, 담당자 확인 필수).
키워드: IPS DCS interface, read only, safety zone, reset, bypass request, SOE, 통신
부품: network, controller
출처: [HMS Networks - Zones and Conduits](https://www.hms-networks.com/tech-blog/blogpost/hms-blog/2024/10/03/zones-and-conduits--essential-building-blocks-of-industrial-network-security), [ProcessOnline - Integrating control and safety](https://www.processonline.com.au/content/safety/article/integrating-control-and-safety-where-to-draw-the-line-608324800)

### Q: Motor trip은 IPS에서 MCC로 어떻게 보내나요?
A: 일반적으로 IPS가 MCC로 Hardwired Trip 명령을 보내 DCS 기동 명령보다 우선하게 합니다. 공개 자료는 ESD를 별도 안전 계층으로서 MCC에 Hardwired Trip을 주는 구조로 설명합니다(비공식 출처). Interposing relay 위치와 DET 여부를 Interface 문서에 명시하세요(초안, 담당자 확인 필수).
키워드: motor trip, MCC interface, hardwired trip, interposing relay, IPS MCC
부품: io, terminal
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system), [Industrial Monitor Direct - ESD vs PLC architecture](https://industrialmonitordirect.com/blogs/knowledgebase/esd-vs-plc-emergency-shutdown-system-architecture-explained)

### Q: IPS 사이버보안은 어떻게 요구하나요?
A: IEC 62443 Zone & Conduit 관점에서 SIS는 자체 Zone으로 두고 최소 연결만 허용하라는 권고가 많습니다. 2차 자료는 IEC 61511-1:2016이 SIS 보안 위험성 평가를 요구한다고 인용하지만 조항은 원문 대조가 필요합니다. 엔지니어링 PC 접근, USB, 원격 접속 정책을 MR에 명시하세요(초안, 담당자 확인 필수).
키워드: SIS cybersecurity, IEC 62443, security risk assessment, safety zone, firewall
부품: network
출처: [HMS Networks - Zones and Conduits](https://www.hms-networks.com/tech-blog/blogpost/hms-blog/2024/10/03/zones-and-conduits--essential-building-blocks-of-industrial-network-security), [Emerson Automation Experts - Safety and control separation](https://www.emersonautomationexperts.com/2009/06/views_on_safety/)

## 표준
### Q: IPS 설계에 적용되는 핵심 표준은?
A: 공정 산업 SIS는 IEC 61511(미국은 ISA 61511), 그 안에 쓰는 장치 제조는 IEC 61508을 기준으로 합니다. IEC 61511은 SIS 안전 요구 사양(SRS), 설계, 운전·유지보수(Proof test, Bypass 관리)까지 수명주기 전체를 다룹니다. 세부 조항은 원문 대조가 필요합니다(초안, 담당자 확인 필수).
키워드: IEC 61511, ISA 61511, IEC 61508, functional safety, safety lifecycle, 기능안전
부품: controller
출처: [IEC Webstore - IEC 61511-1 preview](https://webstore.iec.ch/p-preview/info_iec61511-1%7Bed1.0%7Db.pdf), [IEC 61511:2016 summary](https://kyawminthu20.github.io/Control-System-Tools/standards/functional-safety/iec-61511)

### Q: SRS(Safety Requirements Specification)에는 뭐가 들어가나요?
A: SIF별로 입력, 출력, 안전 상태, Proof test 주기, 응답 시간 등을 정의하고 상세 설계 전에 작성합니다. DET/ETT 구분, Reset 방식, Bypass 요구도 SRS에 들어가야 C&E와 로직이 일관됩니다. 전체 항목 목록은 IEC 61511-1 원문 확인이 필요합니다(초안, 담당자 확인 필수).
키워드: SRS, safety requirements specification, safe state, response time, proof test interval
부품: controller
출처: [IEC 61511:2016 summary](https://kyawminthu20.github.io/Control-System-Tools/standards/functional-safety/iec-61511), [Kenexis - DET vs ETT](https://www.kenexis.com/?p=24577)

### Q: Logic solver SIL 인증서는 뭘 봐야 하나요?
A: 인증 범위가 사용하는 하드웨어 모델·펌웨어 버전·구성(이중화 방식)을 포함하는지, 그리고 Safety manual의 사용 제약을 지켰는지 확인합니다. 벤더 자료에 SIL 3 인증이 있다고 해도 블로그·마케팅 자료가 아닌 현행 인증서와 매뉴얼로 확인해야 합니다. 프로젝트 요구 SIL은 미확인입니다(초안, 담당자 확인 필수).
키워드: SIL certificate, TUV, exida, safety manual, firmware version, 인증서
부품: controller, io
출처: [Industrial Monitor Direct - Triconex TMR getting started](https://industrialmonitordirect.com/blogs/knowledgebase/triconex-safety-plcs-getting-started-with-tmr-systems), [Emerson - DeltaV SIS Logic Solver Hardware](https://Emerson.com/en-us/automation/control-and-safety-systems/safety-instrumented-systems-sis/deltav-safety-instrumented-system/deltav-sis-logic-solver-hardware)

## 시험
### Q: IPS FAT에서는 뭘 시험하나요?
A: Logic solver, Application program, 진단, I/O를 시뮬레이션 신호로 시험하고 C&E Matrix의 모든 Trip·Permissive·Bypass를 확인합니다. 한 자료는 FAT만으로는 설치된 센서·밸브까지 증명하지 못하므로 SAT에서 실제 SIF를 입증해야 한다고 설명합니다. 전원 상실·통신 상실 시 Fail-safe 동작도 꼭 봅니다(초안, 담당자 확인 필수).
키워드: IPS FAT, SIS FAT, C&E test, fail-safe test, simulation, SAT
부품: controller, io, psu, bypass-panel
출처: [Open Exam Prep - SIS Design Constraints](https://open-exam-prep.com/study-guides/pe-control-systems/sis-design-sil/sis-design-constraints), [automationforum - DCS FAT Procedure](https://automationforum.co/dcs-fat-procedure/)

### Q: C&E Matrix 검증은 어떻게 하나요?
A: C&E는 기동 조건과 요구 동작을 연결한 표지만, Reset 조건이나 신호 고장 시 동작, 순서까지는 다 담지 못하므로 Shutdown philosophy와 같이 봐야 합니다. Trip 설정값·Voting·신호 검증을 승인 문서와 대조하고, 각 원인-결과를 관찰 가능한 결과와 응답시간 기준으로 시험합니다. 현장에서도 물리적으로 다시 확인하라는 권고가 있습니다(초안, 담당자 확인 필수).
키워드: cause and effect, C&E matrix, shutdown philosophy, reset, trip test, 인과표
부품: controller, io
출처: [Industrial Monitor Direct - Configuring ESD and PSD](https://industrialmonitordirect.com/blogs/knowledgebase/configuring-esd-and-psd-functions-for-process-safety), [Epcland - Emergency Shutdown System](https://epcland.com/?p=48938)

### Q: Proof test는 왜 중요하고 미루면 어떻게 되나요?
A: Proof test는 진단으로 잡히지 않는 위험 미검출 고장을 찾기 위한 것이며, 커버리지가 100%인 경우는 드뭅니다. SIL 검증은 정해진 시험 주기를 지킨다는 가정으로 계산되므로 시험을 건너뛰거나 미루면 SIL 주장이 무너집니다. 시험 주기와 절차를 SRS·운전 절차에 명시하세요(초안, 담당자 확인 필수).
키워드: proof test, test interval, proof test coverage, dangerous undetected, 주기 시험
부품: controller, io
출처: [Open Exam Prep - Proof Testing, Demands, and Bypasses](https://open-exam-prep.com/study-guides/pe-control-systems/sis-operations/proof-testing-bypass)

## 사양 검토 유의사항
### Q: IPS 사양 검토 때 독립성은 어떻게 확인하나요?
A: 하드웨어·소프트웨어가 DCS와 분리돼 있는지, 공유 부품(네트워크, 전원, 엔지니어링 PC)이 있는지, 공유 시 공통원인 분석 근거가 있는지 봅니다. 한 평가 기준 예시는 하이브리드 솔루션을 배제하고 DCS·ESD 별도 하드웨어·소프트웨어를 요구합니다(출처 기준). 같은 팀이 둘 다 엔지니어링하면 문서·절차 분리에 더 신경 써야 합니다(초안, 담당자 확인 필수).
키워드: independence check, shared component, hybrid, 독립성 검토, 공통원인
부품: controller, network, psu
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system), [ProcessOnline - Integrating control and safety](https://www.processonline.com.au/content/safety/article/integrating-control-and-safety-where-to-draw-the-line-608324800)

### Q: IPS Spare와 여유율은 DCS와 같게 잡나요?
A: 공개 가이드는 DCS·ESD·F&G 각 시스템에 Installed spare 20%를 따로 균등 배분하고, 캐비닛 20% 여유 공간, Controller·Network 부하 SAT 후 40% 여유를 예로 듭니다(출처 기준). 시스템 간 Spare를 합쳐서 계산하지 않도록 주의하세요. 프로젝트 값은 미확인입니다(초안, 담당자 확인 필수).
키워드: IPS spare, installed spare, 20%, controller loading, 여유율
부품: io, cabinet, controller
출처: [instrumentationtools - Control System Spares](https://instrumentationtools.com/control-system-spares)

## MR 작성
### Q: IPS MR에 꼭 들어가야 할 항목은?
A: 요구 SIL과 인증 범위, Logic solver 구조(TMR/QMR/이중화), I/O 이중화·Hot-swap, DET 원칙, Scan time·응답시간, Bypass panel·ESD PB 범위, SOE, DCS Interface, 사이버보안, Spare, FAT/SAT 범위를 적습니다. 인증서·Safety manual·SIL 계산 입력 데이터(고장률)를 벤더 제출 문서로 지정하는 것도 중요합니다. 수치는 프로젝트 Spec 대조 전까지 미확인입니다(초안, 담당자 확인 필수).
키워드: IPS MR, material requisition, SIL requirement, logic solver, bypass panel, SOE, 벤더 문서
부품: cabinet, controller, io, psu, network, bypass-panel, esd-pb
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system), [instrumentationtools - Functional Design Specifications for DCS/SIS](https://instrumentationtools.com/functional-design-specifications-for-dcs-sis-projects)

### Q: IPS 벤더 문서로 무엇을 받아야 하나요?
A: 일반적으로 FDS, System architecture, 캐비닛 GA·배선도, I/O 할당, C&E 기반 로직 도면, Safety manual, SIL 인증서, 고장률 데이터, FAT/SAT 절차서, 발열·전원 계산을 받습니다. ESD 문서에는 보통 C&E Matrix와 ESD Logic diagram이 포함됩니다. 회사 VDRL 양식은 미확인입니다(초안, 담당자 확인 필수).
키워드: vendor document, VDRL, safety manual, SIL certificate, logic diagram, C&E
부품: cabinet, controller
출처: [Skill-Lync - Emergency Shutdown System](https://resources.skill-lync.com/branches/chemical-engineering/questions/process-design/emergency-shutdown-system), [instrumentationtools - Functional Design Specifications for DCS/SIS](https://instrumentationtools.com/functional-design-specifications-for-dcs-sis-projects)

## 자주 하는 실수
### Q: IPS 검토에서 자주 하는 실수는?
A: (1) Logic solver SIL 인증만 보고 SIF 전체 SIL을 판단, (2) DCS와 센서·전원 공유를 근거 없이 허용, (3) Bypass 시간 제한·알람 누락, (4) ETT 회로에 Line monitoring 누락, (5) PST를 Proof test로 대체하는 것이 흔합니다. 각각 위 출처의 일반 권고 기준입니다(초안, 담당자 확인 필수).
키워드: 자주 하는 실수, pitfall, SIL misunderstanding, bypass, ETT monitoring, PST
부품: controller, io, bypass-panel
출처: [exida - SIL verification beyond PFDavg/PFH](https://www.exida.com/Blog/sil-verification-beyond-pfdavg-pfh), [automationforum - IEC 61511 Safety Bypass and Override](https://automationforum.co/iec-61511-safety-bypass-override-sis-maintenance/), [Kenexis - DET vs ETT](https://www.kenexis.com/?p=24577)

### Q: Bypass 키를 꽂아둔 채 두는 것도 문제인가요?
A: 네, 이는 고장률로 평균화되지 않는 Systematic failure의 대표 예로 꼽힙니다. 그래서 교대 인수인계 때 활성 Bypass를 점검하고, 시간이 지나면 자동 연장하지 말고 재평가하라고 권고합니다. HMI에 Bypass 목록과 적용자를 상시 표시하면 놓치는 일을 줄일 수 있습니다(초안, 담당자 확인 필수).
키워드: bypass key left, systematic failure, shift handover, 교대 인수인계, bypass list
부품: bypass-panel
출처: [automationforum - IEC 61511 Safety Bypass and Override](https://automationforum.co/iec-61511-safety-bypass-override-sis-maintenance/), [ESD SIL Verification blog](https://zohaibjahan.blogspot.com/2026/06/SIL-Verification-IEC61511-SIS.html)
