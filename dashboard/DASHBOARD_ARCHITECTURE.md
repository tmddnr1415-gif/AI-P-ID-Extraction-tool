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
| GET `space/projects` · POST `space/projects` `{name}` · GET `space/{pid}` · GET `space/{pid}/saves/{sid}` · POST `space/{pid}/saves` `{data, memo, sum}` · POST `space/{pid}/notes` `{text}` · DELETE `space/{pid}/notes/{nid}` · GET `space/recent?n=` (모든 프로젝트 최근 저장) | 판넬 공간확보 서버 저장 (2026-10-22~). 운영 폴더 `space/{pid}/index.json`(프로젝트 · 저장 메타 · 노트) + `space/{pid}/saves/{sid}.json`(배치안). 보기 = 누구나, 쓰기 = 로그인 + `space` 권한, 노트 삭제 = 본인 · 운영자/그룹장. 일일 백업 포함 |
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

### 방법 A' (2026-10-22~): 같은 서버 `apps/` 앱을 P&ID 와 같은 화면 틀로 — `APP_ROUTES`
- 예: **판넬 공간확보** = `APP_ROUTES.space = { title:'판넬 공간확보', src:'/apps/space/index.html' }`, 파일은 운영 폴더 `apps\space\index.html` (저장소 `dashboard/apps/space/index.html`).
- `MODULES`(카드 안 iframe)와 달리 본문 전체를 채우고(`pid-mode`), 1분 자동 갱신에도 iframe 을 다시 만들지 않는다(`#pidwrap` 유지) — 편집 중인 화면이 날아가지 않음. 위쪽 주간업무 버튼은 숨김.
- 주소 뒤 값: `?embed=1&user=<본명>`. 앱은 `embed=1` 이면 자기 제목줄을 숨긴다.
- 추가하려면: `APP_ROUTES` 에 한 줄 · `ROUTES` 에 키 · `renderMenu()` 에 `btn(...)` 한 줄 · (권한 표에 넣으려면) server.py `MENUS` 에 `(키, 이름)`.

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

### 2026-10-13 (27) — 시수 파일 여러 개 한꺼번에 올리기 (APP_VERSION 2026-10-13.27 / SERVER_VERSION 그대로 2026-10-13.11)
- `openTsUpload(files)`: 올리기 창 놓기 칸 · R&R 화면 아무 곳에 **여러 .xlsx 를 한꺼번에** 끌어다 놓거나 파일 고르기(`multiple`)로 여러 개 선택 가능. 1개면 예전 그대로(미리보기 상세 · 월 고정).
- 여러 개(`takeMany`): 파일마다 서버 미리보기(`POST timesheet/preview`, 저장 안 함)를 차례로 → 한 표: 파일 · **저장할 월 = 파일 안의 월** (못 찾으면 그 줄에서 직접 고름) · 시간 있는 줄 수 · 합계 · 분류 막대 · 상태. 월 순서로 정렬. **.xlsx 가 아닌 파일은 빼고 안내**, **같은 달 파일이 여럿이면 '중복' 표시 + 아래쪽(나중) 것이 덮어씀** 안내.
- [⬆ N개 업로드 · 분석] → 같은 부서원(위 선택)으로 하나씩 `PUT timesheet?…&useMonth=1` → 모두 되면 창 닫고 연간 보기로 다시 그림, 실패가 있으면 창에 남기고 상태 칸에 이유.
- **확인한 것**: `node --check`. 시험: 박민수 1~6월 6개 + 3월 수정본 + 메모.txt 를 R&R 화면에 한꺼번에 놓기 → 7개 표(월 2026-01~06, 3월 '중복'), txt 제외 안내 → [7개 업로드] → 서버에 1~6월 저장(3월은 수정본). 파일 1개 올리기(받은 6월 파일 → 2026-07 고정)도 그대로. 스크립트 오류 없음.

### 2026-10-13 (28) — LOGIC 분석 메뉴를 실제 LOGIC 검토 화면(P&ID 서버 8000 의 /logic)에 연결 (APP_VERSION 2026-10-13.28 / SERVER_VERSION 그대로 2026-10-13.11)
- 13.26 에서 LOGIC 분석을 '별도 서버 8001' 로 잡았던 것을 바로잡음: LOGIC 검토는 **P&ID 추출 도구와 같은 서버(부서장 PC 8000)** 에 들어 있음 — 브랜치 `claude/logic-review-design-pd2z75`(L1~L19)를 P&ID 브랜치에 결합(hotfix89~), 화면 주소 **`/logic`** (`app/logic/api.py` 의 `GET /logic` → `logic.html`, `?user=` 를 작성자 이름으로 읽음).
- `PID_ROUTES` 에 `path` 추가: pid → `/`, logic → `/logic`(포트 둘 다 `PID_PORT` 8000). iframe 주소 `http://<대시보드 서버 호스트>:8000/logic?embed=1&user=<본명>`. 살아 있나 확인은 같은 `/version`. 꺼져 있으면 '…부서장 PC 의 run_lan_service.bat (P&ID 분석과 같은 서버)' 안내.
- 필요 조건: 부서장 PC 의 P&ID 도구가 LOGIC 이 결합된 판(hotfix89 이후, 최신 hotfix93)이어야 함. 그 전 판이면 /logic 이 없어 iframe 에 404.
- **확인한 것**: `node --check`. 실제 P&ID 도구(브랜치 claude/titleblock-parsing-c5st4x = hotfix93 · LOGIC L19)를 시험 PC 에서 8000 으로 켜고 대시보드 → '🔀 LOGIC 분석' → iframe `…:8000/logic?embed=1&user=홍길동`, 화면 제목 'LOGIC 검토', 'Logic 분석 · 어디에 넣을지 · 자료(Logic Diagram 필수 · Loop · System Description · IO List · Logic Table)' 표시. P&ID 분석은 `…:8000/?embed=1&user=…` 그대로. 스크립트 오류 없음.

### 2026-10-13 (29) — 근무시간: 부서원을 누르면 위 숫자가 그 사람 값 · 하루 8시간 기준 · 주 52시간 칸 삭제 (APP_VERSION 2026-10-13.29 / SERVER_VERSION 그대로 2026-10-13.11)
- Management › 근무시간 위 KPI 칸(`renderHours` 의 `kdl` · `kTot` · `kPM` · `kOver8` · `kOff`): 표·주말 현황에서 **부서원 이름(줄)을 누르면**(`HS.person`) KPI 가 **그 사람 값**, 안 누르면 팀 전체. 큰 칸에 '팀 전체 보기' 단추.
  - 칸: **총 근무시간** · **(1인) 월 평균** = 근무시간 ÷ 근무시간이 있는 (사람×)달 수 · **근무일 평균** · **하루 8시간 초과** 일수(최장일) · **주말·공휴일 출근일** · **주말·공휴일 근무시간**(하루 평균). **'주 52시간 초과' 칸은 뺌**.
- 일별 표의 붉은 칸 기준 하루 10시간 → **8시간**(머리글 안내도). 주별 표는 주 52시간 초과 붉게 그대로.
- **확인한 것**: `node --check`. 9월 팀: 753h · 1인 월 평균 188:15 · 8시간 초과 47일 · 주말·공휴일 14일 111h → 홍길동 누름: 150h · 월 평균 150h · 근무일 평균 7:30 · 8시간 초과 0일 · 주말·공휴일 2일 · 10h(시험 파일과 같음) → 연간으로 바꿔도 홍길동 값 유지 → '팀 전체 보기'로 복귀. 일별 9월 붉은 칸 = 8시간 초과. 스크립트 오류 없음.

### 2026-10-13 (30) — LOGIC 분석 메뉴를 요청 사양 그대로 (APP_VERSION 2026-10-13.30 / SERVER_VERSION 그대로 2026-10-13.11)
- 요청 사양: 주소 `http://<P&ID 서버 PC>:8000/logic?user=<로그인 이름>`(P&ID 메뉴와 같은 서버 주소, /logic 만 다름) · 살아 있나 = `:8000/version` · 꺼져 있으면 P&ID 와 같은 안내 · user = P&ID 메뉴와 같은 로그인 이름(LOGIC 메모 작성자).
- 13.28 과 다른 점 두 가지를 맞춤: ① LOGIC 주소에서 `embed=1` 을 뺌 → `/logic?user=본명` (P&ID 는 그대로 `/?embed=1&user=본명`, `PID_ROUTES[key].q`) ② 꺼졌을 때 안내를 두 메뉴 모두 **'P&ID 서버가 꺼져 있습니다 — 부서장 PC 의 run_lan_service.bat 을 확인하세요'**(`PID_OFF`).
- **확인한 것**: `node --check`. 8000 꺼짐 → LOGIC · P&ID 모두 같은 안내 + 다시 시도. 실제 P&ID/LOGIC 도구(hotfix93)를 8000 으로 켬 → LOGIC iframe `http://서버:8000/logic?user=홍길동`, 화면 제목 'LOGIC 검토', 도구 쪽 `user` = 홍길동 / P&ID iframe `…:8000/?embed=1&user=홍길동` 그대로. 스크립트 오류 없음.

### 2026-10-14 (31) — 수행·입찰 행 추가 → 정렬·필터와 상관없이 맨 위 + 그 행으로 이동 (APP_VERSION 2026-10-13.31 / SERVER_VERSION 그대로 2026-10-13.11)
- 13.8 부터 새 행의 order = 가장 작은 order − 10 이라 **기본 순서**에서는 맨 위였지만, ① 머리글 ▾ **열 정렬**을 걸어 두면 정렬 자리로 들어가고 ② 사업군 등 **필터**에 안 맞으면 안 보이고 ③ 화면을 내려 둔 상태면 위가 안 보여 '맨 위로 안 올라간다' 로 보였음.
- `submitRecord`(새 행, 수행·입찰): 만든 행 id 를 `NEW_TOP[시트]` 에 넣고 `filteredRecs` 마지막에 **정렬·필터와 상관없이 맨 위에 고정**(이 화면을 새로고침할 때까지 — 새로고침 뒤에는 order 가 가장 작아 기본 순서에서 맨 위). 그리고 `JUMP` 로 그 행의 PJT명 칸으로 **스크롤 + 깜빡임**.
- **확인한 것**: `node --check`. 시험: 화면을 내린 상태에서 추가 → 맨 위 · 보임 / PJT명 오름차순 정렬 중 '가가…' · '하하…' 추가 → 둘 다 각각 맨 위 / 사업군 'LNG' 필터 중 '발전' 행 추가 → 맨 위에 보이고 깜빡임 / 새로고침 → 맨 위. 스크립트 오류 없음.

### 2026-10-14 (1) — [금주 마감] = 바로 마감하고 다음 주차로 (APP_VERSION 2026-10-14.1 / SERVER_VERSION 2026-10-14.1)
> **서버 재시작 필요** (server.py).
- 예전: [금주 마감] 은 그 시각 데이터를 이번 주 마감본으로 '미리' 저장할 뿐, 주차는 수요일 12:00 까지 그대로였고 수요일 자동 마감이 그 마감본을 다시 덮어씀.
- 이제: **누르지 않으면** 지금처럼 수요일 11:59 에 자동 마감. **누르면** 그 순간 이번 주차로 마감하고 **바로 다음 주차로 넘어감**.
  - server.py: `api_close` 가 `state.json` 에 `manualClosedWeek` = 마감한 주차 기록. `iso_week()` 는 시간으로 정한 주차가 `manualClosedWeek` 이하이면 그다음 주(`manual_closed_week`). `auto_close` 는 그 주 마감본이 수동이고 `manualClosedWeek` ≥ 그 주면 덮어쓰지 않음(예전 방식으로 만든 수동 마감본은 전처럼 수요일에 자동 마감으로 다시 저장).
  - dashboard.html: `curWeek()` 도 `DB.state.manualClosedWeek` 를 반영(머리글 주차 · 마감 날짜 · 주차 선택 · 금주 업데이트 기준). 마감 확인 창 문구 '바로 마감하고 다음 주차 ○○ 로 넘어갑니다'. 폴더 모드 마감도 같은 값 기록.
- **확인한 것**: `node --check`, `py_compile`. 서버 함수 시험: 화요일 15:00 [금주 마감] → W42 마감, 지금 주차 W43(화·수 오전 모두), 다음 수요일 12:01 → W44 / 수요일 12:00 자동 마감 → W42 는 건너뜀(수동 마감본 그대로) / 다음 주 수요일 자동 마감 → W43 정상 저장. 화면 시험(관리자): 머리글 '2026-W42 · 마감 10/14(수)' → [금주 마감] → '2026-W43(1021) · 마감 10/21(수) 11:59', 주차 선택 'W43 (현재) / W42 마감본 / W41 마감본', 서버 info.week = W43. 스크립트 오류 없음.

### 2026-10-15 (1) — 수행·입찰 담당자 그래프: 이름이 들어 있으면 카운트 · 마우스 = 미리보기 · 클릭 = 그 사람 PJT 만 / 계정 비밀번호 변경 (APP_VERSION 2026-10-15.1 / SERVER_VERSION 2026-10-15.1)
> **서버 재시작 필요** (server.py).
- 무엇을: 수행·입찰 위 담당자 그래프의 숫자 = **담당자 칸에 그 사람 이름이 들어 있는 진행 PJT 수**. 예전에는 칸 값을 이름 하나로 잘라 맞췄기 때문에 '홍길동 프로', 'PM 김철수', '박민수(LE), 홍길동', 줄바꿈으로 두 사람 등은 빠지거나 덜 셌음. 왜: 사진(W43)에서 부서원 숫자가 실제보다 적게 나옴.
  - dashboard.html: `nk`(공백 없앤 이름) · `hasName(칸값, 이름)` = 공백 무시 포함 비교(이름 2글자 이상). `pjHero` 담당자 막대 = 부서원 명단(`deptNames`) + 명단에 없는 담당자 토큰, 각자 `hasName` 으로 셈.
  - 막대에 마우스 → 미리보기(`data-tip`): '이름 · 진행 N건 (+종결 M)' + PJT명 · 사업군 목록.
  - 막대 클릭 → 담당자 필터 = 그 이름(`filteredRecs` 의 담당자 조건도 `hasName` 포함 비교) → 그 사람이 들어 있는 PJT 만 표에. 표는 종결 필터를 따로 안 걸었으면 종결 PJT 도 보임(그래프 숫자는 진행만).
- 무엇을: **계정 비밀번호 변경**. 오른쪽 위 계정 메뉴 → '🔑 비밀번호 변경'(서버 연결 때만) → 지금 비밀번호 · 새 비밀번호 · 새 비밀번호 확인.
  - server.py `api_change_pw` · 경로 `POST /api/auth/password` (로그인 필요): 지금 비밀번호 확인(틀리면 로그인과 같은 횟수 제한), 새 비밀번호 규칙 = `check_pw`, 지금과 같으면 거절 → 새 salt·hash 저장, `pwChangedAt`, 그 사람의 다른 로그인(세션) 모두 끊고 새 토큰을 돌려줌(이 화면은 그대로 로그인 유지).
  - dashboard.html `openChangePw`.
- **확인한 것**: `node --check`, `py_compile`. 시험 데이터(담당자 '홍길동 프로\n이영희 프로' · 'PM 김철수' · '홍길동 이영희' · '박민수(LE), 홍길동') → 그래프 홍길동 3 · 김철수 2 · 이영희 2 · 박민수 1. 마우스 → '홍길동 · 진행 3건 (+종결 1) 예시수행-A 발전 …'. 홍길동 클릭 → 표 A·C·D·G(G 종결), 김철수 클릭 → B·H. 비밀번호: 틀린 지금 비밀번호 → '지금 비밀번호가 맞지 않습니다' / 바꿈 → 옛 비밀번호 로그인 실패 · 새 비밀번호 로그인 성공 · 새로고침해도 로그인 유지. 스크립트 오류 없음.
- **회사에서 확인할 것**: 서버 재시작 뒤 Ctrl+F5. 이름이 다른 이름 안에 들어가는 경우(예: '김철'과 '김철수')는 둘 다 셈 — 부서에 그런 이름이 있으면 알려줄 것.

### 2026-10-15 (2) — 행 순서 옮기기 · 새 행 노란 줄 · IEC 인력 · 부서원 생일 · 근로시간 관리(52h) (APP_VERSION 2026-10-15.2 / SERVER_VERSION 2026-10-15.2)
> **서버 재시작 필요** (server.py). 새 폴더 `worktime/` 은 서버가 만듦(자동 백업에도 포함). 생일 명단 = `profiles/_birthdays.json`.
- **행 추가 → 맨 위 / 행 옮기기** (수행 · 입찰 · 통합 업무, `TOP_NEW`)
  - 통합 업무도 새 행 order = 가장 작은 order − 10 + `NEW_TOP` 고정 + 그 행으로 이동 (`submitRecord`). 예전 통합 업무는 같은 유형 맨 뒤에 들어갔음.
  - 표 위 **[⬆ 위로] [⬇ 아래로]** (또는 **Alt+Shift+↑/↓**): 선택한 셀의 행을 지금 표에 보이는 바로 위·아래 행과 order 맞바꿈 (`moveRow`). 서버 `PUT /api/order/{시트}` `{orders:{행ID:order}}` (`api_reorder`, 주간업무보고 권한) — 내용·rev·수정 이력은 그대로. 열 정렬(▾) 중에는 안 됨, 통합 업무는 같은 유형 안에서만, 서버 연결 때만.
- **새로 추가한 행 = 행 전체 노란 음영** (`rowAttr` 의 `newrow`: 마지막 마감 이후 새로 생긴 행(`hlOf(r).all`) · 방금 추가한 행). 작업 칸까지 노랗고 왼쪽에 진한 노란 줄. 표 아래 범례 '노란 행 = 새로 추가한 행'.
- **수행** 열 이름: '계장ENG 업무 현황' → **'업무 현황'**, '계장ENG 현안 (Cost/Schedule Impact)' → **'현안 (Cost/Schedule Impact)'** (필드 이름은 그대로 — 데이터 변화 없음). 입찰은 그대로.
- **IEC 인력 (India Engineering Center, 영문 이름)**
  - 수행 PJT 담당자 그래프: 영문 이름은 **세지 않음**. 입찰 PJT 그래프: IEC 명단(`iecNames`) + 담당자 칸의 영문 이름을 **셈** (막대 옆 'IEC' 표시). `pjHero`.
  - 부서원 명단(`deptNames`)에서 IEC 유닛·영문 이름은 뺌 (할 일·근무시간 등 다른 집계에 안 섞이게).
  - 유닛분장 조직도: Unit 1 · Unit 2 오른쪽에 **I&C ENG Group (IEC 인력 구성)** — 유닛 이름이나 담당에 'IEC' 또는 'I&C ENG' 가 들어간 유닛(`isIecUnit`). 표에 아직 없으면 가장 최근 연도에 기본 명단(`IEC_DEFAULT`: Part Leader Ranjit Malakar + Pro 11명, 받은 사진 그대로)을 보여 주고, 유닛 제목을 누르면 **[표에 등록]** → 유닛분장 행이 생겨 그다음부터 고칠 수 있음(`iecRegister`). 'Part Leader' 도 유닛장처럼 ★.
- **부서원 생일** (Management › 부서원 생일 `mgbday`, `renderBday`)
  - 명단: 이름 · 직급 · 생일(월·일) · 양력/음력. 생일 엑셀(사진 양식: 이름 · 직급 · 생일 '10월 13일' · 양력 '생일(양)/생일(음)')을 올리면 미리보기 후 명단 교체, 한 명씩 추가·고치기·삭제. 서버 `GET /api/birthdays`(로그인) · `PUT /api/birthdays` · `POST /api/birthdays/preview`(엑셀 읽기) — 고치기는 Management 권한.
  - 생일 **하루 전 · 당일**: 로그인한 모든 부서원 화면에 **폭죽 + 축하 팝업** ('오늘은 ○○○ 프로의 생일입니다! 축하해 주세요') — 브라우저·계정마다 하루 한 번(`bdayCheck`, localStorage `dept-bday-shown`). 폭죽은 canvas 로 직접 그림(`fireworks`).
  - 생일 **당일**: 유닛분장 조직도의 그 사람 사진과 왼쪽 위 로그인 이름에 **고깔모자**(`HAT` SVG), 이름 옆 🎂.
  - 음력 생일은 브라우저의 한국 음력 달력(`Intl` 'dangi')으로 그해 양력 날짜 계산(`lunarToSolar`, 음력 30일이 없는 달은 29일). 2/29 양력은 평년에 2/28.
- **근로시간 관리 (52h)** (Management › 근로시간 관리 `mgwork`, `renderWork`)
  - 회사 근태 시스템의 월별 근무시간 엑셀(첨부 양식: 1~2행 머리글 — 작업년월 · 성명 · 사번 · 부서명 · 직급명 · 근무스케줄타입 · 근무조 · 근무상태 · 평일의무/평일근무 · 실근무(평일+휴일) 상태/시간 · 주평균근무 상태/시간 · 연장 · 심야 · 휴일 · 휴일연장 · 탄력(+/−) · 월잔여 최대근무가능/소정)을 올림 — 여러 개 한꺼번에, 끌어다 놓기 가능. 서버 `parse_worktime` · `GET/PUT /api/worktime` · `DELETE /api/worktime/{ID}` — **보기·올리기·지우기 모두 Management 권한**. 저장 `worktime/uploads/{ID}.json` + 원본 `worktime/raw/{ID}.xlsx`.
  - 같은 사람(사번, 없으면 이름)·같은 달이 여러 파일에 있으면 나중에 올린 파일 값. 파일을 지우면 그 파일 값만 빠짐.
  - 판정(`wtJudge`): 기준 = 주 평균 소정 40h · 월 평균 주 52h. **위험** = 주 평균 52h 초과 또는 파일 판정 '위험' / **우려** = 주 평균 48h 이상 또는 파일 판정 '우려' 또는 월잔여 최대근무가능 10h 이하. 주 평균 = 파일의 '주평균근무 시간'(없으면 실근무 ÷ (그달 일수 ÷ 7)). 기준값은 `WT_STD` · `WT_MAX` · `WT_WARN` · `WT_REMAIN`.
  - 화면: 월 탭 → KPI(팀 주 평균 · 위험 · 우려 명단 · 최고 주 평균 · 연장 합계 · 휴일근무 합계) + 부서원 표(판정 · 실근무 · 주 평균 막대(40h 점선 · 52h 빨간 선) · 40h 대비 · 연장 · 심야 · 휴일 · 탄력 · 월잔여 · **시수 파일 합계(근태 제외, 8h 이상 차이면 Δ)** · 사유) / '월별 추이' = 부서원 × 월 주 평균 표 / 이름을 누르면 그 사람의 달별 막대 + 표. 근무시간(월·주·일) · R&R · 투입 분석으로 가는 단추.
  - 숫자 칸은 시간(h)으로 읽음 (`194.07` = 194.07시간, '194:07' 처럼 쓰면 194시간 7분).
- **확인한 것**: `node --check`, `py_compile`, 받은 Foramt.xlsx 읽기(6달 1명, 2026.07 실근무 '우려' · 주평균 '위험'). 시험 서버 화면 시험(시험 계정 · 임시 폴더):
  - 수행 열 머리 '업무 현황 | 현안 (Cost/Schedule Impact)'. 수행 그래프 김철수 2 (담당 'PM 김철수\nNikhil Aggarwal' 에서 영문 안 셈) / 입찰 그래프 Abhishek Sinha 1 · Nikhil Aggarwal 1 (IEC 표시) + IEC 나머지 0.
  - 통합 업무 행 추가 → 맨 위 + 노란 행. 수행 행 추가 → 맨 위 노란 행. 3번째 행 [⬆ 위로] → 2번째 / Alt+Shift+↓ 두 번 → 4번째 / 새로고침해도 유지.
  - 조직도: UNIT 1 | UNIT 2 | I&C ENG Group (IEC 12명, Ranjit Malakar ★) → [표에 등록] → 표 행으로 바뀜.
  - 생일 엑셀 6명 → 미리보기 → 저장, 음력 9/20 → 2026-10-30, 2/29 → 2/28. 홍길동 화면: 팝업 '오늘은 백그룹 그룹장, 홍길동 프로의 생일입니다! … 내일(10/16)은 김철수 프로의 생일입니다!' + 폭죽, 조직도 고깔모자 2개 · 로그인 이름 고깔모자, 새로고침하면 팝업 다시 안 뜸.
  - 근무시간 엑셀 2개(시험 파일 4명·4달 + Foramt.xlsx) 올림 → 2026.09: 위험 홍길동(55h) · 우려 김철수(49h), 2026.10 홍길동 51h + 잔여 7.5h → 우려, 월별 추이 · 개인 막대, 파일 하나 삭제 → 그 파일 달만 빠짐. 일반 부서원은 /api/worktime 403. 스크립트 오류 없음.
- **회사에서 확인할 것**: 서버 재시작 + Ctrl+F5. 근태 시스템 엑셀의 시간 숫자가 '194.07' 처럼 소수면 시간(h)으로 읽음 — 실제로 '시:분' 뜻이면 알려 줄 것. 음력 생일 날짜는 Chrome/Edge 의 음력 달력으로 계산(그 밖의 브라우저는 '계산 안 됨').

### 2026-10-15 (3) — 생일 팝업 바로 · 매번 · 오늘 하루 안 보기 / 주 소정근로시간 공휴일 차감 / 근무시간 숫자 칸 → 부서원별 상세 (APP_VERSION 2026-10-15.3 / SERVER_VERSION 2026-10-15.3)
> **서버 재시작 필요** (server.py: 생일 명단 보기 로그인 불필요).
- **생일 팝업** (생일 하루 전 · 당일)
  - 예전: 로그인한 사람에게 하루 한 번, 데이터를 다 받은 뒤 0.8초 뒤.
  - 이제: **화면(dashboard.html)을 열 때마다 · 로그인할 때마다** 뜸. 열자마자 이 PC 에 보관한 명단(localStorage `dept-bday-cache`)으로 바로 띄우고(`bdayBoot`, init 첫 줄), 서버 명단은 로그인 창보다 먼저 기다리지 않고 받음(`startOnline` 첫 줄). 로그인하면 다시(`afterAuth`). 1분 자동 갱신 때는 다시 안 띄움(`BD.shown`).
  - 비회원 화면에도 뜸: 서버 `GET /api/birthdays` 로그인 불필요(이름·직급·월일만). 오프라인으로 연 파일도 보관 명단으로 뜸.
  - **[오늘 하루 안 보기]**: 누르면 그날(같은 생일자)은 이 브라우저에서 안 뜸 (localStorage `dept-bday-hide` = 날짜|이름들).
  - `<dialog>`(showModal)로 바꿈 → 로그인 창·업데이트 안내가 떠 있어도 그 위에 바로 보임. Esc 로도 닫힘.
- **근로시간 관리 (52h) — 주 소정근로시간 = 40h − 평일 공휴일 × 8h** (`wtStd`)
  - 예) 월요일이 공휴일인 주 = 32h. 달 단위 = 40h × (그달 일수 ÷ 7) − 평일 공휴일 수 × 8h = 월 소정 → ÷ (일수 ÷ 7) = **그달 주 평균 소정** (공휴일 없는 달 = 40h). 토·일과 겹친 공휴일은 빼지 않음. 공휴일 = `HOLIDAYS`(2024~2027, 회사 휴일은 여기에 더함).
  - '40h 대비' 열 → **'소정 대비'** (머리에 그달 주 소정, 마우스 = 계산식), KPI '주 소정 ○○h (공휴일 n일 반영)', 막대 점선 = 그달 소정, 개인 막대에 달마다 소정 점선, 개인 표에 '주 소정' · '소정 대비' 열. 위험·우려 판정(52h · 48h · 잔여 10h)은 그대로.
- **근무시간 (월·주·일) — 위 숫자 칸을 누르면 부서원별 상세** (`HS.kpi`, `kpiDetail`)
  - 1인 월 평균(사람별 총·근무한 달·월 평균 + 달별) · 근무일 평균(근무일·총·하루 평균) · 하루 8시간 초과(초과한 날·최장·초과 시간 합 + 날짜) · 주말·공휴일 출근일 / 근무시간(일수·시간·하루 평균 + 날짜). 많은 순. 줄을 누르면 그 사람 값 · 날짜별 막대(기존). 다시 누르거나 [닫기] = 닫힘.
  - 함께 고침: 시수 칸 합의 반올림 찌꺼기(예: 8.0001h)를 '8시간 초과'·붉은 칸으로 세던 것 → 30초 여유(`EPS_H`).
- **확인한 것**: `node --check`, `py_compile`. 시험 서버: 비회원으로 처음 열기 → 0.3초 만에 팝업(서버 명단) · 다시 열기 → 0.1초(보관 명단) · [오늘 하루 안 보기] 후 다시 열기 → 안 뜸 · 로그인한 부서원 화면 팝업 + 두 단추. 근로시간: 2026.07 소정 40h, 08 38.2h(8/17), 09 34.4h(9/24·25·28), 10 36.4h(10/5·10/9) → 소정 대비 다시 계산. 근무시간 연간: 다섯 칸 모두 눌러 상세 표(8시간 초과 김철수 70일 → 54일로 바로잡힘), 줄 누르면 그 사람 값, 닫기. 스크립트 오류 없음.
- **회사에서 확인할 것**: 서버 재시작 + Ctrl+F5. 부서원 파일(dashboard.html)은 새 버전으로 바꾸면 서버가 꺼져 있어도 보관 명단으로 팝업.

### 2026-10-15 (4) — 생일 팝업: 로그인할 때 · html 을 켤 때 · 그 사용자가 '오늘 하루 안 보기' 누르기 전까지 (APP_VERSION 2026-10-15.4 / SERVER_VERSION 그대로 2026-10-15.3)
- 무엇을·왜: 15.3 은 ① '오늘 하루 안 보기' 가 그 PC(브라우저) 전체에 걸려 같은 PC 의 다른 사람도 안 보였고 ② 로그인 화면이 뜨는 경우 팝업이 로그인 전에 먼저 떠서 로그인한 뒤에는 안 떴고 ③ 바로 뒤에 뜨는 '내 할 일' 창이 팝업을 덮어 단추를 못 누름.
- 이제 (`bdayCheck` · `bdayBoot` · `startOnline` · `afterAuth` · `bdRaise`):
  - **html 을 켤 때**: 저장된 로그인이 있으면 바로(이 PC 보관 명단), 없으면 로그인 화면에서 로그인(또는 비회원 보기)한 뒤.
  - **로그인할 때마다**(사용자가 바뀌면) 다시. 같은 화면·같은 사용자에게는 한 번(1분 자동 갱신·새로고침 단추 때는 다시 안 뜸, `BD.shownFor`).
  - **[오늘 하루 안 보기]** 는 **그 사용자만**(계정 ID, 비회원은 'guest') 그날 안 뜸 — localStorage `dept-bday-hide` = 오늘 키 목록(날짜|생일자|사용자).
  - 팝업이 떠 있는 동안 다른 창(내 할 일 · 업데이트 안내 · 확인 창)이 열려도 팝업이 맨 위(`openDlg` → `bdRaise`).
  - 오프라인으로 연 파일도 보관 명단으로 팝업.
