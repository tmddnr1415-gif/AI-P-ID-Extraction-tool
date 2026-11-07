---
name: ic-item-review
description: 계측제어 Item 에이전트의 공통 업무 절차(취합→대조→초안→확인)와 질의 유형별 처리법(검토 체크리스트, MR 필드, 개념 설명). Item 별 Spec 검토, MR Spec 검토 유의사항, 개념 질문을 받을 때 사용한다.
---

# Item 공통 검토 절차

## 1. 취합
- 질의의 Item·유형 확인 → `Spec for each Item/{Item}/*.md` 읽기 → 프로젝트 Spec·Datasheet 가 있으면 함께 읽기.
- 다른 Item 문서는 읽지 않는다(Interface 절의 타 시스템 언급은 그대로 참고만).

## 2. 대조 (ic-spec-evidence)
- 수치·표준·조항별 출처 확인, 없으면 '미확인'.

## 3. 유형별 초안
| 유형 | 산출 |
|---|---|
| **Spec 검토 유의사항** | 해당 Item md 의 `Integration Checklist` 와 `기술 요구사항` 을 기반으로 유의사항 ≤5개 + 확인 필요 데이터 |
| **MR 필드 채움** | Datasheet/Spec 에서 찾은 값만 JSON 으로: `{"field":..., "value":..., "source":..., "status":"확인|미확인"}` |
| **개념 설명** | 정의 1줄 + 핵심 3줄 + 관련 부품 `part:*` |
| **Interface 질의** | 해당 md 의 Interface 표에서 상대 시스템·방식·원칙만 |

## 4. 확인
- 답변 끝에 "원본 수치 대조 후 승인 필요" 표기, 안전 계통은 ic-safety-gate.
- 형식은 ic-concise-answer.

## Item 별 검토축
각 에이전트 파일(`.claude/agents/ic-*.md`)의 `검토축` 항목을 우선 사용한다.
