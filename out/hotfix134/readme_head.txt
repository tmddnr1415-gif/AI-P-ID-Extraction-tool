PID 업데이트 hotfix134 (2026-11-10) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 · 132 · 133 어느 판이 있든, 적용하면 이 판(134)이 됩니다.
  회사 PC 에서 따로 고친 파일도 원본을 backup\hotfix134_<시각>\ 에 둔 뒤 새 판으로 덮습니다.
  적용 화면 끝의 [덮어씀 - 회사에서 고친 파일] 목록을 보고, 살려야 할 회사 수정이 있으면 backup 에서 다시 반영하세요.
- 회사 Claude Code 로 엔진을 고친 것이 있으면 적용하기 전에 '엔진 개선값' md 를 먼저 뽑아 보내 주세요.

무엇이 바뀌었나 (hotfix133 → 134)
Valve (Datasheet 자동 검토) — valve36 → valve37
- Globe Valve · Butterfly Valve · PSV 도 Ball Valve 와 같은 화면에서 검토합니다.
  대시보드 › 실행 프로젝트 › CO2 PJT › Datasheet › Globe Valve / Butterfly Valve / PSV 를 누르면
  P&ID 서버의 /valve/ 화면이 그 밸브 종류로 열립니다 (프로젝트 공간은 종류마다 따로).
- Datasheet PDF 여러 개(각 수십 장) + Process Data 를 끌어다 놓으면 Ball Valve 처럼 분석합니다.
- 새로 읽는 양식: Form 101 Control Valve(Globe · Butterfly CV) · Form 701 PSV · Code 80 하단 제목란 + Notes 쪽.
- Ball Valve 프로젝트는 valve36 과 같은 결과입니다 (시험으로 확인).
- 대시보드 메뉴 연결은 ① 대시보드 업데이트(v17.33 이상)에 들어 있습니다. 대시보드가 옛 판이면 세 메뉴가 '준비 중' 으로 보입니다.

P&ID · LOGIC · 판넬 · 도서검토
- hotfix133 과 같습니다 (해당 세션 변경 없음).

사람이 확인할 것
- Globe · Butterfly · PSV: 실제 수십 장 PDF 로 첫 대조 · 종류별 꼭 있어야 할 칸 목록 · Process Data 양식(Control Valve / PSV 전용 표 여부).
  Globe · PSV 전용 판정 규칙은 다음 단계입니다 — 지금은 Ball Valve 공통 규칙으로 검토합니다.

아직 안 들어간 것
- 3D 계측제어 (/ic3d): P&ID 서버 주소가 아직 없어 이번 꾸러미에 없습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat (서버 재시작 안내를 따르세요).
2. 화면 위 띠 오른쪽에 '업데이트 134' 가 보이면 새 판입니다. 안 보이면 서버를 다시 켜고 Ctrl+F5 한 번.
