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

### 2026-10-13 (5) — 통합 업무 종결·열 필터·완료 알림 · 사업군 단어 필터 · 조직도 업무 요약 (APP_VERSION 2026-10-13.5 / SERVER_VERSION 그대로 2026-10-13.2)
> dashboard.html 만 바뀜 (서버 재시작은 (4) 의 server.py 를 아직 안 넣었다면 필요).
1. **통합 업무 종결**: 일반업무·To do·기술공유에 `종결 여부`(진행/종결, `closed:1`) 열 추가. 통합 업무 목록 작업 칸 [🏁 종결] / [↩ 진행] 한 번 누르면 저장(`workToggleClose` → `saveEdit`). `workItem`: 종결 → 상태 '🏁 종결'(cls `done`), To do 의 완료 여부 O 는 상시라도 완료.
2. **통합 업무 표 열 필터**: 머리글마다 ▾ (유형·구분·업무 내용·담당·시작·종료·종료 관리·진행 내용, `WCOLS`). 목록 계산을 `workScope()`·`workList(skipCf)`·`workVal()` 로 분리하고, `openCf` 는 `route === 'work'` 이면 `WS.cf / WS.sort` 를 씀. `cfBtn('work', k)`.
3. **완료 알림**: `myTasks` 에서 기존 To do '현황 작성' 업무를 없애고, 통합 업무 중 내가 담당(To do 는 완료·종결 전 전부, 일반업무·기술공유는 지연·임박)인 것을 `🔔 완료 알림`(f `__ack`)으로. 팝업·툴바에서 한 번 누르면 편집 창을 열지 않고 '확인완료'(`ackTask`, 브라우저 localStorage `dept-ack|이름`, 키 = `주차|시트|ID` → 다음 주에 아직 미완료면 다시 알림). 종결·완료하면 알림에서 빠짐. 수행·입찰 PJT '업무 현황 작성'은 그대로(누르면 편집).
4. **사업군 단어 필터**: 수행·입찰 현황판의 사업군 칩·막대를 단어 단위로 (`bizTok`: '발전(UNIT1)' → 발전, '수소/LNG' → 수소·LNG, 숫자 든 조각 제외). 누르면 `fstate().kw` → 사업군에 그 단어가 **들어간** 행 모두 (예: 발전 → 발전(UNIT1)·발전/LNG·발전(UNIT2)·발전). 한 PJT 가 여러 막대에 들어갈 수 있음. 표 아래 "사업군에 '발전' 포함" 표시. (위쪽 '사업군' 드롭다운은 예전처럼 정확히 같은 값)
5. **조직도 → 업무 요약**: 사람을 누르면 프로필 아래 '담당 업무 요약' 3칸 — 수행 PJT(진행, 담당자 칸 기준, PJT명·사업군·업무 현황 첫 2줄), 입찰 PJT, 통합 업무(미완료, 상태 배지). `personSummary`, `brief`.
- **확인한 것**: `node --check`. 시험 서버(사업군 '발전(UNIT1)','수소/LNG','발전/LNG' 등 가짜 데이터)에서 입찰 '발전' → 4건, 'LNG' → 3건; 통합 업무 유형 열 필터 To do → 9건; HAZOP 행 [🏁 종결] → 종결·완료로 바뀌고 알림에서 빠짐; 알림 한 번 누름 → '✓ 확인완료'; 조직도 홍길동 → 요약 3칸. 스크립트 오류 없음.

### 2026-10-13 (6) — 통합 업무를 엑셀형 시트로 · 유형(과제 / 지시사항 및 Action List / To Do List) (APP_VERSION 2026-10-13.6 / SERVER_VERSION 2026-10-13.3)
> **서버 재시작 필요** (server.py `SHEETS` 에 `task` 추가 — 예전 서버는 '잘못된 시트'로 거부).
1. **새 시트 `task` (라벨 '통합 업무', 저장 `data/task/`)** — 메뉴 '🚀 통합 업무' = `#task` (예전 주소 `#work` 는 `render()` 에서 `#task` 로 바꿈). 수행·입찰 PJT 처럼 위 = 현황판(`taskHero`), 아래 = 엑셀형 표(셀 선택·더블클릭 편집·행 추가·열 추가·▾ 열 필터·작성 가이드 모두 공통 시트 기능 그대로).
   - 열: 유형(`ttype` select, 필수) · 구분 · 업무 내용(제목) · 담당자 · 요청자 · 시작일 · 종료일 · 종료 구분(기한/상시) · 진척률(%) · 종결 여부 · 진행 사항 · 비고. 표는 유형별로 묶어 정렬(`sortRecs`: 과제 → 지시사항 → To Do → 미지정, `group:'유형'`).
   - 유형 정의 `TASK_TYPES`, 모양 `TT`/`ttOf`(아이콘·색·설명). **진행 사항 작성 틀이 유형별**(`TASK_TPL`): 과제 = 목표/진행 현황/이슈·다음 단계, 지시사항 = 지시 내용/조치 계획(Action)/조치 결과, To Do = `- `. 편집 창에서 유형을 바꾸면 아직 손대지 않은 틀은 그 유형 틀로 바뀜.
   - 작업 칸 [🏁 종결]/[↩ 진행] (`actCell` 의 `data-wclose`, `#content` 클릭 처리 → `workToggleClose`).
2. **현황판 `taskHero`**: 연도 탭(기본 전체) · [＋ 업무 추가](유형 먼저 고름) · 유형 칩 · **유형별 요약 카드 3개**(진행 수, 지연/임박/진행/상시/종결, 종결률 막대, 과제 = 평균 진척률 · 지시사항 = 요청자별 · To Do = 7일 안 마감, 급한 업무 3개 → 누르면 편집) · 상태 KPI(누르면 표 필터 `fstate().wst`) · 부서원별 상·하반기(누르면 담당자 필터) · 종료 현황 막대. 표 필터는 공통 `fstate('task')`(연도 `YEAR_OF.task` = 시작일/종료일, 유형 = `f['유형']`, 담당자 = `owner`, 상태 = `wst`).
3. 상태 규칙(`workItem('task')`): 종결 → 종결(완료) / 상시 → 추적 안 함 / 기한인데 종료일 없음 → 미입력 / 종료일 지남 → **지연**(종결 전까지) / 7일 이내 → 임박 / 그 외 진행 중.
4. **기존 업무 가져오기** (`importLegacy`, `legacyToTask`): 일반업무 → 과제(구분·소구분 합침, 책임자 → 담당자, 종료일 지난 것 → 종결), To do → 지시사항 및 Action List(PO → 담당자, Issue/Target Date → 시작/종료, 완료 O → 종결, 완료 여부·그룹장 추가요청 → 비고), 기술공유 → 과제(구분 '기술공유', 발표자 → 담당자, 발표일 지남 → 종결). 새 ID = `task-` + 원래 ID 라서 두 번 눌러도 중복 없음(409 건너뜀). 예전 시트는 그대로(숨김, 현황판의 버튼으로 열 수 있음). 가져오기 전에는 현황판 위에 안내 띠.
   - 가져온 행의 변경 표시: 마감본에 그 행이 없으면 예전 시트의 원래 행을 `legacyToTask` 로 바꿔 비교(`baseRec`, `freshImport`) → 가져오기만으로 노란 음영·NEW 가 생기지 않음.
