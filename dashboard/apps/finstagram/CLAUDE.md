# 재무스타그램 — DART 공시 재무 대시보드

회사명을 검색하면 DART 공시 재무제표, 요약, 주가, 컨센서스, 사업부문, 수주 현황(3D 지구본)을 보여주는 로컬 웹 대시보드.
이 문서는 다른 Claude Code 세션이 이어서 개발할 때 필요한 맥락(구조 · 데이터 출처 · 사용자 요구 · 남은 과제)을 담는다.

## 계장ENG그룹 Dashboard 안에서 (2026-11-07~)

- 이 폴더는 대시보드 저장소 `dashboard/apps/finstagram/` = 회사 운영 폴더 `apps\finstagram\`. 대시보드 server.py(`fin_loop`)가 이 server.py 를 함께 띄우고, 메뉴 '재무스타그램'이 `http://<서버>:8765/` 를 iframe 으로 연다. 고치면 대시보드 업데이트 zip 에 같이 들어감.
- 회사 PC 규칙: Python 3.11 표준 라이브러리만(pymupdf 없음 → IR 카드 꺼짐) · **CDN 금지 → 라이브러리는 `vendor/`** · API 키는 배포물에 넣지 않음(대시보드가 `DART_KEY_FILE` 로 서버 PC 키 파일 경로를 넘김) · 사내망 주소만 접속(`allowed`).

## 실행

```bash
# 1) DART API 키 (https://opendart.fss.or.kr 에서 발급) — 둘 중 하나
echo YOUR_KEY > dart_api_key.txt          # 또는 환경변수 DART_API_KEY
# 2) (선택) 회사 IR PDF 분석용
pip install -r requirements.txt           # pymupdf 하나뿐. 없으면 IR 카드만 비활성
# 3) 서버
python server.py                          # → http://localhost:8765
```

- 서버는 **Python 표준 라이브러리만** 사용(ThreadingHTTPServer, 127.0.0.1:8765). DART가 CORS를 막아 서버가 프록시한다.
- Claude 데스크톱 미리보기: `.claude/launch.json`의 `dart-dashboard` 구성(`python server.py`, 포트 8765).
- 첫 실행 시 DART 고유번호 목록(`corp_codes.json`, 약 13MB)을 내려받아 7일 캐시. `cache/` 폴더도 자동 생성된다.
- `dart_api_key.txt`, `corp_codes.json`, `cache/`는 커밋·공유하지 않는다(키는 비밀, 나머지는 재생성됨).

## 파일 구조

| 파일 | 역할 |
|---|---|
| `server.py` | DART 호출, 검색, 재무제표·5개년·사업부문(XBRL)·지속가능성·직원 현황, 규칙 기반 요약, HTTP 라우팅 |
| `extras.py` | 주가 · 컨센서스 · 분기 누적 · 수주현황(사업보고서 원문 파싱) · 날씨/시간대 · 회사 CI · 회사 IR PDF 파싱. `server.py`가 `extras.init(dart_get, fetch_statements, extract_key)`로 의존성 주입 |
| `index.html` | 프런트엔드 단일 파일(ECharts 5.4.3, globe.gl 2.34.1은 지연 로드). 모든 렌더 함수가 여기에 있다 |

### API 라우트 (`server.py` → `Handler.do_GET`)