- **확인한 것**: `node --check`. 시험 서버(같은 브라우저): 처음 켬 → 로그인 화면(팝업 없음) → 홍길동 로그인 → 팝업(내 할 일 창 위) → 다시 켬 → 0.13초 만에 팝업 → [오늘 하루 안 보기] → 다시 켜도 안 뜸 → 로그아웃 후 김철수 로그인 → 팝업 → 새로고침 단추 → 다시 안 뜸 / 새 브라우저 비회원 보기 → 팝업. 스크립트 오류 없음.
- **회사에서 확인할 것**: Ctrl+F5 (server.py 는 안 바뀜, 15.3 서버 그대로). 부서원 파일은 새 버전으로 교체.

### 2026-10-15 (5) — 근로시간 관리: 연장 = 소정근로시간 초과 전부 / 심야는 근태 시스템 값 (APP_VERSION 2026-10-15.5 / SERVER_VERSION 그대로 2026-10-15.3)
- 무엇을·왜: 요청 "평일 소정 주 근로시간을 초과하면 모두 연장". 예전 '연장' 칸은 근태 시스템 엑셀의 '연장근로시간' 그대로라 '소정 대비' 와 맞지 않았음.
- 이제 **연장 = 실근무(평일+휴일) − 그달 월 소정** (`wtOt`) — 월 소정 = 40h × (일수 ÷ 7) − 평일 공휴일 × 8h (`wtStd`, 15.3). 곧 (주 평균 − 주 소정) × 그달 주 수. 근태 시스템 값은 칸 아래 '시스템 ○○' 로 작게, 마우스 = 계산식. KPI '연장근로 합계' · 개인 막대 풍선도 같은 값.
- **심야(오후 8시부터)**: 엑셀에는 달 합계만 있고 출퇴근 시각이 없어 계산할 수 없음 → '심야' 칸은 근태 시스템 값 그대로, 머리에 '근태 시스템 값'(마우스 = 이유). 일별 출퇴근 시각 파일을 받으면 20:00 이후를 세도록 바꿀 것.
- 한계: 진행 중인 달은 실근무가 오늘까지이고 월 소정은 그달 전체라 연장이 적게(0) 나옴 — 달이 끝난 뒤 파일 기준.
- **확인한 것**: `node --check`. 2026.09(월 소정 147.4h): 홍길동 실근무 235.7 → 연장 88.3 (= +20.6 × 30/7, 시스템 67.7), 김철수 210 → 62.6, KPI 합계 220.3h. 스크립트 오류 없음.

### 2026-10-15 (6) — 생일 팝업 계정(로그인)마다 · 본인 축하 인사 / 근로시간 관리 엑셀 값 우선 + 엑셀 기준 확인 (APP_VERSION 2026-10-15.6 / SERVER_VERSION 2026-10-15.4)
> **서버 재시작 필요** (server.py: 생일 '오늘 하루 안 보기' 를 계정마다 서버에 저장).
- **생일 팝업 = 로그인한 사람 기준**
  - '오늘 하루 안 보기' 를 그 **계정**에 저장: server.py `api_bday_hide` · `POST /api/birthdays/hide` → `profiles/_bdhide.json` {계정ID: [오늘 키]} (오늘·어제 것만 남김). `GET /api/birthdays` 가 로그인한 사람의 키를 `hidden` 으로 돌려줌 → 그 사람의 **다른 PC 에서도** 그날은 안 뜸, 같은 PC 의 다른 사람에게는 뜸. 이 PC(localStorage)에도 같이 기록(오프라인용).
  - html 을 켤 때: 서버 명단(그 사람의 안 보기 포함)으로 바로, 서버가 안 닿으면 1.5초 뒤 이 PC 보관 명단으로(`bdayBoot`).
  - 로그인한 사람이 **오늘 생일**이면 맨 위에 '○○○ 프로님, 생일 축하합니다!' (`showBdayPop` 의 `me`), 다른 생일자는 그 아래.
- **근로시간 관리 — 엑셀 값 우선, 계산은 비교** (`wtStd` · `wtWeeks` · `wtCal` · `wtMon` · `wtCmp` · `wtBasis`)
  - 주 평균 = 엑셀 '주평균근무'(없으면 실근무 ÷ 엑셀이 쓰는 주 수). 월 소정 = 엑셀 '평일의무근로시간'(그 사람 값, 없으면 달력). 연장 = 엑셀 '연장근로시간'. 칸 아래 작게 '계산 ○○'(연장 = 실근무 − 월 소정, 소정 초과 전부 / 월 소정 = 달력), 1h 이상 다르면 주황 Δ.
  - 달력 계산 바꿈: 월 소정 = (평일 − 평일 공휴일) × 8h (예: 2026-09 = 19일 × 8 = 152h), 주 소정 = 40h − 8h × 평일 공휴일 ÷ 주 수.
  - 표에 '월 소정 (엑셀 평일의무)' 열 추가(월별 표 · 개인 표). KPI 연장 합계 = 엑셀 값.
  - **📐 엑셀 기준 확인** 카드(월 화면 아래): 그달 엑셀 값으로 ① 주평균근무가 실근무를 몇 주(며칠 ÷ 7)로 나눴는지, 그달 일수와 같은지 ② 평일의무근로시간이 달력(평일 − 평일 공휴일) × 8h 와 같은지, 다른 사람(휴가 등) ③ 연장근로시간이 어느 월 단위 계산(실근무 − 평일의무 / 평일근무 − 평일의무 / (실근무 − 휴일) − 평일의무 / 실근무 − 달력 소정 / (주평균 − 주 소정) × 주 / (주평균 − 40) × 주)과 맞는지(연장 있는 사람 중 ±0.5h 일치 수), 어느 것과도 안 맞으면 '일별(하루 8시간 초과 · 승인 연장) 기준으로 보임' ④ 심야 = 엑셀 값 그대로(출퇴근 시각 없음).
  - 받은 사진(2026.09) 분석: 엑셀 주평균근무 = 실근무 ÷ 약 4.43주 = **31일 ÷ 7** (9월은 30일) — 근태 시스템 집계 기간이 달력 월과 다를 수 있음. 연장근로시간은 실근무 − 소정과 맞지 않음(예: 실근무 183.1 · 휴일 19.2 인데 연장 7.5).
- **확인한 것**: `node --check`, `py_compile`. 생일: 홍길동 PC1 → 본인 축하 인사 + [오늘 하루 안 보기] → 홍길동 PC2(다른 브라우저) 안 뜸 · 김철수 뜸. 근로시간(사진 값으로 만든 시험 엑셀): 2026.09 → '실근무 ÷ 31일/7 (6/6명) · 그달 30일과 다름', '평일의무 152h 5명 · 144h 1명 ↔ 달력 152h', '연장은 월 단위 계산과 안 맞음 → 일별 기준'; 2026.08(연장 = 실근무 − 평일의무로 만든 줄) → '연장 ≈ 실근무 − 평일의무근로시간 3/3명'. 스크립트 오류 없음.
- **회사에서 확인할 것**: 서버 재시작 + Ctrl+F5 → 근로시간 관리에서 실제 엑셀의 '📐 엑셀 기준 확인' 카드 내용을 알려 줄 것 (그 결과로 계산 방식을 엑셀에 맞출 수 있음).

### 2026-10-15 (7) — 메뉴별 그래프 점검: 담당자 이름 맞추기 통일 · 홈 사업군 · R&R 투입 비중 (APP_VERSION 2026-10-15.7 / SERVER_VERSION 그대로 2026-10-15.4)
- 왜: 요청 "각 메뉴의 차트가 제대로 된 현황을 표기하는지 체크". 그래프마다 원본 데이터로 따로 계산한 값과 화면 값을 비교(시험 스크립트 `audit.js`, 시험 서버·가짜 데이터)해서 틀린 곳을 고침.
- 고친 것
  1. **담당자 이름 맞추기를 모든 그래프에서 같게** (`personGroups`): 칸에 그 이름이 '들어 있으면' 그 사람 것 ('홍길동 프로' · 'PM 김철수' · '홍길동 이영희' · '박민수(LE), 홍길동'). 예전엔 수행·입찰 보드만 이렇게 세고 다른 곳은 칸을 이름 하나로 잘라 정확히 같을 때만 셌음 → 덜 세거나 '홍길동 이영희' 같은 이상한 이름이 막대로 나옴.
     - 홈 '담당자별 담당 PJT 수 (진행 중 · 상위 12)' (수행 = 영문 이름 뺌, 입찰 = IEC 포함 — 수행·입찰 보드와 같은 규칙) · 통합 업무 '부서원별 상·하반기 업무 건수' 와 표준화 'ITEM PO ○명' · 조직도에서 사람 누르면 나오는 담당 업무 요약(`personSummary`) · R&R · 투입 분석의 'R&R 계획 대비 실제' 표(PJT R&R 담당자).
  2. **홈 '사업군별 PJT 수'**: 사업군 칸의 첫 줄 전체를 한 묶음으로 세던 것('발전/LNG' 가 따로 한 막대) → 수행·입찰 보드와 같은 사업군 단어(`bizTok`, 여러 개면 각각)로. 제목에 '진행 중'.
  3. **R&R · 투입 분석 (부서원 화면 = 비율만)**: 서버가 사람마다 '연간 = 100' 으로 바꿔 보내서, **월을 고르면** 그 달만 올린 사람이 여러 달 올린 사람보다 훨씬 크게 반영됨(화면 설명 '사람별 비중을 같게' 와 다름) → 고른 기간 안에서 사람마다 100 으로 다시 맞춰 팀 합산(`renderAlloc`). Management 화면(실제 시간)은 그대로 시간 가중.
- 점검 결과 (시험 데이터, 원본 계산 = 화면): 수행·입찰 보드(전체 · 진행 · 종결 · 업데이트+미업데이트 · 사업군별 · 부서원별 · 수행에 영문 이름 없음) / 홈(진행 수행·입찰 · 종결 · 투입인력 · 사업군 차트 · 담당자 차트) / 통합 업무(상태별 6칸 · 유형 합계 · 부서원별) / 근무시간(팀 총 · 근무일 · 근태 · 부서원별 연간) / R&R(연간·월 프로젝트별 % 합 100, 부서원 화면 근태 % = 사람별 근태 비율 평균) — 틀린 곳 0, 스크립트 오류 없음. 근로시간 관리(엑셀 값 그대로)·생일은 15.6 에서 확인.
- **회사에서 확인할 것**: Ctrl+F5 (server.py 안 바뀜). 홈·통합 업무 그래프의 사람별 숫자가 예전보다 늘 수 있음(직함·여러 이름이 든 칸을 이제 셈).

### 2026-10-16 (1) — 가상 광장(메타버스)을 대시보드로 옮김 · 홈 '최근 변경 이력' 반으로 접기 (APP_VERSION 2026-10-16.1 / SERVER_VERSION 2026-10-16.1)
> **서버 재시작 필요** (server.py). 새 폴더 `plaza/` (화면·서버 파일). 새 데이터 `data/plaza/roles.json` · `looks.json` (서버가 만듦, 자동 백업 포함).
- 무엇을·왜: 요청 "타이틀블록 파싱 구현에서 구현한 메타버스는 여기서 관리한다". P&ID 저장소 브랜치 `claude/titleblock-parsing-c5st4x` 의 인계 묶음(`out/plaza_handover`, 커밋 e5b29d1)을 그대로 가져와 `plaza/` 에 둠 — 앞으로 가상 광장은 이 대시보드에서 고침. 자세한 기능·규칙 = `plaza/README_인계.md` (§5 규칙: 사람이 쓴 글은 HTML 로 넣지 않음 · prompt/confirm/alert 금지 · 역할·맞은 사람은 서버가 정함 · LOOK_RANGES 와 plaza.js 표 · 지도 56×32 같게 · 방향키는 code/key/keyCode 모두).
- `plaza/plaza_server.py` (표준 라이브러리만): 인계본 + `--nets-file`·`--allow` 만 더함 — 사설·루프백 말고도 대시보드가 기억하는 사내 대역(`data/_meta/server-nets.json`, 유선↔Wi-Fi 바뀌면 바로 따라감)과 대시보드 `--allow` 대역을 허용. (인계본은 사설 주소만 허용 → 회사 대역 165.244.x.x 등 공인 주소의 부서원이 403.) 길·응답은 그대로. `python plaza/selftest.py` → 모두 통과.
- `plaza/static/plaza.js` 한 줄: embed(대시보드 카드 안)일 때 들어가자마자 스스로 포커스를 가져가지 않음 — 가져가면 대시보드 생일 팝업이 Esc 로 안 닫혔음(키가 광장으로 감). 카드를 한 번 누르면 움직임('클릭하면 캐릭터를 움직일 수 있습니다' 안내는 원래 있음).
- server.py: `plaza_loop` — 대시보드 서버가 켜질 때 `plaza/plaza_server.py --port 8100 --data data/plaza --nets-file … [--allow …]` 를 창 없이 함께 띄움, 꺼지면 30초 안에 다시 띄움(3번 연속 꺼지면 10분 쉼), 이미 8100 에서 광장이 돌고 있으면 그대로 씀. 대시보드가 끝날 때 `plaza_stop` = 자기가 띄운 PID 하나만 terminate (python 일괄 종료 안 함). `--plaza-port 0` = 안 띄움. `/api/info` 에 `plazaPort`.
- dashboard.html 홈:
  - '최근 변경 이력' 카드 제목 오른쪽 [펼치기 ▾ / 반으로 접기 ▴] — 접히면 목록 높이의 절반 + 아래 흐리게, **기본 접힘**, localStorage `dash.history.half` (`recentHalf` · `fitRecent`).
  - 그 바로 아래 '가상 광장' 카드 (메뉴 항목 없음): iframe `http://<대시보드 서버 호스트>:8100/plaza?embed=1&user=<로그인 이름>` (높이 470 · 테두리 없음 · sandbox 없음). 띄우기 전에 `/version` 3초 확인 → 실패면 '가상 광장 서버가 꺼져 있습니다' + [다시 시도]. 비회원 = '로그인하면 …', 오프라인 = '서버에 연결되어 있을 때만'.
  - **홈을 다시 그려도(1분 자동 갱신 · 새로고침 단추) iframe 을 새로 만들지 않음**: iframe 은 `#content` 밖 `#plazaHost` 에 두고 카드 자리 `#plazaSlot` 위에 위치를 맞춰 올림(`placePlaza` — 그릴 때 · 창 크기 · 접기 · 본문 크기 바뀔 때). iframe 을 DOM 에서 옮기면 다시 읽혀 캐릭터가 나갔다 들어오기 때문. 홈을 떠나면 iframe 을 닫아 광장에서 나감(`plazaOff`), 로그인 사용자가 바뀌면 새 이름으로.
- allow_firewall.bat: TCP 8100 도 엶 (규칙 이름 'DeptDashboard Plaza 8100').
- **확인한 것**: `node --check`, `py_compile`, `plaza/selftest.py` 모두 통과, 허용 대역 단위 시험(165.244.1.2: 파일 없으면 거절 → 대역 파일 있으면 허용, 파일이 바뀌면 바로 반영, --allow 65.3/16 허용). 시험 서버(가짜 계정)에서 대시보드 서버를 켜면 광장 서버가 8100 으로 함께 켜짐. 브라우저 두 사람(홍길동·김철수): 홈 카드 자리 = 광장 창 위치, 방향키로 걷기([23,15]→[27,17]), Enter 대화가 상대 대화 기록에 보임, Space 목검, 얼굴 바꾸기 → `data/plaza/looks.json` 저장, [새로고침] 뒤에도 같은 iframe·같은 광장 ID, 접기 풀면 광장 창이 따라 내려감, 수행 메뉴로 가면 나감(상대 화면 접속 2→1명), 홈으로 오면 다시 들어옴(1→2명), 생일 팝업 Esc 로 닫힘. 스크립트 오류 없음.
- **회사에서 확인할 것**: 서버 재시작 + Ctrl+F5 → 홈 아래 '가상 광장'. **처음 한 번** `data/plaza/roles.json` 의 `"operators": []` 에 운영자 이름(대시보드 로그인 이름)을 적으면 그 사람 광장 화면에 [역할 지정]. 부서원이 Wi-Fi 에서 광장만 안 보이면 `allow_firewall.bat` 을 관리자 권한으로 다시 실행. 이름은 iframe 주소의 user= 로 정해지므로 주소를 손으로 바꾸면 다른 이름으로 들어갈 수 있음(역할·얼굴은 장식이라 그대로 둠).

### 2026-10-16 (2) — 가상 광장 서버가 회사 PC(한글 Windows)에서 켜지자마자 꺼지던 것 고침 (APP_VERSION 그대로 2026-10-16.1 / SERVER_VERSION 2026-10-16.2)
> **서버 재시작 필요** (server.py · plaza/plaza_server.py).
- 증상: 홈 '가상 광장' 카드에 "가상 광장 서버가 꺼져 있습니다 (포트 8100)". `data/plaza/roles.json` 은 생겼음.
- 원인: `plaza_server.py` 가 시작 안내를 print 할 때 '—'(U+2014) 이 있는데, 대시보드가 띄울 때 출력이 콘솔이 아니라서 한글 Windows 기본 글자표 cp949 로 쓰다가 UnicodeEncodeError → 바로 종료. roles.json 은 print 직전에 만들어져 파일만 남음. (시험 환경 리눅스는 UTF-8 이라 못 잡음 — `PYTHONIOENCODING=cp949` 로 재현함.)
- 고침: ① plaza_server.py — stdout 을 utf-8(errors=replace)로 바꾸고 print 실패해도 계속, '—' 대신 '-'. ② server.py `plaza_loop` — 광장 서버를 `PYTHONIOENCODING=utf-8` 로 띄우고, 광장 서버의 출력·오류를 운영 폴더 `plaza.log` 에 남김(2MB 넘으면 plaza.log.old) → 다음에 꺼지면 이유가 거기 있음.
- **확인한 것**: `py_compile`, `plaza/selftest.py` 모두 통과. 고치기 전: `PYTHONIOENCODING=cp949` 로 실행 → roles.json 만 생기고 종료(UnicodeEncodeError). 고친 뒤: 같은 조건에서 /version 응답, 대시보드 서버(cp949 환경)가 광장 서버를 띄우고 plaza.log 에 시작 기록.
- **회사에서 확인할 것**: 적용 → 대시보드 서버 다시 켬 → 홈 F5 → 광장 보임. 안 되면 운영 폴더의 `plaza.log` 내용을 보내 줄 것.

### 2026-10-16 (3) — 계장 광장: 이름 · 다른 메뉴에서도 캐릭터 유지 · P&ID/LOGIC 분석 중 표시 · 겹치지 않음 · Space 꾹 (APP_VERSION 2026-10-16.3 / SERVER_VERSION 2026-10-16.3 · PLAZA_VERSION 2026-10-16.3)
> **서버 재시작 필요** (server.py · plaza/plaza_server.py). 돌고 있던 옛 판 광장 서버는 대시보드 서버가 알아서 바꿔 띄움(아래).
- 이름 '가상 광장' → **'계장 광장'** (홈 카드 · 안내 · iframe 제목 · plaza.html 제목 · 로그).
- **다른 메뉴로 가도 캐릭터 유지**: iframe 을 한 번만 만들고 계속 둠 — 홈이 아니면 `#plazaHost.away`(화면 밖 · 보이지 않음 · 접속 그대로). `render()` 첫머리에서 어느 메뉴든 `plazaOn()` (처음부터 다른 메뉴로 들어와도 광장에 들어감). 로그아웃 · 다른 사람 로그인 때만 `plazaOff` (나감).
- **P&ID 분석 · LOGIC 분석 메뉴에 있으면** 광장의 그 캐릭터 이름 아래 '(P&ID 분석 중...)' · '(LOGIC 분석 중...)' — 대시보드 `plazaStatus` 가 iframe 에 postMessage({type:'plaza-status'}) → plaza.js `setStatus` → 서버 `POST /plaza/api/status` (24자, 들어올 때 join 에도 실림) → 모두의 화면(머리 위 글자 · '광장에 있는 사람' 목록). 메시지는 부모 창에서 온 것만 받음. 글자로만 그림(§5 규칙 1).
- **캐릭터끼리 겹치지 않음**: 서버 `api_move` 가 다른 사람이 선 칸으로 가는 걸 막고 `{blocked, x, y}` 를 돌려줌 → 화면이 제자리로 되돌림. 화면도 미리 막음(`occupied` — 남의 서버 칸 · 가고 있는 칸). 들어오자마자 남과 같은 칸이면 가장 가까운 빈 칸으로 비켜섬(`freeNear`).
- **Space 꾹 누르면 계속 휘두름**: keydown 에서 `S.atkHeld`, keyup · 창 벗어남에서 풂, 그리는 동안 0.32초마다 `attack()` (서버는 그대로 0.3초에 한 번).
- **옛 판 광장 서버 바꿔 띄우기**: plaza_server.py 에 `PLAZA_VERSION`, `/version` 에 `ver`, `POST /plaza/api/quit`(이 PC·루프백에서만 → 스스로 끔). server.py `plaza_loop` 가 돌고 있는 광장의 ver 가 파일과 다르면(업데이트 전 · 서버 창을 닫아 남은 것) 끄고 새로 띄움 — 내가 띄운 것이면 그 PID 를 terminate, 아니면 quit 요청, quit 이 없는 16.2 판이면 Windows `netstat -ano` 로 8100 을 듣는 PID 하나를 찾아 `tasklist` 로 python 인지 확인 후 그 PID 만 `taskkill` (python 일괄 종료 안 함). 그래도 안 꺼지면 로그에 안내하고 10분 뒤 다시.
- **확인한 것**: `node --check`(dashboard · plaza.js), `py_compile`, `plaza/selftest.py` 모두 통과(+ 겹치지 않음 · 상태 24자 · 판 번호). 옛 판(ver 'old') 광장을 8100 에 띄워 둔 채 대시보드 서버 시작 → '옛 판(old)이라 새 판으로 바꿉니다' → ver 2026-10-16.3. 브라우저 두 사람: 홍길동이 수행 → P&ID → LOGIC → 게시판 → 홈으로 가는 동안 같은 iframe(새로 안 만듦), 김철수 화면 '홍길동 (P&ID 분석 중...)' → '(LOGIC 분석 중...)' → 표시 없음, 접속 2명 그대로. 김철수를 홍길동 옆 칸에 세우고 홍길동이 그쪽으로 → 못 감(화면 · 서버 둘 다 blocked). Space 1.7초 꾹 → 6번 휘두름, 떼면 멈춤. 스크립트 오류 없음. (netstat·taskkill 경로는 Windows 에서만 — 시험 환경에서는 quit 경로만 확인.)
- **회사에서 확인할 것**: 적용 → 대시보드 서버 다시 켬(server.log 에 '옛 판 … 새 판으로 바꿉니다') → 홈 F5. 그래도 옛 모습이면 plaza.log · server.log 를 보내 줄 것.

### 2026-10-16 (4) — 계장 광장: 한 PC(IP)에 캐릭터 하나 (PLAZA_VERSION 2026-10-16.4 / APP · SERVER 그대로 2026-10-16.3)
> 서버 재시작 필요 없음: 대시보드 server.py 가 30초마다 광장 판을 보고 새 판(plaza_server.py)으로 바꿔 띄움 → 적용 후 30초 뒤 F5.
- 증상: 대시보드를 여러 창(탭)으로 열면 한 사람 캐릭터가 여러 개.
- 이제 (plaza/plaza_server.py · plaza/static/plaza.js):
  - 광장 서버가 접속 주소(IP)를 직접 기록(`do_POST` 가 `_ip` 를 넣음 — 화면이 보낸 값은 덮어씀). `api_join`: 같은 IP · 같은 이름이 이미 있으면 **그 캐릭터를 함께 씀**(같은 id · 지금 자리 · `shared:true`), 같은 IP 에 다른 이름이면 그 PC 의 옛 캐릭터를 내보내고 새로 만듦.
  - 창마다 따로 움직여도 한 캐릭터: 어느 창에서 걸으면 서버 자리가 바뀌고, 다른 창은 1초 넘게 스스로 안 움직였으면 서버 자리를 따라감(`S.lastMove`).
  - 나가기: 창 하나를 닫아도(sendBeacon leave) 같은 캐릭터의 연결이 더 있으면 남김(`streams > 1`), 마지막 창이 닫히면 바로 나감(`left_at` + 연결 끊김). 끊긴 연결은 2초마다 확인(예전 12초).
- **확인한 것**: `node --check`, `py_compile`, `plaza/selftest.py` 모두 통과(+ 같은 PC 에서 창을 더 열면 같은 캐릭터 · 같은 PC 에서 다른 사람이 들어오면 바뀜 — 사람마다 127.0.0.N 주소). 브라우저: 김철수 PC(127.0.0.1) + 홍길동 PC(192.0.2.2) 창 2개 → 김철수 화면 접속 2명(홍길동 하나), 두 창 같은 id · 같은 자리, 창1 에서 걸으면 창2 · 김철수 화면 모두 [22,17], 창1 닫음 → 홍길동 남음, 창2 닫음 → 바로 1명. 스크립트 오류 없음.
- 알아둘 점: 같은 PC 에서 두 사람이 각자 다른 계정으로 동시에 광장에 들어가면 나중에 들어온 사람 캐릭터만 남음 (요청대로 IP 당 하나).

### 2026-10-16 (5) — 계장 광장: 주간업무보고 중 표시 · 상태는 머리 위 (APP_VERSION 2026-10-16.5 / PLAZA_VERSION 2026-10-16.5 / SERVER 그대로 2026-10-16.3)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- dashboard.html `plazaStatus`: 주간업무보고 메뉴 중 홈이 아닌 화면(수행 · 입찰 · 통합 업무 · R&R · 투입 분석 · 유닛분장 · 이슈 · 전달사항 등, `menuOf(route) === 'weekly'`)이면 '(주간업무보고 중...)'. 홈(광장이 보이는 곳)은 표시 없음, P&ID · LOGIC 은 그대로 '(… 분석 중...)', 게시판 · Management 등은 표시 없음.
- plaza.js: 상태 글자를 이름 아래 → **머리 위**로(`statusTag` y = 칸 위 40px), 말풍선이 있으면 상태 위로 16px 올림.
- **확인한 것**: `node --check`(dashboard · plaza.js), `py_compile`. 대시보드 서버가 광장을 2026-10-16.5 로 스스로 바꿈. 브라우저 두 사람: 홍길동 수행 → 통합 업무 → R&R → P&ID → 홈 → 수행 = 김철수 화면 '주간업무보고 중...' ×3 → 'P&ID 분석 중...' → 없음 → '주간업무보고 중...'. 말하는 동안 머리 위 상태 · 그 위 말풍선이 겹치지 않음. 스크립트 오류 없음.

### 2026-10-16 (6) — 계장 광장: 캐릭터 누르기 → [캐릭터 정보] → 그 부서원 정보 창 (APP_VERSION 2026-10-16.6 / PLAZA_VERSION 2026-10-16.6 / SERVER 그대로 2026-10-16.3)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- plaza.js: 지도에서 캐릭터(몸 · 이름표 자리, `actorAt` — 그리는 카메라 자리 `S.cam` 기준)를 누르면 작은 판(`.pz-ctx`): '[칭호] 이름' · 지금 상태(예: 주간업무보고 중...) · **[캐릭터 정보]**. 빈 곳을 누르거나 Esc 면 닫힘. 내 캐릭터도 됨. 글자는 textContent 로만(§5 규칙 1).
- [캐릭터 정보] → 부모 창(대시보드)에 postMessage({type:'plaza-profile', name}) → dashboard.html 이 **내 광장 iframe 에서 온 것만**(source · origin 확인) 받아 `openProfile(name)` — 유닛분장 조직도에서 사람을 누른 것과 같은 창(사진 · 담당 업무 · 전화 · 수행/입찰 PJT · 담당 업무 요약). 광장만 따로 열었을 때는 '대시보드 안에서 열면 볼 수 있습니다'.
- **확인한 것**: `node --check`, `py_compile`, 대시보드 서버가 광장을 2026-10-16.6 으로 스스로 바꿈. 브라우저: 김철수 화면에서 홍길동 캐릭터 누름 → '홍길동 · 주간업무보고 중... · [캐릭터 정보]' → 누름 → 대시보드에 '👤 홍길동' 창(DCS 설계 리드 · 전화 · 수행 3 · 입찰 1 · 통합 업무 4), 빈 곳 누르면 판 닫힘, 내 캐릭터 누르면 '김철수 (나)', 대시보드 페이지가 스스로 보낸 같은 메시지는 무시. 스크립트 오류 없음.

### 2026-10-16 (7) — 계장 광장: 체력 100 · 맞으면 -1 · 0 이면 유령 · 주간 마감에 부활 (PLAZA_VERSION 2026-10-16.7 / APP · SERVER 그대로 2026-10-16.6 · 2026-10-16.3)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5. 바뀐 파일은 `plaza/` 안뿐.
- 무엇을: 모든 캐릭터 체력 100. Space 로 한 대 맞을 때마다 1 씩 줄고(0.3초에 한 번 — 예전 그대로), 0 이 되면 **유령**. 유령은 공격 못 함(누르면 대화창에 나만 보는 안내) · 맞지 않음 · 남과 겹쳐 지나감(남도 유령 칸은 지나감). **주간 마감**이 지나 주차가 바뀌면 모두 100 으로 부활 + 대화창 알림.
- 왜: 사용자 요청 '공격시 피 1씩, 모두 100, 다 깎이면 유령, 다음 주(마감)가 되면 부활'.
- 바뀐 곳: plaza_server.py `HP` · `manual_closed_week` · `plaza_week` · `load_hp` · `check_week` · `hp_of` · `save_hp` · `hp_loop` · `api_attack` · `api_move` · `snapshot`(players 에 hp · hp_max · ghost, 맨 위 week) · `main`. plaza.js `newActor` · `occupied` · `applySnapshot` · `ghostly` · `drawActor` · `hpBar` · `attack` · `localNote` · `showCtx`. selftest.py 7개 더.
  - 체력은 **이름별**로 `data/plaza/hp.json` (`{"week": "2026-W43", "hp": {"홍길동": 0, …}}`, 100 인 사람은 안 적음)에 2초마다 저장 → 창을 닫고 다시 들어오거나 서버를 다시 켜도 유령 그대로.
  - 주차 = 대시보드 server.py `iso_week` 와 같은 규칙(수요일 12:00 이 지나면 다음 주 · [금주 마감] 을 누르면 `data/_meta/state.json` manualClosedWeek 를 읽어 그때 바로). 30초마다 + 때릴 때 · 화면 갱신 때(5초에 한 번) 확인. 서버가 꺼져 있는 동안 마감이 지났으면 켜질 때 부활.
  - 화면: 이름 아래 체력 막대(초록 > 50 · 노랑 > 20 · 빨강), 유령은 막대 대신 '유령' + 희푸른 반투명 몸이 둥둥 · 그림자 없음. 위쪽 '접속 n명 · 내 체력 87/100'(유령이면 '나는 유령 (주간 마감 때 부활)'), 오른쪽 사람 목록에 [유령], 캐릭터 누른 판에 '체력 87/100' 또는 '유령 (주간 마감 때 부활)'.
  - 체력을 손으로 되돌리려면: 광장이 도는 동안 `data/plaza/hp.json` 은 2초마다 다시 쓰이므로, 고치려면 대시보드 서버를 끄고(광장도 꺼짐) 고친 뒤 켠다.
