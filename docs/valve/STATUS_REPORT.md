# Ball Valve Datasheet 검토 도구 — 현황 보고 (2026-11-01 · valve28 기준)

> 읽는 사람: 계장 엔지니어. "무엇이 되나 · 얼마나 믿을 수 있나 · 무엇이 아직 안 되나 · 무엇을 고쳤나"만 적습니다.
> 세부 설계는 `DESIGN.md`(§1~§33), 쓰는 법은 `USER_GUIDE.md`, 개발 인수인계는 `docs/handoff/valve.md`.

---

## 1. 한 줄 요약

Vendor 가 낸 Ball Valve Datasheet PDF(수백 장)를 넣으면 **Tag 별로 읽고, PMS · Process Data · 이전 Revision · 같은 프로젝트의 다른 데이터시트와 맞대어
오류 · 누락 · 사양 위반 · 변경을 찾고, 지적마다 근거(맞대어 본 쪽과 값)를 붙여** Issue List Excel · Mark-up PDF · Valve List Excel 로 내보냅니다.
판정 · 승인은 엔지니어가 합니다. OCR · AI(LLM) 추정은 쓰지 않습니다 — 규칙으로만 판단하고, 모르면 "판단 못 함 + 이유"로 남깁니다.

---

## 2. 만들어진 것

### 2.1 읽기 (추출)

| 항목 | 내용 |
|---|---|
| 입력 | Datasheet PDF(개별 · 병합 모두), Valve List(TBE .xlsx/.xls), Process Data PDF, PMS PDF |
| 방식 | PDF 글자층 + 표 괘선만으로 칸을 찾음 (OCR 없음). Tag 번호로 데이터시트를 나누고 같은 Tag 의 Revision 을 묶음 |
| 견고성 | A3 · 90° 회전 · 2장짜리 · 암호/손상 파일 · 칸 번호 누락 · 글자 크기/괘선 변화 (`valve_sim_pdf.py` 합성 190종 0.992) |
| 실자료 결과 | Datasheet.pdf 456쪽 → 164 데이터시트(On/Off 140 · MOV 24) · 17,471칸 · 456쪽 눈 대조 오류율 3.54 % → **0.009 %** (남은 2건은 도면 오타 → Data Error 로 지적) · TBE 와 Tag 164/164 일치, 값 일치 92.9 % |

### 2.2 검증 엔진 (핵심)

| 묶음 | 규칙 | 무엇을 보나 |
|---|---|---|
| Datasheet 자체 | DM-01·02, OI-01·02, DE-01~09 | 빈칸 · HOLD/TBC · Line No.↔Piping class/size · 운전≤설계 · Fail 위치↔공기 차단 시 동작 · 시트마다 문서번호/머리줄 · 없는 Note 참조 · 엉뚱한 Note 참조 |
| PMS | PMS-항목 | Class 머리(Rating · NACE · Trim · Body) + Ball Valve 품목(재질 · 시트 · Fire-safe · bore) |
| Process Data | PD-항목 | 유체 · 상 · 운전/설계 압력·온도 · 차압 · 유량 · 작동 시간 · Fail 위치 · 기밀 · Line/P&ID (허용오차 1 %, 게이지/절대 기준 불명확하면 Review) |
| 재질 (MR) | 12종 | 시트 vs PMS 온도 한계 · 시트 사용 온도 · P/T 가 class 표 안인지 · 저온 CS · 체/배관 재질 계열 · 사워 서비스 316/볼트/CS · 경화 육성 · 이중인증 316/316L · 유체 vs class 서비스 목록 |
| 설계 (VR) | 14종 | 플랜지 면/규격 · Floating 크기 한계 · Ball 형식 · Fail-safe vs 스프링 · SIL · 누설 등급 · Fire-safe · 캐비티 릴리프 · 연장 스템 · 피깅 · 크기 vs 배관 · 침식 · 액추에이터 여유 |
| 동료 비교 (PC) | PC-01 | 같은 Piping class 데이터시트 다수와 다른 값 |
| Tag (TG) | 5종 | Area/Unit 별로 프로젝트 Tag 에서 배운 번호 규칙 · 중복 Tag · 기능 코드 vs Fail 동작 |
| Revision | REV-01 + 이어받기 | 이전 판 대비 바뀐 칸, 새 판이 오면 이전 검토 결정을 이어받음 (아래 2.4) |

