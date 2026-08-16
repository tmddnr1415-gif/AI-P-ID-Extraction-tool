# P&ID Instrument List 자동 생성 도구 (파일럿)

P&ID PDF 도면을 읽어 지정된 Excel 포맷(`2.0_Instrument List`)으로 Field Instrument 목록을
만들고, **사람이 검토하며 지적한 오류를 판독 규칙으로 되먹여 정확도를 올리는** 반복 검증
파이프라인입니다.

결과물은 실제 플랜트 설계에 쓰이는 **안전 관련 문서**입니다. 이 도구는 초안 작성용이며,
**모든 출력은 사람의 검토를 거쳐야 합니다.**

## API 없이 어디까지 되나

`API 없이 시험 실행` 을 켜면 호출 없이 돌아갑니다. 판독 컬럼 7개 중 **5개**가 채워집니다.

| 컬럼 | API 없이 | 왜 |
|---|---|---|
| `SYSTEM` | ✅ | 도면 제목을 템플릿 SYSTEM 목록과 맞춘다 |
| `P&ID No.` | ✅ | 타이틀블록 |
| `TYPE` | ✅ | 텍스트 레이어의 계기 문자 (`PT`→`PIT`) |
| `Q'ty` | ✅ | NOTES의 `CONFIGURATION IS IDENTICAL FOR ...` |
| `INST. TYPICAL TYPE` | ✅ | 계통+TYPE별 템플릿 최빈값 |
| `DESCRIPTION` | ❌ | 도면 그림에서 설비·배관 맥락을 읽어야 한다 |
| 벤더 공급 범위 제외 | ❌ | `*` / `**` 가 텍스트가 아니라 도형이라 못 읽는다 |

**되는 것**은 계기를 빠짐없이 찾아 표로 세우는 일입니다. 텍스트 레이어에 좌표까지
정확히 들어 있어서 셈이 틀리지 않습니다.

**안 되는 것**은 그 계기를 뭐라고 부를지, 그리고 남의 공급 범위인지 판단하는 일입니다.
둘 다 도면 그림을 봐야 합니다.

그래서 API 없이 쓸 때는 이렇게 됩니다.

1. 시험 실행으로 계기 표를 만든다 (돈 안 듦)
2. `확인 필요` 에 그 도면의 공급 범위 각주 원문이 그대로 뜬다
3. 검토 UI에서 `*` 붙은 계기 행을 지우고 DESCRIPTION 을 채운다
4. Excel 로 받는다

`D00P-10PGB10-M05-0004`(CCW) 처럼 공급 범위 표기가 없는 도면은 **DESCRIPTION만 채우면
정답과 같아집니다**(24행 · TYPE · TYPICAL 일치). `D00P-10LBA10-M05-0001`(HP Steam)처럼
표기가 많은 도면은 34행 중 22행을 사람이 지워야 합니다.

### 비용을 줄이려면

판독 화면에 **예상 입력 토큰**이 뜹니다. 대부분이 도면 이미지라 여기서 줄입니다.

| 설정 | 도면당 입력 토큰 |
|---|---|
| 타일 3x2 · 200dpi (기본) | 약 54k |
| 타일 2x2 · 150dpi | 약 20k |

