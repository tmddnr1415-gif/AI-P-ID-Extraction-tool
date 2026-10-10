import json, html, datetime
from pathlib import Path
ROOT = Path(__file__).parent / "project"
B = {
 "home":"/_blob/51af70a1af129e3757ed1353b76354a9","result":"/_blob/2922d525de7db6747e97dc3a4d57716e",
 "evidence":"/_blob/ac9fe2c141848f936a56b63d61aaa46f","evcrop":"/_blob/8c8e4dea12bdd1544ef9d7102997a25b",
 "range":"/_blob/e8b00a974cea7fd8a61a00825a1ae9e1","celledit":"/_blob/0c8d856b6229ee1c0d88a186ddb5265b",
 "savestate":"/_blob/f17d0b7a89e2391262af5c48c121a1ae","scopepop":"/_blob/dc6a72b5cbb8aa100d9e9a743e0c3f9e",
 "qty":"/_blob/8f06a20463747136d52696d4ce863105","mult":"/_blob/4b78568b69f624331743934a60c83242",
 "markup":"/_blob/292767d14dfb6f8bb91e3b802d41bf3e","side":"/_blob/ad59f61597b5d4462a5846f3bf1bc745",
 "memo":"/_blob/5b543bc4903c221381f4b8bb21e31249","pindlg":"/_blob/26059e74272c31b14fe32c0625147b36",
 "pin":"/_blob/c92947b558fa9a6de85e92f7fe636235","review":"/_blob/35cc64f9c2f536fe2220c1b4f45c2a73",
 "full":"/_blob/5971170518a7903adcc8ade7669f72a8","keys":"/_blob/8be941c3eab13b2550be4d579d562c57",
 "voc":"/_blob/6787cfcc7221e443847c7abf08954d03","popd":"/_blob/397c3b51ecc56833964df968793ffddd",
 "popl":"/_blob/1b8666ad35de6661d33ef67928b98350","running":"/_blob/b1c6e5c72dec246d8305bd67f9128e5a",
 "progress":"/_blob/fdec3be66f217d035d42bb6e373acaef",
}
NAVY, NAVY2, CREAM, CARD, SUNK, BLUE, INK, SOFT, LINE, CHIP = "#1e2a3f","#16213a","#f7f2e6","#fffdf6","#efe8d8","#1a5fb4","#4a3f33","#6b5f4f","#e3dccb","#e8eef9"
FONT = "'Noto Sans KR', 'Malgun Gothic', sans-serif"
MENU = [("홈 (대시보드)",""),("전체","1991"),("Field","1628"),("BFV","0"),("MOV","11"),("Pneumatic","3"),("검토필요","1782")]

