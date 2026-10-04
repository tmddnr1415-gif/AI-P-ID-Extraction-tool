# QA 시뮬레이션

- ## A. API 전수
- jobs 2 · done 2 · B 48b5adbdd28c · A 2098450b4603
-   느림 6.5s GET /jobs/48b5adbdd28c/titleblock
- GET 47개 · 5xx 0
-   PATCH qty → 200
-   PATCH qty 되돌림 → 200
-   PATCH scope → 200
-   PATCH scope 되돌림 → 200
-   PATCH 없는 칸 → 400
-   PATCH 없는 행 → 404
-   PATCH review state → 400 {'detail': "unknown review state 'CHECKED'"}
-   POST rows (마크업) → 200
-   GET history(추가행) → 200
-   DELETE rows(추가행) → 400 {'detail': "unknown reason class 'WRONG'"}
-   POST restore → 200
-   DELETE 검출행(오검출 표시) → 400 {'detail': "unknown reason class 'WRONG'"}
-   POST restore 검출행 → 200
-   POST copy → 200
-   POST propose → 200
-   POST axis_text → 200
-   POST reports → 400
-   POST multipliers → 200
-   DELETE multipliers → 200
-   POST sheet_numbers → 200
-   DELETE sheet_numbers → 200
-   POST titleblock/preview → 400
-   POST titleblock → 200
-   DELETE titleblock → 200
-   POST snapshot → 200
-   POST save → 200
-   GET revisions/{id}/excel → 400
-   POST deleted confirm → 200
-   POST deleted unconfirm → 200
-   PATCH project mode → 200
-   PATCH project mode auto → 200
-   POST symbols/global → 400
-   POST symbols/global/enabled → 200
-   DELETE symbols/global → 404
-   POST diagnostic → 200
-   POST projects 중복 → 409
-   POST projects 새 → 200
-   DELETE projects 확인없이 → 400
-   DELETE projects → 200
-   POST jobs 빈 파일 → 400
- A 끝 — 서버 Traceback 0 · 500 0
- ## B. 화면 전수 클릭
- -- round 1
-   버튼 #excel: 동작 실패 — ElementHandle.click: Timeout 3000ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   탭 1: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   탭 2: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   탭 3: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   탭 4: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   탭 5: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   검토 필요만: 동작 실패 — Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#only-review")
    - locator resolved to <input type="checkbox" id="only-review"/>
  - 
-   검토 필요만 해제: 동작 실패 — Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#only-review")
    - locator resolved to <input type="checkbox" id="only-review"/>
  - 
-   검색어: 동작 실패 — Page.fill: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#filter")
    - locator resolved to <input id="filter" type="search" placeholder="검색 — 모
-   검색어 지움: 동작 실패 — Page.fill: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#filter")
    - locator resolved to <input id="filter" type="search" placeholder="검색 — 모
-   열 머리 0: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 1: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 2: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 3: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 4: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 5: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 6: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 7: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 8: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 9: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 10: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   열 머리 11: 동작 실패 — ElementHandle.click: Timeout 1500ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   행 클릭 0: 동작 실패 — ElementHandle.click: Timeout 2000ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   행 클릭 1: 동작 실패 — ElementHandle.click: Timeout 2000ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   행 클릭 2: 동작 실패 — ElementHandle.click: Timeout 2000ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   행 클릭 3: 동작 실패 — ElementHandle.click: Timeout 2000ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   행 클릭 4: 동작 실패 — ElementHandle.click: Timeout 2000ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   셀 편집 qty: 동작 실패 — Page.dblclick: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#body tr:first-child td[data-col=qty]")
    - locator resolved to <td title="1" data
-   셀 편집 qty 되돌림: 동작 실패 — Page.dblclick: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#body tr:first-child td[data-col=qty]")
    - locator resolved to <td title="1" data
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   mult-panel 버튼 '지정': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable
    - 
-   mult-panel 버튼 '지정': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   mult-panel 버튼 '지정': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   sheet-panel 버튼 '보기': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   sheet-panel 버튼 '지정': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   sheet-panel 버튼 '보기': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

- -- round 2
-   버튼 #excel: 동작 실패 — ElementHandle.click: Timeout 3000ms exceeded.
Call log:
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - elemen
-   탭 1: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   탭 2: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   탭 3: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   탭 4: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   탭 5: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 1: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 2: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 3: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 4: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 5: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 6: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 7: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 8: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 9: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 10: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   열 머리 11: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 5 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 5 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 5 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 5 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   근거 패널 버튼 5 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   도면 상자 클릭: 동작 실패 — Page.click: Timeout 3000ms exceeded.
Call log:
  - waiting for locator("#ov rect.det").first

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-   변경 ▶: 동작 실패 — Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#cmp-changes button[data-step='1']")

-   변경 ◀: 동작 실패 — Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#cmp-changes button[data-step='-1']")

- B 끝 — 페이지/콘솔 오류 누적 0 · 서버 Traceback 0 · 500 0

## 결함 0

