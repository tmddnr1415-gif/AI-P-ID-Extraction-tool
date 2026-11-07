# Transmitter Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: Smart(HART) 트랜스미터는 기존 아날로그 트랜스미터와 무엇이 다른가요?
A: Smart 트랜스미터는 센서 신호를 디지털로 처리한 뒤 4~20 mA 로 내보내고, 같은 선로 위에 HART 디지털 신호를 실어 PV·진단·설정값을 주고받습니다. 그래서 내부에 센서 처리부(A/D)와 출력부(D/A)가 따로 있고, 교정도 sensor trim 과 output trim 으로 나뉩니다. 디지털 PV 를 쓰는 시스템이라면 sensor trim 이 특히 중요합니다.
키워드: smart transmitter, HART, 4-20 mA, digital PV, 디지털 트랜스미터, A/D, D/A, PT, TT, LT, FT
부품: housing, sensor, display
출처: [Fluke - How to simplify maintenance of a HART pressure transmitter](https://www.fluke.com/es-ve/informacion/blog/calibracion/how-simplify-maintenance-hart-pressure-transmitter), [control.com - LRV and URV settings, digital trim](https://control.com/textbook/instrument-calibration/lrv-and-urv-settings-digital-trim-digital-transmitters/)

### Q: Gauge, Absolute, DP 압력 트랜스미터는 어떻게 구분해 쓰나요?
A: Gauge 는 대기압 기준, Absolute 는 진공 기준, DP 는 두 압력의 차를 잽니다. DP 트랜스미터는 유량(orifice 등)·레벨·필터 차압에 쓰이며, 높은 정압(static pressure)에서 정확도가 떨어지는 정압 영향이 있습니다. Fuji Electric 설명으로는 Gauge·Absolute 센서에는 이 정압 영향이 없습니다.
키워드: gauge pressure, absolute pressure, differential pressure, DP, PDT, 정압 영향, static pressure effect
부품: sensor, flange
출처: [Fuji Electric - How to calculate accuracy of a pressure transmitter and TPE](https://fujielectric.fr/en/blog/how-calculate-accuracy-pressure-transmitter-and-what-total-probable-error)

### Q: TPE(Total Probable Error)는 무엇이고 왜 봐야 하나요?
A: TPE 는 기준 정확도(reference accuracy), 주변온도 영향, 정압 영향을 제곱합 제곱근(RSS)으로 합친 값으로, 실제 설치 상태 성능에 가깝습니다. 데이터시트의 reference accuracy 만 보면 현장 성능을 과대평가하기 쉽습니다. Emerson 예시는 기준 정확도 0.025% 와 정압 영향 0.140% 로 TPE 약 ±0.155% of span 을 제시합니다(Emerson 출처 기준).
키워드: TPE, total probable error, RSS, reference accuracy, ambient temperature effect, static pressure effect, 총 오차
부품: sensor
출처: [Fuji Electric - TPE](https://fujielectric.fr/en/blog/how-calculate-accuracy-pressure-transmitter-and-what-total-probable-error), [Emerson - How to calculate pressure transmitter calibration intervals](https://d1-live.emerson.com/documents/automation/technical-note-how-to-calculate-pressure-transmitter-calibration-intervals-en-7432098.pdf)

### Q: Turndown(Rangedown)이 정확도에 어떤 영향을 주나요?
A: 센서 최대 범위(URL)보다 교정 Span 을 작게 잡을수록 오차가 % of span 기준으로 커집니다. 한 비교 기사는 정확도를 기준 정확도와 turndown 효과 포함 정확도 중 큰 값으로 봐야 한다고 정리합니다. Yokogawa 는 TPE 를 rangedown 1:1~5:1 조건으로 표기하는 예가 있으니, 벤더 간 비교 시 같은 rangedown 조건인지 확인하세요.
키워드: turndown, rangedown, URL, span, 정확도 저하, accuracy comparison, 벤더 비교
부품: sensor
출처: [Process Online - Comparing DP transmitter accuracy](https://www.processonline.com.au/content/instrumentation/article/comparing-differential-pressure-transmitter-accuracy-1243567999), [Yokogawa GS01C33C10-01EN](https://web-material3.yokogawa.com/GS01C33C10-01EN.pdf)

### Q: DP 트랜스미터의 정압 영향은 보정할 수 있나요?
A: 정압 영향은 zero 와 span 양쪽에 나타날 수 있으며, zero 성분은 운전 라인 압력에서 zero 교정을 하면 상당 부분 제거할 수 있다고 설명됩니다. span 성분은 남으므로 고정압 DP 유량 측정이라면 데이터시트의 static span effect 를 확인합니다. TPE 에 zero 정압 영향을 넣는지는 자료마다 다르니 벤더 정의를 확인하세요.
키워드: static pressure effect, zero effect, span effect, line pressure zero, 정압 보정, high static DP
부품: sensor, manifold
출처: [ABB 611SS datasheet](https://library.e.abb.com/public/b929ef3e24cf023fc1256d9d0043c748/SSE611SSDIF.pdf), [Instrumentation Tools - Transmitter performance and calibration frequency](https://instrumentationtools.com/how-to-calculate-transmitter-performance-and-calibration-frequency)

## 선정·사이징
### Q: Remote seal(격막 씰) 충전액(fill fluid)은 어떻게 고르나요?
A: Emerson 은 공정 온도와 주변 온도 한계 안에서 동작하도록 충전액을 고르라고 안내합니다. 또한 coplanar, in-line, capillary 구성마다 충전액 최소·최대 온도 표가 따로 있으므로 실제 구성의 표를 봐야 합니다. 진공 서비스라면 충전액 증기압 곡선도 확인 대상입니다.
키워드: fill fluid, 충전액, remote seal, diaphragm seal, Rosemount 1199, silicone, Syltherm XLT, vapor pressure, 진공
부품: flange, sensor
출처: [Emerson - Technical note 1199 direct mount connection guidelines](https://emerson.com/documents/automation/technical-note-1199-direct-mount-connection-guidelines-rosemount-en-77464.pdf), [Rosemount 1199 manual](https://core.instrumart.com/assets/Rosemount-1199-manual.pdf)

### Q: 추운 지역에서 고온용 충전액을 쓰면 무엇이 문제인가요?
A: Emerson 자료에 따르면 DC704·DC705 같은 고온용 충전액은 낮은 주변온도에서 점도가 너무 높아져 응답 시간이 허용 수준을 벗어날 수 있습니다. capillary 시스템은 충전액 대부분이 주변 온도에 노출되기 때문에 이 영향이 큽니다. 고온 공정 + 혹한 지역 조합이면 벤더에 응답시간 계산을 요청하세요.
키워드: cold ambient, 혹한, viscosity, 점도, DC704, DC705, response time, 응답 시간, capillary
부품: flange
출처: [Emerson - Technical note 1199 direct mount](https://emerson.com/documents/automation/technical-note-1199-direct-mount-connection-guidelines-rosemount-en-77464.pdf), [Spartan Controls - Rosemount Thermal Optimizer](https://www.spartancontrols.com/getattachment/0d1ef917-db3a-45dd-80a4-2056002677eb/SC_RosemountThermalOptimizer_Sp2020.pdf)

### Q: 양쪽 remote seal 의 capillary 길이를 같게 하는 이유는?
A: 양쪽 충전액 양이 같은 balanced 시스템이면 온도 변화로 생기는 seal 온도 오차가 양쪽에서 상쇄되어 최소화됩니다. 다만 capillary 높이 차에 의한 head 온도 영향은 balanced 여도 남는다고 설명됩니다. diaphragm 두께, seal 크기, capillary 길이·내경도 온도 오차에 영향을 줍니다.
키워드: balanced system, capillary length, 대칭 구성, seal temperature effect, head temperature effect, tuned system
부품: flange
출처: [Keco Controls - 3051L & 1199 manual](https://kecocontrols.com/uploads/3051L%20&1199%205%20page%20Manual.pdf)

### Q: 온도 트랜스미터에서 RTD 센서 매칭(Callendar-Van Dusen)은 왜 하나요?
A: 개별 RTD 를 교정해 얻은 Callendar-Van Dusen 상수를 트랜스미터에 입력하면 표준 곡선 대신 그 센서 고유 곡선으로 계산해 시스템 오차가 줄어듭니다. Rosemount 3144P 자료의 예시로는 150 °C, 0~200 °C span 조건에서 표준 RTD 는 약 ±1.05 °C, 매칭 RTD 는 약 ±0.18 °C 로 비교됩니다(해당 매뉴얼 예시 기준). 정밀 온도 측정이 필요한 곳에서 검토할 만한 옵션입니다.
키워드: sensor matching, Callendar-Van Dusen, CVD constants, RTD, Pt100, 3144P, 센서 매칭, 온도 트랜스미터
부품: sensor, housing
출처: [Rosemount 3144P reference manual (manualsonline)](https://homeappliance.manualsonline.com/manuals/mfg/emerson_process_management_emerson_electric_co/3144p.html?p=25), [Emerson PKG 214C sensor and 3144P transmitter](https://d1-auth.emerson.com/en-us/catalog/rosemount-pkg-214c-sensor-and-3144p-transmitter)

### Q: RTD 는 3선식과 4선식 중 무엇을 쓰나요?
A: 4선식은 리드선 저항 영향을 측정에서 제거할 수 있어 정확도에 유리하고, 3선식은 리드선 저항이 같다는 가정으로 보상합니다. Rosemount 3144P Quick Start 자료에 따르면 단일 엘리먼트 RTD 는 4선식으로 공급되며, 남는 리드를 절연 처리해 3선식으로도 쓸 수 있습니다. 트랜스미터 설정의 선 수와 실제 결선이 일치해야 합니다.
키워드: RTD 3-wire, 4-wire, 3선식, 4선식, lead wire resistance, 리드선 저항, Pt100
부품: sensor, conduit
출처: [Rosemount 3144P FF Quick Start Guide](https://manualmachine.com/rosemount/3144ptemperaturetransmitterswithfoundationfieldbusprotocol/26852457-quick-start-guide)

### Q: 레벨 측정은 DP 와 GWR(Guided Wave Radar) 중 무엇이 나은가요?
A: DP 는 초기 비용이 낮고 익숙하며 재질·연결 선택지가 많다는 장점이 있지만, 비중(밀도)으로 레벨을 환산하므로 밀도 변화에 영향을 받습니다. GWR 은 impulse line·remote seal·밀도 보상이 필요 없어 유지보수가 적고 비중 변화 영향이 없다는 설명이 있습니다. 다만 GWR 은 유전율 대비, probe 선정, 코팅·폼 등 조건을 따져야 하므로 공정 조건으로 판단합니다.
키워드: DP level, GWR, guided wave radar, Levelflex, specific gravity, 밀도 보상, 레벨 측정 선정, foam
부품: sensor, process-conn
출처: [Control Global - GWR vs DP transmitters for liquid level](https://www.controlglobal.com/measure/level/whitepaper/11364536/transmitters-guided-wave-radar-vs-differential-pressure-transmitters-for-liquid-level-measurement-control-global), [Emerson FAQ - Which level technology is best](https://emerson.com/documents/automation/article-faq-how-to-determine-which-level-measurement-technology-best-for-your-specific-applications-en-10983526.pdf)

### Q: 밀폐 탱크 DP 레벨에서 Dry leg 와 Wet leg 는 어떻게 고르나요?
A: Dry leg 는 저압측 배관에 기체만 있는 방식으로, 증기가 응축되지 않고 공정 온도가 상온에 가까울 때 씁니다. Wet leg 는 저압측을 액체로 채워 기준 액주를 일정하게 유지하는 방식으로, 증기가 응축되기 쉬울 때 씁니다. Dry leg 에 응축수가 차면 지시가 드리프트하고, Wet leg 는 동결이나 누설로 기준이 바뀔 수 있다는 점을 같이 검토합니다.
키워드: dry leg, wet leg, 드라이 레그, 웨트 레그, closed tank, condensate, 응축, reference leg
부품: flange, process-conn
출처: [Instrumentation Tools - DP transmitter dry leg wet leg calculations](https://instrumentationtools.com/dp-transmitter-dry-leg-wet-leg-calculations), [Instrumentation Tools - Closed tank level measurement using DP](https://instrumentationtools.com/closed-tank-level-measurement-using-dp-transmitters)

### Q: Zero elevation 과 Zero suppression 은 무엇인가요?
A: Wet leg 처럼 저압측 액주가 있으면 LRV 가 음수 쪽으로 이동하는데 이를 zero elevation 이라 하고, 트랜스미터가 탭보다 아래에 있어 고압측에 추가 액주가 걸리면 이를 빼 주는 것이 zero suppression 입니다. 계산식은 해당 액주의 밀도×중력×높이로 보정하며, 4 mA·20 mA 값에 각각 반영합니다. 밀도는 온도에 따라 변하므로 설계 밀도 조건을 데이터시트에 명시하세요.
키워드: zero elevation, zero suppression, LRV, URV, 레인지 설정, wet leg calculation, 액주 보정
부품: sensor
출처: [Automation Forum - Zero suppression and zero elevation](https://automationforum.co/zero-suppression-and-zero-elevation/), [Automation Forum - Zero elevation and suppression in level measurement](https://automationforum.co/zero-elevation-zero-suppression-level-measurement/)

### Q: DP 유량 측정에서 Square root 는 어디서 처리하나요?
A: orifice 차압은 유량의 제곱에 비례하므로 유량은 차압의 제곱근입니다. 트랜스미터와 DCS(또는 FF AI block) 모두 제곱근 처리가 가능하므로 한 곳에서만 해야 하며, 두 번 하거나 빠뜨리면 유량이 틀어집니다. 공개 자료는 25% DP 에서 약 50% 유량이 되는지로 확인하는 방법을 소개합니다.
키워드: square root extraction, 제곱근, DP flow, orifice, 유량, double square root, L_TYPE, AI block
부품: sensor
출처: [Industrial Monitor Direct - Extracting square root for DP flow](https://industrialmonitordirect.com/blogs/knowledgebase/extracting-square-root-in-plcs-for-dp-flow-measurement), [Industrial Monitor Direct - Configuring FF DP flow meters](https://industrialmonitordirect.com/blogs/knowledgebase/configuring-foundation-fieldbus-dp-flow-meters)

### Q: Low flow cut-off 는 왜 설정하나요?
A: 제곱근 함수는 0 근처에서 기울기가 매우 커서 작은 차압 노이즈가 큰 유량 흔들림으로 보입니다. Yokogawa 는 설정점 이하에서 출력을 0 또는 선형으로 바꾸는 low-cut 모드를 설명합니다. cut-off 도 square root 처럼 한 곳에서만 설정해야 실제 저유량이 지워지지 않습니다.
키워드: low flow cut-off, low cut, 저유량 차단, square root noise, Yokogawa DPharp, 노이즈
부품: sensor
출처: [Yokogawa - Low flow cut-off application note](https://www.yokogawa.com/nl/library/resources/application-notes/low-flow-cut-off)

## 설치
### Q: 액체 서비스 DP 트랜스미터의 탭 위치와 설치 높이는?
A: Rosemount 3051 Quick Start 기준으로 액체는 배관 측면에 탭을 두고 트랜스미터를 탭 옆이나 아래에 설치합니다. 이렇게 하면 기포가 impulse line 에서 공정 쪽으로 빠져나갑니다. 드레인/벤트 밸브는 위쪽을 향하도록 장착하라고 안내합니다.
키워드: liquid service, tap orientation, 탭 위치, below taps, impulse line, 기포, drain vent
부품: flange, process-conn, manifold
출처: [Emerson - Rosemount 3051 Quick Start Guide](https://d1-live.emerson.com/documents/automation/quick-start-guide-rosemount-3051-pressure-transmitter-3051cf-series-flow-meter-en-89454.pdf)

### Q: 가스 서비스 트랜스미터는 어떻게 설치하나요?
A: 가스는 배관 상부나 측면에 탭을 두고 트랜스미터를 탭 옆이나 위에 설치합니다. 그래야 응축액이 impulse line 에서 공정 쪽으로 흘러내려 액이 고이지 않습니다. 액이 고이면 양쪽 레그 액주 차이로 zero 오차가 생깁니다.
키워드: gas service, above taps, 탭 상부, condensate, 응축액, impulse line slope
부품: flange, process-conn
출처: [Emerson - Rosemount 3051 Quick Start Guide](https://d1-live.emerson.com/documents/automation/quick-start-guide-rosemount-3051-pressure-transmitter-3051cf-series-flow-meter-en-89454.pdf), [PI Process Instrumentation - Tap orientation for DP flow element in gas service](https://www.piprocessinstrumentation.com/instrumentation/flow-measurement/differential-pressure/article/15554364/tap-orientation-for-dp-flow-element-in-gas-service)

### Q: 스팀 서비스 DP 트랜스미터는 어떻게 설치하나요?
A: Rosemount 3051 Quick Start 기준으로 스팀은 배관 측면 탭, 트랜스미터는 탭 옆이나 아래에 두고 impulse line 을 물로 채웁니다. 물이 채워진 레그가 고온 스팀으로부터 센서를 보호하고 양쪽 액주를 같게 유지합니다. 원격 설치 시 응축수가 배관으로 돌아가도록 기울기를 주라는 안내도 있습니다.
키워드: steam service, water filled impulse line, 스팀, 응축수, condensate pot, wet leg
부품: flange, manifold
출처: [Emerson - Rosemount 3051 Quick Start Guide](https://d1-live.emerson.com/documents/automation/quick-start-guide-rosemount-3051-pressure-transmitter-3051cf-series-flow-meter-en-89454.pdf), [Emerson - Rosemount 485 Annubar flanged Flo-Tap Quick Start](https://www.emerson.com/documents/automation/quick-start-guide-rosemount-485-annubar-flanged-flo-tap-assembly-en-75326.pdf)

### Q: Impulse line 기울기는 왜 중요한가요?
A: impulse tubing 은 액체가 고이지 않고 공정 쪽으로 흘러 빠지도록(가스) 또는 기체가 빠지도록(액체) 기울여야 합니다. 기울기가 잘못되면 기포나 액이 갇혀 레그 간 액주 차가 생기고 이것이 그대로 측정 오차가 됩니다. 기울기 수치는 회사 Hook-up 표준으로 확인하세요(미확인).
키워드: impulse line slope, 기울기, gas pocket, liquid trap, impulse tubing, hook-up
부품: process-conn
출처: [Processing Magazine - Quiz corner: DP tap orientation](https://www.processingmagazine.com/process-control-automation/instrumentation/article/55346053/quiz-corner-dp-tap-orientation)

### Q: 3-valve manifold 는 어떻게 구성되고 어떻게 조작하나요?
A: 3-valve manifold 는 고압측 차단, 저압측 차단, 그리고 두 측을 잇는 equalizing valve 로 구성됩니다. 투입 시에는 equalizing 을 연 상태에서 차단밸브를 천천히 열고 누설을 확인한 뒤 equalizing 을 닫는 식입니다. 순서를 잘못하면 센서에 한쪽 압력이 과도하게 걸릴 수 있어 매뉴얼과 현장 절차를 따라야 합니다.
키워드: 3-valve manifold, 3way manifold, equalizing valve, block valve, 균압 밸브, 투입 절차
부품: manifold
출처: [Instrumentation Tools - 3 valve manifold operation](https://instrumentationtools.com/3-valve-manifold-operation), [ICS Schneider - 3 and 5 valve manifolds](https://www.ics-schneider.de/drei-und-fuenfventilbloecke-am-differenzdrucktransmitter-bedienen-ausgleichsventil-und-absperrfolge-richtig-nutzen/?lang=en)

### Q: 5-valve manifold 는 3-valve 와 무엇이 다른가요?
A: 5-valve manifold 는 차단 2개, equalizing 2개에 vent/bleed 밸브가 추가되어 갇힌 압력을 빼거나 현장 교정 연결이 쉽습니다. 가스나 유독 유체처럼 equalizing 중 공정 유체가 섞이거나 배출되면 곤란한 경우에 유리합니다. 조작 순서는 벤더·현장마다 다르므로 투입 전 절차서를 확인하세요.
키워드: 5-valve manifold, bleed valve, vent, double equalizing, 5way manifold, 현장 교정
부품: manifold
출처: [Instrumentation Tools - 5 valve manifold operation](https://instrumentationtools.com/5-valve-manifold-operation), [ICS Schneider - 3 and 5 valve manifolds](https://www.ics-schneider.de/drei-und-fuenfventilbloecke-am-differenzdrucktransmitter-bedienen-ausgleichsventil-und-absperrfolge-richtig-nutzen/?lang=en)

### Q: Manifold 로 DP 트랜스미터 zero 를 볼 때 주의점은?
A: 한 포럼 답변은 equalizing valve 를 열기 전에 트랜스미터를 공정에서 격리해야 한다고 강조합니다. 격리 없이 equalizing 을 열면 고압측 공정 유체가 저압측으로 흘러 레그 상태가 바뀌거나 오차가 생길 수 있습니다. Emerson 커뮤니티 글도 제품 매뉴얼과 현장 안전 문서를 먼저 보라고 권합니다.
키워드: zeroing, zero check, equalize, isolation, 격리, 영점 확인, manifold procedure
부품: manifold
출처: [control.com - Correct DP transmitter isolation procedure](https://control.com/forums/threads/correct-dp-transmitter-isolation-procedure.45293/post-45293), [Emerson Exchange 365 - Being consistent with manifold valve operation](https://emersonexchange365.com/products/measurement-instrumentation/f/level-pressure-temperature-tank-gauging/8718/being-consistent-with-manifold-valve-operation)

## Interface·통신
### Q: HART 와 Foundation Fieldbus(FF) 중 어느 것을 선택하나요?
A: HART 는 4~20 mA 아날로그 위에 디지털을 얹는 방식이라 제어는 DCS 에서 하고 진단은 polling 으로 읽습니다. FF 는 완전 디지털 버스로 한 공개 비교 자료 기준 multidrop 최대 32대(HART 는 15대) 연결이 가능하고, PID 를 필드 기기에서 돌릴 수도 있습니다(해당 출처 기준). 실제 선택은 DCS 벤더 생태계와 프로젝트 Spec 이 결정합니다.
키워드: HART, Foundation Fieldbus, FF, H1, multidrop, 통신 프로토콜, PID in field, polling
부품: housing, conduit
출처: [Automation Forum - Foundation Fieldbus vs HART](https://automationforum.co/foundation-fieldbus-vs-hart-communication-protocols/), [Azbil - HART/Fieldbus solutions](https://aa-industrial.azbil.com/jp/en/solution/hart-foundation-fieldbus/hfbs-whatis)

### Q: DD(Device Description) 파일은 왜 필요한가요?
A: DD 는 기기의 각 파라미터를 기술한 파일로, DCS·핸드헬드 같은 호스트가 기기를 이해하고 설정하는 데 씁니다. HART 와 FF 모두 같은 DD 언어를 쓰지만 FF 는 block 구조라 구성 방식이 다릅니다. 기기 Revision 과 DD Revision 이 호스트에 등록돼 있는지 FAT/통합시험 전에 확인해야 합니다.
키워드: DD, device description, DDL, device revision, host integration, 호스트 등록, FDT DTM
부품: housing
출처: [Azbil - HART/Fieldbus solutions](https://aa-industrial.azbil.com/jp/en/solution/hart-foundation-fieldbus/hfbs-whatis), [Scribd - HART vs FF paper](https://www.scribd.com/doc/251793343/Hart-v-Ff-Paperfinal)

### Q: FISCO 는 무엇인가요?
A: FISCO(Fieldbus Intrinsically Safe Concept)는 FF H1 과 Profibus PA 에서 본질안전 설치를 단순화하는 모델입니다. 한 공개 자료는 FISCO·FNICO·High Power Trunk 개념이 Ex 지역에 설치할 수 있는 기기 수를 크게 늘렸다고 설명합니다. 세그먼트 설계 시 전원·barrier 와 기기 인증이 FISCO 기준을 만족하는지 확인합니다.
키워드: FISCO, FNICO, high power trunk, intrinsic safety fieldbus, Profibus PA, segment design, 세그먼트
부품: housing, conduit
출처: [Industrial Monitor Direct - FF vs Profibus DP/PA comparison](https://industrialmonitordirect.com/blogs/knowledgebase/foundation-fieldbus-vs-profibus-dppa-technical-comparison)

### Q: NAMUR NE43 고장 신호는 몇 mA 인가요?
A: NE43 은 4~20 mA 기기의 고장 신호를 정상 범위 밖, 즉 3.6 mA 이하 또는 21 mA 이상으로 내도록 제안합니다(공개 해설 기준). 그 사이 일부 구간은 측정값 포화(saturation) 영역으로 구분되어 측정 정보와 고장 경보를 분리합니다. DCS 측 고장 판정값과 트랜스미터 alarm 방향(High/Low)을 맞추는 것이 중요합니다.
키워드: NAMUR NE43, NE 43, 3.6 mA, 21 mA, failure alarm, saturation, 고장 신호, fail high, fail low
부품: housing
출처: [Electrical Volt - What is NAMUR NE 43](https://www.electricalvolt.com/what-is-namur-ne-43), [Instrumentation Tools - Transmitters 4-20 mA current alarms](https://instrumentationtools.com/transmitters-4-20ma-current-alarms/amp/?format=pdf)

## 위험지역 (IEC 60079)
### Q: Ex ia, Ex ib, Ex ic 는 어느 Zone 에 쓸 수 있나요?
A: ICS Schneider 자료의 표 기준으로 Ex ia 는 Zone 0 까지, Ex ib 는 Zone 1 까지, Ex ic 는 Zone 2 까지 사용 가능하며 실제 적용은 개별 인증서에 따릅니다(해당 출처 기준). Zone 1 승인 기기를 Zone 0 에 자동으로 쓸 수 없다는 점도 강조됩니다. 기기 인증서의 EPL·가스 그룹·온도등급을 Hazardous area 도면과 대조하세요.
키워드: Ex ia, Ex ib, Ex ic, intrinsic safety, 본질안전, Zone 0, Zone 1, Zone 2, IEC 60079-11, EPL
부품: housing, conduit
출처: [ICS Schneider - Process transmitters in Ex areas (ATEX, HART, 4-20 mA)](https://www.ics-schneider.de/prozesstransmitter-im-ex-bereich-atex-hart-und-4-20-ma-sicher-einsetzen/?lang=en)

### Q: 본질안전(Ex i) 트랜스미터만 있으면 방폭이 끝나나요?
A: 아닙니다. 본질안전은 루프 전체 개념이라 안전지역과 위험지역 사이에 barrier 나 isolator 같은 associated apparatus 가 필요합니다. 또 트랜스미터의 ATEX 인증이 Zone 구분이나 방폭 문서(explosion-protection document)를 대신하지 않는다고 설명됩니다. 루프 entity 파라미터 검증은 별도로 해야 합니다.
키워드: associated apparatus, barrier, isolator, IS loop, entity parameter, 루프 검증, ATEX
부품: housing, conduit
출처: [ICS Schneider - Process transmitters in Ex areas](https://www.ics-schneider.de/prozesstransmitter-im-ex-bereich-atex-hart-und-4-20-ma-sicher-einsetzen/?lang=en)

### Q: Ex d(내압방폭) 트랜스미터는 Zone 0 에 쓸 수 있나요?
A: 공개 자료의 표는 Ex d 를 Zone 0 에 부적합으로, Ex ia 를 Zone 0 사용 가능으로 표시합니다. Ex d 는 하우징이 내부 폭발을 견디고 화염 전파를 막는 방식이라 cable gland·conduit entry 와 커버 체결 상태가 방폭 성능의 일부입니다. 해당 자료 일부는 신뢰도가 낮으므로 IEC 60079-14 와 기기 인증서로 최종 확인하세요.
키워드: Ex d, flameproof, 내압방폭, Zone 0, cable gland, conduit entry, cover, IEC 60079-1, IEC 60079-14
부품: housing, cover, conduit
출처: [Industrial Monitor Direct - Ex d, Ex e, Ex i junction boxes](https://industrialmonitordirect.com/blogs/knowledgebase/exd-ex-e-and-ex-i-junction-boxes-hazardous-area-applications)

## SIL (IEC 61508)
### Q: SIL 2 용 트랜스미터를 고를 때 무엇을 봐야 하나요?
A: Pepperl+Fuchs 평가 보고서에 따르면 IEC 61508-1 저요구(low demand) 모드에서 SIL 2 PFDavg 목표는 10⁻³ 이상 10⁻² 미만입니다(해당 출처 기준). 기기 자체 PFDavg 는 proof test 주기에 따라 달라지므로, 보고서의 주기별 값을 SIF 계산에 넣어야 합니다. SIL 인증은 특정 기기 Revision 에 대한 것이므로 공급 Revision 이 인증 범위인지 확인합니다.
키워드: SIL 2, IEC 61508, PFDavg, low demand, proof test interval, SIF, 안전 계기, functional safety
부품: sensor, housing
출처: [Pepperl+Fuchs - Functional safety assessment report](https://files.pepperl-fuchs.com/webcat/navi/productInfo/cert/cert0416.pdf), [ABB CE 261 SIL2 IEC 61508](https://library.e.abb.com/public/be12c7d663585099c12576dd004a9078/CE_261_SIL2_IEC61508-EN.pdf)

### Q: HFT, SFF, Proven-in-use 는 어떤 관계인가요?
A: IEC 61508 은 기기 유형(Type B 등), SFF(안전 고장 비율), HFT(하드웨어 고장 허용)의 조합으로 달성 가능한 SIL 을 제한합니다. 공개 평가 보고서 예로는 Type B 에서 SFF 60~90% 구간이면 SIL 2 에 HFT 1 이 필요하고, ABB 보고서는 proven-in-use 기기에 한해 HFT 0 을 허용하되 최종 판단은 사용자에게 둡니다(해당 출처 기준). 그래서 단일(1oo1) 구성 가능 여부는 SIS 담당자가 판단해야 합니다.
키워드: HFT, hardware fault tolerance, SFF, safe failure fraction, Type B, proven in use, prior use, 1oo1, 1oo2, IEC 61511
부품: sensor
출처: [Pepperl+Fuchs - Functional safety assessment report](https://files.pepperl-fuchs.com/webcat/navi/productInfo/cert/cert0416.pdf), [ABB 2600T/2000T SIL FMEDA](https://library.e.abb.com/public/e092d274d0e4f461c1257213004b5c50/CE_265_267_269_SIL_FMEDA_EN.pdf)

### Q: SIL 트랜스미터 벤더에게 어떤 문서를 받아야 하나요?
A: 기능안전 인증서(또는 평가 보고서), FMEDA 결과(고장률·SFF·PFDavg), 그리고 Safety Manual 이 기본입니다. Safety Manual 에는 proof test 절차·범위와 사용 조건이 정의되어 있으며, ABB 인증서는 PFDavg 를 이중화 구조·proof test 주기·coverage 와 대조해 확인하라고 명시합니다. Emerson 3051 평가서처럼 'Safety Manual 에 따라 설계되어야 한다'는 조건이 붙는 경우가 많습니다.
키워드: safety manual, FMEDA, SIL certificate, functional safety certificate, proof test coverage, vendor document, VDRL
부품: housing
출처: [Emerson - Functional safety certificate assessment 3051](https://d1-live.emerson.com/documents/automation/functional-safety-certificate-assessment-3051-pressure-transmitter-en-7468180.pdf), [ABB CE 261 SIL2 IEC 61508](https://library.e.abb.com/public/be12c7d663585099c12576dd004a9078/CE_261_SIL2_IEC61508-EN.pdf)

## 시험·교정
### Q: Rerange 와 Sensor trim 은 무엇이 다른가요?
A: Rerange 는 LRV·URV 를 바꿔 4~20 mA 출력 범위만 조정하는 것으로, 압력을 가하지 않고도 할 수 있으며 공장 특성곡선은 바뀌지 않습니다. Sensor trim 은 실제 기준 압력을 가해 디지털 PV 자체를 보정하는 것이라 정확한 장비가 필요하고 잘못하면 성능이 나빠질 수 있습니다. 교정 기록서에는 어느 작업을 했는지 구분해 남겨야 합니다.
키워드: rerange, sensor trim, LRV, URV, characterization curve, 레인지 변경, 센서 트림, HART calibration
부품: sensor
출처: [control.com - LRV and URV settings, digital trim](https://control.com/textbook/instrument-calibration/lrv-and-urv-settings-digital-trim-digital-transmitters/), [Rosemount 3051N manual (manualsonline)](https://cellphone.manualsonline.com/manuals/mfg/emerson/3051n.html?p=26)

### Q: 출력이 틀릴 때 Sensor trim 과 Output trim 중 무엇을 하나요?
A: HART 로 읽은 PV 를 기준 압력계와, 루프 전류를 멀티미터와 각각 비교합니다. PV 는 맞는데 전류가 틀리면 output(D/A) trim, PV 자체가 틀리면 sensor trim 을 합니다. LRV 0, URV 100 으로 설정했다고 중간점 정확도가 보장되지 않으므로 실제 압력을 가한 점검이 필요합니다.
키워드: output trim, analog trim, D/A trim, sensor trim, loop current, 멀티미터, 진단, troubleshooting
부품: sensor, housing
출처: [control.com - LRV and URV settings, digital trim](https://control.com/textbook/instrument-calibration/lrv-and-urv-settings-digital-trim-digital-transmitters/), [Fluke - HART pressure transmitter maintenance](https://www.fluke.com/es-ve/informacion/blog/calibracion/how-simplify-maintenance-hart-pressure-transmitter)

### Q: 트랜스미터 교정 주기는 어떻게 정하나요?
A: Emerson 기술 노트는 요구 성능, TPE, 연간 안정성(stability) 값을 이용해 교정 주기를 계산하는 방법을 제시합니다. 즉 허용 오차에서 설치 TPE 를 뺀 여유를 연간 드리프트로 나누는 개념입니다. 계산 예시 값은 해당 기술 노트 원문을 참조하고, 회사 정비 기준이 있으면 그것이 우선입니다.
키워드: calibration interval, 교정 주기, stability, 장기 안정성, drift, TPE, maintenance
부품: sensor
출처: [Emerson - How to calculate pressure transmitter calibration intervals](https://d1-live.emerson.com/documents/automation/technical-note-how-to-calculate-pressure-transmitter-calibration-intervals-en-7432098.pdf), [Instrumentation Tools - Transmitter performance and calibration frequency](https://instrumentationtools.com/how-to-calculate-transmitter-performance-and-calibration-frequency)

## 사양 검토 유의사항
### Q: 벤더 간 정확도 비교 시 흔히 생기는 오류는?
A: 데이터시트의 reference accuracy 만 비교하고 turndown·정압·주변온도 영향을 빠뜨리는 것입니다. 한 비교 자료는 데이터시트가 zero·span 오차는 쓰면서 turndown 오차를 빠뜨리는 경우가 많다고 지적합니다. 같은 span, 같은 정압, 같은 온도 변화 조건으로 TPE 를 다시 맞춰 비교하세요.
키워드: accuracy comparison, 정확도 비교, reference accuracy, TPE, turndown error, bid evaluation, 기술 평가
부품: sensor
출처: [Scribd - Comparing transmitter performance using TPE](https://www.scribd.com/document/384004577/Comparing-Transmitter-Performance-Using-Total-Probable-Error), [Process Online - Comparing DP transmitter accuracy](https://www.processonline.com.au/content/instrumentation/article/comparing-differential-pressure-transmitter-accuracy-1243567999)

### Q: Remote seal 트랜스미터 사양 검토에서 놓치기 쉬운 점은?
A: 충전액 온도 한계를 공정 온도만 보고 주변 최저온도를 빼먹는 경우가 흔합니다. capillary 길이와 설치 높이 차에 따른 온도 오차·응답시간도 벤더에 계산을 요청해야 합니다. 진공 서비스는 충전액 증기압 조건도 확인합니다.
키워드: remote seal review, fill fluid limit, ambient minimum, capillary length, response time, vacuum, 사양 검토
부품: flange, sensor
출처: [Emerson - Technical note 1199 direct mount](https://emerson.com/documents/automation/technical-note-1199-direct-mount-connection-guidelines-rosemount-en-77464.pdf), [Keco Controls - 3051L & 1199 manual](https://kecocontrols.com/uploads/3051L%20&1199%205%20page%20Manual.pdf)

## MR 작성
### Q: 압력/DP 트랜스미터 MR·데이터시트에 꼭 넣어야 할 항목은?
A: 측정 형식(Gauge/Absolute/DP), 교정 Range 와 센서 범위, 공정 조건(압력·온도·정압), 접액부 재질과 공정 연결, 통신(HART/FF)과 NE43 alarm 방향, 방폭 형식(Ex d/Ex ia 등)과 인증, SIL 요구 여부, manifold·remote seal 포함 여부가 핵심입니다. 벤더 제품 데이터시트(예: Rosemount 3051 PDS)의 주문 코드 항목과 대조하면 누락을 줄일 수 있습니다. 회사 MR 양식 항목과 구체 값은 '미확인'입니다.
키워드: transmitter MR, datasheet, 데이터시트, ordering code, range, wetted material, HART, Ex, SIL, manifold, remote seal
부품: housing, sensor, flange, process-conn, manifold, conduit
출처: [Emerson - Rosemount 3051 product data sheet](https://www.emerson.com/documents/automation/rosemount-3051-pressure-transmitter-3051cf-series-flow-meter-en-73992.pdf), [ICS Schneider - Process transmitters in Ex areas](https://www.ics-schneider.de/prozesstransmitter-im-ex-bereich-atex-hart-und-4-20-ma-sicher-einsetzen/?lang=en)

### Q: 트랜스미터 공급 시 받아야 할 벤더 문서는?
A: 일반적으로 데이터시트·외형도, 방폭 인증서, 교정 성적서, SIL 적용 시 기능안전 인증서·FMEDA·Safety Manual, 설치·운전 매뉴얼(Quick Start 포함)을 받습니다. 방폭 인증서는 Zone 구분을 대신하지 않으므로 Hazardous area 도면과 대조가 필요합니다. 회사 VDRL 의 정확한 목록과 제출 시점은 프로젝트 Spec 확인 전까지 '미확인'입니다.
키워드: vendor document, VDRL, certificate, Ex certificate, calibration certificate, safety manual, FMEDA, quick start guide, 벤더 문서
부품: housing
출처: [Emerson - Functional safety certificate assessment 3051](https://d1-live.emerson.com/documents/automation/functional-safety-certificate-assessment-3051-pressure-transmitter-en-7468180.pdf), [Emerson - Rosemount 3051P Quick Start Guide](https://emerson.com/documents/automation/quick-start-guide-rosemount-3051p-pressure-transmitter-en-193124.pdf)

## 자주 하는 실수
### Q: DP 유량 루프에서 흔한 설정 실수는?
A: 트랜스미터와 DCS 양쪽에서 square root 를 모두 걸거나 둘 다 안 거는 것, 그리고 low flow cut-off 를 두 곳에 걸어 실제 저유량을 지우는 것이 대표적입니다. 루프 시험 때 25% DP 입력에서 유량이 약 50% 로 표시되는지 확인하면 잡을 수 있습니다. 또한 square root 만으로는 가스 밀도 변화가 보정되지 않으므로 밀도 보상 필요 여부를 따로 검토합니다.
키워드: double square root, 이중 제곱근, low cut duplication, loop test, 루프 시험, density compensation, 밀도 보상
부품: sensor
출처: [Industrial Monitor Direct - DP flow transmitter square root extraction](https://industrialmonitordirect.com/blogs/knowledgebase/dp-flow-transmitter-square-root-extraction-with-k-factor), [Yokogawa - Low flow cut-off](https://www.yokogawa.com/nl/library/resources/application-notes/low-flow-cut-off)
