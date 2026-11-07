# hotfix44 대조 다시 — 화면 자기검증

- 누르기 전 서버 counts — {'UNCHANGED': 1430, 'MODIFIED': 458, 'ADDED': 103, 'DELETED_CANDIDATE': 111, 'DELETED': 0}
- ① `대조 다시` 버튼 — 있음
- ② 누르기 전 머리줄 — 'Rev.B vs Rev.A — 추가 103 · 수정 458 · 삭제 후보 111 · 짝 태그 1423 · 기하 465 · 도면번호 바뀐 장 3 · 새 장 4 · 빠진 장 2'
- ③ 누른 뒤 8.6초 · POST /revision 1회 · 머리줄 — 'Rev.B vs Rev.A — 추가 103 · 수정 18 · 삭제 후보 111 · 짝 태그 1423 · 기하 465 · 도면번호 바뀐 장 3 · 새 장 4 · 빠진 장 2' · 서버 counts {'UNCHANGED': 1870, 'ADDED': 103, 'MODIFIED': 18, 'DELETED_CANDIDATE': 111, 'DELETED': 0}
-    수정 458 → 18 · 추가 103 → 103 · 삭제 후보 111 → 111 — 맞음
- ④ 같은 장에 머묾 — 1A1Y-00EKG00-M05-0001 → 1A1Y-00EKG00-M05-0001 — 맞음
- ⑤ 페이지 오류 0
