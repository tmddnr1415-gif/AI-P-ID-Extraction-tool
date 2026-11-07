# DCS Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: DCS가 정확히 뭐고 PLC랑 뭐가 다른가요?
A: DCS(Distributed Control System)는 플랜트 전체 공정 제어를 여러 Controller에 분산시키고, 공통 HMI·엔지니어링·Historian 환경으로 묶은 시스템입니다. 분산 구조 덕분에 한 Controller가 죽어도 플랜트 전체가 멈추지 않도록 설계하는 것이 출발점이었고, 그래서 이중화 개념이 DCS와 함께 발전했습니다. PLC도 요즘은 DCS 기능을 상당 부분 갖추지만, DCS는 대규모 연속 공정에서 단일 DB·통합 알람·Batch/Advanced Control까지 한 플랫폼으로 관리한다는 점이 차이입니다.
키워드: DCS, Distributed Control System, 분산제어, PLC, BPCS, 개념
부품: controller, hmi, network
출처: [instrumentationtools.com - DCS redundancy history](https://instrumentationtools.com/?p=22674), [Control Engineering - PLC architecture has DCS functionality](https://www.controleng.com/articles/plc-architecture-has-dcs-functionality/)

### Q: DCS 기본 구성은 어떻게 되나요?
A: 크게 Controller, I/O 모듈과 Termination, Control Network(Switch), Operator/Engineering Station, Server·Historian, 그리고 System·Marshalling·Power Distribution 캐비닛으로 나뉩니다. 현장 신호는 JB → Marshalling Cabinet → System Cabinet의 I/O로 들어오고, Controller가 연산한 뒤 Network로 HMI에 올라갑니다. 벤더에 따라 Controller·I/O·Workstation 하드웨어를 여러 시스템 계열에 공통으로 쓰기도 합니다.
키워드: DCS 구성, architecture, controller, I/O, HMI, historian, marshalling, system cabinet
부품: cabinet, controller, io, psu, network, terminal, hmi
출처: [Valmet - Controllers and I/O](https://www.valmet.com/automation/control-systems/hardware/), [automationforum - What is Marshalling Cabinet](https://automationforum.co/what-is-marshalling-cabinet/)

### Q: BPCS랑 DCS는 같은 말인가요?
A: 실무에서는 거의 같은 의미로 씁니다. BPCS(Basic Process Control System)는 기능 계층 이름이고, DCS는 그 기능을 구현하는 플랫폼입니다. 중요한 건 BPCS가 SIS(IPS)와 독립되어야 한다는 점이라서, 같은 벤더 통합 플랫폼을 쓸 때도 SIS 기능 무결성이 BPCS 고장에 영향받지 않도록 분리 근거를 남겨야 합니다.
키워드: BPCS, DCS, SIS, 독립성, independence, 통합 플랫폼
부품: controller, network
출처: [ProcessOnline - Integrating control and safety](https://www.processonline.com.au/content/safety/article/integrating-control-and-safety-where-to-draw-the-line-608324800), [Emerson Automation Experts - Safety and control separation](https://www.emersonautomationexperts.com/2009/06/views_on_safety/)

## 설계
### Q: DCS 이중화는 어디까지 해야 하나요?
A: 일반적으로 Controller(Hot standby), Power Supply, Control Network, Server·Operator Station은 이중화하고, I/O 이중화는 중요 루프에 한정하는 경우가 많습니다(출처 기준). 한 입찰 평가 기준 예시에서는 DCS I/O 이중화는 선택, ESD는 필수로 보고 있습니다. 프로젝트 Spec에 이중화 범위가 명시되어 있는지 먼저 확인하세요.
키워드: redundancy, 이중화, hot standby, controller redundancy, I/O redundancy, dual network
부품: controller, io, psu, network
출처: [Skill-Lync - DCS Redundancy Types](https://resources.skill-lync.com/branches/instrumentation/questions/dcs-fieldbus/redundancy-types-dcs), [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system)

### Q: Controller만 이중화하면 충분하지 않나요?
A: 아닙니다. CPU 이중화와 I/O·Network 이중화는 서로 다른 고장 영역이라서, Dual CPU라도 Remote I/O 링이 하나뿐이면 그 링이 끊길 때 같이 죽습니다. 그래서 검토할 때는 Controller → I/O Bus → I/O 모듈 → 전원까지 단일 고장점(SPOF)을 경로별로 따라가 보는 게 좋습니다.
키워드: single point of failure, SPOF, 고장 영역, failure domain, I/O bus, remote I/O
부품: controller, io, network, psu
출처: [Open Exam Prep - DCS, PLC, SCADA Architecture](https://open-exam-prep.com/study-guides/pe-control-systems/control-hmi-logic/system-architecture)

### Q: Controller 절체(switchover) 시간은 얼마로 보나요?
A: 한 DCS/ESD 기술평가 기준 예시는 절체 약 100 ms, Bumpless 전환, Standby가 Primary와 상시 동기화되는 것을 요구합니다(출처 기준). 수치 자체보다 '절체 중 출력이 튀지 않는가'가 핵심이므로 FAT에서 실제 루프를 돌리면서 절체 시험을 해야 합니다. 프로젝트 Spec 수치는 미확인입니다.
키워드: switchover, 절체 시간, bumpless transfer, standby sync, 100 ms
부품: controller
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system)

### Q: Spare I/O는 보통 몇 % 잡나요?
A: EPC 사양에서 흔히 보이는 값은 I/O 종류별 20% Installed spare(배선·단자까지 완료)와 캐비닛 20% 빈 공간입니다(출처 기준). Installed spare는 단자·Fuse·Barrier·Relay까지 포함해 바로 쓸 수 있어야 하고, Controller 부하 계산에도 포함해야 한다는 의견이 많습니다. 다만 10/10/10처럼 더 낮게 잡는 관행도 있어 고객 Spec 값이 우선입니다.
키워드: spare I/O, installed spare, 20%, spare space, 여유율, 예비
부품: io, terminal, cabinet
출처: [instrumentationtools - Control System Spares](https://instrumentationtools.com/control-system-spares), [Control Design - How to plan for spare I/O space](https://www.controldesign.com/articles/2021/how-to-plan-for-spare-io-space)

### Q: Controller·Network·전원 여유율은 어떻게 보나요?
A: 한 공개 가이드는 SAT 이후 Controller 부하 40% 여유, Network 부하 40% 여유, Power Supply 25% 여유, Workstation 메모리·저장공간 50% 여유를 예로 듭니다(출처 기준). 다른 평가 기준은 CPU 부하 60% 이하를 요구해 같은 의미로 볼 수 있습니다. 중요한 건 '언제 기준(SAT 후)'인지와 Installed spare 포함 여부를 Spec에 못박는 것입니다.
키워드: CPU loading, controller loading, network loading, 40%, 60%, memory spare, 여유율
부품: controller, network, psu, hmi
출처: [instrumentationtools - Control System Spares](https://instrumentationtools.com/control-system-spares), [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system)

### Q: I/O 카드 채널 수는 어떻게 정하나요?
A: 한 평가 기준 예시는 AI/AO 16채널 이하, DI/DO 64채널 이하 모듈을 요구합니다(출처 기준). 채널 수가 많을수록 카드 하나 고장 시 잃는 루프가 많아지므로, 중요 루프는 카드를 나눠 배치(분산 배치)하는 게 일반적입니다. 이중화 루프(A/B 트랜스미터)는 반드시 다른 카드에 넣어야 합니다.
키워드: I/O module channel, 16ch, 64ch, I/O 분산 배치, I/O allocation
부품: io
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system)

### Q: Marshalling Cabinet은 왜 따로 두나요?
A: Marshalling Cabinet은 현장 JB에서 온 다심 케이블을 받아 System Cabinet의 I/O 순서로 재배열(cross-wiring)하는 중간 단입니다. 이렇게 하면 현장 배선과 I/O 할당을 분리할 수 있어 설계 변경이나 I/O 재배치가 쉬워집니다. 안에는 단자대, Fuse, 차단기, 접지 단자 등이 들어가고 발열이 있으면 팬이 필요할 수 있습니다.
키워드: marshalling cabinet, cross wiring, 단자대, terminal block, JB, junction box
부품: cabinet, terminal
출처: [automationforum - What is Marshalling Cabinet](https://automationforum.co/what-is-marshalling-cabinet/), [Industrial Monitor Direct - Estimating DCS Marshalling Capacity](https://industrialmonitordirect.com/blogs/knowledgebase/estimating-dcs-marshalling-and-system-cabinet-io-capacity)

### Q: 캐비닛 사양은 보통 어떻게 쓰나요?
A: 한 평가 기준 예시는 Bottom entry, 앞뒤 이중문, IP52 이상, 2100(H, Plinth 100 포함)×1200(W)×800(D) mm, RAL 7035, 30% 여유 공간, AI/DI 별도 Marshalling, DO에 Interposing relay를 요구합니다(출처 기준). 이 값들은 회사마다 달라서 그대로 쓰면 안 되고, 고객 표준과 Control room 배치 도면을 먼저 확인해야 합니다. 전력선과 신호선 분리도 같이 명시하는 게 좋습니다.
키워드: cabinet, 캐비닛, IP52, RAL 7035, bottom entry, interposing relay, 치수
부품: cabinet, terminal
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system)

### Q: DCS 전원은 어떻게 구성하나요?
A: 일반적으로 Controller와 I/O에는 UPS 전원을 이중 Feeder로 공급하고, 캐비닛 조명·팬 같은 유틸리티는 Non-UPS로 공급합니다(출처 기준). UPS 출력은 회로별 차단기로 보호해 한 부하 단락이 전체로 번지지 않게 합니다. 검토 시에는 Feeder A/B가 PSU A/B로 정말 분리되어 들어가는지 단선도로 확인하세요.
키워드: UPS, power distribution, dual feeder, non-UPS, PSU, 전원 분배
부품: psu, cabinet
출처: [automationforum - Panels in automation design](https://automationforum.co/various-panels-involved-in-automation-design/)

### Q: DCS 접지는 어떻게 하나요?
A: 공개 평가 기준 예시는 System 접지, Cable screen 접지, Panel body 접지를 분리(Isolated)하도록 요구합니다(출처 기준). 한 포럼 사례는 캐비닛 주변 접지 Bar를 연결해 외부 접지봉에 묶는 방식을 소개하지만, 이는 특정 현장 사례일 뿐 일반 규칙은 아닙니다. 실제 접지 방식과 도체 굵기는 벤더 설치 매뉴얼과 프로젝트 전기 Spec을 따라야 하며 현재는 미확인입니다.
키워드: grounding, earthing, 접지, instrument earth, shield earth, IE, PE
부품: cabinet, terminal
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system), [Mike Holt Forum - Grounding scheme for DCS marshalling](https://forums.mikeholt.com/threads/grounding-scheme-for-dcs-marshalling-rack-room.150763/)

### Q: 캐비닛 발열(Heat load)은 왜 검토하나요?
A: 캐비닛 발열 합계가 Control room·Rack room HVAC 용량 산정의 입력이기 때문입니다. 발열이 빠지지 않으면 보호기기 온도가 올라 오동작할 수 있습니다. 그래서 DCS 사양서에 벤더가 유닛별 발열량을 견적 단계부터 제출하도록 요구하는 사례가 있습니다.
키워드: heat load, heat dissipation, 발열, HVAC, power consumption, 소비전력
부품: cabinet, psu
출처: [automationforum - What is Marshalling Cabinet](https://automationforum.co/what-is-marshalling-cabinet/), [Scribd - DCS spec excerpt](https://www.scribd.com/document/575140283/1-DCS-spec)

## Interface
### Q: Package PLC를 DCS에 붙일 때 Hardwired와 통신 중 뭘 쓰나요?
A: 일반적으로 운전 감시·지시용 데이터는 Modbus TCP/RTU나 OPC 같은 Serial link로, Trip·Start/Stop 같은 중요 신호는 Hardwired로 갑니다. DCS가 Modbus TCP Master가 되면 OPC 서버 없이 직접 붙일 수 있고, RTU 장비는 Protocol converter가 필요할 수 있습니다. 통신 Interface 목록(Register map)과 고장 시 동작을 Interface 회의에서 확정하는 게 핵심입니다.
키워드: 3rd party interface, package PLC, Modbus TCP, Modbus RTU, OPC, serial link, hardwired, register map
부품: network, io
출처: [Control.com - communication protocol](https://control.com/forums/threads/communication-protocol.33479/post-33479), [Eng-Tips - DCS PLC interface](https://www.eng-tips.com/viewthread.cfm?qid=422908)

### Q: OPC로 연결하면 주의할 점은?
A: OPC(특히 Classic OPC-DA)는 제조사 OPC 서버와 Windows 권한 설정이 필요해 보안·안정성 이슈가 생기기 쉽습니다. 그래서 서버 이중화 여부, 라이선스 범위, 방화벽 경로를 같이 검토해야 합니다. 라이선스 비용 등 구체 값은 미확인입니다.
키워드: OPC, OPC DA, OPC UA, OPC server, license, Windows DCOM
부품: network, hmi
출처: [Industrial Monitor Direct - DeltaV PLC Interface](https://industrialmonitordirect.com/blogs/knowledgebase/emerson-deltav-plc-interface-methods-and-configuration-guide), [Eng-Tips - DCS PLC interface](https://www.eng-tips.com/viewthread.cfm?qid=422908)

### Q: DCS와 SIS(IPS) 사이 Interface는 어떻게 하나요?
A: SIS 상태·알람·Bypass 상태는 DCS HMI에 보여주되, SIS 안전 기능이 DCS 고장에 영향받지 않도록 분리하는 것이 원칙입니다. 통합 플랫폼이라도 런타임 실행 단계에서 분리하고, 엔지니어링·변경 관리도 분리해야 독립성을 주장할 수 있다는 의견이 있습니다. 상세 Interface 방식은 IPS Knowledge도 함께 보세요.
키워드: DCS SIS interface, BPCS SIS separation, 통합 플랫폼, independence, IPS
부품: network, controller
출처: [ProcessOnline - Integrating control and safety](https://www.processonline.com.au/content/safety/article/integrating-control-and-safety-where-to-draw-the-line-608324800)

### Q: HART 통신이나 Asset management는 어떻게 요구하나요?
A: Smart 트랜스미터·포지셔너 진단을 DCS에서 받으려면 I/O 카드의 HART pass-through와 Asset management 소프트웨어(AMS 등)가 필요합니다. 한 평가 기준 예시는 OPC, HART pass-through, Hot-swap 카드, AMS, GPS clock을 필수 기능으로 둡니다(출처 기준). MR에 라이선스 수량까지 적어야 나중에 추가 비용이 안 생깁니다.
키워드: HART, HART pass-through, AMS, asset management, 진단, smart device
부품: io, hmi
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system)

### Q: SOE와 시간 동기화는 어떻게 요구해야 하나요?
A: SOE(Sequence of Events)는 Trip 원인 분석용이라 시간 분해능과 동기화가 핵심입니다. 한 벤더 자료는 SOE 분해능 1 ms, GPS 기반 동기화 시 1~3 ms, 일반 NTP 기반은 Workstation 간 50 ms 수준으로 제시합니다(출처 기준). 여러 Controller 간 1 ms급 정렬이 필요하면 GPS 시각원(Stratum-1급)을 Spec에 넣어야 합니다.
키워드: SOE, sequence of events, time synchronization, GPS, NTP, PTP, 1 ms, 시각동기
부품: controller, network
출처: [Schneider Electric - Foxboro SOE PSS](https://paresource.schneider-electric.com/iaseries/pss/31s2/31s2soe.pdf), [Schneider Electric - Time synchronization PSS](https://paresource.schneider-electric.com/iaseries/pss/31s1/31s1time.pdf), [Emerson Exchange - NTP accuracy and SOE cards](https://emersonexchange365.com/products/control-safety-systems/f/deltav-discussions-questions/8024/remote-stratum-1-ntp-time-server-accuracy-and-soe-cards)

### Q: DCS 네트워크 보안(Cybersecurity)은 뭘 기준으로 보나요?
A: IEC 62443의 Zone & Conduit 개념으로 보안 요구가 같은 장비끼리 Zone을 묶고, Zone 간 통신(Conduit)은 방화벽 규칙으로 통제합니다. 종이로만 Conduit을 정의하고 실제 방화벽 규칙이 없으면 의미가 없다는 지적이 있습니다. SIS는 최소 연결의 별도 Zone으로 두라는 권고가 많습니다.
키워드: cybersecurity, IEC 62443, zone, conduit, firewall, DMZ, 방화벽, 보안
부품: network
출처: [HMS Networks - Zones and Conduits](https://www.hms-networks.com/tech-blog/blogpost/hms-blog/2024/10/03/zones-and-conduits--essential-building-blocks-of-industrial-network-security), [Trout Software - IEC 62443 zones and conduits](https://www.trout.software/blog/iec-62443-zones-and-conduits-explained)

### Q: Network Switch는 어떤 사양을 요구하나요?
A: 한 평가 기준 예시는 Managed switch, 광 포트 2개 이상을 요구합니다(출처 기준). Managed switch여야 포트 상태 진단, VLAN, 이중 링 구성이 가능하기 때문입니다. 실제 포트 수·광케이블 여유(예: 100% spare fiber 권고)는 프로젝트별로 정해야 합니다.
키워드: managed switch, fiber port, 광포트, VLAN, ring, network switch
부품: network
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system), [instrumentationtools - Control System Spares](https://instrumentationtools.com/control-system-spares)

## 표준
### Q: DCS 알람 설계는 어떤 표준을 따르나요?
A: 알람 관리는 ANSI/ISA-18.2, HMI 화면 설계는 ISA-101 원칙을 많이 참조합니다. ISA-18.2의 Rationalization은 각 알람이 정말 알람인지, 우선순위·설정값·조치가 정의됐는지 하나씩 검토하는 과정입니다. Yokogawa는 이 표준을 DCS 선정·Spec 단계부터 적용하라고 권고합니다.
키워드: ISA-18.2, alarm management, rationalization, alarm philosophy, ISA-101, HMI, 알람
부품: hmi
출처: [Yokogawa - Effective Alarm Management Planning Using ISA-18.2](https://www.yokogawa.com/library/resources/media-publications/effective-alarm-management-planning-using-ansiisa-182), [Open Exam Prep - ISA-18.2 Lifecycle](https://open-exam-prep.com/study-guides/isa-cap/system-design-hmi-alarms-enterprise/alarm-management-isa182)

### Q: Alarm philosophy 문서는 누가 언제 만드나요?
A: 운전원과 수명주기 관계자가 참여하는 Cross-functional 팀이 만들고, DCS 상세 설계 전에 확정하는 게 좋습니다. 알람 우선순위와 화면 배정 규칙이 이 문서에서 나오므로 늦으면 DCS 구성(Configuration)을 다시 해야 합니다. Emerson도 알람 관리 프로그램을 시작할 때 철학 문서를 먼저 세우라고 안내합니다.
키워드: alarm philosophy, 알람 철학, rationalization team, 운전원 참여
부품: hmi
출처: [Yokogawa - Effective Alarm Management Planning](https://www.yokogawa.com/library/resources/media-publications/effective-alarm-management-planning-using-ansiisa-182), [Emerson - Tips for starting an alarm management program](https://s1-live.emerson.com/documents/automation/article-tips-for-starting-an-alarm-management-program-deltav-en-37978.pdf)

### Q: FAT·SAT 절차는 어떤 표준을 참조하나요?
A: IEC 62381이 공정 산업 자동화 시스템의 FAT, SAT, SIT 절차를 다루며 부록에 체크리스트와 인증서 양식 예시가 있습니다. 판(Edition)이 여러 개라 프로젝트에 어느 판이 적용되는지 확인해야 합니다. 세부 조항 번호는 원문 미확인입니다.
키워드: IEC 62381, FAT, SAT, SIT, acceptance test, 체크리스트
부품: cabinet, controller, io, hmi
출처: [iTeh Standards - IEC 62381:2006](https://standards.iteh.ai/catalog/standards/iec/a4da7ca3-36f3-4af7-9e63-b98ba33b9d84/iec-62381-2006), [VDE Verlag - IEC 62381 ed3 preview](https://vde-verlag.de/iec-normen/preview-pdf/info_iec62381{ed3.0}b.pdf)

## 시험
### Q: DCS FAT 전에 무엇이 준비돼야 하나요?
A: FDS, C&E Matrix, 제어 철학, Instrument index, I/O DB, 알람 목록, 그래픽 목록, Loop diagram, 시스템 구성·캐비닛 GA, 네트워크 토폴로지, 승인된 FAT 절차서가 필요합니다. 이 문서들을 FAT 전에 동결(Freeze)하지 않으면 로직 변경으로 재시험과 문서 불일치가 생깁니다.
키워드: FAT prerequisite, FDS, C&E, I/O database, FAT procedure, document freeze
부품: controller, io, hmi
출처: [automationforum - DCS FAT Procedure](https://automationforum.co/dcs-fat-procedure/)

### Q: DCS FAT에서 꼭 해야 하는 시험은?
A: 하드웨어 외관·BOM·배선, 전원 투입 순서와 UPS, 이중화 절체(Controller·Network·Server·PSU 하나씩 제거), I/O 전수 시험, 로직·C&E, 그래픽, 알람, Fail-safe(신호·통신·전원 상실), 온라인 변경, 백업·복구, 통신 Interface를 봅니다. 특히 이중화는 '설정되어 있다'와 '무충격으로 넘어간다'가 다르므로 실제 절체를 반복 시험하라고 권고합니다.
키워드: FAT, redundancy test, I/O test, fail-safe test, backup restore, online change, 절체 시험
부품: cabinet, controller, io, psu, network, hmi
출처: [automationforum - DCS FAT Procedure](https://automationforum.co/dcs-fat-procedure/), [Skill-Lync - DCS FAT and SAT](https://resources.skill-lync.com/branches/instrumentation/questions/dcs-fieldbus/dcs-fat-sat-procedures)

### Q: FAT, SAT, SIT는 뭐가 다른가요?
A: FAT는 공장에서 시뮬레이션 신호로 시스템을 검증하는 것이고, SAT는 현장 설치 후 운송 손상·설치 상태와 기능을 다시 확인하는 것입니다. SIT는 DCS와 Package PLC·SIS 등 여러 시스템을 현장에서 연동해 통합 동작을 보는 시험입니다. 현장 계기·밸브와의 실제 Loop check는 SAT/Commissioning 단계에서 이뤄집니다.
키워드: FAT, SAT, SIT, site integration test, loop check, commissioning
부품: cabinet, io, network
출처: [automationforum - FAT vs SAT vs SIT](https://automationforum.co/fat-vs-sat-vs-sit/), [iTeh Standards - IEC 62381:2006](https://standards.iteh.ai/catalog/standards/iec/a4da7ca3-36f3-4af7-9e63-b98ba33b9d84/iec-62381-2006)

### Q: FAT Punch list는 어떻게 관리하나요?
A: 모든 편차를 Punch로 기록하고 내용, 담당자, 완료 상태, 재시험 필요 여부를 적습니다. 매일 FAT 회의에서 미결 Punch를 검토하고, 종결은 고객 대표가 승인합니다. 백업 파일과 Red-line 도면도 FAT 내내 최신으로 유지해야 합니다.
키워드: punch list, 펀치, FAT punch, red-line, closure, 재시험
출처: [automationforum - DCS FAT Procedure](https://automationforum.co/dcs-fat-procedure/)

## 사양 검토 유의사항
### Q: DCS 입찰 기술평가 때 어떤 항목을 보나요?
A: 독립된 DCS/ESD 하드웨어·소프트웨어 여부, 이중화 범위, 절체 시간, CPU 부하, 메모리·배터리 백업, 자기진단, I/O 채널 수, Scan time, Spare, 접지, Switch, 캐비닛, 엔지니어링 기능(온라인 변경 이력 등)을 비교합니다. 한 예시는 DCS Scan time 약 100 ms를 기준으로 둡니다(출처 기준). 각 항목을 Spec 조항과 연결한 Compliance table로 받으면 비교가 쉽습니다.
키워드: technical bid evaluation, TBE, 기술평가, compliance, deviation, scan time
부품: controller, io, cabinet, network
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system)

### Q: 온라인 변경(Online modification) 기능은 왜 중요하나요?
A: 운전 중 로직을 수정할 때 플랜트에 영향이 없어야 하기 때문입니다. 평가 기준 예시는 온라인 변경이 운전에 영향을 주지 않고, 변경 이력을 사용자명·시각과 함께 남기도록 요구합니다(출처 기준). FAT에서 실제 다운로드 시험으로 확인해야 합니다.
키워드: online modification, online download, change log, audit trail, 변경 이력
부품: controller, hmi
출처: [instrumentationtools - Technical Evaluation for DCS and ESD](https://instrumentationtools.com/technical-evaluation-for-dcs-and-esd-distributed-control-system), [automationforum - DCS FAT Procedure](https://automationforum.co/dcs-fat-procedure/)

## MR 작성
### Q: DCS MR에 어떤 Spare를 적어야 하나요?
A: Installed spare 외에 Commissioning spare(퓨즈·단자·릴레이 등 소모품), 2-year operation spare, Mandatory spare를 구분해 적습니다. Commissioning spare는 운영 예비품을 건드리지 않도록 본품과 함께 주문하고, Long-lead 품목은 현장 비축을 권고합니다. 수량은 벤더 추천을 받아 확정하므로 현재 값은 미확인입니다.
키워드: commissioning spare, 2 year spare, mandatory spare, 예비품, long lead
부품: controller, io, psu
출처: [instrumentationtools - Control System Spares](https://instrumentationtools.com/control-system-spares)

### Q: DCS 벤더에게 받아야 할 주요 문서는?
A: 일반적으로 FDS, System architecture, 캐비닛 GA·배선도, I/O 할당(Loading) 목록, 발열·소비전력 계산, Controller 부하 계산, Datasheet·Catalogue, FAT/SAT 절차서, O&M 매뉴얼, Deviation list를 받습니다. 한 사양서 예시는 견적 시 Clause-by-clause deviation을 사유와 함께 영어로 제출하도록 요구합니다. 정확한 VDRL 목록은 회사 양식 미확인입니다.
키워드: vendor document, VDRL, FDS, architecture drawing, GA, heat load, deviation list, 벤더 문서
부품: cabinet, controller, io
출처: [instrumentationtools - Functional Design Specifications for DCS/SIS](https://instrumentationtools.com/functional-design-specifications-for-dcs-sis-projects), [Scribd - DCS spec excerpt](https://www.scribd.com/document/575140283/1-DCS-spec)

### Q: FDS(Functional Design Specification)에는 뭐가 들어가나요?
A: FDS는 시스템이 운전 요구를 만족하는지 확인하는 기준 문서로, 시스템 개요와 기능 요구가 핵심 장입니다. 보통 아키텍처, 제어 기능, HMI·알람, Interface, 시험 방침까지 담아 FAT의 기준이 됩니다. FDS가 늦게 확정되면 Configuration과 FAT 절차서도 같이 밀립니다.
키워드: FDS, functional design specification, 기능 설계서, system overview
부품: controller, hmi, network
출처: [instrumentationtools - Functional Design Specifications for DCS/SIS](https://instrumentationtools.com/functional-design-specifications-for-dcs-sis-projects)

## 자주 하는 실수
### Q: DCS 사양 검토에서 자주 놓치는 건?
A: (1) Installed spare를 Controller 부하 계산에서 빼는 것, (2) 이중화 트랜스미터를 같은 I/O 카드에 넣는 것, (3) 여유율 기준 시점(SAT 후)을 안 적는 것, (4) 3rd-party 통신 고장 시 동작을 안 정하는 것, (5) 시간 동기화 정밀도를 SOE 요구와 안 맞추는 것이 흔합니다. 각 항목은 위 출처의 일반 권고 기준이며 프로젝트 Spec 대조가 필요합니다.
키워드: 자주 하는 실수, pitfall, spare loading, I/O segregation, comm failure, time sync
부품: controller, io, network
출처: [instrumentationtools - Control System Spares](https://instrumentationtools.com/control-system-spares), [Open Exam Prep - DCS Architecture](https://open-exam-prep.com/study-guides/pe-control-systems/control-hmi-logic/system-architecture), [Emerson Exchange - NTP and SOE](https://emersonexchange365.com/products/control-safety-systems/f/deltav-discussions-questions/8024/remote-stratum-1-ntp-time-server-accuracy-and-soe-cards)

### Q: FAT 때 로직이 계속 바뀌면 어떻게 되나요?
A: 늦은 로직 변경은 재시험과 문서 불일치를 만들고 Punch가 끝나지 않는 원인이 됩니다. 그래서 FAT 전 문서 동결과 변경 관리(MOC) 절차를 미리 합의하는 게 좋습니다. 불가피한 변경은 Red-line으로 남기고 재시험 범위를 명시하세요.
키워드: document freeze, late change, 재시험, MOC, red-line
출처: [automationforum - DCS FAT Procedure](https://automationforum.co/dcs-fat-procedure/)
