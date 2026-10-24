# 계장도서검토 — 대시보드 메뉴 연결 안내 (DASHBOARD 작업자용)

이 폴더(`dashboard/apps/books/`)와 `dashboard/books_api.py` 는 **코드만** 개발한 것이다. 대시보드 업데이트 zip(`dashboard_tools/make_patch.py`)에 넣는 일은 DASHBOARD 세션에서 한다.
연결 방식은 판넬 공간확보(`space`)와 같은 **방법 A' — `APP_ROUTES`** (DASHBOARD_ARCHITECTURE.md 7장) + 공용 도서관용 API 하나(`/api/books/…`).

## 1. 넣을 파일

| 저장소 | 운영 폴더 | 내용 |
|---|---|---|
| `dashboard/apps/books/index.html` | `apps\books\index.html` | 화면 + 검색 엔진 + 계장 용어 사전 · 한영 용어집 (한 파일) |
| `dashboard/apps/books/kb.js` | `apps\books\kb.js` | 발전 · 플랜트 계장 지식 베이스 (터빈 · HRSG · DCS · PLC · 펌프 · 설계 산출물 · 써모웰 · 게이지 · 스위치 · 차단 밸브 · MOV · 국제 규격 … 개념 49개 + 분야 15개) 와 **학습 지식 노트**(`notes`: 개념별 [출처, 요약] 118개) — index.html 이 `<script src="kb.js">` 로 읽음, 없으면 기본 사전만으로 동작 |
| `dashboard/apps/books/vendor/pdf.min.js`, `pdf.worker.min.js` | `apps\books\vendor\` | pdf.js 3.11.174 (Apache-2.0) — P&ID 도구와 같은 파일 |
| `dashboard/books_api.py` | `books_api.py` (server.py 옆) | 공용 도서관 API — 표준 라이브러리만 |

`tools/books_sim/` (시뮬레이션 도구 · 질문 · 라벨)은 개발용이라 **넣지 않는다**.

## 2. 고칠 곳

### ① server.py (`SERVER_VERSION` 올림 → 재시작)
```python
import books_api                                            # 맨 위 import 들 옆

def main():
    books_api.setup(P=P, LOCK=LOCK, ApiError=ApiError, read_json=read_json, write_json=write_json)   # main() 첫 줄
    ...

# Handler.api() 안, 다른 head 분기들 사이 (예: if head == 'space': 바로 위)
        if head == 'books':                                         # 계장도서검토 공용 도서관
            return books_api.handle(self, m, seg[1:], q)

MENUS = [ … ('space', '판넬 공간확보'), ('books', '계장도서검토'), … ]
VOC_MENUS = ( … 'space', 'books', … )
```
- 실제 server.py(2026-10-23.1) 사본에 위 줄들을 넣고 `--root <시험 폴더> --port 8790` 으로 띄워 API · 화면 · 색인 · 검색을 끝까지 시험함.
- `books_api` 가 쓰는 Handler 메서드: `is_admin() · is_super() · need_user() · json_body() · raw_body() · send() · cors() · send_response/send_header/end_headers/wfile` (모두 지금 server.py 에 있음).
- 요청 크기 상한 `MAX_BODY`(30 MB)는 그대로 둬도 됨 — 책 1권 색인은 gzip 으로 보통 1 MB 이하.

### ② dashboard.html (`APP_VERSION` 올림)
```js
const APP_ROUTES = { space:{ title:'판넬 공간확보', src:'/apps/space/index.html' },
                     books:{ title:'계장도서검토', src:'/apps/books/index.html' } };
const ROUTES = [ … 'space', 'books', 'mgmt', … ];
// renderMenu(): 판넬 공간확보 줄 아래
    (can('books') ? btn({ k:'books', l:'📚 계장도서검토', n:'', c:0 }, 'top') : '') +
// QF_MENUS (Ctrl+K 빠른 찾기): ['space', '판넬 공간확보'] 뒤
  ['books', '계장도서검토'],
