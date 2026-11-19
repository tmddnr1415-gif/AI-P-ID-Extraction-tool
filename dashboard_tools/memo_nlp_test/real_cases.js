// 실제 업무 메일처럼 직접 쓴 시험 메일 — 기대값(g): subj, from, date, time, reqs:[[찾을 말, 기한]], sched:[[날짜, 시각]], items:[], noReq(요청 없음)
module.exports = [
[`[CO2 PJT] Control Valve Datasheet Rev.B 회신 요청
보낸 사람 홍길동/책임/계장ENG그룹/삼성물산 <gd.hong@samsung.com>
받는 사람 김철수/프로/계장ENG그룹/삼성물산 <cs.kim@samsung.com>
보낸 날짜 2026-11-19 (목) 오전 10:23

김철수 프로님, 안녕하세요.
Fisher 에서 Control Valve Datasheet Rev.B 를 송부하였습니다.
첨부 자료 검토 후 11월 25일까지 회신 부탁드립니다.
또한 FAT 일정은 12월 3일 오전 10시 창원 공장에서 진행 예정입니다.

감사합니다.
홍길동 드림`, { subj:'[CO2 PJT] Control Valve Datasheet Rev.B 회신 요청', from:'홍길동', date:'2026-11-19', time:'1023', reqs:[['회신', '2026-11-25']], sched:[['2026-12-03', '1000']], items:['Control Valve'] }],
[`보낸 사람: 이영희 <yh.lee@samsung.com>
보낸 날짜: 2026년 11월 18일 수요일 오후 4:12
받는 사람: 계장ENG그룹
제목: [공지] 11월 정기 안전교육 안내

안녕하세요, 이영희입니다.
11월 정기 안전교육이 아래와 같이 진행됩니다.
- 일시: 11월 26일(목) 오후 2시 ~ 4시
- 장소: 본사 5층 대강당
- 대상: 계장ENG그룹 전원
교육 이수는 필수이니 일정 조정 부탁드립니다.

감사합니다.`, { subj:'[공지] 11월 정기 안전교육 안내', from:'이영희', date:'2026-11-18', time:'1612', sched:[['2026-11-26', '1400']], reqs:[['일정 조정', '']] }],
[`From: John Smith <john.smith@emerson.com>
Sent: Wednesday, November 18, 2026 3:45 PM
To: Kim Chulsoo <cs.kim@samsung.com>
Cc: Sales Team <sales@emerson.com>
Subject: RE: [Ruwais LNG] Control Valve - Revised Quotation

Dear Mr. Kim,

Thank you for your email.
Please find attached our revised quotation for the 42 control valves.
The delivery lead time has been reduced to 16 weeks ARO.
Kindly confirm the commercial terms by November 25, 2026 so that we can reserve the production slot.
We would also like to propose a kick-off meeting on December 2 at 10:00 AM (KST) via Teams.

Best regards,
John Smith
Emerson Automation Solutions
Mobile: +82-10-1234-5678`, { subj:'RE: [Ruwais LNG] Control Valve - Revised Quotation', from:'John Smith', date:'2026-11-18', time:'1545', reqs:[['commercial terms', '2026-11-25']], sched:[['2026-12-02', '1000']], items:['Control Valve'] }],
[`FW: MOV 납기 지연 관련 협조 요청
보낸 사람 박민수/수석/구매팀/삼성물산 <ms.park@samsung.com>
받는 사람 김철수/프로/계장ENG그룹/삼성물산
참조 홍길동/책임/계장ENG그룹/삼성물산
보낸 날짜 2026-11-17 (화) 오후 2:05

수고 많으십니다. 구매팀 박민수입니다.
Rotork 로부터 MOV 납기가 3주 지연된다는 회신을 받았습니다.
현장 설치 일정에 영향이 있는지 검토하시어 이번 주 금요일까지 의견 주시기 바랍니다.
필요 시 다음 주 화요일 오후 3시에 대책 회의를 진행하고자 합니다.

박민수 드림`, { subj:'FW: MOV 납기 지연 관련 협조 요청', from:'박민수', date:'2026-11-17', time:'1405', reqs:[['검토', '2026-11-20']], sched:[['2026-11-24', '1500']], items:['MOV'] }],
[`[Qatar NFE] PSV 성적서 송부의 건
보낸 사람 최지은/프로/계장ENG그룹/삼성물산
받는 사람 김철수/프로/계장ENG그룹/삼성물산
보낸 날짜 2026-11-16 (월) 오전 9:00

안녕하세요.
요청하신 PSV 시험 성적서 송부드립니다.
참고 부탁드립니다.

감사합니다.`, { subj:'[Qatar NFE] PSV 성적서 송부의 건', from:'최지은', date:'2026-11-16', time:'0900', noReq:true, items:['PSV'] }],
[`보낸 사람: 정우성 <ws.jung@samsung.com>
보낸 날짜: 2026년 11월 19일 목요일 오전 8:31
받는 사람: 김철수
제목: 회의 일정 변경 안내

김 프로님,
오늘 오후 2시로 예정된 DCS 인터페이스 회의가 내일 오전 11시로 변경되었습니다.
회의실은 동일하게 3층 소회의실입니다.
변경된 일정 확인 부탁드립니다.

정우성 드림`, { subj:'회의 일정 변경 안내', from:'정우성', date:'2026-11-19', time:'0831', sched:[['2026-11-20', '1100']], reqs:[['확인', '']], items:['DCS/SIS'] }],
[`From: Sarah Lee <sarah.lee@yokogawa.com>
Sent: Thursday, November 19, 2026 11:02 AM
To: cs.kim@samsung.com
Subject: Flow Meter TBE clarification

Hi Kim,

As discussed, we need the following information to finalize the TBE:
1. Process fluid composition for FT-1201
2. Maximum operating pressure
3. Required accuracy class
Could you send these by end of this week?
Our engineer will be available for a call on Monday at 9 AM.

Regards,
Sarah`, { subj:'Flow Meter TBE clarification', from:'Sarah Lee', date:'2026-11-19', time:'1102', reqs:[['send these', '2026-11-20']], sched:[['2026-11-23', '0900']], items:['Flow Meter'] }],
[`RE: [CO2 PJT] Analyzer Shelter 도면 검토
보낸 사람 강하늘/과장/계장ENG그룹/삼성물산
받는 사람 김철수/프로/계장ENG그룹/삼성물산
보낸 날짜 2026-11-12 (목) 오후 5:47

김철수 프로님
요청사항:
1. Analyzer Shelter GA 도면 Rev.0 검토 (11/18까지)
2. Gas Detector 배치도 확인
3. Cable 물량 산출서 송부 (11/20까지)
검토 의견은 마크업 PDF로 회신 부탁드립니다.

강하늘 드림`, { subj:'RE: [CO2 PJT] Analyzer Shelter 도면 검토', from:'강하늘', date:'2026-11-12', time:'1747', reqs:[['GA 도면', '2026-11-18'], ['배치도', ''], ['물량 산출서', '2026-11-20']], items:['Analyzer', 'Cable/JB'] }],
[`안녕하세요, 윤서연 대리입니다.
내일 오전 10시 Valve 업체 미팅이 있습니다.
미팅 전까지 Control Valve 사이징 결과 공유 부탁드립니다.
감사합니다.`, { subj:'', reqs:[['사이징 결과', '']], sched:[['2026-11-20', '1000']], items:['Control Valve'] }],
[`[Hydrogen Plant] 12월 주간회의 일정
보낸 사람 홍길동/책임/계장ENG그룹/삼성물산
받는 사람 계장ENG그룹
보낸 날짜 2026-11-30 (월) 오후 6:10

12월 주간회의는 매주 월요일 오전 9시 30분에 진행합니다.
첫 회의는 12월 7일이며, 각자 진행 현황을 사전에 업데이트해 주시기 바랍니다.`, { subj:'[Hydrogen Plant] 12월 주간회의 일정', from:'홍길동', date:'2026-11-30', time:'1810', reqs:[['진행 현황', '']], sched:[['2026-12-07', '0930']] }],
[`From: Michael Brown <m.brown@rotork.com>
Sent: Monday, November 16, 2026 7:20 AM
To: Kim
Subject: MOV actuator wiring diagram

Dear Kim,
Please be informed that the wiring diagram for the MOV actuators has been uploaded to the portal.
No action is required from your side at this moment.
Best regards,
Michael`, { subj:'MOV actuator wiring diagram', from:'Michael Brown', date:'2026-11-16', time:'0720', noReq:true, items:['MOV'] }],
[`제목: [긴급] Control Valve 사양 변경 확인 요청
보낸 사람: 박민수
보낸 날짜: 2026-11-19 오후 3:30

김철수 프로님,
발주처에서 FV-2101 Control Valve 의 Cv 값을 120에서 150으로 변경 요청하였습니다.
오늘 중으로 변경 가능 여부를 업체에 확인하여 회신 바랍니다.
금액 변동이 있으면 견적도 함께 받아 주세요.`, { subj:'[긴급] Control Valve 사양 변경 확인 요청', from:'박민수', date:'2026-11-19', time:'1530', reqs:[['변경 가능 여부', '2026-11-19'], ['견적', '']], items:['Control Valve'] }],
[`From: "Müller, Anna" <anna.mueller@samson-group.com>
Sent: Tuesday, 17 November 2026 16:05
To: Kim Chulsoo
Subject: Inspection notification - On/Off Valves

Dear Mr. Kim,

The FAT for the on/off valves (Tag: XV-1001~1012) is planned on 1 December 2026 at 09:00 at our Frankfurt workshop.
Please confirm your attendance by 24 November.
Kindly also send the list of witness points.

With kind regards,
Anna Müller`, { subj:'Inspection notification - On/Off Valves', from:'Anna Müller', date:'2026-11-17', time:'1605', reqs:[['attendance', '2026-11-24'], ['witness points', '']], sched:[['2026-12-01', '0900']], items:['On/Off Valve'] }],
[`RE: RE: [Saudi Jafurah] Level transmitter datasheet
보낸 사람 김철수/프로/계장ENG그룹/삼성물산
받는 사람 David Kim <david.kim@endress.com>
보낸 날짜 2026-11-10 (화) 오전 11:15

David,
Thanks for the update. We reviewed the datasheet and have two comments.
Please revise the wetted material to SS316L and resubmit by Nov 13.

-----Original Message-----
From: David Kim <david.kim@endress.com>
Sent: Monday, November 9, 2026 5:00 PM
Subject: [Saudi Jafurah] Level transmitter datasheet
Please review the attached datasheet and send comments by Nov 11.`, { subj:'RE: RE: [Saudi Jafurah] Level transmitter datasheet', from:'김철수', date:'2026-11-10', time:'1115', reqs:[['wetted material', '2026-11-13']], items:['Transmitter'] }],
[`[계장ENG] 11/24(화) 회식 안내
보낸 사람 정우성/책임/계장ENG그룹/삼성물산
보낸 날짜 2026-11-19 (목) 오후 1:00

11월 24일 화요일 저녁 6시 30분 강남역 한식당에서 그룹 회식이 있습니다.
참석 여부를 내일까지 회신 부탁드립니다~`, { subj:'[계장ENG] 11/24(화) 회식 안내', from:'정우성', date:'2026-11-19', time:'1300', reqs:[['참석 여부', '2026-11-20']], sched:[['2026-11-24', '1830']] }],
[`From: Tom Wilson <tom.wilson@flowserve.com>
Sent: Friday, November 13, 2026 9:30 AM
To: Kim
Subject: Pump seal plan question

Kim,
Can you let us know which seal plan (API 53B or 54) is required for P-101A/B?
We need this information by Wednesday next week to keep the schedule.
Thanks,
Tom`, { subj:'Pump seal plan question', from:'Tom Wilson', date:'2026-11-13', time:'0930', reqs:[['seal plan', '']], items:['Pump'] }],
[`보낸 사람: 홍길동
보낸 날짜: 2026-11-19 오전 7:55
제목: 금일 일정

오늘 10시에 TBE 회의, 2시에 PSV 업체 콜 있습니다.
회의 자료는 9시 30분까지 준비 부탁드립니다.`, { subj:'금일 일정', from:'홍길동', date:'2026-11-19', time:'0755', reqs:[['회의 자료', '2026-11-19']], sched:[['2026-11-19', '1000']], items:['PSV'] }],
[`[Ruwais LNG] DCS I/O List Rev.1 배포
보낸 사람 최지은/프로/계장ENG그룹/삼성물산
받는 사람 계장ENG그룹
보낸 날짜 2026-11-11 (수) 오후 4:40

DCS I/O List Rev.1 을 배포합니다.
주요 변경 사항은 아래와 같습니다.
- AI 12점 추가, DO 4점 삭제
- Marshalling Cabinet 1면 추가
각 담당자께서는 11월 18일까지 담당 계기 I/O 를 확인하시고 이상 있으면 알려 주시기 바랍니다.`, { subj:'[Ruwais LNG] DCS I/O List Rev.1 배포', from:'최지은', date:'2026-11-11', time:'1640', reqs:[['I/O', '2026-11-18']], items:['DCS/SIS'] }],
[`Dear Kim,

Greetings from Endress+Hauser!
We are pleased to invite you to our flow measurement seminar on December 10, 2026 at 2:00 PM at COEX Seoul.
Please register by December 3 using the attached form.

Best regards,
Marketing Team`, { subj:'', reqs:[['register', '2026-12-03']], sched:[['2026-12-10', '1400']] }],
[`제목: 출장 보고서 제출 요청
보낸 사람: 박민수 <ms.park@samsung.com>
보낸 날짜: 2026년 11월 20일 금요일 오전 9:10

지난주 Frankfurt FAT 출장 보고서를 다음 주 수요일까지 제출 바랍니다.
경비 정산도 같은 날까지 마감입니다.`, { subj:'출장 보고서 제출 요청', from:'박민수', date:'2026-11-20', time:'0910', reqs:[['출장 보고서', '2026-11-25']] }],
];
