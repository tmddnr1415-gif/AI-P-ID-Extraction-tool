# [B] `anchors.type_map` 재바인딩 — 결함 1개 · 같은 결함의 다른 사례 · 25개 재판정

## B-1 고친 것

`detect_symbols.ruleset_v3(cfg)` **한 곳**이 `anchors.type_map`·`anchors.not_field` 로 배포 룰셋을 만든다.
import 때 `RULESET_V3 = ruleset_v3(CFG)` 로 한 번, 그리고 **`pipeline._rebind_config` 이 지금 CFG 로 다시 만든다**
(`RULESET_V3` · `FIELD_TYPE_MAP` · `NOT_FIELD_INSTRUMENT` · `ANCHORS` 넷을 같은 표로).
파이프라인은 `ds.RULESET_V3` 를 **속성으로** 읽으므로(`pipeline.py:806` `rules=ds.RULESET_V3`) 재바인딩이 닿는다.
`detect()` 의 기본 인자는 import 때 객체에 묶이지만 파이프라인은 그 기본값을 쓰지 않는다.

같이 다시 만들게 한 셋 — **유도·overlay 가 값을 바꿀 수 있는 키**:

| 값 | 키 | 왜 |
| --- | --- | --- |
| `tb._UC_SEG` · `_UC_FROM/_UC_TO` | `formats.unit_code_segment/chars` | 35회차 미실측(B) — 유도 후보 |
| `da._SC_FROM/_SC_TO` | `formats.system_code_chars` | 같음 |
| `pidcache._DEDUP_WORDS` | `text.dedup_exact_duplicates` | `_fit_layout` 이 **유도해 얹는** 항목 (moved58: `None→False`).  ⚠ `load_pages` 가 `_fit_layout` **앞**에서 읽으므로 이 문서에는 못 닿고 다음 문서부터 닿는다 — 유도값이 그 문서의 낱말에서 나오니 구조상 그럴 수밖에 없다.  같은 프로세스에서 다음 문서로 새지 않게 `_own_config` 가 되돌린다 |

## B-1 ★ import 때 굳는 값 전수 — 37 (AST 로 셌다: 모듈 최상위 대입 중 RHS 에 `CFG`/`cfg.get`)

`_rebind_config` 이 다시 만드는 것 (36회차 뒤 **20**): `ds.LAYOUT` · `ds.KNOWN_GLYPH_SIZES` · `ds.RULESET_V3`+별칭 3 ·
`tb.LAYOUT` · `tb.DWG_NO_RE/DATE_RE/REV_TEXT_RE` · `tb._UC_*` 3 · `da.HANGUL_RE` · `da.REQUIRE_FILL` · `da._SC_*` 2 ·
`dv.LAYOUT` · `pidcache.PROJECT_NAME_REGION/_MIN_HEIGHT` · `pidcache._DEDUP_WORDS`.

**다시 만들지 않는 것 — 같은 결함의 다른 사례 (17)**.  전부 D·E 등급이라 **어느 유도도 건드리지 않으므로**
한 프로세스 안에서 CFG 와 갈릴 길이 없다 (프로필은 import 때 한 번 읽히고 런타임 전환이 없다 — `projectconfig.load` 는
`pipeline`·`ds`·`dv`·`tb`·`da`·`pidcache`·`main` 이 각자 import 때 한 번씩 부른다).  다음 회차 후보로 목록만 낸다:

