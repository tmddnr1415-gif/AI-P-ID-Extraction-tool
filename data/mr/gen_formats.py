# 웹 검토(2026-11-06)로 파악한 MR 구조를 Item별 포맷 JSON 으로 생성한다.  python data/mr/gen_formats.py
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = {
 "gen": [("EPCLand - MR 구성(Fittings)", "https://epcland.com/courses/material-requisition-item-name-fittings/"),
         ("Udemy - MR Pipes", "https://www.udemy.com/course/material-requisition-mr-item-name-pipes/"),
         ("Scribd - Material Request 예시", "https://www.scribd.com/document/396063388/Material-Request"),
         ("LawInsider - MR/Technical Specifications 정의", "https://www.lawinsider.com/dictionary/material-requisition-or-technical-specifications")],
 "esdv": [("Scribd - ESDV 사양 예시", "https://www.scribd.com/document/493578599/ESDV"),
          ("IndustrialMonitorDirect - ESDV 재질 선정", "https://industrialmonitordirect.com/blogs/knowledgebase/esdv-valve-material-selection-for-tropical-marine-condensate-service"),
          ("Eng-Tips - ESDV closing speed", "https://www.eng-tips.com/threads/esdv-closing-speed.286856/post-44450")],
 "psv": [("IndustrialMonitorDirect - API 526 Orifice", "https://industrialmonitordirect.com/blogs/knowledgebase/api-526-psv-orifice-sizes-d%e5%88%b0t-designations-explained")],
 "xmtr": [("Oregon State RFQ - Transmitters", "https://bid.oregonstate.edu/opportunity/viewFile/44440/RFQ_92218032_Transmitters.pdf"),
          ("Scribd - Pressure Transmitter 사양 예시", "https://www.scribd.com/document/648390960/Pressure-Transmitter-ADWEA"),
          ("Emerson - Rosemount 2051 Data Sheet(벤더 예시)", "https://emerson.com/documents/automation/product-data-sheet-rosemount-2051-pressure-transmitter-en-73206.pdf")],
 "dcs": [("Control.com - DCS FAT", "https://control.com/forums/threads/dcs-factory-acceptance-test-fat.29518/"),
         ("Skill-Lync - DCS FAT/SAT 절차", "https://resources.skill-lync.com/branches/instrumentation/questions/dcs-fieldbus/dcs-fat-sat-procedures"),
         ("IndustrialMonitorDirect - DCS I/O 용량", "https://industrialmonitordirect.com/blogs/knowledgebase/estimating-dcs-marshalling-and-system-cabinet-io-capacity")],
 "bulk": [("EPCLand - MR Fittings(MTO 구조)", "https://epcland.com/courses/material-requisition-item-name-fittings/"),
          ("AutomationForum - Impulse piping 설치", "https://automationforum.co/impulse-piping-installation-precautions-how-to-connect-impulse-piping-to-transmitter-manifold-valves/")],
}
def S(k): return [{"title": t, "url": u} for t, u in SRC["gen"] + SRC.get(k, [])]

COMMON_TAIL = [
 {"id": "insp", "title": "5. 검사·시험 (Inspection & Test)", "fields": ["ITP 제출 요구", "Hydro/기능 시험", "Third-party 검사 여부", "시험 성적서·증빙"]},
 {"id": "vdr", "title": "6. Vendor Document Requirement", "fields": ["제출 문서 목록(Datasheet·도면·매뉴얼)", "제출 시점(PO 후 n주)", "문서 번호에 MR No. 표기", "Rev 관리"]},
 {"id": "cert", "title": "7. 인증서 요건", "fields": ["Material Cert (EN 10204 3.1 등, 미확인)", "방폭·SIL 인증서(해당 시)", "Calibration Cert(해당 시)"]},
 {"id": "prio", "title": "8. 문서 우선순위", "fields": ["프로젝트 Spec > 고객·회사 표준 > 국제·업계 표준 순서 명기"]},
 {"id": "pack", "title": "9. 포장·표시·납품", "fields": ["포장 사양", "Tag/Marking", "납기·인도 조건", "예비품·Commissioning spares"]},
]
def fmt(item, folder, types, safety, specific, sk, note=""):
    return {
     "item": item, "folder": folder, "types": types, "safety": safety,
     "basis": "웹 검토로 파악한 일반 EPC MR 구성 + Item 특화 섹션. 회사 MR 양식·승인 조항은 미확인이므로 프로젝트 양식으로 교체 필요.",
     "note": note,
     "header": ["Project", "MR No.", "Rev", "Item / Type", "Date", "작성(Prepared)", "검토(Checked)", "승인(Approved) — 사람이 서명"],
     "sections": [
       {"id": "scope", "title": "1. 적용 범위 (Scope of Supply)", "fields": ["공급 범위", "Tag 목록·수량(MTO)", "제외 범위", "인접 Item과의 경계(Interface)"]},
       {"id": "std", "title": "2. 적용 코드·표준", "fields": ["승인된 조항 라이브러리에 있는 표준만 기재 (없으면 '미확인')"]},
       {"id": "tech", "title": "3. 기술 요구사항 (Datasheet 항목)", "fields": []},
     ] + specific + COMMON_TAIL,
     "sources": S(sk),
    }