def sidebar(active):
    items = []
    for i,(name,n) in enumerate(MENU):
        bg = "background:#2f5bd8;border-radius:10px;" if name == active else ""
        items.append(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;{bg}color:#ffffff;font-size:24px"><span>{name}</span><span style="color:#b9c4d8;font-size:24px">{n}</span></div>')
    menu = "".join(items)
    return (f'<div style="position:absolute;left:0;top:0;width:240px;height:1080px;background:{NAVY};display:flex;flex-direction:column;gap:6px;padding:40px 16px">'
            f'<p style="color:#ffffff;font-size:26px;font-weight:700;line-height:1.2">SAMSUNG C&amp;T</p>'
            f'<p style="color:#b9c4d8;font-size:24px;letter-spacing:2px">P&amp;ID EXTRACTOR</p>'
            f'<p style="color:#8e9bb5;font-size:24px;padding:28px 16px 6px">MENU</p>{menu}'
            f'<div style="flex:1"></div>'
            f'<div style="background:#2a3750;border-radius:10px;padding:12px 16px;color:#ffffff;font-size:24px">QF&nbsp; QFE <span style="color:#ffd66b">변경 180</span></div>'
            f'<p style="color:#b9c4d8;font-size:24px;padding:10px 16px 0">사용자: 홍길동</p>'
            f'<p style="color:#7fd1a0;font-size:24px;padding:0 16px">● 서버 연결됨</p></div>')

def header(title, sub, chips=()):
    ch = "".join(f'<span style="background:{CHIP};color:{BLUE};border:1px solid #c9d7f0;border-radius:999px;padding:6px 18px;font-size:24px">{c}</span>' for c in chips)
    return (f'<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:24px;border-bottom:2px solid {LINE};padding:0 0 18px">'
            f'<div style="display:flex;flex-direction:column;gap:8px"><h2 style="color:{BLUE};font-size:52px;font-weight:700;line-height:1.1">{title}</h2>'
            f'<p style="color:{SOFT};font-size:26px">{sub}</p></div><div style="display:flex;gap:10px">{ch}</div></div>')

def footer(n, total):
    return (f'<div style="position:absolute;left:304px;right:96px;bottom:52px;display:flex;justify-content:space-between;font-size:24px;color:{SOFT}">'
            f'<span>P&amp;ID 계기·밸브 추출 프로그램 — 기능별 동작 화면</span><span>{n} / {total}</span></div>')

def shot(src, w, h, alt):
    return (f'<div style="width:{w}px;height:{h}px;background:{SUNK};border:1px solid {LINE};border-radius:14px;padding:10px;display:flex;align-items:center;justify-content:center">'
            f'<img src="{src}" alt="{alt}" style="width:{w-20}px;height:{h-20}px;object-fit:contain"></div>')

def bullets(title, items, w=520):
    li = "".join(f'<li style="font-size:26px;line-height:1.45;color:{INK}">{x}</li>' for x in items)
    return (f'<div style="width:{w}px;background:{CARD};border:1px solid {LINE};border-radius:14px;padding:28px 30px;display:flex;flex-direction:column;gap:14px">'
            f'<h3 style="font-size:30px;font-weight:700;color:{BLUE}">{title}</h3><ul style="display:flex;flex-direction:column;gap:12px;padding:0 0 0 30px">{li}</ul></div>')

def section(sid, body, active="전체", n=None, total=None, bg=CREAM, pad="88px 96px 130px 304px", trans="fade"):
    foot = footer(n, total) if n else ""
    return (f'<section id="{sid}" data-transition="{trans}" style="background:{bg};color:{INK};font-family:{FONT};padding:{pad};display:flex;flex-direction:column;gap:28px">'
            f'{sidebar(active)}{body}{foot}</section>')

slides = []  # (id, html)
TOTAL = 19
def add(sid, h): slides.append((sid, h))

# 1 cover
cover = (f'<section id="cover" data-transition="fade" style="background:{NAVY2};color:#ffffff;font-family:{FONT};padding:128px;display:flex;flex-direction:column;justify-content:space-between">'
 f'<div style="position:absolute;left:0;top:0;width:1920px;height:1080px;background:{NAVY2}"></div>'
 f'<div style="position:absolute;left:0;top:0;width:18px;height:1080px;background:#2f5bd8"></div>'
 f'<div style="display:flex;flex-direction:column;gap:18px"><p style="font-size:28px;letter-spacing:4px;color:#b9c4d8">SAMSUNG C&amp;T · P&amp;ID EXTRACTOR</p>'
 f'<h1 style="font-size:92px;font-weight:700;line-height:1.15">P&amp;ID 계기·밸브 추출 프로그램</h1>'
 f'<p style="font-size:40px;color:#dfe6f3;line-height:1.4">기능별 실제 동작 화면과 함께 보는 소개</p></div>'
 f'<div style="display:flex;gap:16px">'
 + "".join(f'<span style="background:#2a3750;border:1px solid #3d4b66;border-radius:999px;padding:12px 28px;font-size:26px;color:#ffffff">{c}</span>' for c in ["PDF · DXF 입력","범례에서 규칙을 읽는 엔진","도면 위 검토·편집","Excel 출력 · 개정 대조"])
 + f'</div><div style="display:flex;justify-content:space-between;font-size:26px;color:#b9c4d8"><span>화면은 QFE 프로젝트 Rev.B 분석 결과 (QFE_260326.pdf · 93장)</span><span>2026-10-10 · hotfix80 기준</span></div>'
 f'<aside>프로그램 소개 덱. 모든 화면은 실제 서버에서 Playwright 로 찍은 동작 화면입니다.</aside></section>')
add("cover", cover)

# 2 overview
def card(step, title, lines, color=BLUE):
    li = "".join(f'<li style="font-size:24px;line-height:1.45;color:{INK}">{x}</li>' for x in lines)
    return (f'<div style="flex:1;background:{CARD};border:1px solid {LINE};border-top:8px solid {color};border-radius:14px;padding:26px 28px;display:flex;flex-direction:column;gap:12px">'
            f'<p style="font-size:24px;color:{SOFT}">STEP {step}</p><h3 style="font-size:32px;font-weight:700;color:{color}">{title}</h3><ul style="display:flex;flex-direction:column;gap:8px;padding:0 0 0 26px">{li}</ul></div>')
ov = header("프로그램 한눈에", "P&amp;ID 도면을 넣으면 계기·밸브 목록을 발주처 양식으로 내보냅니다", ["4단계"])
ov += '<div style="display:flex;gap:24px">' + card(1,"입력",["PDF (A1·A3 · 회전 섞임) 또는 DXF 묶음(zip)","프로젝트 · 입찰/실행 종류 · 이전 Rev 선택","암호·손상·스캔 PDF 는 원인을 말하며 거절"]) + card(2,"엔진 분석",["Symbol &amp; Legend 에서 치수·ISA 문자표·승수 유도","계기 버블 · 밸브 몸체·액추에이터 · 별표(공급 주체)","태그 · 라인 번호 · Description · Typical · NOTES 승수"],"#0f8f80") + card(3,"검토 화면",["도면 오버레이 + 엑셀식 목록 + 근거 패널","마크업 · 수량 승수 · 메모·핀 · 듀얼 모니터","이전 Rev 와 나란히 대조 (추가·수정·삭제)"],"#b07614") + card(4,"출력",["발주처 양식 Excel (FIELD · MOV · BFV)","변경 내역 Excel · 피드백 zip · 진단 zip","VOC 함 → 개발 반영 (중복 반영 방지)"],"#c2453f") + '</div>'
ov += (f'<div style="display:flex;gap:16px;align-items:center;background:{CHIP};border:1px solid #c9d7f0;border-radius:14px;padding:18px 28px">'
       f'<span style="font-size:26px;font-weight:700;color:{BLUE}">원칙</span><span style="font-size:26px;color:{INK}">도면이 말하는 것은 도면에서 읽고 외워두지 않는다 · 도면이 말하지 않으면 사람에게 묻는다 · 검출에 LLM 을 쓰지 않는다 · 네 프로젝트(AL NOUF1 · TC2 · QFE · UAD-DXF) 회귀 기준선이 모든 변경을 지킨다</span></div>')
add("overview", section("overview", ov, "홈 (대시보드)", 2, TOTAL))

def feature(sid, title, sub, chips, img, imgw, imgh, btitle, items, active="전체", n=0, extra=""):
    body = header(title, sub, chips) + f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(img, imgw, imgh, title)}<div style="display:flex;flex-direction:column;gap:20px">{bullets(btitle, items)}{extra}</div></div>'
    add(sid, section(sid, body, active, n, TOTAL))

