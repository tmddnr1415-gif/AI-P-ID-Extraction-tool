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