타일을 줄여도 **계기 문자는 텍스트 레이어에서 정확히 오므로** 놓치지 않습니다.
타일은 설비명·배관 맥락을 보는 용도라 해상도를 낮춰도 크게 상하지 않습니다.
모델을 Sonnet으로 바꾸는 것도 ⚙ 설정에서 됩니다. 단가는 계정마다 다르니
[Console](https://console.anthropic.com/settings/billing)에서 확인하세요.

## 도면이 많을 때 — 5장씩 끊어 돌리기

58장을 한 번에 돌리지 마세요. **5장씩 끊어서 보고 고치는 편이 빠릅니다.**

```
5장 판독 → Excel 받아 검토 → 이상한 값 표시 → 규칙 고침 → 그 5장 다시 판독
                                                              ↓ 맞으면
                                                        다음 5장
```

판독 결과는 **쌓입니다.** 5장 돌리고 다음 5장을 돌리면 10장이 됩니다.
이미 판독한 도면을 다시 고르면 **그 도면 행만** 새 결과로 바뀌고 나머지는 그대로입니다.
브라우저를 닫아도 남아 있고, `결과 비우기` 로 언제든 처음부터 시작할 수 있습니다.

규칙이 안정되면 그때 남은 도면을 한 번에 돌리면 됩니다.

### 이상한 값을 규칙으로 바꾸는 길

1. 앱에서 **검토용 JSON** 을 받습니다.
2. `review-ui/standalone.html` 에 넣고 틀린 셀을 고칩니다. 셀마다 **사유**와
   **앞으로 어떻게 나와야 하는지** 를 적는 칸이 있습니다.
3. **피드백 JSON** 을 내보냅니다.
4. 그 파일을 Claude Code 세션에 주면 `rules/*.md` 를 고치고 `review_log.md` 에 남깁니다.
   (직접 하려면 `python3 scripts/apply_feedback.py <피드백.json> --apply-rules`)
5. `python3 scripts/build_web.py` 로 앱을 다시 만들면 새 규칙이 들어갑니다.
6. 같은 5장을 다시 판독해 고쳐졌는지 봅니다.

앱의 **불러오기** 는 앱이 내보낸 검토용 JSON과 파이썬 파이프라인의 `extraction.json`
둘 다 받습니다. 다른 컴퓨터에서 돌린 결과나 Claude Code가 만든 결과를 앱에서 열어
검토하고 Excel로 뽑을 수 있습니다.

## 세 가지 사용법

**① 웹 앱 — 설치 없이 브라우저에서 전 과정** (`web/standalone.html` 더블클릭)

PDF 넣기 → 도면 골라 판독 → **템플릿 서식 그대로의 Excel 다운로드**까지 브라우저에서 끝납니다.
파이썬도 서버도 필요 없고, 필요한 건 Anthropic API 키 하나입니다.
파이썬 파이프라인과 **같은 규칙·같은 프롬프트·같은 Excel 쓰기 방식**을 씁니다.

| | 웹 앱 (파일) | 공유 링크 서버 | 파이썬 파이프라인 |
|---|---|---|---|
| 설치 | 없음 (파일 하나) | 없음 (링크 접속) | `pip install -r requirements.txt` |
| API 키 | 각자 입력 | **서버에만** | 환경변수 |
| Excel 템플릿 | 각자 업로드 | **서버가 제공** | `inputs/` |
| 도면 판독 | ✅ | ✅ | ✅ |
| 템플릿 서식 Excel | ✅ | ✅ | ✅ |
| 사용량 한도 | ✕ | **하루 N장 (KV)** | ✕ |
| 규칙 편집 | 앱 안에서 | 배포자만 (재배포) | `rules/*.md` (git 이력) |
| 검토 피드백 | 검토용 JSON → 리뷰 UI | 검토용 JSON → 리뷰 UI | `apply_feedback.py`로 자동 |
| 배치·자동화·CI | ✕ | ✕ | ✅ |

혼자 몇십 장 돌려보는 데는 웹 앱이, 규칙을 팀이 같이 관리하고 이력을 남기려면 파이썬 쪽이 맞습니다.
결과 JSON 형식이 같아서 **웹 앱 결과를 리뷰 UI로 검토**할 수 있습니다.

```bash
# 웹 앱을 원본에서 다시 빌드할 때
python3 scripts/build_web.py
```

**② 공유 링크 서버** — 팀에 링크 하나로 나눠줄 때 (`server/`)

링크를 받은 사람이 **비밀번호만 넣으면** 어느 컴퓨터에서든 쓸 수 있습니다.
API 키는 서버에만 있고 브라우저로 내려가지 않으며, Excel 템플릿도 서버가 내려줍니다.
사용자는 **PDF만 넣으면** 됩니다. Cloudflare Workers 무료 플랜으로 배포합니다.

```bash
cd server && ./deploy.sh        # 빌드 · KV 한도 · 비밀값 · 배포를 한 번에
```

접속 주소와 비밀번호만 공유하면 됩니다. 자세한 내용은 [`server/README.md`](server/README.md).

**③ 파이썬 파이프라인** — 아래 내용.

## 파이프라인

```
Excel 템플릿 ──▶ inspect_template.py ──▶ config/excel_format.json (컬럼 스펙)
                                        config/typicals.json     (TYPICAL → 사양)
                                        samples/…/ground_truth.json (정답 563행)

P&ID PDF ──▶ pdf_to_images.py ──▶ 도면 이미지 + 확대 타일 + manifest.json
                                   (텍스트 레이어 계기 문자 좌표 포함)
                    │
                    ├──▶ parse_legend.py ──▶ rules/symbol_legend.md
                    │
                    └──▶ extract_instruments.py ──▶ outputs/run_*/extraction.json
                              (rules/*.md 를 시스템 프롬프트로, 이미지+후보 좌표를 입력으로)
                                        │
                                        ▼
                                  build_excel.py ──▶ instrument_list.xlsx  ← 사람이 검토
                                                     result.json           ← 리뷰 UI 입력
                                        │
                                        ▼
                        review-ui/index.html  (셀 수정 + 사유 + 향후 규칙 코멘트)
                                        │
                                        ▼
                                  apply_feedback.py ──▶ review_log.md
                                                        rules/extraction_guide.md
                                                              │
                                                              └─▶ 다시 판독 (정확도 개선 확인)
```

## 설치

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

원본 도면과 템플릿은 `inputs/`에 둡니다(`.gitignore` 처리되어 커밋되지 않습니다).

## 실행 순서

```bash
# 0. 템플릿 해부 — 컬럼 스펙과 TYPICAL 표, 정답 데이터 생성 (최초 1회)
python3 scripts/inspect_template.py inputs/D00P-00CZE00-J30-0001_RC_Field_Instrument_2512xx.xlsx

# 1. PDF → 이미지 + manifest (레전드 4장 + 검증용 도면)
python3 scripts/pdf_to_images.py inputs/D00P_PID_Total_20251125.pdf --pages 2-5,6,16,20,38,40 --tiles 3x2

# 2. Symbol & Legend 판독 → rules/symbol_legend.md
python3 scripts/parse_legend.py --pages 2,3,4,5 --force

# 3. 계기 판독 (도면 1장당 1회 호출)
python3 scripts/extract_instruments.py --pages 6,16,20,38,40

# 4. Excel 생성 (템플릿 서식 그대로)
python3 scripts/build_excel.py outputs/run_YYYYMMDD_HHMM/extraction.json

# 5. 사람이 Excel 검토 → 리뷰 UI에서 수정 (아래 참조)

# 6. 피드백 반영
python3 scripts/apply_feedback.py ~/Downloads/feedback_run_YYYYMMDD_HHMM.json --apply-rules
```

API 키 없이 파이프라인 형태만 확인하려면 3단계에 `--dry-run`을 붙입니다.
텍스트 레이어만으로 기준선 결과를 만들어 4~6단계를 그대로 돌려볼 수 있습니다.

## 검토 UI

여는 방법이 두 가지입니다.

**① 설치도 서버도 없이** — `review-ui/standalone.html` 을 브라우저로 그냥 엽니다(더블클릭).
CSS와 JS가 한 파일에 들어 있어 메일이나 메신저로 그대로 보내도 동작합니다.
원본을 고친 뒤에는 다시 빌드하세요.

```bash
python3 scripts/build_standalone.py
```

**② 개발용** — 원본 3개 파일을 서버로 띄웁니다.

```bash
python3 -m http.server 8000        # 프로젝트 루트에서
# 브라우저에서 http://localhost:8000/review-ui/index.html
```

둘 다 기능은 같습니다. `outputs/run_*/result.json`을 열면 되고,
파이프라인을 아직 돌리지 않았다면 **샘플 데이터로 둘러보기**로 흐름만 먼저 볼 수 있습니다.

- 셀을 클릭하면 **정확한 값 / 오류 유형 / 왜 틀렸는지(사유) / 앞으로 어떻게 출력되어야
  하는지(규칙 코멘트)** 를 입력하는 패널이 열립니다. **사유와 규칙 코멘트는 필수**입니다 —
  이 두 칸이 다음 규칙 개정의 근거가 되기 때문입니다.
- 없는 계기를 잡아냈으면 **오탐 삭제**, 빠뜨렸으면 **누락 추가**로 처리합니다. 여기도 같은 두 칸이 필수입니다.
- 모델이 **제외한 후보**와 **확인 필요 사항**을 함께 보여줍니다. 누락의 원인을 여기서 추적할 수 있습니다.
- 확신도 `low` 행, 아직 안 본 행만 필터링해서 볼 수 있고, 검토 진행률이 표시됩니다.
- 검토 내용은 브라우저에 자동 저장되어 새로고침해도 남습니다.
- 내보내기: **피드백 JSON**(→ `apply_feedback.py`), 수정 반영 `result.json`,
  수정 반영 CSV, `review_log` 스니펫.

## 첨부 자료 분석에서 확인한 사실

이 파이프라인 설계의 근거입니다. 자세한 내용은 `review_log.md` 초기화 항목에 있습니다.

**모델이 도면에서 판독해야 하는 컬럼은 42개 중 7개뿐입니다.**
정답 Instrument List 563행을 분석한 결과입니다.

| 출처 | 개수 | 컬럼 |
|---|---|---|
| `drawing` (도면 판독) | 7 | SYSTEM, P&ID No., TYPE, Q'ty, DESCRIPTION, INST. TYPICAL TYPE, REMARK |
| `typical` (TYPICAL TYPE으로 결정) | 5 | SENSING/ELEMENT/Mounting/Signal Type, BASE OPTION |
| `design_table` (별도 표에서 조인) | 19 | 운전·설계 조건, 배관 정보, 교정 범위, 재질 등 |
| `blank` (템플릿에서 전 행 비어 있음) | 9 | UNIT, SYSTEM CODE, SYSTEM SEQUENCE, TAG, MAKER, MODEL, STATUS 등 |
| `auto_index` / `review` | 2 | NO, 비고란 |

**TAG 열은 563행 전부 비어 있습니다.** 제안 단계 도면이라 계기 버블의 태그 자리가
점선(`.....`)으로 비어 있기 때문입니다. → 태그 번호를 생성하지 않습니다.
행 식별은 `P&ID No. + TYPE + DESCRIPTION` 조합으로 합니다.

**PDF에 텍스트 레이어가 있습니다.** 계기 문자를 좌표까지 결정적으로 추출할 수 있어
판독의 기준선으로 씁니다. 검증 결과:

| 도면 | 텍스트 레이어 | 정답 행 | 차이의 원인 |
|---|---|---|---|
| p38 CCW (4/7) | 24건 | 24행 | 정확히 일치 |
| p20 HRSG Feedwater | 37건 | 33행 | `PT/FT/TT` → `PIT/FIT/TIT` 매핑, `ZS` 제외 |
| p6 HP Steam | 34건 | 12행 | **Q'ty 통합 + 벤더 패키지 범위 제외** |

마지막 행이 이 파일럿의 핵심 난이도입니다. 원시 검출은 거의 완벽하지만,
**무엇을 한 행으로 묶고 무엇을 범위에서 빼는지**가 규칙으로 축적되어야 할 부분입니다.

## 이번 단계 범위와 남은 일

이번 단계는 **Field Instrument 카테고리만** 다룹니다.

- [x] 폴더 구조 / 스크립트 뼈대 (워크플로우 1~4)
- [x] Excel 템플릿 해부 → 컬럼 스펙·TYPICAL 표·정답 데이터 자동 생성
- [x] PDF → 이미지 + 타일 + 텍스트 레이어 계기 후보 추출
- [x] Symbol & Legend 파싱 스크립트
- [x] 계기 판독 (구조화 출력 + 프롬프트 캐싱)
- [x] 템플릿 서식을 유지하는 Excel 생성
- [x] 검토 UI (셀 수정 + 사유 + 규칙 코멘트) 및 피드백 → 규칙/로그 반영
- [x] 브라우저 단독 앱 (PDF → 템플릿 서식 Excel)
- [x] 공유 링크 서버 (비밀번호 인증 + 서버 보관 API 키 + 하루 사용량 한도)
- [ ] `compare.py` — 정답과 자동 대조 (워크플로우 5). DESCRIPTION 정규화 규칙 합의 필요
- [ ] Design Table 조인 (19개 컬럼) — `1.2_Designtable` 시트를 받으면 구현 가능
- [ ] Valve / DCS I/O 카테고리 확장 (`inputs/`에 참고 자료가 이미 있음)

## 확인이 필요한 사항

- `rules/symbol_legend.md`가 이 프로젝트의 Symbol & Legend 도면에서 추출된 것이 아니라
  일반 기준입니다. `parse_legend.py`(API 키 필요)를 돌리면 도면에서 뽑아 채웁니다.
- PDF p15의 타이틀블록 도면번호가 p12와 중복입니다(도면명은 GT Flash Pipe System).
- `D00P-00PAB10-M05-0001`이 p26/27/28/30에 중복 사용되고 있습니다.
- 정답 Excel의 P&ID No. 41개 중 10개가 PDF 58쪽에 없습니다. 도면 세트가 일부 누락된 것인지 확인이 필요합니다.
- TYPICAL TYPE으로 결정되지 않는 컬럼 5개(교정 범위/단위, 소자 재질, 연결 형식, TW 사양,
  방폭 등급)는 서비스 조건에 따라 달라집니다. Design Table 쪽에서 채워야 합니다.