# 3 home
feature("home","첫 화면 — 대시보드","왼쪽 메뉴 · 프로젝트 카드 · 리비전 타임라인 · 업로드",["홈"],B["home"],960,540,"무엇이 보이나",[
 "프로젝트 카드에 <b>PDF 가 인쇄한 프로젝트 제목</b> · 최상위 Rev 와 날짜 · 양식에 나가는 계기 수량",
 "리비전 타임라인 — 분석 상태 · 개정 판정 배지 · 행·장·수정 칸 · 누르면 결과 열림",
 "업로드 카드에서 프로젝트와 <b>입찰 / 실행</b> 종류를 고르고 PDF·DXF 를 넣는다",
 "그래프 셋 — 프로젝트별 · 리비전별 산출 행 · 개정 변경 도넛 (서버가 이미 내던 값만)",
 "알림 알약 — 데이터 위생 · 실패 · 분석 중 · 개정 변경"], "홈 (대시보드)", 3)

# 4 progress
body = header("분석 진행","분석은 별도 프로세스에서 돌고, 화면은 어디서든 현황을 본다",["분석 중"])
body += f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(B["running"],640,360,"첫 화면의 분석 중 카드")}{shot(B["progress"],640,360,"진행 화면")}</div>'
body += (f'<div style="display:flex;gap:24px">' + bullets("진행 현황",["최근 분석 이력 맨 위에 <b>진행 막대 · % · 남은 시간 · 지금 단계</b> (도면 치수 재는 중 — 37/60쪽)","남은 시간은 이 서버에서 끝난 분석의 <b>장당 시간 중앙값 × 장수</b> — 근거를 함께 적고, 없으면 ‘예상할 수 없음’"], 720)
         + bullets("안전하게",["분석은 자식 프로세스 — 메모리 부족으로 죽어도 서버는 살고 그 분석만 실패로 적힌다","다른 메뉴로 갔다 와도 분석은 계속 · 취소는 즉시 · 실패하면 멈춘 단계와 사유를 말한다"], 720) + '</div>')