| 경로 | 함수 | 내용 |
|---|---|---|
| `/api/search?q=` | `search` | 회사 검색. 동명 회사면 대표이사(`ceo_nm`) 첨부, 상장·최근 수정일 우선 정렬 |
| `/api/fin?corp_code&year&reprt&fs` | `build` | 재무제표 전체 + 핵심 계정 + 요약 + 직원 현황 |
| `/api/history` | `history` | 최근 5개년 핵심 계정(KPI 클릭 모달) |
| `/api/segments?rcept_no&reprt&fs` | `segments` | XBRL `fnlttXbrl.xml`에서 영업부문 매출·영업이익 |
| `/api/sustain` | `sustainability` | 7개 항목 상/중/하 + 100점 점수(규칙 기반) |
| `/api/stock?stock_code&corp_code` | `extras.stock` | 네이버 일봉 5년 + 발행주식수(DART) + EPS/BPS(네이버) |
| `/api/quarters?corp_code&stock_code&year&fs` | `extras.quarters` | 분기 실적: DART 실적 → 회사 IR 발표(잠정) → FnGuide 컨센서스(E) 순으로 채움 |
| `/api/ir?corp_code` | `extras.ir_quarters` | 회사 IR 실적발표 PDF → 분기별 사업부문 매출·영업이익 |
| `/api/orders?corp_code` | `extras.orders` | 사업보고서 5년치 원문 `document.xml`에서 수주현황 표 파싱(국가 판별 포함) |
| `/api/weather?names=` | `extras.weather` | Open-Meteo 현재 날씨(국가 대표 도시, 30분 캐시) |
| `/api/logo?stock_code&hm_url` | `extras.logo` | 회사 CI: 네이버 종목 로고 SVG → 홈페이지 파비콘 → 없으면 404(첫 글자 표시) |

## 데이터 출처와 주의점

- **DART OpenAPI**: `corpCode.xml`, `company.json`, `fnlttSinglAcntAll.json`(분·반기는 `*_add_amount` 누적), `empSttus.json`, `fnlttXbrl.xml`, `document.xml`(원문 zip), `list.json`(A001 사업보고서), `stockTotqySttus.json`.
- **주가**: `fchart.stock.naver.com/sise.nhn` (EUC-KR XML, `date|open|high|low|close|volume`).
- **컨센서스**: WiseReport(FnGuide) `navercomp.wisereport.co.kr/v2/company/ajax/cF1001.aspx`. 메인 페이지에서 `encparam`/`id`를 먼저 얻어야 한다. `fin_typ=4` 연결, `3` 별도. `freq_typ` Y/Q. 단위 억원. 컨센서스 열의 영업이익은 `영업이익(발표기준)` 행에만 값이 있는 경우가 있어 폴백한다. 별도 기준 컨센서스는 대부분 회사가 비어 있다(정상 — "없음"으로 표시).
- **회사 IR**: 회사별 어댑터 `extras.IR_ADAPTERS` (현재 **삼성물산 `00149655`만**). 목록 `https://www.samsungcnt.com/ir/event-earnings/li/earnings-release.do?event_year=YYYY`, PDF는 `data-ga-filetype="report"` 링크. PyMuPDF로 '구분 | 'YY.nQ ...' 경영실적 페이지를 토큰 파싱(값 순서: 당분기, 전분기, 증감, 전년동기 …, 단위 십억원, `△`=음수, 단독 `*` 토큰 제거). 최신 보고서 값이 이전 값을 덮어씀(재작성 반영). 2023Q1~2026Q3 15개 분기 모두 부문 합계 = 회사 합계로 검산됨.
- **수주현황**: 사업보고서 원문의 '수주상황(상세)' 표(공사명·발주처·계약일·도급액·잔액). 머리글 띄어쓰기("공 사 명") 무시하고 탐지. 수주 국가 = 발주처 앞 `(국가)` 표기, 수행 국가 = 공사명 속 국가명(`extras.COUNTRIES` 별칭 사전). '기타'로 묶인 소규모 현장은 국가 분류 제외.
- **지도**: 2D는 ECharts + `echarts@4.9.0/map/json/world.json`(jsdelivr). 3D는 globe.gl + three-globe 예제 텍스처(Blue Marble, topology, night-sky). Taiwan/HK는 world.json 폴리곤이 없어 좌표 버블만.
- **시간/날씨**: 국가→IANA 시간대·대표 도시 `extras.TZ`. 현지 시각은 브라우저 `Intl`로 계산(Windows 파이썬에 tzdata 없음).

## 사용자 요구 · 결정 사항 (유지할 것)