```
- `renderApp` 의 iframe 에 `sandbox` 속성을 붙이지 말 것 (새 창 · 원본 열기 · 복사가 막힘). 지금은 없음.
- `appAuth()` 가 보내는 `dept-auth`(토큰 · 본명)를 받아 **공용 도서관 관리 권한 확인**에만 씀.

## 3. 공용 도서관 — 운영 방법

1. 서버 PC(localhost)에서 대시보드 → 📚 계장도서검토 → **[📚 도서관]** → '서버 PC 의 도서 폴더 경로' 에 예) `D:\계장도서` → [경로 저장].
2. **[🔄 색인 갱신]** — 이 브라우저가 서버 폴더의 책을 받아 본문을 뽑아 서버에 올림. 시험: 63권 · 12,232쪽 · 153 MB → **약 2분**. 다음부터는 새로 넣거나 바뀐 파일만 (바뀐 것이 없으면 3초).
3. 부서원은 메뉴를 열면 바로 공용 도서관을 검색 (첫 접속 때 색인을 내려받아 그 PC 에 보관 → 이후 즉시). 원본 미리보기는 서버에서 받아 봄.

| 항목 | 내용 |
|---|---|
| 권한 | 폴더 지정 · 색인 = 운영자(서버 PC) · 그룹장(`SUPER_NAMES`) · `books/config.json` 의 `managers`(본명 목록). 보기 · 검색 · 원본 = 다른 GET 처럼 사내망 누구나 |
| 저장 | 운영 폴더 `books/config.json`(경로 · 관리자 · 번역 설정) · `books/index/<id>.json.gz`(책 1권 색인) · `books/index/manifest.json`(목록) · `books/tcache/`(번역 보관) |
| 백업 | `books/` 는 지금 `make_backup` 목록에 없음 — 색인은 [전체 다시 색인]으로 다시 만들 수 있어 넣지 않아도 됨 (넣으려면 `'books'` 추가) |
| 보안 | 원본은 지정 폴더 **안**의 지원 형식(pdf · epub · docx · hwpx · txt · md)만, `..` 경로 · 폴더 밖 경로 거부 (시험함) |
| API | `GET books/info · files · file?rel= · manifest · book/<id>` / `PUT books/root · book · manifest · translate-config` / `POST books/translate` |

### 번역 (엔진 셋 — '자동' 은 ① → ② → ③ 순으로 되는 것)
| 엔진 | 품질 | 외부 전송 | 조건 |
|---|---|---|---|
| ① Claude (서버 경유) | 가장 정확 · 계장 용어집 적용 · 영/포/스/러/베트남어 → 한국어 | **고른 글(그 쪽 · 고른 부분)이 Anthropic 으로** | **운영자가 켜야 함 (기본 꺼짐)** · API 키 · 로그인한 부서원만 |
| ② 브라우저 내장 번역 | 일반 기계번역 | 없음 (PC 안 모델) | 최신 Edge/Chrome 의 Translator API — 처음 한 번 언어 모델 받기 (폐쇄망이면 안 될 수 있음) |
| ③ 용어 풀이 | 원문 그대로 + 계장 용어 206개 한글 뜻 | 없음 | 항상 |

- 켜기: 서버 PC(localhost)에서 [📚 도서관] → 🌐 번역 → 'Claude 번역 사용' + API 키 → 저장 (`PUT books/translate-config`, 운영자만). 키는 `books/config.json` 에만 있고 화면 · `info` 에 나오지 않음. 서버 환경 변수 `ANTHROPIC_API_KEY` 로도 줄 수 있음.
- 서버 PC 에서 `api.anthropic.com` 으로 나가는 길이 막혀 있으면 "번역 API 에 연결하지 못했습니다" 로 안내되고 ② · ③ 으로 넘어감.
- 요청: Messages API (`claude-opus-5-5` 기본, effort `low`, 고정 지시 · 용어집은 프롬프트 캐시, 정책상 거절 시 `fallbacks: "default"`). 같은 글은 `books/tcache/` 에 보관해 다시 보내지 않음 (부서원끼리 공유). 한 번에 12,000자까지, 동시에 3건.
- 화면: 미리보기 [🌐 번역] = 그 쪽을 원문 옆에 나란히(쪽을 넘기면 따라 번역) · 글을 끌어 고르면 [🌐 번역 · 📋 복사] 단추 · 근거 구절 옆 🌐. 번역 결과는 그 PC 에도 보관.

### 내 PC 폴더 (개인용, 서버 없이도)
[📚 도서관] → [💻 내 PC 폴더] → [📁 폴더 선택]. 파일은 서버로 가지 않고 그 PC 브라우저 안에서만 읽음.
`http://PC이름:8080` 처럼 보안 컨텍스트가 아닌 주소에서는 Edge 가 "업로드할까요?" 라고 묻지만 실제 업로드는 없음(첫 화면 안내 있음).

## 4. 동작 요약

