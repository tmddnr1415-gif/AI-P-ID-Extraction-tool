# P&ID Instrument Extractor

## 0. 당신이 만들 것

**단일 파일 HTML** 하나. Claude.ai Artifact 런타임에서 동작하며 publish 가능해야 한다.

사용자가 P&ID PDF를 드래그앤드롭하면, Claude Vision이 도면을 판독하여 계기(Instrument)를 식별하고, 지정된 Excel Instrument List 포맷으로 출력해 다운로드시킨다.

**최종 산출물 경로: `./index.html`** (다른 파일로 분할하지 말 것)

---

## 1. 프로젝트 구조

```
pid-extractor/
├── CLAUDE.md                          ← 이 문서
├── index.html                         ← 당신이 만들 유일한 산출물
├── ref/
│   ├── example_instrument_list.xlsx   ← 정답 산출물 (572행). 포맷 기준
│   └── PID_Total.pdf                  ← 테스트용 도면 41장
└── dev/
    └── notes.md                       ← 판독 오류와 규칙 보정 이력 (당신이 갱신)
```

---

## 2. 절대 제약 — 위반 시 동작하지 않음

Artifact 샌드박스 규칙이다. 예외 없다.

| 금지 | 대체 |
|---|---|
| `localStorage`, `sessionStorage` | `window.storage` (§6) |
| `<form>` 태그 | `onClick` 핸들러 |
| 외부 API 호출 | Claude 엔드포인트만 허용 |
| cdnjs 외 CDN | `cdnjs.cloudflare.com`만 |
| OCR 라이브러리 (Tesseract 등) | 사용하지 않음. §3 참조 |
| API 키 입력 UI | 불필요. 키 없이 호출됨 |

**Claude 호출 규격**

```javascript
const response = await fetch("https://api.anthropic.com/v1/messages", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "claude-sonnet-4-6",
    max_tokens: 1000,          // 고정값. 변경 불가
    messages: [...]
  })
});
```

`max_tokens: 1000`이 하드 리밋이다. 타일 하나당 계기 8개 분량이 상한이므로, 응답이 잘리면 타일을 더 잘게 나눠야 한다.

**중요: `callClaude()`를 교체 가능하게 만들 것.**
로컬(Claude Code)에서는 인증이 없어 실제 호출이 전부 실패한다. 상단에 플래그를 두고, 로컬에서는 고정 JSON을 반환하는 스텁이 동작하게 하라.

```javascript
const USE_STUB = false;  // 로컬 테스트 시 true
```

---

## 3. 대전제 — 이것을 오해하면 전부 틀린다

이 P&ID는 **입찰 단계 도면이라 계기 버블 내부 태그가 비어 있다** (`.....`로 표시).
정답 파일의 TAG 컬럼(E열) 572행이 전부 공란인 이유가 이것이다.

따라서 이 툴은 **태그 추출기가 아니라 심볼 식별 + Description 생성기**다.
OCR로 읽을 글자가 없으므로 Tesseract 계열은 쓰지 않는다.

역할 분담을 엄격히 지켜라. 이 분리가 정확도를 결정한다.

| Claude Vision이 하는 일 | 결정론적 JS가 하는 일 |
|---|---|
| 심볼 종류 판별 (§7) | TYPE → 사양 매핑 (§8) |
| From/To 주석 읽기 | 중복 병합, 정렬 |
| Description 생성 (§7.4) | Excel 생성 |
| NOTES 텍스트 추출 | Q'ty 계산 (§7.5) |

---

## 4. 처리 파이프라인

### Pass 1 — 도면 메타 (페이지당 1회)

150DPI 전체 페이지 이미지 1장 전송. 추출 항목:

- Drawing No. (예: `D00P-10LBA10-M05-0001`) → Excel G열
- Drawing Title에서 System 명 → Excel F열
- NOTES / GENERAL NOTES 전문 → Q'ty 판정 및 AO열
- `SCT SUPPLIER` 점선 박스의 대략적 위치 → Vendor scope 판정용