add("progress", section("progress", body, "홈 (대시보드)", 4, TOTAL))

# 5 result
feature("result","결과 화면 — 도면 오버레이와 목록","왼쪽 도면 위 판정 상자 · 오른쪽 엑셀식 목록 · 탭은 산출물 단위",["1,991행","93장"],B["result"],960,540,"화면 구성",[
 "상자 색 = <b>공급 주체</b> (SCT 파랑 · VENDOR 주황 · 판정 없음 보라) · 모서리 ● 는 검토 필요 · <b>x N</b> 은 Q'ty",
 "탭 전체 · Field · BFV · MOV · Pneumatic — 발주처 양식 단위와 같다",
 "머리줄 띠 — 범례 재사용 · 프로필 · 실행(1급+2급) 판정 · 저장됨 시각 · 수정 이력",
 "목록 열 — PAGE · P&amp;ID NO. · 귀속 · 개정 · TYPE · TAG NO. · LINE NO. · LINE SIZE · Q'ty · SCOPE …",
 "장 목록에 장마다 ＋추가 ≠수정 －삭제 수 · 범례 판은 끌 수 있다"], "전체", 5)

# 6 evidence
body = header("근거 패널 — 왜 그렇게 판정했나","행을 누르면 그 행의 판정 근거가 그대로 보인다",["근거"])
body += f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(B["evidence"],960,540,"근거 패널")}' + bullets("패널이 말하는 것",[
 "<b>공급 주체</b> — 별표·NOTES 정의줄·패키지 상자 중 무엇이 가렸나, 발주처 양식에 나가는가",
 "<b>수량 근거</b> — 1 symbol x 2 (NOTES: …) · 범례 승수표 · 사람 지정이면 누가·언제",
 "<b>Description · Line No.</b> — 어느 런을 탭했고 깃발을 어디서 읽었나",
 "<b>태그</b> — 지시선이 가리킨 밸브 · 태그 문법 교차 검증 · 개정 판정",
 "사람이 고친 칸은 ✎ 와 이름 — 도면 근거는 옆에 그대로 남는다"]) + '</div>'
body += f'<div style="display:flex;align-items:center;gap:20px">{shot(B["evcrop"],1000,120,"근거 패널 확대")}<p style="font-size:24px;color:{SOFT};width:480px">검토 사유는 다섯 축(스코프 · 수량 · Description · 검출 · 입력 자료)으로 묶여 검토 탭에 집계된다</p></div>'
add("evidence", section("evidence", body, "전체", 6, TOTAL))

# 7 list editing
body = header("목록 편집 — 엑셀처럼","칸을 골라 바로 치고, 범위를 잡고, 되돌린다",["Ctrl+Z","Shift+↑↓","Ctrl+F"])
body += (f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(B["range"],440,488,"범위 선택")}{shot(B["celledit"],440,488,"칸 편집")}'
         + bullets("동작",["한 번 누르면 칸이 골라지고 <b>두 번 누름 · F2 · 바로 타자</b>로 편집이 열린다","Enter 저장 후 아래 · Tab 오른쪽 · Esc 되돌림 · 화살표로 칸 이동","<b>Shift+↑↓</b> 한 열 범위 · Ctrl+C/V · 여러 줄 붙이기는 위에서 한 줄씩 · Ctrl+Enter 범위 채우기 · Delete = 도면 값","<b>Ctrl+Z / Ctrl+Y</b> — 서버에 쓰는 길 넷 전부 되돌린다 (기록은 지우지 않고 한 줄 더 쌓임)","저장 상태 칩 — 저장 중 · 저장됨 시각 · 실패하면 붉게"], 584) + '</div>')
