import json, os, sys, datetime
D = sys.argv[1]
now = datetime.datetime.utcnow()
def iso(d): return (now - datetime.timedelta(days=d)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
rows = {
 'perform': [
  ('발전', '예시 복합화력 #1', 'DEMO-P01', '진행', 'GTCC 1,000MW · EPC', '11월 IFC 도면 발행\n12월 DCS FAT', '홍길동, 김계장', 'P&ID Rev.B 계기 리스트 추출 완료 (2,950개)\nLogic Diagram 50장 검토 중', 'Vendor 도면 지연 — 1주'),
  ('발전', '예시 열병합 #2', 'DEMO-P02', '진행', 'CHP 500MW', '11월 Logic 확정', '이계장', 'Logic From-To 점검 99.5%', ''),
  ('화공', '예시 가스처리 플랜트', 'DEMO-P03', '진행', 'Gas Processing', '12월 HAZOP', '박계장', 'Instrument Index 정리', 'IO 수량 증가 검토'),
  ('인프라', '예시 해수담수화', 'DEMO-P04', '진행', 'SWRO 300,000 m³/d', '1월 기계적 준공', '최계장', 'CCR 판넬 배치 · ROOM SIZE 건축 전달', ''),
 ],
 'bid': [
  ('발전', '예시 입찰 A', 'DEMO-B01', '진행', 'OCGT 600MW', '11/20 제출', '홍길동', '계장 물량 산출 (P&ID 자동 추출)', ''),
  ('화공', '예시 입찰 B', 'DEMO-B02', '진행', 'Ammonia', '12/05 제출', '김계장', 'Control Room 면적 산정', ''),
  ('인프라', '예시 입찰 C', 'DEMO-B03', '진행', 'Water Treatment', '12/15 제출', '이계장', 'IO 리스트 초안', ''),
 ],
}
cols = ['사업군','PJT명','Project Code','종결 여부','PJT 개요','PJT 주요 일정','담당자','업무 현황','현안']
n = 0
for sheet, rs in rows.items():
    os.makedirs(os.path.join(D, 'data', sheet), exist_ok=True)
    for i, r in enumerate(rs):
        rid = f'{sheet}-demo{i+1:02d}'
        rec = {'id': rid, 'sheet': sheet, 'order': (i+1)*10, 'fields': dict(zip(cols, r)),
               'meta': {'createdBy': '홍길동', 'createdAt': iso(10), 'updatedBy': '홍길동', 'updatedAt': iso(i % 3), 'rev': 2,
                        'changes': {'업무 현황': iso(i % 3)}}}
        json.dump(rec, open(os.path.join(D, 'data', sheet, rid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1); n += 1
os.makedirs(os.path.join(D, 'data', 'notice'), exist_ok=True)
for i, (t, c) in enumerate([('P&ID · LOGIC 자동화 도구 시연', '대시보드 메뉴에서 P&ID 분석 · LOGIC 분석 · ROOM SIZE 계산을 바로 열 수 있습니다.'),
                            ('주간업무 마감 안내', '매주 수요일 12:00 자동 마감')]):
    rid = f'notice-demo{i+1:02d}'
    rec = {'id': rid, 'sheet': 'notice', 'order': (i+1)*10, 'fields': {'일자': (now - datetime.timedelta(days=i)).strftime('%Y-%m-%d'), '제목': t, '내용': c},
           'meta': {'createdBy': '홍길동', 'createdAt': iso(i), 'updatedBy': '홍길동', 'updatedAt': iso(i), 'rev': 1}}
    json.dump(rec, open(os.path.join(D, 'data', 'notice', rid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1); n += 1
print('rows', n)
