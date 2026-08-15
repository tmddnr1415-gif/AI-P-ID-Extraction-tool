# P&ID Instrument Extractor

P&ID 도면을 업로드하면 Claude API가 도면을 검토하고 **계기(instrument) 목록을 지정한 포맷으로** 뽑아주는 HTML 기반 웹앱입니다.
빌드 도구·백엔드 없이 `index.html` / `styles.css` / `app.js` 세 파일로 동작합니다.

## 기능

- **도면 업로드** — PNG / JPG / WEBP / GIF / PDF, 여러 장 동시 업로드 (멀티 시트 도면 지원)
- **출력 포맷 지정** — 화면에서 컬럼(필드 키·헤더·추출 기준)을 직접 편집. 편집한 컬럼이 그대로 JSON Schema로 변환되어
  [구조화 출력(structured outputs)](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)으로 모델에 전달되므로,
  응답은 **항상** 지정한 포맷을 그대로 따릅니다.
- **기본 포맷** — ISA-5.1 기준 10개 컬럼: Tag No. / Function / Measured Var. / Service / Line·Equip. /
  P&ID No. / Signal·Loop / Location / I/O Type / Remarks
- **검토 의견** — 태그 중복·누락, 번호 체계 불일치, 심볼-태그 불일치, 판독 불가 영역을 severity와 함께 보고
- **내보내기** — CSV(엑셀 한글 호환 BOM 포함) · 엑셀 붙여넣기용 TSV 복사 · 전체 JSON
- **스트리밍 진행 표시**와 중지 버튼, 검색 필터

## 실행

`file://` 로 열면 브라우저가 API 호출을 CORS로 차단할 수 있으므로 로컬 서버로 띄웁니다.

```bash
# 아무 정적 서버나 사용 가능
python3 -m http.server 8000
#   또는
npx serve .
```

`http://localhost:8000` 접속 → 우측 상단 **⚙ 설정**에서 Anthropic API Key 입력 → 도면 업로드 → **P&ID 검토 실행**.

API Key는 브라우저 `localStorage`에만 저장되고 `api.anthropic.com` 외 어디로도 전송되지 않습니다.

## 설정 항목

| 항목 | 기본값 | 설명 |
|---|---|---|
| 모델 | `claude-opus-5` | 도면 판독 정확도가 가장 높습니다. 빠르고 저렴하게 돌리려면 `claude-sonnet-5`. |
| Effort | `high` | 추론 깊이. 복잡하거나 밀도 높은 도면은 `xhigh`, 단순 도면은 `medium`. |
| 최대 출력 토큰 | 32,000 | 계기 수가 많아 응답이 잘리면(`max_tokens` 경고) 늘리세요. |
| 이미지 자동 축소 | 켬 | 장변 2576px(모델 최대 해상도) 초과 이미지만 축소합니다. 그 이하 이미지는 선이 뭉개지지 않도록 원본 그대로 전송합니다. |

## 동작 방식

1. 업로드한 도면을 base64 `image` / `document` 블록으로 만들어 Messages API에 보냅니다.
2. 시스템 프롬프트는 ISA-5.1 판독 규칙(태그 문자 해석, 버블 테두리 → 설치 위치, 신호선 형태 → 신호 종류)과
   "보이는 것만 기재하고 확인 불가하면 `-`" 원칙을 지시합니다.
3. `output_config.format` 에 컬럼에서 생성한 JSON Schema를 실어 응답 포맷을 강제합니다
   (`instruments[]`, `review_findings[]`, `summary`).
4. 응답은 SSE로 스트리밍해 진행 상황을 표시하고, 완료 시 파싱해 표로 렌더링합니다.

## 정확도를 높이려면

- 도면은 가능한 **고해상도**로 올리세요. 계기 버블의 태그 글자가 뭉개지면 모델도 읽지 못하고, 그런 영역은 검토 의견에 보고됩니다.
- 한 번에 너무 많은 시트를 넣기보다 **시트 단위로 나눠 실행**하면 누락이 줄어듭니다.
- 프로젝트 고유 규칙(태그 체계, 제외 대상, 비고 기재 방식)은 **추가 지시사항**에 적어주세요.
- 결과는 반드시 사람이 검증해야 합니다. 이 도구는 계기 목록 초안 작성용이지 승인 문서 생성용이 아닙니다.

## 제약

- 요청 1건 최대 32MB(PDF 기준). 초과하면 업로드 영역에 경고가 표시됩니다.
- 브라우저에서 API를 직접 호출하므로 API Key를 다루는 사람만 사용하는 내부용 도구로 적합합니다.
  여러 사용자에게 배포하려면 API Key를 서버에 두고 프록시하는 백엔드를 추가하세요.
