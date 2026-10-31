hotfix104 — PID_dev + 운영(PID) 꾸러미  (97a8732 기준 누적 · hotfix101~103 내용 전부 포함)

이번에 들어간 것 — LOGIC
  (L45) 매크로 '내부 동작 보기' 새 창에서 Typical 안쪽의 선·블록
        (S-R 래치 앞뒤 등)도 눌러서 1/0 을 줄 수 있습니다.
        · 새 창에서 준 값은 부모 시트를 통해 함께 돌아갑니다
        · 래치 Q 를 1 로 주면 SET 1 · RESET 0 으로 맞춰 켭니다
  (이전 hotfix103 의 L43 · L44 도 그대로 들어 있습니다)

순서 (zip 을 아무 폴더에 풀고):
  1) apply_to_PID_dev.bat 더블클릭
  2) 분석이 돌고 있지 않을 때  apply_to_PID_ops.bat 더블클릭
       → "포트 8000 서버를 다시 띄울까요? [Y/n]" 에서 Enter
       → "[완료] 서버가 다시 떴습니다 — 업데이트 hotfix104" 가 나오면 됩니다
  3) 대시보드에서 LOGIC 을 다시 열고 Ctrl+F5
  4) 서버 창 파일(run_lan_service.bat)을 이미 새 것으로 바꿨으면 건너뛰세요.
     아직이면 zip 의 files 폴더에 있는 run_lan_service.bat 을 C:\Claude\PID 에 넣습니다
     (서버 창을 모두 닫은 뒤, 옛 파일은 .old 로).

문제가 생기면:  rollback_PID_ops.bat 더블클릭.
