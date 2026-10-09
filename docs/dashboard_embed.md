# 부서 대시보드에 P&ID 분석 넣기 (hotfix50)

부서 대시보드(계장ENG그룹 주간업무 Dashboard · 포트 8080)의 **입찰 프로젝트 / 실행 프로젝트**
메뉴 아래에 하위 메뉴 **P&ID 분석**을 두고, 이 프로그램을 그 안에 띄우는 절차입니다.

## 1. 구조

- 대시보드는 표준 라이브러리 Python 서버 + HTML 한 파일이고 pip 설치가 금지돼 있습니다.
  이 프로그램(FastAPI · PyMuPDF · numpy)을 대시보드 폴더(`apps/`)에 넣어서는 돌지 않습니다.
- 그래서 **이 프로그램은 같은 PC 에서 따로 서버로 돌고**(포트 8000), 대시보드는 그 화면을
  iframe 으로 보여 줍니다 (대시보드 문서 §7 방법 B).
- **대시보드 운영 폴더에 넣을 파일은 없습니다.**  대시보드에서 바뀌는 것은 `dashboard.html`
  하나이고 그 수정은 대시보드를 만든 Claude 가 합니다 (아래 3절 프롬프트).

## 2. 이 프로그램 쪽 (부서장 PC 에서 한 번)

1. hotfix50 꾸러미를 프로그램 폴더에 덮어씁니다.
2. **방화벽** — `open_firewall_8000.bat` 를 오른쪽 클릭 → 관리자 권한으로 실행.
   대시보드와 같은 /16 대역을 더하려면 명령 창에서 `open_firewall_8000.bat 65.3.0.0/16`.
3. **자동 시작** — `install_autostart_lan.bat` 더블클릭.  로그온할 때 `run_lan_service.bat` 이
   최소화 창으로 켜지고, 서버가 멈추면 10초 뒤 다시 켭니다.  지금 한 번 바로 켜집니다.
   - 옆에 `PID_Extract.exe` 가 있으면 그것을, 없으면 `start.bat`(Python 설치본)을 씁니다.
   - 손으로 켜려면 `start.bat --lan --no-reload` 또는 `PID_Extract.exe --lan`.
4. **확인** — 다른 PC 의 Edge 에서 `http://ASEUNGWOOK-B01:8000/` (또는 `http://65.3.30.234:8000/`).
5. **페이지가 끝없이 로딩만 하면** — `check_pid_server.bat` 더블클릭 (hotfix52).  8000 을 잡은 프로그램 ·
   `/version` · 첫 화면 자료가 응답하는지 재고 할 일을 한국어로 말합니다 (같은 글이 `logs\lan_check.txt`).
   hotfix52 부터 서비스 창은 글을 쓰지 않습니다(서버 기록은 `logs\server.log`) — 창을 눌러도 서버가 멈추지 않습니다.
6. 끄기 — 작업 표시줄의 "PID server - LAN port 8000" 창을 닫습니다 (hotfix51 부터 창 이름이 영어입니다).  자동 시작을 지우려면
   `uninstall_autostart_lan.bat`.  (대시보드 서버도 python 이라 python 을 일괄 종료하지 않습니다.)

### 사내망 모드에서 달라지는 것

| 항목 | 예전 (`127.0.0.1`) | `--lan` |
| --- | --- | --- |
| 들어올 수 있는 곳 | 이 PC 만 | 루프백 · 사설망 · **이 PC 의 /16** · `PID_ALLOW` 로 더한 대역 (대시보드 서버와 같은 규칙) |
| 그 밖의 주소 | — | 403 `사내망에서만 접속할 수 있습니다` |
| 포트 | exe 는 빈 포트를 고름 | **8000 고정** (쓰고 있으면 사유를 말하고 멈춤) |
| `/version` | 같은 출처만 | 어느 출처든 읽을 수 있음 — 대시보드가 "살아 있나" 를 묻는 자리.  버전 정보뿐이고 **다른 경로에는 이 허용이 없습니다** |

