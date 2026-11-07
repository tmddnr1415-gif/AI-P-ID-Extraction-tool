# 에이전트 명부 (Agent Roster)

기준: 계측제어 설계 멀티에이전트 챗봇 기획서 (2026-11-06). `*` = 안전 계통 → 답변에 "초안, 담당자 확인 필수" 표기.

## 1. 상위 구조
| 계층 | 이름 | 역할 | 비고 |
|---|---|---|---|
| 사용자 | I&C 설계 엔지니어 | 질의·검토·MR 승인 요청 | 결재자 아님 |
| 오케스트레이터 | Orchestrator | 질의 분류 → 에이전트 호출 → 병합 → 응답, 로그 저장 | 에이전트 간 직접 호출 금지, 복합 질의는 병렬 호출 |
| 사람 승인 | Human Gate | 원본 수치 대조·승인 | 일반: 담당 엔지니어 + 팀 리드 / 안전: + SIS 담당 |

## 2. Item 에이전트 (12)
| # | 에이전트 | 그룹 | 범위 | 검토축(초안) | 참조 표준(후보) | Spec 폴더 | 안전 |
|---|---|---|---|---|---|---|---|
| 1 | DCS | 제어·안전 | 제어 시스템 전체 | I/O 수량·여유율, 이중화, 통신 인터페이스, 알람 관리 | 프로젝트 Spec | `DCS` | |
| 2 | IPS | 제어·안전 | 보호 계통(SIS) | SIL 요구, 투표 구조, DCS 독립성, Proof Test | IEC 61511, 61508 | `IPS` | * |
| 3 | MMS | 제어·안전 | 기계 감시 | 진동·변위·온도 프로브, 보호 로직, 알람·트립 | API 670 | `MMS` | * |
| 4 | CCS | 제어·안전 | 압축기 제어 | 서지·성능 제어, 응답 시간, 밸브 연동 | 프로젝트 Spec | `CCS` | |
| 5 | FGS | 제어·안전 | 화재·가스 감지 | 감지기 타입·배치, 투표 로직, Cause & Effect | IEC 61511 등 | `FGS` | * |
| 6 | Ball Valve | 밸브 | ESDV, SDV, BDV, XV, Control Valve | Fail 방향, 누설 등급, 동작 시간, PST, Fire Safe, Actuator 사이징 | API 6D, 607, ISO 5208 | `Ball Valve` | * (ESDV·BDV) |
| 7 | Globe Valve | 밸브 | Control Valve, PRV, MOV | Cv 사이징, 캐비테이션·소음, Trim, 누설 등급, Positioner | IEC 60534, ISA 75 | `Globe Valve` | |
| 8 | Butterfly Valve | 밸브 | Control Valve, MOV | Offset 형식, Shutoff 등급, 토크, Actuator | API 609 | `Butterfly Valve` | |
| 9 | PSV | 밸브 | 안전밸브 | Set Pressure, Orifice, Back Pressure 형식, 배관 영향 | API 520, 526, 527 | `PSV` | * |
| 10 | Field Gauge | 계기·자재 | 압력·온도·레벨·유량 등 | 정확도, 다이얼 크기, 접액 재질, Process Connection | 프로젝트 Spec | `Field Gauge` | |
| 11 | Transmitter | 계기·자재 | 압력·온도·레벨·유량 등 | Range, 정확도, 통신 방식, 방폭 등급, SIL 인증 | IEC 60079 | `Transmitter` | |
| 12 | Bulk Material | 계기·자재 | Instrument·Cable Hook-up | Tubing·Fitting 재질, Manifold, Gland, Junction Box | 프로젝트 Spec | `Bulk Material` | |

> Spec 폴더 = `Spec for each Item/` 하위 폴더. 각 에이전트는 자기 폴더만 지식 베이스로 사용하고 다른 Item 문서는 섞지 않는다.

## 3. 지원 에이전트 (3)
| 에이전트 | 스킬 | 역할 | 상태 |
|---|---|---|---|
| Anatomy 뷰어 | `ic-anatomy-link` | 답변 태그(part:*) → 부품 점멸, Dimensional 도면 | Anatomy skill 사양 **미확인** |
| MR 작성 | `ic-mr-writer` | Datasheet 매핑 → MR .docx 생성 | 회사 MR 양식 **미확인**, 승인 후에만 확정 |
| 공시 재무제표 | `fin-dashboard-qa` | 재무·공시 질의응답 (계측제어와 분리) | 대시보드 링크/소스 **미확인**, API Key는 환경변수로만 접근 |

## 4. 공통 스킬·가드
- `ic-concise-answer`: 결론 1줄 → 항목 최대 5개 → 출처·미확인 → 후속 제안 1개
- `ic-item-{name}` × 12: Item별 Spec 지식·검토축
- 근거 순위: 프로젝트 Spec > 고객·회사 표준 > 국제·업계 표준 > 일반 지식
- 출처 없는 수치 = '미확인', 질의·답변 로그 저장

## 5. 라우팅 약어 사전 (예시)
| 약어 | 라우팅 |
|---|---|
| ESDV, SDV, BDV, XV | Ball Valve |
| PRV, MOV(Globe) | Globe Valve |
| MOV(Butterfly) | Butterfly Valve |
| PSV, PRV(안전밸브 문맥) | PSV (모호하면 사용자에게 한 줄 되묻기) |
| 재무·공시·실적 | 공시 재무제표 |

## 6. 가정
- IPS = Instrumented Protective System(SIS), MMS = Machinery Monitoring System, PRV = 압력 조절 밸브
- 직책명(담당 엔지니어, 팀 리드, SIS 담당)은 조직에 맞게 변경 필요
