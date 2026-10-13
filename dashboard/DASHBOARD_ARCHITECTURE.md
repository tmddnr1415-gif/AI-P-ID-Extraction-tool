# 계장ENG그룹 주간업무 Dashboard — 구조 안내 (다른 Claude Code 작업자용)

이 문서는 이 프로그램을 처음 보는 Claude Code 가 구조를 파악하고, **별도로 개발한 프로그램을 메뉴(입찰 프로젝트 / 실행 프로젝트 등)에 연결**할 수 있도록 정리한 것이다.
기준 버전: 화면 `APP_VERSION 2026-10-09.3`, 서버 `SERVER_VERSION 2026-10-09.2` (2026-10-09).
- 메뉴 권한: 사이드바 MENU 옆 ⚙(운영자=서버 PC localhost 만 표시) → 사용자·비회원 × 메뉴(weekly/pid/bidpjt/runpjt/board/mgmt) 체크. 기본 전부 허용, **Management(mgmt) 만 기본 비허용**. 저장: `accounts/_perms.json`, API: GET/PUT `admin/perms`(운영자만), 각 계정 권한은 `info.perms`·`auth/ping.perms` 로 전달(30초 안에 반영). 서버는 쓰기 API 에서 메뉴 권한도 확인(주간업무보고 쓰기=weekly, 게시판 쓰기=board → 403).
- 주간업무보고 하위 시트 `issue`(프로젝트 이슈사항): 사업군/PJT명/담당자/이슈사항/첨부파일/종결현황/Remark/AI 요약. 첨부파일은 PUT `files?name=`(pdf·ppt·pptx, 30MB, 로그인+weekly) → `files/{fid}.{ext}`+`files/{fid}.json`, 칸 값은 줄마다 `파일명 [fid]`, GET `files/{fid}` 로 열기. AI 요약은 현재 화면 안의 문장 추출 방식(`issueSummary`, 외부 전송 없음).
- 서버는 요청 본문을 읽지 않고 응답해도 남은 본문을 비움(keep-alive 연결 깨짐 방지, `dispatch`).
현재 위치: `C:\Claude\계장ENG그룹 주간업무 Dashboard\` (코드와 운영 데이터가 같은 폴더. 2장의 Desktop 경로는 옛 구조). 수정 전 백업은 이 폴더의 `backup\파일명_YYYYMMDD_HHMM.*`.

---

## 1. 한눈에 보기

- 엑셀 "계장ENG그룹 주간 업무 보고"를 대체하는 부서 주간업무 입력·조회 웹 프로그램.
- **단일 HTML 파일(`dashboard.html`)** + **Python 표준 라이브러리만 쓰는 서버(`server.py`)**. 빌드 도구·npm·CDN·외부 라이브러리 없음.
- 데이터는 DB 없이 **JSON 파일**(행 1개 = 파일 1개)로 운영 폴더에 저장.
- 서버는 부서장 PC(Windows, `ASEUNGWOOK-B01`, `65.3.30.234`, 포트 **8080**)에서 실행. 부서원은 `dashboard.html` 사본을 각자 PC에서 **Edge 로 file:// 실행**해 서버 API에 접속.
- **계정 로그인**(서버 모드): 첫 화면에서 로그인 / 계정 개설(ID·본명·비밀번호·메일·생년월일) / 비회원 보기. **모든 쓰기 API의 수정자(`by`)는 서버가 로그인 토큰으로 확인한 본명**으로 기록(브라우저가 보낸 by 는 무시). 비회원은 보기 전용. 관리자 기능은 여전히 서버 PC의 localhost 접속 시만(로그인도 필요). 폴더 모드만 예전처럼 이름 입력.
- 사이드바 위쪽에 계정 표시(이름 ▼ → 로그아웃). 오른쪽 '내 업무' 툴바에 사용자 목록(접속 중 녹색 ●, 오프라인 회색)과 쪽지.
- UI는 전부 한국어.

### 제약 (반드시 지킬 것)
| 항목 | 내용 |
|---|---|
| 외부 의존성 | **금지**. CDN, npm 패키지, pip 패키지 사용 불가 (사내 보안 정책, pip 설치 불가 환경) |
| Python | 3.11, 표준 라이브러리만 (`http.server`, `json`, `zipfile`, `ipaddress` …) |
| 브라우저 | Edge/Chrome (File System Access API, IndexedDB 사용) |
| JS 검사 도구 | 이 PC에는 **Node.js 없음** → JS 문법 검사 불가. 수정 후 코드를 다시 읽어 검토하고, 사용자가 Edge로 확인 |
| 보안 | 사내 기밀 데이터. 외부 서비스로 전송 금지. 서버는 사내망(사설망 + 65.3.0.0/16)만 허용 |

---

## 2. 폴더 구성

```
C:\Users\SAMSUNG\Desktop\Claude\                         ← 개발 폴더 (여기서 수정)
├─ dashboard.html            화면 전체 (HTML+CSS+JS 한 파일, 약 2,300줄)
├─ server.py                 REST API 서버 + 정적 파일 + 자동 백업/주간 마감/배포 파일 생성
├─ watchdog.py               server.py 감시·자동 재시작 (pythonw 로 창 없이 실행)
├─ start_server.bat          수동 실행 (포트 8080, 브라우저 자동 열기)
├─ install_autostart.bat     작업 스케줄러(로그온 시) 등록 → watchdog.py 실행
├─ uninstall_autostart.bat   등록 해제 + 프로세스 종료
├─ migrate_xlsx.py           엑셀 → JSON 1회 이관 스크립트 (표준 라이브러리로 xlsx 직접 파싱)
├─ fix_notice.py             주간회의 전달사항 재정리(1회용, 이미 적용 완료)
├─ deploy_backup\            운영 폴더에 배포하기 전 이전 버전 백업
└─ 계장ENG그룹 주간업무 Dashboard\                         ← 운영 폴더 (서버가 실제 사용)
   ├─ dashboard.html, server.py, watchdog.py, *.bat      코드 (개발 폴더에서 복사해 배포)
   ├─ 계장ENG그룹 주간 업무 보고_26.10월1주차.xlsx         원본 엑셀
   ├─ data\{시트키}\{행ID}.json      ★ 실제 업무 데이터 (행 단위)
   ├─ data\_meta\state.json          마감 상태(lastClosedAt/lastClosedWeek, 전체 저장 정보)
   ├─ data\_meta\staffing-columns.json   투입인력 PJT 열 정의
   ├─ history\{시트키}\{행ID}\{시각}_{이름}.json   수정 이력 (7일 보관 후 자동 삭제)
   ├─ trash\{시트키}\{행ID}.json     휴지통 (복구 가능)
   ├─ archive\YYYY-Www.json          주간 마감본 (매주 수 12:00 자동, 수요일 11:59 기준)
   ├─ saves\전체저장_*.json / .xlsx  [전체 저장] 결과
   ├─ board\{글ID}.json              익명게시판
   ├─ backup\YYYY-MM-DD.zip          일일 자동 백업 (60일 보관)
   ├─ deploy\dashboard.html, 부서원_사용법.txt   부서원 배포본 (서버가 자동 생성)
   ├─ apps\                          ★ 연결 프로그램 정적 파일 자리 (/apps/… 로 제공)
   └─ server.log, watchdog.log
