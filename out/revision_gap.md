# 도면 개정 ↔ Excel 불일치 목록

PDF 에 검토자 국문 주석 레이어가 있고, 그 내용이 Excel 에 반영되지 않았습니다.
**규칙으로 보정하지 않았습니다** — 발주처 확인용 목록입니다.

도면 본문에 주석이 있는 도면 **14건**.

| 페이지 | 도면번호 | 도면명 | 주석 | 검출 | Excel | 상태 |
|---|---|---|---|---|---|---|
| p10 | `D00P-10MAN10-M05-0001` | P&ID FOR BYPASS STEAM SYSTEM GRO | I/O 만<br>반영<br>..... I/O 만<br>반영<br>..... I/O 만<br>반영 | 32 | 32 | MATCHED |
| p11 | `D00P-10MAN10-M05-0002` | P&ID FOR BYPASS STEAM SYSTEM GRO | I/O 만<br>FC 반영<br>I/O 만<br>반영<br>I/O 만<br>반영 | 32 | 32 | MATCHED |
| p16 | `D00P-10LCA10-M05-0001` | P&ID FOR CONDENSATE SYSTEM GROUP | ..... RO 추가<br>D MAKE UP LCV RO 추가 | 28 | 31 | MATCHED |
| p17 | `D00P-10LCA10-M05-0002` | P&ID FOR CONDENSATE SYSTEM GROUP | 위치이동<br>DN80 VS 위치이동 VS | 10 | 10 | MATCHED |
| p26 | `D00P-00PAB10-M05-0001` | P&ID FOR SEAWATER INTAKE SYSTEM  | 삭제 | 8 | 5 | MATCHED |
| p27 | `D00P-00PAB10-M05-0002` | P&ID FOR SEAWATER INTAKE SYSTEM  | 삭제 | 8 | 5 | MATCHED |
| p31 | `D00P-10PCB10-M05-0001` | P&ID FOR AUX. COOLING WATER SYST | 위치이동 | 15 | 15 | MATCHED |
| p32 | `D00P-00EGD00-M05-0001` | P&ID FOR FUEL OIL SUPPLY SYSTEM  | 위치이동 (*)<br>위치이동 위치이동 (*)<br>위치이동 (*) | 16 | 10 | MATCHED |
| p35 | `D00P-10PGB10-M05-0001` | P&ID FOR CLOSED COOLING WATER SY | 추가 | 23 | 19 | MATCHED |
| p44 | `D00P-00SCB10-M05-0001` | P&ID FOR SERVICE AIR DISTRIBUTIO | PIT 삭제 | 0 | 1 | MATCHED |
| p46 | `D00P-00GHC10-M05-0001` | P&ID FOR DESAL. WATER SUPPLY SYS | Rev.B 삭제 -><br>Rev.C 복원 | 0 | 0 | PDF_ONLY |
| p49 | `D00P-00GHB10-M05-0001` | P&ID FOR SERVICE WATER DISTRIBUT | 삭제<br>RO FIT 1EA 삭제 GT #21 EVAP. COOLER . UNIT | 17 | 17 | MATCHED |
| p55 | `D00P-00GMA10-M05-0001` | P&ID FOR WASTE WATER TRANSFER SY | 추가 | 0 | 0 | PDF_ONLY |
| p56 | `D00P-00GQA10-M05-0001` | P&ID FOR SANITARY SEWER TRANSFER | 추가 | 0 | 0 | PDF_ONLY |

## 수치로 확인된 건

- **p49 `D00P-00GHB10-M05-0001`** — 주석 `PDIT 3EA, PIT 2EA 삭제`. Excel 은 `PDIT` 6 / `PIT` 4 인데 개정 도면과 검출은 모두 **3 / 2** 입니다. `RO FIT 1EA 삭제` 주석은 `FIT` 1행 결손과 대응합니다. 주석을 반영하면 이 도면 재현율은 11/11 이 됩니다.
- **p44 `D00P-00SCB10-M05-0001`** — 주석 `PIT 삭제`. Excel 의 유일한 1행은 `Instument air ring header PRESSURE` (SYSTEM `Compressed Air System`) 로 이 도면 소관이 아닙니다. 검출 0 이 맞습니다.
- **p16 `D00P-10LCA10-M05-0001`** — `RO 추가` 주석 2건. 도면에는 반영됐는데 Excel 반영 여부 확인이 필요합니다.

## 타이틀블록 `미접수` 표기

`Rev.C P&ID 미접수` 가 타이틀블록에 붙은 페이지: [12, 13, 14, 15, 18, 19, 20, 21, 22, 23, 32, 34, 36, 37, 38, 39, 40, 41, 45, 47, 50, 51]

최신 Rev 도면을 아직 수령하지 못했다는 표시입니다. Excel 이 최신 Rev 기준으로 작성됐다면, 이 페이지들의 결손은 검출기 문제가 아니라 도면 버전 차이입니다.
