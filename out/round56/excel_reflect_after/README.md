# hotfix15 — Excel 이 지금의 데이터를 담는가

- ① 검토 완료 rev 1 · ② 편집 3 · 삭제 1 · 마크업 추가 1 뒤 단추: 'Excel 출력 (편집 반영 — 누르면 새로 만듭니다)'
- ③ 내려받음 — 스냅샷 rev 1 → 2
- 콘솔 오류: 없음
- ④ 통과 — scope 편집 (00EKG00CP001): 'VENDOR(TEST SUPPLIER)'
- ④ 통과 — description 편집 (00EKG40CT001): 'EDITED BY REVIEWER'
- ④ 통과 — qty 편집 (00EKG30CT001): 7
- ④ 통과 — 삭제한 행 (00EKG30CP001A) 이 없다: False
- ④ 통과 — 마크업 추가 행이 있다: ['PDIT', 'P&ID FOR FUEL OIL', 1, 'SCT']
-    FIELD 파일 행 324 (태그 있는 행)
- 실 DB sha256 — 같은가: True