- **지적마다 근거** (valve28): 맞대어 본 문서 · 쪽 · 값(`evidence`), 판정 근거(`basis`), 규칙 번호(`check`).
- **검증 보고** (valve28): Tag 마다 48 항목을 ✓ 통과 / ✗ 지적 / – 판단 못 함(이유) 로 기록. – 는 통과로 치지 않음.
- 공정 값 의견은 출처를 밝힘: *Based on Ref. Process Data CO2S-SSG-IN-REQ-00009 (p.54) design temp. 260 °C …* / *Based on Datasheet …* (valve25).
- 설계사 코멘트는 한 줄(≤160자) · "… shall be reviewed." 말투 (valve12 · valve26). 긴 설명은 Expert 탭.

### 2.3 화면

Dashboard · Document Management · Valve List(Excel 같은 표 ↔ PDF 미리보기) · Datasheet Review 작업대(PDF + Issues · **Checks** · Summary · Data · Process · PMS · Expert · Rev · Notes · Comments · History 탭) ·
Revision Comparison · Process Data Verification · PMS Compliance · Reports & Export · Settings(Tag 규칙 · Ball Valve 지식 28항목 · 진단).
PDF 주석 도구 19종(스탬프 · 메모 · 타자기 · 글상자 · 말풍선 · 형광펜 · 취소선 · 밑줄 · 물결 · 화살표 · 선 · 사각형 · 원 · 꺾은선 · 다각형 · 구름 · 펜 · 지우개 · 선택).

### 2.4 Rev B · C · D 자동 처리 (valve27)

새 판을 올리면 규칙 검토는 자동. 그 위에:
- 이전 판에서 **Dismissed** 한 지적이 같은 칸 · 같은 값으로 다시 나오면 → Dismissed 유지
- **Confirmed**(설계사에게 보낸) 지적이 그대로면 → **"Not addressed since Rev A"** (Major)
- 사라진 지적 = 해결 · 처음 나온 지적 = 새 것 → 머리 칩 `Rev A→B ✓해결 ✗미반영 +새로`
- 칸에 단 글 의견은 그 칸이 안 바뀌었으면 새 판으로 복사

### 2.5 내보내기

| 파일 | 내용 |
|---|---|
| Issue List Excel | No. · Area · Site · Unit · Tag … Description · Required · **Evidence · Basis** · Severity · Status · 도구로 여는 링크 / Summary · Summary by Area · **Verification**(Tag × 48) · Summary by Tag. 만들 때 Issue Type 선택 |
| Mark-up PDF | 지적 상자 + 번호 · 검토자 마크업 · **쪽 옆 번호별 코멘트(근거 포함)** · Tag 별 Issue Summary · 표지 · 책갈피. 기본은 마크업 고정(어느 뷰어에서도 그대로), 끄면 Acrobat 편집 가능 주석 |
| Valve List Excel | 회사 TBE 양식 그대로(바뀐 칸 노랑 + 'Previous:' 메모 · Vendor 행 삭제) + Summary · Summary by Area · All Valves(PFP · Fugitive · Fire safe · NACE · SIL … 열) |
| CSV | 추출 칸 전체 · 감사 기록 · Revision 비교 |

### 2.6 속도 (실측)

| 항목 | 값 |
|---|---|
| 456쪽 읽기 | 약 13 s (28 ms/쪽) |
| 서버 응답 (164 DS, 데워진 뒤) | 화면별 ≤ 63 ms, Summary 0.14 s |
| Tag 넘기기 (990 DS 사본) | **4~19 ms** (전 74~277 ms) |
| 전체 Mark-up PDF (551쪽) | 약 21 s · 4.9 MB |

### 2.7 품질 장치

| 장치 | 결과 (valve28) |
|---|---|
| 실자료 기준값 `valve_eval.py --check` | 불변 (지문 541753c612ed) |
| 추출 차등 비교 `valve_diff_sim.py` | 140 DS · 12,470칸 불일치 0 |
| 규칙 시뮬레이션 `valve_sim.py --n 3000` | recall / precision 1.000 · 퍼즈 500 예외 0 |
| 실자료 변이 재생 `valve_mutate.py` | 164 × 14 전부 100 % |
| 합성 PDF 추출 `valve_sim_pdf.py` | 190종 0.992 |
| Revision 사슬 `valve_rev_sim.py` | 1,500건 × 3판 = 55,223 점검 1.000 |
| 화면 자기점검 `valve_ui_audit.cjs` | 25/25 |
| 전체 시험 | 1,888 통과 |