### Pass 2 — 계기 판독 (타일 단위)

- 300DPI 렌더 → **3×3 타일, 10% 오버랩**
  - **[2026-08-16 보정]** 기본을 **4×4** 로 올렸다. 3×3 은 타일 하나에 계기가 최대
    13개까지 들어와 `max_tokens: 1000`(계기 8개분)에 응답이 잘린다. 4×4 면 타일당
    최대 8개로 떨어지고 상한 초과 타일이 0이 된다. 도면당 호출은 10회 → 17회.
  - **[2026-08-16 보정]** "300DPI" 는 달성 불가이자 기준도 아니다. 모델이 이미지를
    장변 1568px 로 줄여 보므로 실효 해상도는 분할 수가 정한다 (3×3 128 / 4×4 170 /
    5×4 213 DPI). 또 A1 전체를 300DPI 로 그리면 280MB 라 캔버스가 못 버틴다.
    전체를 그린 뒤 자르지 말고 **타일 영역을 직접 렌더**할 것.
- 타일 순서는 좌상 → 우하 (행 우선). 이 순서가 곧 출력 정렬 순서다
- 타일당 1회 호출. 응답 스키마:

```json
[{
  "type": "PIT",
  "x": 0.42, "y": 0.18,
  "line_context": "FROM HRSG#11 / TO HP BYPASS#11",
  "equipment": "HP STEAM MAIN",
  "position": "DOWNSTREAM",
  "redundancy": "A",
  "vendor_scope": false,
  "note_ref": "1"
}]
```

`x`, `y`는 **타일 내부 상대 좌표(0~1)**. JS가 페이지 절대 좌표로 환산한다.

### 후처리 (JS)

1. 오버랩 중복 제거 — 페이지 절대 좌표 ±2% 이내 + 동일 TYPE이면 동일 계기
   - **[2026-08-16 보정]** 이 규칙만으로는 틀린다. 이중화 계기는 같은 배관에 세로로
     나란히 붙고 실측 간격이 페이지의 **1.7%**밖에 안 되어, ±2%로 훑으면 서로 다른
     두 계기를 하나로 합친다 (HP Steam 도면에서 드레인 온도계 8개 → 4개). 세 가지를 건다.
     1. **같은 타일 안에서는 합치지 않는다.** 한 응답에 따로 적혔으면 따로다.
     2. 반경 안에서 아무거나 잡지 말고 **가장 가까운 것**만 짝으로 본다.
     3. 반경은 **±1%**. 같은 지점을 두 타일에서 본 좌표 오차보다는 크고, 세로로 붙은
        서로 다른 계기의 간격(1.7%)보다는 작아야 한다.
