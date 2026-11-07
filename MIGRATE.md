# 다른 컴퓨터로 이관 방법

1. zip 을 풀고 폴더를 Claude Code 로 연다(`claude` 실행). `CLAUDE.md`, `.claude/agents`, `.claude/skills` 가 자동 적용된다.
2. 필요: Node.js 18+, Python 3.9+ (외부 패키지 없음). 실행:
   - `python3 ic-3d-builder/dev/build.py` → 실물 3D 엔진 `ic-3d-builder/index.html` (3D 를 고쳤을 때만)
   - `node app/build.mjs` → `app/index.html` 재생성 (Anatomy kit 은 `anatomy/kit`, 실물 3D 는 `app/viewer-real.html` 로 복사, LLM 지식은 `ic-expert/knowledge`)
   - `python app/server.py` → http://127.0.0.1:8790
3. 재무 기능(선택): 원 PC 의 `../현장회의록_요약/dart_dashboard` 를 벤치마크로 쓴다. 새 PC 에는 없으면 `/fin/` 이 비활성이고 나머지는 동작한다.
   DART 키는 zip 에 넣지 않았다. 새 PC 에서 환경변수 `DART_API_KEY` 또는 프로젝트 `.env`(`DART_API_KEY=...`)로 설정한다. 키 값은 대화·로그에 출력하지 않는다.
4. 구조: `app/`(template.html, app.js, viewer3d.js, sims.js, build.mjs, server.py), `Spec for each Item/`(Spec+Knowledge 12), `data/`(mr, dim, parts), `output/`(MR 초안 docx), `제출/`(과제 제출 3파일).
5. 개선 시 주의: 편집은 app.js / viewer3d.js / sims.js / template.html 에서 하고 `node app/build.mjs` 로 빌드한다. `app/index.html` 은 생성물이다.
6. 알려진 한계: 답변은 기본 로컬 검색형(헤더 [답변 엔진]으로 Claude(LLM) 선택 가능, Anthropic API Key 필요), 실물 3D 는 three.js 를 cdnjs 에서 받으므로 인터넷 필요, 수치는 모두 '미확인'(프로젝트 Spec 대조 필요), 3D 는 개념 모델, 12개 중 볼밸브·CCS 시뮬레이션만 화면 확인.
