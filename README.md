# AI P&ID Extraction Tool

P&ID 도면에서 계기(instrument) 목록을 자동으로 뽑아내는 도구 모음입니다.
결과물은 실제 플랜트 설계에 쓰이는 **안전 관련 문서**이므로, 모든 출력은 사람의 검토를 거쳐야 합니다.

## 무엇을 열어야 하나

| 하고 싶은 일 | 열 파일 | 설치 |
|---|---|---|
| **PDF 넣고 지정 Excel 포맷으로 받기** | `pid-instrument-tool/web/standalone.html` | 없음 |
| 판독 결과를 검토하고 규칙에 되먹이기 | `pid-instrument-tool/review-ui/standalone.html` | 없음 |
| 배치 실행 · 규칙을 git으로 관리 | `pid-instrument-tool/` (파이썬) | `pip install -r requirements.txt` |
| 아무 P&ID나 빠르게 훑어보기 | `index.html` (루트) | 로컬 서버 필요 |

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
