// Held-out test set #2 for the 내 메모장 in-app assistant router.
// "Today" = Thursday 2026-11-19 10:05 KST.
//   내일=11-20(Fri) 모레=11-21 이번 주 금요일=11-20 다음 주 월~금=11-23..11-27 다음 달 3일=12-03
// Row = [text, intent, extra]. extra keys are only given when the sentence states them.
module.exports = [
  // ───────────────────────── add (47)
  ["내일 오후 3시 Emerson 미팅 잡아줘", "add", { due: "2026-11-20", time: "1500" }],
  ["낼오후3시 회의", "add", { due: "2026-11-20", time: "1500" }],
  ["내일 3시 Emerson 미팅임", "add", { due: "2026-11-20", time: "1500" }],
  ["tmrw 2pm Yokogawa call 잡아줘", "add", { due: "2026-11-20", time: "1400" }],
  ["FAT prep meeting next Tue 10am", "add", { due: "2026-11-24", time: "1000" }],
  ["할일추가 TBE 검토", "add", {}],
  ["다음 주 화요일까지 Fisher 밸브 datasheet 회신", "add", { due: "2026-11-24" }],
  ["이번 주 금요일 KOM 자료 준비", "add", { due: "2026-11-20" }],
  ["모레까지 VDR 업데이트", "add", { due: "2026-11-21" }],
  ["다음 달 3일 FAT 일정 넣어줘", "add", { due: "2026-12-03" }],
  ["30분 뒤에 Rotork 담당자한테 전화하라고 알려줘", "add", { due: "2026-11-19", time: "1035" }],
  ["회의 끝나고 알려줘", "add", {}],
  ["오늘 오후 4시 반 loop check 결과 보고", "add", { due: "2026-11-19", time: "1630" }],
  ["담주 월요일 MOV 사양 확정", "add", { due: "2026-11-23" }],
  ["Cv 계산 다시 하기 할 일로 넣어줘", "add", {}],
  ["PO 발행 요청 내일까지 해야 함", "add", { due: "2026-11-20" }],
  ["리마인더: 금요일 오전 9시 주간보고 제출", "add", { due: "2026-11-20", time: "0900" }],
  ["12월 1일 Yokogawa FAT 출장", "add", { due: "2026-12-01" }],
  ["11/25 14:00 VDR 리뷰 회의 등록", "add", { due: "2026-11-25", time: "1400" }],
  ["다음주 수요일 3시 반에 instrument index 검토 미팅", "add", { due: "2026-11-25", time: "1530" }],
  ["이따 2시에 팀장님 보고 잊지 않게 해줘", "add", { due: "2026-11-19", time: "1400" }],
  ["오늘중으로 견적 비교표 작성", "add", { due: "2026-11-19" }],
  ["내일 아침에 현장 사진 정리", "add", { due: "2026-11-20" }],
  ["할 일: 계장 케이블 스케줄 업데이트", "add", {}],
  ["To-do 추가해줘 - Fisher 6000 시리즈 견적 요청, 다음 주 금요일", "add", { due: "2026-11-27" }],
  ["1시간 뒤에 메일 확인하라고 알려줘", "add", { due: "2026-11-19", time: "1105" }],
  ["11월 30일까지 interlock list 리비전", "add", { due: "2026-11-30" }],
  ["다음 달 10일 오후 2시 고객사 정기회의 잡아", "add", { due: "2026-12-10", time: "1400" }],
  ["내일 10시 반 PSV 벤더 미팅 추가해 주실 수 있을까요?", "add", { due: "2026-11-20", time: "1030" }],
  ["Add task: review control valve TBE by Friday", "add", { due: "2026-11-20" }],
  ["오늘 5시까지 DCS I/O list 회신", "add", { due: "2026-11-19", time: "1700" }],
  ["다음 주 목요일에 SIL 검증 회의", "add", { due: "2026-11-26" }],
  ["모레까지 hook-up 도면 마크업 끝내기", "add", { due: "2026-11-21" }],
  ["내일 점심 먹고 Rotork 액추에이터 토크 확인", "add", { due: "2026-11-20" }],
  ["일정 추가 12/3 FAT 사전회의 오전 9시", "add", { due: "2026-12-03", time: "0900" }],
  ["다음주 금 오후 1시 KOM", "add", { due: "2026-11-27", time: "1300" }],
  ["잊지 말고 내일 Yokogawa 견적 유효기간 확인하게 알려줘", "add", { due: "2026-11-20" }],
  ["할 일 하나 추가: 계장 BOQ 물량 재검토", "add", {}],
  ["내일까지 instrument datasheet Rev.B 발행해야 돼", "add", { due: "2026-11-20" }],
  ["오늘 오후 3시 PSV 사이징 회의 생김", "add", { due: "2026-11-19", time: "1500" }],
  ["next Wed 9am loop check kickoff", "add", { due: "2026-11-25", time: "0900" }],
  ["낼 오전 11시 구매팀이랑 PO 조건 협의", "add", { due: "2026-11-20", time: "1100" }],
  ["25일 오후 2시 반 vendor print 검토회의 일정 넣어줘", "add", { due: "2026-11-25", time: "1430" }],
  ["퇴근 전에 일일보고 쓰기 알림", "add", {}],
  ["금요일까지 analyzer shelter 레이아웃 확인", "add", { due: "2026-11-20" }],
  ["12월 15일 오전 10시 HAZOP 참석", "add", { due: "2026-12-15", time: "1000" }],
  ["3시에 Fisher 콜 알림 맞춰줘", "add", { time: "1500" }],
  ["금요일에 Rotork 콜 잡아줘", "add", { due: "2026-11-20" }],

  // ───────────────────────── query (43)
  ["오늘?", "query", { win: "today" }],
  ["오늘 할 일 뭐 있어?", "query", { win: "today" }],
  ["내일 회의 몇 시였지?", "query", { win: "tom" }],
  ["이번 주 일정 보여줘", "query", { win: "tw" }],
  ["담주 스케줄 어때", "query", { win: "nw" }],
  ["밀린 거 있어?", "query", { win: "late" }],
  ["기한 지난 할 일", "query", { win: "late" }],
  ["남은 할 일 전부 보여줘", "query", { win: "all" }],
  ["할 일?", "query", { win: "all" }],
  ["오늘 끝낸 거 뭐야", "query", { win: "done" }],
  ["이번 주에 뭐 끝냈지?", "query", { win: "done" }],
  ["11월 25일 일정 뭐 있어", "query", { win: "d:2026-11-25" }],
  ["다음 주 화요일에 뭐 있지?", "query", { win: "d:2026-11-24" }],
  ["모레 뭐 있어?", "query", { win: "d:2026-11-21" }],
  ["급한 거 뭐 있어?", "query", { win: "all", pri: true }],
  ["박지훈 담당 할 일 보여줘", "query", { win: "all", who: "박지훈" }],
  ["내일 뭐해야 돼?", "query", { win: "tom" }],
  ["What's on my plate today?", "query", { win: "today" }],
  ["이번주 마감 뭐야", "query", { win: "tw" }],
  ["다음주에 잡힌 회의 있어?", "query", { win: "nw" }],
  ["오늘 몇 시에 회의 있지?", "query", { win: "today" }],
  ["아직 안 끝난 일 몇 개야", "query", { win: "all" }],
  ["마감 넘긴 거 알려줘", "query", { win: "late" }],
  ["today's tasks", "query", { win: "today" }],
  ["12/3에 뭐 잡혀있지", "query", { win: "d:2026-12-03" }],
  ["이번 주 남은 일정", "query", { win: "tw" }],
  ["오늘 일정 브리핑해줘", "query", { win: "today" }],
  ["내일 오전에 뭐 있어요?", "query", { win: "tom" }],
  ["우선순위 높은 일만 보여줘", "query", { win: "all", pri: true }],
  ["오늘 급한 일 있나?", "query", { win: "today", pri: true }],
  ["이정민 과장 담당으로 걸린 거 있어?", "query", { win: "all", who: "이정민" }],
  ["다음 주 월요일 일정 확인", "query", { win: "d:2026-11-23" }],
  ["지난주에 끝낸 거 뭐였지", "query", { win: "done" }],
  ["완료한 할 일 뭐뭐 있어", "query", { win: "done" }],
  ["기한 놓친 거 있으면 알려줘", "query", { win: "late" }],
  ["남은 거 다 뭐야", "query", { win: "all" }],
  ["담주 화욜 뭐있지", "query", { win: "d:2026-11-24" }],
  ["오늘 오후 일정 비어 있어?", "query", { win: "today" }],
  ["이번 주 내 할 일 몇 개 남았어", "query", { win: "tw" }],
  ["내일 일정 좀 알려주실래요?", "query", { win: "tom" }],
  ["밀린 일 중에 급한 거", "query", { win: "late", pri: true }],
  ["any meetings next week?", "query", { win: "nw" }],
  ["오늘할일", "query", { win: "today" }],

  // ───────────────────────── done (26)
  ["견적 비교표 다 했어", "done", { q: "견적 비교표" }],
  ["Rotork 콜 끝", "done", { q: "Rotork 콜" }],
  ["회의 끝났어", "done", { q: "회의" }],
  ["다 했어 TBE", "done", { q: "TBE" }],
  ["PO 발행 다 했어", "done", { q: "PO 발행" }],
  ["Fisher datasheet 회신 완료", "done", { q: "Fisher datasheet 회신" }],
  ["loop check 결과 보고 끝냈음", "done", { q: "loop check 결과 보고" }],
  ["KOM 자료 준비 완료 처리해줘", "done", { q: "KOM 자료" }],
  ["Yokogawa 콜 done", "done", { q: "Yokogawa 콜" }],
  ["PSV 사이징 회의 마쳤어", "done", { q: "PSV 사이징 회의" }],
  ["VDR 업데이트 체크 표시해줘", "done", { q: "VDR 업데이트" }],
  ["주간보고 제출했어요", "done", { q: "주간보고" }],
  ["MOV 사양 확정 끝", "done", { q: "MOV 사양" }],
  ["Cv 계산 마무리했다", "done", { q: "Cv 계산" }],
  ["interlock list 리비전 완료!", "done", { q: "interlock list 리비전" }],
  ["팀장님 보고 했음", "done", { q: "팀장님 보고" }],
  ["Emerson 미팅 끝남", "done", { q: "Emerson 미팅" }],
  ["I/O list 회신 보냈어, 완료로 바꿔줘", "done", { q: "I/O list 회신" }],
  ["hook-up 도면 마크업 끝냈어요", "done", { q: "hook-up 도면 마크업" }],
  ["Mark the FAT prep task as done", "done", { q: "FAT prep" }],
  ["견적 유효기간 확인 했고", "done", { q: "견적 유효기간 확인" }],
  ["BOQ 물량 재검토 완료됨", "done", { q: "BOQ 물량 재검토" }],
  ["케이블 스케줄 업데이트 완료 처리", "done", { q: "케이블 스케줄 업데이트" }],
  ["현장 사진 정리 다함", "done", { q: "현장 사진 정리" }],
  ["datasheet Rev.B 발행 끝", "done", { q: "datasheet Rev.B 발행" }],
  ["일일보고 썼어", "done", { q: "일일보고" }],

  // ───────────────────────── move (26)
  ["회의 3시로 미뤄줘", "move", { q: "회의", time: "1500" }],
  ["Rotork 콜 금요일로 옮겨", "move", { q: "Rotork 콜", due: "2026-11-20" }],
  ["FAT 사전회의 하루 늦춰", "move", { q: "FAT 사전회의", shift: "+1d" }],
  ["Emerson 미팅 내일로 변경", "move", { q: "Emerson 미팅", due: "2026-11-20" }],
  ["PSV 회의 30분 뒤로", "move", { q: "PSV 회의", shift: "+30m" }],
  ["KOM 다음 주 월요일로 연기해줘", "move", { q: "KOM", due: "2026-11-23" }],
  ["Yokogawa call 1시간 당겨줘", "move", { q: "Yokogawa call", shift: "-1h" }],
  ["VDR 리뷰 회의 25일에서 26일로 바꿔", "move", { q: "VDR 리뷰 회의", due: "2026-11-26" }],
  ["주간보고 마감 하루 앞당겨", "move", { q: "주간보고", shift: "-1d" }],
  ["loop check kickoff 오전 10시로 조정", "move", { q: "loop check kickoff", time: "1000" }],
  ["Fisher 견적 요청 다음 주 수요일로 미뤄", "move", { q: "Fisher 견적 요청", due: "2026-11-25" }],
  ["팀장님 보고 4시로 옮겨줄래?", "move", { q: "팀장님 보고", time: "1600" }],
  ["HAZOP 일정 12월 17일로 변경됐어", "move", { q: "HAZOP", due: "2026-12-17" }],
  ["고객사 정기회의 2시에서 3시 반으로", "move", { q: "고객사 정기회의", time: "1530" }],
  ["Move the Yokogawa FAT trip to Dec 8", "move", { q: "Yokogawa FAT", due: "2026-12-08" }],
  ["SIL 검증 회의 이틀 미뤄줘", "move", { q: "SIL 검증 회의", shift: "+2d" }],
  ["PO 조건 협의 모레 오후 2시로", "move", { q: "PO 조건 협의", due: "2026-11-21", time: "1400" }],
  ["TBE 검토 마감 연장해줘 다음 주 금요일까지", "move", { q: "TBE 검토", due: "2026-11-27" }],
  ["instrument index 검토 미팅 한 시간 늦춰 주세요", "move", { q: "instrument index 검토 미팅", shift: "+1h" }],
  ["vendor print 검토회의 다음 달 2일로 옮겨", "move", { q: "vendor print 검토회의", due: "2026-12-02" }],
  ["datasheet 회신 기한 11/30으로 바꿔줘", "move", { q: "datasheet 회신", due: "2026-11-30" }],
  ["Rotork 콜 오후 4시 반으로 리스케줄", "move", { q: "Rotork 콜", time: "1630" }],
  ["견적 비교표 마감 내일로 미룰게", "move", { q: "견적 비교표", due: "2026-11-20" }],
  ["MOV 사양 확정 일주일 미뤄", "move", { q: "MOV 사양 확정", shift: "+7d" }],
  ["현장 사진 정리 내일 말고 모레로", "move", { q: "현장 사진 정리", due: "2026-11-21" }],
  ["회의 30분 당겨줘", "move", { q: "회의", shift: "-30m" }],

  // ───────────────────────── cancel (20)
  ["회식 취소됐어", "cancel", { q: "회식" }],
  ["커피챗 지워줘", "cancel", { q: "커피챗" }],
  ["택배 수령 할 일 삭제", "cancel", { q: "택배 수령" }],
  ["Emerson 미팅 취소", "cancel", { q: "Emerson 미팅" }],
  ["PSV 회의 없어졌어", "cancel", { q: "PSV 회의" }],
  ["FAT 출장 안 가게 됐어, 일정 빼줘", "cancel", { q: "FAT 출장" }],
  ["Yokogawa call cancelled", "cancel", { q: "Yokogawa call" }],
  ["loop check kickoff 취소해 주세요", "cancel", { q: "loop check kickoff" }],
  ["Fisher 견적 요청은 필요 없어졌어 지워", "cancel", { q: "Fisher 견적 요청" }],
  ["내일 SIL 회의 캔슬", "cancel", { q: "SIL 회의" }],
  ["Remove the KOM prep task", "cancel", { q: "KOM prep" }],
  ["고객사 정기회의 이번엔 안 한대", "cancel", { q: "고객사 정기회의" }],
  ["할 일에서 analyzer shelter 확인 빼", "cancel", { q: "analyzer shelter 확인" }],
  ["치과 예약 취소", "cancel", { q: "치과 예약" }],
  ["BOQ 재검토 건 삭제해줘", "cancel", { q: "BOQ 재검토" }],
  ["HAZOP 참석 취소됐대", "cancel", { q: "HAZOP 참석" }],
  ["점심 약속 없던 걸로", "cancel", { q: "점심 약속" }],
  ["vendor print 검토회의 날려줘", "cancel", { q: "vendor print 검토회의" }],
  ["PO 조건 협의 일정 지워 주실래요?", "cancel", { q: "PO 조건 협의" }],
  ["중복된 TBE 할 일 하나 삭제", "cancel", { q: "TBE" }],

  // ───────────────────────── sticky (15)
  ["포스트잇 붙여줘: 내일 PSV 도면 출력", "sticky", {}],
  ["스티커로 'Rotork 회신 대기' 붙여", "sticky", {}],
  ["스티키 추가: 금요일 주간보고", "sticky", {}],
  ["메모지 붙여줘 Cv 재계산 필요", "sticky", {}],
  ["sticky note: call Fisher re: trim material", "sticky", {}],
  ["화면에 포스트잇으로 FAT 체크리스트 챙기기 남겨줘", "sticky", {}],
  ["스티커 붙여 — PO 번호 4500123456", "sticky", {}],
  ["노란 포스트잇에 'loop check 2구역' 적어서 붙여줘", "sticky", {}],
  ["포스트잇 하나: 팀장님 휴가 11/24~25", "sticky", {}],
  ["스티키로 남겨 TBE 코멘트 3건 미반영", "sticky", {}],
  ["붙임쪽지 만들어줘 MOV 토크값 재확인", "sticky", {}],
  ["post-it 추가 Yokogawa 담당자 내선 2231", "sticky", {}],
  ["포스트잇으로 띄워 놔: 오후에 VDR 업로드", "sticky", {}],
  ["스티커 메모 하나 붙여줄래? 커피 원두 주문", "sticky", {}],
  ["포스트잇붙여 KOM 장소 3층 대회의실", "sticky", {}],

  // ───────────────────────── note (21)
  ["메모해줘: Fisher 리드타임 16주", "note", {}],
  ["적어둬 PSV 셋압 15.5 barg로 변경", "note", {}],
  ["기록해 둬, 오늘 회의에서 Rotork가 IP67 대신 IP68 제안함", "note", {}],
  ["이거 메모에 추가: Yokogawa FAT 장소 김포 공장", "note", {}],
  ["TBE 결과 메모에 적어줘 - Emerson 1순위, Fisher 2순위", "note", {}],
  ["회의 내용 메모: 고객사가 SIL 2 요구, 추가 검토 필요", "note", {}],
  ["note: control valve noise limit 85 dBA", "note", {}],
  ["메모 남겨 줘. 현장 MOV 3대 토크 스위치 불량", "note", {}],
  ["지금 메모에 이 내용 넣어줘: DCS 마샬링 캐비닛 2면 추가", "note", {}],
  ["오늘 메모에 '구매팀 PO 일정 확인함' 한 줄 추가", "note", {}],
  ["까먹기 전에 적어놔 Cv 계산 시 최대유량 120 m3/h 기준", "note", {}],
  ["기록: 11/19 Emerson 견적 유효기간 30일", "note", {}],
  ["이 내용 메모장에 저장해 줘 — 계장 케이블 트레이 폭 600으로 확정", "note", {}],
  ["메모에 써줘 analyzer 샘플라인 heat tracing 필요", "note", {}],
  ["한 줄 메모: datasheet Rev.B 고객 코멘트 12건", "note", {}],
  ["적어두자, VDR 제출 주기 2주", "note", {}],
  ["메모 좀 해 주세요. 내일 회의 참석자 김부장, 박과장, Rotork 2명", "note", {}],
  ["add to memo: PT range 0-25 barg confirmed", "note", {}],
  ["회의록에 추가해줘 - 액션아이템: I/O list 재발행", "note", {}],
  ["기억해둬 Fisher 담당자 메일 주소 바뀜", "note", {}],
  ["메모햐줘 hook-up 도면 표준 STD-I-001 적용", "note", {}],

  // ───────────────────────── find (26)
  ["지난번 PSV 회의 메모 어디 있지?", "find", {}],
  ["회의록 메모 찾아줘", "find", {}],
  ["Rotork 관련 메모 검색", "find", {}],
  ["Fisher 리드타임 적어둔 거 어디 있더라", "find", {}],
  ["TBE 메모 찾아", "find", {}],
  ["KOM 메모 있었나?", "find", {}],
  ["find my note about Yokogawa FAT", "find", {}],
  ["'Cv' 들어간 메모 다 찾아줘", "find", {}],
  ["지난주 쓴 loop check 메모 어딨어", "find", {}],
  ["SIL 얘기 적은 페이지 어디야", "find", {}],
  ["#견적 태그 붙은 메모 찾아줘", "find", {}],
  ["Emerson 단가 메모해둔 거 찾아줄래", "find", {}],
  ["datasheet 코멘트 정리한 메모 검색해", "find", {}],
  ["MOV 토크 관련 기록 있어?", "find", {}],
  ["작년에 쓴 HAZOP 메모 찾아 줘요", "find", {}],
  ["메모에서 PO 번호 찾아줘", "find", {}],
  ["analyzer 검색", "find", {}],
  ["hook-up 도면 얘기 어디 적었더라", "find", {}],
  ["11월 초에 쓴 VDR 메모 어디 갔지", "find", {}],
  ["search notes for interlock", "find", {}],
  ["고객 코멘트 적어둔 페이지 찾아줘", "find", {}],
  ["케이블 트레이 폭 메모 어디있음", "find", {}],
  ["박과장이 말한 거 적어둔 메모 찾아봐", "find", {}],
  ["김포 공장 들어간 메모 있나", "find", {}],
  ["noise limit 메모 검색 좀", "find", {}],
  ["지난달 회의록 찾아줘", "find", {}],

  // ───────────────────────── open (20)
  ["할 일 목록 열어줘", "open", {}],
  ["메일함 보여줘", "open", {}],
  ["보드 뷰로 열어", "open", {}],
  ["위키 열어", "open", {}],
  ["포스트잇 모아보기", "open", {}],
  ["태그 목록 보여줘", "open", {}],
  ["휴지통 열어줘", "open", {}],
  ["페이지 트리 펼쳐줘", "open", {}],
  ["칸반으로 보여줘", "open", {}],
  ["open mailbox", "open", {}],
  ["스티키 보드 띄워", "open", {}],
  ["메일 정리함 가줘", "open", {}],
  ["휴지통에 뭐 있는지 보자", "open", {}],
  ["태그 페이지로 이동", "open", {}],
  ["할일 보드", "open", {}],
  ["위키 페이지 열어 주세요", "open", {}],
  ["전체 페이지 목록 보여줘", "open", {}],
  ["go to task board", "open", {}],
  ["받은 메일 요약 목록 열어", "open", {}],
  ["삭제한 메모 보관함 열어", "open", {}],

  // ───────────────────────── new (20)
  ["새 메모 만들어줘", "new", {}],
  ["주간회의 회의록 양식으로 메모 하나 열어", "new", {}],
  ["제목 'FAT 준비'로 페이지 만들어", "new", {}],
  ["회의록 메모 만들어줘", "new", {}],
  ["new page", "new", {}],
  ["빈 페이지 하나", "new", {}],
  ["Rotork 미팅 노트 새로 작성할게", "new", {}],
  ["TBE 검토 페이지 새로 만들어 줘", "new", {}],
  ["새 페이지: 11월 PSV 이슈", "new", {}],
  ["출장 보고서 템플릿으로 새 메모", "new", {}],
  ["create a new note titled Yokogawa FAT", "new", {}],
  ["회의록 양식 하나 띄워줘", "new", {}],
  ["새 문서 시작", "new", {}],
  ["오늘 날짜로 일지 페이지 만들어", "new", {}],
  ["KOM 회의록 새로 써야 돼, 페이지 만들어 줄래?", "new", {}],
  ["체크리스트 양식으로 loop check 페이지 생성", "new", {}],
  ["하위 페이지 추가해 줘 - 계장 BOQ", "new", {}],
  ["새메모", "new", {}],
  ["업무일지 템플릿으로 새로 하나", "new", {}],
  ["Fisher 밸브 검토라는 제목으로 새 노트", "new", {}],

  // ───────────────────────── summary (20)
  ["이 메모 요약해줘", "summary", {}],
  ["지금 보는 페이지 세 줄로 정리", "summary", {}],
  ["오늘 쓴 메모 정리해줘", "summary", {}],
  ["견적 메모 요약해줘", "summary", {}],
  ["summarize this page", "summary", {}],
  ["요약", "summary", {}],
  ["이 회의록 핵심만 뽑아줘", "summary", {}],
  ["현재 페이지 3줄 요약 부탁해요", "summary", {}],
  ["이 페이지 짧게 줄여줘", "summary", {}],
  ["오늘 메모들 한 번에 요약", "summary", {}],
  ["TBE 메모 요점 정리", "summary", {}],
  ["열려 있는 메모 TL;DR", "summary", {}],
  ["이 노트 액션아이템만 뽑아서 정리해줘", "summary", {}],
  ["PSV 회의 메모 요약 좀", "summary", {}],
  ["오늘 작성한 노트 다 묶어서 정리해 줄 수 있어?", "summary", {}],
  ["이 페이지 내용 bullet로 요약", "summary", {}],
  ["지금 메모 한 문단으로 요약해 주세요", "summary", {}],
  ["give me a summary of today's notes", "summary", {}],
  ["Rotork 미팅 노트 간단히 정리", "summary", {}],
  ["이 메모 핵심 3가지", "summary", {}],

  // ───────────────────────── pull (20)
  ["CO2 PO 전망 이번 달 표로 불러와", "pull", {}],
  ["수행 PJT 현안 요약해서 가져와", "pull", {}],
  ["이슈 미결 건 목록으로 땡겨와", "pull", {}],
  ["구매 일정 지연 건 메모로 가져와", "pull", {}],
  ["VOC 이번 주 접수 건 표로 붙여줘", "pull", {}],
  ["PSR 최신 내용 메모에 불러와", "pull", {}],
  ["입찰 PJT 목록 가져와서 표로", "pull", {}],
  ["통합 업무 진행 현황 메모에 넣어줘", "pull", {}],
  ["대시보드에서 수행 PJT 일정 끌어와", "pull", {}],
  ["pull open issues into this note", "pull", {}],
  ["주간업무 이번 주 내용 가져와 줘", "pull", {}],
  ["다른 메뉴에서 PO 발행 예정 건 불러와", "pull", {}],
  ["구매 현황 표 복사해서 여기 붙여", "pull", {}],
  ["이슈 트래커 미결 항목 끌어와 줘요", "pull", {}],
  ["PJT별 현안 메모로 가져오기", "pull", {}],
  ["VOC 미처리 건 불러와줘", "pull", {}],
  ["입찰 일정 이번 달 것만 표로 가져와", "pull", {}],
  ["통합업무 내 담당 건 땡겨와", "pull", {}],
  ["CO2 PO 전망 다음 달 거 불러와 줘", "pull", {}],
  ["수행 PJT 진행률 표 붙여넣어 줘", "pull", {}],

  // ───────────────────────── mail (10)
  [`From: Daniel Park <d.park@valve-vendor.example>
Sent: Wednesday, November 18, 2026 5:42 PM
To: I&C Team
Subject: RE: Control valve TBE - clarification

Dear Sir,

Please find our replies to your TBE comments below.
1. Trim material will be changed to 316SS with Stellite hardfacing.
2. Noise level at max flow is 83 dBA.
3. Delivery: 16 weeks after PO.

Please let us know if you need anything further.

Best regards,
Daniel`, "mail", {}],
  [`보낸 사람: 김현수 <hs.kim@epc-client.example>
받는 사람: 계장ENG그룹
날짜: 2026-11-18 (수) 16:20
제목: [PJT-A] Instrument datasheet Rev.B 코멘트 회신 요청

안녕하세요.

지난주 송부드린 datasheet Rev.B 에 대한 고객사 코멘트 12건을 첨부와 같이 전달드립니다.
11월 26일(목)까지 회신 부탁드리며, 특히 PT-1203 range 변경 건은 우선 검토 바랍니다.

감사합니다.
김현수 드림`, "mail", {}],
  [`이 메일 요약해줘

Hi team,

The FAT for the MOV actuators is now confirmed for Dec 3-4 at our factory.
Please send the attendee list by Nov 25 so we can arrange the gate pass.
The test procedure (Rev.1) is attached; kindly return comments by Nov 27.
Lunch will be provided. Parking is limited, so car-pooling is recommended.

Regards,
Sarah Lee
Project Manager`, "mail", {}],
  [`-----Original Message-----
From: 이수진 <sj.lee@purchase.example>
To: 계장 담당자
Subject: PO 발행 일정 안내

안녕하세요, 구매팀 이수진입니다.
Control valve 패키지 PO는 11/24(화) 발행 예정입니다.
발행 전 최종 사양 확인서 회신 부탁드립니다.
감사합니다.`, "mail", {}],
  [`메일 정리해줘
보낸사람: 박정우 책임 <jw.park@site.example>
제목: 현장 loop check 진행 현황 (11/18)

금일 loop check 진행 결과 공유드립니다.
- 2구역: 142 loop 중 120 완료
- 불량 6건 (배선 오결선 4, TX 설정 오류 2)
- 내일은 3구역 착수 예정
조치 필요 사항은 첨부 리스트 참고 부탁드립니다.`, "mail", {}],
  [`From: Kenji Sato <k.sato@dcs-vendor.example>
To: I&C Engineering
Cc: Purchasing
Subject: DCS I/O list Rev.2 - questions

Dear Team,

We have reviewed I/O list Rev.2 and have the following questions:
- 14 AI points have no range information.
- Spare philosophy: please confirm 20% installed spare per card.
- Marshalling cabinet count may increase from 4 to 6.
We would appreciate your reply by Friday.

Best regards,
Kenji`, "mail", {}],
  [`보낸 사람: 최은영 <ey.choi@epc.example>
제목: [회의소집] PSV 사이징 검토회의
일시: 11월 24일(화) 14:00~15:30
장소: 본사 7층 소회의실
참석: 공정 2명, 계장 2명, 배관 1명

안건
1. PSV 23대 사이징 결과 검토
2. Fire case 적용 기준 확인
3. 벤더 데이터시트 일정

참석 가능 여부 회신 바랍니다.`, "mail", {}],
  [`이거 요약 좀
From: QA Team <qa@vendor.example>
Date: Nov 17, 2026
Subject: NCR-0342 Transmitter calibration certificate missing

Dear Customer,
During final inspection we found that calibration certificates for 8 pressure transmitters
(tag PT-2101~2108) were not included in the shipment documentation.
Replacement certificates will be issued within 5 working days.
We apologize for the inconvenience.
QA Team`, "mail", {}],
  [`From: 정다은 <de.jung@client.example>
To: 계장ENG
Subject: Re: Re: analyzer shelter layout

수정 레이아웃 확인했습니다.
다만 샘플 conditioning 패널 앞 유지보수 공간이 800mm 로 부족합니다. 1000mm 이상 확보 부탁드립니다.
또한 HVAC 용량 계산서도 함께 제출해 주세요.
회신은 다음 주 수요일까지 부탁드립니다.

> 2026-11-16 계장ENG 작성:
> 수정 레이아웃 송부드립니다.`, "mail", {}],
  [`보낸 사람: 액추에이터 영업팀 <sales@actuator.example>
받는 사람: 계장ENG그룹
제목: IQ3 액추에이터 견적 (Rev.1)

안녕하세요.
요청하신 MOV 액추에이터 24대 견적을 송부드립니다.
- 단가: 대당 4,850,000원 (VAT 별도)
- 납기: PO 후 14주
- 견적 유효기간: 2026-12-18
추가 문의 사항은 회신 주시기 바랍니다.
감사합니다.`, "mail", {}],

  // ───────────────────────── null (77) — dashboard data / translation / Excel / UI / chit-chat / I&C knowledge
  ["PO 나갔어?", null, {}],
  ["수행 PJT 몇 개야?", null, {}],
  ["구매 일정 지연된 거 몇 건이야", null, {}],
  ["이번 달 PSR 제출 현황 알려줘", null, {}],
  ["VOC 미처리 몇 건?", null, {}],
  ["입찰 PJT 올해 몇 건이야", null, {}],
  ["통합 업무 누가 담당이야?", null, {}],
  ["김민수 과장 전화번호 알려줘", null, {}],
  ["CO2 PO 전망 이번 달 얼마야", null, {}],
  ["A 프로젝트 현안이 뭐야?", null, {}],
  ["이 문장 영어로 번역해줘: 납기 지연에 대해 사과드립니다", null, {}],
  ["Please translate to Korean: The valve shall be fail-close on loss of air.", null, {}],
  ["이 문장 자연스럽게 다듬어줘: We kindly request you to submit the revised datasheet ASAP.", null, {}],
  ["맞춤법 검사해줘 '검토후 회신 부탁드립니다'", null, {}],
  ["엑셀로 다운로드", null, {}],
  ["구매 일정 엑셀로 뽑아줘", null, {}],
  ["다크모드", null, {}],
  ["글씨 크게 해줘", null, {}],
  ["라이트 모드로 바꿔", null, {}],
  ["안녕", null, {}],
  ["고마워", null, {}],
  ["수고했어", null, {}],
  ["ㅎㅇ", null, {}],
  ["thanks!", null, {}],
  ["너 누구야?", null, {}],
  ["점심 뭐 먹지", null, {}],
  ["오늘 날씨 어때?", null, {}],
  ["Equal percentage 특성이 뭐야?", null, {}],
  ["SIL 2 가 뭐야", null, {}],
  ["PT-101 태그 뜻", null, {}],
  ["Cv 계산식 알려줘", null, {}],
  ["fail-open이랑 fail-close 차이", null, {}],
  ["4-20mA HART 원리 설명해줘", null, {}],
  ["PSV 셋압이랑 CDTP 차이가 뭐야", null, {}],
  ["MOV랑 SOV 뭐가 달라", null, {}],
  ["loop check 절차 알려줘", null, {}],
  ["TBE가 뭐의 약자야?", null, {}],
  ["DCS랑 PLC 차이", null, {}],
  ["IP66이랑 IP67 차이 알려줘", null, {}],
  ["Ex d랑 Ex ia 차이", null, {}],
  ["choked flow가 뭐야", null, {}],
  ["orifice beta ratio 보통 얼마로 잡아?", null, {}],
  ["이번 주 계장 그룹 주간업무 현황 어때", null, {}],
  ["Fisher 밸브 PO 일정 지연됐어?", null, {}],
  ["PJT별 납기 현황 보여줘", null, {}],
  ["VOC 처리 현황 알려줘", null, {}],
  ["B 프로젝트 입찰 마감 언제야", null, {}],
  ["계장 광장 열어줘", null, {}],
  ["P&ID 분석 메뉴로 가줘", null, {}],
  ["재무스타그램 켜줘", null, {}],
  ["ROOM SIZE 계산 어디서 해?", null, {}],
  ["택배 스티커 떼줘", null, {}],
  ["PSR 지연 PJT 몇 개?", null, {}],
  ["다음 달 PO 예정 건 몇 개야", null, {}],
  ["통합 업무 이번 주 마감 뭐야", null, {}],
  ["수행 PJT 중에 지연된 거 있어?", null, {}],
  ["PJT 현안 업데이트 언제 했어?", null, {}],
  ["검수 영어로 뭐야?", null, {}],
  ["Please proofread: Kindly be informed that FAT will held on Dec 3.", null, {}],
  ["일본어로 번역: 견적서를 보내주세요", null, {}],
  ["비밀번호 바꾸는 법", null, {}],
  ["폰트 바꿀 수 있어?", null, {}],
  ["ㅋㅋㅋ", null, {}],
  ["좋은 아침이에요", null, {}],
  ["배고프다", null, {}],
  ["로그아웃", null, {}],
  ["Rotork IQ3 액추에이터 사양 알려줘", null, {}],
  ["transmitter turndown ratio 뜻", null, {}],
  ["HART 7이랑 HART 5 차이", null, {}],
  ["이 표 엑셀로 내보내기", null, {}],
  ["김대리 내선번호 뭐야", null, {}],
  ["VDR이 뭐야", null, {}],
  ["KOM 하면 보통 뭐 준비해?", null, {}],
  ["구매 담당자 누구야 이 PJT", null, {}],
  ["입찰 PJT 중 계장 범위 큰 거 알려줘", null, {}],
  ["오늘 며칠이야?", null, {}],
  ["글자 너무 작아", null, {}],
];