- 확인한 것: `py_compile`, `node --check`, `python plaza/selftest.py` 모두 통과(남은 1 맞으면 유령 · 유령 공격 못 함 · 유령 안 맞음 · 유령 겹쳐 지나감 · 파일에 남음 · [금주 마감] 기록 → 부활 · 새 주차). 브라우저 두 사람: 체력 3 인 홍길동을 김철수가 Space 꾹 → 0 · 유령, 양쪽 화면 같음, 대화창 '홍길동 님이 김철수 님에게 쓰러져 유령이 되었습니다', 홍길동 Space → 안내 한 줄, 캐릭터 판 '유령 (주간 마감 때 부활)'. 스크립트 오류 없음.
- 회사에서 확인할 것: 수요일 12:00(또는 [금주 마감]) 뒤 30초 안에 유령이 다시 사람으로 돌아오는지.

### 2026-10-16 (8) — 계장 광장: 캐릭터 그림체 바꿈 (큰 머리 · 큰 눈 · 진한 외곽선 · 음영 · 손에 목검) (plaza.js 만 · APP · SERVER · PLAZA_VERSION 그대로)
> plaza.js 는 광장 서버가 파일에서 바로 읽어 주므로(no-store) 서버 재시작 필요 없음 → 적용 후 Ctrl+F5.
- 무엇을: 사용자가 보낸 도트 캐릭터 그림(2등신 · 큰 눈 · 굵은 검은 외곽선 · 밝음/중간/어둠 3단 음영 · 무기를 세워 듦) 느낌으로 캐릭터를 새로 그림. **옷은 따라하지 말라**는 요청대로 옷은 예전 것(저고리 + 흰 깃 + 고름, 통 넓은 바지 + 대님, 노비 무명옷 + 새끼줄 띠)과 역할 머리 장식(관모 · 사모 · 왕관 · 두건)을 그대로 두고 새 그림체로만 다시 그림.
- 바뀐 곳: plaza.js `charSprite` 를 통째로 새로 씀 — 몸 격자 20×28 점(예전 16×24), 머리 14×13 점. 점 판(`grid`)에 색을 칠한 뒤 빈 칸 중 그림에 닿은 칸을 외곽선(`OL`)으로 칠하는 방식(외곽선이 늘 1점 · 끊김 없음). 새 인자 `armed` = 손에 목검 듦(휘두르는 동안은 `drawSwing` 이 그리므로 안 듦 · 얼굴 바꾸기 판의 머리 단추 · 유령은 안 듦). 새 상수 `GW` `GH` `CW` `CH` `FOOT`(그림 위 → 발바닥 px) `HEAD_PX`(발바닥 → 모자 꼭대기).
  - 이를 쓰는 곳도 맞춤: `drawActor`(가운데 = 칸 가운데, 발 = 칸 바닥) · 상태 글자 · 말풍선 높이(`HEAD_PX`) · `actorAt`(누르는 자리) · `drawSwing`(손 높이) · 얼굴 판 미리보기(2배) · 머리 모양 단추(머리 부분만 잘라 보임).
  - 외형 번호(머리 10 · 머리색 8 · 피부 4 · 눈 5 · 수염 4 · 옷 12 · 바지 6)는 그대로 → 저장된 얼굴(looks.json) 그대로 쓰임. '점 눈' 은 빛 한 점 있는 까만 큰 눈, '큰 눈' 은 속눈썹 + 갈색 눈동자 + 빛.
- 확인한 것: `node --check`. 모든 역할 × 4 방향 × 걸음 3, 머리 모양 10 × 앞 · 옆 · 뒤, 눈 5 · 수염 4 를 한 장에 그려 봄(스크립트 오류 없음). 광장에서 두 사람: 걷기 · 말풍선 · '(주간업무보고 중...)' · 체력 막대 · 휘두르기 · 맞은 표시 · 캐릭터 머리 누르기 → [캐릭터 정보] 판 · 얼굴 바꾸기 판 모두 자리 맞음.
- 회사에서 확인할 것: 캐릭터가 예전보다 조금 커서(가로 약 1칸, 세로 약 2칸) 옆 칸 사람과 이름표가 겹쳐 보일 수 있음 — 거슬리면 말해 주면 조정.

### 2026-10-16 (9) — 계장 광장: 부여성 남쪽 지도도 캐릭터와 같은 도트 해상도 (plaza.js 만 · APP · SERVER · PLAZA_VERSION 그대로)
> 서버 재시작 필요 없음 → 적용 후 Ctrl+F5.
- 무엇을: 땅 · 생울타리 · 나무 · 집 · 문 · 울타리 · 남문 · 성벽 · 우물 · 등 · 장승 · 좌판을 캐릭터처럼 **2px 한 점 · 짙은 외곽선 · 또렷한 색**으로. 왜: 사용자 요청 '부여성 남쪽 이미지도 비슷한 해상도로'.
- 바뀐 곳: plaza.js 새 함수 `layers` · `shrink` · `palette` · `pixelize`. 소품 그림 함수(`treeImg` `houseImg` `gateImg` `fenceImg` `southGateImg` `castleWallImg` `wellImg` `lanternImg` `jangseungImg` `stallImg`)는 모양 그리는 부분은 그대로 두고 끝에서 `pixelize(c)` 를 돌려줌. `drawGround` 끝에서 땅 전체를 반으로 줄였다 2배(점 2px) + 잔디밭 둘레 짙은 선.
  - `pixelize`: 반으로 줄여 색을 고름 → 원래 그림에서 많이 쓴 색 16 개(`palette`, 0.2% 미만은 뺌)로 맞춰 섞인 중간색 없앰 → 반투명 가장자리 없앰 → 그림 둘레 빈 칸을 옆 색의 아주 어두운 색으로(외곽선) → 2배. 그림자는 `c.shadow`(layers 가 만듦)에 따로 그려 점 모양 반투명으로, 글자(南 門 · 장승 글씨)는 `c.after` 로 다 바꾼 뒤 또렷하게 덧씀. 결과 그림은 둘레로 2px 씩 커짐(자리는 그대로).
  - 지도는 처음 열 때 한 번만 만듦(그 뒤 매 틀은 붙이기만) → 움직임 속도 그대로.
- 확인한 것: `node --check`. 브라우저 큰 창(1900×1150)에서 지도 전체 · 확대: 나무가 점 덩어리 잎 + 외곽선, 집 · 남문 · 성벽 · 우물 · 좌판 외곽선, 南 門 글자 또렷, 그림자 자리 맞음, 캐릭터 · 이름표 · 체력 막대 그대로. 스크립트 오류 없음.

### 2026-10-16 (10) — 계장 광장: 캐릭터를 보낸 그림에 더 가깝게 (plaza.js 만 · APP · SERVER · PLAZA_VERSION 그대로)
> 서버 재시작 필요 없음 → 적용 후 Ctrl+F5.
- 무엇을: 사용자가 다시 보낸 도트 캐릭터 5장처럼 — **얼굴보다 넓고 풍성한 머리**(앞머리 가닥 14줄 · 빛띠 · 가닥 사이 그늘), **세로 4점 큰 눈**(속눈썹 + 바깥 꼬리 · 진한/중간/밝은 갈색 눈동자 · 흰 빛 두 점), **키보다 긴 목검**(나뭇결 · 코등이 · 끈 감은 손잡이), 둥근 3단 음영. 옷은 이번에도 우리 것 그대로(저고리 · 흰 깃 · 고름 · 통 넓은 바지 · 대님 · 노비 무명옷, 역할 모자).
- 바뀐 곳: plaza.js `charSprite` 다시 씀 — 몸 격자 22×31(예전 20×28), 머리 = 위 16줄(키의 절반), 머리카락 덩어리 폭 19점. 새 도구 `blob`(둥근 덩어리를 왼쪽 위 밝게 · 오른쪽 아래 둘레 어둡게 칠함 — 머리카락 · 얼굴 · 쪽 · 상투 · 양갈래 · 포니테일에 씀) · `get` · `eye`(눈 5가지를 한 곳에서) · `sword`. 상수 `GW` 22 · `GH` 31 · `OY` 6, `FOOT` · `HEAD_PX` 는 자동으로 따라감. `drawSwing` 칼 1.4배 · 칼바람 반지름 30, 발밑 그림자 14×5, 머리 모양 단추는 위 23줄을 잘라 보임.
  - 외형 번호 · looks.json 그대로 (머리 10 · 머리색 8 · 피부 4 · 눈 5 · 수염 4 · 옷 12 · 바지 6).
- 확인한 것: `node --check`. 모든 역할 × 4 방향 × 걸음 3, 머리 모양 10 × 앞 · 옆 · 뒤, 눈 5 · 수염 4 를 한 장에(오류 없음). 광장 두 사람: 말풍선 · 상태 글자 · 이름표 · 체력 막대 · 휘두르기 · 맞은 표시 · 캐릭터 누르기 판 자리 맞음.
- 회사에서 확인할 것: 캐릭터 폭이 한 칸(32px)보다 조금 넓어(약 44px) 바로 옆 칸 사람과 몸이 맞닿아 보임 — 거슬리면 말해 주면 조정.

### 2026-10-16 (11) — 계장 광장: 노비(운영자)를 산발 · 거지 같은 누더기로 (plaza.js 만 · APP · SERVER · PLAZA_VERSION 그대로)
> 서버 재시작 필요 없음 → 적용 후 Ctrl+F5.
- 무엇을: 사용자 요청 '노비는 더 산발에 거지같이'. 운영자(노비) 캐릭터만 바뀜.
  - 머리: 고른 머리 모양과 상관없이 **늘 산발**(머리색만 따름) — 사방으로 뻗친 머리칼 12가닥, 엉킨 옆머리가 어깨 아래까지, 들쭉날쭉 긴 앞머리 · 한쪽 눈을 덮는 머리칼, 뒤는 들쭉날쭉 긴 뒷머리. **두건은 없앰.**
  - 옷: 더 바랜 삼베 색, 다른 색 헝겊으로 기운 자국 + 바늘땀, 얼룩, 너덜너덜한 밑단, 찢어진 소매(팔뚝이 보임), 무릎 구멍, 새끼줄 띠 끝이 늘어짐.
  - 발 · 얼굴: 대님 대신 맨 정강이 + **짚신**(발가락 보임). 볼 홍조 대신 때 자국.
- 바뀐 곳: plaza.js `charSprite` — `hs = nobi ? -1 : F.hair`(머리 모양 무시), `if (nobi)` 누더기 덩어리(헝겊 · 밑단 · 소매 · 무릎 · 짚신), '노비 — 산발' 덩어리(머리칼 · 옆머리 · 앞머리), 얼굴의 때 자국 · 눈 덮는 머리칼, 역할 장식에서 두건 삭제. 얼굴 바꾸기 판 안내 문구 `openFace`: '운영자는 노비 차림 — 머리는 늘 산발, 옷은 기운 누더기에 짚신입니다 (머리 모양 · 옷 색 · 바지 색은 안 씀).'
- 확인한 것: `node --check`. 노비를 4 방향 × 걸음 3 × 머리색 3 가지로 그려 봄(오류 없음) — 산발 · 기운 자국 · 짚신 · 눈 덮는 머리칼 보임. 다른 역할은 그대로.

### 2026-10-16 (12) — 계장 광장: 노비에 흰 머리띠 (plaza.js 만 · APP · SERVER · PLAZA_VERSION 그대로)
> 서버 재시작 필요 없음 → 적용 후 Ctrl+F5.
- 무엇을: 사용자 요청 '노비는 흰색 머리띠도'. 산발 위 이마 높이에 흰 무명 머리띠(좀 때 탄 주름 · 얼룩). 앞에서는 옆으로 삐져나온 끝, 옆에서는 뒤로 늘어진 끝, 뒤에서는 뒤통수 매듭 + 늘어진 두 끝.
- 바뀐 곳: plaza.js `charSprite` 역할 장식의 `role === "operator"` 덩어리(11 에서 지운 두건 자리), `openFace` 안내 문구 '머리는 늘 산발에 흰 머리띠'.
- 확인한 것: `node --check`, 노비 4 방향 × 걸음 3 그려 봄(오류 없음).

### 2026-10-19 (1) — 계장 광장: 처치 수 · killer · 이름이 점점 짙은 붉은색 (PLAZA_VERSION 2026-10-19.1 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 사용자 요청 '사용자를 많이 죽이면 killer 로 표기하면서 이름을 점점 짙은 붉은색으로'. 상대 체력을 0(유령)으로 만들면 처치 1.
  - 이름 색: 1명부터 붉어짐 — 연분홍(1) → 새빨강(5쯤) → 짙은 붉은색(10명 이상). 테두리는 늘 검정.
  - **3명부터** 이름 앞에 **[killer n]**(빨강) + 이름 둘레 붉은 빛무리. 3명이 되는 순간 대화창 '⚔ ○○ 님이 이번 주 3명을 쓰러뜨려 killer 가 되었습니다!'.
  - 오른쪽 사람 목록: killer 딱지 + 이름 붉은색, 캐릭터 누른 판: '체력 … · 이번 주 n명 처치 (killer)'.
  - 처치 수는 **주마다 새로**: 주간 마감(부활)할 때 체력과 함께 0. (계속 쌓이게 하려면 plaza_server.py `check_week` 의 `kills={}` 를 빼면 됨)
- 바뀐 곳: plaza_server.py `KILLER_AT`(3) · `HP["kills"]` · `load_hp` · `check_week` · `save_hp`(hp.json 에 kills) · `api_attack`(0 으로 만든 사람에게 +1) · `snapshot`(players 에 kills · killer). plaza.js `killColor` · `nameTag` · `newActor` · `applySnapshot`(사람 목록) · `showCtx`. plaza.css `.pz-who .role.killer`. selftest.py 처치 수 시험(3명 → killer · 마감에 0).
- 확인한 것: `py_compile`, `node --check`, `python plaza/selftest.py` 모두 통과. 대시보드 서버가 광장을 2026-10-19.1 로 스스로 바꿈. 브라우저: 처치 0 · 1 · 3 · 6 · 10 의 이름 색과 [killer n], 사람 목록 딱지, 캐릭터 판 문구. 스크립트 오류 없음.

### 2026-10-19 (2) — 계장 광장: 고양이 기사 캐릭터 (사용자가 준 시트에서 뽑은 그림) · 동물 6 · 갑옷 6 · 망토 7 · 사람도 고를 수 있음 (PLAZA_VERSION 2026-10-19.2 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 사용자가 준 '고양이 기사' 캐릭터 시트(1254×1254 PNG — 갈색 고양이 얼굴 · 은빛 갑옷 · 빨간 망토 · 황금 검, 8방향 · 걷기 · 달리기 · 공격 · 피격 · 점프 · 사망 칸)를 기준으로 광장 캐릭터를 바꿈. **모두 처음엔 원본 고양이 기사**, [얼굴 바꾸기] 에서 종류(고양이 기사 / 사람) · 동물(치즈 · 회색 · 검은 · 흰 고양이 · 호랑이 · 여우) · 갑옷(은빛 · 황금 · 흑철 · 청동 · 푸른 강철 · 백은) · 망토(빨강 · 파랑 · 초록 · 보라 · 검정 · 흰 · 노랑). '사람' 을 고르면 예전 사람 캐릭터(머리 · 눈 · 수염 · 옷 · 역할 모자 · 노비)가 그대로.
- 그림 만든 방법 (회사에서 다시 만들 일은 없음 — 결과 PNG 만 씀): 시트 전체는 쓰지 않고 캐릭터 칸만 잘라 → 남색 배경을 테두리에서부터 지워 투명 → 시트의 점 크기(방향 줄 약 3.1px · 걷기/공격 줄 약 2.7px, AI 그림이라 줄마다 다름)에 맞춰 한 점 크기로 줄이고(칠한 픽셀만 평균) → 원본 캐릭터 픽셀에서 뽑은 40 색 팔레트로 맞춰 번짐 없앰 → `plaza/static/catknight.png`(548×48 · 25KB, 16 칸). 화면에서는 2배(PX) 로 키우되 imageSmoothing 끔 → 흐리지 않음.
  - 쓴 칸: 서 있기 = 시트의 DOWN · UP · LEFT · RIGHT, 걷기 = WALK 4~8번(오른쪽 보는 5칸, 왼쪽은 좌우 뒤집음 — 1~3번은 왼쪽을 봐서 안 씀), 공격 = ATTACK 1 · 2 · 3(뒤집음) · 4(뒤집음) · 6 (칼바람 포함 — 옆으로 공격할 때), 맞음 = HURT 1번(옆), idle 큰 그림은 칸 목록엔 있지만 지금은 안 씀.
  - 시트에 없는 것은 만들지 않음: 위 · 아래로 걸을 때는 서 있는 칸을 한 점씩 들썩임, 서 있을 때는 0.8초마다 한 점 오르내림(숨쉬기), 위 · 아래 공격은 예전 칼 휘두르기(색만 황금 검)를 겹침, 유령은 서 있는 칸을 반투명하게.
- 바뀐 곳:
  - plaza.js: `KINDS` `FURS` `ARMORS` `CAPES` · `RANGES`(kind · fur · armor · cape) · `defaultFace`(kind 0 = 고양이 기사) · 새 `CAT_FR`(칸 자리 · 가운데 · 발바닥) · `CAT_PAL`(40 색 + 묶음: O 외곽선 · F 털 · f 털(머리 쪽만 — 갑옷 반사에도 쓰인 색) · m 주둥이 · A 갑옷 · G 금 장식 · C 망토) · `loadCat` · `rgb2hsl` · `hsl2rgb` · `FUR_T` `MUZ_T` `ARM_T` `CAPE_T`(색 바꾸는 법) · `catMap` · `catSprite`(색 바꾸기 + 2배 + 뒤집기, canvas.cx · canvas.foot) · `catPose`(서기 · 걷기 · 공격 · 맞음 칸 고르기) · `isCat`. `drawActor`(고양이 기사 · 유령) · `drawSwing(…, gold)` · `drawPreview` · `buildFace` · `faceNote` · `arrowRow` · 무작위(종류는 그대로).
  - plaza_server.py: `LOOK_EXTRA`(kind 2 · fur 6 · armor 6 · cape 7, 없으면 0 — 예전에 저장한 얼굴도 그대로 읽힘) · `clean_look` · FILES 에 `/static/catknight.png`.
  - plaza.html: [얼굴 바꾸기] 단추 설명. selftest.py: 얼굴 저장(예전 값 → 기본값 붙음 · 고양이 기사 값) · PNG 파일 시험.
- 확인한 것: `py_compile`, `node --check`, `python plaza/selftest.py` 모두 통과. 대시보드 서버가 광장을 2026-10-19.2 로 스스로 바꿈. 브라우저 두 사람: 서 있기 · 오른쪽/왼쪽 걷기(걷기 칸 돌아감) · 위 · 옆 공격(칼바람 칸) · 이름 · 체력 막대 · 상태 자리, 얼굴 판(고양이 줄 · 사람 줄로 바꾸기 · 미리보기 · 저장 → 상대 화면에도 같은 모습), 동물 6 · 갑옷 6 · 망토 7 을 한 장에 그려 봄. 스크립트 오류 없음.
- 회사에서 확인할 것: 예전에 '얼굴 바꾸기' 로 사람 모습을 저장한 사람도 이번엔 고양이 기사로 나옴(종류 값이 없던 저장본 = 고양이 기사). 사람으로 돌리려면 [얼굴 바꾸기] → 종류 ▶ 사람 → 저장.

### 2026-10-19 (3) — 계장 광장: 그룹장 = 황금 갑옷 + 금빛 후광 · 유닛장 = 은색 갑옷 + 은빛 후광 (plaza.js 만 · PLAZA_VERSION · APP · SERVER 그대로)
> 서버 재시작 필요 없음 → 적용 후 Ctrl+F5.
- 무엇을: 사용자 요청. 고양이 기사일 때 **그룹장은 황금 갑옷, 유닛장은 백은(밝은 은색) 갑옷** — 역할이 정하므로 [얼굴 바꾸기] 의 갑옷 줄은 '황금 갑옷 (그룹장)' / '백은 갑옷 (유닛장)' 으로 고정 표시(고를 수 없음, 동물 · 망토는 고름). 부서원 · 운영자는 예전처럼 갑옷을 고름.
  - 후광: 몸 뒤에 천천히 숨쉬는 빛(그룹장 금빛 · 유닛장 은빛) + 머리 뒤 둥근 고리(PX 칸 점으로 그림) + 몸 둘레를 도는 반짝이 6개. 사람 모습을 고른 그룹장 · 유닛장에게도 후광은 나옴(왕관 · 사모는 그대로). 유령일 때는 없음.
- 바뀐 곳: plaza.js 새 `ROLE_ARMOR` · `roleFace` · `AURA` · `drawAura`, `drawActor`(역할 갑옷 · 후광), `drawPreview`, `buildFace`(갑옷 줄 고정), `faceNote` · 사람 안내 문구.
- 확인한 것: `node --check`. 시험 서버(임시 폴더의 roles.json 에 그룹장 · 유닛장 지정)에서 세 사람: 그룹장 황금 갑옷 + 금빛 고리 · 빛, 유닛장 백은 갑옷 + 은빛 고리 · 빛, 부서원은 그대로. 유닛장 얼굴 판 '갑옷 백은 갑옷 (유닛장)'. 스크립트 오류 없음.

### 2026-10-19 (4) — 계장 광장: 마을 시트 — 캐릭터 5종(고양이 양반 · 팬더 학자 · 사자 무관 · 호랑이 무관 · 노비) · 마을 배경 · 운영자 = 노비 (PLAZA_VERSION 2026-10-19.3 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 사용자가 준 '마을' 시트(1536×1024 — 캐릭터 5종의 큰 그림 · 대기/걷기/달리기/공격/점프 줄, 배경 타일셋 · 건물 · 소품, 마을 지도 예시)처럼 캐릭터와 배경을 바꿈. **운영자는 늘 노비**(시트의 노비 · 평민).
  - [얼굴 바꾸기] 종류: 고양이 기사 · 사람 · 고양이 양반 · 팬더 학자 · 사자 무관 · 호랑이 무관 (노비는 운영자만 — 다른 사람은 못 고름, 운영자는 '노비 (운영자)' 고정). 마을 캐릭터는 색 고르기 없이 시트 그대로, 미리보기는 시트 맨 위 큰 그림.
  - 그룹장 · 유닛장 후광은 모든 종류에 나옴(갑옷 색 고정은 고양이 기사만).
- 그림 만든 방법 (결과 PNG 만 씀): 시트 전체는 안 쓰고 필요한 칸만 잘라 → 남색 배경을 테두리에서부터 지워 투명 → 시트의 점 크기(약 2px)로 한 점씩 줄이고 → 원본 팔레트(캐릭터 48 색 · 배경 64 색)로 맞춰 번짐 없앰. 시트 칸 구분선(가는 줄) · 나무 밑의 시트 뒤판(물빛)은 지움.
  - `plaza/static/village_chars.png`(512×125 · 65KB): 캐릭터 칸 28 + 큰 그림 5. 쓴 칸 — 앞모습 대기(2칸, 0.65초마다 번갈아 = 숨쉬기) · 앞으로 걷기(2~4칸) · 옆(비스듬한) 모습(1~4칸, 반대쪽은 좌우 뒤집음) · 공격 칸(고양이 양반 부채 · 팬더 · 사자 · 호랑이 칼바람). 시트에 **뒷모습이 없어** 위로 갈 때도 앞모습, 노비는 공격 칸이 없어 예전 칼 휘두르기.
  - `plaza/static/village.png`(512×105 · 46KB): 땅 타일(흙 · 풀 · 물 · 돌판) · 건물 4(집 · 작은 집 · 깃발 걸린 전각 · 문채) · 나무 3(초록 2 · 벚꽃) · 나무문 · 울타리 · 분수 · 꽃덤불 · 깃발 2 · 석등 2 · 수레 · 항아리 2 · 좌판 · 우물(나무 통) · 덤불.
- 배경: 지도 배치(56×32 칸 · 길 · 남문 · 성벽 · 장승 · 당산나무)는 그대로 두고 그림만 바꿈.
  - 땅: 흙 · 풀 · 물은 시트 타일의 색 4 가지만 뽑아 2px 점을 흩뿌림(시트 타일을 그대로 깔면 칸 가장자리 선이 격자로 보여서), 돌길은 시트의 밝은 돌판 타일, 잔디 둘레는 시트 덤불(생울타리), 연못 둘레는 돌.
  - **오른쪽 잔디 테 안에 연못**(48~50 · 17~21 칸, 막힘) + 가운데 분수. 집 2 → 시트 전각 · 집, 오른쪽 위에 작은 집, 왼쪽 위 잔디에 문채, 작은 문 3 → 나무문, 울타리 · 우물 · 좌판 · 석등 → 시트 그림, 좌판 옆 수레 · 항아리, 남문 앞 깃발 2 · 석등 2 · 깃발 1 더, 잔디 나무 → 시트 나무(벚꽃 약 28%), 잔디에 꽃덤불(밟고 지나감). 남문 · 성벽 · 장승 · 당산나무는 손그림 그대로(시트에 맞는 것이 없음).
  - 그림 파일을 받은 뒤 한 번에 만듦(`buildWorld`) — 6초 안에 못 받으면 예전 손그림 지도. 시작 자리는 지도가 다 만들어진 뒤 고름(`join` 이 `WORLD.promise` 를 기다림).
- 바뀐 곳: plaza.js `WATER` · 연못 `fill/block` · `drawGround`(IIFE → 함수, 마을 그림이면 `drawGroundVil`) · 새 `CHR_FR` `VIL_FR`(칸 자리 · 가운데 · 발바닥) · `VIL` `CHR` · `loadAtlas` · `atlasSprite` · `vs` · `vFence` · `drawGroundVil` · `place`(이제 목록에만 적음: make · vil · vsolid · vilOnly · flat) · `trees(V)` · `WORLD` · `buildWorld` · `KINDS`(7) · `KIND_FR` · `isChr` · `chrSprite` · `chrPose` · `roleFace`(운영자 → 노비 · 노비는 운영자만) · `drawActor` · `drawPreview` · `arrowRow(…, skip)` · `kindRow` · `buildFace` · `faceNote` · 프레임의 소품 정렬(`p.z`). plaza_server.py `LOOK_EXTRA.kind` 7 · FILES 에 village.png · village_chars.png. selftest.py PNG · 마을 캐릭터 얼굴 저장 시험.
- 확인한 것: `py_compile`, `node --check`, `python plaza/selftest.py` 모두 통과. 대시보드 서버가 광장을 2026-10-19.3 으로 스스로 바꿈. 브라우저 + 다른 주소에서 들어온 시험 캐릭터 5: 고양이 양반(그룹장 금빛 후광) · 사자 무관(유닛장 은빛 후광) · 노비(운영자) · 팬더 학자 · 호랑이 무관 · 고양이 기사 함께, 걷기 · 공격 칸(사자 칼바람) · 맞은 표시, 지도 곳곳(집 · 문채 · 연못 · 분수 · 좌판 · 수레 · 나무 · 꽃덤불 · 석등 · 깃발), 얼굴 판(운영자 '노비 (운영자)' 고정 · 종류 돌리기에 노비 없음 · 큰 그림 미리보기). 스크립트 오류 없음.
- 회사에서 확인할 것: 운영자(roles.json operators)가 노비로 나오는지. 오래된 PC 에서 처음 들어올 때 그림 두 장(약 110KB)을 받느라 1초 정도 늦을 수 있음.

### 2026-10-19 (5) — 계장 광장: 조선 마을 RPG 로 개편 (지도 64×44 · 구역 · 한옥 · 담장 · 연못 · 시장 · 자연스러운 땅) (PLAZA_VERSION 2026-10-19.4 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 사용자가 준 '조선 마을 타일셋'(1536×1024 — 땅 타일 · 풀 · 꽃 · 나무 · 바위 · 석등 · 울타리 · 돌담 · 우물 · 좌판 · 수레 · 통 · 깃발 · 한옥 · 지붕 · 기와 담장 · 관아문 · 다리 · 연못 · 돌계단, 오른쪽 위 완성 지도)을 참고해 광장을 조선시대 마을로. 이동 · 충돌 · 캐릭터 · 체력 · 말 · 상태 · 캐릭터 정보 등 기능은 그대로.
- 지도(plaza.js `W` `H` = 64 × 44, plaza_server.py `MAP_W` `MAP_H` 도 같게): 북쪽 관아(큰 한옥 · 돌판 앞마당 · 깃발 · 석등) / 가운데 둥근 흙 광장(당산나무 · 우물 · 석등 넷 · 장승 둘) / 서쪽 주거(한옥 넷 · 낮은 돌담 · 울타리 · 장독대 셋 · 우물통 · 수레, 남북 골목) / 동쪽 시장(좌판 두 줄 — 가운데 줄은 걸어 다니는 통로, 수레 · 통 · 항아리 · 상자 · 깃발) / 북동 연못(연못 둘 · 잇는 물길 위 나무다리 · 다리 건너 정자 · 바위 · 대나무 울타리 · 연잎) / 남쪽 성문(관아문 모양 문루 · 기와 담장 · 석등 · 이끼 돌) / 둘레는 숲(소나무 · 벚꽃 · 큰 나무), 안쪽 풀밭에 나무 · 덤불 · 꽃.
  - 걸을 수 있는 칸 1715 / 2816, 시작 자리에서 모두 이어짐(한 칸만 떨어짐). 처음 시작 자리는 광장 둘레 고리(가운데에서 4~9칸)에 이름마다 흩어짐(`spawn`) — 성문 앞에 몰리지 않음.
  - 건물은 아래 벽 · 기단만 막고 지붕은 막지 않음 → 뒤로 지나가면 지붕에 가려지고, 그때 그 건물을 반투명(55%)하게 그려 내 캐릭터가 보임(`fade`). 이름표 · 말풍선은 늘 맨 위. 앞뒤는 예전처럼 발바닥 높이로 정렬.
