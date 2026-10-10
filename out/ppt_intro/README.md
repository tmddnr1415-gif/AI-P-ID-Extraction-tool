# 기능 소개 PPT (hotfix80 기준 · 2026-10-10)

- 덱: https://claude.ai/artifact/Pd8RZLkV7a4pP9jUUdaonV (Slides 아티팩트 · Share › Export 로 .pptx / PDF 내려받기)
- `shots/` — QFE Rev.B 분석 결과(사본 데이터 · 사용자 홍길동)를 Playwright 로 찍은 실제 동작 화면 23장
- `slides/` + `deck.json` — 슬라이드 19장의 원본 HTML (실제 UI 와 같은 남색 메뉴 · 크림 배경 · 파란 제목)
- `gen_slides.py` — 슬라이드 생성기 (이미지는 아티팩트 자산 `/_blob/<id>` 를 가리킨다)
- `capture_shots*.py` — 화면 캡처 스크립트 (실 DB 를 열지 않고 `PID_DATA_DIR` 사본에서 서버를 띄운다)

## pptx 파일

`PID_기능소개.pptx` — 같은 19장을 PowerPoint 파일로 (13.333×7.5in · 글꼴 Malgun Gothic · 실제 UI 와 같은 남색 메뉴·크림 바탕).
만드는 법: `npm i pptxgenjs` 뒤 `SHOTS=shots OUT=PID_기능소개.pptx node build_pptx.js` (`build_pptx.js` 는 pptx 스킬의 `apply_theme.js` 를 쓴다).
검증: `validate.py` 통과 · LibreOffice 렌더 19장 눈 확인 (hotfix80 · 2026-10-10).
