# 계장도서검토 — 대시보드 메뉴 연결 안내 (DASHBOARD 작업자용)

이 폴더(`dashboard/apps/books/`)는 **코드만** 개발한 것이다. 대시보드 업데이트 zip(`dashboard_tools/make_patch.py`)에 넣는 일은 DASHBOARD 세션에서 한다.
연결 방식은 판넬 공간확보(`space`)와 같은 **방법 A' — `APP_ROUTES`** (DASHBOARD_ARCHITECTURE.md 7장).

## 1. 넣을 파일 (운영 폴더 `apps\books\`)

| 파일 | 내용 |
|---|---|
| `index.html` | 화면 + 검색 엔진 + 계장 용어 사전 (한 파일, 외부 의존성 없음) |
| `vendor/pdf.min.js`, `vendor/pdf.worker.min.js` | pdf.js 3.11.174 (Apache-2.0) — P&ID 도구(`pid-instrument-tool/web/vendor/`)와 같은 파일 |

서버(`send_app_file`)가 `/apps/books/` 로 그대로 제공한다 — **server.py 코드 변경 없이도 동작**(아래 2-②는 권한 표에 넣기 위한 것).

## 2. 고칠 곳

### ① dashboard.html (`APP_VERSION` 올림)
```js
const APP_ROUTES = { space:{ title:'판넬 공간확보', src:'/apps/space/index.html' },
                     books:{ title:'계장도서검토', src:'/apps/books/index.html' } };
const ROUTES = [ … 'space', 'books', 'mgmt', … ];
// renderMenu(): 판넬 공간확보 줄 아래
    (can('books') ? btn({ k:'books', l:'📚 계장도서검토', n:'', c:0 }, 'top') : '') +
// QF_MENUS (Ctrl+K 빠른 찾기): ['space', '판넬 공간확보'] 뒤
  ['books', '계장도서검토'],
```

### ② server.py (`SERVER_VERSION` 올림 → 재시작)
```python
MENUS = [ … ('space', '판넬 공간확보'), ('books', '계장도서검토'), … ]
VOC_MENUS = ( … 'space', 'books', … )
```
기본 권한은 `DEFAULT_PERMS` 규칙대로 전원 허용(mgmt 만 비허용).

## 3. 동작 요약 (대시보드 쪽에서 알아야 할 것)

- 주소 뒤 값: `?embed=1` 이면 앱 자체 제목(📚 계장도서검토)을 숨긴다. `user` 등 다른 값은 쓰지 않는다. 로그인 토큰(`dept-auth` postMessage)도 쓰지 않는다 — **서버 API 를 전혀 호출하지 않는다.**
- 도서 파일은 부서원 PC 브라우저 안에서만 읽는다. 뽑은 본문(색인)은 그 PC 의 IndexedDB `gyejang-books` 에 보관 → 서버 저장 공간·백업과 무관.
- 폴더 고르기
  - `http://PC이름:8080` 처럼 보안 컨텍스트가 아닌 주소(부서원 대부분)에서는 `<input webkitdirectory>` 를 쓴다. Edge 가 "파일 N개를 이 사이트에 업로드할까요?" 라고 묻지만 실제 업로드는 없다(첫 화면에 안내 문구 있음). 끌어다 놓기도 된다.
  - `http://localhost:8080`(서버 PC)에서는 `showDirectoryPicker` 로 폴더 권한을 기억해 다음 접속 때 [폴더 다시 연결] 한 번으로 이어진다.
  - 폴더를 다시 고르지 않아도 **보관된 색인으로 바로 검색**된다. 원본 쪽 그림 미리보기·원본 열기·새 파일 반영만 폴더 연결이 필요하다.
- IndexedDB 는 **주소(origin)별**이다. 같은 부서원이 `http://PC이름:8080` 과 `http://65.3.30.234:8080` 으로 번갈아 들어오면 색인을 두 번 만든다(기능 문제는 없고 첫 인덱싱 시간만 다시 듦).
- 1분 자동 갱신 때 iframe 을 다시 만들지 않는 `APP_ROUTES` 틀이라 검색 중인 화면이 유지된다.
- Edge/Chrome 103 이상 필요(`DecompressionStream('deflate-raw')` — EPUB·DOCX·HWPX 풀기).

## 4. 지원 형식 · 한계

- PDF(글자 있는 것) · EPUB · DOCX · HWPX · TXT(UTF-8/CP949/UTF-16) · MD.
- 스캔(그림)만 있는 PDF 는 글자가 없어 파일명·책갈피로만 찾는다(목록에 "글자 없음" 표시).
- 옛 HWP(5.0 바이너리)는 아직 읽지 않는다 — 필요하면 HWPX 로 저장해 넣는다.
- 검색은 사전 기반(계장 용어 사전 + BM25)이다. 사전에 없는 분야의 동의어는 스스로 넓히지 못한다 → 사전 보강은 `index.html` 의 `THES` 배열에 한 줄 추가.
