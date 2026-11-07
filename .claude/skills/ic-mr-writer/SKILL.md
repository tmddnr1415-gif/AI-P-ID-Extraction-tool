---
name: ic-mr-writer
description: Item 에이전트가 채운 MR 필드(JSON)를 회사 MR 양식(.docx)에 넣어 Material Requisition 초안을 만든다. 'MR 작성', 'Material Requisition', '자재 구매 요청서' 요청 시 사용한다. .docx 생성은 docx 스킬을 따른다.
---

# MR 작성 규칙

## 절차
1. Item 에이전트에서 MR 필드 JSON(`field, value, source, status`)을 받는다.
2. **이 프로그램의 Item별 MR 포맷**을 쓴다: `data/mr/MR_Format_{ItemKey}.json`(12종, 웹 검토로 구축, 출처 URL 포함). 회사 양식(`MR_Template_{ITEM}.docx`)이 있으면 그것이 우선. 공통 골격: 적용 범위 / 코드·표준 / 기술 요구사항(Datasheet) / Item 특화 / 검사·시험 / VDR / 인증서 / 문서 우선순위 / 포장·납품.
3. 표준 조항은 승인된 조항 라이브러리(`Standards_{ITEM}.xlsx` 등)에 있는 것만 넣는다. 없으면 넣지 않고 '미확인'.
4. 빈칸·근거 없는 값은 `미확인` 으로 노란 강조.
5. 생성: Item 에이전트 JSON 을 `values.json`(`{필드명:{value,source,status}}`)으로 저장 후 `python data/mr/make_mr.py {ItemKey} values.json`. 결과 `output/MR_{ItemKey}_{YYYYMMDD}_DRAFT.docx`(+`_latest_`). 서식 고급 편집은 `anthropic-skills:docx` 스킬. 사용자가 요청하면 즉시 생성한다(승인란은 비움).
6. 안전 계통이면 ic-safety-gate 적용.
7. 사람 승인 전에는 확정·발송하지 않는다.

## 금지
- 필드 값 추정, 표준 조항 원문 확인 없는 인용, 자동 발행.
