hotfix37 — Line No. 는 사각형 안 코드(12LBB50) · Line Size 열 신설(DN 800)  (2026-10-03)

사용자 정의: "Line number 의 형식은 12LBB50 이며 Line Size 는 DN 800 이다."

무엇이 달라지나
  · Line No. 열은 깃발 사각형 안의 코드 하나(12LBB50)만 적는다.  아래 줄(BR010)은 근거 패널의
    "배관 번호" 로 남는다 (hotfix36 은 둘을 붙여 "12LBB50 BR010" 으로 냈다).
  · Line Size 열이 Line No. 오른쪽에 새로 선다 — 깃발 건너편 글줄 "DN800H LBB1" 에서 직경만
    "DN 800" 꼴로.  보온 글자(H/P/N)와 설계 코드(LBB1)는 근거 패널 "Line Size 근거" 에 적힌다.
    사람이 고칠 수 있고(EDITABLE) 지문 밖이다.
  · 세 조각의 형식은 그 도면 범례 p5 "PIPING DESIGNATION FLAG" 에서 배운다 — 보온 글자는
    "- H : INSULATION …" 글줄에서, 직경 접두(DN)는 범례 예시가 획으로 그려져 글자가 없으므로
    본문 깃발이 두 장 이상에서 되풀이한 접두에서.  코드에 DN·H·P·N 을 적지 않았다 (AST 시험).
    범례가 없는 문서는 글자+숫자 구조만으로 가르고 근거 패널이 "범례 정의 없음" 이라고 적는다.
  · 발주처 양식 Excel 에 내려면 그 양식 config 에 `line_size: <열 번호>` 한 줄 (line_no 와 같다).

QFE 실측 (93장)
  __QFE_LINE__

고친 것
  · app/engine/line_labels.py             parse_spec · learn_flag_format(범례) · learn_prefix_from_labels(본문) · LineLabel.line_no/pipe_no
  · app/pipeline.py                        Row.line_size · 범례 형식 학습 · 행에 size 붙이기 · 접힌 표시기 승계 · 근거 format
  · app/db.py                              EDITABLE 에 line_size
  · app/static/app.js                      Line Size 열 · 근거 패널 "Line Size 근거"(형식 출처)
  · spike/ui_audit_lineno.py · spike/line_label_probe3.py   자기검증 도구에 Line Size
  · tests/test_hotfix37_line_size.py       6건 (빠른 시험 649)

주의
  · hotfix36 으로 분석해 둔 결과는 Line No. 가 "12LBB50 BR010" 꼴로 남아 있다 — 다시 분석해야 바뀐다.
  · DXF 입력에서는 여전히 Line No./Line Size 를 읽지 않는다.