- 그림: `plaza/static/joseon.png`(1024×196 · 268KB · 103 칸) — 시트에서 배경색으로 떨어진 덩어리(136 개)를 찾아 **그 덩어리의 픽셀만** 쓰고(옆 덩어리가 겹친 칸도 섞이지 않음, 덩어리 안 구멍은 메움), 땅 타일은 덩어리 안쪽(테두리 3px 안)만 → 경계를 짐작해 자르지 않음. 점 크기 약 2px → 한 점, 원본 96 색 팔레트. 시트에 없는 **장독대**는 같은 화풍(2px 점 · 짙은 외곽선 · 3단 음영)으로 그림(`jangdokImg`). 장승은 예전 그림. 예전 `village.png` 는 지움(캐릭터 `village_chars.png` 는 그대로).
- 땅(`drawGround`, 처음 한 번): 점 해상도(1024×704)로 칠한 뒤 2배.
  1) 흙 · 풀 · 물 경계는 값 잡음(`vnoise`)으로 일렁이게(돌판 · 이끼 돌은 반듯).
  2) 칸(16점)마다 시트 타일의 다른 16×16 조각을 떼어 쓰고 좌우 · 위아래 뒤집기도 칸마다 다르게 — 같은 무늬가 규칙적으로 되풀이되지 않음, 점은 늘이지 않음. 풀은 세 가지(풀 · 흰꽃 풀 · 분홍꽃 풀), 흙은 두 가지를 큰 잡음으로 섞음. 물은 시트 연못의 청록 4 색 + 가끔 물결.
  3) 풀 끝은 어둡게(흙 · 돌을 만나는 곳), 풀 아래 흙에 그늘, 물가는 돌 · 짙은 물.
  4) 흩뿌림: 풀포기 · 작은 꽃 · 흙자국 · 꽃덤불(풀밭), 자갈(흙 · 돌판), 흙길 가장자리 풀포기, 연잎 · 연꽃(물).
- 바뀐 곳: plaza.js 지도 부분 다시 씀 — `DIRT LAWN PAVE WATER MOSS` · `oval` · `unblock` · 새 지도 배치 · `CHR_FR` · `JOS_FR` · `JOS` · `loadAtlas` · `atlasSprite` · `js` · `vnoise` · `drawGround` · `drawGroundPlain`(그림을 못 받으면 땅 색만) · `jangdokImg` · `PLACES` · `put` · `bld` · 소품 배치 · `TREES` · `scatter` · `WORLD` · `buildWorld`, `spawn`, 프레임의 소품 그리기(`fade`). 예전 손그림 소품(`treeImg` `houseImg` `gateImg` `fenceImg` `southGateImg` `castleWallImg` `wellImg` `lanternImg` `stallImg`) · `VIL` · `drawGroundVil` 은 지움(`jangseungImg` 만 남김). `__plazaDebug` 에 `solid` `ground` `W` `H` `props` `WORLD`(시험용). plaza_server.py `MAP_W/MAP_H` · FILES(`joseon.png` 넣고 `village.png` 뺌). selftest.py PNG 이름.
- 확인한 것: `node --check`, `py_compile`, `python plaza/selftest.py` 모두 통과. 대시보드 서버가 광장을 2026-10-19.4 로 스스로 바꿈. 브라우저(그림 받고 그리기까지 약 2.6초 · 스크립트 오류 · 빠진 파일 없음):
  - 지도 전체(2100×1460 창) · 구역마다 확대 화면.
  - 갈 수 있는 곳 BFS: 관아 앞 · 광장 · 서쪽 길 · 주거 골목 남북 · 시장 통로 · 시장 남쪽 · 다리 · 정자 앞 · 성문 앞 · 동쪽 길 끝 모두 이어짐.
  - 충돌: 관아 기단(위로 걸으면 10줄에서 멈춤) · 당산나무 줄기 · 연못 물 · 닫힌 성문(34줄에서 멈춤)은 막히고, 나무다리는 건너감(12 → 6줄), 시장 통로는 지나감.
  - 앞뒤: 한옥 뒤(지붕 아래)에 서면 한옥이 반투명해지고 이름표는 보임. 시험 캐릭터 6(다른 주소) 함께 · 겹침 없음.
  - 화면 크기: 640×420 · 1100×700 · 1920×1080 · 대시보드 홈 안 모두 정상(카메라가 지도 끝에서 멈춤).
- 회사에서 확인할 것: 처음 들어갈 때 그림 두 장(약 330KB)을 받고 땅을 그리느라 2~3초 걸릴 수 있음. 지도가 넓어져 예전 자리(56×32 안)에 있던 사람도 그대로 들어오지만, 새로 들어오는 사람은 광장 둘레에서 시작.

### 2026-10-22 (1) — 계장 광장: EPC 발전플랜트 현장 RPG (설비 점검 · 수리 · 경험치 · 기력 · 유닛장 회복 오라 · NPC) (PLAZA_VERSION 2026-10-22.1 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 조선 마을 배경을 **EPC 발전플랜트 현장**으로 바꾸고, 계장 설비를 점검 · 교정 · 수리하는 놀이를 넣음. 광장 기능(이동 · 대화 · 공격 · 체력/유령 · killer · 캐릭터 정보 · 상태 표시 · 얼굴 바꾸기 · 역할)은 그대로, 캐릭터 디자인(고양이 기사 · 사람 · 마을 캐릭터 5종 · 노비)도 그대로. **실제 DCS · 계장 설비와는 아무 연결이 없다(모든 값은 광장 안에서만).**
- 참고 그림: 사용자가 말한 `assets/reference/wide_detailed_isometric_top_down_game_concept.png` 는 저장소 · PC 어디에도 없음. 첨부 사진(발전플랜트 콘셉트 그림 · 계장 아이콘 · 변전소 게임 화면 · 엔지니어 스프라이트)은 **구성 · 색감 참고만** 하고 그림은 쓰지 않음 — 콘셉트 그림은 등각 시점이라 탑다운인 광장과 안 맞고, 아이콘 · 엔지니어 스프라이트는 다른 회사 사이트의 그림. 설비 · 건물은 전부 캐릭터와 같은 화풍(2px 점 · 짙은 외곽선 · 왼쪽 위 빛)으로 코드가 그림 (그림 파일 0 개 추가, `joseon.png` 는 지움).
- 지도(64 × 44 칸, 크기는 그대로): A 주 발전동(터빈 홀 · 발전기동 · 연돌 항공등) / B 공정 · 유틸리티(냉각수 펌프 스키드 3 · 열교환기 · 냉각탑 2셀, 팬이 돎) / C 배관랙 통로(6 줄 배관 · 케이블 트레이 · 철골 기둥 5 칸마다 · 사다리, 밑은 그레이팅) / 동서 · 남북 큰길(차선 · 횡단보도) / D 변전(울타리 · 변압기 2 · 단로기) · MCC/E-HOUSE · 마샬링 / E 중앙 제어실(지붕 없는 단면 — 영상 벽 · 경보창 · 콘솔 2 · 의자 · DCS/I/O/PLC/마샬링 캐비닛, 북쪽 입구) / F 시운전 구역(시험 전송기 · 밸브 · 임시 케이블 · LOOP CHECK 판 · 시험대 · 콘) / G 정비동(작업대 · 공구판 · 케이블 드럼 3 · 부품 선반) / H 현장 사무소(2층 컨테이너 사무실) · 해상 컨테이너 3 · 크레인(경고등) · 지게차 · 파이프 스풀 · 주차장(트럭 5) · 쉼터(자판기 · 벤치) · 경비실 · 정문 / 둘레 녹지 · 나무 · 조명탑 10(바닥 불빛). 바닥: 자갈 · 콘크리트(줄눈) · 아스팔트 · 그레이팅 · 에폭시(제어실) · 잔디를 점마다 무늬 + 큰 잡음으로 섞고, 구역 노란 안전선 · 맨홀 · 얼룩 · 그림자.
  - 걸을 수 있는 칸 1787, 모두 이어짐. 건물은 바닥 점유 칸만 막고, 뒤에 서면 반투명(예전 그대로). 시작 자리는 가운데 네거리 둘레 길 · 보도에 흩어짐.
- 설비 28 개(서버 `EQUIP` — PT · DPT · TT · FT · LT · CV · PG · JB · TRAY · MC · DCS · IO · PLC · CON): 상태 정상(초록 점) · 경고(주황 !) · 고장(빨간 ✕ 깜빡 + 바닥 붉은빛). 처음엔 경고 4 · 고장 2, 15초마다 1/2 확률로 정상 하나가 경고(동시 7 개까지), 경고를 3분 두면 고장.
  - 설비 옆(한 칸 안)에서 **E** → 정상: Loop Check 3초 +5 XP · 경고: 교정 5초 +10 · 고장: 수리 7초 +20. 내 직무의 설비면 0.6배 시간 · 1.5배 XP, 시운전 리드는 무엇이든 0.8배. 진행 막대 · 도구(HART 통신기 · 루프 교정기 · 렌치와 불똥 · 콘솔 화면빛 · 케이블 릴) · 완료 글씨 · 깡충 축하. 걸으면 작업 취소. 남이 작업 중인 설비는 '○○ 작업 중'. 교정 · 수리 · 레벨 업은 대화창에 알림.
  - 경험치는 이름별 `data/plaza/xp.json`(주간 마감과 상관없이 쌓임), 레벨 = √(XP/25)+1.
- 유닛장(roles.json `unit_leaders`) = **시운전 리드, 회복 오라**: 둘레 4 칸 안 팀원 체력 1초에 +1(최대 100, 유령은 안 됨 — 부활은 그대로 주간 마감), 기력 회복 2배. 발밑 바닥빛 · 맥동 점선 고리 · 퍼지는 물결 · 올라가는 초록/청록 입자, 회복될 때 '+1 HP' · 체력 막대가 부드럽게 늘어남. 설정은 plaza_server.py `HEAL_ROLES` `HEAL_RADIUS` `HEAL_PER_SEC`.
- 기력: Shift 로 달리기(한 칸 0.125초, 초당 −24), 쉬면 +12, 15 밑이면 지침(느리게 · 땀). 이동 키에 WASD 도.
- 직무: 계장 엔지니어 · DCS 엔지니어 · 현장 기술자 · 케이블 기술자 (얼굴 바꾸기 판 '직무'), 유닛장은 시운전 리드 고정. 이름 밑에 직무 · 레벨, 사람 목록에 직무 · Lv · 체력.
- NPC 5(계장 · DCS · 시운전 리드 · 현장 · 케이블, 마을 캐릭터 그림): 자기 직무 설비들을 A* 길로 돌며 7초씩 작업. 위치를 '지금 시각'으로 계산해 누구 화면에서나 같은 자리. 내 캐릭터는 NPC 칸에 못 들어가고, NPC 는 사람을 지나쳐 감(서버가 NPC 를 모름). 공격 · 회복 · 캐릭터 정보 대상 아님.
- 화면: 왼쪽 위 작은 상태판(HP · 기력 · Lv/XP · 직무 · 지금 하는 일 · 설비 현황), 가까운 설비 위 [E] 안내, 남색 철골 틀 · 현판 'EPC 발전플랜트 현장', 작은 화면에선 대화창 · 상태판을 줄임. 입자 180 개 풀 · 떠오르는 글씨 40 개까지(재사용).
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` · `LOOK_EXTRA.job` · 새 `HEAL_*` `EQ_*` `JOBS` `JOB_CATS` `WORK` `EQUIP` `EQ` `XP` `level_of` `eq_init` `eq_tick` `job_of` `eq_near` `heal_tick` `save_xp` `api_work`(start · done · cancel, 거리 · 시간 확인) `equip_defs` · `hp_loop`(1초) · `snapshot`(players 에 xp · lv · job · healer · heal_seq/age · cheer_age · work, 맨 위 eq · heal_r) · `api_move`(걸으면 작업 취소) · GET `/plaza/api/equip` · POST `/plaza/api/work` · FILES(joseon.png 뺌). plaza.js 지도 부분 다시 씀(땅 종류 · 배치 · `pix` · `building` 과 설비 · 건물 그림 함수들 · `drawGround` · `PLACES` · `put` · `loadEquip` · `buildWorld` · `findPath`) · 새 EPC 부분(`JOB_*` · 기력 · 입자 `PARTS` `puff` · `floater` · `nearEquip` · `interact` · `finishWork` · `cancelWork` · `NPC_DEF` `npcInit` `npcUpdate` `npcAt` · `drawHealAura` · `drawTool` · `drawEqMarks` · `updateHud`) · `spawn` · 틀 · `RANGES.job` · `newActor` · `epcFields` · `applySnapshot` · `occupied` · `stepActor`(달리기 · 지침) · `drawActor`/`drawActorBody` · `hpBar` · `jobTag` · `nameTag` · `frame` · 자판(E · Shift · WASD) · 얼굴 판 `jobRow`. plaza.html 상태판 · 안내 · 제목. plaza.css 상태판 · 작은 화면. selftest.py 설비 · 작업 · 경험치 · 회복 시험.
- 확인한 것: `py_compile`, `node --check`, `python plaza/selftest.py` 모두 통과(설비 목록 · 멀면 거절 · 시간 전 완료 거절 · 완료 XP · xp.json · 유닛장 곁 회복). 대시보드 서버가 광장을 2026-10-22.1 로 스스로 바꿈. 브라우저 두 사람(김철수 · 유닛장 홍길동): PT-101 Loop Check → +8 XP(계장 직무 1.5배), 고장 MC-302 수리 → 정상 · +20 · Lv 2, 걸으면 취소, 걷기 1.5초 8 칸 · 달리기 12 칸(기력 100 → 65), 터빈 홀 벽 · 랙 기둥 · 제어실 벽 막힘 · 제어실 입구로 들어감, 유닛장 곁 체력 73 → 77(4.5초) · 멀어지면 멈춤, NPC 5 가 설비마다 작업, 640×420 · 1100×700 · 1920×1080(60 fps) · 대시보드 홈 안, 스크립트 오류 · 빠진 파일 없음.
- 아직 안 한 것: 시트에 없는 동작(작업 · 축하 · 지침)은 도구 · 깡충 · 땀으로만 표현(캐릭터 그림 자체의 작업 포즈 없음). NPC 와 사람의 겹침은 내 쪽만 막음. 실내(제어실 외) 건물 안으로는 못 들어감.

### 2026-10-22 (2) — 계장 광장: EPC 시트 그래픽 · UI · 효과 (직무 캐릭터 작업 포즈 · 초상 상태판 · 도구칸 · 미니맵 · 장비/효과 아이콘) (PLAZA_VERSION 2026-10-22.2 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 사용자가 준 EPC 에셋 시트(안전모 쓴 직무 캐릭터 · 초상 · 계장 장비 · 도구 · UI 효과 아이콘)를 배경을 빼고 잘라 `static/epc.png`(512×201, 투명) 한 장으로 만들어 씀. 요청 "그래픽 · UI · 스킬 이펙트 동일한 수준으로". 콘셉트 그림(회사 로고 있음) · 게임 화면 예시는 구성 참고만.
- 캐릭터: 얼굴 종류에 **7 = EPC 안전모 (직무별)** 추가, 새 기본값. 직무 → 그림: 계장 엔지니어 고양이 · DCS 판다 · 시운전 리드 사자(유닛장) · 현장 기술자 호랑이 · 케이블 기술자 작업자. 시트 동작 그대로: 대기 · 걷기 5 · 점검 · HART · 케이블 · DCS · 수리 · 점프(축하 때) · 피격 · 축하 · 지침. 작업 종류와 설비에 따라 포즈가 바뀜. 시트에 뒷모습이 없어 위로 걸을 때도 앞모습. 유령은 같은 그림 반투명.
  - 예전에 저장된 얼굴(판 표시 `v` 없음)은 한 번만 EPC 안전모로 옮김. 얼굴 판에서 다시 고양이 기사 · 사람 · 마을 캐릭터로 바꿀 수 있고, 저장하면 `v: 2` 가 붙어 다시 안 옮김.
- 효과: 설비 그림 = 시트의 장비 아이콘(PT · DPT · TT · FT · LT · CV · PG · JB · MC · IO · PLC · CON · DCS 카드), 설비 상태 = LED(정상) · ?(경고) · 경보(고장) 아이콘. 작업 중 스캔 빛 · 불똥 · 케이블 연결 · HART 신호 아이콘, 완료 때 측정값 말풍선(가짜 값, 예 '4.02 mA OK'), 레벨 업 아이콘, 유닛장 회복 오라에 도는 + 십자.
- UI: 왼쪽 위 상태판을 남색 빛나는 판으로 — 내 직무 초상 · Lv · 직무 · HP/기력/XP 막대(시트 아이콘) · 하는 일 · 과제 줄 'LOOP CHECK 정상 n/28 · 경고 · 고장'. 아래 가운데 도구칸 5(Loop · 교정 · 케이블 · 측정 · 수리) — **누르는 버튼이 아니라 표시만**: 지금 작업에 노란 불, 내 직무 칸은 파란 테두리. 오른쪽 아래 미니맵(땅 · 건물 · 설비 상태 점(고장 깜빡) · 사람 · NPC · 지금 보이는 곳). 작은 화면에선 도구칸 · 초상 · 과제 줄을 숨기고 미니맵을 줄임(폭 560 밑은 미니맵도 숨김). 설비 위 '○○ 작업 중' 글씨는 작업자 머리 위 진행 막대와 겹쳐 뺌.
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` · `LOOK_EXTRA`(kind 8 · 새 v 4) · FILES(`/static/epc.png`). plaza.js 새 `EPC_FR` `EPC` `eps` `EQ_ICON` `JOB_CHAR` `isEpc` `epcWho` `workPose` `epcPose` `fxIcon` `POPS` `reading` `drawPops` `paintIcons` `hudPortrait` `TOOL_OF` `JOB_TOOL` `drawMini` · 바뀐 `atlasSprite`(그림 묶음별 캐시 키) · `eqImg` · `KINDS` `RANGES`(v) · `defaultFace` · `faceOf`(옮김) · `drawActorBody`(EPC 갈래) · `drawTool` · `drawEqMarks` · `drawHealAura` · `updateHud` · `frame` · 얼굴 판(초상 · 설명 · 저장 v) · NPC 얼굴. plaza.html 상태판 · 도구칸 · 미니맵. plaza.css 같은 것. selftest.py 얼굴 기대값(v) · epc.png.
- 확인한 것: `node --check`, `py_compile`, `python plaza/selftest.py` 모두 통과. 시험 서버에서 광장이 2026-10-22.2 로 바뀜. 브라우저(1500×900 · 900×560 두 사람): EPC 캐릭터 · NPC 그림, PT-101 Loop Check 포즈 · 스캔 효과 · 진행 막대 · 완료 말풍선, 상태판 초상 · 아이콘 막대 · 과제 줄, 도구칸 'Loop' 불, 미니맵 점 · 보이는 곳 네모, 달리기, 얼굴 판 초상, 스크립트 오류 · 빠진 파일 없음.
- 회사에서 확인할 것: 처음 들어가면 캐릭터가 모두 EPC 안전모로 바뀜(정상). 예전 모습을 원하면 '얼굴 바꾸기'에서 종류를 바꾸고 저장.

### 2026-10-22 (3) — 계장 광장: EPC 캐릭터 뒷모습 · 아이템(무작위 3 개 · 쓰러지면 떨어뜨림 · 밟으면 주움) · 운영자 무적 · 운영자 부활 (PLAZA_VERSION 2026-10-22.3 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 뒷모습: EPC 시트에 뒷모습이 없어, 앞모습(대기 · 걷기 5)을 고쳐 만든 30 칸을 `static/epc.png` 맨 아래 줄에 붙임(512×201 → 512×272): 안전모 앞 로고 지움 · 얼굴 → 털/머리 뒤통수(고양이 주황 · 판다 흰색+검은 귀 · 사자 갈기 · 호랑이 줄무늬 · 작업자 갈색 머리) · 등 반사띠 · 꼬리(고양이 · 사자 · 호랑이). 위로 걷거나 위를 보고 서 있으면 뒷모습(유령도). 이름 `<동물>_back_idle` `<동물>_back_w0~4`.
- 아이템: EPC 시트의 도구 그림 20 종(HART 통신기 · 멀티미터 · 루프 교정기 · 케이블 드럼 · 계장 케이블 · 글랜드 · 단자대 · 에어/임펄스 튜브 · 포지셔너 · 교정 펌프 · 안전모 · 조끼 · 렌치 · 드라이버 · 노트북 · 점검표 · 무전기 · 압력계 · DCS 카드). 처음 들어온 사람은 무작위 3 개. 쓰러지면(유령) 가방을 그 자리에 떨어뜨림(튀어나와 흩어지는 그림 · 반짝임 · 대화창 알림). 산 사람이 그 칸을 밟으면 주움(가방 8 칸, 떨어진 지 0.8초 뒤부터). 부활하면 빈 가방은 새로 3 개. 주간 마감에 바닥은 치우고 빈 가방은 새로. 가방은 상태판 아래 8 칸 · 캐릭터를 누르면 '가방: …'. 아이템은 모으는 것뿐(능력치 없음). 파일 `data/plaza/items.json`.
- 운영자: **무적**(맞아도 체력 안 줄고 쓰러지지 않음 · 체력 막대 금색 ∞ · 상태판 '∞ 무적'). **부활**: 유령 곁(2.5 칸 안)에서 **R** (또는 유령을 눌러 '부활 (운영자)' 단추) → 체력 100 · 빛기둥 · '부활!' · 대화창 '✨ 운영자 ○○ 님이 △△ 님을 부활시켰습니다'. 운영자 곁 유령 위에 '[R] 부활' 안내.
- 배경: 요청의 '첨부처럼' 그림이 이번 메시지에 안 붙어 와서 이번엔 바꾸지 않음.
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` · 새 `hp_p`(운영자 = 늘 가득) · `ITEM_NAMES` `ITEM_START` `ITEM_MAX` `GROUND_MAX` `REVIVE_DIST` `ITEMS` `load_items` `save_items` `give_items` `drop_items` `pick_up` `items_new_week` `api_revive`(POST `/plaza/api/revive`) · `check_week` · `heal_tick` · `api_work` · `snapshot`(players 에 inf · items · revive_age/by, 맨 위 ground) · `api_join`(아이템 줌) · `api_move`(줍기 → picked) · `api_attack`(운영자 무적 · 쓰러지면 떨어뜨림) · `equip_defs`(items) · `hp_loop`(저장) · `main`. plaza.js `EPC_FR`(뒷모습) · `epcPose` · 유령 그림 · `epcFields` · 새 `ITEM_DEF` `itemName` `GROUND` `G_SEEN` `drawGroundItems` `drawRevive` `nearGhost` `revive` · `applySnapshot`(ground) · `loadEquip` · `frame` · `hpBar`(∞) · `updateHud`(가방) · R 키 · `showCtx`(가방 · 부활 단추) · 안내 글. plaza.html 가방 칸 · 안내. plaza.css 가방. selftest.py 아이템 · 부활 · 무적 시험(첫 때리기 시험은 운영자를 때리므로 '무적'으로 바꿈).
- 확인한 것: `node --check`, `py_compile`, `python plaza/selftest.py` 모두 통과(들어오면 3 개 · 쓰러지면 바닥에 3 개 · 밟으면 주움 · 부서원 부활 403 · 멀면 400 · 곁이면 200 · 유령 아니면 400 · 운영자 무적 · items.json/hp.json 기록). 브라우저 두 사람(김철수 · 운영자 박민수): 위로 걷기/서기 뒷모습, 운영자를 때려도 안 맞음, 박민수가 김철수를 쓰러뜨림 → 아이템 3 개 튀어나옴 · 대화창 알림, 그 칸을 밟아 주움(+ 글씨 · 가방 6 칸), [R] 부활 안내 → R → 빛기둥 · 체력 100 · 새 아이템 3 개, 스크립트 오류 · 빠진 파일 없음.
- 회사에서 확인할 것: 운영자는 roles.json `operators` 에 있는 사람(광장 '역할 지정'). 처음 적용하면 광장에 있던 사람 모두 아이템 3 개를 받음.

### 2026-10-22 (4) — 계장 광장: 레벨 → 최대 체력 · 마나 증가 / 마나 쓰는 기술 3 개 (PLAZA_VERSION 2026-10-22.4 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 레벨이 오르면 최대 체력 · 마나가 오르고, 마나를 쓰는 기술을 넣음. 요청 "레벨 오르면 체력과 마나도 오르게, 스킬 마나 사용 적절하게".
- 체력: 최대 = 100 + 레벨마다 10 (Lv 2 110 · Lv 5 140, Lv 30 까지). 맞으면 그대로 1 씩. 기록이 없으면 가득이라 레벨이 오르면 바로 늘어난 만큼 가득.
- 마나: 최대 = 50 + 레벨마다 5. 1초에 +1 찬다(유령은 안 참). 주간 마감 · 부활 · 서버 다시 켜면 가득. 상태판에 보라색 막대.
- 기술 (키 1 · 2 · 3 또는 아래 가운데 기술 칸을 누름): **1 강타** 마나 10 · 3초 — 앞 사람 체력 −5 (평타는 −1) / **2 응급 처치** 마나 20 · 8초 — 내 체력 +25 / **3 현장 지원** 마나 30 · 15초 — 둘레 3 칸 팀원 체력 +15 · 기력 +30. 앞에 사람이 없거나 체력이 가득하거나 둘레에 팀원이 없으면 마나를 안 씀. Lv 1 마나 50 이면 강타 5 번 또는 지원 한 번 + 응급 한 번 정도, 다 쓰면 50초에 다시 참.
  - 효과: 강타 불꽃 고리 · 튀는 불똥 · '강타!' / 응급 처치 초록 고리 · 하트 · 올라가는 초록빛 / 현장 지원 3 칸까지 퍼지는 청록 고리 · 둘레 빛 알갱이 · 대화창 알림. 맞으면 머리 위에 '−5' · '−1' (운영자는 '무적'), 회복은 '+15 HP' 처럼 실제 양.
  - 기술 칸: 아이콘 · 키 · 마나 숫자, 재사용 중엔 어두운 덮개 + 남은 초, 마나 모자라면 빨간 테두리, 유령이면 흐림. 폭 1100 밑에선 도구칸은 숨기고 기술 칸만, 폭 700 밑에선 숨김(키는 됨).
  - 운영자도 기술을 씀(무적은 그대로). 값은 plaza_server.py `SKILLS` `STRIKE_DMG` `AID_HEAL` `SUPPORT_HEAL` `SUPPORT_R` `HP_PER_LV` `MP_BASE` `MP_PER_LV` `MP_REGEN` 에서 바꾸면 화면도 따라감(`/plaza/api/equip` 로 받음).
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` · 새 `HP_PER_LV` `MP_*` `LV_CAP` `SKILLS` 값들 `MP` `lv_of` `hp_max` `mp_max` `mp_of` `set_hp` `damage` `mp_tick` `api_skill`(POST `/plaza/api/skill`) · `hp_of`(레벨 최대) · `hp_p` · `load_hp` · `check_week`(마나 가득) · `heal_tick` · `hp_loop` · `api_attack`(damage 로) · `api_revive` · `snapshot`(hp_max 레벨별 · mp · mp_max · skill/seq/age · hit_dmg · heal_amt) · `equip_defs`(skills). plaza.js 새 `SKILL` `SKILL_KEYS` `dmgFloat` `skillFx` `useSkill` `drawSkillFx` `updateSkillBar` · `epcFields` · `applySnapshot`(맞은 양) · `loadEquip` · `updateHud`(마나) · `paintIcons` · `frame` · 키 1·2·3 · 레벨 업 안내. plaza.html 마나 막대 · 기술 칸 · 안내. plaza.css 같은 것. selftest.py 기술 · 레벨 시험(xp.json 에 '고수' 400 XP = Lv 5).
- 확인한 것: `node --check`, `py_compile`, `python plaza/selftest.py` 모두 통과(강타 −5 · 마나 70→60 · 재사용 거절 · 지원 회복 · 마나 50→20 · Lv 5 체력 140 · 마나 부족 거절). 브라우저 두 사람(김철수 Lv 2 체력 110 · 마나 55 / 운영자 박민수): 1 강타 −5, 2 응급 처치, 3 현장 지원 +15, 운영자를 치면 '무적', 앞에 없으면 '앞 칸에 사람이 없습니다', 기술 칸 재사용 덮개 · 남은 초, 스크립트 오류 없음(지원 고리 크기가 음수가 되던 것 고침).

### 2026-10-22 (5) — 계장 광장: 아이템 공격력 · 마법 공격력(무작위 · 등급) / Z 로 줍기 / 사람끼리 교환 / 마법 기술 '전기 충격' (PLAZA_VERSION 2026-10-22.5 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 요청 "죽으면 아이템 떨어트리게, 떨어진 아이템은 Z 키로 먹게, 아이템은 상대방과 교환할 수 있도록, 아이템 공격력은 랜덤으로 적절하게, 마법 공격력도".
- 아이템마다 **공격력 · 마법 공격력 · 등급**: 등급 일반 70% · 고급 22% · 희귀 7% · 전설 1% (배수 1 · 1.6 · 2.4 · 3.5), 값 = 종류 성향 × 2~5 × 배수. 공구(렌치 · 드라이버 · 케이블 드럼 …)는 공격, 계측 · 통신 · 전자(HART · 노트북 · DCS 카드 · 무전기 …)는 마법 쪽 (`ITEM_W`). 예: 일반 렌치 공 3~8, 희귀 케이블 드럼 공 14. 가방(8 칸)에 든 것의 합이 내 공격력 · 마법 공격력.
  - 예전(판3) 파일의 '종류만 있는 아이템'은 처음 읽을 때 값을 새로 굴려 붙임.
