# Phase 0 검증 스파이크

`docs/design.md` §15 Phase 0 / 부록 A 의 검증 스크립트.

| # | 스크립트 | 목표 | 상태 |
|---|---|---|---|
| 1 | `extract_titleblocks.py` | 58페이지 타이틀블록 파싱 성공률 100% | ✅ **통과 (58/58)** |
| 2 | `detect_symbols.py` | 단일 페이지 심볼 검출 재현율 ≥ 90% | 미구현 |
| 3 | `parse_notes.py` | Note 승수 파싱 전수 검증 | 미구현 |

## 1. 타이틀블록 파싱

```bash
pip install pymupdf numpy
python spike/extract_titleblocks.py --pdf data/pid_total.pdf \
                                    --out out/titleblocks.csv \
                                    --rev-sheet out/rev_cells.png
```

`--rev-sheet` 는 58개 REV 셀을 판독 결과와 함께 한 장으로 붙인 PNG를 만듭니다.
REV 는 대부분의 페이지에서 텍스트 레이어와 대조할 수 없는 유일한 필드라
육안 검증용으로 붙였습니다.

### 결과

| 필드 | 성공 | 비율 |
|---|---|---|
| `drawing_no` | 58/58 | 100% |
| `drawing_title` | 58/58 | 100% |
| `unit_code` | 58/58 | 100% |
| `rev` | 58/58 | 100% (전부 HIGH) |
| `rev_date` | 9/58 | 15.5% (아래 §설계 영향 참조) |

파싱 실패 페이지 **없음**.

### 설계 영향 — 설계안 수정이 필요한 실측 발견

**① 타이틀블록이 두 가지 변종으로 섞여 있다.**
58페이지 중 10페이지만 타이틀블록 소문자 텍스트(라벨·REV·리비전 이력)가
실제 텍스트 레이어입니다. 나머지 48페이지는 **모노라인 CAD 스트로크 폰트로
플롯되어 텍스트가 전혀 없는 벡터 폴리라인**입니다.
도면번호·제목·프로젝트명은 전 페이지 Arial 텍스트라 영향 없습니다.

`docs/design.md` §17 은 "대상 PDF가 100% 벡터이므로 OCR 미구현"이라고
적었는데, 그 결론 자체는 맞지만 근거가 한 단계 어긋납니다. 벡터라서 OCR이
불필요한 게 아니라, **벡터 도형을 문서 자체에서 부트스트랩한 글리프 템플릿과
매칭**해서 읽어야 합니다. 이 스크립트가 쓰는 방식입니다:

- 글자 템플릿 ← 리비전 이력 REV 칸 중 **1글자짜리 칸**. 이력 행은 아래에서
  위로 A, B, C… 순으로 채워지므로 행 순서가 곧 라벨입니다.
- 숫자 `1` 템플릿 ← SHEET 칸. 전 도면이 `1/1` 이고, 텍스트 변종 페이지에서
  그 값이 확인됩니다.
- 글리프는 잉크 바운딩박스로 크롭 후 고정 격자로 면적평균 → 위치·크기·선
  굵기에 무관. 문자당 템플릿을 **평균 내지 않고 리스트로 보관**해 서로 다른
  서체(스트로크 / Arial / 페이지 48의 굵은 서체)를 함께 인식합니다.

**② 리비전 이력 행 수로 Rev 를 추론하면 안 된다.**
페이지 7·9·20 은 이력 행이 A·B 두 줄인데 정작 REV 칸은 **A** 입니다.
원본 도면 자체가 불일치합니다. 행 수 기반 추론은 이 3페이지에서 틀립니다
(10개 정답 페이지 중 3개 오답 = 30%). 따라서 REV 칸은 **추론하지 않고 판독**
합니다.

**③ Rev 가 항상 한 글자가 아니다.**
페이지 48 은 Rev **`A1`** 입니다. REV 칸을 단일 글리프로 보지 않고 문자
단위로 분할해야 합니다.

**④ 페이지 48 은 다른 프로젝트 도면이다.**
EMPLOYER `PDP GEN TWO SDN BHD`, PROJECT NAME `PORT DICKSON 1400MW CCGT`
(나머지 57페이지는 `AL NOUF1 PROJECT`), Description 도 `FOR PROPOSAL`
(나머지는 `FOR INTERNAL USE`). 유입 경위 확인이 필요합니다.

**⑤ 도면번호가 중복된다.** `pid_page` 를 `drawing_no` 로 키잉하면 깨집니다.

| drawing_no | 페이지 | 제목 |
|---|---|---|
| `D00P-00GHC10-M05-0001` | 46 / 47 | DESAL. WATER SUPPLY / DEMINERALIZED WATER DISTRIBUTION (1 OF 2) |
| `D00P-00GMA10-M05-0001` | 52 / 55 | CHEMICAL WASTE WATER TRANSFER / WASTE WATER TRANSFER (SEA WATER / STORM WATER) |
| `D00P-10LBG10-M05-0001` | 12 / 15 | AUXILIARY STEAM SYSTEM GROUP 10 / GT FLASH PIPE SYSTEM UNIT 11 |

서로 다른 도면인데 번호가 같으므로 페이지 번호를 포함한 키가 필요합니다.
§11 중복 판정 로직과는 **별개 사안**입니다(같은 기기의 중복이 아니라 채번 오류).

**⑥ 2페이지가 270° 회전 저장되어 있다** (7, 48). `page.rotation_matrix` 로
동일 좌표계에 매핑하면 나머지 56페이지와 같은 규칙이 그대로 적용됩니다.
전 파이프라인이 이 변환을 거쳐야 합니다.

**⑦ `rev_date` 는 9/58 만 추출됩니다.** 날짜 역시 48페이지에서 스트로크
폰트라 글자 단위 판독이 필요한데, 숫자 0·2·5·9 와 월 약어 템플릿을
부트스트랩할 근거가 문서 안에 없습니다(SHEET 칸이 `1` 만 제공).
`rev_date` 는 필수 필드가 아니라 CSV에 공란으로 두고 실패로 잡지 않았습니다.
필요해지면 텍스트 변종 페이지에서 날짜 템플릿을 라벨링하는 작업이 별도로
필요합니다.

### 검증 방법

- 텍스트 레이어가 있는 10페이지에 대해 판독 결과와 텍스트를 대조 → **10/10 일치**.
- 나머지 48페이지는 `--rev-sheet` 산출물로 육안 확인 → **58/58 일치**.
- `unit_code` 는 `drawing_no` 에서 재유도해 교차 검증 → 불일치 0.

### 산출물

- `out/titleblocks.csv` — 58행. 필드별 값과 함께 `rev_method`(TEXT/GLYPH),
  `rev_confidence`, `rev_detail`(매칭 거리·마진), `status`, `issues` 를 같이
  기록합니다. 설계안 §4 의 "근거 없는 값은 저장하지 않는다" 원칙에 맞춘 것으로,
  그대로 `pid_page` + `item_evidence` 에 적재할 수 있습니다.
- `out/rev_cells.png` — REV 셀 58개 육안 검증 시트.
