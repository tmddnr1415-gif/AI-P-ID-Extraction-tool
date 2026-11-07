# hotfix39 UI 자기검증 — 직전/현재 결과 전환

- 서버 — previous_job_id '2098450b4603' · next_jobs []
- ① 스위치: '결과\n이전 Rev.A\n현재 Rev.B' — 맞음
- 현재: {'job': '48b5adbdd28c', 'rows': 1991, 'page': 6, 'dwg': '1A1Y-00EKG00-M05-0001', 'label': 'Rev.B vs Rev.A — 추가 103 · 수정 458 · 삭제 후보 111 · 짝 태그 1423 · 기하 465 · 도면번호 바뀐 장 3 · 새 장 4 · 빠진 장 2', 'grid': 2102}
- ② 이전으로 (처음 읽음) — 9221ms · 요청 23 · {'job': '2098450b4603', 'rows': 1999, 'page': 51, 'dwg': '1A1Y-10LCM10-M05-0001', 'label': 'Rev.A (비교 대상 없음)', 'grid': 1999} — 맞음
- ③-요청 ['/jobs/48b5adbdd28c/multipliers', '/jobs/48b5adbdd28c/sheet_numbers', '/jobs/48b5adbdd28c/notes/51', '/jobs/48b5adbdd28c/page/51.png?zoom=1.6', '/static/favicon.svg']
- ③ 현재로 (메모리) — 3251ms · 결과 요청 0 · {'job': '48b5adbdd28c', 'rows': 1991, 'page': 51, 'dwg': '1A1Y-10LCM10-M05-0001', 'label': 'Rev.B vs Rev.A — 추가 103 · 수정 458 · 삭제 후보 111 · 짝 태그 1423 · 기하 465 · 도면번호 바뀐 장 3 · 새 장 4 · 빠진 장 2', 'grid': 2102} — 맞음
- ④ 다시 이전으로 (메모리) — 3214ms · 결과 요청 0 · rows 1999 — 맞음
- ⑤ 스위치 문구: '결과\n이전 Rev.A\n현재 Rev.B\n직전 결과를 보는 중 — 편집은 그 결과에 저장됩니다 · 전환 1087ms (메모리)'
- ⑥ 페이지 오류 0
