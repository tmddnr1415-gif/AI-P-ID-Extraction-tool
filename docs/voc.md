# VOC — 부서원의 오류·요청을 개발이 읽고 반영하는 길 (hotfix71)

## 한 장 요약

```
부서원 (운영 서버 8000 · 대시보드 안)                 회사 Claude Code (C:\Claude\PID_dev)
  마크업 · 오검출 표시 · 오류 신고 · [VOC] · 실패 화면     python spike/voc.py list      ← 회차 시작
        │  분류 + 사유 + 로그인 이름                       python spike/voc.py brief     ← 한 장 요약
        ▼                                                  … 원인 재기 · 고치기 · 회귀 …
  C:\Claude\PID\voc\inbox\VOC-…\voc.json · crop.png  ──▶   python spike/voc.py resolve VOC-… --by … --release hotfix72
                                                             │
        ◀── resolution.json (그 VOC 폴더에) ──────────────────┤  C:\Claude\PID_dev\voc\ledger.json (장부)
  화면 목록: "반영됨 — hotfix72 (다음 업데이트에 포함)"         ▼
             → 업데이트가 깔리면 "(이 서버에 적용됨)"         다음 회차 list 에 다시 안 나온다 (중복 반영 방지)
```

## 부서원 쪽 — 어디서 남기나

| 입구 | 무엇이 담기나 |
| --- | --- |
| 마크업 — 누락 행 추가 (사각형) | 분류(㉡ 미검출 …) · **사유 필수** · 그 행 · 사각형 · 도면 조각 · 제안값 |
| 마크업 — 기존 상자 누름 (오검출 · 값 틀림 · 미지정 심볼) | 분류 · 사유 · 그 행(엔진 값 · 사람 값 · 적용 규칙) · 도면 조각 |
| 오류 신고 (행 · 도면 위치) | 신고 목록(DB)과 **VOC 함 둘 다** |
| 머리줄 / 첫 화면의 **[VOC]** | 어떤 내용이든 — 불편 · 느림 · 기능 요청 … 결과 화면이면 지금 장·고른 행을 함께 |
| 분석 실패 화면 **[VOC 로 신고]** | 실패 문장 · 멈춘 단계 · 예외 원문 |

마크업 대화상자에는 **"개발팀에 VOC 로 신고"** 가 기본으로 켜져 있다.  켜 둔 채로 사유를 비우면
저장되지 않는다 (끄면 예전처럼 마크업만 남는다).  작성자는 대시보드 로그인 이름(hotfix66)이다.

## 어디에 쌓이나

`app/voc.py` 의 `voc_root()` 하나가 정한다:

