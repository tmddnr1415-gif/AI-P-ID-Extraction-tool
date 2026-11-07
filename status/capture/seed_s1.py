import json, os, sys, time
root = sys.argv[1]
now = time.strftime('%Y-%m-%dT%H:%M:%S')
def row(sheet, i, fields):
    d = os.path.join(root, 'data', sheet); os.makedirs(d, exist_ok=True)
    rid = f'{sheet}-demo{i:02d}'
    json.dump({'id': rid, 'sheet': sheet, 'order': i * 10, 'fields': fields,
               'meta': {'createdBy': '시연', 'createdAt': now, 'updatedBy': '시연', 'updatedAt': now, 'rev': 1}},
              open(os.path.join(d, rid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
P = [('발전', 'PJT-A 복합화력', '김계장, 이계장'), ('발전', 'PJT-B 열병합', '박계장'), ('화공', 'PJT-C CO2 포집', '홍길동, 최계장'), ('인프라', 'PJT-D 수처리', '이계장')]
for i, (g, n, o) in enumerate(P, 1):
    row('perform', i, {'사업군': g, 'PJT명': n, 'Project Code': f'P{i:03d}', '종결 여부': '진행', 'PJT 개요': '시연용 예시 프로젝트',
                       'PJT 주요 일정': '2026-12 IFC', '담당자': o, '업무 현황': '- P&ID Rev.2 계기 목록 검토\n- Logic 검토 의견 회신', '현안': '없음'})
B = [('발전', 'BID-E 가스터빈', '김계장'), ('화공', 'BID-F LNG', '홍길동'), ('인프라', 'BID-G 담수', '이계장')]
for i, (g, n, o) in enumerate(B, 1):
    row('bid', i, {'사업군': g, 'PJT명': n, 'Project Code': f'B{i:03d}', '종결 여부': '진행', 'PJT 개요': '시연용 예시 입찰', '담당자': o,
                   '업무 현황': 'MR 초안 · Datasheet 사양 대조', '현안': '-'})
print('seeded')
