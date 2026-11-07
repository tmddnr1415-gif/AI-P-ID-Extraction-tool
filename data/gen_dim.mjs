import { writeFileSync } from "node:fs";
const S = (title,url,note)=>({title,url,note});
const U = "미확인";
const items = {
 "BallValve_ESDV": { item:"Ball Valve", type:"ESDV", dims:{ face_to_face: U, flange: U, actuator_iso5211: U }, notes:"Trunnion 볼밸브 FTF 기준이 공급사별로 ASME B16.10 또는 API 6D로 다름 → 프로젝트 Spec으로 확정", sources:[
   S("Valvotubi Class 300 trunnion (FTF B16.10, flange B16.5)","https://app.bilbaoexhibitioncentre.com/en/exhibitor/VALVOTUBI-IND/product/Vlvula-de-bola-Trunnion-mounted-ball-valves-RF-ANSI-class-300/33767/?idioma=US","링크만"),
   S("Williams Valve trunnion catalog (FTF API 6D, flange B16.5, API 6FA fire safe)","https://static1.squarespace.com/static/61cc92f8aa6b5f348b889cd5/t/641e10c1ca8e7f73aeaf4f3e/1679692468788/WilliamsValve_TrunnionCatalog_V15.pdf","링크만"),
   S("Hy-Lok API 6D/6A ball valve catalog (Class 150/300 표, 참고용)","https://www.fitok.org.ru/brands/hy-lok/pdfs/api-6d-and-6a-ball-valves-2021.pdf","수치 미추출")]},
 "GlobeValve_Control": { item:"Globe Valve", type:"Control Valve", dims:{ face_to_face: U }, notes:"ISA 75.08 시리즈는 유료/AI 입력 제한 → 표 수치 미수록", sources:[
   S("ISA 75.08.01 Class 125-600 flanged globe","https://standards.globalspec.com/std/1112167/isa-75-08-01","링크만"),
   S("ISA 75.08.06 Class 900-2500 flanged globe","https://standards.globalspec.com/std/1586628/isa-75-08-06","링크만")]},
 "ButterflyValve_Control": { item:"Butterfly Valve", type:"Control Valve / MOV", dims:{ face_to_face: U }, notes:"FTF 기준 API 609 / ASME B16.10 / ISO 5752 중 프로젝트 지정 필요", sources:[
   S("API STD 609 (범위: lug/wafer NPS 3-48 등)","https://online.standard.no/en/api-std-609","링크만"),
   S("API 609 e8 preview","https://www.api.org/~/media/files/publications/whats%20new/609_e8%20pa.pdf","링크만")]},
 "PSV": { item:"PSV", type:"PSV", dims:{ center_to_face: U, orifice_area: U }, notes:"API 526 표 미확인. LESER: 플랜지 치수가 B16.5를 초과할 수 있음(API 526 §2.4)", sources:[
   S("LESER Type 526 data sheet","https://www.unitecd.com/ecatalog-files/leser-5262-6594-api-series-data-sheet-2.pdf","링크만"),
   S("Neutrium API 526 orifice areas","https://neutrium.net/tags/api-526/","링크만")]},
 "Transmitter": { item:"Transmitter", type:"Pressure (Coplanar)", dims:{ coplanar_overall: U, manifold: U }, notes:"Siemens DS III 값(DN25/PN40 ∅D 115, H2≈52)은 front-flush 형이라 coplanar에 사용 금지", sources:[
   S("Emerson Rosemount 2051 datasheet (Dimensional drawings 절)","https://emerson.com/documents/automation/product-data-sheet-rosemount-2051-pressure-transmitter-en-73206.pdf","링크만"),
   S("AS-Schneider W2RA 2-valve manifold","https://www.as-schneider.com/gb/en/Products-Services/Instrumentation-Valves-and-Manifolds/E-Series-Manifolds/Direct-Mount-Manifolds-Integral-Style/2-Valve-Manifolds-W2RA-Type.html","링크만")]},
 "FieldGauge": { item:"Field Gauge", type:"Pressure Gauge NG100", dims:{ case_front_dia_mm:100, case_rear_dia_mm:96, height_H_mm:135, depth_t_mm:50, connection:"G 1/2 bottom" }, notes:"Loesi 개별 제품 값(EN 837-1 표기). 일반 EN 837-1 치수와 다를 수 있음 → 제조사 도면 대조 필요", sources:[
   S("Loesi double-scale gauge NG100","https://loesi.de/shop/en/pressure-gauge-double-scale-0-40-bar-thread-g1-2-ng100-connection-bottom-valcon.html","수치 인용"),
   S("RS PRO 100mm gauge datasheet","https://docs.rs-online.com/5702/A700000012202765.pdf","컬럼 정의 미확인")]},
 "BulkMaterial": { item:"Bulk Material", type:"Instrument Hook-up", dims:{ standard_detail: U }, notes:"Stanchion/표준 상세는 회사·프로젝트 표준 라이브러리 확인 필요", sources:[
   S("Impulse piping installation precautions","https://automationforum.co/impulse-piping-installation-precautions-how-to-connect-impulse-piping-to-transmitter-manifold-valves/","개념"),
   S("Yokogawa EJA110E manual (3-valve manifold 설치 순서)","https://www.manualsdir.com/manuals/360033/yokogawa-eja110e.html?page=28","개념")]},
 "DCS": { item:"DCS", type:"System/Cabinet", dims:{ cabinet_W_mm:800, cabinet_D_mm:"600 또는 800(변형)", cabinet_H_mm:"2000 + 플린스 100/200", vendor:"Emerson DeltaV CTO (예시)" }, notes:"특정 벤더 사례. 프로젝트 벤더 확정 전 '미확인'", sources:[
   S("Emerson DeltaV CTO DCS cabinets","https://www.emerson.com/en/automation-systems/distributed-control-systems-dcs/deltav-distributed-control-system/deltav-controllers-io/deltav-cto-dcs-cabinets","수치 인용")]},
 "GlobeValve_PRV":{item:"Globe Valve",type:"PRV/MOV",dims:{},notes:"전용 검색 미실시(ISA 75.08 링크는 GlobeValve_Control 참조)",sources:[]},
 "IPS":{item:"IPS",type:"SIS",dims:{},notes:"도면 검색 대상 아님(시스템 구성 블록)",sources:[]},
 "MMS":{item:"MMS",type:"Monitoring",dims:{},notes:"검색 미실시",sources:[]},
 "CCS":{item:"CCS",type:"Compressor Control",dims:{},notes:"검색 미실시",sources:[]},
 "FGS":{item:"FGS",type:"F&G",dims:{},notes:"검색 미실시",sources:[]},
};
for (const [k,v] of Object.entries(items)) writeFileSync(`data/dim/Dim_${k}.json`, JSON.stringify({...v, retrieved:"2026-11-06", policy:"제조사 도면 복제 금지: 수치와 URL만 저장. 출처 없는 값은 미확인"}, null, 2));
console.log(Object.keys(items).length);
