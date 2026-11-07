---
name: ic-safety-gate
description: 안전 계통(IPS, FGS, MMS, ESDV, BDV, SDV, PSV 등) 답변에 '초안, 담당자 확인 필수'를 표기하고 확정 표현을 막으며 사람 승인 경로를 안내한다. 안전 계통이 포함된 모든 답변·MR 에서 사용한다.
---

# 안전 계통 게이트

## 대상
IPS(SIS), FGS, MMS, ESDV, SDV, BDV, PSV, SIL 인증·Proof test·Trip 관련 모든 내용.

## 규칙
1. 답변 맨 위에 `⚠ 초안, 담당자 확인 필수` 표기.
2. 확정 표현 금지: "~해야 한다/적합하다" → "~로 정리됨(원본 확인 필요)".
3. SIL, Set Pressure, 누설 등급, Stroke time, 투표 구조 등은 출처 없으면 `미확인`.
4. Safety 신호는 Hardwired 원칙을 인용할 때도 프로젝트 Spec 대조 필요라고 덧붙인다.
5. 승인 경로 안내: 담당 계측 엔지니어 + **안전(SIS) 담당자** 원본 대조 → 팀 리드 승인.
6. MR 은 승인 전 `DRAFT` 워터마크/문구를 유지하고 자동 발행·발송하지 않는다.
