# VOC — 미반영 4건

회사 Claude Code 용 요약.  한 건씩 원인을 재고(§9 · 렌더로 확인), 고친 뒤 `python spike/voc.py resolve <id> --by <이름> --release <업데이트> --note <무엇을>` 으로 표시한다.  같은 원인의 VOC 는 함께 resolve 하거나 `dup --of` 로 묶는다.

## VOC-20261009-130640-68c76d — 기능 요청

* 작성: 홍길동 · 2026-10-09T13:06:40 · 일반 VOC
* 자리: (분석 없음 — 일반 VOC)
* 사유: 첫 화면에서 프로젝트를 이름으로 찾고 싶습니다

## VOC-20261009-130647-22520d — 느림 · 무거움

* 작성: 홍길동 · 2026-10-09T13:06:47 · 일반 VOC
* 자리: QFE · Rev.Rev.B · QFE_260326.pdf · p6 · 1A1Y-00EKG00-M05-0001
* 사유: 이 장에서 확대하면 버벅입니다
* PDF: `/tmp/qfe_rev_data2/uploads/48b5adbdd28c_QFE_260326.pdf`

## VOC-20261009-130703-42446e — Scope 판정 틀림

* 작성: 홍길동 · 2026-10-09T13:07:03 · 오류 신고 (행 · 도면 위치)
* 자리: QFE · Rev.Rev.B · QFE_260326.pdf · p6 · 1A1Y-00EKG00-M05-0001 · 사각형 [480.4, 308.2, 506.0, 381.9]
* 사유: Q'ty 는 x2 여야 합니다
* 행: TIT 00EKG01CT001 [FIELD] key=07e655c75580c463
  * 엔진 값: type=TIT scope=SCT qty=1 · 사람 값: 없음 · 규칙: -
* PDF: `/tmp/qfe_rev_data2/uploads/48b5adbdd28c_QFE_260326.pdf`
* 조각: `/tmp/qfe71/voc/inbox/VOC-20261009-130703-42446e/crop.png`

## VOC-20261009-130706-b12c69 — 분석이 멈춤 / 실패

* 작성: 홍길동 · 2026-10-09T13:07:06 · 분석 실패 화면
* 자리: QFE · Rev.Rev.B · QFE_260326.pdf
* 사유: 새 양식 PDF 가 타이틀블록 단계에서 멈춥니다
* PDF: `/tmp/qfe_rev_data2/uploads/48b5adbdd28c_QFE_260326.pdf`