2. 정렬 — y 우선, 같은 행(±3%)이면 x 순
   - **[2026-08-16 확인]** 정답 파일은 UNIT 번호순(#11 → #12 → #10)이라 이 순서와
     다르다. 내용은 같고 순서만 다르므로 대조는 다중집합으로 한다.
3. TYPE 룩업 적용 (§8)
4. Q'ty 적용 (§7.5)
5. 행 번호 부여

### 동시성

동시 호출 **최대 2개**. 실패 시 지수 백오프로 3회 재시도.
최종 실패한 타일은 UI에 목록으로 남기고 나머지 처리는 계속한다.

---

## 5. Excel 출력

**라이브러리: ExcelJS 사용** (cdnjs). SheetJS 커뮤니티 버전은 폰트·서식 지정이 안 되므로 쓰지 말 것.

- 시트명: `2.0_Instrument List`
- 헤더 6행, 데이터 8행부터 (정답 파일과 동일)
- 폰트: Arial

### 5.1 자동 채움 — Vision 결과

| 열 | 항목 | 값 |
|---|---|---|
| A | NO | 1부터 순번 |
| F | SYSTEM | Pass 1 |
| G | P&ID No. | Pass 1 |
| H | TYPE | Pass 2 |
| I | Q'ty | §7.5 |
| J | DESCRIPTION | §7.4 |
| W | Fluid | 계통명에서 추론 (STEAM / WATER / FUEL GAS / FUEL OIL / AIR / SEA WATER) |
| AO | REMARK | Vendor scope 표기, 관련 NOTE 번호 |

### 5.2 자동 채움 — 룩업 테이블

X ~ AI열. §8의 테이블을 그대로 적용.

### 5.3 반드시 공란으로 둘 것

| 열 | 이유 |
|---|---|
| B, C, D, E (TAG) | 입찰 단계라 태그 미부여. **절대 생성하지 말 것** |
| K, L ~ V | Heat Balance / Line List 소관. 이 툴 범위 밖 |
| AC (Calibration Range) | 프로세스 조건에 따라 달라짐. §8 주석 참조 |
| AJ, AK, AL, AM, AN | 견적 단계 입력 |

### 5.4 말미

마지막에 SPARE 행 블록 추가: PIT 2행, PDIT 1행, TI 1행, TIT 2행 (J열에 `SPARE`)

---

## 6. 영구 저장소 `window.storage`

키당 5MB. 키 이름에 공백·슬래시·따옴표 불가. **전 호출을 try-catch로 감쌀 것** (없는 키를 읽으면 null이 아니라 throw).

### 개인 저장소 (`shared: false`)

| 키 | 용도 |
|---|---|
| `job:current` | 파일명, 선택 페이지, 진행 위치 |
| `result:{도면번호}` | 도면별 계기 JSON |

페이지 1장 완료 시마다 기록. 탭을 닫아도 "이어서 처리" 가능해야 한다.
관련 데이터는 한 키에 묶어 저장하라. 호출이 잦으면 rate limit에 걸린다.

### 공유 저장소 (`shared: true`)

| 키 | 용도 |
|---|---|
| `rules:overrides` | 사용자 수정 이력에서 도출한 판독 보정 규칙 |

사용자가 결과 테이블에서 TYPE을 바꾸거나 행을 삭제하면 그 패턴을 누적하고, 다음 판독 시 프롬프트에 주입한다.

**공유 저장소는 모든 사용자에게 보인다는 사실을 UI에 명시할 것.**
"내 데이터 초기화" 버튼 필수.

---

## 7. 판독 규칙 — Pass 2 시스템 프롬프트에 삽입

### 7.1 추출 대상 (12종 화이트리스트)

```
PIT  PI  TIT  TI  PDIT  FIT  FE  LIT  LI  LS  FS  RO
```

### 7.2 제외 대상

- 컨트롤밸브: `FCV` `TCV` `PCV` `LCV`
- 밸브·구동기: `XV` `MOV` `NRV` `HV` `PSV` `BPRV` `PRV`
- 밸브 부속 신호: `ZS` `ZSO` `ZSC` `ZT` `ZI` `HS` `YS` `YSO` `YSR` `YSA`
- 분석기: `AT` `AIT` `QMS`
- 제어 심볼: `I/P` `SCT` 표기, 로직 박스
- 도면 간 참조 화살표 블록 (`D00P-…-M05-000n`) — 계기가 아님

### 7.3 Vendor Scope

`SCT SUPPLIER` 점선 박스 내부, 또는 `SUPPLIED BY ○○ VENDOR` / `PROVIDED BY ○○ VENDOR` 주석이 적용되는 범위의 계기.

**정답 파일은 vendor scope를 완전히 제외했다.**
기본 동작은 "포함 + AO열에 `VENDOR SCOPE` 표기"로 구현하되, UI 체크박스로 제외 전환이 가능하게 하라.

### 7.4 Description 문법

전부 대문자.

```
UNIT #[nn] + [계통·설비명] + [위치] + [측정변수] + [접미사]
```

| 요소 | 허용값 |
|---|---|
| UNIT | `#11` `#12` `#10` `#20` `#00`(플랜트 공통) |
| 위치 | SUPPLY / RETURN / INLET / OUTLET / UPSTREAM / DOWNSTREAM / DISCHARGE / SUCTION / BODY DRAIN / **DRAIN** |
| 측정변수 | PRESSURE / TEMPERATURE / FLOW / LEVEL / DIFFERENTIAL PRESSURE / FLOW ELEMENT |
| 접미사 | 이중화 `A` `B` `C` / 물리적 복수 `1` `2` `3` `4` |
| LS 전용 | `LEVEL HIGH` / `LEVEL HIGH HIGH` |

설비명과 위치는 **라인의 From/To 주석 및 인접 장비 라벨**에서 도출한다.

**[2026-08-16 추가] SYSTEM(F열)은 도면 제목을 그대로 쓰지 않는다.** 제목은 전부
대문자(`P&ID FOR HP STEAM SYSTEM GROUP 10`)이지만 정답의 SYSTEM은 `HP Steam System`
이다. 머리글자만 대문자로 바꾸되 계통 약어(HP IP LP CRH HRH CCW HRSG GT ST STG BFP
CEP DCS AUX BOP)는 대문자로 남긴다.

**[2026-08-16 추가] DESCRIPTION 문장은 JS가 조립한다.** Vision은 부품(equipment,
position, redundancy, line_context)만 돌려주고, `UNIT + 설비 + 위치 + 측정변수 + 접미사`
결합과 측정변수 매핑(TYPE → PRESSURE/TEMPERATURE/…)은 결정론적 코드가 한다.
같은 부품에서 매번 같은 문장이 나와야 회귀 테스트가 성립한다.

검증용 실제 정답 예시:

```
UNIT #11 HP STEAM PRESSURE A
UNIT #11 HP STEAM BYPASS VALVE DOWNSTREAM TEMPERATURE C
UNIT #10 CRH STEAM TO CLEAN DRAIN TANK LEVEL HIGH HIGH
UNIT #12 BFP A/B MOTOR COOLER CCW RETURN TEMPERATURE
UNIT #11 GENERATOR HYDROGEN GAS COOLER CCW SUPPLY PRESSURE 3
UNIT #10 AUX STEAM LETDOWN VALVE SPRAY WATER FLOW ELEMENT
```

### 7.5 Q'ty — NOTES에서 자동 도출

| NOTES 문구 | Q'ty |
|---|---|
| `IDENTICAL FOR GROUP#20` | 2 |
| `IDENTICAL FOR UNIT#12,21,22` | 4 |
| 해당 문구 없음 (플랜트 공통 계통) | 1 |

### 7.6 기타

- `FE`와 `FIT`는 **별도 행**으로 분리한다 (오리피스 + 전송기)
- `PI`/`TI`(로컬 게이지, 원형 단일선)와 `PIT`/`TIT`(전송기)를 심볼로 구분한다
- 동일 계기가 두 도면에 걸치면 한 번만 계상한다. 실제로 그려진 도면이 소유 도면이다

---

## 8. TYPE 룩업 테이블

정답 파일 572행에서 추출한 최빈값. 그대로 코드에 넣어라.

```javascript
const TYPE_SPEC = {
  PIT:  { X:'PIT-1',  Y:'Pressure',       Z:'Diaphragm',      AA:'Remote',      AB:'4~20mA', AD:'bar(g)', AE:'316SS',  AF:'1/2" NPT',  AG:'-', AH:'-',
          AI:'2-WAY MANIFOLD, MOUNTING BRACKET' },
  PI:   { X:'PI-1',   Y:'Pressure',       Z:'Bourdon',        AA:'Direct',      AB:'-',      AD:'bar(g)', AE:'316SS',  AF:'1/2" NPT',  AG:'-', AH:'-',
          AI:'DIAL SIZE: 100mm, 2-WAY MANIFOLD, OIL FILLED,' },
  PDIT: { X:'PDIT-1', Y:'Diff. Pressure', Z:'Diaphragm',      AA:'Remote',      AB:'4~20mA', AD:'bar',    AE:'316SS',  AF:'1/2" NPT',  AG:'-', AH:'-',
          AI:'5-WAY MANIFOLD, MOUNTING BRACKET' },
  TIT:  { X:'TIT-3',  Y:'Temp.',          Z:'Thermocouple-K', AA:'Head-Mount',  AB:'4~20mA', AD:'℃',      AE:'T/C-K ', AF:'24Ф WI',    AG:'U:120/T:50/Ext.N:200 mm', AH:'-',
          AI:'T/C K TYPE, DUPLEX ELEMENT, W/ ELEMENT & THERMOWELL' },
  TI:   { X:'TI-1',   Y:'Temp.',          Z:'Bi-metal',       AA:'Direct',      AB:'-',      AD:'℃',      AE:'316SS',  AF:'24Ф WI',    AG:'U:60/T:50/Ext.N:200 mm\n316LSS', AH:'-',
          AI:'DIAL SIZE: 100mm, W/ THERMOWELL' },
  FIT:  { X:'FIT-1',  Y:'Diff. Pressure', Z:'Diaphragm',      AA:'Remote',      AB:'4~20mA', AD:'T/h',    AE:'316SS',  AF:'1/2" NPT',  AG:'-', AH:'-',
          AI:'5-WAY MANIFOLD, MOUNTING BRACKET' },
  FE:   { X:'FE-1',   Y:'-',              Z:'Orifice',        AA:'-',           AB:'-',      AD:'T/h',    AE:'316LSS', AF:'',          AG:'-', AH:'-',
          AI:'Flange with Bolt/Nut/Gasket Set' },
  RO:   { X:'RO-1',   Y:'-',              Z:'Orifice',        AA:'-',           AB:'-',      AD:'-',      AE:'316SS',  AF:'',          AG:'-', AH:'-',
          AI:'None' },
  LIT:  { X:'LT-6',   Y:'Diff. Pressure', Z:'Diaphragm',      AA:'Direct',      AB:'4~20mA', AD:'mm',     AE:'316LSS', AF:'2" RF',     AG:'-', AH:'-',
          AI:'2" RF FLANGE : 316LSS' },
  LI:   { X:'LI-4',   Y:'-',              Z:'Float',          AA:'-',           AB:'-',      AD:'mm',     AE:'316LSS', AF:'2" RF',     AG:'-', AH:'-',
          AI:'LOCAL DIAL INDICATOR, W/ GUIDE  PIPE, MOUNTING BRACKET' },
  LS:   { X:'LS-2',   Y:'-',              Z:'Displacer',      AA:'-',           AB:'Contact',AD:'-',      AE:'316SS',  AF:'1" SW',     AG:'Chamber:316SS', AH:'-',
          AI:'2-SPDT OR 1-DPDT, CHAMBER W/ DRAIN VALVE, C-C LENGTH : 300MM' },
  FS:   { X:'FS-1',   Y:'Pressure',       Z:'-',              AA:'Direct',      AB:'Contact',AD:'-',      AE:'316SS',  AF:'1/2" NPT',  AG:'-', AH:'Ex.d',
          AI:'1-DPDT (OR 2-SPDT)' }
};
```

### 8.1 변종 — 자동 판정하지 말 것

같은 TYPE이라도 서비스 조건에 따라 다른 사양을 쓴다. 이건 프로세스 조건을 알아야 결정되므로 **자동 채움 대상이 아니다.**

| TYPE | 기본값 | 변종 | 적용 조건 |
|---|---|---|---|
| PIT | PIT-1 (Diaphragm) | PIT-2 (Remote Diaphragm Seal, Gold Plated Monel) | 해수·부식성·슬러리 |
| TIT | TIT-3 (T/C-K) | TIT-5 (RTD PT100) | 저온 (~60℃급) |
| TI | TI-1 (24Ф WI) | TI-2 (2" FF) | 플랜지 접속 |
| PI | PI-1 (Bourdon) | PI-6 (Diaphragm Seal) | 해수·부식성 |
| PDIT | PDIT-1 | PDIT-2 / PDIT-3 (Capillary) | 해수, 방폭 Ex.d |

**처리 방식:** 기본값으로 채우고, 해당 행 AO열에 `VARIANT CHECK` 를 표기하여 사용자가 검토하게 한다. UI 결과 테이블에서 X열을 드롭다운으로 변경 가능하게 만들 것.

### 8.2 AC (Calibration Range)

프로세스 조건에서 나오므로 **공란으로 둔다.** FE/RO의 AF(구경)도 라인 사이즈에 종속되므로 공란.

---

## 9. UI 요구사항

1. PDF 드롭존 → 페이지 썸네일 그리드 → **처리할 페이지 다중 선택** (전체 41장 강제 금지)
2. 진행 표시: `페이지 3/41 · 타일 5/9` + 누적 계기 수
3. 결과 테이블 인라인 표시 (F·G·H·I·J·AO열) — 다운로드 전 육안 검증용
4. 행 단위 삭제, DESCRIPTION 인라인 수정, TYPE·X열 드롭다운 변경
5. 버튼: `Excel 다운로드` / `이어서 처리` / `내 데이터 초기화`
6. 실패 타일 목록 + 재시도 버튼
7. 사용량 경고: "도면 1장당 약 10회 호출. 5~10장씩 나눠 처리하는 것을 권장" 안내 문구

---

## 10. 작업 순서 — 이 순서를 지킬 것

### Phase 1. 렌더링만

PDF 드롭 → 300DPI 렌더 → 3×3 타일 분할 → **화면에 타일 미리보기.**
Claude 호출은 붙이지 않는다.

> **완료 기준:** `ref/PID_Total.pdf`의 HP Steam 도면에서 계기 버블 내부가 육안으로 구분 가능한가. 흐리면 DPI나 분할 수를 먼저 조정한다. 여기서 실패하면 이후 전부 실패한다.

### Phase 2. 단일 도면 판독

`D00P-10LBA10-M05-0001` (HP Steam) 1장만 Pass 1 + Pass 2 연결.

> **완료 기준:** `ref/example_instrument_list.xlsx` 8~19행이 정답이다. PIT 2개 + TIT 10개, 총 12행.
> 재현율과 오탐을 `dev/notes.md`에 기록하고, 누락 원인을 §7 규칙에 반영한다.

### Phase 3. Excel 출력

ExcelJS로 §5 포맷 생성 + 다운로드.

> **완료 기준:** 생성 파일을 정답 파일과 열 단위로 대조. 공란이어야 할 열(B~E, K~V)에 값이 들어가지 않았는지 확인.

### Phase 4. 저장소 연결

`window.storage` 기반 중단 복구 + 규칙 축적.

### Phase 5. 확장

나머지 도면으로 확대. 오류 발견 시 §7에 규칙을 추가하고 **해당 도면만 재실행**한다.

---

## 11. 규칙 학습 원칙

모델이 학습하는 게 아니다. 규칙은 이 문서(§7)와 프롬프트 문자열로만 존재한다.

판독 오류를 발견하면:

1. `dev/notes.md`에 증상과 원인을 기록
2. §7에 규칙 문장을 **추가** (기존 문장을 지우지 말 것 — 회귀 원인 추적 불가해짐)
3. `index.html`의 프롬프트에 반영
4. Phase 2의 HP Steam 도면으로 **회귀 테스트** 후 확장

이 문서가 원본이다. Artifact에서 직접 수정하지 말고 반드시 여기서 고쳐 반영하라.

---

## 12. 미결정 사항 — 사용자에게 확인 필요

1. **Vendor scope** — 제외(정답 파일 방식) vs 포함 후 AO 표기. 기본값은 후자로 구현
2. **PI/TI 로컬 게이지 범위** — 정답 파일은 CCW 계통에서 쿨러별 supply/return을 전부 개별 행으로 잡아 170행이 나왔다. 이 수준까지 자동 생성할지