- 주소 뒤 값: `?embed=1` 이면 앱 자체 제목을 숨김. `?q=검색어` 로 바로 검색.
- 새 창: 미리보기 [⧉ 새 창] = `?viewer=1&sig=…&p=…&q=…&f=…&src=srv|local`, 연관 검색 창 = `?related=1&t=낱말&sig=…&q=…&src=…`. 공용 도서관이면 원본을 서버에서, 내 PC 폴더면 처음 창(opener)에서 빌림.
- 복사: 보안 컨텍스트면 `navigator.clipboard`, 아니면 `execCommand('copy')` — iframe 에 `allow` 속성이 없어도 동작.
- IndexedDB `gyejang-books` 는 주소(origin)별 — `http://PC이름:8080` 과 `http://IP:8080` 을 번갈아 쓰면 색인 사본이 두 벌 (공용 도서관은 다시 내려받기만, 수 초).
- Edge/Chrome 103 이상 (`DecompressionStream` / `CompressionStream`).

## 5. 지원 형식 · 한계

- PDF(글자 있는 것) · EPUB · DOCX · **XLSX/XLSM**(시트 = 쪽, 행은 `|` 로 이어 붙임) · **PPTX**(슬라이드 = 쪽, 제목은 목차로) · HWPX · TXT(UTF-8/CP949/UTF-16) · MD · CSV.
- 옛 형식 **DOC · XLS · PPT · HWP(5.0)** 는 본문을 읽지 않고 **파일명으로만** 찾음 ([📚 도서관] '본문을 읽지 못한 파일' 에 '옛 형식' 으로 표시 — 새 형식으로 저장하면 본문도 읽힘). `books_api.py` 의 `SUPPORTED` 에도 같은 확장자가 있어야 서버가 목록 · 원본을 내려 준다.
- 글꼴 인코딩이 깨진 PDF(글자가 다른 글자로 뽑히는 것)는 '본문 깨짐' 으로 표시 — 다시 받거나 OCR 후 저장.
- 스캔(그림)만 있는 PDF 는 파일명 · 책갈피로만 찾음 ([📚 도서관] 의 '본문을 읽지 못한 파일' 목록).
- AI 모델 없이(사내 정책) 찾음: 계장 용어 사전(개념 50개 · 표현 약 700개) + 발전 · 플랜트 지식 베이스 `kb.js`(개념 42개 · 표현 약 1,300개 · 핵심 하위 항목) + 관점 11개 + 한영 일반 기술 용어집(약 250개) + BM25. 사전 · 용어집에 없는 다른 말(동의어)은 넓히지 못함 → `kb.js` 에 개념 한 줄, 또는 `index.html` 의 `THES_ADD` · `GLOSS_SRC` 에 표현 한 줄 추가. 품질 시험 방법은 `tools/books_sim/SIMULATION.md`.
- **💬 답변 상자** (결과 맨 위): 질문에 대한 답을 두 상자로 나눠 보여 준다. ① **📂 폴더 도서 근거** — 지정 폴더(공용 도서관 또는 내 PC 폴더)의 상위 도서에서 질문의 주제 개념이 실제로 나오는 문장을 **원문 그대로** 인용하고 `[#도서 번호] 파일명 · 쪽` 을 붙임(누르면 그 쪽, 📋 는 출처 포함 복사). ② **🧠 학습 지식** — `kb.js` 의 `notes` 에 적힌 규격 · 제작사 자료 요약(출처 표시)으로, 폴더와 무관한 내장 지식임을 상자 제목에 명시. 학습 지식의 출처 규격이 폴더에 있으면 '📂 폴더에 있음: #번호' 로 이어 준다. 폴더가 없거나 폴더에 관련 책이 없으면 그 사실을 ①에 적고 ②만 보여 준다.
- **도서 번호 `#N`**: 폴더 안 경로 순(가나다 · ABC)으로 1부터 매김 — 결과 행 · 미리보기 · 도서관 목록 · 바로 볼 곳 · 인용 복사(`— [#12] 파일명, p.34`)에 모두 같은 번호. 책이 추가 · 삭제되면 번호가 바뀔 수 있으므로 인용에는 파일명을 함께 둔다.
- 시니어 관점 설명: 책마다 **종류**(교재 · 매뉴얼 · 규격 · 설계 문서 · 목록 · 법규 · 강의 · 노트 · 보고서 · 일반 도서)와 **분야**를 본문 특징으로 자동 판단하고, '왜 관련 있나' 에 🧭 핵심 항목 n/m · 🔗 연관 주제 · 📚 종류 · 분야 · 💡 한 줄 조언을 붙인다. 결과 위에 **📚 추천 읽기 순서**(① 원리 · 개요 → ② 실무 → ③ 규격 · 법규)를 보여 준다. 판단이 틀린 책이 있으면 `profileBook()` 의 제목 · 본문 규칙에 한 줄 추가.
