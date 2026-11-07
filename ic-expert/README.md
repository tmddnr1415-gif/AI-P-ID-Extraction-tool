# I&C Expert — 계장 전문가 챗봇

프로젝트 스펙·데이터시트·질문을 넣으면 **시니어 계장 리드 엔지니어**로서 의견과 근거를 주는 챗봇입니다.

- **답의 형태**: Answer(의견·결론) → Basis(근거: 국제 코드 / 발주처 표준 / 벤더 데이터 구분) → Check / risks(검증할 것)
- **스펙 리뷰**: 발견사항 표 `# · 조항 · 스펙 내용 · 전문가 의견 · 근거 · 심각도 · 조치` + Open questions
- **벤더 비교**: 모델 · 주요 사양 · 인증/SIL · 적합성 표 (최종 선정은 프로젝트 AVL)
- 한국어로 물으면 한국어로 답합니다. 표준명·모델명·용어는 영어 그대로.

## 쓰는 법

1. `ic-expert/index.html` 을 브라우저로 엽니다 (더블클릭, 설치 없음).
2. ⚙ Settings 에 Anthropic API 키. 기본 모델 `claude-opus-5-5`, effort `high`.
3. 왼쪽 **Project context** 에 발주처(Saudi Aramco / QatarEnergy / ADNOC / Shell DEP / KOC / 국제코드), 프로젝트,
   현장 조건, 위험지역·SIL 을 적습니다. 모든 답변에 반영됩니다.
4. 스펙·데이터시트(PDF, 이미지, TXT/CSV)를 끌어다 놓고 질문합니다. 첨부는 다음 메시지와 함께 전송됩니다.
5. **Web search** 를 켜 두면 지식베이스에 없는 내용, 최신 모델·개정판을 웹에서 찾아 출처와 함께 답합니다.
6. **Export** 로 대화를 Markdown(출처 포함)으로 저장합니다.

## "학습"은 어떻게 했나

모델 자체를 재학습시킨 것이 아니라, 웹에서 조사한 **출처 달린 지식베이스**(`knowledge/*.md`)를 매 질문마다
전문가 프롬프트와 함께 넣습니다(프롬프트 캐시로 반복 비용을 줄임). 빈 곳은 실시간 웹 검색으로 채웁니다.

| 파일 | 내용 |
|---|---|
| `01-international-codes.md` | IEC 61508/61511, IEC 60079, ISA-5.1/75/84, API 551~556/670/2350/520/526, ASME PTC 19.3 TW, ISO 5167, NAMUR NE 43/107, NACE MR0175 … |
| `02-saudi-aramco.md` | SAES-J / SAES-Z / 34-SAMSS 문서 색인과 공개적으로 확인되는 요구사항 |
| `03-qatarenergy-gulf.md` | QatarEnergy · QatarEnergy LNG, ADNOC, Shell DEP, KOC, PDO, 걸프 현장 설계 조건 |
| `04-vendors-emerson-honeywell.md` | Rosemount, Micro Motion, Fisher, DeltaV, Honeywell SmartLine/Experion/Safety Manager … |
| `05-vendors-yokogawa-bently-wika.md` | Yokogawa DPharp/CENTUM VP/ProSafe-RS, Bently Nevada 3500·3300 XL·API 670, WIKA |
| `06-instrument-items-selection.md` | 아이템별 선정·사이징·설치·데이터시트·흔한 실수, 기타 벤더(E+H, Siemens, ABB, Krohne, VEGA, Rotork …) |

각 사실 뒤에는 출처 링크가, 확인하지 못한 내용에는 `[general knowledge — verify]` 표시가 붙어 있습니다.
지식베이스를 고친 뒤에는 `python3 ic-expert/dev/build.py` 로 단일 파일 앱을 다시 만듭니다.

## 한계 (정직하게)

- **Saudi Aramco SAES/SAMSS, QatarEnergy 표준은 통제 문서**라 원문을 구할 수 없습니다. 지식베이스에는 공개적으로
  확인되는 문서 번호·제목·범위·알려진 요구사항만 있고, 챗봇은 조항 원문을 지어내지 않고 "프로젝트 통제본 확인"을 안내합니다.
  회사가 보유한 원문을 지식베이스에 추가하면(사내 반입 규정 확인 후) 정확도가 크게 올라갑니다.
- 벤더 사양은 카탈로그 기준입니다. 구매·설계 확정은 벤더 인증 데이터시트와 프로젝트 AVL 을 따릅니다.
- 이 도구는 설계 검토를 돕는 것이지, 책임 엔지니어의 검증과 발주처 승인을 대신하지 않습니다.
- 답변 정확도는 아직 체계적으로 측정하지 않았습니다. 과거 프로젝트의 리뷰 코멘트로 평가 세트를 만들기를 권합니다.

## 개발

```
python3 ic-expert/dev/build.py                       # knowledge/*.md → src/kb.gen.js → index.html
NODE_PATH=$(npm root -g) node ic-expert/dev/test_mock.mjs   # 가짜 API 스트림으로 대화·웹검색·이어받기 테스트
```

Claude Code 에서는 스킬 `.claude/skills/ic-expert` 가 같은 지식베이스로 답합니다.