F = {}
F["DCS"] = fmt("DCS","DCS",["System"],False,[
  {"id":"dcs1","title":"4. DCS 특화","fields":["I/O 수량(AI/AO/DI/DO)·여유율","이중화(Controller/Network/PSU)","FSD(Functional Specification)","FAT 범위","SAT 범위","3rd-party 인터페이스(Modbus 등)","사이버보안(IEC 62443 적용 여부)"]}],"dcs")
F["IPS"] = fmt("IPS","IPS",["SIS/ESD"],True,[
  {"id":"ips1","title":"4. IPS 특화","fields":["SIL 요구(SRS 근거)","투표 구조(1oo2, 2oo3 등)","DCS와의 독립성","Bypass/Reset 방식","Proof Test 주기","FAT/SAT"]}],"dcs")
F["MMS"] = fmt("MMS","MMS",["Machinery Monitoring"],True,[
  {"id":"mms1","title":"4. MMS 특화","fields":["프로브 수량·배치","Alarm/Trip 설정값","Voting·Hardwired Trip","API 670 적용 범위","FAT/SAT"]}],"dcs")
F["CCS"] = fmt("CCS","CCS",["Compressor Control"],False,[
  {"id":"ccs1","title":"4. CCS 특화","fields":["Anti-surge 제어 방식","성능 제어","응답 시간","밸브 연동(Anti-surge valve)","FAT/SAT"]}],"dcs")
F["FGS"] = fmt("FGS","FGS",["Fire & Gas"],True,[
  {"id":"fgs1","title":"4. FGS 특화","fields":["감지기 타입·수량·배치","투표 로직","Cause & Effect Matrix","Line monitoring","FAT/SAT"]}],"dcs")
F["BallValve"] = fmt("Ball Valve","Ball Valve",["ESDV","SDV","BDV","XV"],True,[
  {"id":"bv1","title":"4. Ball Valve 특화","fields":["Fail 방향(FC/FO/FL)","누설 등급(ISO 5208 Rate, 미확인)","Fire Safe 시험(API 607/6FA, 미확인)","동작 시간(Closing/Opening)","Partial Stroke Test 기능","Actuator 사이징(공급압·Safety factor)","SOV/Limit switch/Position 사양","SIS용 Datasheet(SIL, PFDavg, 미확인)","Body 구조(Trunnion/Floating), 단·분할 Body"]}],"esdv",
  "ESDV 중심 양식. SDV/BDV/XV는 동일 양식에서 Type 열만 변경.")
F["GlobeValve"] = fmt("Globe Valve","Globe Valve",["Control Valve","PRV","MOV"],False,[
  {"id":"gv1","title":"4. Globe Valve 특화","fields":["Cv/Kv 사이징 데이터(Flow·ΔP·T)","Trim 형식·재질","캐비테이션·소음 한계","Shutoff 등급(ANSI/FCI 70-2, 미확인)","Positioner/Actuator 사양","PRV인 경우 설정압·Pilot 방식"]}],"gen")
F["ButterflyValve"] = fmt("Butterfly Valve","Butterfly Valve",["Control Valve","MOV"],False,[
  {"id":"bf1","title":"4. Butterfly Valve 특화","fields":["Offset 형식(Concentric/Double/Triple)","Shutoff 등급","Actuator 토크 마진","Seat 재질","Positioner(Control인 경우)"]}],"gen")
F["PSV"] = fmt("PSV","PSV",["Conventional","Bellows","Pilot-operated","PVRV"],True,[
  {"id":"psv1","title":"4. PSV 특화","fields":["Set Pressure·Cold Differential Set Pressure","Orifice 지정(API 526 문자, 미확인)","Back Pressure 형식·값","Seat Tightness 시험 기록(API 527, 미확인)","Set Pressure 시험 성적서","입출구 Flange Rating","재질(Body/Trim/Spring)"]}],"psv")
F["FieldGauge"] = fmt("Field Gauge","Field Gauge",["Pressure","Temperature","Level","Flow"],False,[
  {"id":"fg1","title":"4. Field Gauge 특화","fields":["다이얼 크기·정확도 등급","접액 재질","Process Connection","Thermowell 사양(해당 시)","Fill fluid/Case 보호등급"]}],"gen")
F["Transmitter"] = fmt("Transmitter","Transmitter",["Pressure","DP","Temperature","Level","Flow"],False,[
  {"id":"tx1","title":"4. Transmitter 특화","fields":["Range·Span·정확도","출력/통신(4-20mA HART 등)","방폭 등급(IEC 60079, 미확인)","SIL 인증서(해당 시)","Manifold/Mounting bracket","Calibration 성적서","Type test 보고서","BOM(구성품 목록)"]}],"xmtr")
F["BulkMaterial"] = fmt("Bulk Material","Bulk Material",["Tubing & Fitting","Cable & Gland","Junction Box","Manifold","Support"],False,[
  {"id":"bm1","title":"4. Bulk 특화 (MTO 표)","fields":["MTO 표: 번호 | 품명 | 규격 | 재질 | 단위 | 수량 | 여유율 | 비고","Tubing 재질·치수","Gland·방폭 인증(IEC 60079-14, 미확인)","Junction Box 보호등급·재질"]}],"bulk",
  "수량 열은 Hook-up Drawing 기준 MTO 에서 사람이 채운다. 에이전트는 수량을 추정하지 않는다.")

for k, v in F.items():
    json.dump(v, open(os.path.join(HERE, f"MR_Format_{k}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("formats", len(F))
