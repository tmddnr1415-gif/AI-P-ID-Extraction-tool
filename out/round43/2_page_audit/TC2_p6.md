# TC2 p6 — D02J-31LBA10-M05-0001 (HP STEAM) · 39회차

캡처 `캡처/TC2_p6_원본.png` · `캡처/TC2_p6_오버레이.png` · `캡처/crop_tc2_p6_fit_stack.png`

## ① 눈으로 센 것
계기 버블 TIT 8 · TW 4 · PIT 4 · FIT 2 · FE 1 = **19** (그중 TIT 2 는 Typical `D` 상세 안).
밸브 MOV 3 (M 원) · 수동 밸브 다수(범위 밖) · PSV 0.

## ② 대조 (행 15)
| 판정 | 건수 | 내용 |
| --- | --- | --- |
| ㉠ 정상 | 16 | TIT 6·TW 4·PIT 4 (Typical D ×4 → q=32 두 행 포함 · 38회차) · FE 자리에 행 1 |
| ㉡ 있는데 행 없음 | 2 + 3 | **FIT 2** (FIT/FIT/FE 맞닿은 세 버블이 LS 한 행으로 접혔다) · MOV 3 (38회차 [E] `act_box` 절대 pt — 누적) |
| ㉢ 없는데 행 있음 | 0 | |
| ㉣ 값 틀림 | 1 | 접힌 행의 TYPE 이 `LS` (config `merged_type`) — 도면은 F 변수 |

## ③ 원인
`pipeline._signal_groups` 의 묶음 조건이 *변수 글자가 같고 · 맞닿고 · 겹친다* 뿐이었다.  사용자 확정(5회차)은
**레벨 스위치 하나가 여러 설정점을 보고한다** 는 것인데 규칙은 "같은 변수" 만 적었다.  FIT·FIT·FE 는 크롭에서
보듯 **탭이 셋** 이고 FIT 두 개가 각각 신호선을 가진다 — 기기 셋이다.  단계: 검출 뒤 `_signal_groups` (묶음).  §4 유형: 외워둔 값(AL NOUF1 의 묶음이 전부 LS 라서 조건이 거기까지만 갔다).

## ④ 전수 (결과 json 의 `signal_groups`)
| 프로젝트 | 묶음 | 스위치 아닌 구성원 포함 |
| --- | --- | --- |
| AL NOUF1 | LSHH+LSH+LSL 만 | **0** |
| SADARA | 0 | 0 |
| TC2 | LSHH+LSH+LSL 8 · FIT+FIT+FE 6 · FIT+FIT+FIT+FE 1 | **7** (p6 · p9 · p10 ×2 · p11 · p17 · p18 · 접힌 행 15) |
| UAD | 0 | 0 |
→ 여러 건 · 방법론.

## ⑤ 고침
접는 조건에 **그 문서의 ISA 표가 기능 글자를 `SWITCH` 로 읽을 것** 을 더했다 (`pipeline._is_switch`).  글자 뜻은 코드에 적지
않고 `isa.succeeding` 에서 읽는다 — AL NOUF1·TC2·SADARA 표 전부 `S: SWITCH`, UAD 표는 `S` 가 없다(묶음도 0).
표가 없거나 그 글자를 안 찍으면 접지 않는다.  시험 `tests/test_signal_bundle.py` 5건.  예상: TC2 +15행, AL NOUF1 불변.
`merged_type: LS` 는 그대로 — 지금 접히는 묶음이 전부 L 변수라 근거가 없다(P 스위치 묶음이 오면 그때).
