# hotfix36/37 UI 자기검증 — Line No. · Line Size 열

- 머리글: ['Page ▲▾', 'P&ID No.▾', '귀속', 'Type▾', 'Tag No.', 'Line No.', 'Line Size', 'Valve Type▾', "Q'ty▾", 'System▾', 'Vendor▾', 'Scope', 'Description', '등급', 'Remark', '']
- ① 머리글 순서 Type@3 · Tag No.@4 · Line No.@5 · Line Size@6 — 맞음
- ② p46 목록 1999행 · Tag No. 있는 행 1505 · Line No. 있는 행 726 · Line Size 있는 행 718 · 예 [{'tag': '00EKG01CT001', 'line': '00EKG01', 'size': 'DN 600', 'type': 'TIT'}, {'tag': '00EKG00CL001', 'line': '00EKG10', 'size': 'DN 50', 'type': 'LIA'}, {'tag': '00EKG02CP001', 'line': '00EKG02', 'size': 'DN 600', 'type': 'PIT'}]
- ②-b Line No. 에 공백이 든 행 0 · Line Size 꼴 ['DN']
- ③ 근거 패널 'Line No. 근거' 있음 · 'Line Size 근거' 있음 — ['Line No. 근거', 'Line Size 근거', 'Line No. 규칙']
- ③-b 근거 값: 00EKG01 — 도면 깃발 라벨 (사각형 안) · 배관 번호 BR001 · 건너편 750x600 DN600P EKG1 | DN 600 · 보온 P · 설계 코드 EKG1 — 범례 p5 의 깃발 정의 (보온 글자) · 직경 접두는 본문 깃발 다수
- ④ 페이지 오류 0
