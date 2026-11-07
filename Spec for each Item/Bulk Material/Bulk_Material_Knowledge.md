# Bulk Material Knowledge Base
> 웹 조사 2026-11-06. 일반 지식·공개 자료 요약이며 프로젝트 Spec 대조 전까지 '미확인'.

## 개념
### Q: 계장 Bulk Material 에는 어떤 자재가 들어가나요?
A: 계기 Hook-up 과 배선에 쓰이는 공통 자재로, 튜빙·압축 피팅·매니폴드·튜브 지지대(Tube tray/clamp), 케이블·케이블 글랜드·Junction box·케이블 트레이 등이 대표적입니다. 개별 계기처럼 Tag 별로 사지 않고 수량(길이·개수)으로 집계해 구매하기 때문에 'Bulk' 라고 부릅니다. 수량 산출은 Hook-up 도면과 케이블 스케줄에서 나옵니다.
키워드: bulk material, hook-up, 벌크자재, tubing, fitting, cable gland, junction box, cable tray, MTO
부품: tubing, fitting, gland, jb, tray, support, cable
출처: [Instrument Junction Boxes (controlandinstrumentation.com)](https://www.controlandinstrumentation.com/design/junction-box.html), [Swagelok Installer Pocket Guide (Purdue copy)](https://www.chem.purdue.edu/chemsafety/docs/chem/SwageLokPocketInstallerGuide.pdf)

## 튜빙·피팅
### Q: 계장 튜빙은 왜 경도(Hardness)를 따지나요?
A: 압축 피팅의 Ferrule 이 튜브 표면을 물어서 밀봉하는데, 튜브가 너무 단단하면 제대로 물리지 않아 누설·이탈이 생길 수 있습니다. 한 자료는 스테인리스 튜빙 경도를 Rb 90 이하, 권장 Rb 80 으로 제시합니다(출처 기준). ASTM A269 일반 등급도 90 HRB 이하 한도를 둔다고 소개되는데, 일부 유통 제품은 95 HRB 로 표기되어 있어 충돌이 있으니 Mill certificate 로 확인해야 합니다.
키워드: tubing hardness, 경도, HRB, Rb 80, Rb 90, ASTM A269, 316 SS, seamless, ferrule
부품: tubing, fitting
출처: [Common Causes of Imperfect Bends (instrumentationtools)](https://instrumentationtools.com/instrument-tube-fitting-installation-part-3/), [ASTM A269 (Scribd copy)](https://www.scribd.com/document/730305108/ASTM-A269)

### Q: 튜브 두께(Wall thickness)는 어떻게 정하나요?
A: 설계 압력·온도와 튜브 재질·외경에 따라 제조사 튜빙 압력 정격표에서 고릅니다. Swagelok 같은 제조사는 튜브 외경·두께별 허용 압력표와 피팅에 맞는 두께 범위를 카탈로그에 제공합니다. 두께가 너무 얇으면 피팅 체결 시 튜브가 찌그러지고, 너무 두꺼우면 Ferrule 이 충분히 물지 못할 수 있습니다. 구체 압력값은 이번 조사에서 원문을 확인하지 못해 '미확인'입니다.
키워드: wall thickness, 두께, pressure rating, 압력정격, tubing data, OD, 1/2 inch, 6 mm
부품: tubing
출처: [Swagelok Tube Fittings catalog MS-12-01](https://www.swagelok.com/downloads/webcatalogs/en/MS-12-01.PDF)

### Q: 압축 피팅은 어떻게 체결하고 확인하나요?
A: Swagelok 설치 가이드는 튜브를 피팅 본체 숄더에 닿을 때까지 끝까지 넣고 너트를 손으로 조인 뒤 규정 회전수만큼 조이도록 안내합니다. 초기 체결 후에는 Gap inspection gauge 를 너트와 본체 사이에 넣어 보고, 들어가지 않으면 충분히 조인 것, 들어가면 더 조여야 한다는 의미입니다. 사이즈별 회전수는 제조사 Installer Pocket Guide 로 확인('미확인')하세요.
키워드: compression fitting, 압축피팅, pull-up, gap inspection gauge, 갭게이지, finger tight, 체결
부품: fitting, tubing
출처: [Swagelok Installer Pocket Guide (Purdue copy)](https://www.chem.purdue.edu/chemsafety/docs/chem/SwageLokPocketInstallerGuide.pdf), [How the Swagelok Gap Inspection Gauge is Used](https://allentown.swagelok.com/en/services/education-and-training/our_tech_tip_videos/component_assembly_tips/gap-inspection-gauge-video)

### Q: Gap gauge 로 확인할 수 없는 경우는요?
A: Gap inspection gauge 는 첫 체결에만 유효하고 재조립한 피팅에는 쓰지 않습니다. Preswaging tool 로 조립한 피팅에도 쓰지 않는다고 안내됩니다. 또 과도하게 조인 경우는 게이지로 잡을 수 없는데, 과체결은 피팅에 응력을 주어 수명을 줄입니다. 압력이 걸린 상태에서 피팅을 조이거나 풀면 안 되고 반드시 감압 후 작업합니다.
키워드: reassembly, 재조립, preswaging, over-tightening, 과체결, depressurize, 감압
부품: fitting
출처: [Gap inspection gauge fitting story (Swagelok SoCal)](https://socal.swagelok.com/en/resources/downloads/fitting-stories/gap-inspection-gauge)

### Q: 서로 다른 제조사 피팅 부품을 섞어 써도 되나요?
A: 다른 제조사의 너트·Ferrule 을 본체와 섞는 것을 Interchange/Intermix 라고 합니다. 일부 제조사는 이를 위험하다고 보고, 섞어도 된다고 하는 SSP 조차 위험을 줄일 수는 있어도 완전히 없앨 수는 없다고 인정합니다. 혼용하면 제조사 보증과 압력 정격이 무효가 될 수 있어서, 프로젝트 Spec 에서 혼용 금지를 명시하는 경우가 많습니다. 프로젝트 기준은 '미확인'입니다.
키워드: intermix, interchange, 혼용, 다른 제조사, ferrule, warranty, 보증, Parker, Swagelok
부품: fitting
출처: [The truth about interchanging/intermixing instrumentation tube fittings (SSP)](https://info.myssp.com/blog/the-truth-about-interchanging-intermixing-instrumentation-tube-fittings)

### Q: 튜브 벤딩에서 자주 생기는 불량은 무엇인가요?
A: 반경이 너무 작거나 작은 튜브를 큰 반경 블록에 굽히면 납작해지고(Flattening), 튜브가 벤더에서 미끄러지거나 열처리 안 된 튜브는 꺾이며(Kink), 얇은 튜브는 주름(Wrinkle)이 생기기 쉽습니다. 단단한 튜브를 짧은 반경으로 굽히면 깨질 수도 있습니다. 클램프 블록으로 튜브를 단단히 고정하고 두께·경도에 맞는 반경을 써야 합니다. 최소 벤딩 반경 수치는 해당 자료에 없어 '미확인'입니다.
키워드: tube bending, 벤딩, flattening, kink, wrinkle, bend radius, 굽힘반경, bender
부품: tubing
출처: [Common Causes of Imperfect Bends (instrumentationtools)](https://instrumentationtools.com/instrument-tube-fitting-installation-part-3/)

### Q: 튜빙 라우팅에서 압력 손실이나 오프셋은 어떻게 처리하나요?
A: 한 자료는 90° 벤딩 한 번이 45° 두 번보다 압력 손실이 크다고 설명합니다. 오프셋은 30° 일 때 L = F × 2, 45° 일 때 L = F × 1.414 로 계산하며, Parker 핸드 벤더가 45° 에 맞춰져 있어 45° 를 권합니다(출처 기준). 불필요한 피팅을 줄이고 벤딩으로 방향을 바꾸면 누설 포인트도 줄어듭니다.
키워드: routing, offset bend, 45 degree, 오프셋, pressure drop, 압력손실, 라우팅
부품: tubing, fitting
출처: [Common Causes of Imperfect Bends (instrumentationtools)](https://instrumentationtools.com/instrument-tube-fitting-installation-part-3/)

### Q: 튜브 지지대(Support)는 어떻게 하나요?
A: 튜브는 연속형 튜브 트레이(예: TUBETRACK)나 채널 트레이 위에 클램프로 고정하는 방식이 많이 쓰입니다. 지지대와 튜브 재질이 다르면 갈바닉 부식이 생길 수 있어, 내식성 소재나 HDPE 클램프로 이종금속 접촉을 막는 제품도 있습니다. 지지 간격 표는 2차 블로그 자료밖에 확인하지 못해 '미확인'이며 제조사 설치 매뉴얼·프로젝트 Spec 으로 확정해야 합니다.
키워드: tube support, 튜브지지, tube tray, clamp, P-clamp, galvanic corrosion, 이종금속, support spacing
부품: support, tubing
출처: [TechLine Corrosion-Resistant Tubing Clamps](https://techlinemfg.com/noncorrosivetubingclamps.html), [TUBETRACK (James C. White)](https://issuu.com/jcwcomarketing/docs/tubetrack_printable), [Swagelok P-clamp support SS-TBP6](https://products.swagelok.com/en/c/p-clamp-supports/p/SS-TBP6)

### Q: 튜빙 재질을 고를 때 고온 조건은 어떻게 보나요?
A: 한 자료는 300 계열 스테인리스를 약 425 °C(800 °F) 이상에서 쓸 때 유체 적합성을 고려해야 한다고 설명합니다(출처 기준). 해양·염분 환경에서는 316 SS 보다 고합금 재질을 검토하는 경우도 있지만, 이번 조사에서 근거를 확인하지 못해 '미확인'입니다. 튜브와 피팅 재질은 맞추는 것이 원칙이며, 구리 튜브에 황동 피팅처럼 관행적 예외가 있습니다.
키워드: tubing material, 재질, 316 SS, high temperature, 고온, brass, copper, material compatibility
부품: tubing, fitting
출처: [Common Causes of Imperfect Bends (instrumentationtools)](https://instrumentationtools.com/instrument-tube-fitting-installation-part-3/), [SS 316 Instrumentation Tubing SOP (Industrial Monitor Direct)](https://industrialmonitordirect.com/blogs/knowledgebase/ss-316-instrumentation-tubing-sop-fittings-supports-and-installation)

## 매니폴드
### Q: 3-valve 매니폴드와 5-valve 매니폴드는 뭐가 다른가요?
A: 3-valve 는 블록 밸브 2개와 균압(Equalizing) 밸브 1개로, 차압 송신기를 과압에서 보호하고 교정·정비 때 공정에서 격리합니다. 5-valve 는 블록 2개, 균압 2개, 벤트(Bleed) 1개로 구성되어 갇힌 압력을 원격 위치로 배출할 수 있습니다. 공통 규칙은 블록 밸브 두 개가 모두 열린 상태에서 균압 밸브를 절대 열지 않는 것입니다.
키워드: manifold, 3-valve manifold, 5-valve manifold, equalizing valve, block valve, bleed, 매니폴드, DP transmitter
부품: fitting
출처: [What is valve manifold? 3 valve and 5 valve manifolds (Automation Forum)](https://automationforum.co/valve-manifold-3-valve-5-valve-manifolds/), [3-Valve/5-Valve Manifold (Yokogawa)](https://www.yokogawa.com/mx/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/pressure-accessories/instrument-manifolds/3-valve5-valve-manifold)

### Q: 3-valve 매니폴드 조작 순서는 어떻게 되나요?
A: 한 자료의 서비스 투입 순서는 모두 닫음 → 균압 열기 → 고압 블록 열기 → 균압 닫기 → 저압 블록 열기이고, 제거는 저압 블록 닫기 → 균압 열기 → 고압 블록 닫기입니다. 다만 어느 쪽 블록을 먼저 닫느냐는 자료마다 다르며, Emerson 글은 스팀 서비스에서 고압측 공동이 남는 문제 때문에 저압측을 먼저 닫는다고 설명합니다. 제조사 절차와 현장 안전 규칙을 따르세요.
키워드: manifold operation, 조작순서, zeroing, 영점, equalize, isolation sequence, steam
부품: fitting
출처: [What is valve manifold? (Automation Forum)](https://automationforum.co/valve-manifold-3-valve-5-valve-manifolds/), [Being Consistent with Manifold Valve Operation (Emerson Exchange)](https://emersonexchange365.com/products/measurement-instrumentation/f/level-pressure-temperature-tank-gauging/8718/being-consistent-with-manifold-valve-operation)

## 케이블 글랜드
### Q: 방폭 지역 케이블 글랜드는 어떻게 고르나요?
A: IEC 60079-14 기준으로 글랜드의 방폭 방식은 연결되는 기기의 보호 수준과 같거나 높아야 한다고 설명됩니다. 글랜드 사이즈는 케이블 외경에 맞아야 하고, 테이프나 수축 튜브로 케이블을 키워 맞추면 안 됩니다. 케이블 갑옷(Armour) 종류에 맞는 클램핑 방식도 골라야 합니다. 조항 번호는 원문 확인 전 '미확인'입니다.
키워드: cable gland, 케이블글랜드, IEC 60079-14, Ex d, Ex e, explosion proof, 방폭, cable OD
부품: gland, cable
출처: [IECEx Cable Gland Selection Guide (Thorne & Derrick)](https://www.powerandcables.com/iecex-cable-gland-selection/)

### Q: Barrier 글랜드는 언제 필요한가요?
A: Ex d 기기에서는 케이블이 원형·조밀하고 압출 베딩·시스를 가지며 비흡습성 충전재를 쓰는 경우가 아니면 Barrier(컴파운드) 글랜드가 필요하다고 소개됩니다. 영국 HSE 가 '새 규칙'에 따른 설치가 안전하지 않을 수 있다고 경고한 점을 들어, 의심스러우면 Barrier 글랜드를 쓰라는 권고도 있습니다. Ex e 에서도 케이블을 따라 가스가 이동할 우려가 있으면 Barrier 글랜드를 고려합니다.
키워드: barrier gland, compound gland, 컴파운드글랜드, Ex d, gas migration, extruded bedding, HSE
부품: gland
출처: [IECEx Cable Gland Selection Guide (Thorne & Derrick)](https://www.powerandcables.com/iecex-cable-gland-selection/), [To Barrier or Not to Barrier (Source IEx)](https://www.sourceiex.com/Catalogs/To%20Barrier%20or%20Not%20to%20Barrier.pdf)

### Q: IEC 60079-14 2024년 판에서 글랜드 관련 바뀐 점이 있나요?
A: Element 의 백서는 2024년 8월 발행된 IEC 60079-14:2024 가 특히 Ex d 용도의 케이블 글랜드에 새 요구를 도입했다고 설명합니다. 글랜드와 밀봉 가스켓을 함께 시험·인증하는 방향도 언급됩니다. 프로젝트가 어느 판을 적용하는지 먼저 확인하고, 세부 변경 내용은 원문으로 확인('미확인')해야 합니다.
키워드: IEC 60079-14:2024, 2024 edition, 개정, gland certification, sealing washer, Ex d
부품: gland
출처: [Understanding the changes to IEC 60079-14:2024 (Element)](https://www.element.com/resources/white-papers/understanding-the-changes-to-iec-60079-142024)

### Q: 글랜드 형식 코드(E1W, E1FX 등)는 무슨 뜻인가요?
A: 한 자료에 따르면 W 는 SWA/AWA 강선 갑옷, X 는 편조(Braid), T·Y·Z 는 다른 갑옷 형식이고, A~E 는 밀봉·클램핑 방식(예: E 는 내·외피 모두 클램프·밀봉)입니다. 예를 들어 E1W 는 내·외피 IP66 씰을 가진 SWA 케이블용입니다(출처 기준). 코드 체계는 제조사마다 다를 수 있으므로 Hawke·CMP 등 실제 카탈로그로 확인하세요.
키워드: gland code, E1W, E1FX, E2W, SWA, braid, armour, 글랜드형식, Hawke, CMP
부품: gland, cable
출처: [IECEx Cable Gland Selection Guide (Thorne & Derrick)](https://www.powerandcables.com/iecex-cable-gland-selection/)

### Q: 글랜드 재질과 IP 등급은 어떻게 확인하나요?
A: 글랜드 재질은 기기·케이블 갑옷과 맞추는 게 이상적이고, 일반적으로 무전해 니켈 도금 황동이 많이 쓰이며 부식 환경에서는 10 μm 이상 도금을 권하는 자료가 있습니다(출처 기준). 아주 부식성이 강한 환경은 스테인리스를 검토합니다. IP 등급 유지를 위해 밀봉 와셔가 필요할 수 있고, 그 와셔가 글랜드와 함께 시험된 것인지 IECEx 인증서로 확인합니다.
키워드: gland material, nickel plated brass, 니켈도금황동, stainless steel, IP66, sealing washer, IECEx certificate
부품: gland
출처: [IECEx Cable Gland Selection Guide (Thorne & Derrick)](https://www.powerandcables.com/iecex-cable-gland-selection/)

## Junction Box
### Q: Junction box 크기는 어떻게 정하나요?
A: 단자 수와 폭, 케이블 수·인입구 수가 박스 크기를 결정하고, 실드 케이블은 단자가 더 필요해 박스가 커집니다. 한 자료는 배선 편의를 위해 작은 것보다 큰 박스를 고르라고 권하고, 약 200~500 mm 크기 범위를 예로 듭니다(출처 기준). 탈착식 기어 플레이트와 DIN 레일을 쓰면 조립이 빨라집니다.
키워드: junction box sizing, JB, 정션박스, terminal, gear plate, DIN rail, screen, 크기
부품: jb
출처: [Instrument Junction Boxes (controlandinstrumentation.com)](https://www.controlandinstrumentation.com/design/junction-box.html)

### Q: Junction box 예비(Spare) 용량은 어떻게 두나요?
A: 한 자료는 향후 증설을 위해 메인 멀티코어 케이블에 최소 2쌍 이상의 예비 페어를 남기는 것을 좋은 관행으로 소개합니다(출처 기준). 예비 단자 비율(예: %)은 공개 자료로 확인하지 못했으므로 '미확인'이며 프로젝트 Spec 으로 확정해야 합니다. 예비 인입구도 블랭킹 플러그 처리 방식과 함께 고려하세요.
키워드: spare, 예비, spare pairs, spare terminals, future expansion, multicore, 증설
부품: jb, cable
출처: [Instrument Junction Boxes (controlandinstrumentation.com)](https://www.controlandinstrumentation.com/design/junction-box.html)

### Q: Ex e 와 Ex d Junction box 는 무엇이 다른가요?
A: Ex e 박스는 보통 가스켓으로 볼트 체결한 글랜드 플레이트에 구멍을 뚫어 쓰고, 인증서에 등재된 단자만 사용해야 합니다. Ex d 박스는 본체에 직접 나사 가공하며, 쓰지 않는 구멍은 인증된 블랭킹 플러그로 막습니다. 글랜드는 박스와 같은 위험지역 기준을 만족해야 합니다. 제품 예로 R. Stahl 8118 시리즈 같은 IP66 Ex e 박스가 있습니다.
키워드: Ex e junction box, Ex d junction box, increased safety, flameproof, blanking plug, certified terminal, IP66, Stahl 8118
부품: jb, gland
출처: [Instrument Junction Boxes (controlandinstrumentation.com)](https://www.controlandinstrumentation.com/design/junction-box.html), [Series 8118 junction boxes (R. Stahl)](https://r-stahl.com/en/in/products/junction-and-terminal-boxes/grp-ex-e-junction-and-terminal-boxes/series-8118-junction-boxes-38240/)

### Q: Junction box 접지와 설치 위치는 어떻게 하나요?
A: 한 자료는 레일의 접지 단자나 내·외부 접지 스터드(예: 내부 M6, 외부 M10, SS316L)를 쓰고 문-본체, 기어플레이트-본체를 녹황색 본딩선으로 연결하라고 설명합니다(출처 기준). 박스는 밝고 접근하기 쉬운 곳에 두고, 최소 4개의 외부 취부 러그를 쓰는 예가 제시됩니다. 최소 IP 는 실외 기준 IP56 을 예로 듭니다. 프로젝트 값과 다르면 충돌로 표시하세요.
키워드: earthing, 접지, earth stud, bonding, mounting lug, IP56, 316L, 설치위치
부품: jb
출처: [Instrument Junction Boxes (controlandinstrumentation.com)](https://www.controlandinstrumentation.com/design/junction-box.html)

### Q: IS 회로용 Junction box 는 어떻게 표시하나요?
A: 한 자료는 IS 신호가 들어가는 박스에 흰 글씨의 파란 외부 태그 "Intrinsically Safe Circuits" 를 붙이라고 설명합니다(출처 기준). IS 회로 JB 에는 Ex e 박스가 자주 쓰입니다. 박스 내부의 IS/비IS 분리 규칙은 아래 분리 항목과 프로젝트 Spec 을 함께 확인하세요.
키워드: intrinsically safe, IS, 본질안전, blue tag, 파란 태그, IS junction box, labeling
부품: jb
출처: [Instrument Junction Boxes (controlandinstrumentation.com)](https://www.controlandinstrumentation.com/design/junction-box.html)

## 케이블·트레이
### Q: IS 케이블과 비IS 케이블은 어떻게 분리하나요?
A: 여러 자료가 같은 외함·트레이 안에서 IS 와 비IS 회로를 최소 50 mm 띄우거나 접지된 금속 격벽·절연 격벽으로 분리하라고 설명합니다(출처 기준). IS 케이블을 색으로 구분할 때는 외피를 연한 파란색으로 하고, 다른 회로에는 연한 파란색을 쓰지 않습니다. 이 수치가 IEC 60079-14 의 어느 조항인지는 확인하지 못해 '미확인'입니다.
키워드: IS segregation, 50 mm, 분리거리, light blue sheath, 하늘색, partition, IEC 60079-14, intrinsic safety
부품: cable, tray, jb
출처: [Cables in Hazardous Areas (ATEX shop wiki)](https://www.atexshop.com/atex-wiki/specific-equipment-16/cables-in-hazardous-areas-025), [Intrinsically Safe Wiring Practices (Hach manual)](https://www.manualslib.com/manual/1630603/Hach-911.html?page=11)

### Q: 계장 케이블과 동력 케이블 이격 거리는 얼마인가요?
A: 이번 조사에서는 동력-계장 케이블 최소 이격 거리를 신뢰할 수 있는 공개 자료로 확인하지 못했습니다. 그래서 이 값은 '미확인'이며 프로젝트 Spec 이나 회사 표준으로 확정해야 합니다. IEC 61537 계열 자료는 트레이 시스템이 케이블 분리에 쓰일 수 있다고만 언급합니다.
키워드: segregation, 이격거리, power cable, instrument cable, noise, EMC, 동력케이블
부품: cable, tray
출처: [IEC Insights (cable tray segregation)](https://insights.ieci.org/wp-content/uploads/flipbook/31/files/basic-html/page13.html)

### Q: 케이블 트레이 형식(Ladder, Perforated)은 어떻게 고르나요?
A: 벤더 자료는 Ladder 트레이가 무거운 동력 케이블과 긴 스팬에 적합하고, Perforated(타공) 트레이는 저압 동력·데이터 혼합이나 계장 케이블 경로에 많이 쓰인다고 설명합니다. 이는 일반 지침이지 설계 규칙은 아닙니다. 국제 기준은 IEC 61537, 미국은 NEMA VE 1(CSA C22.2 No.126.1 병행)이 하중 시험 등을 다룹니다.
키워드: cable tray, ladder tray, perforated tray, 케이블트레이, IEC 61537, NEMA VE 1, load class, span
부품: tray
출처: [Types of Cable Trays (Electrical Volt)](https://www.electricalvolt.com/types-of-cable-tray), [Understanding NEMA standards for cable tray systems (Agilix)](https://www.goagilix.com/blog/understanding-nema-standards-for-cable-tray-systems/)

### Q: 트레이 하중 등급과 적재율(Fill)은 어떻게 검토하나요?
A: NEMA VE 1 은 스팬별 하중 등급(예: 8B, 8C 등)으로 트레이를 분류하고, 한 벤더는 2.4 m 스팬에서 Ladder 8C, Perforated 8B 로 시험했다고 밝힙니다(출처 기준). 벤더 주장은 실제 시험 보고서로 확인해야 합니다. 적재율 계산은 NEC Article 392 와 NEMA VE 1 을 1차 참고로 소개하며, 프로젝트 기준은 '미확인'입니다.
키워드: load class, 하중등급, NEMA 8C, span, fill ratio, 적재율, NEC 392
부품: tray, support
출처: [Understanding NEMA standards for cable tray systems (Agilix)](https://www.goagilix.com/blog/understanding-nema-standards-for-cable-tray-systems/)

### Q: IEC 61537 은 어떤 표준인가요?
A: 케이블 트레이와 케이블 래더 시스템의 구조, 시험, 사양을 다루는 국제 표준입니다. 2001년 판은 2006년 판으로 대체되어 폐지되었다고 소개되므로 최신판을 확인해야 합니다. 프로젝트가 IEC 계열인지 NEMA 계열인지에 따라 하중 등급 표기 방식이 달라집니다.
키워드: IEC 61537, cable tray standard, cable ladder, 트레이표준, edition
부품: tray
출처: [IEC 61537:2001 (SCC)](https://scc-ccn.ca/standardsdb/standards/2038714)

### Q: IS 계장 케이블 제품 사양에서 볼 점은?
A: IS 용 실드 제어 케이블(예: Lapp ÖLFLEX EB CY)은 파란 PVC 외피와 주석도금 동 편조 실드를 갖고 IEC/EN 60079-14 관련 조항을 근거로 든다고 데이터시트에 적혀 있습니다. 이는 공급사 주장이라 표준 원문과 대조가 필요합니다. IS 루프 계산을 위해 케이블 정전용량·인덕턴스 값도 데이터시트에서 받아야 하나, 기준값은 '미확인'입니다.
키워드: IS cable, instrument cable, screened cable, braid screen, capacitance, inductance, Lapp, blue sheath
부품: cable
출처: [ÖLFLEX EB (Lapp)](https://products.lappgroup.com/online-catalogue/power-and-control-cables/various-applications/intrinsically-safe-circuits/oelflex-eb.html)

## 자주 하는 실수
### Q: Bulk Material 검토에서 자주 하는 실수는 무엇인가요?
A: ① 피팅 제조사 혼용, ② 튜브 경도·두께를 피팅 제조사 권고와 대조하지 않음, ③ 글랜드 사이즈를 테이프로 맞춤, ④ Ex d 박스에 Barrier 필요 여부 미검토, ⑤ IS 케이블 분리·표시 누락이 자주 지적됩니다. 모두 위 자료들이 경고하는 사항이며 프로젝트 Spec 대조 전 '미확인' 체크리스트로 쓰세요.
키워드: review checklist, 자주 하는 실수, intermix, hardness, gland size, barrier, IS segregation
부품: fitting, tubing, gland, jb, cable
출처: [IECEx Cable Gland Selection Guide (Thorne & Derrick)](https://www.powerandcables.com/iecex-cable-gland-selection/), [The truth about intermixing tube fittings (SSP)](https://info.myssp.com/blog/the-truth-about-interchanging-intermixing-instrumentation-tube-fittings)

## MR 작성
### Q: 튜빙·피팅 MR 에 넣을 항목은 무엇인가요?
A: 튜브 재질·규격(예: ASTM A269 이음매 없음), 외경·두께, 최대 경도, 표면 상태, 피팅 형식(Double ferrule 등)·재질·연결 규격, 제조사 혼용 금지 여부, 설계 압력·온도를 넣는 것이 일반적입니다. 경도 한도는 ASTM 한도와 피팅 제조사 권장치가 다를 수 있으니 둘 다 확인하세요. 수치는 프로젝트 Spec 대조 전 '미확인'입니다.
키워드: MR, tubing specification, fitting specification, ASTM A269, double ferrule, hardness, 구매사양
부품: tubing, fitting
출처: [ASTM A269 (Scribd copy)](https://www.scribd.com/document/730305108/ASTM-A269), [Common Causes of Imperfect Bends (instrumentationtools)](https://instrumentationtools.com/instrument-tube-fitting-installation-part-3/)

### Q: 글랜드·JB MR 에 넣을 항목은 무엇인가요?
A: 글랜드는 방폭 방식(Ex d/Ex e/Barrier), 케이블 갑옷 형식과 외경 범위, 나사 규격, 재질·도금, IP 등급, 인증(IECEx/ATEX)을 넣습니다. JB 는 방폭 방식, 재질, IP 등급, 단자 수·형식(인증서 등재 단자), 예비 수량, 인입구 수·크기, 접지 스터드, IS 표시를 넣습니다. 나사 규격(Metric/NPT)은 이번 조사 자료에서 다루지 않아 '미확인'입니다.
키워드: MR, gland MR, junction box MR, IECEx, ATEX, thread, entries, terminal, 구매사양
부품: gland, jb
출처: [IECEx Cable Gland Selection Guide (Thorne & Derrick)](https://www.powerandcables.com/iecex-cable-gland-selection/), [Instrument Junction Boxes (controlandinstrumentation.com)](https://www.controlandinstrumentation.com/design/junction-box.html)

## 벤더 문서
### Q: Bulk Material 벤더에게 받아야 할 문서는 무엇인가요?
A: 튜브 Mill certificate(경도·화학성분), 피팅 카탈로그·압력 정격표·설치 가이드, 글랜드·JB 방폭 인증서(IECEx/ATEX)와 Ex 등급 표시, 트레이 하중 시험 보고서, 케이블 데이터시트(IS 파라미터 포함)가 일반적입니다. 특히 글랜드는 밀봉 와셔를 포함한 인증 범위를 확인해야 합니다. 구체 목록은 프로젝트 VDRL 로 확정('미확인')하세요.
키워드: vendor document, mill certificate, IECEx certificate, test report, catalog, 인증서, 벤더문서
부품: tubing, fitting, gland, jb, tray, cable
출처: [Swagelok Tube Fittings catalog MS-12-01](https://www.swagelok.com/downloads/webcatalogs/en/MS-12-01.PDF), [IECEx Cable Gland Selection Guide (Thorne & Derrick)](https://www.powerandcables.com/iecex-cable-gland-selection/)