body += f'<div style="display:flex;align-items:center;gap:20px">{shot(B["savestate"],760,90,"저장 상태")}<p style="font-size:24px;color:{SOFT}">고친 값은 사람 값(✎)으로 남고 엔진 값은 그대로 — 다음 리비전에 안정 ID 로 승계된다</p></div>'
add("listedit", section("listedit", body, "전체", 7, TOTAL))

# 8 drawing edit
body = header("도면에서 바로 고치기","상자를 누르면 공급 주체, 라벨을 누르면 수량",["SCOPE","x N"])
body += (f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(B["scopepop"],480,290,"공급 주체 판")}{shot(B["qty"],480,470,"수량 라벨")}'
         + bullets("동작",["상자 → <b>SCT 공급 · VENDOR(이 도면에서 읽은 공급자 이름) · 둘 다 아님(식별 지우기)</b>","지운 상자는 붉은 ✕ · 목록 취소선 · Excel 에서 빠짐 · 다시 누르면 되돌리기","<b>x N</b> 라벨 → 이 태그만 · 이 페이지 전체 · Shift 범위 — 저장은 한 곳, 목록·라벨이 같은 값","Shift 끌기로 띠 선택 → 묶음 판에서 공급 주체·승수 일괄 변경 (요청 하나)","작성자는 대시보드 로그인 이름으로 자동 기록"], 504) + '</div>')
add("drawedit", section("drawedit", body, "전체", 8, TOTAL))

# 9 fullscreen
feature("fullscreen","도면 전체화면에서도 편집","⛶ 전체화면 · 도면 위 편집 카드 · 목록에 저절로 반영",["⛶"],B["full"],960,540,"동작",[
 "⛶ 를 누르면 도면 창이 화면 전체 — 대시보드 iframe 안이면 화면 안 전체화면",
 "상자를 누르면 오른쪽 위에 <b>편집 카드</b> (목록 머리글과 같은 칸 · Enter 저장 · ◀ ▶ 다음 항목)",
 "저장 길은 목록 칸과 같은 하나 — 어디서 고쳤든 목록이 같은 값으로 선다",
 "목록을 끝까지 접어 안 보일 때도 같은 카드가 뜬다 · Esc 는 선택 풀기 → 전체화면 끝"], "전체", 9)

# 10 mult
body = header("수량 승수 판","여러 장을 골라 장마다 승수를 적으면 Q'ty 가 바로 바뀐다",["Q'ty"])
body += f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(B["mult"],1000,220,"페이지별 승수 판")}</div>'
body += ('<div style="display:flex;gap:24px">' + bullets("페이지별 승수 (지금 결과)",["행이 있는 장마다 한 줄 — 도면번호 · 행 수 · <b>지금 xN</b> · 승수 칸 · Q'ty 전→후","칸에 적으면 저절로 골라지고 Shift 로 사이 장까지 · ‘선택한 장에 같은 승수’","새 Q'ty = 기본 개수 × 승수 — 사람이 고친 Q'ty(✎)로 저장 · 다음 Rev 에 승계"], 720)
         + bullets("유닛코드 승수 (다음 분석부터)",["범례 승수표가 없는 문서는 유닛코드로 묶어 <b>세 번의 답</b>으로 수백 행을 덮는다","읽는 순서 — 범례 → 그 장 NOTES → 사람 → 설정 폴백 → 빈칸 · 사람은 도면을 이기지 않는다","지정한 값은 다음 분석부터 적용 — 판에 상주하는 줄이 그렇게 말한다"], 720) + '</div>')
add("mult", section("mult", body, "전체", 10, TOTAL))

# 11 markup
feature("마크업","마크업 — 누락 행 추가 · 오검출 표시","사각형을 그리면 도면을 먼저 읽어 값을 제안한다",["＋행","✕"],B["markup"],960,540,"동작",[
 "마크업 모드에서 사각형을 끌면 그 자리의 <b>별표 · NOTES · 같은 장 수량 · TYPE</b> 을 읽어 제안",
 "제안을 그대로 두면 출처 DRAWING, 바꾸거나 채우면 USER — 근거 패널이 그대로 말한다",
 "추가 행은 녹색 음영 · 안정 ID 는 같은 장부에서 · 다음 리비전에 엔진이 그 자리를 찾으면 잇는다",
 "기존 상자 ✕ — 오검출 · 값 틀림 · 미지정 심볼 분류 + 사유 · 행은 지우지 않고 표시만",
 "‘개발팀에 VOC 로 신고’ 가 기본 켜짐 — 사유를 적어야 저장된다"], "전체", 11)
