hotfix36 — QFE 실측 · 배관 라인 번호(Line No.)를 도면에서 읽어 목록에 낸다  (2026-10-03)

무엇이 달라지나
  · 목록에 Type · Tag No. · Line No. 열이 이 순서로 보인다.  Line No. 는 그 계기가 탭한
    배관의 깃발 라벨(사각형 안 12LBB50 + 아래 BR010 → "12LBB50 BR010")이고 사람이 고칠 수 있다.
    근거 패널에 "Line No. 근거"(건너편 DN·배관 등급 글줄 포함)와 규칙이 적힌다.
  · QFE 처럼 범례 글자를 세 번 겹쳐 인쇄한 문서에서도 ISA 표의 SUCCEEDING 칸이 읽혀
    PIT/PI · TIT/TI 접기(hotfix31)가 돈다 — QFE 실측 접힌 행 117.
  · 발주처 양식 Excel 에 Line No. 열을 내려면 그 양식 config 에 `line_no: <열 번호>` 한 줄.

QFE 실측 (93장 · 2019행)
  태그 붙은 행 1505 · Line No. 붙은 행 727 (FIELD 567/1656) · 안 붙는 것은 FIT/FE 처럼
  신호선으로만 이어진 계기, 깃발이 없는 라인, Typical 상세 안의 행.
  ⚠ ISA 표가 읽히자 LA · LCA · LICA · GTC · PICA 같은 제어·경보 기능 버블도 행이 됐다
  (입찰 전수 정책 · 50회차와 같은 가족).  현장 계기와 가르는 것은 다음 회차.

고친 것
  · app/engine/line_labels.py (신규)      깃발 라벨 읽기
  · app/pipeline.py                        행에 붙이기(탭한 런 · 인출선 교차 · 접힌 표시기 승계) · Row.line_no
  · app/engine/describe_axis.py            page_runs — 판정과 라벨이 같은 런을 받는다
  · app/engine/isa_table.py                겹쳐 찍은 글자 접기 · 돌려 찍은 표
  · app/db.py                              EDITABLE 에 line_no
  · app/static/app.js                      Line No. 열 · 근거 패널
  · spike/egg_extract.py                   분할 egg 풀기
  · spike/projects_3p.json · baselines     QFE 항목
  · tests/test_hotfix36_line_labels.py     13건

주의
  · DXF 입력에서는 Line No. 를 읽지 않는다 (글자 방향 정보가 없다).
  · 같은 런에 깃발이 둘이면 가장 가까운 것을 쓰고 근거 패널에 "라벨 N개" 로 적는다.