꾸러미: `out/PID_dev+ops_valveNN_<날짜>.zip` — valve01~28, 누적이라 **valve28 하나만 적용**하면 됩니다.

---

## 3. 실자료 검토 결과 (CO2 PJT, 164 Tag)

| Issue 종류 | 건수 | 메모 |
|---|---|---|
| Data Missing | 2,527 | 대부분 PROCESS DATA 빈칸(Process DS 참조) — 요청대로 전부 표기, 작업대에서 한 카드로 묶임 |
| Open Item (HOLD/TBC) | 84 | |
| Valve Review | 77 | |
| PMS Review | 68 | PMS 로 확인 못 함 |
| Process Mismatch | 42 | Line No. 32 · P&ID 8 · Fail 위치 2 |
| Material Review | 34 | |
| Data Error | 7 | |
| PMS Non-Compliance | 1 | |

검증 보고: 164 × 48 = 7,872 검사 → ✓ 6,806 · ✗ 426 · **– 640 (판단 못 함)**.

---

## 4. 아직 안 되는 것 · 한계 (정직하게)

### 4.1 판단 범위의 빈틈 — "– 판단 못 함" 640건의 내역

| 이유 | Tag 수 | 결과 |
|---|---|---|
| 설계 온도가 데이터시트에도 Process Data 에도 없음 | 294 (검사 기준) | 시트 온도 한계(MR-01·02) · P/T 표(MR-03) 가 돌지 않음 |
| 첫 판(이전 Revision 없음) | 163 | 정상 — 비교할 것이 없음 |
| Tag 이 Process Data 에 없음 | 98 | 공정 값 비교 불가. 올린 Process Data(MR Annexure 7)가 68 Tag 만 담고 있음 |
| Piping class 'API5L-X65' 가 PMS 에 없음 | 60 | PMS 기반 규칙 불가. 파이프라인 class 는 별도 PMS 문서일 가능성 — **해당 PMS 를 받아야 함** |
| Area/Unit 의 Tag 가 3개 미만 | 18 | Tag 번호 규칙을 배우지 못함 |
| class '1C0KL-A' 가 PMS 에 없음 | 4 | 표기 오타인지 확인 필요 |
| 같은 class 의 다른 데이터시트 없음 | 3 | 동료 비교 불가 |

### 4.2 아직 없는 검사

1. **PMS Gasket · Bolting 품목 대조** — 볼트는 데이터시트 Note 로 재질 검토(MR-11)만.
2. **Cv · 소음 · 차압 사이징 검토** — Process Data 의 유량으로 밸브 크기를 계산하지 않음.
3. 액추에이터 토크 계산 — 여유 계수(1.5 등) 표기만 확인.
4. 회사 Tag Numbering Procedure · Ball Valve 사양서 대조 — 문서를 받지 못해 **프로젝트 Tag 에서 배운 규칙**과 **일반 실무값**(Floating 크기 한계, 시트 온도 한계, PST 정책)을 씀. 회사 값이 다르면 규칙표를 맞춰야 함.

### 4.3 읽기의 한계

1. **스캔본(글자층 없는 쪽)은 읽지 못함** — 경고만 띄움. OCR 은 원칙상 쓰지 않음.
2. 검증된 양식은 CO2 PJT 의 On/Off (Form 80) · MOV (Form 102). 다른 Vendor 양식은 합성 시뮬레이션(0.992)으로만 확인 — **실제 다른 양식은 아직 시험하지 못함**.
3. TBE 값 일치 92.9 % — 나머지 7 % 는 표기 차이(재질 동치 처리 후)와 TBE 쪽 오기가 섞여 있음, 칸 단위 목록은 `valve_eval` 보고서 B 절(Agreement with TBE).

### 4.4 Revision 처리의 한계

1. 이어받기는 **칸 키(field key) 기준** — 새 판에서 칸 배치가 바뀌어 같은 항목이 다른 키로 읽히면 이전 결정을 못 이어받음(그 경우 Open 으로 다시 뜸 — 놓치지는 않음).
2. 자유 그림 마크업(구름 · 펜 등)은 옛 쪽 것이라 새 판에 복사하지 않음.
3. Revision 순서는 `A < B < … < 0 < 1 < 2` 규칙. 'R1', '0A' 같은 다른 체계는 시험하지 않음.

### 4.5 운영 · 확인 안 된 것

