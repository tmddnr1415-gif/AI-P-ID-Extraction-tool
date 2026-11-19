내 메모장 '말로 할 일 넣기'(mmNLP) 시험 — node 만 있으면 됨 (설치 필요 없음)
  cd dashboard_tools/memo_nlp_test
  node run.js            정답표 142 문장 (기준 2026-11-19 목 10:05)
  node run2.js           까다로운 문장 63 (오인식 금지 · 연말 · 주말 · 한밤 · 영어 섞어 쓰기)
  node gen.js 4000 7     날짜 × 시각 × 내용 × 말끝 무작위 4000 문장 (끝 숫자 = 씨앗, 바꿔 가며)
  node gen2.js 4000 11   붙여 쓰기 · 말머리 · 장소 · 담당 · 우선순위 섞인 거친 문장
nlp.js 는 dashboard/dashboard.html 안의 해석기를 그대로 읽어 씀. dashboard.html 의 해석기를 고치면 위 넷을 다시 돌려 모두 통과하는지 볼 것.