slides[-1] = ("markup", slides[-1][1].replace('id="마크업"', 'id="markup"'))

# 12 side by side
feature("sidebyside","개정 대조 — 나란히 보기","왼쪽 최신 Rev.B · 오른쪽 직전 Rev.A · 태그로만 대조",["ADD","MOD","DEL?"],B["side"],960,540,"동작",[
 "실행 프로젝트는 <b>(TYPE, 태그)</b> 로 짝을 짓는다 — 위치 좌표로는 비교하지 않는다",
 "같은 도면에 새 태그와 사라진 태그가 함께 남으면 전부 <b>수정(MOD)</b> · 한쪽만이면 추가 / 삭제 후보",
 "도면번호가 바뀐 장은 공유 태그로 알아보고 옛 번호 장을 오른쪽에 띄운다",
 "오른쪽 도면 아래 <b>이 장 변경 목록</b> · ◀ ▶ 로 두 창이 그 자리로 · 확대·스크롤이 함께 움직인다",
 "‘대조 다시’ — 재분석 없이 새 규칙으로 다시 대조 · 변경 내역 Excel 로 내보내기"], "전체", 12)

# 13 memo & pin
body = header("장별 메모 · 핀 메모","도면번호를 열쇠로 같은 프로젝트의 모든 Rev 에서 보인다",["📌"])
body += (f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(B["pin"],900,506,"핀 메모 작성칸")}'
         + bullets("동작",["도면 아래 <b>장별 메모장</b> — 저장 한 번이 판 하나, 지우지 않고 쌓인다 · 다른 Rev 에서 쓴 판은 표식과 함께","<b>📌 핀 메모 달기</b> → 도면을 누르면 압정이 꽂히고 작성칸에 날짜·작성자(로그인)가 자동","메모장의 메모를 누르면 도면이 그 자리로 가서 압정이 두 번 깜박임 · 압정을 누르면 메모장이 그 메모로","완료 · 숨김은 표시뿐 — 고친 글은 이력으로 남는다","도면번호가 바뀐 장도 옛 번호의 메모를 함께 보인다"], 560) + '</div>')
body += f'<div style="display:flex;align-items:center;gap:20px">{shot(B["memo"],560,160,"장별 메모장")}<p style="font-size:24px;color:{SOFT};width:900px">장별 메모장 — 지금 메모 · 이력 판 · ‘다른 Rev 에서’ 표식. 저장은 projects/&lt;프로젝트&gt;/sheet_notes.json 한 곳</p></div>'
add("memo", section("memo", body, "전체", 13, TOTAL))

# 14 review
feature("review","검토 탭 — 사유별로 묶어 처리","검토 축 다섯 · 필터 · 검색 · 개정 필터",["검토필요"],B["review"],960,540,"동작",[
 "검토 축 — <b>스코프 판정 · 수량 · Description · 검출 · 입력 자료</b> (등록 안 된 사유는 OTHER 로 보이고 숨기지 않음)",
 "행마다 미처리 · 확인함 · 수정함 · 보류 — 한 일만 저장",
 "검색(Ctrl+F) · 귀속 · 검토 필요만 · 개정 필터(추가만 · 수정만 · 삭제만) · 열별 필터",
 "Description 일괄 적용 — 같은 도면 · 같은 TYPE · 같은 문장인 묶음에 한 번에",
 "이름표(접미) · 사용자 입력 사유는 근거 패널에 SUFFIX: 로 남는다"], "검토필요", 14)