1. `PID_VOC_DIR` 이 있으면 거기
2. `PID_DATA_DIR`(시험 · 화면 자기검증) 이면 그 밑 `voc/`
3. exe 면 `pid_data\voc\`
4. 소스로 돌면 **그 폴더의 `voc\`** — 운영 PC 에서는 `C:\Claude\PID\voc\`, 개발 서버(8001)는 `C:\Claude\PID_dev\voc\`

한 건은 폴더 하나다 — `voc\inbox\VOC-20261009-142233-a1b2c3\voc.json` (+ `crop.png`).  다 쓴 뒤 이름을
바꿔 넣으므로 반쯤 쓴 VOC 는 보이지 않는다.  `voc/` 는 `.gitignore` 대상이고 꾸러미에도 들어가지 않는다
(도면 조각 · 사람 이름 · 분석 경로가 들어간다).

## 회사 Claude Code 쪽 — 읽고 반영하기

```bat
cd C:\Claude\PID_dev
python spike\voc.py list                  REM 미반영만 (오래된 것부터)
python spike\voc.py brief                 REM 미반영 전부 → out\voc_brief.md (행 · 엔진 값 · PDF 경로 · 조각 경로)
python spike\voc.py show VOC-…            REM 한 건 전부
REM … 원인을 재고(§9 · 렌더로 확인) 고치고 회귀를 돌린 뒤 …
python spike\voc.py resolve VOC-… VOC-… --by "Claude Code (회사)" --release hotfix72 --note "무엇을 고쳤나"
python spike\voc.py dup VOC-… --of VOC-… --by …        REM 같은 원인
python spike\voc.py wontfix VOC-… --by … --note "왜"   REM 고치지 않기로 함 (사유 필수)
python spike\voc.py needinfo VOC-… --by … --note "무엇이 더 필요한가"
```

`list` 는 이 폴더의 `voc\inbox` 와 **옆 폴더 `..\PID\voc\inbox`**(운영 서버에 쌓인 것)를 함께 읽고 id 로
하나로 센다.  다른 PC 에서 받은 inbox 는 `--inbox 경로` 로 더한다.

### 식별 VOC — O/X 평가는 "고칠 일" 이 아니라 "학습 자료" 다 (hotfix82)

부서원이 결과 화면의 **식별 VOC 탭**(또는 어느 탭의 O/X 칸)에서 행마다 적는 것 셋 — 식별 O/X(이 행이 식별되어야
하는가 · X 는 출력에서 빠진다) · 수량 O/X(Q'ty 가 맞는가) · 비고.  누락은 같은 탭에서 ＋행 마크업으로 더한다.
누르는 순간 저장되고(`row_verdict`) 요청마다 VOC 한 건(`source: VERDICT`)이 함에 쌓인다 — 행마다 엔진 값 · 자리 · 평가.
[VOC Excel] 이 그 탭을 파일로 낸다 (요약 · 식별 VOC · 누락 추가 · 출력 제외).

개발 쪽에서는 `list` 에 **안 나온다** (반영 표시할 일이 아니다).  대신 정답지로 모은다:

```bat
python spike\voc.py verdicts                          REM O/X 평가 · 마크업 → out\verdicts\<프로젝트>.json
python spike\verdict_set.py score out\run.json out\verdicts\QFE.json   REM 결과가 정답지를 얼마나 지키나
python spike\regression_3p.py                          REM out\verdicts\<이름>.json 이 있으면 참고축으로 같이 찍는다 (게이트 아님)
python spike\shape_train.py --pdf data\x.pdf --verdicts out\verdicts\QFE.json   REM 밸브 모양 사전 — O 는 보기로, X 는 거름
```

정답지의 한 줄 = 도면번호 · TYPE · 태그(또는 자리) · 판정(O · X · MISSED).  같은 항목에 여러 번 적혔으면 나중 것이
이긴다.  **판정 코드는 정답지를 읽지 않는다** — 재는 자이지 규칙이 아니다 (CLAUDE.md §9 · 44회차 [E-5]).

### 중복 반영을 막는 두 겹

1. **장부** `PID_dev\voc\ledger.json` — 처리한 id 마다 상태 · 누가 · 언제 · 어느 업데이트 · 무엇을.
   **지우지 않고 쌓기만 한다.**
2. **표시** — 그 VOC 가 있던 inbox 폴더에 `resolution.json`.  운영 화면이 이것을 읽어 "반영됨" 을 보이고,
   장부가 없는 새 개발 폴더에서도 다시 오르지 않는다.

둘 중 하나라도 있으면 `list` 에 다시 나오지 않고, `resolve` 는 이미 처리된 id 를 건드리지 않는다
(`이미 처리됨 … 건너뜀` · `--force` 로만).  운영 폴더에 표시를 못 쓰면(권한) 장부만으로 막고 그 사실을
장부의 `marker_errors` 에 남긴다.

### 반영 순서 (권장)

1. 회차를 시작하면 `list` → `brief`.
2. 같은 원인끼리 묶는다 — 한 원인을 고치면 그 VOC 들을 한 번에 `resolve` (나머지는 `dup --of`).
3. 고친 것은 **회귀 하네스로 확인한 뒤** `resolve` 한다 (`spike/regression_3p.py`).  `--release` 는
   그 수정을 담을 꾸러미 이름이다 — 운영 화면은 그 번호가 이 서버의 업데이트 딱지(hotfix34) 번호 이하가 되면
   "(이 서버에 적용됨)" 으로 바꾼다.
4. 도면이 답하지 않는 것(발주처 판단 · 실무 판단)은 `wontfix` 가 아니라 CLAUDE.md §5 에 올리고
   `needinfo` 로 두는 것이 맞다.

## 지키는 것

* VOC 는 **판정에 닿지 않는다** — 쓰기만 하고 엔진은 읽지 않는다 (지문 · 회귀 무관).
* 서버는 VOC 함에 **쓰기만** 한다.  반영 표시(`resolution.json` · 장부)는 `spike/voc.py` 만 쓴다.
* 운영 폴더의 `app\_data` 는 건드리지 않는다 — VOC 함은 그 밖(`PID\voc\`)이다.
