# Symbol & Legend

> 이 문서는 판독 프롬프트에 통째로 들어간다. 도구 사용법이 아니라 **모델이 읽을 판독 기준**만 적는다.
> 프로젝트의 Symbol & Legend 도면에서 자동 생성할 수 있다 (README의 `parse_legend.py` 참조).

**현재 상태: 이 프로젝트의 Symbol & Legend 도면(`D00P-00GEN00-M05-0002`~`-0005`)에서
추출된 기호 정의표가 아직 없다.** 아래 일반 기준으로 판독하되, 도면에서 아래에 없는 기호를
만나면 추측하지 말고 `review_findings`에 그 기호와 위치를 적는다.

## 계기 버블 테두리 → 설치 위치

| 버블 | 의미 |
|---|---|
| 가로선 없는 원 | Field mounted (현장 설치) |
| 가로 실선 1개가 지나는 원 | 주 제어실 패널 / DCS |
| 가로 점선 1개가 지나는 원 | Behind panel (패널 뒤) |
| 이중선 원 | 보조 위치 / 공유 표시 |
| 사각형 안의 원, 육각형 | 컴퓨터 기능 / 공유 표시 제어 |

`Mounting Type` 컬럼은 이 버블 모양이 아니라 **INST. TYPICAL TYPE 표에서 결정**된다
(`Direct`, `Remote`, `Head-Mount`, `Remote Capillary`). 버블 모양은 TYPICAL TYPE을 고를 때의 참고다.

## 신호선

| 선 | 의미 |
|---|---|
| 실선 | 배관 / 기계 연결 |
| 가는 실선 | 전기 배선 |
| 빗금이 그어진 선 | 공압 신호 |
| 점선 | 전기 신호 |
| 원이 이어진 선 | 소프트웨어 / 데이터 링크 |
| `X` 표시가 반복되는 선 | 캐필러리 (원격 다이어프램 실) |

캐필러리가 보이면 TYPICAL TYPE은 `Remote Diaphragm Seal` 계열(`-2`/`-3`)이다.

## 밸브 상태 기호

| 기호 | 의미 |
|---|---|
| `FO` | Fail Open |
| `FC` | Fail Closed |
| `FL` | Fail Last (현 위치 유지) |
| `LO` / `LC` | Locked Open / Locked Closed |

밸브 자체는 이번 판독 범위가 아니다. 밸브에 딸린 리밋스위치(`ZS`)도 제외한다.

## 이 프로젝트에서 실제로 쓰이는 계기 문자

정답 Instrument List 563행에서 확인된 조합이다. 여기 없는 조합을 발견하면
`review_findings`로 보고한다.

| TYPE | 해석 |
|---|---|
| `PI` / `TI` / `LI` | 압력 / 온도 / 레벨 **지시계** (현장 게이지) |
| `PIT` / `TIT` / `LIT` / `FIT` | 지시 + **전송기** |
| `PDIT` | 차압 지시 전송기 |
| `LS` / `FS` | 레벨 / 유량 **스위치** (접점 출력) |
| `FE` | 유량 요소 (오리피스 등). 전송기 `FIT`와 별도 행 |
| `RO` | 제한 오리피스 (Restriction Orifice) |

도면에는 전송기가 `PT`/`TT`/`LT`/`FT`로 그려지지만 Instrument List의 TYPE은
`PIT`/`TIT`/`LIT`/`FIT`로 쓴다 (`extraction_guide.md` 4절).

## 태그 번호

이 프로젝트의 제안 단계 도면은 계기 버블의 태그 번호 자리가 점선(`.....`)으로 비어 있다.
**태그 번호를 만들어내지 않는다.** 자세한 내용은 `naming_convention.md`.