# 15 output & VOC
body = header("출력과 신고","최종 저장 · Excel 출력 · 변경 내역 Excel · VOC",["Excel","VOC"])
body += (f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(B["voc"],960,540,"VOC 창")}'
         + bullets("출력",["<b>최종 저장</b> — 편집·삭제·마크업을 스냅샷으로 굳히고 첫 화면 저장 이력에","<b>Excel 출력</b> — 발주처 양식 FIELD · MOV · BFV 에 그대로 (REMARK 앞머리에 개정·사용자 추가·오검출 표시)","<b>변경 내역 Excel</b> — 요약 · 추가 · 수정 · 삭제 · 장","<b>VOC</b> — 못 읽은 것·틀린 것·바라는 기능을 분류 + 사유 + 이름만 적으면 서버가 분석·장·행·엔진 값·도면 조각을 담아 VOC 함에 쌓는다","반영된 VOC 는 ‘반영됨 — hotfixNN’ 으로 표시되고 다시 반영되지 않는다"]) + '</div>')
add("output", section("output", body, "전체", 15, TOTAL))

# 16 dual monitor
body = header("듀얼 모니터 — 도면 · 목록을 새 창으로","두 창이 같은 결과를 보며 서로 연동된다",["⧉"])
body += f'<div style="display:flex;gap:28px;align-items:flex-start">{shot(B["popd"],700,394,"도면 새 창")}{shot(B["popl"],700,394,"목록 새 창")}</div>'
body += ('<div style="display:flex;gap:24px">' + bullets("동작",["⧉ 도면 새 창 · ⧉ 목록 새 창 — 각 모니터에 하나씩 전체화면","목록에서 행을 누르면 도면 창이 그 장·그 상자로 · 도면에서 상자를 누르면 목록 창이 그 행·근거로"], 720)
         + bullets("연동",["저장은 쓰기 요청이 끝난 것을 보고 알린다 — 받은 창은 <b>그 행만</b> 다시 받는다","장 · 고른 행 · Shift 묶음 · 메모 · 결과 전환이 같이 움직인다 · ⇆ 한 창으로 합치기"], 720) + '</div>')
add("dual", section("dual", body, "전체", 16, TOTAL))

# 17 shortcuts
feature("shortcuts","단축키","이 화면이 실제로 받는 키만 적는다 — ⌨ 단추 또는 도면에서 ?",["⌨"],B["keys"],960,540,"자주 쓰는 키",[
 "<b>Ctrl+F</b> 검색 · <b>F2</b> 편집 · Enter / Tab 저장 후 이동 · Esc 되돌림",
 "<b>Shift+↑↓</b> 범위 · Ctrl+C / Ctrl+V · <b>Ctrl+Enter</b> 범위 채우기 · Delete 도면 값",
 "<b>Ctrl+Z / Ctrl+Y</b> 되돌리기 · 다시",
 "Shift+클릭 · Shift+끌기 묶음 선택 · Ctrl+휠 확대 · Alt+← → 변경 이동",
 "메모 Ctrl+Enter 저장 · ⛶ 전체화면 · ? 도움말"], "전체", 17)

# 18 speed & quality
def trow(cells, head=False):
    tag = "th" if head else "td"
    st = f'padding:12px 18px;font-size:26px;border-bottom:1px solid {LINE};text-align:left;' + ("color:#ffffff;background:" + BLUE if head else f"color:{INK}")
    return "<tr>" + "".join(f'<{tag} style="{st}">{c}</{tag}>' for c in cells) + "</tr>"
t1 = "<table style=\"width:760px;border-collapse:collapse;background:" + CARD + "\">" + trow(["화면 동작 (QFE 1,991행)","이전","지금"], True) + "".join(trow(r) for r in [["결과 열기","6.3초","1.9초"],["장 넘기기","840ms","249ms"],["검색 한 글자","1,065ms","148ms"],["목록 끝까지 굴리기","2.4초","1.1초"],["묶은 73행 공급 주체 바꾸기","847ms · 요청 73","215ms · 요청 1"],["묶은 20행 식별 지우기","10.9초","0.42초"]]) + "</table>"
t2 = "<table style=\"width:700px;border-collapse:collapse;background:" + CARD + "\">" + trow(["분석 시간 (같은 답)","이전","지금"], True) + "".join(trow(r) for r in [["AL NOUF1 · 58장","830초","366초"],["TC2 · 60장 (270° 회전)","632초","308초"],["QFE · 93장","984초","554초"],["UAD · DXF 32장","—","67초"]]) + "</table>"
body = header("속도와 검증","여러 번 시뮬레이션하며 고친 결과 — 답은 그대로, 시간만 줄었다",["hotfix69~80"])
body += f'<div style="display:flex;gap:28px;align-items:flex-start">{t1}{t2}</div>'
body += (f'<div style="display:flex;gap:16px">' + "".join(f'<div style="flex:1;background:{CARD};border:1px solid {LINE};border-radius:14px;padding:20px 24px;display:flex;flex-direction:column;gap:6px"><p style="font-size:40px;font-weight:700;color:{BLUE}">{a}</p><p style="font-size:24px;color:{SOFT}">{b}</p></div>' for a,b in [("1,060","빠른 시험 통과 (18 건너뜀)"),("5xx 0","API 퍼징 · 모든 경로 × 본문 14종"),("0 결함","화면 전수 클릭 · 전 흐름 QA 시뮬레이션"),("4 프로젝트","회귀 기준선 — 지문·행·Q'ty·축3 불변")]) + '</div>')
add("speed", section("speed", body, "홈 (대시보드)", 18, TOTAL))

