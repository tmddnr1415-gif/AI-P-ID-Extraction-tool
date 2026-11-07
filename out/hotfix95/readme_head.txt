hotfix95 — PID_dev + 운영(PID) 꾸러미  (97a8732 기준 누적 · hotfix56 ~ 94 + LOGIC L1 ~ L20 포함)

LOGIC 검토 (L20 · 이번에 새로 들어간 것)
  · 새 프로젝트 Logic 분석이 "[WinError 5] 액세스가 거부되었습니다 … status.json" 으로 멈추던 것을 고쳤습니다.
    진행 상황을 적는 순간 화면이나 백신이 그 파일을 잡고 있어도, 잠깐 기다렸다 다시 쓰고
    끝내 안 되면 그 한 줄만 건너뜁니다 — 진행 표시 때문에 분석이 멈추지 않습니다.
  · 업데이트 뒤 멈췄던 Logic 은 다시 분석해 주세요.

이전 꾸러미 내용도 모두 들어 있습니다
  (hotfix94: 도면에서 Shift 로 여러 계기를 고른 뒤 Shift+클릭 → SCT / VENDOR / 둘 다 아님 일괄 적용).

순서 (zip 을 아무 폴더에 풀고):
  1) apply_to_PID_dev.bat 더블클릭
  2) 분석이 돌고 있지 않을 때  apply_to_PID_ops.bat 더블클릭
       → "포트 8000 서버를 다시 띄울까요? [Y/n]" 에서 Enter
       → "[완료] 서버가 다시 떴습니다 — 업데이트 hotfix95" 가 나오면 됩니다
  3) 대시보드에서 P&ID 분석 · LOGIC 을 다시 열고 Ctrl+F5
  4) (hotfix93 때 아직 안 했다면 한 번만) 서버 창 파일 바꾸기 — zip 의 service 폴더의
     run_lan_service.bat 을 C:\Claude\PID 에 넣습니다 (서버 창을 모두 닫은 뒤, 옛 파일은 .old 로).
     이미 했으면 건너뛰세요.

문제가 생기면:  rollback_PID_ops.bat 더블클릭.
