# CCS Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: 압축기 Surge 가 정확히 뭐고 왜 그렇게 위험한가요?
A: Surge 는 원심·축류 압축기가 최소 유량에서 더 이상 헤드를 유지하지 못해 유량이 역류하고 압력이 주기적으로 요동하는 불안정 현상입니다. 일반적으로 Surge 사이클은 0.3~3초 주기로 반복되며 진동·온도 상승·소음을 동반한다고 설명됩니다(출처 기준). 로터가 앞뒤로 밀리면서 Thrust bearing 손상과 과열이 생길 수 있어서, 몇 번의 Surge 만으로도 기계 손상이 누적될 수 있습니다. 그래서 CCS 의 최우선 목적은 운전점을 Surge 영역에서 떨어뜨려 놓는 것입니다.
키워드: Surge, 서지, 역류, flow reversal, thrust bearing, 압축기 불안정, centrifugal compressor
부품: compressor
출처: [Anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/), [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: Surge 는 주로 언제 발생하나요?
A: 유량이 갑자기 줄어드는 기동(Start-up), 비상정지(ESD/Trip), 하류 수요처가 막히는 상황에서 가장 잘 일어납니다. 정지 시에는 구동기 속도가 떨어지면서 운전점이 빠르게 Surge 선 쪽으로 이동하기 때문에 ASV 가 충분히 빨리 열려야 합니다. 따라서 검토할 때는 정상 운전뿐 아니라 기동·정지·Trip 시나리오를 따로 확인해야 합니다.
키워드: start-up, shutdown, trip, ESD, 기동, 정지, surge 시나리오, 하류 차단
부품: compressor, asv, driver
출처: [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: SLL 과 SCL 은 무슨 차이인가요?
A: SLL(Surge Limit Line)은 압축기 성능곡선상 실제 Surge 가 시작되는 경계이고, SCL(Surge Control Line)은 여기에 안전 여유(Margin)를 더해 오른쪽으로 옮긴 제어선입니다. Anti-surge 제어기는 운전점이 SCL 보다 오른쪽(안전 쪽)에 머물도록 ASV 를 엽니다. 일반적으로 Margin 은 Surge 시 입구 체적유량의 3~10% 정도로 소개되며 예시로 10% 를 쓰기도 합니다(출처 기준). 실제 값은 압축기 벤더·제어기 벤더와 확정해야 하므로 '미확인'입니다.
키워드: SLL, SCL, surge limit line, surge control line, surge margin, 서지 마진, 제어선
부품: controller, compressor
출처: [Anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/), [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: Surge Margin 을 작게 잡으면 뭐가 좋고 뭐가 위험한가요?
A: Margin 이 작을수록 Recycle 유량을 줄여 에너지 효율이 좋아집니다. 반대로 측정 오차나 밸브 응답 지연을 흡수할 여유가 줄어서 외란 시 실제 Surge 로 들어갈 위험이 커집니다. 그래서 일부 제어 방식은 운전점이 Surge 쪽으로 빠르게 다가오면 Margin 을 자동으로 넓히고, 안정되면 다시 줄이는 적응형 방식을 씁니다. 검토 시에는 Margin 값보다 '측정·밸브 응답이 그 Margin 을 감당하는지'를 같이 봐야 합니다.
키워드: margin, 효율, recycle, adaptive margin, 측정 오차, energy saving
부품: controller, asv
출처: [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge), [Controlling Surge in Centrifugal Compressors (Emerson)](https://www.emersonautomationexperts.com/2019/control-safety-systems/controlling-surge-centrifugal-compressors/)

### Q: CCS 는 Anti-surge 말고 어떤 기능을 하나요?
A: 보통 세 축으로 나뉩니다. Anti-surge 제어(Surge·Choke 보호), 성능(Performance/Capacity) 제어(흡입·토출 압력이나 유량 같은 공정 변수 유지), 그리고 여러 대 압축기의 Load sharing 입니다. Load sharing 과 성능 제어는 직렬·병렬 구성에 따라 Anti-surge 제어기 위에 추가로 얹히는 구조로 설명됩니다. 여기에 저흡입압·고토출압 같은 Limiting control 을 같이 두기도 합니다.
키워드: CCS, compressor control system, anti-surge, performance control, load sharing, limiting control, 성능제어
부품: controller
출처: [CCC Antisurge Control (Honeywell)](https://process.honeywell.com/us/en/products/turbomachinery-automation-systems/ccc-control-software/compressor-control/antisurge-control), [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/)

### Q: Surge 방지 제어와 Surge 감지(Detection)는 다른 건가요?
A: 네, 다릅니다. Surge 방지는 Surge 가 일어나기 전에 운전점을 SCL 오른쪽에 유지하는 폐루프(PI) 조절 제어입니다. Surge 감지는 이미 Surge 가 시작된 것을 유량·압력의 급격한 변화로 잡아내는 이산(Discrete)·개루프 기능이고, 감지되면 ASV 를 단계적으로 추가 개방합니다. 두 기능이 같은 송신기 신호를 공유하는 경우가 많아서 송신기가 양쪽 응답 요구를 모두 만족해야 합니다.
키워드: surge detection, surge prevention, 서지 감지, open loop, step opening, surge counter
부품: controller, ft, asv
출처: [Controlling Surge in Centrifugal Compressors (Emerson)](https://www.emersonautomationexperts.com/2019/control-safety-systems/controlling-surge-centrifugal-compressors/), [Rapid response (Digital Refining)](https://www.digitalrefining.com/article/1001227/rapid-response)

### Q: 분자량이 바뀌는 가스에서 Surge 선이 왜 문제가 되나요?
A: Surge 선은 가스 조성(분자량)과 흡입 조건에 따라 성능곡선상 위치가 달라지기 때문입니다. 한 자료는 분자량이 크게 바뀌는 경우 가스 조성별로 Surge 선을 따로 만들어야 한다고 설명합니다. CCC 같은 전용 제어기는 조성·조건 변화에 덜 민감한 'Invariant coordinate' 방식을 내세웁니다. 검토할 때는 운전 Case 별 가스 조성 범위와 제어기의 좌표계 방식을 확인해야 합니다.
키워드: molecular weight, 분자량, gas composition, invariant coordinates, 무차원 좌표, surge map
부품: controller, compressor
출처: [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge), [CCC Antisurge Control (Honeywell)](https://process.honeywell.com/us/en/products/turbomachinery-automation-systems/ccc-control-software/compressor-control/antisurge-control)

## 설계
### Q: Anti-surge Valve(ASV) 사이즈는 어떻게 잡나요?
A: 너무 작으면 운전점이 Surge 선 위에 붙어 버리고, 너무 크면 제어 감도가 떨어져 불안정해집니다. 일반적으로 선정 밸브 최대 용량이 Surge 곡선이 요구하는 최악 용량의 1.8~2.2배가 되도록 잡는다고 소개됩니다(출처 기준). CCC 측 자료도 정상 요구 용량의 약 2배가 동특성상 적절하다고 언급합니다. 최종 사이즈는 압축기 벤더·밸브 제조사와 기동·정지·정상 Case 로 확인해야 합니다.
키워드: ASV sizing, anti-surge valve, Cv, 1.8~2.2, 밸브 사이징, recycle valve
부품: asv, recycle-line
출처: [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/), [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: ASV 스트로크 시간은 얼마나 빨라야 하나요?
A: 운전점이 안전 영역에서 Surge 선까지 가는 공정 안전 시간에서 역산합니다. 일반적으로 개·폐 모두 0.5~2초, 또는 완전 닫힘에서 완전 열림까지 2초 미만이 제시됩니다(출처 기준). 다만 한 사례 연구에서는 개방 시간이 같아도 Cv 가 작은 밸브는 유량 저하를 막지 못했다고 하니, 속도와 용량을 같이 봐야 합니다. 프로젝트 값은 '미확인'이며 벤더 동특성 검토 결과로 확정합니다.
키워드: stroke time, stroking speed, 스트로크 시간, fast opening, 2 sec, 개방 속도, booster, quick exhaust
부품: asv
출처: [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/), [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: ASV 의 Fail position 과 신호 방향은 어떻게 하나요?
A: ASV 는 계장공기나 SOV·포지셔너 전원·신호를 잃으면 열리는 Fail Open 이 일반적입니다. 한 자료는 4 mA 에서 열림, 20 mA 에서 닫힘으로 설명합니다(출처 기준). 정지·고장 상황 자체가 Surge 를 유발하기 쉬우므로 '고장 = 압축기 보호' 방향으로 잡는 것입니다. 프로젝트 Valve datasheet 와 제어기 출력 방향이 일치하는지 반드시 대조하세요.
키워드: fail open, FO, fail position, 4-20mA, 신호 방향, air failure, SOV
부품: asv, signal
출처: [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/), [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: ASV 의 Trim 특성, 누설 등급, 소음 기준은 어떻게 보나요?
A: 한 자료는 Linear 특성을 선호하고(Equal percentage 도 언급), 정상 운전 중 흡입측으로 새는 유량을 막기 위해 누설 Class IV 를 제시합니다(출처 기준). 출구 속도는 0.3 Mach 이하로 제한하는 예가 소개됩니다. 누설이 크면 Recycle 이 상시 흘러 효율이 떨어지고, 속도가 높으면 소음·진동 문제가 생기기 때문입니다. 프로젝트 Valve Spec 값과 다르면 충돌로 표시하세요.
키워드: linear, equal percentage, leakage class IV, 누설등급, 0.3 Mach, noise, trim
부품: asv
출처: [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/)

### Q: ASV 위치는 어디가 좋은가요?
A: 제어 루프의 Dead time 과 Lag 을 줄이기 위해 압축기 토출 플랜지에 가능한 한 가깝게 두는 것이 권장됩니다. 토출 측 Check valve 도 압축기 출구 가까이 두어 Recycle 루프 안의 체적을 줄여야 응답이 빨라집니다. 계장공기 튜빙도 가능한 짧게 해서 누설과 지연을 줄이라는 권고가 있습니다. 배관 설계(Piping)와 같이 GA 도면에서 확인해야 하는 항목입니다.
키워드: valve location, dead time, lag, discharge flange, check valve, piping volume, 위치
부품: asv, recycle-line
출처: [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/), [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: Hot recycle 과 Cold recycle 은 언제 같이 쓰나요?
A: 정상 Recycle 은 토출 쿨러 하류에서 빼는 Cold recycle 을 쓰는데, 이 루프는 체적이 커서 Trip 같은 급변에 느릴 수 있습니다. 그래서 토출 Check valve 상류에 Hot gas bypass 를 추가해 기동·Trip 시 빠른 보호를 맡기는 구성이 소개됩니다. Hot recycle 은 흡입 온도를 올리므로 짧게만 쓰고 지속 유량은 Cold recycle 이 담당하는 전략이 일반적입니다. 공정 P&ID 에서 두 라인과 쿨러 위치를 함께 확인하세요.
키워드: hot gas bypass, hot recycle, cold recycle, recycle cooler, 리사이클 쿨러, trip protection
부품: recycle-line, asv
출처: [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: Recycle line 에 쿨러가 왜 필요한가요?
A: Recycle 된 가스는 압축열 때문에 온도가 올라가 있고, 이를 그대로 흡입에 돌리면 흡입 온도가 계속 올라 성능이 떨어지고 Surge 쪽으로 밀립니다. 그래서 Recycle 라인에 쿨러를 두어 흡입 온도를 관리하는 구성이 소개됩니다. 장시간 Recycle 운전(기동, 저부하)이 예상되면 쿨러 용량과 위치가 특히 중요합니다.
키워드: recycle cooler, suction temperature, 흡입온도, 쿨러, after cooler
부품: recycle-line
출처: [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: 성능 제어 방식(속도, IGV, 흡입 스로틀)은 어떻게 고르나요?
A: 가변속(Speed) 제어는 부분 부하 효율이 좋지만 유량과 헤드가 비례해서 변하는 경우에 효과가 크고, 헤드는 거의 일정한데 유량만 바뀌는 경우엔 이득이 적습니다. IGV(Inlet Guide Vane)는 정속기에서 턴다운과 효율을 개선하지만 기계 복잡도가 늘어납니다. 흡입 스로틀은 단순하지만 손실이 있고, 토출 스로틀은 비효율적이라 잘 권하지 않습니다. 한 자료는 흡입 스로틀(ITV)이 소형 정속 전동기 구동기(약 1.9 MW 이하)에 아직 쓰인다고 설명합니다(출처 기준).
키워드: performance control, speed control, IGV, inlet guide vane, suction throttling, ITV, discharge throttling, 성능제어
부품: driver, controller
출처: [Best practices: Turbo-compressor control monitoring](https://www.plantengineering.com/best-practices-turbo-compressor-control-monitoring/), [Centrifugal and Axial Compressor Control (Greg McMillan)](https://www.emersonautomationexperts.com/wp-content/uploads/2024/05/Centrifugal-and-Axial-Compressor-Control-Greg-McMillan.pdf)

### Q: Anti-surge 루프와 성능 제어 루프의 Decoupling 은 왜 필요한가요?
A: ASV 를 열면 유량뿐 아니라 토출 압력도 변하기 때문에, 독립된 압력 제어 루프와 서로 싸우면서 지속 진동이 생길 수 있습니다. 그래서 각 압축기의 Anti-surge 와 용량 제어를 서로 간섭하지 않게(Decoupled) 구성하라는 권고가 있습니다. 전용 CCS 는 이 Decoupling 로직을 내장하는 경우가 많으므로, 벤더 제안서에 해당 기능이 있는지 확인하세요.
키워드: decoupling, loop interaction, 루프 간섭, 진동, oscillation, performance controller
부품: controller, asv
출처: [Best practices: Turbo-compressor control monitoring](https://www.plantengineering.com/best-practices-turbo-compressor-control-monitoring/)

### Q: 병렬 압축기 Load sharing 의 기본 원리는 뭔가요?
A: CCC 측 설명에 따르면 병렬 Train 들을 Surge 로부터 '같은 상대 거리'에 두고 운전하는 것이 성능·안전·효율의 핵심입니다. 이렇게 하면 부하가 고르게 나뉘고, 한 대만 Recycle 하는 불필요한 낭비를 줄일 수 있습니다. 저부하에서도 Recycle 율을 Train 간에 조정(Recycle balancing)해 총 Recycle 을 최소화합니다. 단순 Base loading 방식과 비교할지 여부는 프로젝트 제어 철학에서 확인해야 합니다.
키워드: load sharing, parallel compressor, 병렬운전, equal distance to surge, recycle balancing, 부하분담
부품: controller, compressor
출처: [Optimising flow in parallel compressor networks (Honeywell CCC)](https://process.honeywell.com/us/en/ccc/support/industry-articles/optimising-flow-parallel-compressor)

### Q: 병렬 압축기 배관에서 꼭 챙겨야 할 게 있나요?
A: 병렬 압축기는 각각 자기 토출 Check valve 를 가져야 한다고 설명됩니다. 그래야 한 대가 Trip 되었을 때 다른 압축기의 고압 가스가 역류해 들어오지 않습니다. 또 각 Train 마다 독립된 Anti-surge 루프(ASV·FT)가 있어야 Load sharing 이 의미가 있습니다.
키워드: parallel, check valve, 역류, reverse flow, 개별 ASV, train
부품: recycle-line, asv, compressor
출처: [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

## Interface
### Q: Anti-surge 제어에 필요한 측정점은 무엇인가요?
A: 일반적으로 흡입 유량, 흡입 압력·온도, 토출 압력·온도가 필요하고, 압력·온도 보정으로 정확한 유량을 계산합니다. 유량이 운전점 위치를 정하는 1차 측정이며, 압력·온도는 Surge 선과의 거리를 계산하는 데 쓰입니다. ASV 에는 위치 송신기를 추가하기도 합니다. 계측 리스트(Instrument index)에서 이 측정점들이 CCS 전용인지, DCS 와 공유인지 구분해 두세요.
키워드: suction flow, suction pressure, discharge pressure, temperature, 측정점, compensation, 보정
부품: ft, pt-tt, flow-element
출처: [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/), [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge)

### Q: Anti-surge 용 유량 송신기는 얼마나 빨라야 하나요?
A: 한 자료는 Surge 알고리즘에 쓰는 송신기가 "less than 100 milliseconds" 로 응답해야 한다고 설명합니다(출처 기준). 또 다른 자료는 초당 5 샘플 수준의 송신기로는 약 200 ms 보다 빠른 유량 급락을 분해하지 못한다고 예시를 들고, 디지털 dP 송신기의 1차 지연을 줄여야 한다고 강조합니다. Damping 을 크게 걸면 Surge 신호가 뭉개지므로 송신기 Damping 설정도 검토 대상입니다.
키워드: fast transmitter, response time, 100 ms, sampling rate, damping, dP transmitter, 응답시간
부품: ft, flow-element
출처: [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge), [Rapid response (Digital Refining)](https://www.digitalrefining.com/article/1001227/rapid-response)

### Q: CCS 를 전용 제어기로 할지 DCS 안에 넣을지는 어떻게 판단하나요?
A: Emerson 자료는 전용 'Black box' Anti-surge 제어기가 예전보다 줄었고, 충분히 빠른 최신 DCS 플랫폼이 이 기능을 수행할 수 있다고 설명합니다. 핵심은 플랫폼이 아니라 실행 주기와 전체 응답 시간이 요구를 만족하는지입니다. 같은 자료는 API 670 5판 기준으로 로직 실행 100 ms 이하, Surge 감지 전체 응답 500 ms 미만을 언급합니다(출처 기준, 조항 번호 미확인). 결정은 압축기 벤더 요구와 프로젝트 Spec 으로 확정하세요.
키워드: dedicated controller, DCS integration, scan time, 실행주기, black box, CCC, DeltaV, API 670
부품: controller
출처: [Controlling Surge in Centrifugal Compressors (Emerson)](https://www.emersonautomationexperts.com/2019/control-safety-systems/controlling-surge-centrifugal-compressors/)

### Q: CCS 와 DCS·MMS·ESD 사이의 신호는 무엇을 확인하나요?
A: 일반적으로 DCS 와는 운전 상태·Setpoint·알람 통신, ESD/IPS 와는 Trip 신호(정지 시 ASV 강제 개방 등), MMS 와는 진동·축변위 상태 신호가 오갑니다. 각 신호가 하드와이어인지 통신인지, Fail-safe 방향이 맞는지가 검토 핵심입니다. 구체적인 신호 목록은 공개 자료로 일반화하기 어려워 '미확인'이며, 프로젝트 Interface 문서와 압축기 벤더 Interlock 도면으로 확인해야 합니다.
키워드: interface, hardwired, serial link, Modbus, trip signal, ESD, MMS, DCS 통신, 인터페이스
부품: signal, controller
출처: [Controlling Surge in Centrifugal Compressors (Emerson)](https://www.emersonautomationexperts.com/2019/control-safety-systems/controlling-surge-centrifugal-compressors/), [CCC Antisurge Control (Honeywell)](https://process.honeywell.com/us/en/products/turbomachinery-automation-systems/ccc-control-software/compressor-control/antisurge-control)

### Q: Limiting control 은 어떤 경우에 쓰나요?
A: 저흡입압이나 고토출압처럼 Surge 외의 운전 한계가 있을 때 Recycle 또는 Blow-off 밸브로 운전을 제한하는 기능입니다. CCC 제품 설명에서는 주 루프와 Limiting 루프 사이를 매끄럽게 전환하며 최대 3개 Limiting 루프를 구성할 수 있다고 합니다(출처 기준). 그 밖에 구동기 한계(모터 전류)와 Choke(Stonewall)도 고려해야 할 운전 한계로 소개됩니다.
키워드: limiting control, low suction pressure, high discharge pressure, choke, stonewall, motor current, 한계제어
부품: controller, asv, driver
출처: [CCC Antisurge Control (Honeywell)](https://process.honeywell.com/us/en/products/turbomachinery-automation-systems/ccc-control-software/compressor-control/antisurge-control), [Best practices: Turbo-compressor control monitoring](https://www.plantengineering.com/best-practices-turbo-compressor-control-monitoring/)

## 시험
### Q: 현장 Surge test 는 왜 하고 위험하지 않나요?
A: 실제 불안정 영역 경계를 찾는 확실한 방법이 Surge test 이기 때문에 수행하지만, 압축기와 생산에 위험을 주는 작업입니다. 현장 Surge 곡선은 측정 오차 등으로 공장(Shop) 곡선과 10% 이상 다를 수 있다는 실무 의견이 있어, 여러 운전 조건에서 시험해 SLL 을 만드는 경우가 있습니다. 그래서 Surge test 전에 ASV·배관 포함 전체 응답 시험을 먼저 하고, 벤더 입회로 절차를 승인받아 진행합니다.
키워드: surge test, field surge test, 서지 시험, commissioning, shop curve, SLL 확인
부품: compressor, controller, asv
출처: [Fine points of compressor surge control](https://www.controlglobal.com/control/loop-control/article/11319889/fine-points-of-compressor-surge-control)

### Q: Anti-surge 제어기 튜닝 시험은 어떻게 진행하나요?
A: Step test 는 제어기를 Manual 로 두고 밸브가 시트에서 떨어진 상태(예: 15~85% 개도)에서 수행한다는 실무 설명이 있습니다(출처 기준). 시험 중 압축기가 Recycle 상태이므로 실수로 Surge 로 밀리지 않도록 매우 주의해야 합니다. 제어는 보통 PI 이며, 큰 Surge 에는 Derivative 를 추가하기도 합니다.
키워드: step test, tuning, 튜닝, PI, manual mode, 15-85%, derivative
부품: controller, asv
출처: [Fine points of compressor surge control](https://www.controlglobal.com/control/loop-control/article/11319889/fine-points-of-compressor-surge-control), [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/)

### Q: FAT 에서 CCS 기능 시험은 어떻게 하나요?
A: 한 현장 절차 예시는 4-20 mA 신호 발생기로 유량 신호를 단계적으로 바꾸며 각 제어선에서 제어기 동작을 추적하고, 다른 단에도 반복합니다. 이 자료는 검증되지 않은 템플릿이라 참고용입니다. ASV 스트로크 시간 실측, Fail 동작, Trip 시 강제 개방도 FAT/SAT 항목으로 넣는 것이 좋습니다. 공식 절차는 벤더 FAT 절차서로 확정('미확인')합니다.
키워드: FAT, SAT, functional test, simulation, signal generator, 4-20mA, 기능시험, stroke test
부품: controller, signal, asv
출처: [Search: compressor surge test commissioning (Scribd Test Procedure)](https://www.scribd.com/document/322291177/Test-Procedure)

## 사양 검토 유의사항
### Q: Surge 시 Driver Trip 같은 동작은 어떻게 정하나요?
A: API 670 5판(2014.11)에 Surge 감지 항목이 추가되어 각 Surge 사이클을 감지하고 알람을 내도록 요구한다고 설명됩니다. 정해진 시간 창 안에 설정된 횟수의 Surge 가 일어나면 ASV 급개방이나 구동기 정지 같은 추가 동작을 선택적으로 하게 됩니다. 정확한 조항 번호와 횟수는 '미확인'이며 API 670 원문과 압축기 벤더 요구로 확정해야 합니다.
키워드: API 670, surge detection, surge counter, driver trip, alarm, 5th edition
부품: controller, driver
출처: [Rapid response (Digital Refining)](https://www.digitalrefining.com/article/1001227/rapid-response)

### Q: 최악 Surge 시나리오는 어떻게 정의하나요?
A: Emerson 자료는 상·하류에서 생길 수 있는 가장 빠른 유량 감소 사건(예: 공기 상실로 닫히는 Fail-close 밸브)으로 방지 시간을 정하라고 설명합니다. 대형 압축기일수록 압력 변화가 빠르고, 압축기와 제한부 사이 체적이 클수록 동특성이 느리고 완만해집니다. 그래서 동특성(Dynamic) 해석으로 ASV 속도·크기를 검증하는 것이 중요합니다.
키워드: worst case, dynamic simulation, 동특성 해석, fail-close valve, volume, 최악 시나리오
부품: asv, recycle-line, compressor
출처: [Controlling Surge in Centrifugal Compressors (Emerson)](https://www.emersonautomationexperts.com/2019/control-safety-systems/controlling-surge-centrifugal-compressors/)

### Q: CCS 사양 검토 때 자주 놓치는 항목은 무엇인가요?
A: ① 송신기 Damping·응답 시간 미기재, ② ASV 가 정상 Case 로만 사이징되고 기동·정지 Case 미검토, ③ ASV 와 Check valve 위치가 멀어 Recycle 체적이 큼, ④ 성능 루프와의 Decoupling 누락, ⑤ 가스 조성 변화 Case 미반영이 자주 언급되는 문제입니다. 각 항목은 위에 인용한 자료들이 권고하는 내용을 뒤집은 것이므로, 체크리스트로 쓰면 좋습니다. 프로젝트 Spec 과 대조하기 전까지는 모두 '미확인'입니다.
키워드: review checklist, 검토 체크리스트, 자주 하는 실수, damping, sizing case, decoupling
부품: ft, asv, recycle-line, controller
출처: [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/), [Best practices: Turbo-compressor control monitoring](https://www.plantengineering.com/best-practices-turbo-compressor-control-monitoring/)

### Q: 유량 측정 요소(Flow element)는 어디에 두나요?
A: Anti-surge 의 1차 측정은 유량이므로, 일반적으로 압축기 흡입 측 유량을 측정합니다(토출 측 측정 방식도 있음). 측정 정확도와 직관부, 차압 크기가 Surge 선과의 거리 계산 정확도를 좌우합니다. 현장·공장 Surge 곡선 차이가 측정 부정확도에서 온다는 의견도 있으므로 Flow element 설계를 가볍게 보면 안 됩니다. 구체 직관부 요구는 Flow element 공급사 자료로 확인('미확인')하세요.
키워드: flow element, orifice, venturi, suction flow, 직관부, straight run, 유량측정
부품: flow-element, ft
출처: [Protecting A Centrifugal Compressor From Surge](https://pgjonline.com/magazine/2012/march-2012-vol-239-no-3/features/protecting-a-centrifugal-compressor-from-surge), [Fine points of compressor surge control](https://www.controlglobal.com/control/loop-control/article/11319889/fine-points-of-compressor-surge-control)

## MR 작성
### Q: CCS MR 에 꼭 넣어야 할 항목은 무엇인가요?
A: 기능 범위(Anti-surge·성능·Load sharing·Limiting), 실행 주기·응답 시간 요구, 대상 압축기 구성(단수, 직렬·병렬), I/O 와 DCS/ESD 통신, 이중화, 시뮬레이션·FAT·현장 Surge test 지원 범위를 넣는 것이 일반적입니다. ASV·송신기를 CCS 벤더 범위에 넣을지 계장 Item 으로 따로 살지도 명확히 해야 합니다. 응답 시간 같은 수치는 API 670 원문·벤더 요구로 확정 전까지 '미확인'으로 기재하세요.
키워드: MR, material requisition, scope of supply, 공급범위, FAT, simulation, redundancy, 이중화
부품: controller, asv, ft
출처: [Controlling Surge in Centrifugal Compressors (Emerson)](https://www.emersonautomationexperts.com/2019/control-safety-systems/controlling-surge-centrifugal-compressors/), [CCC Antisurge Control (Honeywell)](https://process.honeywell.com/us/en/products/turbomachinery-automation-systems/ccc-control-software/compressor-control/antisurge-control)

### Q: ASV Datasheet 에서 확인할 핵심 항목은 무엇인가요?
A: 사이징 Case(기동·정지·정상), 최대 Cv 와 요구 Cv 비, 개·폐 스트로크 시간, Fail position, Trim 특성, 누설 등급, 출구 속도·소음, 액추에이터 부스터·Quick exhaust 유무입니다. 앞서 본 일반 권고치(1.8~2.2배, 0.5~2초, Class IV, 0.3 Mach 이하)와 비교하되, 다르면 충돌로 표시합니다. 최종값은 압축기 벤더·밸브 제조사·설계사 합의로 확정합니다.
키워드: ASV datasheet, Cv ratio, stroke time, fail open, leakage, noise, booster relay, 데이터시트
부품: asv
출처: [anti surge controller working principle](https://instrumentationtools.com/anti-surge-controller-working-principle/)

## 벤더 문서
### Q: CCS 벤더에게 받아야 할 문서는 무엇인가요?
A: 일반적으로 제어 철학(Control narrative), Surge map·SLL/SCL 정의, 동특성 해석 보고서, I/O·통신 리스트, Cause & Effect, FAT/SAT 절차서, 튜닝·Surge test 보고서가 필요합니다. 압축기 성능곡선은 압축기 벤더 문서이므로 CCS 벤더와의 인터페이스를 명확히 해야 합니다. 문서 목록 자체는 공개 자료로 확정할 수 없어 '미확인'이며, 프로젝트 VDRL 로 확정하세요.
키워드: vendor document, VDRL, control narrative, surge map, dynamic study, FAT procedure, 벤더문서
부품: controller, compressor
출처: [CCC Antisurge Control (Honeywell)](https://process.honeywell.com/us/en/products/turbomachinery-automation-systems/ccc-control-software/compressor-control/antisurge-control), [Fine points of compressor surge control](https://www.controlglobal.com/control/loop-control/article/11319889/fine-points-of-compressor-surge-control)