5. 알림·요약·홈은 `workRecs()` = 통합 업무 + 아직 안 가져온 예전 행. 완료 알림: 과제 = 지연·임박만, 지시사항·To Do = 종결 전 전부. 홈 '기한 지난 업무' 배지·팝업, KPI '통합 업무 미종결 (기한)'.
- 예전 통합 업무 화면 코드(`renderWork`, `WS`, `workList` 등)는 지움.
- **확인한 것**: `node --check`, `py_compile`. 시험 서버(가짜 데이터)에서 #work → #task, 가져오기 24건(유형 과제/지시사항), 노란 음영 없음, 셀 더블클릭으로 유형 변경, 업무 추가(유형 고르기 → 지시사항 틀 → 과제로 바꾸면 과제 틀), 열 추가 '관련 PJT', 유형 카드 → 표 10건, [🏁 종결] 저장. 스크립트 오류 없음.
- **회사에서 확인할 것**: 서버 재시작 후 통합 업무 화면의 **[기존 업무 가져오기]** 를 한 사람만 한 번 누름 → 각자 자기 업무의 **유형**이 맞는지 고침.

### 2026-10-13 (7) — 통합 업무 유형에 '기술공유' 추가 (APP_VERSION 2026-10-13.7 / SERVER_VERSION 그대로 2026-10-13.3)
> dashboard.html 만 바뀜 (v13.6 을 이미 적용했다면 서버 재시작 필요 없음).
- `TASK_TYPES` = 과제 / 지시사항 및 Action List / To Do List / **기술공유**. `TT['기술공유']` = 💡, 색 `#0b84c6`, 설명 '기술 발표 · 사례 공유 · 세미나 (종료일 = 발표일)'. 과제 설명에서 '기술공유' 뺌.
- 작성 틀 `TASK_TPL['기술공유']` = 1. 발표 주제 / 2. 주요 내용 / 3. 자료 · 질의응답.
- 요약 카드(기술공유): 다음 발표(가장 가까운 종료일·제목·발표자) · 발표 완료 수.
- 완료 알림: 과제·기술공유 = 지연·임박만, 지시사항·To Do = 종결 전 전부.
- 가져오기(`legacyToTask`): 예전 기술공유 → 유형 **기술공유**, 구분 = 'YYYY년 발표'(연도 칸). (v13.6 으로 이미 가져온 경우 기술공유 행은 유형 '과제'·구분 '기술공유' 로 들어가 있음 → 구분 열 ▾ 필터로 '기술공유' 를 골라 유형만 바꾸면 됨)
- **확인한 것**: `node --check`. 시험 서버에서 가져오기 → 과제 8 · 지시사항 9 · 기술공유 7, 기술공유 카드 → 표 7건, 업무 추가 창에 4가지 유형, 기술공유 틀. 스크립트 오류 없음.

### 2026-10-13 (8) — 통합 업무 유형 개편 · 수행/입찰 새 행 맨 위 · 이름 변경 · 툴바 이동 · 게시판 유형·실명 (APP_VERSION 2026-10-13.8 / SERVER_VERSION 2026-10-13.4)
> **서버 재시작 필요** (server.py: 게시판 `kind`·`real`, 이름 문구).
1. **통합 업무 유형** `TASK_TYPES` = **일반업무**(그룹 업무) / **표준화 담당**(ITEM PO) / To Do List / 기술공유 / **그룹장 요청 사항**. 담당자 열 머리 = '담당자 / ITEM PO'. 작성 틀 `TASK_TPL`: 일반업무 = 목표·진행 현황·이슈, 표준화 담당 = 표준화 ITEM·제·개정 현황·검토·배포, 그룹장 요청 사항 = 요청 내용·조치 계획(Action)·조치 결과. 카드 요약: 표준화 담당 = ITEM 수·ITEM PO 수·평균 진척률, 그룹장 요청 = 요청자별. 완료 알림: To Do·그룹장 요청 = 종결 전 전부, 나머지 = 지연·임박.
   - 예전 이름(v13.6~13.7): `TYPE_ALIAS` 과제 → 일반업무, 지시사항 및 Action List → 그룹장 요청 사항. 화면·필터·정렬·편집 창은 `normType()` 으로 새 이름처럼 다룸. 현황판 띠의 [저장된 값도 새 이름으로 바꾸기] (`renameOldTypes`) 로 실제 값도 바꿈. 가져오기 규칙도 일반업무 → 일반업무, To do → 그룹장 요청 사항, 기술공유 → 기술공유.
