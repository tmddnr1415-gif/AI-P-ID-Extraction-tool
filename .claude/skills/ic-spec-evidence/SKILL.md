---
name: ic-spec-evidence
description: Spec 수치와 조항을 근거 순위에 따라 대조하고 출처를 표기하며, 근거 없는 값은 '미확인'으로 처리한다. 모든 Item 에이전트가 수치·표준·조항을 인용하기 전에 사용한다.
---

# 근거 대조 규칙

## 근거 순위
1. 프로젝트 Spec  2. 고객·회사 표준  3. 국제·업계 표준  4. 일반 지식

## 절차
1. 자기 Item 폴더 `Spec for each Item/{Item}/` 와 프로젝트 Spec·Datasheet 를 Read/Grep 으로 확인한다.
2. 인용할 값마다 출처를 찾는다: `파일명 · Rev · 절/표`.
3. 상위 자료와 하위 자료가 충돌하면 둘 다 적고 `충돌` 표시한다.
4. 출처를 못 찾으면 값을 쓰지 않고 `미확인`으로 적는다. 기억에 의존한 숫자·조항 번호 금지.
5. `Spec for each Item/` 의 md 는 일반 기준 초안이므로 `참고(일반 기준)` 로 표기하고 프로젝트 Spec 대조 필요를 명시한다.

## 출력 예
`Fail 방향: Fail-Close — Ball_Valve_Integration_Spec.md §1.1 (참고, 프로젝트 Spec 대조 필요)`
`누설 등급: 미확인`