- 화면/글은 **한국어**. 사용자는 삼성물산 사업팀 관점(건설·수주·해외 현장)에 관심이 많다.
- UI 톤: 인스타그램 느낌의 **차분한 미니멀**. 화려한 그라데이션·3D 차트 금지(사용자 피드백 "UI 너무 화려하고 3D 보기 불필요함"). **예외: 수주 지도는 사용자가 Google Earth 같은 3D 지구본을 요청** → 기본 3D, 2D 전환 가능.
- 차트는 **dataviz 스킬 규칙**을 따른다: 검증된 범주 팔레트(라이트 `#2a78d6 #eb6834 #1baf7a #eda100 #e87ba4 #008300`, 다크 별도 단계), 고정 순서·엔티티별 고정 색, 막대 ≤24px·끝 4px 라운드·누적 2px 간격, 시리즈 1개면 범례 없음, 툴팁은 값 먼저, 이중 축 금지, 전년 비교는 회색 강조 해제, 큰 숫자는 비례폭 숫자, 다크 모드는 `:root[data-theme]` 스코프까지 별도 지정. 팔레트를 바꾸면 dataviz의 `validate_palette.js`로 검증.
- **모든 금액 표에 `(단위: 억원)` 캡션**. (예외: 주가 표는 원·주)
- 분기 누적 실적: DART 미공시 분기는 **회사 IR 발표(표시 IR) → 컨센서스(표시 E)** 순. 컨센서스는 상단 재무제표 선택(연결/별도)과 **같은 기준**. 누적(반기 등) KPI 카드에 연간 예상치 병기.
- 반기·분기·사업부별 실적은 **각 회사 공식 IR 사이트 보고서를 참조**해 반영(사용자 지시). 진행 중 반기는 전년 같은 분기끼리 비교.
- 검색 결과 동명 회사에는 대표이사 표기. 직원 현황은 정규직/비정규직 · 사업부문별 표.
- 지도: 각국 현지 시각·날씨 표기, 원 넓이(2D)/막대 높이(3D) = 금액, 기본 '해외만'(국내가 46%라 해외가 묻힘), 지역 프리셋(전 세계·중동·아시아·미주·유럽·오세아니아), 국가 클릭 → 프로젝트 필터.
- 회사 CI 표기(프로필 아바타).
- 사용자가 언급한 '재무현황' 스킬, '지도' 스킬은 원래 환경에서 찾지 못해 dataviz 스킬로 대체했다. 새 환경에 그 스킬이 있으면 그 지침을 우선 적용할 것.

## 남은 과제 / 알려진 이슈

- [ ] **회사 IR 어댑터 추가**: 사용자가 대상 회사를 알려주기로 함. 회사마다 `IR_ADAPTERS[corp_code] = {"name", "page", "list": fn(years) -> [(year, q, pdf_url)]}` 추가, 표 형식이 다르면 `parse_ir_results_page` 보강. 추가 후 분기별 부문 합계 = 회사 합계, DART 값과 대조 검산.
- [ ] 2026 반기보고서(`rcept_no 20260814002969`)에서 `/api/segments`가 "XBRL 파일을 받지 못했습니다: File is not a zip file" — 분·반기 XBRL 제공 여부/파라미터 확인 필요(사업보고서는 정상).
- [ ] 수주현황 파서는 삼성물산 형식으로 검증. 다른 건설사는 표 형식이 달라 일부 누락 가능.
- [ ] 지속가능성 상/중/하 기준은 업종 무관 일반 기준(은행 등 고부채 업종 불리).
- [ ] 콘솔의 404 1건은 favicon.
- [ ] 라이트 모드 확인 시 미리보기 창의 color-scheme 에뮬레이션이 먹지 않아 `document.documentElement.dataset.theme='light'`로 확인했다.

## 검증 습관

- 서버 수정 후에는 서버 재시작(모듈 캐시). 브라우저 확인은 `pick(검색결과)` 후 15~20초 대기(XBRL·원문·IR PDF 첫 다운로드).
- 확인용 회사: 삼성물산(`00149655`, 028260 — 수주·IR 모두 지원), 삼성전자(`00126380`, 005930 — 사업부문 DX/DS/SDC/Harman).
