# 클로드 비서 ↔ 분석 메뉴 연결 약속 (dash-bot v1)

대시보드의 **클로드 비서**가 P&ID 서버(8000)에서 도는 분석 화면(ROOM SIZE 계산 · Valve Datasheet · P&ID · LOGIC · 도서검토 · 3D 계측제어)과
재무스타그램에 일을 시키는 방법. 대시보드 쪽은 다 되어 있고(APP_VERSION 2026-11-08.23~), **각 앱이 아래 받기 코드를 넣으면** 바로 동작한다.
앱을 만드는 곳 = '2. PID 코드' 세션(ROOM SIZE · Valve 포함). 앱이 아직 안 받으면 비서는 화면만 열어 주고 "아직 연결 안 됨" 이라고 말한다.

## 흐름
1. 부서원이 비서에게 말함: "Panel 결과 CAD로 출력해줘", "Valve Datasheet 결과 엑셀로", "Ball Valve 결과 요약",
   Equipment List 를 비서 창에 끌어다 놓고 "이걸 새로운 \"CO2 PJT\" 프로젝트 \"MCC\" 룸 \"A\" revision 으로 생성해".
2. 대시보드가 **메뉴 권한**(`can(menuOf(key))`)을 확인 → 없으면 🔒 로 거절.
3. 그 메뉴를 열고(iframe), 앱 주소(origin)로 한정해 `postMessage` 로 명령을 보냄. 쓰기(생성)는 비서가 먼저 미리보기 → [✔ 생성 실행] 을 눌러야 보냄.
4. 앱이 답하면 비서 창에 글 · 표 미리보기 · 받은 파일 다운로드.

## 대시보드 → 앱
```js
{ type:'dash-bot', v:1, id:'b17…', cmd, args, user:{ name:'홍길동' }, files:[{ name, type, data:ArrayBuffer }] }
```
| cmd | args | 앱이 할 일 |
|---|---|---|
| `result` | {} | 지금 보고 있는 결과를 표(`table`)로 (ROOM SIZE 는 도면 `geometry` 도) |
| `summary` | {} | 결과 요약 글(`text`) — 표만 줘도 대시보드가 숫자 요약 |
| `export` | `{format:'xlsx'\|'dxf'\|'pdf'\|'csv'}` | 앱의 내보내기 파일을 `files` 로. 못 하면 `ok:false, error:'unknown cmd'` → 대시보드가 `result` 를 받아 직접 .xlsx/.csv/.dxf 를 만듦 |
| `create` | `{project, room, revision}` + `files`(Equipment List 등) | 새 프로젝트/룸/리비전 생성, 파일 반영 |
| `open` | `{project, room, revision}` | 그 항목 열기 |

## 앱 → 대시보드
```js
// 화면이 뜨면 (선택)
parent.postMessage({ type:'dash-bot-hello', cmds:['result','summary','export','create'] }, '*');
// 답 (받은 메시지의 e.source 로, e.origin 에만)
e.source.postMessage({ type:'dash-bot-reply', id:d.id, ok:true,
  text:'MCC 룸: 판넬 10면, 필요 면적 약 62 m²',
  table:{ cols:['Panel','W(mm)'], rows:[['DCS-01', 800]] },
  geometry:{ units:'mm', entities:[ {type:'rect',x,y,w,h,layer,text}, {type:'line',x1,y1,x2,y2,layer}, {type:'poly',points:[[x,y],…],closed,layer}, {type:'circle',x,y,r,layer}, {type:'text',x,y,h,text,layer} ] },
  files:[{ name:'MCC_rev A.dxf', type:'application/dxf', data:ArrayBuffer }] }, e.origin);
// 실패: { type:'dash-bot-reply', id, ok:false, error:'이유' }
```
- `text` 는 글자 그대로 보여 줌(HTML 아님). 답은 12초 안에.
- 받기 코드는 **보낸 쪽 origin 이 대시보드 서버(같은 호스트, 포트 8080 등)인지 확인**하고, 권한이 필요한 일은 앱 자기 서버 권한(로그인 토큰 `dept-auth`)도 그대로 따른다.

## 앱 쪽 받기 코드 (최소 예)
```js
addEventListener('message', async e => {
  const d = e.data; if (d?.type !== 'dash-bot' || e.source !== parent) return;
  if (new URL(e.origin).hostname !== location.hostname) return;          // 같은 서버 PC 의 대시보드만
  const rep = x => e.source.postMessage({ type:'dash-bot-reply', id:d.id, ...x }, e.origin);
  try {
    if (d.cmd === 'result')  return rep({ ok:true, table:myResultTable(), geometry:myLayout() });
    if (d.cmd === 'summary') return rep({ ok:true, text:mySummary(), table:myResultTable() });
    if (d.cmd === 'create')  { await myCreate(d.args, d.files); return rep({ ok:true, text:'생성했습니다' }); }
    rep({ ok:false, error:'unknown cmd' });
  } catch (err) { rep({ ok:false, error:String(err.message || err) }); }
});
```