# 19 closing
cl = (f'<section id="closing" data-transition="fade" style="background:{NAVY2};color:#ffffff;font-family:{FONT};padding:128px;display:flex;flex-direction:column;justify-content:space-between">'
 f'<div style="position:absolute;left:0;top:0;width:18px;height:1080px;background:#2f5bd8"></div>'
 f'<div style="display:flex;flex-direction:column;gap:24px"><p style="font-size:28px;letter-spacing:4px;color:#b9c4d8">운영</p><h1 style="font-size:72px;font-weight:700;line-height:1.2">부서 대시보드 안에서 그대로 쓴다</h1></div>'
 f'<div style="display:flex;gap:24px">'
 + "".join(f'<div style="flex:1;background:#2a3750;border:1px solid #3d4b66;border-radius:14px;padding:28px 30px;display:flex;flex-direction:column;gap:12px"><h3 style="font-size:30px;font-weight:700;color:#ffd66b">{t}</h3><p style="font-size:24px;line-height:1.5;color:#dfe6f3">{d}</p></div>' for t,d in [
   ("사내망 서버","run_lan_service.bat 하나로 포트 8000 · 사내망 주소만 받는 문지기 · 멈추면 10초 뒤 다시"),
   ("대시보드 임베드","입찰/실행 메뉴 → P&amp;ID 분석 iframe · 로그인 이름이 작성자로 자동 · ?embed=1&amp;mode=&amp;user="),
   ("업데이트","변경분 꾸러미(apply_to_PID_dev · ops) · 첫 화면 오른쪽 아래 업데이트 딱지 · 옛 탭이면 새로고침 띠"),
   ("VOC → 개발","부서원 신고가 voc/inbox 에 쌓이고 개발 PC 의 Claude Code 가 읽어 반영 · 장부로 중복 반영 방지")])
 + f'</div><p style="font-size:26px;color:#b9c4d8">문의 · VOC 는 화면 머리줄 [VOC] 단추로 — 분류 · 사유 · 이름만 적으면 나머지는 서버가 담습니다</p>'
 f'<aside>마무리. 운영 절차는 docs/dashboard_embed.md · docs/voc.md 에 있습니다.</aside></section>')
add("closing", cl)

assert len(slides) == TOTAL, len(slides)
for sid, h in slides:
    assert h.count("<section") == 1 and f'id="{sid}"' in h, sid
    (ROOT / "slides" / f"{sid}.html").write_text(h, encoding="utf-8")
order = [s for s,_ in slides]
deck = {"v":4,"createdOnFiles":{"v":1,"at":datetime.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"},"lists":"css",
 "title":"P&ID 추출 프로그램 기능 소개","order":order,
 "sections":{"s1":{"description":"프로그램이 무엇을 하는지 한눈에","start":"cover"},
             "s2":{"description":"첫 화면부터 결과 화면까지 기본 흐름","start":"home"},
             "s3":{"description":"검토 · 편집 · 마크업 · 개정 대조 기능","start":"listedit"},
             "s4":{"description":"출력 · 협업 · 속도와 검증 · 운영","start":"output"}},
 "faces":{"noto-sans-kr":{"family":"Noto Sans KR","href":"https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap"}},
 "designSystems":[]}
(ROOT / "deck.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8")
print(order)
