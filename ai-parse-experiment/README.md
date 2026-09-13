# AI 파싱 실험 — HTML + AI 로 P&ID 를 읽는다

기존 규칙 기반 도구와 **나란히** 둔 실험이다. 대체가 아니다.
바꾸는 것은 **읽는 부분 하나**이고, 행 스키마·화면·Excel 은 기존 것을 그대로 쓴다.

```
기존   PDF → 텍스트 레이어 + 규칙 → 행 → 화면 · Excel
실험   PDF → ★ AI 가 읽는다     → 행 → 같은 화면 · 같은 Excel
```

기존 저장소(`pid-instrument-tool/`, `pid-extractor/`)는 **읽기만 한다.**
이 디렉터리 밖의 파일은 고치지 않는다.

---

## 이 실험이 답하려는 것

> 규칙으로 알아낸 P&ID 읽는 법을, 글로 적어 AI 에게 주면 규칙만큼 읽는가.

목적은 둘 중 하나를 먼저 재는 것이다.

- **(a) 규칙을 대체한다** — 정확도가 규칙을 넘어야 한다
- **(b) 규칙을 감사한다** — 규칙이 놓친 것을 찾는다 ← 먼저 재는 쪽

---

## 돌리는 법

```bash
pip install pymupdf
cd ai-parse-experiment

# 0) 장치가 도는지부터 — API 없이, 합성 도면으로
python3 selftest.py

# 1) 최소 실험 — 5장. 58장을 바로 돌리지 않는다
export ANTHROPIC_API_KEY=sk-...
python3 run_experiment.py \
    --pdf ../pid-instrument-tool/inputs/AL_NOUF1_PID.pdf \
    --truth ../pid-instrument-tool/samples/test_set_v1/ground_truth.json \
    --pages 6,16,20,38,40 --repeats 3 --grid 3x2

# 2) 결과
#    out/ai_parse_result.zip  ← 0_요약 · 1_보고서 · 2_방법론 · 3_대조표
#                                4_결정성 · 5_감사수확 · 6_비용 · 7_캡처/
```

`--pages` 를 빼면 본문 장에서 **균등 간격**으로 고른다. 쉬운 장을 고르지 않는다.
`--pdf` 를 빼면 합성 도면으로 배관만 확인한다 — **그 숫자는 성적이 아니다.**

전량은 `--all-pages` + `AI_PID_CONFIRM_FULL=1` 이라야 돈다. 5장 결과를 먼저 본다.

### 정답지 모양

```json
{"rows": [{"pid_no": "D00P-10LBA10-M05-0001", "type": "PIT",
           "description": "UNIT #11 HP STEAM PRESSURE A", "page": 6}]}
```

`pid_no` · `type` · `description` · `page` 만 있으면 된다.
대조 키는 `P&ID No. + TYPE + 정규화 DESCRIPTION` 이고,
정규화 규칙은 `compare.py` 의 `norm_desc()` 한 곳에 모여 있다.

---

## 파일

| 파일 | 하는 일 |
|---|---|
| `methodology/pid_reading.md` | ★ AI 에게 주는 방법론 문서 전문. 이 실험의 진짜 자산 |
| `schema.py` | 기존 `config/excel_format.json` 을 읽어 행 스키마를 든다. 여기서 정의하지 않는다 |
| `render.py` | PDF → 이미지 + 결정적 텍스트 레이어 (`pdfscan.js` 와 같은 규칙) |
| `analyzer.py` | AI 호출. 방법론을 system 으로, 출력을 JSON 스키마로 강제 |
| `baseline.py` | 기존 규칙 기준선을 **고치지 않고** 옮긴 것. 대조 상대 |
| `compare.py` | D-1 정답지 대조 · D-3 좌표 오차 · D-5 감사 수확 |
| `determinism.py` | D-2 결정성 |
| `cost.py` | D-4 토큰·시간·해상도 스윕 |
| `run_experiment.py` | 전체를 돌려 `out/ai_parse_result.zip` 을 낸다 |
| `selftest.py` | API 없이 측정 장치가 도는지 확인 |
| `make_fixture.py` | 합성 도면 생성 (배관 확인 전용) |

---

## 알아 둘 것

**결정성을 먼저 잰다.** 기존 도구의 규율은 '같은 입력 → 같은 지문' 이고
회귀 시험이 그것으로 결함을 잡는다. AI 가 같은 장에 다른 답을 내면
정확도가 아무리 좋아도 (a) 대체는 불가능하다.
`determinism.py` 는 흔들리는 스텁을 실제로 잡아내는 것까지 `selftest.py` 에서 확인한다.

**해상도는 DPI 가 아니라 분할 수가 정한다.** 모델이 이미지를 장변 1568px 로
줄여 보므로 `--dpi` 를 올려도 실효 해상도는 안 오르고 업로드 바이트만 는다.
올리려면 `--grid` 를 잘게 한다. 대가는 `6_비용.md` 의 스윕 표에 있다.

**AI 가 채우지 않는 칸이 있다.** `sensing_type` · `element_type` · `mounting_type` ·
`signal_type` · `base_option` 은 `inst_typical_type` 에서 코드가 결정적으로 파생한다.
같은 부품에서 매번 같은 값이 나와야 회귀가 성립하기 때문이다.

**폐쇄망.** 회사 PC 는 외부 API 를 못 쓴다. 결과가 좋아도 회사 PC 에 그대로 못 올린다.
남는 쓰임은 새 프로젝트 온보딩 때 **개발 PC 에서** 한 번 돌려
규칙이 놓치는 자리를 찾아 규칙에 되먹이는 것이다. 상시 판독 경로가 될 수 없다.

**못 잰 것은 '못 쟀다' 고 적는다.** 도면·정답지·API 키 중 무엇이 없으면
그 칸은 `측정 못 함` 으로 남는다. 채우지 않는다.