- 피해 · 회복 (공 = 공격력, 마 = 마법): 평타(Space) 1 + 공/10 · 1 강타 5 + 공/4 · **4 전기 충격(새 마법 기술, 마나 15 · 4초)** 보는 쪽 4 칸 안 첫 사람 4 + 마/3 · 2 응급 처치 +25 + 마/3 · 3 현장 지원 +15 + 마/4. 가방 합이 공 20 · 마 15 쯤이면 평타 3 · 강타 10 · 전기 9 → 체력 100 을 평타만으론 30 대쯤. 식은 plaza_server.py `dmg_basic` `dmg_strike` `dmg_bolt` `heal_aid` `heal_support`.
- 죽으면 떨어뜨림(그대로) — 대화창에 아이템 · 값까지. 바닥 아이템: 고급 이상은 등급 색 바닥빛, 곁에 가면 '[Z] 이름 공·마'.
- **Z 로 줍기**: 선 칸 + 둘레 8 칸의 아이템을 가까운 것부터 가방이 찰 때까지(밟기만 해서는 안 주움). 가방이 차면 '가방이 가득' 안내.
- **교환**: 상대를 눌러 '교환' → 내 가방 · 상대 가방에서 고르고(여러 개 · 한쪽만 = 선물도 됨) '교환 제안' → 상대 화면 위에 제안 판(받음/줌 그림 · 값) '수락 · 거절', 보낸 쪽엔 '기다리는 중 · 취소'. 3 칸 안 · 1분 · 둘 다 살아 있어야 함 · 그사이 아이템이 바뀌면 취소 · 가방이 넘치면 거절. 끝나면 대화창 '🤝 A ↔ B 교환 — …' · 둘 머리 위 '교환!'.
- 화면: 상태판에 '⚔ 공격력 · ✦ 마법 · 평타', 가방 칸 테두리 = 등급 색(희귀 · 전설은 빛), 캐릭터를 누르면 가방 그림 · 공격력 · 마법. 기술 칸에 '4 전기'. 폭 1360 밑에선 도구칸을 숨기고 기술 칸만(대화창과 겹침 방지).
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` · 아이템 부분 다시 씀(`ITEM_W` `RARITY` `PICK_DIST` `TRADE_DIST` `TRADE_S` `TRADES` `make_item` `fix_item` `load_items` `save_items` `bag` `power` `item_txt` `give_items` `drop_items` `api_pickup`(POST `/plaza/api/pickup`) `dist` `api_trade`(POST `/plaza/api/trade` offer · accept · decline)) · `pick_up` 없앰(걸어서 줍기 없음) · `SKILLS.bolt` `BOLT_*` `dmg_*` `heal_*` · `api_attack` · `api_skill`(bolt · 값 반영) · `snapshot`(items 에 값 · atk · matk · trade_age · skill_to · ground 에 등급/값 · trades) · `equip_defs`(rarity · trade_dist). plaza.js 새 `RARE` `RARE_COL` `itemStat` `itemFull` `itemIcon` `pickup` `openTrade` `closeTrade` `fillTrade` `sendTrade` `answerTrade` `showTrades` · `itemName` · `epcFields` · `drawGroundItems` · `SKILL.bolt` · `drawSkillFx`(번개) · `useSkill` · `updateHud`(가방 · 힘) · 키 Z · 4 · Esc · `showCtx`(가방 그림 · 교환). plaza.html 교환 판 · 제안 판 · 힘 줄 · 기술 4 · 안내. plaza.css 같은 것. selftest.py 아이템 값 · Z 줍기 · 강타/전기 식 · 교환 시험.
- 확인한 것: `node --check`, `py_compile`, `python plaza/selftest.py` 모두 통과(값 붙음 · 멀면 못 주움 · 밟기만으론 안 주움 · 곁에서 Z 3 개 · 강타 = 5 + 공/4 · 전기 = 4 + 마/3 · 남의 아이템 제안 거절 · 멀면 거절 · 받는 사람만 수락 · 수락하면 서로 바뀜 · 끝난 제안 404). 브라우저 두 사람(김철수 · 운영자 박민수): 4 전기 충격 번개 · −8 → 쓰러져 3 개 떨어뜨림, [Z] 안내 · Z 로 주움(가방 8 칸 가득 → 1 개 남음 안내), R 부활, 김철수가 박민수를 눌러 교환 판 → 제안 → 박민수 화면 제안 판 → 수락 → 서로 바뀜 · 대화창, 스크립트 오류 없음.
- 회사에서 확인할 것: 판3 의 아이템은 처음 켤 때 값이 무작위로 새로 붙음. 평타가 세져서(1 → 1 + 공/10) 유령이 예전보다 빨리 나옴 — 너무 세면 `dmg_basic` 의 10 을 키우면 됨.

### 2026-10-22 (6) — 기술공유 최신순 · 왼쪽 메뉴 숨기기 · 수행/입찰 열 숨기기(나에게만) · 엑셀식 복사/선택 · 그룹장 권한 · 게시판 피드형 · 홈 배치 · LNG/수소 묶기 · 담당자 그래프 수행/입찰 색 (APP_VERSION 2026-10-22.1 / SERVER_VERSION 2026-10-22.1)
> server.py 가 바뀜 → **서버 재시작 필요** (8장 3번). 부서원 사본은 새 버전 [다운로드] 배너로 받음.
- 1 기술공유: 기술공유 시트와 통합 업무의 '기술공유' 유형 모두 **최신 날짜가 맨 위**(발표일 → 시작일 → 종료일, 날짜 없는 행은 아래). 열 필터의 정렬을 고르면 그쪽이 우선. 바뀐 곳: `dateDesc` `tsDate` `sortRecs`.
- 2 왼쪽 메뉴 숨기기: 사이드바 로고 옆 **◀ 숨기기**, 숨기면 위 ☰ 단추가 '☰ 메뉴'(다시 열기). 넓은 화면에서 숨긴 상태를 이 PC 에 기억(localStorage `dept-nav-closed`). 좁은 화면(900px 이하)은 예전처럼 겹쳐 여닫기. 바뀐 곳: `#sideHide` · `setNavClosed` · CSS `body.nav-closed #burger`.
- 3 수행 · 입찰 열 숨기기: 머리글 ▾ → '🙈 이 열 숨기기 (나에게만)' 또는 셀을 고르고(여러 열은 Shift/Ctrl) 툴바 '🙈 선택 열 숨기기'. **숨긴 사람에게만** 적용(이 PC localStorage `dept-hidecols`, 로그인 이름별 — 다른 PC 에서 같은 사람으로 들어오면 그 PC 에서 다시 숨겨야 함). 표 위에 '🙈 숨긴 열 n개' 줄(이름을 누르면 그 열만 · '모두 보이기'), 숨긴 자리 바로 오른쪽 머리글에 '◂n' 표시(누르면 다시 보임). PJT명(제목 열)은 숨기지 않음. 엑셀 내보내기 · 다른 부서원 화면 · 데이터는 그대로. 바뀐 곳: `LS_HIDE` `HIDE_SHEETS` `hiddenCols` `setHidden` `hideCols` `visCols` · `tableHtml` · `drawTable` · `openCf`(data-cfhide) · `renderSheet`(#fHide) · 본문 클릭(data-unhide).
- 4 엑셀식 복사 · 선택: Ctrl+C 가 **엑셀 표 모양**(탭 구분 글 + HTML 표, 칸 안 줄바꿈 유지)으로 복사 → 엑셀 · 메일 · PPT 에 표로 붙여넣기. 예전엔 `navigator.clipboard` 를 써서 http://PC이름:8080 (보안 연결 아님)에서 복사가 안 됐음 → 브라우저 copy 이벤트에 직접 넣음(안 오면 예전 방식). **Shift+방향키** = 범위 늘리기, **머리글 클릭** = 열 전체(Shift = 열 범위, Ctrl = 더하기), **작업 칸 빈 곳 클릭** = 행 전체(Shift = 행 범위), **마우스로 끌기** = 사각형 범위. 바뀐 곳: `selGrid` `copySel` copy 이벤트 · `nextCell` `moveSel` `extendSel` `selectLines` · 끌기(`DRAG`) · 키 처리 · 본문 클릭.
- 5 그룹장 권한: server.py `SUPER_NAMES = ('구종현',)` — 운영자(서버 PC)와 같은 권한: 모든 메뉴(Management 포함) · 금주 마감 · 휴지통 영구삭제 · 게시판 관리자 삭제 · 시수 실제 시간. **메뉴 권한 설정(⚙, 부서원 권한 주기)만 운영자(서버 PC)** 그대로. 로그인 계정 본명으로 확인(토큰). `/api/info` · `auth/ping` 에 `super` 추가, 화면은 `SUPER` · `MGR()`. 바뀐 곳: server.py `SUPER_NAMES` `is_super` `need_super` · `need_menu` · info · ping · 시수 · trash 영구삭제 · close · board 삭제 / dashboard.html `SUPER` `MGR` `setPerms(p, sup)` `can` `closeWeek` `openTrash` `bAdmin` `renderHeader` `serverLabel` `refreshPerms`.
- 6 익명게시판: 인스타그램 느낌 피드 — 가운데 한 줄 카드, 유형 '스토리' 동그라미(전체 · 블라블라 · 회식제안 · VOC + 글 수), 둥근 검색창, '무슨 이야기를 나눠 볼까요?' 글쓰기 상자, 동그란 프로필(익명 🙂 회색 · 닉네임 색 · 실명 파랑 ✔ · 테두리 = 유형 색), '몇 분 전', 유형 색 카드 안 제목 · 본문, 긴 글은 접고 '… 더 보기', 댓글은 최근 2 개 미리보기 + '댓글 n개 모두 보기', 아래 '댓글 달기… 게시'. 기능(익명/닉네임/실명 · 수정 · 삭제 · 관리자 삭제)은 그대로. 바뀐 곳: `renderBoard` `drawBoard` `agoText` `avatarHtml` · `boardAction`(more) · CSS `.ig*`.
- 7 주간업무보고 첫 화면: 아래 칸을 **왼쪽 = 주간회의 전달사항(크게, 최대 620px · 글자 14.5) + 계장 광장**, **오른쪽 = 최근 변경 이력(작게 · 스크롤 460px)**. 이력은 지난 마감 이후 ~ 이번 주 마감 전까지 전부(건수 표시), '반으로 접기' 단추는 없앰. 바뀐 곳: `renderHome` · CSS `.memo.big` `.recentside`.
- 8 LNG/수소: 그래프 · 사업군 칩에서 LNG 와 수소를 **'LNG/수소' 하나**로(홈 '사업군별 PJT 수' · 수행/입찰 PJT 보드 사업군 칩 · 사업군별 막대 · 표 필터). 마우스를 올리면 'LNG n개 · 수소 n개 · LNG/수소 n개'(엑셀 사업군 값 기준)와 PJT 목록(각 PJT 의 구분). 바뀐 곳: `BIZ_LH` `bizGrp` `lhKind` `lhSplit` `lhLine` · `renderHome` · `pjHero`(`bizTip`) · `filteredRecs`.
- 9 담당자별 담당 PJT 수(홈): 한 막대에 **수행(파랑) · 입찰(주황)** 을 쌓고 끝에 '5 (3 + 2)', 막대 조각에 마우스 = 그쪽 PJT 만, 이름 · 줄 = '■ 수행 n건 … ■ 입찰 n건 …' 로 나눠서. 제목 옆 범례. 바뀐 곳: `PJ_COL` · `svgBars`(parts) · `renderHome`.
- 확인한 것: `py_compile`, JS 문법(`node --check`, 스크립트 부분), 임시 폴더 서버(사본 데이터)로 브라우저: 기술공유 · 통합 업무 기술공유 최신순, ◀ 숨기기 → 새로고침해도 숨김 · ☰ 메뉴로 열림, 열 숨기기(▾ · 선택 열) → 숨긴 열 줄 · ◂ 표시 · 다시 보이기, Shift+→→↓ = 6 칸 · 복사 글/HTML 표, 머리글 클릭 = 열 · Shift = 2 열, 작업 칸 = 행, 끌기 = 15 칸, 구종현(서버 PC 아님) 금주 마감 단추 보임 · ⚙ 안 보임 · Management 보임 · `admin/perms` 403 / 일반 부서원 금주 마감 403, 게시판 피드, 홈 배치, LNG/수소 툴팁, 수행/입찰 막대 툴팁, 스크립트 오류 없음.
- 회사에서 확인할 것: 엑셀에 붙여넣기(표 모양 · 칸 안 줄바꿈). 구종현 계정의 본명이 정확히 '구종현' 이어야 함(띄어쓰기 없이) — 다르면 server.py `SUPER_NAMES` 를 고침.

### 2026-10-22 (7) — 계장 광장: 아이템 들기(선택) · 내려놓기 · 단축키 판 · 얼굴 바꾸기 점검(머리 그리드 안 숨던 것 고침) (PLAZA_VERSION 2026-10-22.6 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 아이템 들기(선택): 상태판 가방 칸을 누르거나 **Q**(가방의 다음 것, 끝이면 내려놓은 상태) → 든 아이템은 노란 테두리 · 상태판 '🖐 들고 있음: …' · 캐릭터 손 옆에 그림(모두에게 보임, 희귀 이상은 빛). **X** = 든 아이템을 선 자리에 내려놓음(남이 Z 로 주움 · 0.8초 뒤부터). 교환 판을 열면 든 아이템이 '줄 것'에 미리 골라짐. 서버 POST `/plaza/api/hold` `{item}` (없으면 내려놓음) · POST `/plaza/api/drop` `{item}` · snapshot players 에 `held`.
- 단축키 판: **H · ?** 또는 오른쪽 아래 '⌨ 단축키' 단추 — 걷기 · 달리기 · E · Space · 1~4 기술(마나 · 식) · Q · X · Z · Enter · 사람 클릭 · R. Esc 로 닫음. 판이 열려 있으면 키가 캐릭터로 안 감.
- 얼굴 바꾸기 점검(브라우저로 8 종류 × 저장 · 새로고침 · 취소 · 사람 머리 10 종): 저장 · 유지 · 취소 모두 정상. **고친 것**: 사람(머리 모양 그리드)에서 다른 종류로 넘기면 머리 그리드가 그대로 보이던 것 — `.pz-hairs{display:grid}` 가 `hidden` 을 이김 → CSS `[hidden]{display:none!important}`.
- 마법 · 기술: 1~4 키와 기술 칸 클릭 둘 다 됨을 다시 확인(앞에 사람이 없거나 체력이 가득하면 마나 안 씀). 바뀐 곳: plaza_server.py `PLAZA_VERSION` `api_hold` `api_drop` · snapshot(held) · POSTS. plaza.js `S.held` `holdItem` `holdNext` `dropHeld` `drawHeld` `KEY_ROWS` `toggleKeys` · `updateHud`(가방 칸 클릭 · hud-held) · `epcFields`(heldItem) · `drawActor` · `openTrade` · 키 Q · X · H · ?. plaza.html 가방 안내 · `#hud-held` · `#pz-keys` · '⌨ 단축키'. plaza.css 같은 것 + `[hidden]`. selftest.py 들기 · 내려놓기 · 다시 줍기.
- 확인한 것: `node --check` · `py_compile` · `selftest.py` 모두 통과. 브라우저 두 사람: 가방 칸 클릭 → 들림 · 상대 화면에 손 옆 그림, Q 두 번(다음 → 없음), X · Z, 1~4 (전기 충격 55→40 · 현장 지원 → 11 · 상대 +17), H → 15 줄 판 → Esc, 단추로 열기, 사람 → 고양이 양반에서 머리 그리드 숨김, 교환 판 미리 선택, 스크립트 오류 없음.

### 2026-10-22 (8) — 계장 광장: 사람 캐릭터 없앰(동물만) · 케이블 기술자 = 검은 고양이 · 아이템 착용(더블클릭 · F) → 모습 바뀜 (PLAZA_VERSION 2026-10-22.7 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 사람 캐릭터 없앰: 얼굴 바꾸기 '종류'에서 '사람'을 뺌 → 고양이 기사 · 고양이 양반 · 팬더 학자 · 사자 무관 · 호랑이 무관 · EPC 안전모 (동물만). 무작위 단추도 동물 종류 중에서. 예전에 '사람'으로 저장한 얼굴은 EPC 안전모로(화면 `faceOf` · 서버 `clean_look` 둘 다).
  - EPC 안전모의 케이블 기술자는 사람(작업자) 그림이었음 → **검은 고양이** (치즈 고양이 그림 22 칸의 털색만 짙은 회색으로 바꿔 `epc.png` 맨 아래에 붙임 · `bcat_*` `p_bcat`). NPC 케이블 기술자도 같음.
  - 운영자 = 노비(마을 시트)는 예전 요청대로 그대로 둠 — 노비도 없애려면 plaza.js `roleFace` 의 `kind: 6` 을 바꾸면 됨.
- 아이템 착용: 상태판 가방 칸 **더블클릭**(또는 고른 뒤 **F**) → 손(도구) · 머리(안전모) · 몸(안전 조끼) 칸에 끼기 / 다시 하면 벗기. 낀 칸은 초록 테두리, 상태판 '착용 🖐 렌치 ⛑ 안전모 🦺 안전 조끼', 캐릭터를 누르면 '착용: …'.
  - 모습: 손 = 도구가 손 옆에 · 몸 = 주황 안전 조끼를 입음 · 머리 = EPC 캐릭터는 자기 안전모 색이 등급 색(일반 노랑 · 고급 초록 · 희귀 파랑 · 전설 금), 다른 캐릭터는 머리 위에 작은 안전모. 희귀 · 전설을 끼면 반짝이. 걷기 · 옆 · 뒷모습에서도 보이고, 다른 사람 화면에도 보임.
  - 능력치: 낀 아이템은 공격력 · 마법이 **두 배**로 셈(가방 합 + 낀 것 한 번 더). 가방에서 빠지면(내려놓기 · 교환 · 쓰러짐) 저절로 벗음. 저장 `data/plaza/items.json` 의 `eq`.
  - 단추 정리: 클릭 = 고르기(내려놓기 X · 교환용), 더블클릭 · F = 끼기, 단축키 판에 F 줄 추가. 예전 '들기(손에 보임)'는 '착용 손'으로 합침.
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` · 새 `SLOTS` `SLOT_NAME` `slot_of` `equipped` `api_equip`(POST `/plaza/api/equip`) · `power`(낀 것 한 번 더) · `load_items` `save_items`(eq) · snapshot(`equip`) · `clean_look`(kind 1 → 7). plaza.js `EPC_FR`(bcat) · `JOB_CHAR` · `KINDS` · `faceOf` · `kindRow` · 무작위 · `NPC_DEF` · 새 `SLOT_ICON` `equipItem` `rareTint` `helmTint` `HELM_COL` `drawEquip` · `drawHeld`(손 착용) · `drawActorBody`(그림 위치 `_top` `_h` `_ox` · 안전모 색) · `updateHud`(착용 줄 · 더블클릭) · `epcFields`(equip) · 키 F · `KEY_ROWS` · `showCtx`. plaza.html `#hud-equip` · 안내. plaza.css `.worn` · `.equip`. epc.png(512×334). selftest.py 착용 · 벗기 · 사람 → EPC.
- 확인한 것: `node --check` · `py_compile` · `selftest.py` 모두 통과. 브라우저: 종류 한 바퀴에 '사람' 없음 · 무작위 5 번 모두 동물, 케이블 기술자 = 검은 고양이 초상 · 걷기, 안전모 · 조끼 · 렌치 더블클릭 → 공 21 → 35 · 모습 바뀜(앞 · 옆 · 뒤) · 상대 화면에도 보임, F 로 벗기, 고양이 기사 · 팬더 · 호랑이에도 조끼 · 작은 안전모, 스크립트 오류 없음.

### 2026-10-22 (9) — 판넬 공간확보 메뉴 · 분석·도구 화면 헤더 정리 (APP_VERSION 2026-10-22.3 / SERVER_VERSION 2026-10-22.2)
> server.py 가 바뀜(메뉴 권한 표에 '판넬 공간확보' 한 줄) → **서버 재시작 필요** (8장 3번). 재시작 전에도 화면은 열린다(권한 기본 = 허용).
> 새 파일 `apps\space\index.html` 이 운영 폴더에 생긴다 (패치 APPLY.bat 이 폴더를 만듦). 데이터 폴더는 건드리지 않음.
- 무엇을: 계장 Control Room 판넬 **초기 공간확보 툴**(단일 HTML 프로토타입)을 세 번째 분석 메뉴 '🗄 판넬 공간확보'로 넣음 (P&ID 분석 · LOGIC 분석과 같은 레벨). 왜: 계장이 판넬을 대략 배치해 필요 면적 · 권장 실 크기를 건축에 전달하는 업무.
  - 툴 정리: Google Fonts · claude.ai 전용 다운로드 코드 제거(폐쇄망), 대시보드 색 · 글꼴 토큰, 다크모드 제거, 출력 창이 처음부터 떠 있던 버그(`[hidden]`) 수정.
  - 세 메뉴 맞춤: 흐름 ①②③ 번호 · '<형식> 출력' 버튼 이름 · OK/경고/간섭 pill · 검토 문장에 '→ 어떻게 고치나' · 불러오기 실패 알림.
  - 추가 기능: ① 프로젝트 정보(프로젝트명 · Room 명칭 · 작성자 · Rev → 요약 머리 · DXF 타이틀 · 파일 이름), Panel Type 프리셋 저장/불러오기, Spare 공간 %(+ 증설 방향, 기본 0%), Rev 이력(이전 Rev 대비 면적 변화).
  - 저장: 지금은 브라우저 보관(localStorage `crspace.v1`) + 배치안 JSON 파일. 서버 폴더 저장은 제안만(보고서) — 승인 후 구현.
  - 대시보드: P&ID · LOGIC · 판넬 공간확보 화면에서 위쪽 주간업무 전용 버튼(주차 · 전체 저장 · 금주 마감 · CSV · 엑셀 내보내기 · 인쇄 · 대기열)을 숨기고 부제목을 '<메뉴> · 입력 → 실행 → 결과 → 출력은 아래 화면 안에서' 로. 예전엔 P&ID 화면에서 '엑셀 내보내기'를 누르면 주간업무가 받아졌음.
- 바뀐 곳: dashboard.html 새 `APP_ROUTES` `FRAME_ROUTES` `appUrl` `renderApp`, `render()`(pid-mode · keepPid · 분기) · `ROUTES` · `renderMenu` · `PZ_STATUS` · `renderHeader`(부제목) · CSS `body.pid-mode header.top .actions` / server.py `MENUS` / 새 `apps/space/index.html`.
- 확인한 것: `py_compile`, `node --check`(두 HTML 의 스크립트). 임시 폴더 + 가짜 계정으로 server.py(8780) 와 P&ID 도구(8000, titleblock 브랜치 소스 그대로)를 띄워 Chromium 에서 홈 · P&ID · LOGIC · 판넬 공간확보 캡처, 페이지 · iframe 요청 중 외부 주소 **0건**. 공간확보: 시나리오(기둥 간섭 · 실 밖) 불러오기 → 간섭 2건 문장, 출력 4종 실제 다운로드(.txt · .dxf · .csv(BOM) · .json 이름 그대로), DXF ezdxf audit 오류 0 · Layer 8개 · 글자 스타일 CR-KOR(malgun.ttf), Spare 20% X → 권장 27,700 × 10,600(손 계산 일치), Rev A→B +35.0 m². P&ID · LOGIC 코드는 이 작업에서 0줄 바뀜.
- 회사에서 확인할 것: (1) 서버 재시작 후 ⚙ 메뉴 권한 표에 '판넬 공간확보'. (2) DXF 를 AutoCAD 2026 에서 열어 Layer · 치수 · 한글(CR-KOR = 맑은 고딕) 확인. (3) Edge 개발자도구 Network 탭에서 외부 요청 0건. (4) P&ID 회귀 `python spike/regression_3p.py` 와 LOGIC 샘플 1건 — 코드는 안 바뀌었지만 완료 기준이라 기록을 남김.

### 2026-10-22 (10) — 판넬 공간확보: 어두운 CAD 화면 · 도어 위치/열림 · 회전 궤적 (APP · SERVER 그대로 — apps/space/index.html 만)
> 서버 재시작 · 대시보드 교체 필요 없음. `apps\space\index.html` 만 바꾸고 화면에서 Ctrl+F5.
- 무엇을: 요청 "UI 를 CAD 처럼 어둡게, 도어가 열리는 궤도까지, 판넬 Type 을 만들 때 L-R Open · 전면 · 후면 어디에 도어가 있는지 선택".
  - 기본 화면 = 어두운 CAD(짙은 회색 바탕 · 흰 벽선), 도구줄 [☀ 밝게] 로 예전 밝은 화면 (localStorage `crspace.theme`).
  - Type 카드: Door 위치(없음/전면/후면/전·후면) · 열림(L 힌지/R 힌지/양개 L-R — 그 면 앞에 서서 볼 때 기준). 화면에 열린 문짝 + 점선 호, DXF 새 Layer `CR-DOOR`(LINE + ARC).
  - 검토(경고): 문짝 반경 > 유지보수 공간, 궤적이 벽 · 기둥 · 다른 판넬에 닿음. 궤적이 유지보수 공간 밖이면 필요 영역에 포함.
  - 예전 배치안 · 프리셋 Type 은 '도어 없음' → 예전 숫자 그대로. CSV 에 Door · Hinge 열.
- 바뀐 곳: apps/space/index.html — CSS 테마 토큰(`:root` 어두움 · `[data-theme=light]`), `setTheme`, `DOOR_AT` `HINGE` `fixDoor` `FRONT_N` `edgeOf` `doors`, `check`(도어 경고), `envelope`, `render`(문짝 · 호), `buildTypes`(선택칸), `cleanType`, 요약 · CSV · DXF(`arc`, CR-DOOR).
- 확인한 것: `node --check`. 임시 서버 + Chromium: 도어 시험 배치(L · R · 양개 · 1200 단문 · 후면만 · 벽 옆) → 경고 3건 기대대로, DXF ezdxf audit 오류 0 · ARC 15 = 문짝 수 · 각도 확인, 도어 없는 예전 시나리오 권장 실 23,400 × 10,600 그대로, 외부 요청 0건.
- 회사에서 확인할 것: AutoCAD 에서 CR-DOOR 호의 방향(힌지 쪽)이 화면과 같은지, L/R 기준(앞에서 볼 때)이 부서 관례와 맞는지.

### 2026-10-22 (11) — 판넬 공간확보: DXF Layer 색을 화면과 같은 톤으로 (apps/space/index.html 만)
- 무엇을: 요청 "DXF 출력도 너무 눈부시다. UI 와 같은 색감으로". 원색(빨강 1 · 노랑 2 · 초록 3 · 자홍 6 · 순백 7)을 화면 색에 가장 가까운 ACI 로.
  CR-ROOM 254 · CR-COLUMN 8 · CR-PANEL 253 · CR-PANEL-FRONT 254 · CR-CLEARANCE 43 · CR-ENVELOPE 161 · CR-TEXT 9 · CR-DIM 151 · CR-DOOR 133. Layer 이름 · 도형은 그대로.
- 바뀐 곳: `$('#bDxf').onclick` 의 `layers`.
- 확인한 것: ezdxf audit 오류 0, Layer 색 읽어 확인, 화면 바탕색(#212830)으로 그려 비교.
- 회사에서 확인할 것: AutoCAD 바탕이 흰색이면 회색 선(254 · 9)이 흐릴 수 있음 — 그 경우 CR-ROOM · CR-TEXT 를 7 로 되돌리면 됨.

### 2026-10-22 (12) — 판넬 공간확보: PPT 도형 삽입처럼 Type 만들기 · 저장 · 눌러서 배치 (apps/space/index.html 만)
- 무엇을: 요청 "Panel 을 PPT 주석 넣듯 Type 별로 생성 · 저장하고, 생성된 Type 을 누르면 그 Type 의 panel 을 배치". 개발 의도 = 1단계(계장이 빈 상태에서 판넬을 배치해 필요 볼륨 산출) → 건축 전달 → 건축 Room CAD → 계장이 그 CAD 를 backdrawing 으로 상세 배치.
  - 도구줄 아래 'Panel 삽입' 줄(그림 단추) → 누르면 배치 모드 → 도면 클릭. ✎/두 번 누르기 = 고치기, [＋ 새 Type] = 만들기 창(실시간 미리보기 · 입력 오류 문장).
  - 📚 라이브러리(localStorage `crspace.lib.v1`) — 다른 프로젝트에서 다시 쓰기.
- 바뀐 곳: apps/space/index.html — HTML `.ribbon #palette` · `#tdlg` · `#libdlg`, `buildTypes`(삽입 줄), `typeSvg` `doorSvg`, `geom(p, tt)`, `openTypeDlg` `tdRead` `tdPreview` `tdSave`, `libGet` `libSet` `libPut` `buildLib`, 키 입력(열린 창이면 도면 단축키 끔 · Esc 닫기). 사이드 Type 입력 카드 삭제.
- 확인한 것: `node --check`, Chromium 으로 만들기 → 만들고 배치 → 도면 클릭 2 EA, 다른 Type 단추 배치, 이름 중복 오류, 라이브러리 1건, 스크립트 오류 0.
- 회사에서 확인할 것: 라이브러리는 PC · 브라우저마다 따로 (Edge 사이트 데이터 지우면 사라짐) — 부서 공용은 서버 저장(보고서 5-1) 승인 시.

### 2026-10-22 (13) — 판넬 공간확보: 서버에 프로젝트별 · 날짜별 저장 · 저장 이력 · 프로젝트 노트 / 도면 노트 / 기둥 편집 (APP_VERSION 2026-10-22.4 / SERVER_VERSION 2026-10-22.3)
> server.py 가 바뀜 → **서버 재시작 필요** (8장 3번). 운영 폴더에 `space\` 폴더가 생긴다(일일 백업 zip 에 포함). 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 요청 "프로젝트별 · 날짜별로 작업을 저장, 도면에 또는 별도 노트를 추가, 다른 부서원이 그 history 를 볼 수 있게, 기둥 위치도 사용자가 바꿀 수 있게".
  1. 서버 저장 (server.py 새 API `space/…`, 위 5장 표): 저장은 덮어쓰지 않고 매번 새 파일 → 날짜별 이력(시각 · 저장한 사람 · 메모 · Rev · 판넬 수 · 필요 영역 · 권장 실). 프로젝트 노트(시각 · 사람). 작성자 = 서버가 로그인 토큰으로 정함.
  2. 앱: ① 에 '서버 프로젝트' 상자 [💾 서버에 저장] [🗂 프로젝트 · 이력 · 노트], 🗂 창(프로젝트 · 저장 이력 · 프로젝트 노트 세 칸), 저장본 열기, '서버 저장 이후 바뀜' 표시.
  3. 도면 노트: [📌 노트] → 도면 위 번호 핀 + 말풍선, 목록 · 끌어 옮기기 · 고치기, 배치안에 저장(서버 이력에도), 요약 7절 · DXF CR-NOTE.
  4. 기둥 편집: [기둥 편집] → 기둥 Drag 이동 · 빈 곳 클릭 추가 · Delete 삭제 · X/Y/W/H 입력, [격자로 다시 만들기].
  5. dashboard.html: 연결 앱에 로그인 토큰을 postMessage 로 전달(부서원 file:// 사본은 앱 주소의 저장소를 못 읽음) — 받는 쪽 = 앱 주소로 한정.
- 바뀐 곳: server.py 새 `SPACE_ID_RE` `space_id` `space_idx_path` `space_idx` `space_name` `api_space_projects` `api_space_project_new` `api_space_get` `api_space_save_get` `api_space_save` `api_space_note_add` `api_space_note_del`, `api()` 의 `space` 분기, 백업 · 시작 폴더에 `space` / dashboard.html `renderApp` · 새 `appAuth` · `render()` / apps/space/index.html `sapi` `openHist` `loadProjects` `loadProject` `updSrv`, 노트(`hitNote` `openNote` `saveNote` `buildNotes`), 기둥(`toCustomCols` `hitCol` `delCol`, `columns()` 이 `S.cols` 우선).
- 확인한 것: `py_compile`, `node --check`, 임시 폴더 서버 + 가짜 계정 두 개(홍길동 · 김철수): API 생성 · 중복 409 · 비로그인 401 · 잘못된 배치안 400 · 잘못된 ID 400 · 노트 삭제 · 저장본 읽기. 브라우저: 홍길동 저장 2회 · 노트 → 김철수가 이력 2건 · 노트 1건 보고(남의 노트 지우기 없음) 첫 저장본 열기, file:// 사본에서 postMessage 로 로그인 전달, 도면 노트 · DXF(audit 0), 기둥 이동 · 추가 · 삭제 · 격자로 다시. 스크립트 오류 0.
- 회사에서 확인할 것: (1) 서버 재시작 후 [🗂] 창이 열리는지, 두 사람이 서로의 저장 · 노트를 보는지. (2) 부서원 PC(file:// 사본)에서 [💾 서버에 저장] 이 본인 이름으로 남는지. (3) 메뉴 권한 표에서 '판넬 공간확보' 를 끈 사람은 보기만 되는지.

### 2026-10-22 (14) — 판넬 공간확보: P&ID · LOGIC 과 같은 첫 화면 (APP 그대로 / SERVER_VERSION 2026-10-22.4)
> server.py 가 바뀜(GET `space/recent` 한 개) → **서버 재시작 필요**. (11) 과 함께 적용하면 재시작 한 번.
- 무엇을: 요청 "프로젝트별 저장은 P&ID 분석 · LOGIC 분석 첫 화면 UI 와 같이". 메뉴에 들어오면 첫 화면 — ① 어디에 넣을지(프로젝트 · 새 프로젝트 · Room · Rev) · ② 어떻게 시작할지(최근 저장본 / 하던 작업 / 빈 실 / 예시 / JSON) · [배치 시작] · 저장된 프로젝트 · 최근 저장 이력. 배치 화면 [⌂ 첫 화면] 으로 돌아옴. 첫 화면은 밝게(P&ID · LOGIC 첫 화면과 같은 색 · 모양), 배치 화면은 어두운 CAD.
- 바뀐 곳: server.py 새 `api_space_recent` + `space` 분기 / apps/space/index.html `#home` (CSS `.lh-*` `.pj*` `.jn` `.jm` — LOGIC logic.css 와 같은 이름), `showHome` `showEditor` `hmLoad` `hmRender` `hmLast` `hmOpen`, `#hmGo`, 도구줄 `#bHome`, `HAD_LOCAL`.
- 확인한 것: `py_compile`, `node --check`, Chromium 으로 첫 화면 → 새 프로젝트 → 배치 시작 → 서버 저장 → 첫 화면에 카드 · 최근 이력 → 이력 줄로 열기. 스크립트 오류 0.
- 회사에서 확인할 것: P&ID · LOGIC 첫 화면과 나란히 봤을 때 같은 느낌인지.


### 2026-10-22 (15) — 통합: 계장 광장(판 7 · 8) 과 판넬 공간확보(판 9~14) 를 한 판으로 (APP_VERSION 2026-10-22.4 / SERVER_VERSION 2026-10-22.4 / PLAZA_VERSION 2026-10-22.7)
- 두 갈래가 따로 만든 수정본을 합침. 겹친 파일은 이 문서뿐(광장은 plaza/ 만, 판넬 공간확보는 dashboard.html · server.py · apps/space/ 만 바꿈).
- 위 (9)~(14) 는 판넬 공간확보 쪽에서 (7)~(12) 로 적었던 것을 번호만 뒤로 옮김.
- 회사에서: server.py 가 바뀜 → 서버 재시작. 적용 후 Ctrl+F5 → 왼쪽 메뉴 '🗄 판넬 공간확보' · 홈 '계장 광장' 둘 다 확인.

### 2026-10-22 (15) — 계장 광장: 착용이 몸에 자연스럽게 · 무기마다 휘두르기 효과 (PLAZA_VERSION 2026-10-22.8 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5. (이 번호는 판넬 공간확보 (12)~(14) 다음)
- 무엇을: 요청 "아이템 끼면 자연스럽게 껴져야 하고, 무기 휘두를 때 이펙트가 무기 특성에 맞아야 한다" (사진: 노비 위에 조끼 그림이 통째로 붙고 케이블 드럼이 몸을 가림).
  - 몸(안전 조끼): 그림을 위에 붙이지 않고 **캐릭터 그림의 몸통 점 색을 형광 주황 + 반사띠 두 줄**로 바꿈(외곽선 · 머리 · 다리는 그대로) — 어느 캐릭터(EPC · 고양이 기사 · 마을 · 노비)나, 앞 · 옆 · 뒤 모두.
  - 머리(안전모): EPC 는 자기 안전모 색 = 등급 색(그대로), 안전모가 없는 캐릭터는 머리 폭에 맞춘 크기로 머리 위에.
  - 손(도구): 캐릭터 키의 36% 크기로 줄여 **몸 옆 손 높이**에 (몸통을 가리지 않음, 왼쪽을 보면 왼손).
  - 휘두르기(Space · 1 강타): 목검 대신 **손에 낀 도구를 실제로 휘두르고**, 효과는 도구 성질대로 —
    둔기(렌치 · 단자대 · 글랜드 · 압력계 · 포지셔너) = 무거운 호 + 끝에서 '쾅' 충격 고리 · 불똥 / 찌르기(드라이버) = 앞으로 찌름 + 별빛 /
    채찍(케이블 드럼 · 계장 케이블 · 에어 · 임펄스 튜브) = 케이블이 앞 칸으로 휘감겨 '찰싹'(케이블 색) / 전기(HART · 멀티미터 · 교정기 · 노트북 · DCS 카드) = 내민 도구에서 번개 + 파란 빛 /
    전파(무전기) = 퍼지는 전파 고리 / 분사(교정 펌프) = 물안개 / 종이(점검표) = 종이 휘두르기 + 종잇조각. 희귀 · 전설은 맞는 곳에 등급 빛. 공격 칸이 있는 마을 캐릭터 · 고양이 기사도 도구를 끼면 같은 효과. 도구가 없으면 예전 목검.
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` 만. plaza.js 새 `WPN` `WHIP_COL` `SWING_A` `drawWeaponSwing` `cvCam` `vestTint` `dress` · `drawSwing`(도구 있으면 그쪽) · `drawEquip`(조끼 덧그림 없앰 · 안전모 크기) · `drawHeld`(크기 · 자리) · `drawActorBody`(모든 캐릭터 `dress` · 그림 너비 `_w` · 도구 휘두르기 조건).
- 확인한 것: `node --check` · `py_compile` · `selftest.py` 모두 통과. 브라우저: 운영자(노비) 조끼 · 안전모 · 케이블 드럼 → 몸에 입혀짐 · 드럼은 손 옆 · 왼쪽 걷기 · Space = 케이블 채찍. EPC 캐릭터 렌치 · 드라이버 · 케이블 드럼 · HART · 무전기 · 교정 펌프 · 점검표 하나씩 끼고 Space — 들고 있는 모습과 휘두르는 두 순간 캡처로 효과 7 종 확인, 스크립트 오류 없음.

### 2026-10-22 (16) — 익명게시판 메뉴별 VOC (실명 · 그림 첨부) · 모든 화면 '📷 스크린 → VOC' (APP_VERSION 2026-10-22.5 / SERVER_VERSION 2026-10-22.5)
> server.py 가 바뀜 → **서버 재시작 필요** (8장 3번). 부서원 사본은 새 버전 배너로 교체. 그림은 운영 폴더 `board\img\` 에 저장(게시판 폴더라 일일 백업에 함께).
- 무엇을: 요청 "익명게시판에 각 메뉴별 VOC · VOC 는 실명만 · 왼쪽 = 사진/스크린 미리보기 · 오른쪽 = VOC 적는 칸 · 모든 화면에서 스크린 단추 → 범위 지정 → 바로 VOC · 등록해도 지금 화면 유지(예: P&ID 분석)".
  - 게시판: 'VOC' 동그라미를 누르면 메뉴 탭(전체 · 주간업무보고 · P&ID 분석 · LOGIC 분석 · 판넬 공간확보 · 입찰/실행 프로젝트 · 익명게시판 · Management · 계장 광장 · 기타 + 글 수) · [📣 VOC 쓰기] · [📷 화면 캡처로 VOC]. VOC 글 카드에 '📍 메뉴' · 첫 그림 크게 + 나머지 작게(누르면 원본 새 창).
  - VOC 창: 왼쪽 = 그림 미리보기(끌어다 놓기 · **Ctrl+V 붙여넣기** · 파일 고르기 · [📷 화면 캡처 추가], 최대 6 장, 큰 그림은 JPEG 로 줄임), 오른쪽 = 메뉴(지금 보던 화면이 기본) · 제목 · 내용 · '작성자 ✔ 본명'. 예전 글쓰기 창에서 VOC 를 고르면 이 창으로. VOC 글 수정도 이 창.
  - **실명만**: 서버가 VOC 글은 익명 · 닉네임을 보내도 로그인 본명으로 기록(비회원 401).
  - **📷 스크린 → VOC** 단추: 위쪽 제목 옆(P&ID · LOGIC · 판넬 공간확보 화면에서도 보임). 누르면 브라우저 화면 공유('이 탭' 허용) → 멈춘 화면 위에서 끌어 범위 지정(Enter = 전체 · Esc = 취소) → 그 자리에 VOC 창(메뉴 = 지금 화면) → 등록 → 안내 한 줄, **화면 전환 없음**(P&ID 분석 iframe 그대로).
  - 브라우저 제한: 화면 캡처(getDisplayMedia)는 보안 연결에서만 됨 — 서버 PC(localhost) · 부서원 file:// 사본은 됨, `http://PC이름:8080` 으로 연 화면은 막힘 → 'Win+Shift+S 로 캡처 후 VOC 창에 Ctrl+V' 안내 후 VOC 창을 엶.
- 바뀐 곳: server.py `SERVER_VERSION` · 새 `VOC_MENUS` `IMG_ID_RE` `IMG_MAX` `IMG_TYPES` `VOC_IMG_MAX` `img_ext`(PNG/JPG/GIF/WEBP 머리 바이트 확인) `img_path` `api_board_img_put` `board_voc` · `api_board_create` `api_board_update`(뺀 그림 지움) `api_board_delete`(그림도 지움) · `board` 분기(GET `board/img/{id}` 누구나 · PUT `board/img` 로그인 + 게시판 권한). dashboard.html `APP_VERSION` · `Board.create/update`(menu · images) · `BS.vmenu` · `renderBoard`(#bvoc) · `drawBoard`(메뉴 탭 · 필터 · 그림) · `boardAction`(VOC 수정) · `openPost`(VOC → 창 바꿈) · 새 `VOC_MENU` `imgUrl` `vocImgsHtml` `vocMenuOf` `blobToJpeg` `openVoc` `captureRegion` `pickRegion` `shotToVoc` · `#btnShot` · CSS `.vtabs` `.vimgs` `.vocdlg` `.shotov` `.shotbtn`.
- 확인한 것: `py_compile` · JS 문법. 임시 서버 + 가짜 계정 브라우저(Chromium, 탭 캡처 자동 허용): P&ID 분석 화면에서 📷 → 범위 600×450 → VOC 창(메뉴 = P&ID 분석 · 그림 1) → 파일 하나 더(2 장) → 등록 → 창 닫힘 · 주소 #pid 그대로 · P&ID 화면 그대로, 게시판 VOC › P&ID 분석 탭에 글 1 · 그림 2 장 표시(실제 크기로 읽힘), 일반 글쓰기에서 VOC 고르면 VOC 창, 서버에 익명으로 보내도 본명 · 없는 그림 ID 는 버림, 보안 연결이 아닌 주소에서 안내 → VOC 창. 스크립트 오류 없음.
- 회사에서 확인할 것: (1) 서버 재시작 후 부서원 PC(file:// 사본)에서 📷 → Edge 가 '이 탭 공유'를 물으면 허용. (2) `http://PC이름:8080` 으로 여는 사람은 Win+Shift+S → Ctrl+V. (3) 그림이 큰 VOC 가 많으면 `board\img` 용량 확인(그림 하나 최대 8MB, 보통 0.2~1MB).

### 2026-10-22 (17) — 계장 광장: 접속 경험치 (하루 첫 접속 · 연속 접속일 · 접속 유지) · 레벨 업 때 체력 · 마나 가득 (PLAZA_VERSION 2026-10-22.9 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 요청 "접속 횟수 · 접속 유지가 많고 오래될수록 경험치를 주고, 레벨이 오를 때마다 체력 · 마나를 적절히 올려라".
  - **하루 첫 접속 +10 XP**, **연속 접속일 보너스** 이틀째부터 하루마다 +4 (7일 연속부터 최대 +28/일). 같은 날 다시 들어와도 한 번만.
  - **접속 유지**: 광장에 연결되어 있으면(대시보드 어느 메뉴에 있든 광장 접속은 유지됨) 5분마다 +2, 오늘 1시간 넘게 머물면 5분마다 +3. 켜 두기만 해서 끝없이 오르지 않게 **하루 60 XP 까지**.
    → 하루 최대 약 10 + 28 + 60 = 98 XP. 예) 매일 30분 접속 · 일주일 연속이면 Lv 1 → 약 Lv 5. 설비 작업 경험치(5 · 10 · 20, 직무 1.5배)는 그대로.
  - **레벨 업**(어떤 경험치로든): 최대 체력 +10 · 마나 +5 (예전 규칙 그대로, Lv 30 까지) + **체력 · 마나 가득 참**(유령은 그대로) + 대화창 '🎉 Lv n 달성! 최대 체력 … (+10) · 마나 … (+5) — 가득 찼습니다' + 머리 위 '레벨 업!' · 금빛 불꽃.
  - 화면: 받으면 머리 위 '+2 XP · 접속 유지 25분' 등. 상태판에 '🕒 오늘 n분 · 🔥 연속 n일 · 접속 XP n/60 · 총 n일'. 머리 위 글이 여럿이면 줄을 바꿔 차례로(겹쳐 읽히던 것 고침).
  - 값은 plaza_server.py `VISIT_XP` `STREAK_XP` `STREAK_CAP` `STAY_EVERY` `STAY_XP` `STAY_LONG` `STAY_CAP` 에서 바꿈. 기록 `data/plaza/xp.json` 의 `pres`(오늘 머문 초 · 받은 접속 XP) · `streak`(연속일 · 총 접속일).
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` · 새 `VISIT_XP` … `STAY_CAP` `today_str` `pres_of` `add_xp`(레벨 업 · 가득 · 알림) `visit_xp` `stay_tick`(10초마다) · `api_work`(add_xp 로) · `api_join`(두 갈래 모두 visit_xp) · `hp_loop` · `eq_init`(읽기) · `save_xp` · snapshot(xp_seq · xp_gain · xp_why · xp_age · lvup_age · pres). plaza.js `epcFields`(접속 XP · 레벨 업 표시) · `updateHud`(#hud-pres) · `floater`(줄 바꿔 차례로) · `drawFloats`. plaza.html `#hud-pres`. plaza.css `.pres`. selftest.py 접속 경험치 · 같은 날 한 번 · 5분 +2 · 하루 상한 · 연속 이틀째 · 레벨 업 가득(작업 경험치 기대값에 첫 접속 +10 반영).
- 확인한 것: `py_compile` · `node --check` · `selftest.py` 모두 통과. 브라우저: XP 95 · 체력 40 인 캐릭터가 들어오자 +10 → Lv 3 · 체력 120/120 · 마나 60/60 · 대화창 알림, 615 → Lv 6 (150 · 75), 머리 위 '+10 XP · 오늘 첫 접속' · '레벨 업!' · '최대 체력 · 마나 증가 · 가득 참' 이 세 줄로 차례로, 상태판 접속 줄, 스크립트 오류 없음.

### 2026-10-22 (18) — 계장 광장: 레벨 무기 빛 · NPC 한마디 · 박병두 프로님 동상 · 복지 구역(식당 · 헬스장 실내) · 지도 확장 (PLAZA_VERSION 2026-10-22.10 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 (대시보드 서버가 30초 안에 새 판 광장으로 바꿈) → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 요청 "레벨 오를수록 무기 빛 · 임팩트 화려하게 / NPC 를 때리면 '이름 프로님 그만좀 때리세요!!' / NPC 를 마우스로 누르면 '아!! 프로님 왜 불러요!! 바쁜데' / 광장에 '박병두 프로님' 동상 — 때리면 움직여 때린 사람을 따라다니며 10번 때리고 제자리로 와서 다시 동상 / 광장을 더 크게 · 식당 · 헬스장 · 들어가면 배경이 바뀌게".
  - **레벨 빛**: 휘두를 때 무기 빛 · 빛 꼬리 · 맞는 곳 고리(1~4겹) · 빛살 · 섬광 · 불꽃이 레벨에 따라 커짐. 색 단계 1~4 없음 · 5~9 초록 · 10~14 파랑 · 15~19 보라 · 20~29 주황 · 30 무지개. Lv 5 부터 손에 든 도구 둘레도 맥동하는 빛(15 부터 반짝이).
  - **NPC 한마디**(모두에게 보임): Space 로 앞 칸 NPC 를 치면 NPC 가 붉게 번쩍 + '박부서 프로님 그만좀 때리세요!!', 마우스로 누르면 '아!! 프로님 왜 불러요!! 바쁜데'. 연타는 0.4초에 한 번. NPC 체력 · 경험치는 없음(놀이).
  - **박병두 프로님 동상**: 복지 광장 가운데 받침대(칸 78,31 · 명판 '박병두 프로님'). Space(또는 1 강타)로 치면 흔들리며 깨어나 → 때린 사람이 **걸은 칸을 그대로 밟아** 따라가(벽을 뚫지 않음, 문으로 들어가면 같이 들어감) 곁에서 0.8초마다 한 대씩 **10대**(한 대 체력 −3, 운영자는 무적이라 시늉만) → 걸어온 길을 되짚어 받침대로 돌아와 다시 돌빛 동상. 쓰러지거나 나가거나 2분이 지나면 바로 돌아감. 대화창에 깨어남 · 10대 알림, 머리 위 '1대!' … '10대! 이제 됐다.'
  - **지도 확장** 64×44 → 96×60: 동쪽에 '복지 구역'(식당 · 헬스장 건물 · 보도블록 광장 · 꽃밭 · 벤치 · 가로등 · 나무 · 자판기), 큰길을 동쪽 끝까지. 아래 44~59 줄은 **실내**(바깥과 안 이어짐).
  - **실내 · 배경 바뀜**: 건물 문 칸(식당 71,11 · 헬스장 86,11)으로 걸어 들어가면 화면이 잠깐 어두워졌다 밝아지며 방 안으로 — 카메라는 그 방만, 밖은 어둡게, 바닥 · 벽 · 소품이 실내로. 식당 = 마루 · 크림 벽지 · 배식대(김 나는 반찬통) · 메뉴판 · 식탁 12 · 식판 반납 · 정수기. 헬스장 = 고무 바닥 · 거울 벽 · 러닝머신 4(벨트 움직임) · 덤벨 · 벤치프레스 · 스쿼트랙 · 샌드백 · 매트. 방 아래 빨간 깔개 칸으로 나오면 건물 앞. 현장 지도는 바깥만(실내면 건물 자리에 내 점), 동상 점(돌빛 · 깨면 빨강).
- 바뀐 곳: plaza_server.py `PLAZA_VERSION` · `MAP_W/MAP_H` 96·60 · 새 `STATUE_*` `STATUE` `statue_say` `statue_wake` `statue_front` `statue_trail` `statue_step` `statue_home` `statue_tick` `statue_loop`(0.07초 스레드) `statue_snap` `NPC_LINES` `NPC_SAY` `api_npc`(POST /plaza/api/npc {id, npc, kind: hit|click}) · `api_attack`·`api_skill`(강타)에서 동상 깨움 · `api_move`(쫓기는 사람 칸 적기) · snapshot(statue · npc_say) · `main`. plaza.js `W/H` · 새 `H_OUT` 땅 종류 `WOOD RUBBER VOID WALLI PAVE` · `ROOMS` `DOORS` `roomAt` `goDoor` `STATUE_HOME` · 새 그림 `foodHallImg` `gymImg` `awning` `pedestalImg` `flowerBedImg` `counterImg` `menuBoardImg` `tableImg` `chairsImg` `waterImg` `trayRackImg` `treadmillImg` `dumbbellImg` `benchPressImg` `squatRackImg` `punchBagImg` `matImg` `bannerImg` · `drawGround`(정수 해시 `ih` 로 빠르게 · 마루 · 고무 · 보도블록 · 실내 벽 · 동상 둘레 무늬) · `frame`(방 카메라 · 잘라 그리기 · 문 안내 · 방 이름 · 어둡게 전환) · `drawMini` · 새 `lvFx` `lvRgb` · `drawWeaponSwing` `drawSwing` `drawHeld` · NPC `npcOn` `npcAtPx` · 동상 `statueActor` `stoneTint` `statueLift` · `applySnapshot` · `attack` · 캔버스 클릭 · `nameTag` `jobTag` `occupied` · `KEY_ROWS`. plaza.html/css 현장 지도 192×88. selftest.py NPC 말 2 · 동상 2.
- 확인한 것: `py_compile` · `node --check` · `selftest.py` 모두 통과. 브라우저(임시 서버): 동상 앞에서 Space → 흔들리며 깨어남 → 오른쪽으로 달아나자 같은 칸을 밟아 따라와 10대(체력 −30) → 제자리 돌빛 동상. 식당 문 → 방 안(배경 · 카메라 바뀜) → 빨간 깔개 → 건물 앞, 헬스장도 같음. NPC 치기 · 누르기 말풍선. Lv 1 · 10 · 20 · 30 휘두르기 캡처 비교. 스크립트 오류 없음.
- 회사에서 확인할 것: 두 사람이 함께 들어가 동상 쫓기 · 식당 안에서 서로 보이는지. 예전에 칸 62~63(옛 동쪽 끝)에 떨어뜨린 아이템은 그 자리 그대로.

### 2026-10-22 (19) — 계장 광장: 배경 품질 — 해질녘 · 밤 조명 · 땅 · 나무 다듬기 (PLAZA_VERSION 2026-10-22.11 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 요청 "첨부한 epc_plant_game_starter.zip 같은 퀄리티로 배경 개선". 첨부의 참고 그림(EPC 발전플랜트 야경 — 남색 · 철골 회색 · 따뜻한 작업등 · 상태 LED · 풍성한 나무)은 **보기만** 하고(그림 · 로고는 넣지 않음), 지금 지도 · 설비 · 충돌 · 캐릭터는 그대로 두고 그리는 방식만 바꿈.
  - **해질녘 · 밤 조명**(기본): 화면 전체를 남색으로 낮추고, 가로등 아래 노란 빛 웅덩이(살짝 일렁임) · 켜진 창(건물 · 현장 사무소 · 경비실 · 식당은 따뜻한 색 · 헬스장은 흰 파랑) · 제어실 화면 · 자판기 · 가로등 머리가 스스로 빛남. 설비는 상태 색 빛(정상 초록 · 경고 주황 · 고장 빨강 깜빡), 사람 · NPC 둘레는 은은한 빛(얼굴이 보이게), 휘두르면 무기 빛이 땅을 비춤(레벨이 높을수록 크게), 유닛장 회복 오라는 초록 빛. 화면 가장자리는 조금 더 어둡게. 실내는 천장 등(식당 따뜻 · 헬스장 차가움).
  - **🌙 밤 / ☀ 낮** 단추(오른쪽 아래 '얼굴 바꾸기' 옆): 예전 낮 화면으로 돌아감 · 이 PC 브라우저에 기억.
  - **땅**: 차도 연석(밝은 돌 줄 + 차도 쪽 그늘) · 잔디 가장자리 그늘 · 잔디 결 · 아스팔트 균열 · 바퀴 자국 · 막힌 칸(설비 · 건물 밑동) 아래 · 오른쪽 접지 그림자.
  - **나무 · 덤불**: 잎 3~4 톤(아래 그늘 → 왼쪽 위 빛 · 잎 끝 점) · 밑동 그림자 · 덤불 꽃.
  - 이름표 · 말풍선 · 설비 표시 · 효과는 조명 뒤에 그려 늘 또렷함. 빛 지도는 반 해상도로 그려 느려지지 않게(시험 PC 50 fps 안팎).
  - 참고: 스타터가 권한 '1.5~1.8배 확대'는 하지 않음 — 지금 캐릭터 키가 화면 높이의 약 8% 로 스타터 기준(7~12%) 안이라서.
- 바뀐 곳: plaza.js 새 `lit` `WARM` `COOL` `SCREEN` `NIGHT` `nightBtn` `toggleNight` `AMB_*` `drawNight` · `building`(창 · 간판 빛, `glowCol`) · `lightPoleImg` `vendingImg`(→`vendingImg0`) `crWallN`(→`crWallN0`) · 현장 사무소 · 경비실 put · `treeImg` `shrubImg` · `drawGround`(연석 · 그늘 · 잔디 결 · 균열 · 바퀴 자국) · `frame`(drawNight). plaza.html `#pz-night`. plaza_server.py `PLAZA_VERSION` 만.
- 확인한 것: `node --check` · `py_compile` · `selftest.py` 모두 통과. 브라우저: 큰길 네거리 · 터빈 홀 앞 · 공정 구역 · 복지 구역(식당 · 헬스장 앞) · 동상 광장 · 식당 · 헬스장 안을 밤 · 낮으로 캡처, 스크립트 오류 없음, 약 50 fps.
- 회사에서 확인할 것: 회사 PC 에서 너무 어둡거나 느리면 ☀ 낮 단추. 어둡기는 plaza.js `AMB_OUT`(바깥 남색, 숫자가 클수록 밝음)에서 바꿈.

### 2026-10-22 (20) — 계장 광장: 공격 = 무기를 손에 쥐고 휘두르는 동작 (PLAZA_VERSION 2026-10-22.12 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 요청 "공격 모션을 무기로 공격하는 자연스러운 동작으로". 예전엔 무기 그림이 손에서 떨어져 몸 둘레를 돌았고, 몸은 거의 안 움직였고, 시트의 '수리' 칸(손에 렌치가 그려져 있음)을 써서 도구가 둘로 보였음.
  - 한 번 휘두르기 = **준비**(몸을 뒤로 젖히며 무기를 머리 뒤로 들어 올림, 내려치기는 살짝 솟음) → **휘두름**(점점 빠르게 · 무기 뒤로 옅어지는 잔상) → **맞힘**(멈칫 · 무기 끝에서 충격) → **돌아옴**(허리 옆 쉬는 자리). 0.28 → 0.32초.
  - **손잡이가 늘 손에** 붙어 있고 손은 몸과 함께 움직임(쉴 때 허리 · 들어 올리면 어깨). 머리 뒤로 들어 올린 동안 · 뒷모습일 때는 무기를 몸 뒤에 그림.
  - 도구마다 쥐는 법: 렌치 · 단자대 · 글랜드 · 압력계 · 포지셔너 = 내려치기 / 드라이버 = 당겼다 찌르기 / 점검표 = 옆으로 후려치기 / 목검(맨손) = 베기 / 케이블 드럼 · 케이블 · 튜브 = 들고 케이블을 앞으로 '찰싹' / HART · 멀티미터 · 교정기 · 노트북 · DCS 카드 · 무전기 · 교정 펌프 = 세워 든 채 앞으로 내밀어 끝에서 번개 · 전파 · 물안개(반동).
  - EPC 시트 도구 아이콘은 비스듬하고 옆 아이콘이 섞여 있어, 무기마다 깨끗한 자리 · 손잡이 점 · 머리 점을 따로 적음(`WGRIP`).
  - 몸 그림은 서 있는 칸 그대로(걷기 칸은 크기가 작아 몸이 줄었다 커져 보였음) — 움직임은 젖힘 · 내딛음 + 손의 무기.
  - 레벨 빛(판10)은 무기 끝을 따라감.
- 바뀐 곳: plaza.js `ATK_MS` 320 · 새 `ATK_ARC` `easeO/easeI/easeIO` `atkCurve` `atkKind` `atkLean` `scrAng` `handOf` `WGRIP` `WSC` `weaponIcon` `weaponLen` `weaponTip` `uprightTilt` `drawWeaponAt` `drawAttack` · `drawSwing`(몸 뒤 · 앞 두 번) · `drawActorBody`(젖힘 · 내딛음, 네 갈래 모두 drawSwing 두 번) · `epcPose`(공격 중 서 있는 칸). 옛 `drawWeaponSwing` 없앰. plaza_server.py `PLAZA_VERSION` 만.
- 확인한 것: `node --check` · `selftest.py` 모두 통과. 브라우저에서 시각을 멈춰 렌치 · 드라이버 · 케이블 드럼 · HART · 무전기 · 점검표 · 목검 × 4 방향 × 8 순간 캡처로 동작 확인, Space 꾹 누르기(실제 시간) 연속 휘두르기, 스크립트 오류 없음.

### 2026-10-22 (21) — 계장 광장: 그래픽 해상도 2배 · 4배 (PLAZA_VERSION 2026-10-22.13 / APP · SERVER 그대로)
> 서버 재시작 필요 없음 → 적용 후 30초 뒤 Ctrl+F5.
- 무엇을: 요청 "계장 광장 그래픽의 해상도를 높여줘". 그림은 점(dot) 하나 = 2px 의 픽셀 그림이라 한 점이 2×2 네모로 커져 계단 모서리가 보였음.
  - **2배 (Scale2x / EPX)**: 점 그림을 키울 때 이웃 점을 보고 모서리 · 비스듬한 선 · 둥근 곳을 한 단계 잘게 다듬음. 건물 · 설비 · 소품(점 그림 pix) · 캐릭터 · 아이콘(시트) · 무기 · 땅 모두. 땅은 그 위에 1px 결(자갈 · 콘크리트 · 아스팔트 · 잔디)을 더함.
  - **4배 (.hd)**: 그림마다 한 번 더 키운 그림(점 하나 = 4px)을 만들어 두고 화면에 그릴 때 그것을 같은 크기로 부드럽게 줄여 그림 → 보통 화면(100%)은 계단 대신 매끈한 테두리, 윈도우 배율 125% 이상 · 노트북 화면은 화면 실제 화소만큼 잘게. 글씨(간판 · 명판)는 4배 그림에 큰 글씨로 따로 써서 또렷함. 색 입힌 그림(맞을 때 붉게 · 유령 · 안전모/조끼 색 · 동상 돌빛)도 4배를 따라 만듦.
  - 땅 그림의 4배는 너무 커서(6144×3840) 만들지 않음.
  - 주소에 `hd=0` 을 붙이면 예전처럼(2배만). 느린 PC 대비.
- 바뀐 곳: plaza.js 새 `EPX_TOL` `epx` `HD` `hdOf` · `pix`(EPX · .hd · 글씨 두 번) · `awning`(.hd 에도) · `atlasSprite`(scale 2 = EPX + .hd) · `drawGround`(EPX + 1px 결) · `weaponIcon`(2배 · HD 4배, `k`) · `drawWeaponAt` · `tinted` `ghostly` `helmTint` `vestTint` `stoneTint`(.hd 따라 만듦) · 화면 캔버스 `ctx.drawImage`(.hd 가 있으면 그것을 같은 크기로 부드럽게). plaza_server.py `PLAZA_VERSION` 만.
- 확인한 것: `node --check` · `selftest.py` 통과. 브라우저(배율 100% · 150%)로 같은 자리 전후 캡처 비교 — 동상 둘레 고리 · 보도블록 · 간판 · 문 모서리가 매끈, 스크립트 오류 없음. 시험 PC(그래픽 카드 없음) 속도: 100% 48 → 40 fps, 150% 25 → 23.5 fps. 처음 그리기 1.1 → 1.3초.
- 회사에서 확인할 것: 회사 PC 에서 느리면 `hd=0`(대시보드 광장 카드 주소 끝에 `&hd=0`) — 다음 판에서 단추로 뺄 수 있음.

### 2026-10-23 (22) — VOC 처리 완료 (운영자) · 완료 표기 (APP_VERSION 2026-10-23.1 / SERVER_VERSION 2026-10-23.1)
> server.py 가 바뀜 → **서버 재시작 필요** (8장 3번). 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 요청 "VOC 는 운영자가 처리 완료를 누를 수 있도록 하고, 처리가 완료되면 완료된 표기".
  - 운영자 = 서버 PC 또는 그룹장(`SUPER_NAMES`, 지금은 구종현) — 게시판 관리 삭제와 같은 사람. VOC 글 카드에 **[✅ 처리 완료]** 단추 → 창에서 처리 내용 한 줄(선택) → 모두에게 **'✅ 처리 완료 · 처리한 사람 · 언제'** + 💬 처리 내용, 제목 앞 ✅, 카드가 조금 옅어짐. 실수하면 **[완료 취소]**.
  - 처리 전 VOC 는 **'⏳ 처리 대기'**. VOC 탭 줄에 '✅ 완료 n · ⏳ 미처리 n' 과 **[미처리만]** 체크(완료 글 숨김).
  - 부서원 화면엔 단추가 없고, 서버도 운영자가 아니면 거절(403). 글쓴이가 글을 고쳐도 완료 표시는 그대로, VOC 가 아닌 유형으로 바꾸면 지움.
  - 기록: 글 파일 `board/<id>.json` 의 `done: {by, at, note}`. 폴더 직접 연결(file://, 서버 없이) 모드에서는 보기만(단추 없음).
- 바뀐 곳: server.py `SERVER_VERSION` · 새 `api_board_done` · `board_voc`(VOC 아니면 done 지움) · `board` 분기(POST `board/{id}/done` {done, note} — `need_super`). dashboard.html `APP_VERSION` · `Board.done` · `renderBoard`(미처리만) · `drawBoard`(상태 · 단추 · 탭 줄 수) · `boardAction`(vdone · vundo) · CSS `.vdone` `.vwait` `.vnote` `.vstat` `.vopen` `.btn.ok` `.igpost.vocdone`.
- 확인한 것: `py_compile` · JS 문법. 임시 서버 + 가짜 계정 브라우저(다른 PC 주소로 접속): 부서원 = '처리 대기'만 · 단추 없음 · API 403, 그룹장 = 단추 → 처리 내용 입력 → '✅ 처리 완료 · 구종현 · 방금' + 처리 내용, 부서원 새로고침하면 완료 보임, [미처리만] 체크하면 완료 글 빠짐, [완료 취소] → 다시 '처리 대기'. 스크립트 오류 없음.
- 회사에서 확인할 것: 서버 재시작 후 그룹장 계정(구종현) 또는 서버 PC 에서 VOC 하나 처리 완료 → 부서원 PC 에서 보이는지.

### 2026-10-23 (23) — 전체 점검: 내 업무 툴바 도킹 · 작성 가이드 접기 · 마감 D-day · 🔍 빠른 찾기(Ctrl+K) · 광장 카드 오류 (APP_VERSION 2026-10-23.2 / SERVER 그대로 / PLAZA_VERSION 2026-10-23.1)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체 · 광장은 30초 안에 새 판으로 바뀜.
- 무엇을: 요청 "전체적으로 대시보드를 검토하고 개선 · 보완 · 기능 추가, UI 편집은 시뮬레이션을 돌려가며". 임시 서버에 부서원·그룹장·운영자로 접속해 22개 메뉴 × 3가지 화면(1500·1180·그룹장) + 창 28개(행 편집 · 이력 · 행/열 추가 · 휴지통 · 대기열 · 내 정보 · 비밀번호 · 내 업무 · 쪽지 · 글쓰기 · VOC · 메뉴 권한 · 금주 마감 · 전체 저장 · 마감본 · 인쇄 · 메뉴 숨김)을 캡처하고 콘솔 오류 · 가로 넘침 · 글자 잘림을 자동으로 검사. 스크립트 오류 1건(광장) 외 깨짐 없음. 고친 것·더한 것:
  1. **내 업무 툴바 도킹**: 펼쳐 둔 툴바가 본문 위에 떠서 `+ 행 추가` · 편집/이력/삭제 단추 · 오른쪽 KPI 카드를 가렸음(시험 스크립트도 `+ 행 추가`를 못 눌렀음). 이제 펼쳐 두면 본문 오른쪽을 270px 비워 **나란히** 놓임. 접거나(–) 끌어서 옮기면 비우지 않음(⠿ 두 번 누르면 원래 자리 + 다시 도킹). **1300px 미만 화면은 처음에 접힌 탭**으로 시작(사용자가 펼쳐 둔 기억이 있으면 그대로). 인쇄 때 여백 없음.
  2. **작성 가이드 접기**: 행 추가·편집 창의 '✍ 작성 가이드' 상자에 [접기]/[펼치기] — 접으면 한 줄만, 이 PC 에 기억(`dept-guide-fold`).
  3. **⏰ 마감까지 n일 n시간**: 홈 배지 줄에 이번 주 마감(수요일 11:59)까지 남은 시간. 24시간 안이면 붉게. 마감본을 보는 중엔 없음.
  4. **🔍 빠른 찾기 (Ctrl+K · 머리의 [🔍 찾기])**: 메뉴 이름 · 모든 시트의 행(제목·내용·담당자 등 모든 칸) · 게시글을 한 번에 검색 → ↑↓ Enter 또는 클릭으로 그 행(칸)으로 이동(노란 표시, 기존 `jumpTo`), 메뉴면 그 메뉴로, 게시글이면 게시판 검색어로. 시트당 8건 · 전체 40건 · 찾은 글자 노란 표시. 권한 있는 메뉴만.
  5. **계장 광장 카드 오류**: 홈 카드가 치워져 크기 0 일 때 `drawImage` 오류(InvalidStateError) → 캔버스가 2px 미만이면 그리지 않음.
- 바뀐 곳: dashboard.html `APP_VERSION` · CSS `body.tb-dock #main` `.gbox .gfold` `.gbox.fold` `.badge.dday` `.findbtn` `.qf …` · `renderTaskBar`(min 기본값 · tb-dock) `tbDragInit`(옮기면 해제 · resize 때 다시) · 새 `LS_GFOLD` `guideFolded` `guideBox`(GUIDE_BOX 사용처) · 새 `ddayChip`(홈 배지) · 새 `QF_MENUS` `qfSearch` `openFind` + Ctrl+K · 머리 `#btnFind`. plaza.js `frame`(크기 0 보호) · plaza_server.py `PLAZA_VERSION`.
- 확인한 것: JS 문법 · `py_compile` · 광장 selftest 통과. 브라우저: 홈·일반업무·판넬 공간확보에서 padding 270 · 접으면 0 · 펼치면 270 · 끌면 0 · ⠿ 두 번 = 270, 인쇄 0, 1180 화면은 접힌 채 시작, 예전에 펼침을 저장했으면 펼침. 행 추가 창 가이드 접기 → 다시 열면 접힌 채. Ctrl+K '노랑' → 수행 1건 → Enter → #perform 으로 이동 · 셀 표시, '게시판' → 메뉴 이동, 없는 글 → '찾은 것이 없습니다'. 홈에 30초 머물며 광장 카드 오류 없음(전엔 1건).
- 회사에서 확인할 것: 회사 모니터 크기에서 툴바가 나란히 놓이는지(1300 미만이면 접힌 탭). 불편하면 툴바를 끌어 옮기거나 접으면 예전처럼 됨.

### 2026-10-23 (24) — VOC 스크린 캡처: 작업 중 어디서든 · 빠르게 · 하던 일 그대로 (APP_VERSION 2026-10-23.3 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 요청 "P&ID · LOGIC · 주간업무보고 · 판넬 어디서 무슨 작업을 하든 스크린샷 범위 지정 → 바로 내용 작성 → 그 메뉴 VOC 에 자동 저장. 작업 화면에서 이동하면 안 되고, 등록 뒤 하던 작업을 문제없이 이어서. 가볍고, 스크린샷이 오래 걸리면 안 됨".
- 고치기 전 측정(시험 브라우저): 캡처마다 1.4초 + 실제 브라우저는 매번 '탭 공유' 허락 창. 그리고 **버그 2개**: ① 행 편집 창이 열린 채 📷 를 누르면 범위 고르기 화면이 편집 창 **밑에** 깔림, ② VOC 창이 편집 창과 같은 창(`dlg`)을 써서 **쓰던 편집 내용이 사라짐**.
- 바꾼 것:
  1. **빠른 캡처**: '이 탭 공유'를 한 번 허락하면 5분 동안 연결을 살려 둠 → 두 번째부터는 묻지 않고 **0.1~0.2초** 안에 범위 고르기 화면. 마지막 캡처 후 5분 지나면 · 브라우저의 '공유 중지' · 범위 화면의 [끄기] 로 끊김. 📷 단추 옆 **초록 점** = 켜짐. (켜져 있는 동안 브라우저 위쪽에 '이 탭 공유 중' 표시가 보이는 것은 브라우저 규칙)
  2. **범위 고르기 = 최상위 창**(`#shotdlg`): 편집 창 · 다른 창이 열려 있어도 맨 위에 뜸. Esc = 취소(아무 일 없던 것처럼, 포커스도 원래 칸).
  3. **VOC 쓰기 = 전용 창**(`#vocdlg`): 열려 있던 편집 창 · 쓰던 글 · 스크롤 · 메뉴 · iframe(P&ID · LOGIC · 판넬) 상태를 건드리지 않음. 등록하면 창만 닫히고 **포커스가 쓰던 칸으로 돌아감** → 바로 이어서 작업. 메뉴는 지금 화면으로 자동(주간업무보고 하위 · R&R · 통합 업무 = 주간업무보고, Management 하위 = Management).
  4. **F8 = 어디서든 스크린 → VOC** (편집 창이 열려 있어도). Edge 는 Ctrl+Shift+S 를 자기 '웹 캡처'로 써서 F8 로 정함. VOC 창에서 **Ctrl+Enter = 등록**. (P&ID · LOGIC 화면 안을 클릭한 상태면 키가 그 화면으로 가므로 📷 단추를 누름)
  5. **가볍게**: 큰 범위는 WebP(0.92), 작은 범위는 PNG(글자 또렷). 그림 여러 장은 한꺼번에 올림. 등록 뒤 게시판 새로고침은 기다리지 않음(등록 → 닫힘 0.1초 안팎).
  6. **임시 저장**: 글을 쓰다 등록 안 하고 닫으면 이 창(탭)에서 기억 → 다음 📷/VOC 쓰기 때 '✏ 지난번에 닫은 VOC 를 이어 씁니다' + [새로 쓰기]. 그림만 찍고 닫은 것은 버림.
  7. **보안 연결이 아닌 주소**(`http://PC이름:8080` — 브라우저가 캡처 자체를 막음): F8/📷 = 바로 VOC 창(메뉴 자동) + 그림 칸에 포커스 + 안내 'Win+Shift+S 로 캡처 → Ctrl+V'. (전엔 안내 창을 한 번 더 닫아야 했음.) 서버 PC(localhost) · 부서원 사본(file://)은 1~6 그대로 됨.
- 바뀐 곳: dashboard.html `APP_VERSION` · 새 창 `#vocdlg` `#shotdlg` · CSS `dialog.shotov` `.shotbar .qon` `.shotbtn.warm` `.vdraft` · `openVoc`(전용 창 · back 포커스 · VDRAFT · Ctrl+Enter · 병렬 업로드 · 기다리지 않는 새로고침) · 새 `SHOT_KEEP_MS` `SHOT` `shotStop` `shotArm` `shotStream` `shotFrame` · `captureRegion` · `pickRegion`(최상위 창 · WebP/PNG · [끄기]) · `shotToVoc`(보안 아님 → 바로 VOC · 취소 = 포커스 복귀) · F8 단축키 · #btnShot 설명.
- 확인한 것: JS 문법. 임시 서버(127.0.0.1, 탭 캡처 자동 허락) 시뮬레이션 26 항목 모두 통과 — 수행 표를 내리고 행 편집 창에 글을 쓰는 중 F8 → 범위 화면이 편집 창 위 → 끌어 고름 → VOC(메뉴 주간업무보고 자동) → Ctrl+Enter → 편집 창 · 쓰던 글 · 스크롤 · #perform 그대로, 포커스 쓰던 칸, 이어서 편집 저장 정상. 첫 캡처 0.83초(허락 포함) · 두 번째 0.15~0.2초. 판넬 화면(iframe)에 Room 입력 중 VOC → 입력값 그대로 · 다시 안 불러옴. P&ID · LOGIC · 게시판 · R&R 화면 메뉴 자동. 닫았다 다시 열면 이어 쓰기 · [새로 쓰기]. 창 안 '화면 캡처 추가' → 2장. [끄기] → 초록 점 꺼짐. 게시판에 VOC 3건(그림 수 맞음). 보안 아닌 주소(192.0.2.2): F8 → VOC 창 · 그림 칸 포커스 · 붙여넣기 → 등록 · #logic 그대로.
- 회사에서 확인할 것: Edge 에서 첫 📷 때 '이 탭 공유' 허락 → 5분 안의 다음 📷 은 묻지 않는지. `http://PC이름:8080` 으로 쓰는 부서원은 Win+Shift+S → Ctrl+V. 그 주소에서도 바로 캡처를 쓰려면 회사 IT 가 Edge 정책 `OverrideSecurityRestrictionsOnInsecureOrigin` 에 `http://PC이름:8080` 을 넣으면 됨(선택).

### 2026-10-24 (25) — 작업 창 관리: 가장자리·모서리 크기 조절 · 최대화 · 최소화 · 왼쪽/오른쪽 절반 (APP_VERSION 2026-10-24.1 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 요청 "내용을 수정할 때 뜨는 작업 창을 각 모서리를 마우스로 끌어 크기 조절 · 최대화 · 최소화 · 화면 오른쪽 절반 / 왼쪽 절반 배치". 편집 창뿐 아니라 제목 줄(`.dh`)이 있는 모든 창(행 편집 · 행 추가 · VOC · 확인 · 내 정보 …)에 적용. 범위 고르기 화면(#shotdlg)은 제외.
  - **크기 조절**: 창의 네 가장자리 · 네 모서리를 끌면 크기가 바뀜(커서가 ↔ ↕ ⤡ 모양으로 바뀜). 최소 380×220, 화면 밖으로 안 나감. 줄이면 안쪽만 스크롤되고 [저장]·[취소] 줄은 늘 보임.
  - **제목 줄 단추 4개** (닫기 왼쪽): [왼쪽 절반] [오른쪽 절반] [최대화 ↔ 이전 크기] [최소화 ↔ 되살리기]. 같은 절반 단추를 한 번 더 누르면 가운데로. **제목 줄 두 번 누르기** = 최대화 ↔ 이전 크기.
  - **끌어서 붙이기(윈도우처럼)**: 제목 줄을 화면 왼쪽/오른쪽 끝으로 끌면 파란 미리보기 → 놓으면 절반, 위쪽 끝이면 최대화. 붙여 둔 창의 제목 줄을 끌면 떼어 내 원래 크기로.
  - **절반 · 최소화 동안 뒤 화면을 씀**: 이때는 '뒤 화면을 쓸 수 있는 창'으로 바뀌어 표를 스크롤 · 클릭 · 복사하며 편집할 수 있음. 절반이면 본문이 나머지 절반에 맞춰 보임(오른쪽 절반 → 본문이 왼쪽 절반). 최소화한 창은 왼쪽 아래 한 줄(여러 개면 위로 쌓임) — 제목 줄을 누르면 되살아남(이전 배치 그대로).
  - **쓰던 글 보호**: 창 모드를 바꿔도 입력값 · 커서 위치 그대로. 창을 세워 둔(절반 · 최소화) 동안 다른 [편집]을 누르거나 바로 가기로 다른 행을 열려 하면 덮어쓰지 않고 그 창을 되살려 반짝 + '열어 둔 작업 창이 있습니다 — 먼저 저장하거나 닫으세요'. 내 업무 · 빠른 찾기 이동도 세워 둔 창은 닫지 않음.
  - **마지막 배치 기억**: 창 종류(편집 창 · VOC 창 …)마다 마지막 배치(절반 · 최대화 · 직접 바꾼 크기)를 이 PC 에 기억(`dept-wm`) → 다음에 열 때 그대로. 가운데로 되돌려 두면 다음에도 가운데. 확인 창 같은 작은 창은 기억하지 않음.
- 바뀐 곳: dashboard.html `APP_VERSION` · CSS `dialog .wmb` `dialog.wm-n` `.wm-fill` `.wm-left` `.wm-right` `.wm-max` `.wm-min` `[data-rz]` `.wmhint` `body.wm-split-r/l` · `.toast` z-index 2000 · `openDlg`(세워 둔 창 보호 · 배치 클래스 유지 · 마지막 배치 · 단추) · 창 관리 묶음 새 `WM` `WmBusy` `wmOn` `wmParked` `dlgModalOpen` `wmBusy` `wmKey` `wmSave` `wmRestore` `wmModal`(close 이벤트 삼킴) `wmSet` `wmLayout` `WM_SVG` `wmInject` `wmButtons` `wmAct` `wmZone` · 크기 조절 · 끌어 붙이기(옛 '제목 줄 끌어 이동'을 대신) · MutationObserver · 표 키보드 이동 2곳(`dlgModalOpen`) · `jumpTo` · 내 업무 시수 이동(세워 둔 창 안 닫음).
- 확인한 것: JS 문법. 임시 서버 시뮬레이션 36 항목 모두 통과 — 수행 행 편집 창에 글을 쓴 채: 오른쪽 아래 모서리로 980×792 → 680×592, 왼쪽 가장자리로 넓히기(오른쪽 끝 고정), 위 가장자리로 높이 줄이기, 저장 단추 보임, 최대화 1428×868 → 두 번 눌러 이전 크기, 오른쪽 절반(본문 왼쪽 절반 · 뒤 표 스크롤), 다른 [편집] → 덮어쓰지 않음 · 안내, 왼쪽 절반, 최소화(360×45 왼쪽 아래 · 뒤 스크롤) → 제목 줄로 되살리기(왼쪽 절반 그대로), 끝으로 끌어 오른쪽 절반 · 끌어 떼어 내기 · 위로 끌어 최대화, 그 뒤 저장 → 표에 반영, 닫히면 본문 원래대로, 다음 편집 창이 마지막 배치로 열림, 삭제 확인 창 최대화 → 취소 = 삭제 안 됨, VOC 창 절반 · 최소화 · 되살리기 · 등록, 모서리 커서 모양. 콘솔 오류 없음.
- 회사에서 확인할 것: 회사 모니터에서 오른쪽 절반 + 왼쪽 표 보기가 편한지. 화면이 좁으면(1366 등) 본문이 반이 되어 표가 좁아짐 → 그때는 크기 조절로 맞추면 됨.

### 2026-10-24 (26) — VOC 그림 마크업 (펜 · 형광펜 · 네모 · 화살표 · 글자) (APP_VERSION 2026-10-24.2 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 요청 "VOC 작성 시 캡처된 이미지에 그림펜으로 마크업". VOC 창 왼쪽 그림 위에 도구줄 — **펜 · 형광펜 · 네모 · 화살표 · 글자**, 색 5(빨강 · 노랑 · 파랑 · 초록 · 검정), 굵기 3, **되돌리기 · 다시 · 원본으로**. 그림 위에 끌면 바로 표시, 글자는 누른 곳에 쓰고 Enter.
  - 단축키(글 칸 밖): P 펜 · H 형광펜 · R 네모 · A 화살표 · T 글자 · Ctrl+Z 되돌리기 · Ctrl+Y(또는 Ctrl+Shift+Z) 다시. 고른 도구 · 색 · 굵기는 이 PC 에 기억(`dept-voc-pen`).
  - 표시는 그림 좌표로 기억하고 그릴 때마다 0.3초 뒤 원본 + 표시를 한 장으로 굳힘 → 썸네일에 ✏ 표시, 등록하면 표시가 들어간 그림이 올라감(원본은 안 올림). 큰 그림 WebP · 작은 그림 PNG.
  - 굳힌 뒤에도 표시를 기억 → 다른 그림으로 갔다 와도 · '화면 캡처 추가' 뒤에도 · 닫았다 이어 쓰기 때도 되돌리기 · 원본으로 가능. VOC 수정 때 올린 그림에 표시하면 새 그림으로 바꿔 올림(표시를 모두 지우면 원래 그림 그대로).
  - 창을 키우면(최대화 · 절반 · 크기 조절) 그림판도 따라 커짐 — 크게 놓고 정밀하게 표시.
  - 함께 고침: VOC 창 안 '화면 캡처 추가' 때 '쓰던 VOC 는 기억해 둡니다' 안내가 잘못 뜨던 것.
- 바뀐 곳: dashboard.html `APP_VERSION` · CSS `.vprev canvas` `.vtxt` `.vtools …` `.vth .vmark` · 새 `VMK_COLORS` `VMK_SIZES` `VMK` `vmkSave` `VMK_I` `VMK_TOOLS` `VMK_BAR` `vmkOps` `vmkLive` `vmkPaint` `vocMarkup`(그리기 · 글자 · 되돌리기 · 굳히기 flush · 크기 따라 다시 그림) · `openVoc`(그림 = {id|blob, base, ops} · 도구줄 · drawList · snap/임시 저장에 표시까지 · 등록 전에 굳히기 기다림 · 화면 캡처 추가 때 onclose 끊기).
- 확인한 것: JS 문법. 임시 서버 시뮬레이션 22 항목 모두 통과 — 캡처 → 빨간 펜(굳힌 그림 그 자리 빨강) · 노란 굵은 네모(변만 노랑 · 안쪽 그대로) · A 키 화살표 · 형광펜 · 글자 '여기 고쳐 주세요'(빨강 픽셀) · Ctrl+Z/Ctrl+Y · 원본으로(원래 색 · ✏ 없음) → 되돌리기로 살림 · 화면 캡처 추가(2장 · 첫 그림 표시 기억 · 돌아가 되돌리기) · 최대화하면 그림판 580 → 769px · 큰 창에서도 같은 자리 · 등록 → 서버에 올라간 그림에서 빨간 펜 · 노란 네모 확인 · 닫았다 열면 표시 · 글 그대로. 콘솔 오류 없음.

### 2026-10-24 (27) — 서버 꺼졌을 때 오프라인으로 안 열리고 '데이터 폴더 선택'이 뜨던 문제 (APP_VERSION 2026-10-24.3 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 질문 "서버 켜졌을 때 한 번 들어왔다가, 서버 꺼졌을 때 오프라인이 안 되고 데이터 폴더를 선택하라고 함". 재현(브라우저 프로필 유지 · 껐다 켜기)으로 원인 4가지 확인:
  1. **주소(http://PC:8080)로 들어갔던 사람이 서버 꺼진 뒤 파일 사본을 엶** → 브라우저 보관본(IndexedDB)은 주소마다 따로라 파일 쪽엔 없음. (서버가 꺼지면 http 주소는 아예 안 열림)
  2. **파일로 열었지만 로그인 화면에서 닫음** → 보관본은 로그인 뒤에만 만들었음.
  3. **브라우저가 닫을 때 사이트 데이터를 지움** (회사 정책 · 설정) · InPrivate · 다른 브라우저 → 보관본 없음.
  4. 보관본이 없으면 '폴더 모드'로 떨어져 왼쪽 아래에 [데이터 폴더 선택]이 보였음 → 부서원이 헷갈림.
  - 고친 것:
    - (2) 로그인 화면이 뜨면 그 뒤에서 보관본을 먼저 만듦(`loadAll({warm:true})`, 생일 팝업 없음). 로그인 뒤 불러오기와 겹치지 않게 끝날 때까지 기다림.
    - 보관본 저장 뒤 `navigator.storage.persist()` 한 번 요청(브라우저가 임의로 안 지우게).
    - (1)(3) **파일 안에 보관본을 넣음**: `<script id="deptSnap" type="application/json">`(`<` → `<`). 새 버전 교체(`replaceSelf`) 때 자동으로, 그리고 왼쪽 아래 새 단추 — 주소로 연 부서원: **[📥 내 PC 사본 받기]**(서버의 최신 파일 + 지금 데이터 → dashboard.html 내려받기), 파일로 연 부서원: **[📥 이 파일에 최신 데이터 넣기]**(이 파일을 덮어씀). 서버 PC(관리자 · 주소)는 안 보임.
    - 파일로 열 때 서버가 없으면: 브라우저 보관본과 파일 안 보관본 중 **새것**으로 오프라인. 브라우저 보관본이 없어 파일 것으로 열면 '이 파일에 들어 있는 ○○ 기준 데이터로 열었습니다' 안내.
    - 주소로 연 부서원(관리자 아님)에게 하루 한 번 배너 '서버가 꺼지면 이 주소는 열리지 않습니다 → [📥 내 PC 사본 받기]' + [오늘은 그만]. 한 번 받으면 안 보임(`dept-copy-at` · `dept-copy-hide`).
    - (4) 보관본이 하나도 없을 때 화면: 제목 '서버가 꺼져 있어 열 수 없습니다' + 흔한 이유 3가지 쉬운 말로 + [다시 시도] [서버 주소 변경]. '폴더 모드'는 아래 작은 '관리자용' 글씨로만, 왼쪽 아래 [데이터 폴더 선택] · [이름 변경] 숨김.
- 바뀐 곳: dashboard.html `APP_VERSION` · `loadAll(o)`(warm · 오프라인 때 `snapLoad` 대체) · `cacheSave`(persist) · 새 `PERSIST_ASKED` `SNAP_TAG` `withSnap` `snapLoad` `saveCopy` `copyTip` `fileCopyUpdate` · `replaceSelf`(withSnap · 저장 창 못 쓰는 브라우저는 saveCopy) · `authStart(beforeDialog)` · `startOnline`(warm) · 처음 열기 file:// 갈래(파일 안 보관본 · 보관본 없음 화면) · `renderHeader`(#btnCopy) · 배너 · data-net copy/copyno · 새 단추 `#btnCopy`.
- 확인한 것: JS 문법. 임시 서버 + 브라우저 프로필 유지(껐다 켜기) 재현: 파일로 로그인 → 서버 끔 → 오프라인 ✅(전에도 됨) / **로그인 화면에서 닫음 → 서버 끔 → 오프라인 ✅(전엔 폴더 선택)** / 주소로만 씀 → 파일 → '서버가 꺼져 있어…' 안내 화면(데이터 폴더 선택 단추 없음) / **주소에서 배너 [📥 내 PC 사본 받기] → 받은 파일 → 서버 끔 → 오프라인 ✅** / **새 프로필(보관본 지워진 브라우저)에서 그 파일 → 오프라인 ✅**. 파일 안 보관본을 다시 넣을 때 겹치지 않음(지우고 새로). 배너는 받은 뒤 사라짐.
- 회사에서 확인할 것: 부서원에게 "바탕화면의 dashboard.html 파일로 열기" 안내. 주소로 쓰는 부서원은 배너로 사본 받기. 파일 크기는 데이터만큼 커짐(시험 데이터 0.6 MB → 0.7 MB). Edge 정책 '닫을 때 검색 데이터 지우기'가 켜져 있는지 IT 확인(켜져 있어도 파일 안 보관본으로는 열림 — 다만 그 파일에 넣은 시점 데이터).

### 2026-10-24 (28) — 오프라인(서버 꺼짐) 보기가 끊기지 않게: 배포 파일에 데이터 · 파일 자동 보관 (APP_VERSION 2026-10-24.4 / SERVER_VERSION 2026-10-24.1)
> **server.py 바뀜 → 서버 재시작 필요** (stop_server → start_server). 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 요청 "절전(오프라인) 모드를 이런 문제가 안 일어나게 개선". (27)은 브라우저 보관본이 없을 때의 대비였고, 이번엔 **파일 자체가 늘 데이터를 들고 있게** 함.
  1. **서버가 만드는 배포 파일에 데이터를 넣음**: `deploy/dashboard.html` 과 `/dashboard.html?download=1`(새 버전 다운로드) 안에 지금 데이터(비회원이 보는 범위: 시트 · 열 · 상태 · 기준 마감본 · 게시판 목록 · 구성원 사진 제외)를 `deptSnap` 으로 넣음. `deploy/` 는 30분마다 데이터만 새로 넣어 다시 만듦(안내문 · 로그는 화면 파일/IP 가 바뀔 때만). → **처음 받은 파일도 서버에 한 번도 연결하지 않고 바로 오프라인으로 열림.** 그냥 화면으로 여는 `/dashboard.html` 에는 안 넣음(가볍게).
  2. **파일 사본 자동 보관**: 파일로 열고 서버에 연결되면 3시간마다 이 dashboard.html 파일 안의 보관본을 조용히 새로 씀(서버의 같은 버전 파일 + 지금 보관본). 파일 쓰기 허락이 없으면(처음 · 허락이 끝난 경우) 파일 안 보관본이 없거나 3일 넘었을 때만 배너 '💾 서버가 꺼져도 이 파일로 열리게 … [💾 자동 보관 켜기] [오늘은 그만]' → 한 번 누르면 저장 창(지금 연 파일 선택) · Edge '방문할 때마다 허용' 이면 그 뒤로는 안 물음. 다른 이름 파일을 고르면 쓰지 않음. 새 버전이 있으면 교체 쪽으로(교체 때 보관본도 같이 들어감).
  3. 왼쪽 아래 [📥 이 파일에 최신 데이터 넣기] = 2를 바로 실행(전엔 교체 + 다시 열기). 부서원 사용법.txt 4번에 '주소로 들어가면 서버가 꺼졌을 때 안 열리니 늘 이 파일로' 추가.
- 바뀐 곳: server.py `SERVER_VERSION` · `html_bytes(snap)` · 새 `SNAP_RE` `snap_data`(dashboard.html `cacheSave` 와 같은 모양, savedAt = `stamp()`) `embed_snap` · `_build_deploy`(30분 · 데이터만 갱신) · GET `/dashboard.html?download=1`. dashboard.html `APP_VERSION` · 새 `EMBED_MS` `EMBED_ASK` `embedAt` `embedSelf` `autoEmbed` `embedTip` · 배너 data-net embed/embedno · `startOnline`(4초 뒤 + 30분마다 autoEmbed) · `replaceSelf`(dept-embed-at 기록) · #btnCopy · 보관본 없음 화면 문구. (27)의 `fileCopyUpdate` 없앰.
- 확인한 것: 문법(JS · Python). 임시 서버: deploy 파일 · ?download=1 에 데이터 들어감, 그냥 화면 파일엔 없음. **서버가 만든 deploy 파일 → 서버 끔 → 새 브라우저(보관본 없음)에서 오프라인으로 열림 ✅**. 보관본 없는 파일로 로그인 → 배너 → [자동 보관 켜기](저장 창은 시험용 가짜) → 파일에 데이터가 써짐 · 배너 사라짐 → 그 파일을 서버 끔 + 새 브라우저로 열기 → 오프라인 ✅. (27) 경우(로그인 화면에서 닫음 → 오프라인) 그대로 ✅. 아무 데이터도 없는 파일 + 새 브라우저 → 안내 화면.
- 회사에서 확인할 것: 서버 재시작 뒤 `deploy\dashboard.html` 크기가 데이터만큼 커졌는지(30분마다 시각 갱신). Edge 에서 [💾 자동 보관 켜기] → 저장 창 → '방문할 때마다 허용' 이 뜨는지 · 다음날 다시 묻지 않는지(묻는다면 그 PC 정책상 허락이 세션마다 끝나는 것 — 3일에 한 번만 배너). 서버 PC 공유 폴더 deploy 를 부서원이 볼 수 있는 곳이면 안의 데이터도 같이 보임(비회원 보기 범위와 같음).

### 2026-10-24 (29) — 오른쪽 위 '오프라인 보관' 초록/빨강 표시 · 메뉴 이름 ROOM SIZE 계산 (APP_VERSION 2026-10-24.5 / SERVER_VERSION 2026-10-24.2)
> server.py 는 메뉴 이름 한 줄만 바뀜 → 서버 재시작하면 '메뉴 권한' 창 이름도 바뀜(안 해도 동작엔 문제 없음). 부서원 사본은 새 버전 배너로 교체.
- 무엇을:
  1. 요청 "서버에 접속되면 서버 꺼지기 전 데이터를 저장했다고 오른쪽 위에 심볼로 — 녹색 = 저장됨, 빨강 = 안 됨, 빨강일 때 부서원이 강제로 저장". 머리줄 [🔍 찾기] 왼쪽에 **● 오프라인 보관됨(초록) / ● 오프라인 보관 안 됨(빨강, 깜빡임)**. 좁은 화면(1200px 아래)은 점만.
     - 파일로 연 경우 초록 = 이번 접속에서 브라우저 보관본 저장 + **이 파일 안 보관본이 하루 안**(브라우저가 지워도 파일로 열림). 주소로 연 경우 초록 = 하루 안에 [내 PC 사본 받기] 함(주소는 서버 꺼지면 안 열리므로).
     - **빨강 누르기 = 바로 강제 저장**: 파일 → 이 파일 안에 지금 데이터 쓰기(`embedSelf(true)`, 처음엔 저장 창) · 주소 → 사본 파일 내려받기. 초록 누르기 = 자세히(브라우저 보관 시각 · 파일 안 보관 시각) + [지금 다시 저장].
     - 서버 PC(관리자 · 주소) · 오프라인 중 · 폴더 모드에는 안 보임(오프라인 중엔 위 빨간 배너가 있음).
  2. 요청 "판넬 공간확보 가 아니라 ROOM SIZE 계산 으로": 대시보드에 보이는 이름만 바꿈 — 왼쪽 메뉴 · 화면 제목 · VOC 메뉴 이름 · 메뉴 권한 목록 · 광장 상태('ROOM SIZE 계산 중...') · server.py `MENUS`. 메뉴 키(`space`) · 주소(#space · /apps/space/) · 권한 · 저장 자료는 그대로. **도구 안쪽 화면(apps/space)의 제목은 그 도구를 만드는 쪽에서 바꿀 것.**
- 바뀐 곳: dashboard.html `APP_VERSION` · 새 단추 `#btnSafe` · CSS `.safebtn` · 새 `CACHE_OK` `SAFE_MS` `SNAP_AT` `safeState` `renderSafe` `safeClick` · `cacheSave`(CACHE_OK) · `saveCopy`(dept-copy-at = 시각) · `embedSelf`(조용히 쓴 뒤 표시 갱신) · `renderHeader`(renderSafe) · `VOC_MENU` `APP_ROUTES` 메뉴 · 권한 목록 · `PZ_STATUS`. server.py `SERVER_VERSION` · `MENUS`.
- 확인한 것: 문법(JS · Python). 임시 서버: 보관본 없는 파일로 로그인 → 빨강 → 누름(저장 창은 시험용 가짜) → 파일에 써짐 → 초록 → 누르면 자세히 창. 서버가 만든 deploy 파일 → 처음부터 초록. 주소(보안 아닌 192.0.2.2)로 → 빨강 → 누름 → dashboard.html 내려받음 → 초록. 서버 PC 주소 → 안 보임. 메뉴 · #space 제목 'ROOM SIZE 계산'. 콘솔 오류 없음.
- 회사에서 확인할 것: Edge 에서 빨강 → 저장 창 → 지금 연 dashboard.html 선택 → [저장] → 초록. 다음날 빨강으로 바뀌면(허락이 세션마다 끝나는 PC) 한 번 눌러 주면 됨.

### 2026-10-25 (30) — LOGIC 분석 하위 메뉴 'LOGIC 작성' (APP_VERSION 2026-10-25.1 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 요청 "LOGIC 작성은 LOGIC 분석 메뉴의 하위 메뉴로". 왼쪽 메뉴 🔀 LOGIC 분석을 접기/펼치기 묶음으로 바꾸고 아래에 **LOGIC 작성**. 누르면 P&ID 서버(같은 포트 `PID_PORT`)의 `/logic/draw`(LOGIC 작도 화면, 다른 브랜치 `claude/logic-review-design-pd2z75` 에서 만듦)를 P&ID · LOGIC 분석과 같은 틀(본문 전체 iframe · 새 창으로 열기 · 서버 꺼짐 안내)로 띄움. 머리(🔀 LOGIC 분석)를 누르면 그대로 `/logic`.
  - 권한은 'LOGIC 분석'과 같음(따로 권한 칸 없음). VOC 메뉴 = LOGIC 분석. 광장 상태 'LOGIC 작성 중...'. 빠른 찾기(Ctrl+K)에 'LOGIC 분석 · LOGIC 작성'. 접기 상태 기억 `dept-nav-logic-open`.
- 바뀐 곳: dashboard.html `APP_VERSION` · `PID_ROUTES.logicdraw` · `ROUTES` · `menuOf`(logicdraw → logic) · `NAV_LS` · `renderMenu`(LOGIC 묶음) · `QF_MENUS`(권한은 menuOf) · `PZ_STATUS`.
- 확인한 것: JS 문법. 임시 서버: 메뉴에 LOGIC 분석 ▾ › LOGIC 작성, 누르면 #logicdraw · 주소 `http://…:8000/logic/draw?user=본명` · 제목 'LOGIC 작성', 다시 LOGIC 분석 → `/logic`. (시험 PC 엔 P&ID 서버가 없어 '서버가 꺼져 있습니다' 안내까지 확인.) 콘솔 오류 없음.
- 회사에서 확인할 것: 회사 P&ID 서버에 LOGIC 작도(`/logic/draw`)가 들어 있는 판이어야 화면이 뜸 — 없으면 iframe 안에 Not Found. 그 판은 LOGIC 쪽 zip 으로 적용.

### 2026-10-25 (31) — 메뉴 '🌪️ 도서검토' 연결 (APP_VERSION 2026-10-25.2 / SERVER_VERSION 2026-10-25.1)
> **server.py 바뀜 → 서버 재시작 필요.** 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 사용자 "🌪️ 도서검토도 다른 브랜치에서 업데이트한다". 도서검토 앱(`apps/books/` · `books_api.py`)은 다른 작업 줄기(`claude/new-session-v23o67`, 그쪽 `apps/books/INTEGRATION.md`)에서 만들고 zip 도 거기서 냄 → 여기서는 ROOM SIZE 계산과 같은 방식(`APP_ROUTES`)으로 **메뉴 연결만**. 이 zip 에 도서검토 파일은 없음.
  - 왼쪽 메뉴 ROOM SIZE 계산 아래 **🌪️ 도서검토** → `/apps/books/index.html` 를 본문 전체 iframe 으로. 메뉴 권한 키 `books`(기본 허용) · VOC 메뉴 '도서검토' · 빠른 찾기 · 광장 상태 '도서검토 중...'.
  - server.py: `books_api` 를 **있으면** 불러옴(`try: import books_api`), `main()` 에서 ROOT 정한 뒤 `books_api.setup(...)`, `/api/books/…` → `books_api.handle`. **books_api.py 가 없어도 서버는 정상**(그 API 만 404 '설치되지 않았습니다').
  - 연결 앱 화면 파일이 서버에 없으면(도서검토 zip 을 아직 안 넣음) iframe 에 서버 오류 글 대신 '화면 파일이 서버에 아직 없습니다 — apps\books 폴더 필요, 업데이트 zip 을 적용하세요' 안내(`renderApp`, ROOM SIZE 계산도 같음).
- 바뀐 곳: dashboard.html `APP_VERSION` · `APP_ROUTES.books` · `ROUTES` · `renderMenu` · `VOC_MENU` · `QF_MENUS` · `PZ_STATUS` · `renderApp`(404 안내). server.py `SERVER_VERSION` · `books_api` 선택 import · `main`(setup) · `Handler.api`(head 'books') · `MENUS` · `VOC_MENUS`.
- 확인한 것: 문법(JS · Python). 임시 서버: books_api.py · apps/books 없음 → 서버 정상 기동 · `/api/books/info` 404 안내 · 메뉴 → '화면 파일이 아직 없습니다'. 시험 폴더에만 그쪽 브랜치 파일을 넣고 재기동 → `/api/books/info` 정상 · 메뉴 → 도서검토 화면(제목 '계장도서검토') iframe 으로 뜸. 콘솔 오류 없음.
- 회사에서 확인할 것: 이 zip 적용 + 서버 재시작 → 메뉴에 🌪️ 도서검토. 화면은 도서검토 쪽 zip(apps\books\ · books_api.py)을 넣고 **서버 재시작**해야 뜸. 메뉴 권한 창에 '도서검토' 줄이 생김.

### 2026-10-26 (32) — ROOM SIZE 계산 · 도서검토를 P&ID 서버(run_lan_service.bat)로 연결 (APP_VERSION 2026-10-26.1 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 사용자 "ROOM SIZE 계산은 LOGIC 분석, PID 분석과 같이 run_lan_service.bat 에서 동작해야 한다" (현장 사진: 대시보드 서버 `/apps/space/` 의 옛 판넬 화면이 뜨고 있었음). P&ID 쪽 꾸러미(`claude/titleblock-parsing-c5st4x` hotfix106~116)가 같은 P&ID 서버(8000)에 `/space`(ROOM SIZE 계산, 저장 `{data}/space/`)와 `/books/`(도서검토, hotfix115~)를 이미 넣어 둠 → 대시보드 메뉴를 그쪽으로.
  - `PID_ROUTES.space` = `:8000/space?embed=1&user=본명`, `PID_ROUTES.books` = `:8000/books/?embed=1&user=본명` (P&ID · LOGIC 과 같은 `pidBase` · `/version` 확인 · 새 창으로 열기). `APP_ROUTES` 는 비움(틀만 남김).
  - P&ID 서버 확인 넉넉히(3 → 6초, 분석 중엔 늦을 수 있음) · '꺼져 있습니다' 화면에 있는 동안 **5초마다 자동 재연결**(켜지면 저절로 화면이 뜸). LOGIC 작성이 '꺼져 있습니다'로 남던 현장 사진 대응.
  - 대시보드 서버의 `/api/space/*` · `books_api` 연결은 그대로 둠(옛 자료 · P&ID 쪽 '대시보드 자료 가져오기'가 `/api/space` 를 읽음).
- 바뀐 곳: dashboard.html `APP_VERSION` · `PID_ROUTES`(space · books) · `APP_ROUTES`(빈 것) · `PID_OFF` · `pidConnect`(6초 · 5초 자동 재시도).
- 확인한 것: JS 문법. 임시 대시보드 서버 + 가짜 P&ID 서버(8000, `/version` · 페이지): P&ID 서버 꺼짐 → ROOM SIZE 계산 '꺼져 있습니다' → 가짜 서버 켬 → 자동으로 `:8000/space?embed=1&user=박부서` iframe. 도서검토 → `:8000/books/?embed=1&user=…`, LOGIC 작성 → `:8000/logic/draw?user=…`. 콘솔 오류 없음.
- 회사에서 확인할 것: P&ID 서버에 hotfix116 이상(판넬 `/space` · 도서 `/books`)이 깔려 있어야 함. 예전에 대시보드 서버에 저장한 판넬 자료는 ROOM SIZE 계산 첫 화면 ① 카드의 [대시보드 자료 가져오기]로 P&ID 서버에 들임(P&ID 쪽 기능). 도서 색인은 P&ID 서버에서 한 번 [색인 갱신].

### 2026-10-26 (33) — 📷 스크린 → VOC 를 누르면 바로 '화면 캡처를 취소했습니다'만 뜨던 것 (APP_VERSION 2026-10-26.2 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체.
- 무엇을: 현장 사진(서버 PC `localhost:8080` · 수행 화면) — 단추를 누르자마자 '화면 캡처를 취소했습니다'. 고르는 창이 뜨기도 전에 브라우저가 화면 캡처(`getDisplayMedia`)를 거절한 것 = 사람이 취소한 게 아니라 **회사 Edge 정책(ScreenCaptureAllowed 등) · 보안 프로그램 · 브라우저 설정이 캡처를 막음**. 예전 코드는 어떤 실패든 '취소'로 보고 아무것도 안 했음.
  - 거절이 0.8초 안에 오거나 NotAllowedError 가 아닌 오류면 '막힘'으로 봄 → **바로 VOC 창을 열고**(지금 화면 · 메뉴 자동 그대로) 'Win+Shift+S 로 캡처 → 왼쪽 그림 칸 Ctrl+V(그림 파일 끌어 놓기도 됨)' 안내 + 그림 칸에 포커스. 그날은 다시 묻지 않고 바로 VOC 창(`dept-shot-blocked` = 오늘 날짜). VOC 창 안 '화면 캡처 추가'도 같은 안내.
  - 사람이 고르는 창에서 [취소] 한 것(0.8초 넘어서 거절)은 전과 같음(아무 일 없음).
- 바뀐 곳: dashboard.html `APP_VERSION` · `shotStream`(오류 이름 · 걸린 시간 → `SHOT.err.blocked`) · `captureRegion`('blocked' 돌려줌) · 새 `shotBlocked` `vocPaste` · `shotToVoc` · VOC 창 `#vShot`.
- 확인한 것: JS 문법. 임시 서버: 캡처 즉시 거절(정책 흉내) → VOC 창 열림 · 안내 · #perform 그대로 → 다시 누르면 묻지 않고 바로 VOC 창 · 창 안 '화면 캡처 추가' → 안내. 고르는 창에서 1.5초 뒤 취소 → '취소했습니다'만(전과 같음). 정상 캡처(탭 허락) → 범위 고르기 화면. 콘솔 오류 없음.
- 회사에서 확인할 것: 서버 PC 에서 📷 → VOC 창 + 안내가 뜨는지. Win+Shift+S 도 막힌 PC 면 그림 파일을 끌어 놓기. 브라우저 캡처를 쓰고 싶으면 IT 에 Edge 정책 `ScreenCaptureAllowed`(또는 `ScreenCaptureAllowedByOrigins` 에 `http://localhost:8080` · `http://PC이름:8080`) 확인 요청(선택).

### 2026-10-28 (34) — 부서원 VOC 3건: 접어서 '나' 위주로 · 홈 그래프 수행/입찰 색 (APP_VERSION 2026-10-28.1 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음. 부서원 사본은 새 버전 배너로 교체.
- 무엇을 (게시판 VOC · 이영주):
  1. **수행 · 입찰 PJT 보드 '👥 부서원별 진행 PJT'** — "펼치기 전에 너무 많은 사람이 보임, 2~3명만 · 아래 수행/입찰 표가 첫 화면에 보이게": 접힌 상태 = **3명**(많이 맡은 순, 전엔 절반). 나 · 지금 고른 사람은 접혀도 보임(`foldPick`). [▼ 나머지 N명 펼치기] / [▲ 접기].
  2. **R&R · 투입 분석** (주간업무보고 메뉴):
     - 🏗 프로젝트별 투입 = 처음엔 **내가 시수를 쓴 수행 · 입찰 PJT 만**(공통 입찰 묶음 포함) + [▼ 나머지 항목 N개 더 보기].
     - 👤 부서원별 = 처음엔 **나 + 나와 같은 PJT(코드 있는 수행 · 입찰)를 한 사람**(+ 지금 고른 사람) + [▼ 나머지 부서원 N명 더 보기]. 공통 묶음(입찰 공통 · 코드 없음)은 '같은 PJT' 로 안 봄.
     - 🎯 개인 R&R 표 = '계획 투입(투입인력 시트 고정값)' · '차이' 열 **뺌** → 'R&R · 실제 투입'. 투입인력에만 있고 R&R · 시수가 없는 줄도 뺌. 많이 투입된 **상위 3줄** + [▼ 나머지 항목 N개 더 보기].
     - 내 시수가 없으면(관리자 등) 접지 않고 전부. **Management › R&R · 투입 분석은 처음부터 펼침**(팀 전체 보는 곳, 접기 단추는 있음). 펼침 상태는 그 메뉴 안에서 유지(`AS.open`).
  3. **홈 그래프 수행/입찰 색 구분**: '사업군별 PJT 수' = 수행(파랑) · 입찰(주황) **쌓은 막대**(조각에 마우스 = 그쪽 PJT 만), 'PJT별 투입인력' = 막대 색 = 투입인력 열 구분(수행 · 입찰 · 기타 회색) · 범례.
- 바뀐 곳: dashboard.html `APP_VERSION` · 새 `PJ_FOLD_N` `foldPick` `pjLegend` · `pjHero`(ofold) · `AS.open` · `renderAlloc`(isPj · myPj · opened · foldBtn · mates · R&R 표 · projRows · data-afold) · `svgBars`(세로 막대 parts · i.color) · `renderHome`(grpItems parts · 투입인력 색 · 범례) · CSS `.afnote`.
- 확인한 것: JS 문법. 임시 서버: 수행 · 입찰 보드 부서원 3명 + '나머지 15명/27명 펼치기'. 시수 있는 계정(박민수): 프로젝트 11 → 내 PJT 5 + '나머지 6개', R&R 표 6 → 3 + '나머지 3개', 열 = PJT · 구분 · R&R 역할 · 기간 · 실제 투입, 펼치기 → 11 · 6. 시수 없는 계정 → 접지 않음. 홈 두 그래프 수행/입찰 두 색. 콘솔 오류 없음.
- 회사에서 확인할 것: 회사 해상도에서 수행/입찰 표가 첫 화면에 보이는지(사업군 줄이 많으면 왼쪽 카드 높이만큼은 남음). VOC 처리 완료는 운영자가 게시판에서.

### 2026-10-29 (35) — 새 버전 교체가 바탕화면 등 다른 폴더에 저장되어 적용되지 않던 것 (APP_VERSION 2026-10-29.1 / SERVER 그대로)
> server.py 안 바뀜 → 서버 재시작 필요 없음.
- 무엇을 (VOC · 이영주): 교체 창에 '지금 쓰는 파일: D:\Desktop\새 폴더\dashboard.html' 이 나오는데 [예] → 저장 창이 **바탕화면**에서 열림 → 그대로 [저장] → 바탕화면에 새 파일이 생기고 지금 쓰는 파일은 그대로. 예전 코드는 **이름만 같으면(dashboard.html) 성공으로 보고 그 '다른 파일'을 기억** → 다음 교체 · 파일 자동 보관도 묻지 않고 계속 바탕화면 파일에 씀.
  - 고른 파일이 지금 연 파일인지 **수정 시각으로 확인**(`isSelfFile`: file:// 문서의 `document.lastModified` = 그 파일의 수정 시각 ↔ 고른 파일의 `lastModified`, 2.5초 안 · 이번 접속에서 직접 쓴 뒤의 시각도 인정). 같은 이름이라도 다른 폴더면 다름.
  - 저장 창 전에 **지금 폴더 경로를 클립보드에 복사**하고 '저장 창 위쪽 주소 칸 Ctrl+V → Enter' 안내(`selfPick`). 다른 폴더를 고르면 '⚠ 지금 쓰는 파일이 아닙니다' 창 → [다시 고르기] / [그래도 거기에 저장] / [취소]. 저장 창이 새로 만든 빈 파일은 지움.
  - 예전에 기억한 파일이 다른 폴더의 것이면 버리고 다시 고름(교체 · 파일 자동 보관 둘 다). 지금 쓰는 파일일 때만 기억.
  - 교체 뒤 다시 열렸는데 버전이 그대로면 '교체가 지금 쓰는 파일에 들어가지 않았습니다' 알림 + 기억한 파일 버림(`sessionStorage` `dept-upd`). 바뀌었으면 '새 버전으로 바꿨습니다'.
  - 저장 창을 못 쓰는 브라우저(내려받기)는 '다운로드 폴더의 그 파일을 <지금 폴더> 로 옮겨 덮어쓰세요' 안내.
- 바뀐 곳: dashboard.html `APP_VERSION` · 새 `selfDir` `SELF_WROTE` `isSelfFile` `selfPick` `selfWrite` · `askUpdate`(안내 문구) · `replaceSelf` · `embedSelf` · `saveCopy`(file:// 안내) · 처음 열기 file:// 갈래(교체 결과 확인).
- 확인한 것: JS 문법. file:// 의 `document.lastModified` = 파일 수정 시각(일치). 옛 버전 파일 + 임시 서버 + 저장 창 흉내: [지금 교체] → 첫 번째로 '다른 폴더'를 고름 → 경고 창 · 빈 파일 지움 · 아무 데도 안 씀 → [다시 고르기] → 지금 파일 → 씀 · 다시 열기 → (흉내라 실제 파일은 그대로) '교체가 지금 쓰는 파일에 들어가지 않았습니다' 알림. 콘솔 오류 없음.
- 회사에서 확인할 것: **이번 한 번은 옛 코드로 교체**되므로, 이미 바탕화면 파일을 기억한 PC 는 또 바탕화면에 저장됨 → 그 파일을 쓰는 폴더로 직접 옮겨 덮어쓰기(또는 서버 폴더 deploy 의 새 dashboard.html 복사). 그 다음 교체부터는 위처럼 확인함.

### 2026-10-30 (36) — VOC: 홈 그래프 누르면 상세 · 제목 = 첫 화면 · '변경 없음' 저장도 내 업무 완료 (APP_VERSION 2026-10-30.1 / SERVER_VERSION 2026-10-30.1)
> **server.py 바뀜 → 서버 재시작 필요.** 부서원 사본은 새 버전 배너로 교체.
- 무엇을 (게시판 VOC · 백승욱):
  1. **주간업무보고 첫 화면 그래프** "마우스 올리면 현황, 누르면 상세": 그래프 막대 · 쌓은 조각 · 도넛을 누르면 **상세 창** — 그 칸의 PJT/행 목록(시트 · 항목 · 담당자 · 사업군 · 금주 작성/변경 없음/미작성 · 최근 수정), 줄을 누르면 그 행으로 이동. PJT별 투입인력은 투입인력 행 목록. 막대에 `data-rows`('시트|ID,…'), `chartA` · `chartDetail`.
  2. **머리줄 제목 '계장ENG그룹 Dashboard'** 를 누르면 주간업무보고 첫 화면(#home).
  3. **"변경 없음 — 눌러도 내 업무에서 완료로"**: 수행 · 입찰 편집 창에서 바꾼 것 없이 [저장] → 서버가 `meta.checkedAt/checkedBy` 를 적음(내용 · rev 그대로 → 다른 사람 편집과 충돌 없음, 이력 action `check` '변경 없음 확인'). 이번 주(마지막 마감 이후)에 확인했으면 **내 업무 완료 · 금주 업데이트율 · 미업데이트 목록/배지 · 금주 업데이트 필터**에서 '작성'으로 셈(`isChecked` · `isDone`). 수정 표시(노란 칸 · 메뉴 !(n) · 시트별 업데이트 그래프)는 그대로 실제 수정만(`isUpdated`). 옛 서버는 confirm 을 모르므로 전처럼 '변경된 내용이 없습니다'.
- 바뀐 곳: dashboard.html `APP_VERSION` · 새 `isChecked` `isDone` `chartA` `chartDetail` + 클릭 처리 · `saveEdit`(confirm) · 편집 저장(수행 · 입찰 confirm) · `afterSave`('checked') · `ACT.check` · `myTasks` · 미업데이트 목록 · `renderHome`(notUpd · 그래프 rows · 안내 문구) · 수행/입찰 보드 업데이트율 · 필터 · 제목 클릭 · CSS `.cdt` `.cdtip`. server.py `SERVER_VERSION` · `api_update`(confirm → checked).
- 확인한 것: 문법(JS · Python). 임시 서버(박민수): 내 업무 '수행 PJT 예시수행-D 미완료' → 편집 창 → 그대로 저장 → '완료' · 보드 '18건 중 0건 → 1건 작성'. 제목 클릭 → #home. 사업군 그래프 수행 조각 클릭 → '발전 · 수행 11개' 창 11줄(예시수행-D = ✓ 변경 없음) → 줄 클릭 → #perform 이동. 투입인력 막대 → 3줄. 콘솔 오류 없음.
- 같은 날 VOC 중 **LOGIC 분석 3건(매크로가 보이지 않음 · 글자 상자 잘림 · LOGIC 기호 잘림)** 은 LOGIC 작성 화면(`/logic/draw`, P&ID 서버) 안의 일 → '3. LOGIC 검토 코드' / '2. PID 코드' 에서.

### 2026-10-30 (37) — 내 업무: 담당자 중 누구든 작성/변경 없음이면 완료 · 누가 했는지 표시 (APP_VERSION 2026-10-30.2 / SERVER 그대로)
- 무엇을: 사용자 "수행 · 입찰, 내 업무에서 해당 프로젝트에 어사인된 사람 중 어느 누구 한 명이라도 수정(변경 없음)하면 완료되도록". 완료 판정은 원래부터 **PJT 행 기준**(`isDone` = 이번 주 수정 또는 변경 없음 확인, 누가 했든) → 그대로. 확인: 박민수가 '변경 없음' 저장한 예시수행-D(담당 박민수 · 홍길동)가 홍길동 내 업무에서도 '완료'. 다른 사람이 한 것은 1분 자동 갱신 때 반영.
  - 헷갈리지 않게 완료 항목 설명(내 업무 창 · 툴바 마우스)에 **'박민수 님이 변경 없음 확인 (10-30 09:04)' / '내가 작성 (…)'** 표시, 미완료 설명에 '담당자 중 한 명만 하면 완료'.
- 바뀐 곳: dashboard.html `APP_VERSION` · `myTasks`(수행 · 입찰 sub). 서버는 v16.48 그대로(변경 없음 확인은 v16.48 서버 필요).
- 확인한 것: JS 문법 · 위 시나리오(홍길동 로그인 → 예시수행-D 완료 · 설명 '박민수 님이 변경 없음 확인').

### 2026-10-30 (38) — '변경 없음'이 회사에서 안 되던 것: 판넬 브랜치 server.py 합침 · 그 판도 덮어쓰기 · 옛 서버 안내 (APP_VERSION 2026-10-30.3 / SERVER_VERSION 2026-10-30.2)
> **server.py 바뀜 → 서버 재시작 필요.**
- 무엇을: 사용자 "변경 없음 기능이 반영되지 않았다". 원인(유력): 판넬 브랜치(`ccr-d82d97fa-bb3ty3`, 10-24 `0a80898` · `9ccd881`)가 **대시보드 server.py 를 따로 고쳐(SERVER 2026-10-24.1/.2) 회사에 보냄** → 회사 server.py 가 이 저장소가 모르는 판 → 대시보드 zip 의 APPLY.bat 이 server.py 를 덮지 않고 **`server.py.new`** 로만 둠 → 서버에 v16.40 이후 서버 변경(파일 안 보관본 · 도서 연결 · 변경 없음 기록)이 안 들어감. 임시 서버에 그 판 server.py 를 띄워 재현: 그대로 [저장] → '변경된 내용이 없습니다'(기록 안 됨).
  - 판넬 브랜치의 server.py 변경(룸 · Rev 만들기 · 프로젝트/룸/Rev 지우기 API, `space_room` `space_rev_add` `space_trash_saves` `space_can_del` `api_space_room_new` `api_space_rev_new` `api_space_project_del` `api_space_room_del` `api_space_rev_del` + 라우팅)을 이 server.py 에 **합침**(`git apply --3way`, 충돌 없음) → 덮어써도 그쪽 기능이 사라지지 않음.
  - `dashboard_tools/known_extra.txt`(새): 다른 줄기가 회사에 보낸 판의 커밋 목록 → `make_patch --any` 가 그 판들도 `known/` 에 넣음 → **회사본이 판넬 브랜치 판이어도 백업 후 덮어씀**.
  - 화면: 수행 · 입찰을 그대로 저장했는데 서버가 옛 판(2026-10-30.1 전)이면 '⚠ 서버가 옛 판(v…)이라 변경 없음을 기록하지 못했습니다 — server.py 를 새 판으로(옆에 server.py.new 가 있으면 그것) 바꾸고 서버 재시작' 안내.
- 바뀐 곳: server.py `SERVER_VERSION` · 판넬 API(위) · Handler 'space' 라우팅. dashboard.html `APP_VERSION` · `afterSave`(nochange 안내). dashboard_tools `make_patch.py`(extra) · `known_extra.txt`.
- 확인한 것: 문법. 새 서버(2026-10-30.2): 홍길동 예시수행-A 그대로 저장 → 완료 · `/api/space/projects` 정상. 판넬 브랜치 server.py(2026-10-24.2): 그대로 저장 → 위 ⚠ 안내 · 미완료(재현). zip 의 known/ 에 판넬 브랜치 server.py 가 들어감(아래 전달 기록).
- 회사에서 확인할 것: 대시보드 폴더에 **`server.py.new`** · `dashboard.html.new` 등 `.new` 파일이 있는지 — 있으면 이번 zip 을 적용하면 덮어씀(옛 것은 backup\). 적용 후 서버 재시작 → 왼쪽 아래 '서버 v2026-10-30.2' 확인.