2. **수행·입찰 행 추가 → 맨 위** (`submitRecord`: order = 가장 작은 order − 10).
3. **이름**: 화면 제목·`<title>`·로그인 화면·server 사용법 문구 '계장ENG그룹 주간업무 Dashboard' → **'계장ENG그룹 Dashboard'**. (운영 폴더 이름 `C:\Claude\계장ENG그룹 주간업무 Dashboard\` 는 그대로 — APPLY.bat 는 `*Dashboard*` 로 찾음)
4. **내 업무 툴바 이동**: 머리(⠿)나 접힌 탭을 끌면 옮겨지고 위치는 브라우저에 기억(`dept-taskbar-pos`), ⠿ 두 번 누르면 원래 자리. `tbDragInit`, `tbPlace`. 끈 뒤 바로 오는 클릭은 무시.
5. **게시판**: 글 유형 `kind` = 💬 블라블라 / 🍻 회식제안 / 📣 VOC (예전 글 = 블라블라), 목록 위 유형 칩(`#bkinds`, 글 수). 글·댓글 작성자 = **익명 / 닉네임 / 실명**. 실명은 브라우저가 보낸 이름이 아니라 **서버가 로그인 계정 본명**으로 기록(`board_author`, `real:true`, 화면 '✔ 이름'). 익명·닉네임은 예전처럼 실명 저장 안 함. server: `api_board_create/update/api_comment_add(…, acc)`, `BOARD_KINDS`, `board_kind`.
- **확인한 것**: `node --check`, `py_compile`. 시험 서버(가짜 데이터): 제목 '계장ENG그룹 Dashboard', 예전 유형 행 2건 → [새 이름으로 바꾸기] 후 유형 = 일반업무 9 · 그룹장 요청 사항 10 · 기술공유 7, 툴바 끌어 옮김 → 새로고침 후에도 같은 자리, 수행 행 추가 → 맨 위, 게시판 회식제안(실명)·VOC(익명) 등록 → 칩 수·필터, API 로 real + 다른 이름을 보내도 계정 본명으로 저장. 스크립트 오류 없음.

### 2026-10-13 (9) — 엑셀 시트 구분대로 유형 나누기 · To do list → To Do List · 부서원 차트 접기 (APP_VERSION 2026-10-13.9 / SERVER_VERSION 그대로 2026-10-13.4)
> dashboard.html 만 바뀜. 서버 재시작 필요 없음.
- **원인**: v13.8 가져오기 규칙이 엑셀 'To do list' 시트를 '그룹장 요청 사항' 으로, '일반업무' 시트 전부를 '일반업무' 로 넣었음 → 회사 화면 To Do List 0건.
- **새 규칙** (`legacyType`, `generalType`): 일반업무 시트는 구분+소구분 글자로 — `ITEM` · `MDL` · `상품 담당` · 단어 `PO` → **표준화 담당**, `지시` · `Action` → **그룹장 요청 사항**, 과제 · 그룹 업무 · 그 외 → **일반업무**. To do list 시트 → **To Do List**, 기술공유 시트 → 기술공유. (회사 일반업무 시트의 구분 값: 과제 (Set-up 중) / 그룹 업무 - 업무 / 지시사항, Action List 등 / ITEM PO/MDL - 상품 담당 · MDL · PO)
- **이미 가져온 행 다시 나누기** (`reclassList`, `reclassify`): ID 가 `task-general-…` / `task-todo-…` 이고 유형이 예전 자동값(일반업무 / 그룹장 요청 사항, 예전 이름 포함)인 행만 대상. 원래 시트 행이 있으면 그 구분으로, 없으면 통합 업무의 구분 칸으로 판단. 사람이 다른 유형으로 고친 행은 건드리지 않음. 현황판 띠의 [유형 다시 나누기] → 확인 창(바뀔 건수) → 저장. 비교 기준(`baseRec` → `legacyToTask`)도 새 규칙이라 다시 나눈 유형 칸은 노란 음영이 생기지 않음.
- **부서원별 상·하반기 차트 반으로 접기**: 7명 이상이면 기본으로 위쪽 절반만(건수 많은 순), 머리의 [▼ 나머지 n명 펼치기] / [▲ 반으로 접기], 아래 [▼ n명 더 보기]. `fstate('task').pfold`.
- **확인한 것**: `node --check`. 시험 서버에서 회사와 같은 구분 값으로 '예전 규칙으로 가져온' 24건을 만들어 [유형 다시 나누기] → To do 9건 → To Do List, 일반업무 시트 7건 → 일반업무 3 · 표준화 담당 3 · 그룹장 요청 1, 사람이 기술공유로 바꿔 둔 행은 그대로, 띠 사라짐. 부서원 14명 → 접으면 7명, 펼치면 14명. 스크립트 오류 없음.
- **회사에서 할 일**: 통합 업무 화면 위 띠의 **[유형 다시 나누기]** 를 한 사람이 한 번.

### 2026-10-13 (10) — 시수 파일 끌어다 놓기 · 미리보기 후 업로드 · 실제 양식(두 줄 머리글) 읽기 · 조직도 꾸미기 (APP_VERSION 2026-10-13.10 / SERVER_VERSION 2026-10-13.5)
> **서버 재시작 필요** (server.py: 두 줄 머리글 읽기, 미리보기 API, 월 지정).
1. **실제 시수 양식 읽기 버그 수정** (`parse_timesheet`): 회사 양식(개인 집계_6월.xlsx)은 머리글이 두 줄 — 1행 `S/O · Project · Work · 2026-07 · Total`, 2행 `OBS · Type · Detail · 01~31`, 3행 요일. 예전 코드는 Type 과 Project 가 같은 줄에 있어야 해서 "머리글을 찾지 못했습니다" 오류. 이제 위·아래 두 줄을 합쳐 머리글을 찾음. 시간 칸은 `h:mm` 서식(하루 비율 ×24), 마지막 'Total' 줄 제외.
   - 받은 6월 파일 시뮬레이션: 9줄 중 시간 입력 2줄(6일 — 공통 계장ENG 주간회의 3:10, D026 4:10), 합계 7:20 = 엑셀 값과 일치. **파일 이름은 6월인데 파일 안 날짜는 2026-07(1일=수요일, 7월 달력)** → 아래 미리보기에서 경고.
2. **끌어다 놓기 → 미리보기 → [업로드 · 분석]** (`openTsUpload(file)`): 업로드 창의 큰 놓기 칸(또는 눌러서 고르기), R&R · 투입 분석 화면 아무 곳에 놓아도 창이 열림. 놓으면 서버 `POST /api/timesheet/preview`(저장 안 함, `api_ts_preview`)로 읽어 파일 안의 월·줄 수·합계·분류(Step 1: 부서업무 / PJT / 미등록 코드) 막대·표·줄별 내용을 보여 줌. 파일 이름의 'N월' 과 파일 안 월이 다르면 경고. **저장할 월**(기본 = 파일 안의 월)을 확인·변경하고 [업로드 · 분석] 을 눌러야 저장(`PUT timesheet?…&useMonth=1` → 화면에서 고른 월 사용).
3. **조직도 꾸미기 v2** (CSS '조직도 v2' 블록, `</style>` 바로 앞): 은하수 배경(빛 번짐·점무늬·천천히 도는 오로라), 빛나는 'ORGANIZATION' 제목, 통계 배지(유닛·인원·프로필 등록·수행/입찰 PJT 수), 유닛마다 다른 색(`--uc`)·번호 배지·담당 분야 칩·인원/PJT 수, 빛나는 연결선, 구성원 카드(유닛 색 띠·마우스 올리면 떠오름·빛), 그룹장 카드 은은하게 빛남. 유닛 열을 grid 로 가운데 정렬(회사 화면에서 오른쪽으로 치우치던 것 수정). 인쇄 때 움직임 끔.
- **확인한 것**: `node --check`, `py_compile`. 받은 6월 파일로 서버 읽기 = 엑셀 값과 일치(7:20). 시험 서버에서 업로드 창에 파일을 끌어다 놓기 → 미리보기(2026-07, 9줄·2줄, 7:20, 6월/7월 경고) → 저장할 월 2026-06 → [업로드 · 분석] → 6월로 저장·분석 화면 갱신. 분석 화면에 놓기 → 창 열림·미리보기. 조직도(유닛 2개·19명) 가운데 정렬·배지·마우스 효과. 스크립트 오류 없음.
- **회사에서 확인할 것**: 각자 시수 파일을 끌어다 놓고 미리보기의 합계가 엑셀 Total 과 같은지, 파일 안 월이 맞는지(템플릿 머리글 '2026-07' 을 고치지 않고 쓰는 경우 저장할 월을 직접 고름).

### 2026-10-13 (11) — 수행·입찰 부서원 그래프 전체 표시·반 접기 · 통합 업무 유형별 필터 분리 · 메뉴 이모지 삭제 (APP_VERSION 2026-10-13.11 / SERVER_VERSION 그대로 2026-10-13.5)
1. **수행·입찰 PJT 보드의 담당자 그래프** (`pjHero`): '상위 8명' → **전체 부서원**('부서원별 진행 PJT · 전체 n명'). 명단 = 진행 PJT 담당자 + 가장 최근 연도 유닛분장의 구성원(그룹장 제외, 새 함수 `deptNames()`) — PJT 0건인 사람도 0 으로 표시. 건수 많은 순 → 이름순. 7명 이상이면 기본으로 **위쪽 절반만**, 머리의 [▼ 나머지 n명 펼치기] / [▲ 반으로 접기], 아래 [▼ n명 더 보기] (`data-pjf="pfold|"`, 상태 `fstate('perform'|'bid').pfold`). 통합 업무 부서원 차트와 같은 방식.
2. **통합 업무: 유형마다 필터 따로** (`taskTypeSwitch(st, 유형)`, `TASK_FKEYS`): 유형 칩·유형 카드·표 위 '유형' 선택 상자로 유형을 바꾸면 지금 유형의 필터(담당자·사람 클릭·내 업무만·검색·종결 여부·현황 카드(지연/임박…)·열 필터·정렬)를 `st.byType[유형]` 에 넣어 두고, 새 유형의 필터를 꺼냄(처음이면 빈 필터). '전체' 도 하나의 유형으로 따로 기억. 연도 탭은 모든 유형이 함께 씀. [필터 초기화] 는 지금 보는 유형의 필터만 지움(연도·유형·다른 유형 기억은 유지).
3. **메뉴 글자**: '👥 R&R · 투입 분석' → 'R&R · 투입 분석', '🚀 통합 업무' → '통합 업무' (메뉴만, 화면 제목은 그대로).
- **확인한 것**: `node --check`. 시험 서버(유닛 2개·18명): 수행·입찰 보드 접힘 9명 / 펼침 18명, PJT 0건인 사람도 표시. 통합 업무 To Do List(9건)에서 사람 클릭 → 3건, 일반업무로 바꾸면 필터 없이 8건, 다시 To Do List → 3건(사람 선택 유지), [필터 초기화] → 9건·유형 유지. 메뉴에 이모지 없음. 스크립트 오류 없음.
- **회사에서 확인할 것**: 부서원 명단은 **가장 최근 연도 유닛분장의 '구성원'** 칸을 씀 — 빠진 사람이 있으면 유닛분장에 추가.

### 2026-10-13 (12) — 시수 파일 삭제 단추 · 통합 업무 진행 상태 필터 · 필터 창 스크롤 유지 · 삭제 취소선 없앰 (APP_VERSION 2026-10-13.12 / SERVER_VERSION 2026-10-13.6)
> **서버 재시작 필요** (server.py: 시수 삭제 때 원본 엑셀도 지움).
1. **올린 시수 파일 삭제** (`openTsDelete(list)`, R&R · 투입 분석 위 **[🗑 올린 파일 삭제]**): 그 연도에 지울 수 있는 파일(본인 것, Management 권한자는 전부)을 부서원·월·파일·올린 사람 목록으로 보여 주고 [삭제] → 확인 → `DELETE /api/timesheet/{id}/{YYYY-MM}`. 아래 '시수 업로드 현황' 표의 ✓ 도 마우스를 올리면 빨간 ✕ 로 바뀌어 눌러서 지울 수 있음(예전부터 있던 기능을 보이게 함). 서버 `api_ts_delete` 는 이제 `timesheets/{YYYY}/raw/{id}_{YYYY-MM}.xlsx` 원본도 함께 지움.
   - 주의: `ask()` 창을 연달아 열 때 앞 창의 close 이벤트가 새 창을 닫아 버리므로 `setTimeout(0)` 한 번 기다린 뒤 다음 창을 엶.
2. **통합 업무 필터** (`renderSheet`, `colVal`):
   - 담당자 옆에 **진행 상태(전체 / 진행 중 / 종결)** 선택 상자 (수행·입찰과 같은 `st.closed`, 유형별 필터 기억에 포함).
   - 머리글 ▾ 필터 목록에서 **'종결 여부' 빈 칸 = '진행'** 으로 보임(값이 '종결' 이 아니면 진행). '종료 구분' 빈 칸 = 화면에 보이는 자동 값('기한' / '상시'). 저장된 값은 그대로.
   - **필터 창(▾)이 마우스 휠로 화면을 굴려도 닫히지 않음** — ▾ 단추를 따라 움직임(`placeCf`). 다른 곳 클릭 · Esc 로 닫힘.
3. **수행·입찰 등 편집 시 '지운 내용 붉은 취소선(~~ ~~)' 기능 없앰**: 편집 창 저장 때 `mergeStrike` 를 쓰지 않고 지운 내용은 그냥 지움(`mergeStrike`·`joinTokens` 삭제). 추가된 내용의 **파란 글씨**(마지막 마감 대비, `markAdded`)는 그대로. 예전에 남은 `~~내용~~` 은 화면(`fmtText`)·엑셀 내보내기(`xlCell`)에서 숨기고, 편집 창에는 안 보이며 그 행을 저장하면 지워짐(`purgeStrike`). 편집 창의 취소선 안내 문구와 [취소선 내용 모두 완전 삭제] 단추 삭제.
- **확인한 것**: `node --check`, `py_compile`. 시험 서버: 시수 3건 올림 → [🗑 올린 파일 삭제] 목록 3줄 → 1건 삭제 → 목록 2줄, json·원본 xlsx 모두 지워짐. 통합 업무 24건 → 진행 상태 '종결' 10 / '진행 중' 14, '종결 여부' 필터 목록 = 종결 10 · 진행 14 (빈 셀 없음), '종료 구분' = 기한 20 · 상시 4. 필터 창 열고 휠 → 창 유지·단추 따라 이동, 다른 곳 클릭 → 닫힘. 수행 행에 `~~예전에 지운 줄~~` 을 넣어 두면 화면에 안 보임, 편집 창에도 안 보임, 내용 추가 후 저장 → 저장값에 ~~ 없음, 추가 부분만 파란 글씨. 스크립트 오류 없음.
- **회사에서 확인할 것**: 서버 재시작 후 시수 삭제. 예전 취소선이 남아 있던 행은 화면에서 사라짐(데이터에서 완전히 지우려면 그 행을 한 번 편집·저장).

### 2026-10-13 (13) — 서버 PC 절전 방지 · 서버가 꺼졌을 때 쓴 내용 '덮어쓸까요?' · 부서원 dashboard.html 자동 교체 (APP_VERSION 2026-10-13.13 / SERVER_VERSION 2026-10-13.7)
> **서버 재시작 필요** (server.py: 절전 방지).
1. **절전 모드** (server.py `keep_awake_loop`, 새 옵션 `--allow-sleep`): 서버가 켜져 있는 동안 1분마다 Windows `SetThreadExecutionState(ES_SYSTEM_REQUIRED)` (ctypes, 표준 라이브러리) → 서버 PC 가 **유휴 절전(대기) 모드로 들어가지 않음**. 화면 끄기·화면 잠금은 그대로 됨. 노트북 덮개 닫기·전원 단추·시작 메뉴 '절전'으로 직접 재우는 것은 못 막음 → 그때는 아래 2번(오프라인)으로 동작. 서버 로그에 `절전 방지: 켜짐`. 절전을 허용하려면 `server.py --allow-sleep` (bat 수정 필요).
2. **서버가 꺼져 있을 때 쓴 내용 → 서버가 켜지면 '덮어쓸까요?'** (`trySync`, 새 `askOverwrite`, `syncOp(op, force)`, `SYNC_HOLD`): 기존 오프라인 모드(부서원 PC 의 dashboard.html = file:// 로 열고 서버 연결 실패 → 이 PC 보관본 표시, 수정은 IndexedDB 대기열)는 그대로. 서버가 다시 연결되면(30초마다 자동 재연결 · [지금 재연결] · 파일을 다시 열 때 `startOnline`) 내 대기열이 있으면 먼저 팝업: 목록(시트·항목·작업·시각) + **[예 (덮어쓰기)]** = 모두 서버에 반영, 그 사이 다른 사람이 같은 행을 고쳤어도 묻지 않고 내 것으로(`force`, 서버 이력에 'overwrite' 로 남음) / **[하나씩 확인]** = 예전처럼 충돌 행만 비교 창 / **[나중에]** = 이 PC 에 보관, 자동 재연결 때는 다시 묻지 않고 배너의 [지금 동기화] 로 다시 물음.
   - 다른 사람이 이 PC 에서 오프라인으로 쓴 것은 예전처럼 그 사람이 로그인했을 때 올림.
   - 서버에 한 번도 연결된 적 없는 PC(보관본 없음)는 오프라인으로 열 수 없음 (안내 화면) — 기존과 같음.
3. **프로그램 업데이트 → '부서원의 dashboard.html 을 업데이트 파일로 교체하세요'** (`askUpdate`, `replaceSelf`, `newHtml`, IndexedDB 키 `self`): file:// 사본의 `APP_VERSION` 이 서버 dashboard.html 버전과 다르면(서버 연결 직후 · 오프라인 대기열 처리 뒤) 팝업 [예 (교체)] / [나중에]. [예] → 서버에서 새 `/dashboard.html`(DEFAULT_SERVERS 치환본) 받기 → File System Access API 로 **이 PC 의 파일을 덮어쓰고 다시 엶**. 처음 한 번은 저장 창이 열림 → 지금 쓰는 dashboard.html 을 골라 [저장] → [바꾸기]. 고른 파일 핸들을 IndexedDB 에 기억 → 다음 업데이트부터는 창 없이 바로(권한 확인 창만 뜰 수 있음). 고른 파일 이름이 지금 연 파일과 다르면 "그 파일을 여세요" 안내. 브라우저가 지원하지 않으면 예전처럼 내려받기. 배너에 [지금 교체] 단추 추가(나중에 → 다시 하기).
4. `ask()` 수정: 창을 연달아 열 때 앞 창의 늦은 close 이벤트가 새 창을 닫던 문제 → `dlg2.onclose` 는 창이 실제로 닫혀 있을 때만 처리.
- **확인한 것**: `node --check`, `py_compile`. 시험: 서버가 준 파일을 부서원 PC 사본처럼 file:// 로 열고(버전 하나 낮춤) → 업데이트 팝업·배너. 서버 끔 → 수행 2행 편집 → 오프라인·대기 2건, 파일을 닫았다 다시 열어도 유지. 서버 켬 + 다른 사람이 같은 행을 서버에서 고침 → [지금 재연결] → '덮어쓸까요?' 목록 2건 → [예] → 충돌 창 없이 두 행 모두 내 내용으로 서버 반영. 이어서 업데이트 팝업 → [예] → 새 버전(2026-10-13.13) 파일 내용을 저장 (자동 시험이라 저장 창은 흉내). 스크립트 오류 없음. (절전 방지는 Windows 전용이라 여기서는 문법만 확인)
- **회사에서 확인할 것**: 서버 로그에 '절전 방지: 켜짐'. 부서원 PC 한 대에서 [예 (교체)] → 저장 창에서 지금 쓰는 dashboard.html 고르기 → 다시 열린 화면 왼쪽 아래 버전이 새 버전인지. 회사 보안 정책이 파일 저장 창을 막으면 [새 버전 다운로드] 로.

### 2026-10-13 (14) — 서버 PC 를 사내 Wi-Fi 로 쓸 때 부서원 접속 (APP_VERSION 2026-10-13.14 / SERVER_VERSION 2026-10-13.8)
> **서버 재시작 필요** (server.py). 새 파일 `allow_firewall.bat`, `check_network.bat` (서버 폴더, ASCII · CRLF · chcp 없음).
- **증상**: 서버 PC 가 유선 LAN 일 때는 부서원 접속 OK, LAN 을 빼고 사내 Wi-Fi 로 바꾸면 접속 안 됨.
- **원인 후보와 대응**
  1. (코드) **허용 대역이 서버 시작 때 한 번만 정해짐**: `ALLOW_NETS` = 서버 IP 의 /16. 회사 IP 가 사설망(10.x·172.16~31.x·192.168.x)이 아니면, 서버가 Wi-Fi IP 로 시작했을 때 유선 부서원 대역이 '사내망 아님' 403 으로 거절됨(부서원 화면에는 그냥 '서버 연결 실패'로 보였음). → `refresh_nets()`: 30초마다(`weekly_loop`) IP 를 확인해 **지금까지 쓴 모든 /16 대역을 `data/_meta/server-nets.json` 에 기억**하고 계속 허용. 403 메시지에 접속 PC 주소 포함, 부서원 화면에 그대로 표시(`BLOCKED`).
  2. (코드) **IP 가 바뀌면 부서원 파일의 서버 주소가 옛 IP**: 배포본 `DEFAULT_SERVERS` = [PC 이름 주소, IP 주소]. → 배포본을 IP 가 바뀔 때도 다시 만듦(`_build_deploy` 기준 = 파일 시각 + `server_urls()`). 부서원 화면은 연결될 때마다 서버 주소들(`info.urls` + 지금 주소)을 localStorage `dept-server-known` 에 기억하고, 연결할 때(`findServer`: 시작 · 오프라인 재연결 `trySync`) **설정 주소 → 기본 주소 → 기억한 주소를 동시에** 시도(각 8초). 'PC 이름' 주소는 IP 가 바뀌어도 사내 DNS 가 새 IP 를 알려 주면 그대로 됨.
  3. (Windows) **Wi-Fi 가 '공용 네트워크'** 이거나, 처음 'python 액세스 허용?' 창에서 공용을 빼서 생긴 **python 차단 규칙**(차단이 허용보다 우선) → 방화벽이 막음. 서버가 시작·IP 변경 때 `Get-NetConnectionProfile` 로 네트워크 종류를 로그에 남기고(`net_profiles`), 서버 PC 관리자 화면에 '공용 네트워크' 경고 배너 · IP 바뀜 배너(`/api/info` 의 `net`, 관리자만). **`allow_firewall.bat`**(관리자 권한): TCP 8080 인바운드 허용(모든 네트워크 종류) + python 인바운드 차단 규칙 끄기 + 네트워크 종류·IP 표시.
  4. (회사망) **사내 Wi-Fi 와 유선망이 서로 막혀 있음**(무선 단말 간 격리·방화벽) → 코드로 못 고침. `check_network.bat`(관리자 권한 불필요): 네트워크 종류, IP, 서버 응답, 8080·python 방화벽 규칙, 방화벽 상태를 화면과 `network_check.txt` 로 보여 줌 → 3 이 아닌데도 안 되면 IT 문의.
- **바뀐 곳**: server.py `refresh_nets`, `net_profiles`, `nets_file`, `NET_STATE`, `EXTRA_NETS`, `_build_deploy`, `weekly_loop`, `main`, `_dispatch`(403 메시지), info / dashboard.html `findServer`, `rememberServers`, `serverCandidates`, `knownServers`, `BLOCKED`, `trySync`, init(file://), `render` 관리자 배너.
- **확인한 것**: `node --check`, `py_compile`, bat ASCII·CRLF. 서버 함수 시험: 유선 65.3.x → Wi-Fi 165.244.x 로 IP 바꿈 → 허용 대역 두 개 모두(유선 부서원 65.3.99.1 허용, 외부 8.8.8.8 거절), Wi-Fi 상태로 다시 시작해도 유선 대역 유지, 배포본 주소가 새 IP 로 바뀜. 화면 시험: 부서원 파일로 한 번 연결 → 주소 기억 → 기본 주소가 닿지 않는 파일로 열어도 1.7초 만에 기억한 주소로 연결. 관리자 화면 경고 배너(Windows 정보는 흉내). bat 은 Windows 에서만 실행 가능해 여기서는 형식만 확인.
- **회사에서 할 일**: ① 서버 재시작 ② 서버 PC 를 Wi-Fi 로 바꾼 뒤 `check_network.bat` → 'Public' 이나 python 'Block' 이 보이면 `allow_firewall.bat` 를 관리자 권한으로 ③ 부서원 PC 에서 `http://서버PC이름:8080/` 이 열리는지, 안 되면 `http://(Wi-Fi IP):8080/` ④ 둘 다 안 되면 IT 에 '사내 Wi-Fi ↔ 유선 PC 간 TCP 8080 허용' 요청.

### 2026-10-13 (15) — Management 메뉴: R&R · 투입 분석(실제 시간 병기) · 근무시간(월별·주별·일별) (APP_VERSION 2026-10-13.15 / SERVER_VERSION 2026-10-13.9)
> **서버 재시작 필요** (server.py: Management 권한자에게 일별 시간도 보냄).
1. **메뉴**: '🛠 Management' 가 하위 메뉴 묶음이 됨(접기/펼치기, localStorage `dept-nav-mgmt-open`) — **R&R · 투입 분석**(route `mgalloc`) · **근무시간 (월·주·일)**(route `mghours`). 머리(#mgmt)를 누르면 #mgalloc 으로. 두 화면 모두 메뉴 권한 키 `mgmt`(`menuOf`). 예전 `MODULES.mgmt`(준비 중 빈 화면) 삭제.
2. **R&R · 투입 분석 두 곳으로 나눔** (`renderAlloc(c, mg)`): 같은 화면·같은 데이터, 표시만 다름. `H` = 서버가 실제 시간을 줌(권한), `SH = H && mg` = 화면에 시간 표시.
   - 주간업무보고 › R&R · 투입 분석(`alloc`): **누구나 비율(%)만**. Management 권한자에게는 '실제 시간은 [Management › R&R · 투입 분석]' 단추.
   - Management › R&R · 투입 분석(`mgalloc`): **비율과 실제 시간 병기** — 예: `54.6% (116:00h)`, 프로젝트별 `53.6% … 437:40h`, 부서원 막대 오른쪽 총 시간, 도넛 가운데 총 시간, R&R 표 실제 투입 `54.6% 116:00h`, 월별 추이 위 월 합계.
   - 시수 올리기·삭제는 두 곳 모두.
3. **근무시간 (월·주·일)** (`renderHours`, `hoursIndex`, 상태 `HS`): 시수 파일의 **날짜별 실제 시간**(rows[].days)으로 부서원 × 기간 표.
   - [📅 월별] 1~12월 · [🗓 주별] 월요일~일요일(연간 = 시수가 있는 주만, 월 선택 = 그 달에 걸친 주 — 달 경계 주는 앞뒤 달 시간 포함 '그 주 전체') · [📆 일별] 한 달 1~31일(요일, 주말 회색).
   - 칸 색: 많을수록 진하게, **주 52시간 초과 · 하루 10시간 초과는 붉게**. 합계 열 · 평균 열(입력 있는 달/주/날 기준) · 팀 합계 줄.
   - 요약: 팀 총 근무시간, 1인 평균, 근무일 평균(하루), 하루 10시간 초과 일수(최장일), 주 52시간 초과 건수(사람 × 주).
   - 이름을 누르면 개인 상세: 날짜별 막대(PJT / 부서업무 / 기타·미등록 쌓기, 점선 = 8시간) + 합계·비율.
4. **server.py `api_ts_list`**: Management 권한자(`can_hours`)에게만 행마다 `days`(날짜 → 시간)를 더 보냄. 일반 부서원 응답은 그대로(비율 단위, days 없음).
- **확인한 것**: `node --check`, `py_compile`. 시험 서버(4명 × 6~9월 시수, 김철수 7/13~17 매일 11시간): 다른 PC 주소로 접속 시 일반 부서원 `canHours false · days 없음`, Management `true · days 있음`. Management 메뉴 하위 2개, #mgmt → #mgalloc. Management › R&R = `%(h)` 병기, 주간업무보고 › R&R = 같은 사람이어도 시간 안 보임. 근무시간 월별 김철수 6~9월 201:50 / 212:30 / 184:00 / 200:20 = 엑셀 합과 같음, 7월 주별 7/13~7/19 55:00 붉은 칸·52시간 초과 1건, 일별 34열(1~31+합계·평균), 개인 상세 23일·212:30h·PJT 93%. 일반 부서원은 메뉴 없음·주소로 들어와도 '접근 권한 없음'. 스크립트 오류 없음.
- **회사에서 확인할 것**: 시수 파일의 Total 과 근무시간 화면의 그 달 합계가 같은지.

### 2026-10-13 (19) — 13.15 로 되돌린 뒤 시수 Type 분류만 추가 (APP_VERSION 2026-10-13.19 / SERVER_VERSION 그대로 2026-10-13.9)
> **되돌림**: 사용자 요청으로 dashboard/ 전체를 2026-10-13.15 (커밋 5707be4, Management 근무시간까지) 상태로 되돌림. 그 뒤에 만들었던 13.16(net_check.py · PowerShell 없는 점검 bat · 서버 netsh), 13.17(보관 상태 표시), 13.18(파일에 데이터 담기 EMBED) 은 **회사에 적용하지 않음** — git 기록(커밋 2d8be53 · 2f76d28 · 7e39f99)에만 있음. 회사 운영본은 13.15 에서 이 변경으로 바로 감. 서버 재시작 필요 없음(server.py 는 13.15 와 같음).
- **시수 Type 분류** (`tsClass`, `tsIsPjtType`):
  - Type **'근태'** → '근태' 한 묶음 (kind `leave`, 노랑) — 여러 줄이어도 하나로, Project 코드가 있어도 무시.
  - Type **'공통'** → 부서업무 (전과 같음).
  - Type **'성과품'**으로 시작(성과품 · 성과품 과정관리 · 성과품 과정정리 …) 또는 **'신사업'** → Project Code 로 수행·입찰 PJT 찾기. **Project Code 가 비어 있으면 '입찰 (Project Code 없음)'** (kind `bid`, 입찰 PJT 로 셈). 코드가 있는데 PJT 에 없으면 전처럼 '미등록 코드'.
  - **그 밖의 Type**(교육 등) → Type 이름 그대로 (kind `other`, '기타 Type'), 코드가 있어도 PJT 로 안 셈.
- R&R · 투입 분석: 근태 KPI 추가(`.alkpis` 6칸), 부서업무 KPI 에 기타 Type %, 프로젝트별 순서 프로젝트 → 미등록 → 기타 Type → 부서업무 → 근태(`AL_RANK`). 업로드 미리보기·설명 문구도 새 규칙.
- 근무시간 화면(`hoursIndex`, `renderHours`): **근태는 근무시간에서 뺌**(합계 · 주 52시간 · 하루 10시간 계산 제외), 요약 '근태 ○h 제외', 개인 상세에 근태 따로.
- **확인한 것**: `node --check`. 시험 시수(공통 · 성과품 과정관리 19LT · 성과품 과정관리 코드 없음 · 신사업 코드 없음 · 근태 X1 · 교육 19LT): 입찰 (Project Code 없음) 52:00h, 예시수행-A 45:00h, 교육 17:00h(기타 Type), 부서업무 15:00h, 근태 20:00h → 프로젝트 투입 65.1%(입찰 포함), 근무시간 129:00h = 149 − 근태 20. 스크립트 오류 없음.

### 2026-10-13 (20) — 시수 분류 규칙 다시 정함: Project Code 우선 (APP_VERSION 2026-10-13.20 / SERVER_VERSION 그대로 2026-10-13.9)
- **규칙** (`tsClass`, 위에서부터 차례로):
  1. Type **'근태'** → 근태 (Project Code 가 있어도 무시).
  2. **Project Code 가 있으면** (Type 상관없음) → 수행·입찰 PJT 의 'Project Code' 칸과 대조해 **수행 / 입찰**. 어느 PJT 에도 없으면 '미등록 코드 ○○'.
  3. 코드 없음 + Type **'공통'** + Detail 에 **'입찰'** 이 들어 있으면 → **입찰** ('입찰 (공통 · Detail 입찰)', kind `bid`).
  4. 코드 없음 + Type **'공통'** (그 밖의 Detail) → **부서업무**.
  5. 코드 없음 + Type **'성과품'**(성과품 · 성과품 과정관리 · 과정정리 …) · **'신사업'** → **입찰** ('입찰 (Project Code 없음)') — 코드가 없어 수행 PJT 를 알 수 없으므로 13.19 규칙 유지.
  6. 코드 없음 + 그 밖의 Type(교육 등) → Type 이름 그대로 (기타 Type).
  - 13.19 와 다른 점: 코드가 있으면 Type 이 무엇이든(공통 · 교육 등) PJT 로 셈. 공통 + Detail 입찰 → 입찰.
- 화면 설명·업로드 창 '집계 방법' 문구도 새 규칙으로. 근태는 근무시간에서 빼는 것 그대로.
- **확인한 것**: `node --check`. 시험 시수 10줄(공통 회의 / 공통 Detail 입찰 / 공통 D026 / 성과품 과정관리 19LT / 성과품 코드 없음 / 신사업 B205 / 교육 A101 / 교육 코드 없음 / 근태 A101 / 성과품 과정관리 Z999) → 부서업무 19h · 입찰(공통 Detail 입찰) 18h · 예시입찰-A 22h · 예시수행-A 34h · 입찰(코드 없음) 13h · 예시입찰-C 21h · 예시수행-B 18h · 교육(기타) 14h · 근태 22h · 미등록 Z999 16h. 근무시간 175h = 197 − 근태 22. 스크립트 오류 없음.

### 2026-10-13 (21) — Management › R&R · 투입 분석: 근태를 누르면 날짜별 근태 상세 (APP_VERSION 2026-10-13.21 / SERVER_VERSION 그대로 2026-10-13.9)
- Management › R&R · 투입 분석(`mgalloc`)의 **🌴 근태** KPI 칸이 단추가 됨(`data-aleave`, 상태 `AS.leave`) → 누르면 KPI 아래에 **근태 상세** 카드(`leaveCard`): 지금 고른 기간(**연간** 또는 **월**)에 부서원별 근태 합계 · 일수 · **날짜별 칩**(월/일 · 요일 · 시간 · Detail 예: 연차/반차, 8시간 이상은 진하게). 월 탭을 바꾸면 그 달만. 다시 누르거나 [닫기]로 닫힘.
- 데이터: 시수 파일의 Type '근태' 줄(`tsClass` kind `leave`)의 날짜별 시간(`rows[].days`, Management 권한자에게만 서버가 보냄).
- 주간업무보고 › R&R · 투입 분석(비율만)에서는 단추 아님(그대로 %만).
- **확인한 것**: `node --check`. 시험: 근태 칸 누름 → 연간 98:00h · 46일 날짜별 칩(Detail 연차·반차), 12월 → 22:00h · 14일, 7월 → '근태 기록이 없습니다', 주간업무보고 쪽에는 단추 없음. 스크립트 오류 없음.

### 2026-10-13 (22) — 근무시간 막대그래프 색: 평일 파랑 · 주말/공휴일 빨강 · 근태 회색 (APP_VERSION 2026-10-13.22 / SERVER_VERSION 그대로 2026-10-13.9)
- Management › 근무시간 › 이름 클릭 → 날짜별 막대(`renderHours` 의 `bar`): 그날 **근무 시간**을 한 덩어리로 — **평일 = 파랑**(`.hc-work`), **주말·공휴일 = 빨강**(`.hc-off`) — 그 위에 **근태 = 회색**(`.hc-leave`)을 쌓음(예: 반차 4h 근무 + 4h 근태). 근태만 있는 날도 회색 막대로 보임. 막대 위 숫자 = 근무+근태, 마우스 = 근무·PJT·부서업무·기타·근태 내역. 공휴일은 날짜 아래 '휴'.
- 요약줄: 총 근무 · 근무일(근무시간 있는 날) · 일 평균 · **주말·공휴일 근무 ○h (○일)** · 근태 ○h(근무시간에서 제외) · PJT/부서업무/기타 비율(글자).
- **공휴일 목록** `HOLIDAYS` (2024~2027, 대체공휴일·선거일 포함, `isOff(dt)` = 토·일 또는 공휴일). 일별 표 머리글의 빨간 날짜도 공휴일까지. **회사에서 확인할 것**: 목록이 회사 달력과 맞는지(특히 2027년 · 임시공휴일), 회사 휴일(창립기념일 등)·2028년 이후는 `HOLIDAYS` 에 'YYYY-MM-DD' 추가.
- **확인한 것**: `node --check`. 시험 시수 2026-09(평일 8h, 9/5 토 4h, 9/24 추석 6h, 9/10 근태 8h, 9/11 근무 4h + 근태 4h): 막대 평일 파랑 · 9/5·9/24 빨강 · 9/10 회색 · 9/11 파랑+회색, 요약 '주말·공휴일 근무 10:00h (2일)', 머리글 빨간 날 = 주말 + 9/24·25·26·28. 스크립트 오류 없음.

### 2026-10-13 (23) — 내 업무: 매달 첫째 주 '직전 달 시수 파일 올리기' · 🔔 알림은 그 업무 행으로 이동만 (APP_VERSION 2026-10-13.23 / SERVER_VERSION 그대로 2026-10-13.9)
1. **시수 할 일** (`myTasks`, `TS_DUE`, `tsDueMonth`, `tsDueFrom`, `tsDueCheck`): 로그인한 부서원(서버 연결 시)의 '내 업무'(접속 팝업 · 오른쪽 툴바)에 **'⏱ 시수 · ○월 시수 입력 파일 올리기'**(○ = 직전 달).
   - 표시: 매달 **1~7일(첫째 주)**. 직전 달 내 시수 파일(서버 `timesheets?year=` 목록에서 내 ID · 그 달)이 **없으면 '미완료'** — 첫째 주가 지나도 올릴 때까지 계속 표시. 올리면 '완료'(첫째 주 동안만 '완료'로 보이고 그 뒤 사라짐).
   - 누르면 R&R · 투입 분석(#alloc)으로 가서 **시수 올리기 창**이 열림. 올리면(`openTsUpload` 성공 · `loadTs`) 바로 완료로 바뀜.
   - 접속 때 `startOnline` 에서 `tsDueCheck()` 후 `showMyTodo()`.
2. **🔔 통합 업무 알림 클릭** (`startTask` 의 `__ack`): 예전 = 확인완료만. 이제 **확인완료 + 그 업무 행으로 이동**(`jumpTo(key, rid, 제목 칸, false)` — 칸 선택·깜빡임, **편집 창은 열지 않음**).
- **확인한 것**: `node --check`. 날짜를 고정해 시험(김철수, 직전 달 10월): 11/3 미업로드 → '10월 시수 입력 파일 올리기 · 미완료', 누르면 #alloc + 올리기 창 / 11/20 미업로드 → 여전히 미완료 / 10월 올린 뒤 11/3 → '✓ 완료' / 11/20 → 표시 안 됨. 홍길동 🔔 To Do 알림 클릭 → #task 로 이동, 그 행 칸 선택, 편집 창 없음, 툴바 '확인완료'. 스크립트 오류 없음.

### 2026-10-13 (24) — 시수: 코드 없음 + 공통 + Detail 교육 → '교육' (APP_VERSION 2026-10-13.24 / SERVER_VERSION 그대로 2026-10-13.9)
- `tsClass` ③ 에 추가: Project Code 없음 + Type '공통' + Detail 에 **'교육'** 이 들어 있으면(교육 · 안전교육 · 사내교육 …) → **'교육'** (키 `__type:교육`, kind `other` — Type 이 '교육' 인 줄과 같은 한 묶음). 순서: Detail '입찰' → 입찰 먼저, 그다음 '교육', 나머지 → 부서업무. Project Code 가 있으면 전처럼 코드 우선(수행/입찰).
- 근무시간 화면에서는 교육도 근무시간(기타)으로 셈. 설명 문구 갱신.
- **확인한 것**: `node --check`. 시험 시수(이영희 8월: 공통·회의 16h / 공통·입찰 15h / 공통·교육 19h / 공통·안전교육 22h / Type 교육 11h / 공통·교육·A101 23h) → 교육 52h(19+22+11) · 예시수행-B 23h · 부서업무 16h · 입찰 15h. 스크립트 오류 없음.

### 2026-10-13 (25) — 근무시간: 주말·공휴일 출근 현황 · 시수 업로드 월 = 파일 안의 월 (APP_VERSION 2026-10-13.25 / SERVER_VERSION 그대로 2026-10-13.9)
> 회사 운영본은 13.22 → 이번 zip 으로 13.23(시수 할 일 · 알림 이동) · 13.24(공통+교육 → 교육) · 13.25 를 한꺼번에 받음.
1. **Management › 근무시간 — 주말·공휴일 출근 현황** (`renderHours`): 선택 기간(연간/월)에 토·일·공휴일(`isOff`, `HOLIDAYS`)에 근무시간이 있는 날(근태 제외).
   - KPI 칸 **'🗓 주말·공휴일 출근 ○일'** (○명 · ○h).
   - 카드 **'🗓 주말·공휴일 출근 현황'**: 부서원별 출근 일수 · 시간 · 날짜 칩(월/일 · 요일 · 시간, 공휴일은 '공휴일' 표시·진한 빨강). 줄을 누르면 그 사람 날짜별 막대(아래 개인 상세).
2. **시수 업로드 월** (`openTsUpload`): 파일 이름의 'N월'이 아니라 **파일 안의 월**(머리글 '2026-07' 등)로 저장 — 찾으면 '저장할 월' 칸을 그 값으로 **고정**(바꿀 수 없음), 이름과 다르면 'ℹ 파일 이름은 6월이지만 파일 안의 월 2026-07 로 저장합니다'. 파일 안에서 월을 못 찾을 때만 직접 고름.
- **확인한 것**: `node --check`. 근무시간 연간 '주말·공휴일 출근 31일 4명', 9월 14일 · 카드에 9/6(일) · 9/24·25·28(공휴일) 등, 줄 클릭 → 개인 막대. 받은 6월 파일(이름 6월 · 안 2026-07) 끌어다 놓기 → 저장할 월 2026-07 고정 + 안내. 스크립트 오류 없음.

### 2026-10-13 (26) — LOGIC 분석 메뉴 (P&ID 분석과 같은 방식) (APP_VERSION 2026-10-13.26 / SERVER_VERSION 2026-10-13.11)
> **서버 재시작 필요** (server.py: 메뉴 권한 목록에 LOGIC 분석). SERVER_VERSION 은 되돌린 13.10 과 겹치지 않게 13.11.
- 메뉴 **'🔀 LOGIC 분석'** (route `logic`, P&ID 분석 바로 아래). P&ID 분석과 같은 틀(`PID_ROUTES` 를 일반화): 대시보드 서버와 **같은 호스트의 포트 8001**(`PID_ROUTES.logic.port`)에서 `/version`(JSON) 을 3초 안에 확인 → 되면 `/?embed=1&user=본명` 을 화면 가득 iframe, 안 되면 'LOGIC 분석 서버가 꺼져 있습니다 — LOGIC 분석 서버(포트 8001) 을 확인하세요' + [다시 시도]. 위쪽 '새 창으로 열기 ↗'.
  - `pidBase(key)`, `pidUrl(key)`, `renderPid`, `pidConnect` 가 key 별 제목·포트·안내(`svc`) 사용. P&ID(8000) 동작은 그대로.
- **LOGIC 분석 도구 자체는 아직 없음** — 별도 프로그램(P&ID 추출 도구처럼)을 포트 8001 로 띄우면 연결됨. 필요한 것: `GET /version` → JSON, `GET /?embed=1&user=…` → 화면, 다른 출처(iframe) 허용.
- 메뉴 권한: server.py `MENUS` 에 `('logic', 'LOGIC 분석')` → ⚙ 메뉴 권한 설정에 칸 생김, 기본 허용(`DEFAULT_PERMS`).
- **확인한 것**: `node --check`, `py_compile`. 시험: 메뉴 순서 P&ID 분석 → LOGIC 분석, 8001 꺼짐 → 안내·다시 시도, 시험용 가짜 LOGIC 서버(8001) 켬 → [다시 시도] → iframe(`http://서버:8001/?embed=1&user=홍길동`)에 화면 표시, P&ID 분석은 그대로(8000 안내), 권한 목록·info.perms 에 logic. 스크립트 오류 없음.