```

> ⚠️ **운영 폴더의 데이터 폴더(data, history, trash, archive, saves, board, backup, apps 안의 데이터)는 절대 덮어쓰거나 지우지 않는다.** 코드 파일만 개발 폴더에서 복사한다.

---

## 3. 실행 모드 (dashboard.html 이 스스로 판단)

| 열린 방식 | 모드 | 동작 |
|---|---|---|
| `http://localhost:8080/` (서버 PC) | 서버 모드 + **관리자** | API 사용. 금주 마감·휴지통 영구삭제 표시 |
| `http://PC이름:8080/` 등 | 서버 모드 | API 사용 |
| `file:///…/dashboard.html` (부서원 PC) | 서버 모드(원격) | `DEFAULT_SERVERS` = [PC이름 주소, IP 주소] 순서로 접속 시도. 사용자가 [서버 주소 설정]으로 바꾸면 localStorage `dept-server-url` 사용 |
| file:// 인데 서버 연결 실패 + 보관본 있음 | **오프라인 모드** | IndexedDB 보관본 표시, 수정은 대기열에 저장 → 30초마다 재연결, 연결되면 자동 업로드(충돌 시 선택창) |
| file:// + 서버 실패 + 보관본 없음 | 안내 화면 | [다시 시도] [서버 주소 변경] [폴더 모드로 열기] |
| 폴더 모드 (구버전 방식) | File System Access API | 공유폴더를 직접 선택해 JSON 읽기/쓰기. 서버 없이 동작 (잠금 없음) |
| VS Code Live Preview 등 `/api` 없는 서버 | 안내 화면 | "서버로 접속하세요: http://localhost:8080" |

- 서버가 배포본(`/dashboard.html`, `deploy\dashboard.html`)을 줄 때 `const DEFAULT_SERVERS = [...]` 줄을 이 PC 기준 주소로 **치환**한다 (`server.py: html_bytes()`).
- 화면 버전(`APP_VERSION`)이 서버의 dashboard.html 버전과 다르면 file:// 사본에 "새 버전 [다운로드]" 배너 (`/dashboard.html?download=1`).

---

## 4. 데이터 모델

### 4.1 시트 (메뉴: 주간업무보고 하위 9개)
| 키 | 메뉴명 | 주요 필드 (fields 의 키, 한국어 그대로) |
|---|---|---|
| perform | 수행 | 사업군, PJT명, PJT 개요, PJT 주요 일정, 담당자, 업무 현황, 현안 |
| bid | 입찰 | (수행과 동일) |
| rnr | PJT R&R | 구분(수행/입찰), 사업군, PJT명, 담당자, 역할(LE/RE/LE (PMO)), 시작일, 종료일, 설계공정률, Remarks |
| general | 일반업무 | 구분, 소구분, 업무 내용, 책임자, 시작일, 종료일, 진행사항 |
| unit | 유닛분장 | 연도, 유닛, 그룹장, 구성원, 담당, 수행 PJT, 입찰 PJT |
| techshare | 기술공유 | 연도, 발표 내용, 발표자, 발표일 |
| todo | To do list | 구분, 소구분, 지시 사항, Issue Date, Target Date, PO, 완료 여부(O/△/X), 현황, 그룹장 추가요청 사항 |
| staffing | 계장 투입인력 | 그룹, 분야, 이름, 과제+기타업무(%), Remarks, **배정**: `{열ID: {pct:숫자, role:'LE'|'RE'}}` (매트릭스 화면) |
| notice | 주간회의 전달사항 | 일자(YYYY-MM-DD), 제목, 내용 — 화면·엑셀 모두 **일자 내림차순(최신이 위)** |

시트 정의는 `dashboard.html` 의 `const SHEETS = [...]` (열 순서·너비·여러 줄 여부 `long`·날짜 `date` 등).

### 4.2 행 레코드 (`data/{시트키}/{ID}.json`)
```json
{
  "id": "perform-0001",            // 이관분: 시트-0001, 새 행: 시트-<시간36진><랜덤>
  "sheet": "perform",
  "order": 10,                      // 표시 순서 (그룹 사이에 끼울 때 소수 가능)
  "fields": { "PJT명": "...", "업무 현황": "여러 줄\n텍스트" },
  "meta": {
    "createdBy": "엑셀이관", "createdAt": "...",
    "updatedBy": "백승욱", "updatedAt": "2026-10-07T07:54:18.585Z",   // UTC ISO (밀리초+Z)
    "rev": 3,                        // 저장할 때마다 +1 → 동시 수정 충돌 감지
    "changes": { "업무 현황": "<ISO>" },   // 필드별 마지막 변경 시각
    "orig": { ... }, "origSince": "<lastClosedAt>"   // 마감 이후 첫 수정 직전 내용(파란 글씨 비교용)
  }
}
```
- 텍스트 안의 `~~내용~~` = **삭제 표시(붉은 취소선)**. 저장 데이터에 실제로 들어 있음. 한 번 더 지우면 완전 삭제 (`mergeStrike`).
- "추가된 내용(파란 글씨)" 표시는 저장 데이터에 넣지 않고 화면에서 계산 (`markAdded`, 내부 표식 `\uE000…\uE001`).
- 수정자 `엑셀이관` = 이관/정리 작업 (변경 표시·최근 이력에서 제외).