대역을 더하려면 환경 변수 `PID_ALLOW=65.4.0.0/16,10.20.0.0/16`.

### 주소 뒤에 붙는 세 값

| 값 | 뜻 |
| --- | --- |
| `embed=1` | 이 화면의 왼쪽 메뉴를 숨깁니다 (대시보드 메뉴가 이미 왼쪽에 있습니다).  결과 탭(전체 · Field · …)은 결과 머리 아래 줄로 옵니다.  첫 화면으로는 `← 첫 화면` |
| `mode=bid` · `mode=epc` | 새 프로젝트를 입찰 / 실행으로 시작합니다 (장부에 이름과 함께 적힘 · 라디오로 언제든 바꿈).  이미 있는 프로젝트의 선언은 건드리지 않습니다 |
| `user=이름` | 편집 · 저장 기록의 이름 (대시보드에 적은 이름).  자칭이라는 사실은 그대로입니다 |

## 3. 대시보드를 만든 Claude 에게 줄 프롬프트

```
입찰 프로젝트와 실행 프로젝트 메뉴에 하위 메뉴 "P&ID 분석"을 추가해 줘.
P&ID 분석은 같은 PC(부서장 PC)의 포트 8000 에서 따로 도는 P&ID 계기·밸브 추출 도구다
(사내망 모드로 켜져 있고 iframe 을 막는 헤더가 없다).
DASHBOARD_ARCHITECTURE.md 7장의 방법 B(별도 서버를 iframe 으로)로 연결한다.

1. 메뉴
   - 📈 입찰 프로젝트 아래 하위 메뉴 "P&ID 분석" (route 키 bidpjt-pid)
   - 🏗 실행 프로젝트 아래 하위 메뉴 "P&ID 분석" (route 키 runpjt-pid)
   - 주간업무보고 하위 메뉴와 같은 방식으로 접고 펼친다. ROUTES, MODULES(또는 새 분기), renderMenu 에 추가.
   - 기존 bidpjt / runpjt 화면("준비 중")은 그대로 둔다.

2. iframe 주소
   - http://<대시보드 서버 호스트>:8000/?embed=1&mode=<bid|epc>&user=<이름>
     입찰 메뉴는 mode=bid, 실행 메뉴는 mode=epc.  user 는 localStorage dept-dashboard-user 값을
     encodeURIComponent 해서 넣는다.
   - 호스트는 localhost 로 고정하지 말 것.  부서원은 file:// 사본으로 접속한다.
     지금 연결된 대시보드 서버 주소(서버 모드면 location.hostname, file:// 이면 실제 접속에 성공한
     DEFAULT_SERVERS 또는 dept-server-url 항목)의 호스트만 쓰고 포트를 8000 으로 바꾼다.
     서버 PC 에서 localhost:8080 으로 열었을 때는 localhost:8000 이 맞다.
   - 이 iframe 에는 기존 ?user=&server=&admin= 쿼리를 붙이지 않는다. 위 세 값만 넘긴다.
   - 포트 8000 은 상수 하나(예: PID_PORT)로 두고 주석에 "P&ID 추출 도구 서버 포트" 라고 적는다.

3. 화면
   - iframe 은 본문(#content) 전체 높이와 폭을 채운다. 테두리 없음. 대시보드 본문의 바깥 스크롤은 생기지 않게.
   - sandbox 속성은 쓰지 않는다. P&ID 도구는 PDF 업로드, Excel·zip 다운로드, 새 창 열기를 쓴다.
     꼭 써야 하면 allow-scripts allow-same-origin allow-forms allow-downloads allow-popups 를 다 넣는다.
   - 화면 위에 작은 줄 하나: "P&ID 분석 · 새 창으로 열기" (같은 주소를 target=_blank 로).
     큰 도면을 넓게 보고 싶을 때 쓴다.

4. 연결 실패
   - iframe 을 띄우기 전에 http://<호스트>:8000/version 을 fetch 해 본다 (timeout 3초, mode 'no-cors' 금지,
     JSON 이 와야 성공 — 이 경로 하나는 다른 출처의 fetch 를 허용한다). 실패하면 iframe 대신 안내를 보인다:
     "P&ID 분석 서버에 연결할 수 없습니다. 부서장 PC 에서 P&ID 분석 프로그램이 켜져 있는지 확인하세요."
     [다시 시도] 버튼.
   - 대시보드가 오프라인 모드여도 P&ID 서버가 살아 있으면 열어도 된다 (P&ID 는 대시보드 데이터를 쓰지 않는다).

5. 지킬 것
   - P&ID 도구의 데이터와 대시보드 데이터는 섞지 않는다. server.py 는 고치지 않는다 (API 추가 없음).
   - 외부 의존성 금지는 그대로. 운영 폴더의 data, history, trash, archive, saves, board, backup, apps 는 건드리지 않는다.
   - 배포 전 운영 폴더의 dashboard.html 을 deploy_backup\ 에 백업하고 APP_VERSION 을 올린다.
   - 이 작업으로 바뀌는 파일은 dashboard.html 하나여야 한다.
   - 수정한 부분을 다시 읽어 검토하고, 사용자가 Edge 에서 확인할 순서를 적어 줘
     (서버 PC localhost:8080 · 다른 PC 의 file:// 사본 · P&ID 서버를 끈 상태 세 경우).
```

