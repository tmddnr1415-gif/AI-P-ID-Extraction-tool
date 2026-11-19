내 메모장 '말로 할 일 넣기'(mmNLP) 시험 — node 만 있으면 됨 (설치 필요 없음)
  cd dashboard_tools/memo_nlp_test
  node run.js            정답표 142 문장 (기준 2026-11-19 목 10:05)
  node run2.js           까다로운 문장 63 (오인식 금지 · 연말 · 주말 · 한밤 · 영어 섞어 쓰기)
  node gen.js 4000 7     날짜 × 시각 × 내용 × 말끝 무작위 4000 문장 (끝 숫자 = 씨앗, 바꿔 가며)
  node gen2.js 4000 11   붙여 쓰기 · 말머리 · 장소 · 담당 · 우선순위 섞인 거친 문장
nlp.js 는 dashboard/dashboard.html 안의 해석기를 그대로 읽어 씀. dashboard.html 의 해석기를 고치면 위 넷을 다시 돌려 모두 통과하는지 볼 것.

2026-11-19 v18.09 — 메일 정리(mmMail) · 비서 명령(mmIntent) 시험 추가 (nlp.js 가 dashboard.html 에서 함께 꺼냄)
  node run_mail.js                       직접 쓴 실제 같은 메일 20통 (정답표)
  node run_mail.js ./holdout_cases.js    고친 뒤 처음 본 메일 15통 (보지 않은 시험)
  node run_mail.js ./holdout_cases.js 2  글자 읽기 오류 흉내 (수준 1~3)
  node gen_mail.js 3000 3                합성 메일 3000통 (녹스 · 아웃룩 한/영 · Gmail · 머리글 없음, 회신 사슬 · 서명). NOISE=2 를 앞에 붙이면 오류 흉내
  node run_assist.js                     비서 명령 — 새로 쓴 자연스러운 말 53개
  node gen_assist.js 4000 5              비서 명령 4000개 (할 일 · 질문 · 완료 · 스티커 · 메모 · 찾기 · 열기 · 불러오기 · 대시보드 질문은 넘김)
  ocr_e2e.js (+ mailtest.html)           화면 캡처 → 한국어+영어 글자 읽기 → 정리 끝단 시험 (Playwright 필요).
                                         대시보드 서버를 임시 폴더에서 띄우고 mailtest.html 을 그 서버의 apps\translate\ 에 복사한 뒤
                                         BASE=http://127.0.0.1:포트 node ocr_e2e.js x2   (저장소의 apps\translate 에는 넣지 말 것)
