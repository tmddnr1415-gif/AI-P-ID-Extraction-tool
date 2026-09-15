# 새 프로젝트 P&ID 를 받았을 때

이 문서는 **무엇이 그대로 따라오고 무엇을 다시 재야 하는지**만 말합니다. 수치의
근거는 `CLAUDE.md`, 항목별 계수는 각 config 파일의 주석에 있습니다.

규칙은 세 층입니다.

| 층 | 위치 | 새 프로젝트에서 |
| --- | --- | --- |
| **범례 유도** | 코드 (`legend_rules` · `isa_table` · `describe_equipment.derive_symbols`) | **그대로.** 그 문서의 범례에서 런타임에 다시 잽니다 |
| **① 업계 표준 약어** | `config/plant_standard_abbr.yaml` | **그대로 복사.** 발전 플랜트면 같습니다 |
| **② 표기 선택 · ③ 프로젝트 고유** | `config/project_<이름>.yaml` | **다시 채웁니다** — 아래 목록 |

이 프로젝트에서 잰 값: 기기 라벨 **486건 중 379건(78.0%)** 은 범례 어휘만으로
잡힙니다. 나머지 **22%** 가 아래 ③층 항목에서 나옵니다.

## 0. 먼저 확인할 것 (입력이 없으면 그 산출물은 사유와 함께 건너뜁니다)

- [ ] `data/` 에 도면 PDF 와 빈 양식 3종을 넣었는가 (`CLAUDE.md` §6 의 파일명)
- [ ] 범례 시트가 문서에 포함돼 있는가 — Symbol & Legend, ISA 문자표(보통 p3),
      EQUIPMENT 표(보통 p2). 없으면 **거의 모든 유도가 불가**하고 그렇게 보고됩니다
- [ ] 타이틀블록 형식이 같은가 (도면번호·unit code·제목 위치)

## 1. ①층 — 손대지 않습니다

`config/plant_standard_abbr.yaml` 는 그대로 복사합니다. **방향을 고정하지 않으므로**
새 발주처가 어느 형태를 쓰든 그대로 쓸 수 있습니다.

- [ ] 그 플랜트에만 있는 약어가 나오면 `candidates:` 에 **후보로만** 추가하고
      실무자 확인 후 `confirmed:` 로 옮깁니다
- [ ] **프로젝트 고유 표기를 여기 섞지 마세요.** 이 프로젝트에서는 `CD`(이 플랜트의
      계통명)와 `RO`(계기 태그와 충돌)를 프로젝트 파일로 내렸습니다

## 2. ②층 — 표기 선택 (발주처 리스트가 있을 때만)

`description.equipment_alias_choice` — ①의 각 세트에서 **이 발주처가 기기 이름으로
쓰는 형태**를 고릅니다. 이름(머리) 자리에서 쓴 적이 없는 세트는 **비워 둡니다**.

- [ ] 발주처 리스트에서 세트별 머리/수식어 사용 횟수를 세었는가
- [ ] 센 값을 주석으로 함께 적었는가

발주처 리스트가 없으면 이 층은 비웁니다 — 별칭이 적용되지 않을 뿐, 나머지는 돕니다.

## 3. ③층 — 프로젝트 고유값 (`config/project_<이름>.yaml`)

각 항목 옆에 **센 횟수를 주석으로 남기는 것이 규칙**입니다. 근거 없는 값은 넣지
않습니다.

| 항목 | 무엇을 재는가 | 없으면 |
| --- | --- | --- |
| `regions.*` · `matching.*` | 타이틀블록·도면영역 좌표, 제목 매칭 불용어 | 필수 |
| `description.prefix` / `unit_mark` / `title_open` / `title_close` | 문장 머리와 제목 괄호 낱말 | 필수 |
| `description.unit_prefix_skip_codes` | 발주처가 접두어를 안 쓰는 unit code | 접두어가 항상 붙음 |
| `description.variable_words` | 범례 문자표에 없거나 발주처 철자가 다른 태그 | 범례 표기 그대로 |
| `description.alarm_suffix` | 스위치 꼬리 문자(H/L) 표기 | 접미 없음 |
| `description.position_word_types` | 위치어를 쓰는 계기 TYPE (부착률 1/3 이상) | 위치어 없음 |
| `description.position_by_side` / `_by_system` / `_by_noun` | 방향·계통·기기종류별 위치어 | 좌우 기하만 |
| `description.end_ordinal_types` | 끝 순번을 쓰는 TYPE | 끝 순번 없음 |
| `description.line_phrase_types` | 라인 문구(`TO ...`)를 쓰는 TYPE | 라인 문구 없음 |
| `description.system_abbreviations` | 제목 어구 ↔ 발주처 약어 | 제목 그대로 |
| `description.equipment_words` | 범례 EQUIPMENT 표 밖의 기기 명사 | 범례 어휘만 (이 문서에서 78%) |
| `description.equipment_modifiers` | 그 명사 앞에 발주처가 쓰는 수식어 | 배관 주석이 섞임 |
| `description.between_symbol_types` | 중간 심볼을 쓰는 TYPE | 전 TYPE 에 제안 |
| `description.sole_equipment_sheet_max` | 기기가 몇 개 이하인 시트에서 거리 제한을 끄는가 | 항상 거리 제한 |
| `description.user_input_reasons` | 도면이 답하지 못한다고 **측정된** 부류 | 사유 표시 없음 |
| `description.project_abbreviations` | ①에 없는 이 프로젝트만의 약어 | 없음 |

**필수 3 · 발주처 리스트가 있어야 채울 수 있는 것 12 · 선택 2** — 모두 **17항목**.

## 4. 발주처 리스트가 없을 때 (실사용 기본)

실사용 입력은 **PDF + 빈 양식**뿐입니다. 위 12항목은 비워 두고 시작하며, 그러면:

- 계기·밸브 검출, 스코프, 수량, 등급, Excel 출력은 **전부 정상 동작**합니다
- Description 은 `UNIT #n + 계통 + 변수어` 까지 나오고, 중간 서술은 도면이 기기
  이름을 인쇄한 곳에서만 채워집니다
- 나머지는 `PARTIAL` 등급과 Remark 사유로 표시되어 검토 화면에서 직접 입력합니다

## 5. 회귀

- [ ] `pytest -q -m "not slow and not ui"` (5초)
- [ ] `pytest -q -m slow` · `-m ui`
- [ ] `fingerprint` 를 기록하고, 검출을 바꾸지 않았는데 바뀌면 원인을 규명합니다
