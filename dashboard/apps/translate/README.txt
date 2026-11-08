계장ENG그룹 Dashboard — 클로드 비서 번역 · 그림 속 영어 읽기 (apps\translate\)   2026-11-08

이 폴더는 대시보드 서버(server.py)가 /apps/translate/ 로 그대로 내보내고, 부서원 브라우저 안에서만 동작합니다.
글 · 그림은 서버에도, 인터넷에도 보내지 않습니다(브라우저 안 WebAssembly). 처음 쓸 때 모델(약 35~45MB)을 서버에서 한 번 받습니다.

구성 (모두 공개 소프트웨어 · 공개 모델, 원본 그대로 — 바꾼 곳은 fx\fxtranslate_wasm.js 맨 아래 Node 전용 부분뿐)
  translate-worker.js      대시보드가 띄우는 번역 워커(여기서 작성)
  fx\                      fxtranslate 0.5.0 — Firefox 번역 모델을 돌리는 엔진 (MPL-2.0, https://www.npmjs.com/package/fxtranslate)
  models\enko\ · koen\     Mozilla Firefox Translations 모델 (영→한 · 한→영, base-memory)
                           출처: https://mozilla.github.io/translations/firefox-models/  (모델 목록 JSON: storage.googleapis.com/moz-fx-translations-data--303e-prod-translations-data/db/models.json)
                           Mozilla 가 Firefox 에 내장해 배포하는 공개 모델 (mozilla/translations, MPL-2.0)
  ocr\                     tesseract.js 7.0.0 + tesseract.js-core 6.1.2 (Apache-2.0) — 그림 속 글자 읽기
  ocr\lang\eng.traineddata.gz   영어 인식 데이터 (@tesseract.js-data/eng 4.0.0_best_int, MIT 패키지 / tessdata Apache-2.0)

업데이트: 대시보드 zip 에 함께 들어 있음(make_patch KEEP_PREFIX). 없으면 비서가 "번역 프로그램 파일이 서버에 없음" 이라고 알립니다.