### 4.3 기타 파일
| 파일 | 내용 |
|---|---|
| `data/_meta/staffing-columns.json` | `{columns:[{id, name, kind:'수행'|'입찰'|'기타'}]}` |
| `data/_meta/state.json` | `lastClosedAt`, `lastClosedWeek`, `closedBy`, `lastFullSaveAt/By/File` |
| `archive/YYYY-Www.json` | `{week, closedAt, closedBy, auto, cutoff, sheets:{시트키:[레코드…]}, staffingColumns}` |
| `history/…/{at}_{이름}.json` | `{sheet, rid, action(create/update/overwrite/delete/restore/purge), by, at, label, before, after, changed[]}` |
| `trash/{시트}/{ID}.json` | 레코드 + `meta.deletedBy/deletedAt` |
| `board/{ID}.json` | `{id,title,body,nick,createdAt,updatedAt,tokenHash,comments:[{id,body,nick,createdAt,tokenHash}]}` — 실명 저장 안 함 (쓰기는 로그인 필요, 계정과 연결하지 않음) |
| `accounts/{ID}.json` | `{id, name(본명), salt, hash(PBKDF2-SHA256 20만 회), rsalt, rhash(메일+생년월일 확인용 해시), createdAt, pwChangedAt}` — 비밀번호·메일·생년월일 원문 저장 안 함 |
| `accounts/_sessions.json` | `{sha256(토큰): {id, at}}` 로그인 세션 30일 (서버 재시작해도 유지) |
| `messages/{ID}/in\|sent/{쪽지ID}.json` | `{id, from, fromName, to, toName, body, at, read, readAt}` 쪽지, 180일 후 자동 삭제 |

### 4.4 주차·마감 규칙
- **수요일 오전 11:59까지 = 그 주 데이터, 수요일 12:00부터 = 다음 주.** 표기 `2026-W41(1007)` (= ISO 주차 + 그 주 수요일 MMDD).
- 서버가 매주 수 12:00 `archive/` 에 자동 저장(`auto_close`). 서버가 꺼져 있었으면 켜진 뒤 이력(7일)으로 마감 시점 데이터를 복원해 저장(`snapshot_at`).
- **변경 표시(노란 음영 / NEW(n) / 파란 글씨)** 의 기준 = 마지막 마감본(`state.lastClosedWeek`)과 필드 단위 비교 (`hlOf`, `isUpdated`, `baseFieldsOf`).

---

## 5. 서버 API (`server.py`, 모두 JSON, 경로 앞 `/api/`)

| 메서드 · 경로 | 설명 |
|---|---|
| GET `info` | `{mode:'server', admin, week, version(화면), serverVersion, urls, host}` |
| GET `all` | `{recs:{시트:[레코드]}, cols, state, archives:[주차…]}` |
| GET `rec/{시트}/{id}` | 행 1개 (없으면 404) |
| POST `rec/{시트}` | 새 행 `{fields, id?, order?, by}` |
| PUT `rec/{시트}/{id}` | 수정 `{fields, baseRev, force?, action?, by}` → `{status:'ok'|'conflict'(+cur)|'deleted'|'nochange'}` |
| DELETE `rec/{시트}/{id}?by=` | 휴지통으로 이동 |
| GET `trash` · POST `trash/{시트}/{id}/restore` · DELETE `trash/{시트}/{id}`(관리자) | 휴지통 |
| GET `history/{시트}/{id}` · GET `recent` | 이력 |
| GET `archive/{주차}` | `{arch, prev}` (직전 마감본 포함) |
| POST `close`(관리자) | 수동 주간 마감 |
| POST `columns` | 투입인력 PJT 열 추가 |
| POST `saveall` · PUT `saves?tag=` | 전체 저장(JSON) · 엑셀 파일 업로드 |
| GET/POST/PUT/DELETE `board…` | 익명게시판 (토큰 해시로 본인 확인, 로그에 IP 미기록) |
| GET `/`, `/dashboard.html[?download=1]` | 화면 (기본 서버 주소 치환) |
| GET `/apps/…` | **연결 프로그램 정적 파일** (운영 폴더 `apps/`, 상위 경로 접근 403) |
| POST `auth/register` · `auth/login` · `auth/reset` · `auth/logout`, GET `auth/me` | 계정. 로그인 응답 `{token, user:{id,name}}`, 이후 요청 헤더 `X-Auth-Token`. 로그인·재설정 5회 실패 시 10분 잠금 |
| POST `auth/ping` | 접속 표시 갱신(화면이 30초마다) → `{users:[{id,name,online}], unread}`. 75초 안에 요청이 있었으면 online |
| GET `msg` · POST `msg` `{to, body}` · POST `msg/{id}/read` · DELETE `msg/in\|sent/{id}` | 쪽지 (로그인 필요) |

- 쓰기 API(rec, trash 복구/영구삭제, close, columns, saveall, saves, board 쓰기)는 **로그인 필요(401)**. GET 은 비회원도 가능.