1. **valve01~28 모두 회사 적용 확인 전** — 실제 사용 피드백(Dismissed 비율, Review Feedback json)이 아직 없음. 규칙의 실무 정밀도는 사용 후 `valve_voc.py` 로 다시 측정해야 함.
2. Data Missing 2,527 건 — 요청대로 Process DS 참조 빈칸도 전부 지적. 설계사 전달본에서 양이 많으면 Issue Type 선택이나 일괄 Dismiss 로 줄여야 함.
3. 990 DS 규모에서 valve28 의 **첫 Summary 계산 시간은 아직 재지 않음** (164 DS 는 처음 4 s, 이후 0.14 s).
4. Mark-up PDF 기본값이 '마크업 고정' — 받은 쪽에서 주석을 편집할 수 없음(선택 창에서 끌 수 있음).
5. Process Data 문서번호: 데이터시트 Note 8 은 999-98-PR-DTS-00023 을 가리키지만 올린 파일은 CO2S-SSG-IN-REQ-00009(MR Annexure 7). 코멘트에는 **올린 파일의 번호**가 찍힘 — 정식 Process DS 를 받으면 다시 올릴 것.

---

## 5. 이번 회차들에서 찾아 고친 결함

| 회차 | 결함 | 증상 | 조치 |
|---|---|---|---|
| valve21 | Grid 캐시 + gzip | 목록이 가끔 안 뜸 (`ERR_CONTENT_LENGTH_MISMATCH`) | 캐시에 응답 객체 대신 바이트 저장, 매번 새 응답 |
| valve21 | PMS Fire Safe HOLD | HOLD 를 위반으로 판정 | Review 로 |
| valve21 | NACE 'NA' | 부적합으로 판정 | Review 로 |
| valve24 | 마크업 색 | 고른 색이 화면에 안 보이고 분류 색으로 그려짐 | 화면에 style 전달 |
| valve24 | 팔레트 | 그린 직후 다음 색을 고르면 방금 그린 것이 바뀜 | 그리기 중엔 다음 표시에만 |
| valve24 | 꺾은선 Enter | 편집 창까지 열림 | 키 이벤트 차단 |
| valve25 | PDF 코멘트 | 프로그램 코멘트가 번호 · 팝업으로만 있음, 브라우저 뷰어에서 안 보임 | 쪽 옆 여백에 인쇄 + 마크업 고정 |
| valve25 | 공정 값 출처 | 어느 문서의 값인지 없음 | "Based on Ref. Process Data <번호> (p.N) …" |
| valve25 | 리뷰 캐시 | 꾸러미를 올려도 옛 문구가 디스크 캐시에 남음 | 캐시 키에 버전 |
| valve27 | 큰 프로젝트 끊김 | Tag 넘길 때마다 984행 목록 다시 그림 (최대 277 ms) | 강조만 옮김 → 4~19 ms |
| valve27 | Revision 집계 | Dismissed 였던 지적을 '새 지적'으로 셈 | 수정 (시뮬레이션이 찾음) |
| valve27 | 작업대 머리 | 노트북 폭에서 값이 몇 픽셀로 눌림 | 좁은 폭에선 Tag + 칩만 |
| valve28 | 근거 없는 지적 | Excel · PDF 지적 행에 맞대어 본 쪽 근거 0 % | 모든 지적에 evidence · basis · check |

그 이전(valve01~20)의 주요 결함과 조치는 `DESIGN.md` §9~§24 와 `docs/history/other_log.md` 에 있습니다 (R-PTFE 토큰화, MR-03 두 점 P-T, 1A1A 거짓 PMS Review 16 → 0 등).

---

## 6. 다음에 할 일 (엔진 우선, 우선순위 순)

1. **회사 적용 후 사용 피드백 수집** → `valve_voc.py` 로 Dismissed 많은 규칙부터 조정 (실무 정밀도의 유일한 근거).
2. **누락 문서 확보**: API5L-X65 class PMS · 정식 Process DS(999-98-PR-DTS-00023) · Tag Numbering Procedure · 회사 Ball Valve 사양 → "판단 못 함" 을 줄이는 가장 빠른 길.
3. PMS Gasket · Bolting 품목 대조.
4. Process Data 유량 기반 Cv · 차압 검토.
5. Valve List(TBE) 열에 check 번호 연결 — 검토 결과 재사용.
6. 다른 Vendor 양식 실자료로 추출 검증.
7. 990 DS 규모에서 valve28 첫 계산 시간 측정 · 필요하면 검증 보고를 미리 계산(warm)에 포함.
