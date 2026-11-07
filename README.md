# AI P&ID Extraction Tool → I&C 통합 사양 검토 멀티에이전트

이 저장소의 기준은 해커톤 프로젝트 **「계측제어(I&C) 통합 사양 검토 멀티에이전트」**입니다
(규칙: [`CLAUDE.md`](CLAUDE.md), 이관: [`MIGRATE.md`](MIGRATE.md)). 그 위에 지금까지 만든 도구를 반영했습니다.

| 하고 싶은 일 | 여는 곳 |
|---|---|
| **계측제어 질의 → Item 에이전트 답변 · MR 초안 · Anatomy 3D** (주 대시보드) | `python app/server.py` → http://127.0.0.1:8790 (또는 `app/index.html` 더블클릭) |
| 부품 단위 실물 3D (GA·치수도 → 분해·주석 3D, STL/OBJ) | 대시보드 Anatomy 탭 **실물 3D**, 단독: `ic-3d-builder/index.html` |
| 계장 전문가 챗봇 (프로젝트별 발주처 컨텍스트, 스펙 리뷰 표) | `ic-expert/index.html` |
| P&ID PDF → Instrument List Excel | `pid-instrument-tool/web/standalone.html` |

해커톤 기준에 더한 것:
- **Anatomy 실물 3D 모드**: 개념·시뮬레이션(Canvas) 옆에 파라메트릭 실물 3D. 사이즈·등급 연동 치수와 출처 배지,
  휠로 분해, 부품 설명·재질 카드, 컷어웨이. 답변의 `part:*` 태그를 누르면 실물 3D 에서 그 부품이 강조됩니다
  (`data/parts/Map_3d.json`). Ball(ESDV)·Globe·Butterfly·PSV·Transmitter·DCS/IPS 캐비닛.
- **답변 엔진 선택**: 헤더 [답변 엔진] → 로컬 검색형(기본) 또는 Claude(LLM). LLM 도 CLAUDE.md §5 규칙
  (근거 순위·'미확인'·간결 형식·안전 게이트·part 태그)을 그대로 따르고 Item 문서 + 전문가 지식베이스만 근거로 씁니다.
- **전문가 지식베이스** `ic-expert/knowledge` (국제 코드, Saudi Aramco, QatarEnergy, 주요 벤더, 아이템별 선정; 출처 약 1,790개).
- 스킬: `.claude/skills/` 의 해커톤 6종 + `ic-ga-to-3d`(도면→3D) + `ic-expert`(전문가 질의응답).

```
node app/build.mjs                                  # 대시보드 빌드 (실물 3D·LLM 지식 포함)
NODE_PATH=$(npm root -g) node app/test_e2e.mjs      # 통합 테스트 14개
```

---

## (이전) P&ID 계기 추출 도구

## 무엇을 열어야 하나

| 하고 싶은 일 | 열 파일 | 설치 |
|---|---|---|
| **PDF 넣고 지정 Excel 포맷으로 받기** | `pid-instrument-tool/web/standalone.html` | 없음 |
| 판독 결과를 검토하고 규칙에 되먹이기 | `pid-instrument-tool/review-ui/standalone.html` | 없음 |
| 배치 실행 · 규칙을 git으로 관리 | `pid-instrument-tool/` (파이썬) | `pip install -r requirements.txt` |
| 아무 P&ID나 빠르게 훑어보기 | `index.html` (루트) | 로컬 서버 필요 |
| **계측제어 품목 GA 도면 → 3D** (캐비닛·훅업·CV·MOV·밸브·PSV) | `ic-3d-builder/index.html` · 스킬 `.claude/skills/ic-ga-to-3d` | 없음 (오프라인, 내장 3D 엔진) |
| **계장 전문가 챗봇** — 스펙·데이터시트 리뷰, 코드·발주처·벤더 질의 | `ic-expert/index.html` · 스킬 `.claude/skills/ic-expert` | 없음 (API 키) |

`standalone.html` 두 개는 **더블클릭하면 바로 열립니다.** 서버도 파이썬도 필요 없습니다.

## 주 워크플로우

```
P&ID PDF ──▶ web/standalone.html ──▶ instrument_list.xlsx  (템플릿 서식 그대로)
                    │                └─▶ result.json
                    │                        │
                    │                        ▼
                    │            review-ui/standalone.html
                    │              셀 수정 + 사유 + 향후 규칙 코멘트
                    │                        │
                    └────── 규칙 개정 ◀───────┘
```

한 번에 완벽한 자동화가 목표가 아닙니다. 사람이 검토하며 지적한 오류를 **판독 규칙으로 바꿔
누적**하고, 다시 돌려 정확도를 올리는 반복 검증이 이 도구의 핵심입니다.

## 시작하기

1. `pid-instrument-tool/web/standalone.html` 을 브라우저로 엽니다.
2. ⚙ 설정에 Anthropic API 키를 넣습니다. (키는 브라우저에만 저장됩니다)
3. P&ID PDF와 Excel 템플릿을 넣습니다.
4. 판독할 도면을 고르고 실행합니다. **먼저 3~5장으로 정확도를 확인한 뒤** 범위를 넓히세요.
5. Excel을 받아 검토하고, 틀린 곳은 검토 UI에서 사유·규칙과 함께 고칩니다.

자세한 내용은 [`pid-instrument-tool/README.md`](pid-instrument-tool/README.md) 를 보세요.

## 정확도에 대해

이 도구는 아직 **실제 정확도가 측정되지 않았습니다.** 대표 도면 세트로 정답과 대조해
규칙을 몇 바퀴 다듬은 뒤에 도면 범위를 넓히는 것을 전제로 만들었습니다
(`pid-instrument-tool/samples/test_set_v1/README.md`).