- 모든 쓰기는 서버 내부 `LOCK`(RLock) 안에서 수행, 파일은 임시 파일 → `os.replace` 로 원자적 교체.
- 접속 제한: 클라이언트 IP 가 루프백·사설망·서버 /16 대역(`--allow` 추가 가능)이 아니면 403. `Origin` 헤더가 `null`(file://) 또는 서버 자신 주소가 아니면 403 (CORS 는 그 경우에만 허용 헤더 응답).
- 관리자 = 요청 IP 가 `127.0.0.1`/`::1`.
- 백그라운드 스레드: 1시간마다 백업·이력 정리, 30초마다 주간 마감 확인·`deploy/` 갱신.

---

## 6. dashboard.html 내부 구조

한 파일 안에 `<style>` → 화면 골격(사이드바 `#side`, 상단 `header.top`, 본문 `#content`, 대화상자 `#dlg`/`#dlg2`) → `<script>` (IIFE 하나). 스크립트 구역(주석 `/* ===== … */`) 순서:

| 구역 | 주요 내용 |
|---|---|
| 상수 / 시트 정의 | `SHEETS`, `SHEET`, `PALETTE`, `IMPORT_BY='엑셀이관'` |
| 유틸 | `esc`(HTML 이스케이프, **innerHTML 에 넣는 모든 값에 사용**), `flatten`, `diffPaths`, `recLabel`, `toast` |
| 파일 시스템 계층 / 서버 | `APP_VERSION`, `DEFAULT_SERVERS`, `api(method, path, body, raw)` (네트워크 오류 시 `err.offline=true`), 폴더 모드용 `sub/readJSON/writeJSON`, IndexedDB `kv()` |
| 상태 | `DB={recs, cols, state, archives, baseSheets, board, recent}`, `view`(주차 선택), `route`, `curWeek()`, `weekLabel()`, 변경 판정 `hlOf/isUpdated/baseFieldsOf` |
| 데이터 로드 | `loadAll()` — 모드별(오프라인/서버/폴더)로 DB 채움, 서버 모드에서 보관본 저장 `cacheSave()` |
| 저장 / 이력 / 삭제 / 복구 | `createRecord`, `saveEdit`(rev 비교), `deleteRecord`, `restoreFromTrash`, `addColumn`, `closeWeek` — 모드별 분기(서버 API / 오프라인 대기열 / 폴더) |
| 오프라인 모드 | `QUEUE`(IndexedDB 'queue'), `applyOp`, `offlineCreate/Update/Delete`, `trySync`, `syncOp`(충돌 선택창), 대기열 내보내기/가져오기 |
| 다이얼로그 | `openDlg`, `ask`(Promise 반환 확인창), 편집 `openEdit/openStaffEdit/submitRecord/afterSave`(충돌 처리), 이력/휴지통 |
| 렌더링: 공통 | `render()` = `renderMenu()` + `renderHeader()` + route 별 본문, 메뉴 정의 `ROUTES`, `validRoute`, `renderMenu` |
| 익명게시판 | `Board` 객체, `renderBoard` |
| **입찰/실행 프로젝트** | **`MODULES` + `renderModule()`** ← 연결 프로그램 자리 |
| 홈 | `renderHome` (KPI·SVG 차트·툴팁·팝업 `openPop`·메모), 접속 시 할 일 팝업 `showMyTodo`, 칸 이동 `jumpTo` |
| 시트 화면 | `renderSheet`, `drawTable`, `tableHtml`/`matrixHtml`, 셀 서식 `fmtText`(글머리·날짜·취소선·추가 표시), 셀 선택(Ctrl/Shift)·크기 조절 |
| CSV / 엑셀 | `exportCsv`, 순수 JS xlsx 생성(`zipStore`(무압축 ZIP+CRC32), `xlSheets`, `buildXlsx`) |
| 초기화 | `init()` IIFE: 모드 판정 → `startOnline()` / 오프라인 / `initFolderMode()` |

라우팅: `location.hash` (`#home`, `#perform`, …, `#bidpjt`, `#runpjt`, `#board`). `go(route)` 로 이동.
메뉴 구조: 📋 주간업무보고(= `home` 대시보드, 하위 9개 시트) / 📈 입찰 프로젝트(`bidpjt`) / 🏗 실행 프로젝트(`runpjt`) / 💬 익명게시판(`board`).
브라우저 저장소 키(localStorage): `dept-dashboard-user`(이름), `dept-server-url`, `dept-dashboard-layout`(열 너비 등), `dept-nav-weekly-open`, `dept-board-*`, `dept-todo-hide`. IndexedDB `dept-dashboard` / store `kv` (키: `root`, `cache`, `queue`).

---

## 7. ★ 새 프로그램 연결 방법 (입찰 프로젝트 / 실행 프로젝트 메뉴)

현재 두 메뉴는 **빈 화면("준비 중")** 이다. 연결 지점은 이미 만들어져 있다.

### 방법 A (권장): 독립 HTML 앱을 `apps/` 에 두고 iframe 으로 연결
1. 프로그램을 **정적 파일(HTML/JS/CSS)** 로 만든다. 외부 CDN·라이브러리 금지 (필요하면 파일로 동봉).
2. 운영 폴더에 넣는다: `계장ENG그룹 주간업무 Dashboard\apps\bidpjt\index.html` (실행 프로젝트는 `apps\runpjt\`).
   → 서버가 `http://<서버>:8080/apps/bidpjt/` 로 제공 (재시작 불필요).
3. `dashboard.html` 의 `MODULES` 에 경로만 넣는다:
   ```js
   const MODULES = {
     bidpjt: { title:'입찰 프로젝트', src:'/apps/bidpjt/index.html' },
     runpjt: { title:'실행 프로젝트', src:'' },
   };
   ```
4. iframe 주소에 쿼리로 넘어가는 값: `?user=<이름>&server=<서버 주소>&admin=1|0`. 연결 앱은 이 `server` 값으로 `/api/...` 를 호출하면 기존 데이터(예: `GET /api/all` 의 `recs.bid`, `recs.rnr`, `recs.staffing`)를 그대로 쓸 수 있다.
5. 서버가 꺼져 있거나 오프라인 모드면 "서버에 연결되어 있을 때만 사용할 수 있습니다" 안내가 나온다.
6. `APP_VERSION` 을 올리고 배포 (8장).

### 방법 B: 별도 서버로 도는 프로그램 (예: 다른 포트의 웹 앱)
- `src:'http://ASEUNGWOOK-B01:8000/'` 처럼 전체 주소를 넣으면 iframe 으로 표시된다.
- 해당 서버가 iframe 삽입을 막는 헤더(X-Frame-Options 등)를 보내면 표시되지 않는다 → 그 서버 설정 확인 필요.
- 주의: 이 PC의 **8000 포트는 P&ID 추출 도구(uvicorn)가 사용 중**. 대시보드는 8080.

### 방법 C: dashboard.html 안에 직접 화면 구현 (데이터가 이 대시보드와 긴밀할 때)
- `renderModule(c, key)` 대신 새 렌더 함수를 만들고 `render()` 의 분기(`else if (MODULES[route]) …`)에서 호출.
- 새 데이터가 필요하면 `server.py` 에 **별도 접두어 API**(예: `/api/pjt/...`)와 **별도 저장 폴더**(예: 운영 폴더 `modules/pjt/`)를 추가하고, 쓰기는 반드시 `with LOCK:` + `write_json()`(원자적 교체) 사용. 기존 `data/` 구조는 바꾸지 말 것.
- 기존 함수 재사용: `api()`, `esc()`, `openDlg()/ask()`, `toast()`, `fmtText()`, `jumpTo(시트, 행ID, 필드)`.

### 메뉴를 더 추가하려면
- `ROUTES` 배열과 `MODULES` 에 키 추가 → `renderMenu()` 의 메뉴 HTML 에 `btn({k:'<키>', l:'<아이콘 이름>', n:'', c:0}, 'top')` 한 줄 추가.

---

## 8. 개발·배포 규칙

1. 개발 폴더에서 수정 → 확인 → **운영 폴더로 코드 파일만 복사**.
2. 배포 전 운영 폴더의 기존 `dashboard.html`(·`server.py`)을 개발 폴더 `deploy_backup\dashboard_YYYYMMDD_HHMM.html` 로 백업 (롤백용).
3. `dashboard.html` 을 바꾸면 **`APP_VERSION` 을 올린다** (부서원 사본에 새 버전 안내가 뜨는 기준). `server.py` 를 바꾸면 `SERVER_VERSION` 을 올리고 **서버 재시작** 필요(작업 스케줄러 사용 중이면 `uninstall_autostart.bat` → `install_autostart.bat`, 또는 watchdog 이 재시작하도록 server 프로세스만 종료).
4. `deploy\` 는 서버가 `dashboard.html` 변경을 감지해 30초 안에 자동 갱신.
5. 서버 기능 시험은 **운영 데이터가 아닌 사본**으로: 운영 `data\` 를 임시 폴더로 복사 → `python server.py --root <임시폴더> --port 87xx --log x.log` → urllib 로 API 호출 → 프로세스 종료.
6. Python 파일은 `python -m py_compile` 로 문법 확인. JS 는 Node 가 없어 검사 불가 → 수정 부분을 다시 읽어 검토.
7. 엑셀 원본이 열려 있으면 `~$` 잠금 파일이 생긴다 → glob 시 `~$` 로 시작하는 파일 제외.

---

## 9. 알려진 한계

- 계정 인증은 있으나 비밀번호 재설정이 메일+생년월일 확인뿐(메일 발송 없음) → 이 정보를 아는 사람은 재설정 가능. 메일·생년월일까지 잊은 경우 서버 PC에서 `accounts\{ID}.json` 을 지우고 다시 개설.
- 비회원도 데이터 조회는 가능. 사내망·출처 제한이 조회에 대한 접근 통제.
- 폴더 모드로 직접 파일을 쓰는 사용자가 있으면 서버 잠금이 적용되지 않음 → 부서원은 서버 접속(또는 file:// 사본)만 사용.
- 주간 마감 복원은 이력 7일 범위 안에서만 정확.
- 입찰/실행 프로젝트 메뉴는 현재 빈 화면 (이전에 만들었던 PJT 카드 화면은 `deploy_backup\dashboard_20261008_*.html` 에 남아 있음).

---

## 변경 이력

> 새 변경은 이 아래에 날짜별로 덧붙인다. 각 항목: 무엇을·왜 / 바뀐 곳(함수 이름) / 확인한 것 / 회사에서 확인할 것.

### 2026-10-13 — 시트 화면에 엑셀식 열 필터 (APP_VERSION 2026-10-13.1 / SERVER_VERSION 그대로 2026-10-09.2)
- **무엇을**: 수행·입찰·이슈사항·R&R·일반업무·유닛분장·기술공유·To do·투입인력·전달사항 등 모든 시트 표의 각 열 머리글에 `▾` 버튼. 누르면 엑셀 자동 필터처럼
  ↑오름차순 / ↓내림차순 정렬, 이 열 필터·정렬 지우기, 값 검색(포함된 값만), (모두 선택) + 값별 체크 목록(건수 표시), 확인/취소.
  - 필터·정렬이 걸린 열은 버튼이 파란색(정렬이면 ↑/↓ 표시). 표 아래 "열 필터 n개 적용 중".
  - 목록 값은 다른 열 필터를 적용한 뒤 남은 행 기준 (엑셀과 같음). 값은 칸 전체 문자열 그대로, `~~취소선~~` 부분은 목록 표시에서만 뺌. 빈 칸 = "(빈 셀)".
  - 구분(group) 있는 시트(R&R·일반업무·유닛분장·기술공유·To do)는 정렬해도 구분 묶음 순서는 유지하고 묶음 안에서만 정렬.
  - 투입인력 매트릭스: 이름·그룹·분야·수행·입찰·Total·각 PJT 열(값 예: `60 (LE)`)·과제+기타·합계%·Remarks 모두 필터 가능.
  - 기존 위쪽 필터(사업군·담당자·검색 등)와 함께 걸린다(AND). [필터 초기화] 누르면 열 필터·정렬도 함께 풀림. 상태는 메모리에만(새로고침하면 풀림).
  - 결과 0건이어도 [열 필터 모두 지우기] 버튼이 나와 풀 수 있다. CSV 내보내기는 화면에 보이는 행·순서 그대로, 엑셀 내보내기(전체)는 영향 없음. 인쇄에는 ▾ 안 나옴.
- **바뀐 곳** (dashboard.html만): CSS `.cfb`, `#cfPop`, `table.m th.cfh` / 시트 화면 구역 새 함수 `colVal`, `cfLabel`, `cfCmp`, `cfSort`, `openCf`, `closeCf` + 문서 click/keydown(Esc)/scroll 리스너 / `filteredRecs(s, skipCf)` 에 열 필터 조건 추가, 끝에서 `cfSort` / `thR(ck, label, extra, key)` 4번째 인자가 있으면 ▾ 버튼(`cfBtn`) / `tableHtml`·`matrixHtml` 머리글에 시트 키 전달 / `drawTable` 0건일 때 지우기 버튼·적용 개수 표시. 상태: `fstate(key).cf`, `fstate(key).sort`.
- **확인한 것**: 가짜 샘플 데이터(임시 폴더, 저장소에 넣지 않음)로 server.py 를 띄워 Chromium 에서 수행(사업군=화공 → 3건, PJT명 내림차순), 입찰·R&R·To do·투입인력 버튼 표시, 투입인력 PJT 열 'LE' 검색 → 2건, 아무것도 안 고르고 확인 → 경고 후 창 유지, Esc 로 닫힘. 스크립트 오류 없음.
- **회사에서 확인할 것**: Edge 에서 실제 데이터로 긴 글 칸(업무 현황 등) 목록이 너무 길지 않은지, 셀 선택·편집·열 너비 드래그가 그대로 되는지.

### 2026-10-13 (2) — 통합 업무 · 유닛 조직도 · 내 정보 · PJT 종결 · 작성 가이드 · 연도 탭 (APP_VERSION 2026-10-13.2 / SERVER_VERSION 2026-10-13.1)
> **서버 재시작 필요** (server.py 변경: 프로필 API·폴더). dashboard.html 만 먼저 바뀌어도 화면은 열리고, 프로필만 안 보인다.

1. **통합 업무 (route `work`, 메뉴 '🚀 통합 업무')** — 일반업무·To do·기술공유를 한 화면으로 합침.
   - **데이터는 합치지 않았다**: 지금처럼 `data/general`, `data/todo`, `data/techshare` 에 따로 저장. 화면만 합쳐 보여 준다 (이관 위험·마감본·엑셀 내보내기 호환 때문). 세 시트는 사이드바에서 숨김(`SHEETS[].merged:1`)이지만 주소 `#general` `#todo` `#techshare` 와 홈 팝업 이동은 그대로 동작, 통합 화면의 [원본 시트 보기] 버튼으로도 간다.
   - 매핑 `WORK` (dashboard.html): 제목/담당/시작/종료/진행 칸 = general(업무 내용/책임자/시작일/종료일/진행사항), todo(지시 사항/PO/Issue Date/Target Date/현황), techshare(발표 내용/발표자/발표일/발표일/-).
   - **연도 탭**(전체·데이터 연도 + 2024·2025·올해 항상 표시), 유형 칩, KPI(완료율 링·진행·임박 7일·지연·완료·상시·종료일 미입력, 누르면 그 상태만), **부서원별 상·하반기 막대**(기준일 = 시작일, To do = Issue Date, 기술공유 = 발표일. 1~6월 상반기, 7~12월 하반기. 날짜 없으면 합계 옆 `+n`. 담당 칸에 여러 명이면 각자 1건), 종료 현황 막대 + '지금 챙길 업무'(지연·임박), 업무 목록(상태 순 정렬, 편집/이력/삭제는 원본 시트 레코드로).
   - **종료 구분** 새 필드 `종료 구분` = `기한`(종료일 추적) / `상시`(종료일 없음, 추적 안 함) / 빈 칸(자동: 종료일 있으면 기한, 없으면 상시. 기술공유는 기본 기한). 세 시트 cols 에 `{f:'종료 구분', endk:1}` 추가, 편집 창은 select. 상태 계산 `workItem()`: todo = 완료 여부 O→완료, 기한 지남→지연, 7일 이내→임박 / general = 종료일 지남→종료(완료) / techshare = 발표일 지남→발표 완료. 상태 `WST_*`.
   - 상태 `WS`(메모리). 함수: `WORK`, `workItem`, `renderWork`, `WST_ORDER/WST_LABEL`.
2. **유닛분장**: 연도 탭(기본 = 가장 최근 연도) + **🏢 조직도(기본) / 📋 표** 전환. `수행 PJT`·`입찰 PJT` 열 삭제(cols·엑셀 `XL.unit` 에서 제거. 기존 JSON 값은 그 행을 다시 저장할 때 없어짐, 이력에는 남음).
   - 조직도 `orgHtml/orgPill/orgClick`: 맨 위 = 그룹장 칸의 이름, 그 아래 유닛(유닛명·담당·인원) → 구성원 알약(사진·이름·직책·전화·PJT 칩). 구성원 칸은 줄/쉼표로 나누고 `이름(직책)` 이면 괄호 안을 직책으로 표시. 유닛 머리를 누르면 그 행 편집, 사람을 누르면 `openProfile`.
3. **내 정보 (프로필)** — 계정 메뉴(이름 ▼)에 '🙋 내 정보', 조직도 아래 버튼. 사진(브라우저에서 240×240 JPEG 로 잘라 줄임, `shrinkPhoto`), 전화번호, 담당 업무, 수행/입찰 PJT(진행 중 PJT명 체크). `openMyInfo`, `loadProfiles`, `profOf`(계정 본명 ↔ 구성원 이름을 `normName` 으로 맞춤). `DB.profiles` 를 오프라인 보관본(`cacheSave`)에도 저장.
   - **server.py**: `GET /api/profiles` (모든 계정 프로필, **전화번호는 로그인한 사람에게만**), `PUT /api/profile` (로그인 본인만, `{phone≤30자, duty≤100자, run[], bid[], photo:data URL(jpeg/png/webp, 400KB 이하)}`). 저장 `profiles/{ID}.json` (시작 시 폴더 생성, 일일 백업 zip 에 포함). 함수 `api_profiles`, `api_profile_put`, `prof_list`, `PHOTO_RE`, `PHONE_RE`.
   - 폴더 모드(서버 없음)에서는 프로필을 쓰지 않는다.
4. **수행·입찰 PJT 종결 여부**: 새 필드 `종결 여부` (`진행`/`종결`, 빈 칸 = 진행) 열 추가(`c.closed`), 표에 배지, 종결 행은 회색, 위쪽 '진행 상태' 필터. `isLive(r)`.
   - **홈**: 수행/입찰 PJT 수·사업군별·담당자별 차트·'이번 주 미업데이트 PJT'·내 업무(`myTasks`)에서 **종결 PJT 제외**. KPI '현안' **삭제** → '종결 PJT (집계 제외)' 로 바꿈. 'To do 미완료' KPI 는 통합 업무로 이동.
5. **작성 가이드** (행 추가 시): 긴 글 칸(이름·제목 칸 제외, `guideOn`)에 틀 `1. / - / - / 2. / -` (일정 칸은 `- YY.MM.DD :`) 을 미리 넣고, 편집 창 위에 가이드 상자(`GUIDE_BOX`), 칸마다 서식 버튼(1. - → ※ 들여쓰기 내어쓰기 틀, `guideBar/guideAct`), `Enter` = 같은 글머리 이어 쓰기(빈 글머리에서 Enter = 지움), `Tab`/`Shift+Tab` = 3칸 들여쓰기(`guideKey`). 저장할 때 글머리만 남은 빈 줄은 지움(`cleanGuide`). 편집(기존 행)에도 버튼·키는 동작, 틀은 행 추가 때만.
6. **주간회의 전달사항**: 연도 탭(일자 기준, 기본 = 최근 연도). 공통 `YEAR_OF`, `yearsOf`, `yearSel`, `yearTabs`, `fstate().year` (`jumpTo` 는 연도를 '전체'로 풀어 항목이 숨지 않게).
- 공통: `fstate` 에 `closed, year, view` 추가. 인쇄 때 연도 탭·버튼 숨김.
- **확인한 것**: `node --check`(스크립트 문법), `py_compile`. 임시 폴더 가짜 데이터 + 가짜 계정 5개로 server.py 를 띄워 Chromium 에서 홈·수행·통합 업무(전체/2025/2026·임박)·유닛 조직도(2026/2025)·프로필 팝업·내 정보·행 추가 가이드·전달사항 연도 탭을 열어 스크립트 오류 없음. 새 일반업무 저장 → 빈 글머리 줄이 지워져 `1. 첫 항목` 만 저장, `종료 구분=상시` 저장 확인. 수행 PJT 를 종결로 저장 → 홈 '수행 PJT(진행 중)' 6→5, '종결 PJT' 4→5.
- **회사에서 확인할 것**: (1) 서버 재시작 후 각자 '내 정보' 입력 → 조직도에 사진·PJT 가 뜨는지 (구성원 칸 이름이 계정 본명과 같아야 함). (2) 기존 일반업무·To do 의 '종료 구분'은 빈 칸이라 자동 판단 — 상시 업무는 '상시'로 골라 주면 정확해짐. (3) 오른쪽 '내 업무' 막대가 표 오른쪽 칸(작업 버튼)을 가리는 것은 원래 동작 — 막대의 `–` 로 접어서 쓴다.

### 2026-10-13 (3) — 조직도 직책 심볼 · 수행/입찰 PJT 현황판 (APP_VERSION 2026-10-13.3 / SERVER_VERSION 그대로 2026-10-13.1)
> dashboard.html 만 바뀜. 서버 재시작 필요 없음.
- **조직도 심볼**: 그룹장 = 💎 다이아(아바타 오른쪽 아래 다이아 배지 + 하늘빛 테두리·빛), 유닛장 = ★ 골드(금색 원 배지 + 금색 테두리·알약). 유닛장 판단은 구성원 칸의 `이름(유닛장)` (`isUnitLead`: '유닛장'·'Unit Leader'·'UL'). 유닛 안에서 유닛장이 맨 위로 정렬. 조직도 아래 범례 표시. 바뀐 곳 `orgPill`, `orgHtml`, CSS `.osym .dia/.gold`, `.opill.r-dia/.r-gold`, `.olg`.
- **수행·입찰 PJT 현황판** (`pjHero(s)`, `#pjhero`): 통합 업무와 같은 그라데이션·카드 디자인을 표 **위에** 붙임. 아래 **엑셀형 표·필터·열 필터·셀 편집은 그대로**.
  - 머리 띠(수행 = 파랑→청록, 입찰 = 보라→주황) + 사업군 칩(누르면 표의 사업군 필터), KPI: 금주 업데이트율 링 · 진행 중 · 종결 · 금주 업데이트 · 미업데이트 (누르면 표가 그 조건으로 걸러짐, 다시 누르면 해제). 사업군별 진행/종결 막대, 담당자별 진행 PJT 막대(프로필 사진, 누르면 담당자 필터).
  - 새 필터 상태 `fstate().upd` ('upd' 금주 업데이트 / 'not' 미업데이트), `filteredRecs` 에 조건 추가. 공용 `avHtml(name)`. 인쇄 때 현황판 숨김(`.pjhero`).
- **확인한 것**: `node --check`. 임시 폴더 가짜 데이터로 Chromium 에서 조직도(2026)·수행·입찰 화면, '종결' 카드 → 표 2건, 담당자 막대 → 표 2건으로 걸러짐, 스크립트 오류 없음.
- **회사에서 확인할 것**: 유닛장 심볼이 나오려면 유닛분장 구성원 칸에 `홍길동(유닛장)` 처럼 써야 함.

### 2026-10-13 (4) — R&R · 투입 분석 (월말 시수 업로드) · Project Code · 열 추가 (APP_VERSION 2026-10-13.4 / SERVER_VERSION 2026-10-13.2)
> **서버 재시작 필요** (server.py: 시수·열 추가 API, `timesheets/` 폴더).
1. **메뉴 '👥 R&R · 투입 분석' (route `alloc`)** — PJT R&R(`rnr`) + 계장 투입인력(`staffing`)을 한 화면으로. 두 시트는 사이드바에서 숨김(`SHEETS[].merged:'alloc'`), 데이터·주소(`#rnr` `#staffing`)·화면 오른쪽 위 '원본 시트' 버튼은 그대로.
2. **월말 시수 파일 업로드** (부서원 개인 집계 엑셀 .xlsx, 예: `개인 집계_7월.xlsx`)
   - 서버 `parse_timesheet` (표준 라이브러리 zipfile + ElementTree): 머리글에 `Type`·`Project` 가 있는 시트를 찾고, 그 오른쪽에서 `01~31` 날짜 줄(숫자·'01' 글자·날짜서식 모두)을 찾아 줄마다 시간을 합산. 시간 값은 시간서식(`[h]:mm`, 하루 비율 → ×24), `h:mm` 글자, 서식 없는 숫자(모두 1 이하면 하루 비율로 봄) 모두 처리. 'Total'·'합계' 줄은 제외. 월은 파일 안의 `2026-07` 같은 글자/날짜에서, 없으면 업로드 창에서 고른 월.
   - 저장: `timesheets/{연도}/{계정ID}_{YYYY-MM}.json` (`rows:[{type, detail, code, work, days:{일:h}, h}]`) + 원본 `timesheets/{연도}/raw/…xlsx`. 같은 사람·같은 달은 덮어씀. 일일 백업에 포함.
   - API: `PUT /api/timesheet?person=ID&month=YYYY-MM&name=파일명` (본문 = xlsx, 로그인+주간업무보고 권한, **다른 사람 것은 Management 권한자만**), `GET /api/timesheets?year=YYYY` (로그인 필요), `DELETE /api/timesheet/{ID}/{YYYY-MM}` (본인 또는 Management).
   - **Step3 권한**: Management 메뉴 권한(`perms_for(...).mgmt`, 운영자=서버 PC 포함)이 있으면 `canHours:true` + 실제 시간. 없으면 서버가 **시간을 보내지 않고** 사람·연도별 합계가 100 이 되는 비율 단위 `v` 로만 보냄(사람 안의 월·프로젝트 비율은 그대로 정확). 화면 배지 🔒/🔓.
3. **Step1 분류** (`tsClass`, 화면에서 계산): Type 이 `공통` → 부서업무 / 그 외 → `Project` 코드를 **수행·입찰 PJT 의 새 칸 `Project Code`**(쉼표·줄바꿈으로 여러 개)와 맞춤(`projIndex`) / 못 찾으면 '미등록 코드 X'(경고 띠에 목록) / 코드 없음.
4. **Step2 화면** (`renderAlloc`, 상태 `AS`): 연도 탭 · 월 칩(연간/1~12월) · KPI(프로젝트 %, 부서업무 %, 미등록 %, 업로드 인원) · 부서원별 100% 막대(마우스 = 상세, Management 는 시간) · 프로젝트별 팀 대비 비율(권한 없으면 사람별 비중 동일 가정이라고 표시) · 개인 분석(도넛, 12개월 구성 막대, **R&R · 계획 대비 실제** 표 = rnr 역할·기간·공정률 + staffing 배정% (열 이름 ↔ PJT명 이름 맞춤 `nmKey`) + 시수 실제%, 차이 %p) · 업로드 현황(부서원×월 ✓, 본인/Management 는 눌러서 삭제). 색은 연도 전체 기준으로 고정.
5. **수행·입찰 `Project Code` 칸** (PJT명 옆).
6. **열 추가** (모든 표 시트, 투입인력 매트릭스 제외): [＋ 열 추가] → 이름·한 줄/여러 줄·너비. 정의는 `data/_meta/sheet-columns.json` (`GET all` 의 `sheetCols`), API `POST /api/sheetcols {sheet,f,long,w}` · `DELETE /api/sheetcols/{sheet}?f=`. 화면은 `applyExtraCols()` 가 `render()` 때마다 `s.cols = baseCols + 추가 열`. 지우기 = 그 열 머리글 ▾ → '추가한 이 열 지우기'(정의만 지움, 행의 값은 남음). 열 이름에 `.` `<` `>` 불가(필드 경로 규칙).
- **확인한 것**: `node --check`, `py_compile`. openpyxl 로 만든 가짜 시수 파일(시간서식/글자 두 방식)을 서버가 읽은 합계 = 엑셀 값과 일치(예: D026 40h, 19LT 21h). 시험 서버(사내망 주소)에서 일반 부서원 = 비율만, Management 권한자 = 시간 표시, 일반 부서원이 다른 사람 것 올리기·지우기 → 403, 비로그인 GET → 401, xlsx 아닌 파일 → 400. 화면: 연간/7월, 개인 분석·R&R 표, 업로드 창, 열 추가 → 저장 확인. 스크립트 오류 없음.
- **회사에서 확인할 것**: (1) 실제 개인 집계 파일 1개를 올려 합계가 엑셀 'Total' 과 같은지. 양식이 다르면(머리글 이름 등) 오류 문구 그대로 알려 주면 맞춤. (2) 수행·입찰 PJT 에 Project Code(D026, 19LT 등) 입력. (3) 실제 시간을 볼 사람에게 ⚙ 메뉴 권한에서 Management 체크.
