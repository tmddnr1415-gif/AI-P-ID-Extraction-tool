# QA 시뮬레이션

- ## A. API 전수
- jobs 2 · done 2 · B 48b5adbdd28c · A 2098450b4603
-   느림 6.7s GET /jobs/48b5adbdd28c/titleblock
- GET 47개 · 5xx 0
-   PATCH qty → 200
-   PATCH qty 되돌림 → 200
-   PATCH scope → 200
-   PATCH scope 되돌림 → 200
-   PATCH 없는 칸 → 400
-   PATCH 없는 행 → 404
-   PATCH review state → 200
-   POST rows (마크업) → 200
-   GET history(추가행) → 200
-   DELETE rows(추가행) → 200
-   POST restore → 200
-   DELETE 검출행(오검출 표시) → 200
-   POST restore 검출행 → 200
-   POST copy → 200
-   POST propose → 200
-   POST axis_text → 200
-   POST reports → 200
-   PATCH report → 200
-   DELETE report → 200
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
-   버튼 #excel 비활성
-   탭 0: 동작 실패 — Locator.click: Timeout 2000ms exceeded.
Call log:
  - waiting for locator("#tabs button, #tabs a, #tabs .tab").first
    - locator resolved to <button data-tab=
-      가림: {'row': [853.5, 821.0625, 2488.765625, 28.953125], 'top': 'TD#.', 'rightCompare': '', 'modal': 'modal hidden'}
-   탭 1: 동작 실패 — Locator.click: Timeout 2000ms exceeded.
Call log:
  - waiting for locator("#tabs button, #tabs a, #tabs .tab").nth(1)

-      가림: {'row': [853.5, 821.0625, 2488.765625, 28.953125], 'top': 'TD#.', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 766.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 753.421875, 2480.71875, 28.953125], 'top': 'DIV#stage.', 'rightCompare': '', 'modal': 'modal hidden'}
-   mult-panel 버튼 '지정': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 662.515625, 2410.640625, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   mult-panel 버튼 '지정': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 566.53125, 2272.828125, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   mult-panel 버튼 '지정': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 566.53125, 2272.828125, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   sheet-panel 버튼 '보기': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 490.125, 2272.828125, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   sheet-panel 버튼 '지정': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 490.125, 2272.828125, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   sheet-panel 버튼 '보기': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [341.5, 490.125, 2272.828125, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
- -- round 2
-   버튼 #excel 비활성
-   열 머리 1: 동작 실패 — Locator.click: Timeout 1500ms exceeded.
Call log:
  - waiting for locator("#grid thead th").nth(1)
    - locator resolved to <th data-col="pid_no">…</th>
  - at
-      가림: {'row': [530.5, 500.9375, 2279.453125, 28.953125], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 2 '확인함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 3 '수정함': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 4 '보류': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   근거 패널 버튼 5 'SCT': 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   도면 상자 클릭: 동작 실패 — Page.click: Timeout 3000ms exceeded.
Call log:
  - waiting for locator("#ov rect.det").first

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   오버레이 토글 복귀: 동작 실패 — ElementHandle.click: Element is not attached to the DOM
Call log:
  - attempting click action
    - waiting for element to be visible, enabled and stable

-      가림: {'row': [422.5, 500.9375, 2279.453125, 27.84375], 'top': 'svg#ov.[object SVGAnimatedString]', 'rightCompare': '', 'modal': 'modal hidden'}
-   변경 ▶: 동작 실패 — Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#cmp-changes button[data-step='1']")

-      가림: {'row': [0, 0, 0, 0], 'top': 'SPAN#.head-mark', 'rightCompare': 'compare', 'modal': 'modal hidden'}
-   변경 ◀: 동작 실패 — Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#cmp-changes button[data-step='-1']")

-      가림: {'row': [0, 0, 0, 0], 'top': 'SPAN#.head-mark', 'rightCompare': 'compare', 'modal': 'modal hidden'}
- B 끝 — 페이지/콘솔 오류 누적 0 · 서버 Traceback 0 · 500 0
- ## C. 합성 PDF 전 흐름
-   C 프로젝트 생성 → 200
-   Rev.A 업로드 → 200 5e0126c4db40
-   Rev.A 분석 done · 189초 · 행 None
-   C PATCH qty → 200
-   C 마크업 추가 → 200
-   C 최종 저장 → 200
-   C 변경 내역(비교 대상 없음 → 400) → 400
-   Rev.B 업로드 → 200 af6785b18df0
-   Rev.B 분석 done · 184초 · 행 None
-   C GET revision → 200
-   대조: Rev.B vs Rev.A · counts {'MODIFIED': 40, 'UNCHANGED': 40, 'DELETED_CANDIDATE': 1, 'DELETED': 0} · matched_by {'TAG': 0, 'GEOMETRY': 80} · previous_job_id=True
-   C 변경 내역 Excel → 200
-   Rev.A 편집 승계: qty=5 행 1
-   C 화면: {'side': True, 'sw': True, 'label': 'Rev.B vs Rev.A — 수정 40 · 삭제 후보 1 · 짝 태그 0 · 기하 80 · 빠진 장 1'} · 오류 0
-   C DELETE job Rev.B 확인없이 → 400
-   C DELETE job Rev.B → 200
-   삭제 뒤 — 기본 비교 대상 'Rev.A' · 선택지 ['Rev.A'] · 첫 화면 Rev.B missing=True deleted=True
-   C 지워진 리비전과 비교 요청 → 400 → 400
-   범례 없는 PDF (프로젝트 안 · 프로필 재사용) → done · 행 None
-   범례 없는 PDF (프로젝트 밖) → failed · 사유 '이 PDF 에서 Symbol & Legend 시트를 읽지 못했고, 이 프로젝트에 저장된 범례 프로필도 없습니다. 범례 장이 든 PDF 로 한 번 분석하면 그 값이 프로젝트에 저장되고, 다음 개정본부터는 범례 장이 없' · stopped_stage 'measuring rules off the legend sheets'
-   C 실패한 분석 삭제 → 200
-   C error_detail → 404 {'detail': '그런 분석이 없습니다'}
-   C 분석 중 취소 → 200
-   취소 뒤 상태 cancelled · 행 None · 18초
-   C 취소된 분석 삭제 → 200
-   C 프로젝트 삭제 미리보기 → 200
-   C 프로젝트 삭제 → 200
-   삭제 뒤 /home 에 QA-SYN 남음: False
- C 끝 — 서버 Traceback 1 · 500 0

## 결함 0