## 3-1. (선택) 메뉴를 옮겨도 iframe 을 버리지 않기 — 대시보드 Claude 에 줄 두 번째 프롬프트

P&ID 쪽은 hotfix57 부터 **iframe 이 새로 만들어져도 이 브라우저가 지켜보던 분석으로 돌아간다**
(진행 중이면 진행 화면, 그 사이 끝났으면 결과).  그래서 이 프롬프트는 없어도 된다.  넣으면 더
매끄럽다 — 돌아올 때 다시 읽지 않고, 결과 화면의 장·확대·스크롤까지 그대로 남는다.

```
dashboard.html 의 P&ID 분석 화면(iframe)을 메뉴를 옮길 때마다 새로 만들지 말고 한 번 만든 것을 숨겼다가
다시 보여 줘.
- 처음 P&ID 메뉴를 열 때만 /version 확인 뒤 iframe 을 만든다. 다른 메뉴로 가면 그 iframe 을 지우지 말고
  display:none 으로 숨긴다 (innerHTML 로 본문을 갈아 끼우는 방식이면 iframe 을 본문 밖 컨테이너에 둔다).
  다시 P&ID 메뉴로 오면 보이기만 한다 — src 를 다시 넣지 않는다 (분석 화면이 처음으로 돌아간다).
- 연결 실패 안내(서버가 꺼져 있음)가 떠 있던 경우에만 [다시 시도] 로 새로 만든다.
- 바뀌는 파일은 dashboard.html 하나. 배포 전 deploy_backup\ 백업 · APP_VERSION 올리기.
- Edge 에서 확인: PDF 분석을 걸고 다른 메뉴 → 다시 P&ID 분석 메뉴 → 진행 막대와 경과 시간이 이어지는지.
```

## 4. 알아 둘 것

- 분석은 전부 부서장 PC 에서 돕니다.  한 분석에 메모리 5~7GB 이고 여러 명이 올리면 차례로 처리됩니다
  (그 PC 는 16GB 이상 권장).
- 이 프로그램에는 로그인이 없습니다 — 대시보드와 같습니다.  사내망 · /16 제한이 유일한 울타리입니다.
- 결과는 이 프로그램 폴더의 `app/_data/`(exe 는 `pid_data/`)에 남고 대시보드 폴더와 섞이지 않습니다.