| 모듈 | 값 | 키 | 등급 |
| --- | --- | --- | --- |
| `detect_all` | `STOPWORDS` | `matching.stopwords` | E |
| `detect_valves` | `DELIVERABLES` · `CV_TAGS` · `XV_TAGS` · `TYPE_ACTUATOR` | `valves.deliverables/cv_tags/xv_tags/valve_type_actuator` | D |
| `main` | `DOC_REV_RULE` | `revision.document_rule` | D |
| `pipeline` | `ACTIVE_SCOPE` · `VALVE_DISABLED` · `SCOPE_OVERRIDES` · `SUPPLIER_SPAN` · `_VENDOR_DESC` · `MULTI_SIGNAL_TYPE/MERGE/DESCRIPTION` · `_SUPPLIER_RE` · `_TYPE_DISPLAY` | `scope.*` · `valves.disabled_rules` · `qty_scope_overrides` · `supplier_interface_span` · `multi_signal_bundle.*` · `description.type_display_names` | D |

**⚠ 이것이 곧 22회차 격리의 경계다** — `_own_config` 는 CFG 를 되돌리고 `_rebind_config` 을 부르지만, 위 17 은
그 함수 밖에 있다.  지금은 유도가 안 건드리므로 안전하고, **어느 하나가 유도 대상이 되는 순간** 이 표에서
`_rebind_config` 으로 옮겨야 한다.  `tests/test_config_isolation.py` 가 `global` 문만 세므로 이 표는 못 본다.

## B-2 25개 재판정 — 전부 ㉣ (유도 없음 → 멈춤)

worktree `/tmp/r35_strip` 에 같은 재바인딩을 넣고, 35회차와 같은 방법(유도가 얹힌 뒤 `anchors.*` 25잎을 sentinel 로 · 나머지 전부 되살림)으로
탐침 10장을 돌렸다 (`out/round36/b2_anchors_probe.json`):

```
ok=false · missing=cfg.anchors.type_map.TT · 89.8초 · MissingConstant (유도 뒤 _rebind_config → ruleset_v3 에서)
```

35회차에는 같은 실험이 **199행 · `0087c236` 로 완주**했다 — 검출이 import 때 굳은 표를 읽어서다.  이제 표가 CFG 를 따라
다시 만들어지므로 첫 잎에서 멈춘다.  `ruleset_v3` 는 `type_map` 의 잎 **전부**를 `str(v)` 로 읽고 `not_field` 도 순회하므로,
하나를 되살리면 다음 잎에서 같은 방식으로 멈춘다 — 25개 모두 **㉣** 이고, 한 번 더 돌려 두 번째 잎에서 멈추는 것까지
확인할 가치는 없다(코드가 그렇게 읽는다).

| 판정 | 35회차 | 36회차 |
| --- | ---: | ---: |
| 시험불가 | 25 | **0** |
| ㉣ 유도 없음 | 26 | **51** |

다섯 목록: **결함 25 → 0**, 그 25는 **사람 지정**(A/D — `TT→TIT` 같은 접기는 발주처 표기, 범례 p3 ISA 표에는 `TIT`·`FIT`·`LI` 가
인쇄되지 않는다 — `detect_symbols.py` 의 주석이 처음부터 그렇게 적었다).  다만 **앵커 낱말 자체**(TT·PT·LSH …)는 범례
ISA 표가 정의하고 `isa_table.derive` 가 런타임에 읽고 있다 — 접기 값이 아니라 **키 집합**은 도면이 답할 수 있는 자리다
(18회차 [G] 가 AT·AIT 를 넣으면 축2 가 내려간다고 쟀으므로 자동 확장은 아니고, "config 앵커 중 이 도면 범례에 없는 것" 을
말해 주는 감사 자리).  다음 회차 후보.

## B-3 게이트 — 통과

`out/round36/8_regression_4p_BC.json` ([B]+[C] 코드): AL NOUF1 `fb85b039`·1037·1931·축3 95.1 · SADARA `0767ba79`·82 ·
TC2 `c0a2d29d`·607·3047 · UAD `db1a77d1`·149 — **"기준선과 같습니다"**.  type_map 이 유도로 바뀌어 AL NOUF1 이 움직이는
일은 없다 — 유도가 없으므로(㉣) 표는 언제나 config 그대로다.  순서 바꿔 돌리기는 [F] 에서.
