const SPECS = /*__SPECS__*/null;
const KB = /*__KB__*/null;
const A = [
 {id:"dcs",n:"DCS",g:"제어·안전",f:"DCS",sc:"Controller·I/O·HMI·Network",q:["DCS I/O 여유율은 어떻게 잡나요?","Controller 이중화 요구사항은?","DCS FAT 에서 확인할 것은?","DCS MR 작성해줘"]},
 {id:"ips",n:"IPS",g:"제어·안전",f:"IPS",s:1,sc:"SIS/ESD·SIL·Bypass",q:["IPS 와 DCS 독립성은 왜 필요한가요?","2oo3 투표는 언제 쓰나요?","Bypass/Reset 관리 기준은?","Proof test 주기는?"]},
 {id:"mms",n:"MMS",g:"제어·안전",f:"MMS",s:1,sc:"진동·축변위·API 670",q:["Proximity probe 는 왜 X/Y 두 개를 다나요?","Keyphasor 역할은?","진동 Trip voting 은?","MMS 와 DCS Interface 는?"]},
 {id:"ccs",n:"CCS",g:"제어·안전",f:"CCS",sc:"Anti-surge·성능 제어",q:["Anti-surge 제어 원리는?","Anti-surge valve 응답 시간 요구는?","Surge line 과 control line 차이는?","CCS 와 DCS 경계는?"]},
 {id:"fgs",n:"FGS",g:"제어·안전",f:"FGS",s:1,sc:"화재·가스 감지",q:["가스 감지기 배치 기준은?","Flame detector 선정 시 유의점은?","FGS voting 로직은?","Cause & Effect 검토 포인트는?"]},
 {id:"ball-valve",n:"Ball Valve",g:"밸브",f:"Ball Valve",s:1,sc:"ESDV·SDV·BDV·XV",q:["ESDV Spec 검토 시 유의사항은?","ESDV stroke time 기준은?","PST 는 왜 필요한가요?","BDV 와 ESDV 의 Fail 방향 차이는?"]},
 {id:"globe-valve",n:"Globe Valve",g:"밸브",f:"Globe Valve",sc:"Control·PRV·MOV",q:["Control valve Cv 사이징 시 유의점은?","캐비테이션은 어떻게 막나요?","Shutoff class 선정 기준은?","Positioner 사양에서 볼 것은?"]},
 {id:"butterfly-valve",n:"Butterfly Valve",g:"밸브",f:"Butterfly Valve",sc:"Control·MOV",q:["Triple offset 은 언제 쓰나요?","Butterfly valve 토크 마진은?","Butterfly 를 control 용으로 쓸 때 주의점은?","Lug 와 Wafer 차이는?"]},
 {id:"psv",n:"PSV",g:"밸브",f:"PSV",s:1,sc:"Conventional·Bellows·Pilot",q:["Bellows PSV 는 언제 쓰나요?","Set pressure 와 CDTP 차이는?","PSV 입구 압력손실 3% 규칙은?","PSV MR 작성해줘"]},
 {id:"field-gauge",n:"Field Gauge",g:"계기·자재",f:"Field Gauge",sc:"압력·온도·레벨 지시계",q:["압력계 Range 선정 기준은?","Thermowell wake frequency 계산이 왜 필요한가요?","Liquid filled gauge 는 언제 쓰나요?","Siphon 과 snubber 차이는?"]},
 {id:"transmitter",n:"Transmitter",g:"계기·자재",f:"Transmitter",sc:"압력·DP·온도·레벨",q:["DP transmitter manifold 구성은?","Remote seal 은 언제 쓰나요?","SIL 인증 transmitter 선정 시 유의점은?","Impulse line 설치 시 주의점은?"]},
 {id:"bulk-material",n:"Instrument Bulk",g:"계기·자재",f:"Bulk Material",sc:"Tubing·Fitting·Gland·JB",q:["Instrument tubing 재질 선정은?","Cable gland Ex d 와 Ex e 차이는?","Junction box 검토 포인트는?","Bulk MTO 여유율은?"]},
 {id:"mr-writer",n:"MR 작성",g:"지원",sc:"Item별 MR → Word(.docx)",q:["ESDV MR 작성해줘","PSV MR 작성해줘","Transmitter MR 작성해줘"]},
 {id:"anatomy-viewer",n:"Anatomy 뷰어",g:"지원",sc:"Item 3D 부품 도해",q:["Ball Valve 부품 보여줘","PSV 구조 보여줘","DCS 캐비닛 보여줘"]},
 {id:"fin-dashboard",n:"공시 재무제표",g:"지원",sc:"DART OpenAPI 원본 인용",q:["삼성물산 실적 알려줘","현대건설 재무제표","DL이앤씨 매출"]}
];
const byId=Object.fromEntries(A.map(a=>[a.id,a]));
const state={}; const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let cur="orch"; const threads={}; const unread={};

/* ---- 좌측 목록 ---- */
function renderList(){
  let h="",g="";
  const row=(id,label,a)=>{const st=state[id]||"idle";return `<div class="ag ${st} ${cur===id?"sel":""}" data-id="${id}"><span class="dot"></span>${label}${unread[id]?`<span class="un">${unread[id]}</span>`:""}${a&&a.s?'<span class="sf">안전</span>':''}<span class="st">${st==="run"?"동작 중":st==="done"?"완료":""}</span></div>`};
  h+=`<h4>ORCHESTRATOR</h4>`+row("orch","오케스트레이터 (전체)");
  for(const a of A){if(a.g!==g){g=a.g;h+=`<h4>${g}</h4>`}h+=row(a.id,a.n,a)}
  $("#agents").innerHTML=h;
  document.querySelectorAll(".ag").forEach(e=>e.onclick=()=>select(e.dataset.id));
}
/* ---- 조직도 ---- */
const POS={};
function buildOrg(){
  const svg=$("#org");let s="";const NW=118,NH=36;
  const cols=[["제어·안전",["dcs","ips","mms","ccs","fgs"]],["밸브",["ball-valve","globe-valve","butterfly-valve","psv"]],["계기·자재",["field-gauge","transmitter","bulk-material"]],["지원",["mr-writer","anatomy-viewer","fin-dashboard"]]];
  POS.user=[205,6,120,32];POS.gate=[395,6,126,32];POS.orch=[185,70,160,38];
  cols.forEach(([gn,ids],ci)=>{const x=6+ci*130;ids.forEach((id,ri)=>{POS[id]=[x,190+ri*46,NW,NH]})});
  const c=id=>[POS[id][0]+POS[id][2]/2,POS[id][1]+POS[id][3]/2];
  const edge=(a,b,key)=>{const [x1]=c(a),[x2]=c(b);const ya=POS[a][1]+POS[a][3],yb=POS[b][1];const my=(ya+yb)/2;return `<path class="edge" id="e-${key}" d="M${x1} ${ya} C${x1} ${my} ${x2} ${my} ${x2} ${yb}"/>`};
  s+=edge("user","orch","user");
  s+=`<path class="edge" id="e-gate" stroke-dasharray="3 3" d="M${POS.orch[0]+POS.orch[2]} ${POS.orch[1]+19} L${POS.gate[0]} ${POS.gate[1]+16}"/>`;
  for(const [,ids] of cols)for(const id of ids)s+=edge("orch",id,id);
  cols.forEach(([gn],ci)=>{s+=`<text x="${6+ci*130}" y="178" font-size="11" fill="#888" font-weight="700">${gn}</text>`});
  const node=(id,label,cls="")=>{const [x,y,w,h]=POS[id];return `<g class="node ${cls}" id="n-${id}" style="cursor:pointer"><rect x="${x}" y="${y}" width="${w}" height="${h}"/><text x="${x+w/2}" y="${y+h/2}">${label}</text></g>`};
  s+=node("user","사용자 (I&C 엔지니어)");s+=node("gate","Human Gate","safety");s+=node("orch","오케스트레이터");
  for(const a of A)s+=node(a.id,a.n+(a.s?" ★":""),(a.s?"safety ":"")+(a.dash?"dash":""));
  s+=`<text x="6" y="${190+5*46+6}" font-size="10.5" fill="#888">★ 안전 계통(초안, 담당자 확인 필수) · 노드 클릭 = 해당 Agent 와 채팅</text>`;
  svg.innerHTML=s;
  svg.querySelectorAll(".node").forEach(n=>{const id=n.id.slice(2);if(byId[id]||id==="orch")n.onclick=()=>select(id)});
}
function paint(){
  for(const id of ["user","orch","gate",...A.map(a=>a.id)]){
    const n=document.getElementById("n-"+id);if(!n)continue;const st=state[id]||"idle";
    n.classList.remove("run","done");if(st!=="idle")n.classList.add(st);
    const e=document.getElementById("e-"+id);if(e)e.classList.toggle("on",st==="run");
  }
  renderList();
}
const setS=(id,st)=>{state[id]=st;paint()};

/* ---- 스레드(Agent 별 채팅) ---- */
function thread(id){
  if(!threads[id]){const d=document.createElement("div");d.className="thread";d.style.display="none";$("#msgs").appendChild(d);threads[id]=d;
    const a=byId[id];
    if(id==="orch")addMsg(id,"안녕하세요. 12개 Item 에이전트를 조율하는 <b>오케스트레이터</b>입니다. 무엇이든 물어보시면 담당 에이전트에게 나눠 맡기고 답을 모아 드립니다. 왼쪽에서 Agent 를 고르면 그 Agent 와 <b>1:1 채팅</b>도 할 수 있어요.<br><span class='src'>지식: 웹 조사 Q&amp;A(Item별 *_Knowledge.md) + Item Spec 초안. 로컬 검색형 답변이며 수치는 프로젝트 Spec 대조 전까지 미확인입니다.</span>","sys");
    else{const n=(KB&&a.f&&KB[a.f]||[]).filter(r=>r.k==="kb").length;
      addMsg(id,`<div class="who">${esc(a.n)} 에이전트</div>안녕하세요, <b>${esc(a.n)}</b> 담당 에이전트입니다 (${esc(a.sc||"")}). ${a.f?`웹 조사 Q&amp;A <b>${n}</b>건과 <code>${esc(SPECS[a.f]?.file||"")}</code> 를 근거로 답합니다.`:""}${a.s?"<br><span class='gate' style='display:inline-block;margin-top:6px'>⚠ 안전 계통 — 모든 답변은 초안이며 담당자 확인이 필요합니다.</span>":""}<br>아래 질문 예시를 누르거나 자유롭게 물어보세요.`,"a")}}
  return threads[id];
}
function addMsg(tid,html,cls=""){const d=document.createElement("div");d.className="m "+cls;d.innerHTML=html;thread(tid).appendChild(d);if(tid!==cur){unread[tid]=(unread[tid]||0)+1;renderList()}else $("#msgs").scrollTop=1e9;bindTags(d);return d}
function select(id){
  cur=id;unread[id]=0;for(const k in threads)threads[k].style.display="none";thread(id).style.display="flex";
  const a=byId[id];
  $("#chead").innerHTML=id==="orch"?`<b>오케스트레이터</b><span class="sub">전체 질의 → Item 에이전트 자동 분류·병렬 호출·병합</span>`:`<b>${esc(a.n)} 에이전트</b><span class="sub">${esc(a.sc||"")} · 1:1 채팅 (오케스트레이터 경유 기록)</span>${a.s?'<span class="badge w">안전 계통</span>':""}<span class="sp"></span>${V3D.MODELS[id]?`<button class="btn" style="margin:0" onclick="showModel('${id}',true)">3D 부품 보기</button>`:""}`;
  const qs=id==="orch"?["ESDV Spec 검토 시 유의사항은?","ESDV 와 PSV 를 같이 검토해줘","PRV 선정 기준은?","DCS 와 IPS Interface 는?","PSV MR 작성해줘"]:a.q||[];
  $("#chips").innerHTML=qs.map(t=>`<span class="chip">${esc(t)}</span>`).join("");
  document.querySelectorAll("#chips .chip").forEach(c=>c.onclick=()=>handle(c.textContent));
  $("#q").placeholder=id==="orch"?"예: ESDV Spec 검토 시 유의사항은? / PSV MR 작성해줘":`${a.n} 에이전트에게 질문하기…`;
  if(V3D.MODELS[id])showModel(id,true);
  renderList();$("#msgs").scrollTop=1e9;
}

/* ---- 분류 ---- */
const RULES=[
 [/ESDV|SDV|BDV|\bXV\b|볼\s*밸브|ball/i,"ball-valve"],[/글로브|globe|control\s*valve|조절\s*밸브|컨트롤\s*밸브|cv\s*사이징/i,"globe-valve"],[/버터플라이|butterfly/i,"butterfly-valve"],
 [/PSV|안전\s*밸브|릴리프|relief|PVRV/i,"psv"],[/\bDCS\b/i,"dcs"],[/\bIPS\b|\bSIS\b|\bESD\b(?!V)/i,"ips"],[/\bMMS\b|진동|vibration|API\s*670/i,"mms"],[/\bCCS\b|서지|surge|컴프레서|압축기/i,"ccs"],[/\bFGS\b|화재|가스\s*감지|F&G|flame/i,"fgs"],
 [/게이지|gauge|압력계|온도계|thermowell/i,"field-gauge"],[/트랜스미터|transmitter|전송기|\bPT\b|\bDPT\b/i,"transmitter"],[/자재|벌크|bulk|instrument\s*bulk|tubing|튜빙|gland|글랜드|hook-?up|케이블|junction|\bJB\b/i,"bulk-material"],[/재무|공시|실적/i,"fin-dashboard"]
];
function classify(q){
  if(/\bPRV\b/i.test(q)&&!/글로브|globe|PSV|안전밸브/i.test(q))return{ask:"PRV 는 Globe Valve 의 압력조절밸브(자력식)인가요, 아니면 안전밸브(PSV)를 뜻하나요?",opts:[["Globe Valve(PRV)","globe-valve"],["PSV(안전밸브)","psv"]]};
  if(/\bMOV\b/i.test(q)&&!/글로브|globe|버터플라이|butterfly/i.test(q))return{ask:"MOV 는 Globe Valve 용인가요, Butterfly Valve 용인가요?",opts:[["Globe Valve(MOV)","globe-valve"],["Butterfly Valve(MOV)","butterfly-valve"]]};
  const hit=[];for(const [re,id] of RULES)if(re.test(q)&&!hit.includes(id))hit.push(id);
  return{items:hit,mr:/\bMR\b|material\s*requisition|구매\s*요청|자재\s*요청/i.test(q),viz:/부품|구조|도해|anatomy|점멸|3D|보여줘/i.test(q)};
}

/* ---- 검색형 답변(지식 베이스 + Spec) ---- */
const STOP=new Set("은 는 이 가 을 를 의 에 에서 로 으로 와 과 도 및 시 때 대해 대한 관련 알려줘 알려 주세요 해줘 해주세요 무엇 뭐 뭐야 뭔가요 어떻게 왜 인가요 있나요 하나요 사항 경우 좀 무엇인가요 언제 쓰나요 필요한가요 같이 the and for what how why spec".split(" "));
const toks=q=>q.toLowerCase().replace(/[?？!.,()\[\]"'`~]/g," ").split(/\s+/).map(t=>t.replace(/(은|는|이|가|을|를|의|에서|에|으로|로|와|과|도|이란|란|인가요|나요|은요|는요)$/,"")).filter(t=>t.length>=2&&!STOP.has(t));
function search(f,q){
  const rows=(KB&&KB[f])||[];const T=toks(q);if(!T.length)return[];
  const intent=/유의|주의|검토|실수|체크|pitfall/i.test(q)?/유의|검토|실수|체크|checklist|주의/i:null;
  const out=[];
  for(const r of rows){
    const head=(r.q+" "+r.kw).toLowerCase(),body=(r.a+" "+r.topic).toLowerCase();let sc=0;
    for(const t of T){const lat=/^[\x00-\x7f]+$/.test(t);if(head.includes(t))sc+=lat?4:3.2;else if(body.includes(t))sc+=lat?2:1.6;else if(!lat&&t.length>=3){for(let i=0;i<t.length-1;i++)if(head.includes(t.slice(i,i+2)))sc+=0.5}}
    const ql=r.q.toLowerCase();let qh=0;for(const t of T)if(ql.includes(t))qh++;sc+=qh*1.8+(qh>=2?3:0);
    if(intent&&intent.test(r.topic+" "+r.q))sc+=2.5;
    if(r.k==="kb")sc*=1.25;
    if(sc>0)out.push([sc,r]);
  }
  return out.sort((a,b)=>b[0]-a[0]);
}
const ALIAS={"액추에이터":"actuator","구동기":"actuator","솔레노이드":"solenoid","sov":"solenoid","리밋":"limit-switch","limit":"limit-switch","스프링":"spring","시트":"seat","seat":"seat","볼":"ball","스템":"stem","stem":"stem","플랜지":"process-conn","flange":"process-conn","포지셔너":"positioner","positioner":"positioner","pst":"pst","디스크":"disc","disc":"disc","노즐":"nozzle","nozzle":"nozzle","bonnet":"bonnet","보닛":"bonnet","trim":"trim","트림":"trim","yoke":"yoke","shaft":"shaft","샤프트":"shaft","lever":"lever","매니폴드":"manifold","manifold":"manifold","글랜드":"gland","gland":"gland","트레이":"tray","tray":"tray","튜빙":"tubing","tubing":"tubing","fitting":"fitting","피팅":"fitting","junction":"jb","정션":"jb","컨트롤러":"controller","controller":"controller","i/o":"io","hmi":"hmi","network":"network","네트워크":"network","psu":"psu","전원":"psu","terminal":"terminal","marshalling":"terminal","bypass":"bypass-panel","바이패스":"bypass-panel","reset":"bypass-panel","프로브":"probe","probe":"probe","keyphasor":"keyphasor","rtd":"rtd","bearing":"bearing","베어링":"bearing","axial":"probe-axial","thrust":"probe-axial","anti-surge valve":"asv","asv":"asv","recycle":"recycle-line","flow element":"flow-element","orifice":"flow-element","감지기":"gas-detector","gas detector":"gas-detector","flame":"flame-detector","open path":"op-gas","mac":"mac","call point":"mac","beacon":"beacon","horn":"beacon","dial":"dial","다이얼":"dial","pointer":"needle","bourdon":"case","blow-out":"blowout","socket":"socket","소켓":"socket","thermowell":"process-conn","housing":"housing","하우징":"housing","lcd":"display","sensor":"sensor","센서":"sensor","conduit":"conduit","impulse":"process-conn","cabinet":"cabinet","캐비닛":"cabinet","compressor":"compressor","압축기":"compressor","driver":"driver","케이블":"cable","cable":"cable"};
function partsFor(id,text,given){
  const m=V3D.MODELS[id];if(!m)return[];const set=new Set((given||[]).filter(p=>m.parts[p]));const tl=text.toLowerCase();
  for(const [k,p] of Object.entries(ALIAS))if(m.parts[p]&&tl.includes(k))set.add(p);
  return [...set].slice(0,4);
}
const tagHtml=(id,ps)=>ps.map(p=>`<span class="tag" data-i="${id}" data-p="${p}" title="${esc(V3D.MODELS[id].parts[p])}">part:${p}</span>`).join("");
const first=(t,n=150)=>{const s=t.split(/(?<=[.다요])\s/)[0];return s.length>n?s.slice(0,n)+"…":s};
const sents=t=>t.split(/(?<=[.다요])\s+(?=[^\s])/).map(x=>x.trim()).filter(x=>x.length>1);
function compose(a,q,mode){
  const hits=search(a.f,q);const kb=hits.filter(h=>h[1].k==="kb"),sp=hits.filter(h=>h[1].k==="spec");
  let h=`<div class="who">${esc(a.n)} 에이전트${mode==="via"?" · 오케스트레이터 경유":""}</div>`;
  if(a.s)h+=`<span class="gate">⚠ 초안, 담당자 확인 필수 — 확정 판단은 담당 엔지니어·SIS 담당자가 합니다</span>`;
  const top=kb[0],ok=top&&top[0]>=4;
  if(!ok&&!(sp.length&&sp[0][0]>=2)){
    const sug=((KB&&KB[a.f])||[]).filter(r=>r.k==="kb").sort(()=>Math.random()-.5).slice(0,3);
    h+=`<div class="concl">질문과 직접 맞는 근거를 찾지 못했습니다 → <b>미확인</b></div><p>추측해서 답하지 않을게요. 아래 질문은 근거를 갖고 답할 수 있습니다.</p><ol>`+sug.map(r=>`<li><span class="chip ask">${esc(r.q)}</span></li>`).join("")+`</ol>`;
    return {html:h,hits:0};
  }
  if(ok){
    const r=top[1];const ss=sents(r.a).map(x=>x.replace(/\(초안, 담당자 확인 필수\)\.?$/,"").trim()).filter(Boolean);
    h+=`<div class="concl">💡 ${esc(ss[0]||r.a)}</div>`;
    h+=`<div class="sec">Q. ${esc(r.q)}</div>`;
    if(ss.length>1)h+=`<ol class="pts">${ss.slice(1).map(x=>`<li>${esc(x)}</li>`).join("")}</ol>`;
    const pt=partsFor(a.id,r.a+" "+r.q,r.parts);if(pt.length)h+=`<div class="tagrow">관련 부품 ${tagHtml(a.id,pt)}</div>`;
    const more=kb.slice(1,4).filter(x=>x[0]>=top[0]*0.45);
    if(more.length)h+=`<div class="sec">같이 보면 좋은 점</div><table class="mt"><tr><th style="width:34%">항목</th><th>요점</th></tr>`+more.map(([,x])=>`<tr><td><b>${esc(x.q)}</b></td><td>${esc(first(x.a,140))}${tagHtml(a.id,partsFor(a.id,x.a+" "+x.q,x.parts).slice(0,2))}</td></tr>`).join("")+`</table>`;
  }else h+=`<div class="concl">📄 웹 조사 Q&amp;A 에는 딱 맞는 내용이 없어, Item Spec 초안에서 관련 조항을 찾았습니다.</div>`;
  const sps=sp.slice(0,ok?3:5).filter(x=>x[0]>=2);
  if(sps.length)h+=`<div class="sec">프로젝트 Spec 초안 대조 <span class="src">${esc(SPECS[a.f].file)}</span></div><table class="mt"><tr><th style="width:30%">절</th><th>내용</th></tr>`+sps.map(([,x])=>`<tr><td>§ ${esc(x.topic)}</td><td>${esc(x.a.length>200?x.a.slice(0,200)+"…":x.a)}${tagHtml(a.id,partsFor(a.id,x.a,[]).slice(0,2))}</td></tr>`).join("")+`</table>`;
  const srcs=[];for(const [,x] of kb.slice(0,4))for(const s of x.src)if(!srcs.some(y=>y.u===s.u))srcs.push(s);
  h+=`<div class="sec">출처 · 확인</div><ul class="srcl">${srcs.slice(0,4).map(s=>`<li><a href="${esc(s.u)}" target="_blank" rel="noopener">${esc(s.t)}</a></li>`).join("")}${sps.length?`<li>${esc(SPECS[a.f].file)} (일반 EPC 기준 초안)</li>`:""}<li>수치·조항은 프로젝트 Spec·Datasheet 대조 전까지 <b>미확인</b> · ${a.s?"승인: 담당 계측 엔지니어 + SIS 담당자 → 팀 리드":"원본 대조 후 사람 승인"}</li></ul>`;
  const nxt=ok&&kb.slice(4,10).find(x=>x[1]!==top[1]);
  if(nxt)h+=`<div class="next">다음 질문 제안 <span class="chip ask">${esc(nxt[1].q)}</span></div>`;
  return {html:h,hits:kb.length+sps.length};
}

/* ---- 진행 ---- */
function logLine(t){$("#log").textContent+="\n"+new Date().toLocaleTimeString("ko-KR")+"  "+t}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let busy=false;
async function runPlan(steps){
  const total=steps.reduce((s,x)=>s+x.ms,0);const t0=performance.now();
  const tick=setInterval(()=>{const el=Math.min(performance.now()-t0,total);setBar(el/total,el,total)},80);
  for(let i=0;i<steps.length;i++){const s=steps[i];$("#plab").innerHTML=`<b>${i+1}/${steps.length}</b> ${s.label}`;(s.ids||[]).forEach(id=>setS(id,"run"));await sleep(s.ms);(s.ids||[]).forEach(id=>setS(id,id==="orch"?"run":"done"));if(s.fn)s.fn()}
  clearInterval(tick);setBar(1,total,total);$("#plab").innerHTML=`<b>완료</b> · ${steps.length}단계`;
}
function setBar(p,el,total){$("#barfill").style.width=(p*100).toFixed(1)+"%";$("#ppct").textContent=Math.round(p*100)+"%";$("#peta").textContent=p>=1?"총 "+(total/1000).toFixed(1)+"s":"남은 약 "+((total-el)/1000).toFixed(1)+"s"}
function resetStates(){for(const k in state)delete state[k];paint()}
const done=()=>{["user","orch","gate",...A.map(a=>a.id)].forEach(id=>{if(state[id]==="run")state[id]="done"});paint();busy=false;$("#go").disabled=false};

async function handle(q){
  if(busy)return;busy=true;$("#go").disabled=true;
  const tid=cur;addMsg(tid,esc(q),"u");logLine(`Q[${tid}]: `+q);resetStates();
  const me=byId[tid];let items=[],mr=false,viz=false,fin=false;
  if(me&&me.f){items=[me];const c=classify(q);mr=c.mr;viz=c.viz}
  else{
    const c=classify(q);
    if(c.ask){setS("user","done");setS("orch","run");await sleep(400);setS("orch","done");
      const d=addMsg(tid,esc(c.ask)+"<br>"+c.opts.map(([l,id])=>`<button class="btn" data-pick="${id}">${l}</button>`).join(" "),"a");
      d.querySelectorAll("[data-pick]").forEach(b=>b.onclick=()=>{busy=false;handle(q.replace(/\bPRV\b|\bMOV\b/i,m=>m+" "+byId[b.dataset.pick].n))});
      $("#plab").textContent="사용자 확인 대기 (분류 모호)";busy=false;$("#go").disabled=false;return}
    fin=c.items.includes("fin-dashboard");items=c.items.filter(i=>i!=="fin-dashboard").map(i=>byId[i]);mr=c.mr||tid==="mr-writer";viz=c.viz||tid==="anatomy-viewer";
    if(tid==="fin-dashboard"){fin=true;items=[];mr=false;viz=false}
    if(!items.length&&!fin){addMsg(tid,tid==="mr-writer"?"어느 Item 의 MR 을 만들까요? (예: ESDV MR 작성해줘)":tid==="anatomy-viewer"?"어느 Item 을 볼까요? (예: PSV 구조 보여줘)":"어느 Item 에 대한 질문인지 알아듣지 못했어요. ESDV, PSV, DCS, Transmitter 처럼 Item 이름을 넣어 다시 물어봐 주세요. 왼쪽에서 Agent 를 골라 1:1 로 물어보셔도 됩니다.","a");done();$("#plab").textContent="대기 중";return}
  }
  const safety=items.some(a=>a.s);const steps=[];
  steps.push({label:me&&me.f?`오케스트레이터 → ${me.n} 직접 전달`:"질의 분류(Item·작업 유형 식별)",ms:me&&me.f?400:700,ids:["user","orch"]});
  steps.push({label:"Item 에이전트 검색·답변 · "+[...items.map(a=>a.n),...(fin?["공시 재무제표"]:[])].join(", ")+(items.length>1?" (병렬)":""),ms:1200+items.length*400,ids:[...items.map(a=>a.id),...(fin?["fin-dashboard"]:[])]});
  if(items.length>1)steps.push({label:"결과 병합(ic-concise-answer)",ms:500,ids:["orch"]});
  if(safety)steps.push({label:"안전 게이트(ic-safety-gate)",ms:500,ids:["orch","gate"]});
  const dev=items.find(a=>V3D.MODELS[a.id]);
  if(dev)steps.push({label:"Anatomy 3D 부품 태그 연결",ms:400,ids:["anatomy-viewer"]});
  if(mr)steps.push({label:"MR 필드 → .docx 초안(ic-mr-writer)",ms:1000,ids:["mr-writer"]});
  steps.push({label:"응답 · 로그 기록",ms:300,ids:["orch"],fn:()=>{
    if(fin)finAnswer(tid,q);
    for(const a of items){
      const r=mr&&!/검토|유의|기준|왜|어떻게/.test(q)?{html:`<div class="who">${esc(a.n)} 에이전트</div>${a.s?'<span class="gate">⚠ 초안, 담당자 확인 필수</span>':""}<p><b>${esc(a.n)} MR 초안</b>을 이 프로그램의 Item별 MR 포맷으로 준비했어요. 오른쪽 <b>MR 미리보기</b> 탭에서 Word(.docx)를 내려받을 수 있습니다. 값은 Datasheet 대조 전이라 노란색 <b>미확인</b>으로 표시되고, 승인란은 비워 두었습니다.</p>`}:compose(a,q,tid==="orch"?"":"direct");
      addMsg(tid,r.html,"a");
      if(tid==="orch")addMsg(a.id,`<div class="src">오케스트레이터 경유 질의: “${esc(q)}”</div>`+r.html,"a");
    }
    logLine("A: "+items.map(a=>a.n).join(",")+(safety?" [SAFETY]":""));
    if(dev){showModel(dev.id,viz)}
    if(mr&&items.length){fillMR(items,safety);if(!dev||!viz)selTab("mrp")}
  }});
  await runPlan(steps);done();
}
function bindTags(root){root.querySelectorAll(".tag").forEach(t=>t.onclick=()=>{if(t.dataset.i){showModel(t.dataset.i,true);setTimeout(()=>V.blink(t.dataset.p),60)}});root.querySelectorAll(".chip.ask").forEach(c=>c.onclick=()=>handle(c.textContent))}
function selTab(id){document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("on",t.dataset.t===id));document.querySelectorAll(".pane").forEach(p=>p.classList.toggle("on",p.id===id));if(id==="anap")setTimeout(()=>V.kick(),30)}
document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>selTab(t.dataset.t));
function fillMR(items,safety){
  const rows=items.flatMap(a=>(SPECS[a.f]?.items||[]).slice(0,6).map(t=>`<tr><td>${a.n}</td><td>${esc(t)}</td><td style="background:#FFF6B0">미확인</td><td>${esc(SPECS[a.f].file)}</td></tr>`)).join("");
  $("#mrbox").className="";$("#mrbox").innerHTML=`<div style="font-weight:700;margin-bottom:6px">Material Requisition ${safety?'<span class="badge w">DRAFT · 안전 계통</span>':'<span class="badge">DRAFT</span>'}</div>
  <table><tr><th>Item</th><th>요구 항목</th><th>값</th><th>출처</th></tr>${rows}</table>
  <div style="margin:8px 0">${[...new Set(items.map(a=>a.f.replace(/ /g,"")))].map(k=>`<a class="chip" style="text-decoration:none;display:inline-block;margin-right:6px" href="../output/MR_${k}_latest_DRAFT.docx" download>⬇ ${k} MR (.docx)</a>`).join("")}</div>
  <div class="note">Item별 MR 포맷(<code>data/mr/MR_Format_*.json</code>)으로 만든 Word 초안입니다. 값 채움은 Claude Code 의 ic-mr-writer(<code>python data/mr/make_mr.py {Item} values.json</code>). 승인 전 확정·발송하지 않습니다.</div>`;
}

/* ---- 공시 재무제표 (app/server.py → DART OpenAPI, 키는 서버 코드가 .env/환경변수에서 읽음) ---- */
const eok=v=>{const t=String(v||"").replace(/,/g,"");if(!/^-?\d+$/.test(t))return v||"-";return Math.round(Number(t)/1e8).toLocaleString("ko-KR")};
const comma=v=>/^-?\d+$/.test(String(v||""))?String(v).replace(/\B(?=(\d{3})+(?!\d))/g,","):v;
async function finAnswer(tid,q){
  const d=addMsg(tid,`<div class="who">공시 재무제표 에이전트</div>DART 공시를 조회하고 있어요…`,"a");
  if(!location.protocol.startsWith("http")){d.innerHTML=`<div class="who">공시 재무제표 에이전트</div>지금은 파일로 열린 화면이라 DART 에 접속할 수 없습니다. 터미널에서 <code>python app/server.py</code> 를 실행한 뒤 <b>http://127.0.0.1:8790</b> 으로 접속해 주세요. (API Key 는 서버 코드가 <code>.env</code>/환경변수에서 읽고, 화면에는 표시하지 않습니다.)`;return}
  try{
    const r=await (await fetch("/api/fin/ask?q="+encodeURIComponent(q))).json();
    if(!r.ok){d.innerHTML=`<div class="who">공시 재무제표 에이전트</div>${esc(r.msg)}`;return}
    const rows=r.rows.map(x=>x.missing?`<tr><td>${x.label}</td><td colspan="2" style="background:#FFF6B0">미확인(계정 없음)</td></tr>`:`<tr><td>${esc(x.label)}<div class="src">${esc(x.sj_nm||"")} · ${esc(x.account_nm||"")}</div></td><td style="text-align:right;font-variant-numeric:tabular-nums"><span title="원본: ${esc(comma(x.thstrm))} 원">${esc(eok(x.thstrm))}</span></td><td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--sub)"><span title="원본: ${esc(comma(x.frmtrm))} 원">${esc(eok(x.frmtrm))}</span></td></tr>`).join("");
    const t0=r.rows.find(x=>!x.missing);finSync(r.corp);
    d.innerHTML=`<div class="who">공시 재무제표 에이전트</div><div class="concl">📊 ${esc(r.corp.corp_name)}${r.corp.stock_code?` (${esc(r.corp.stock_code)})`:""} · ${esc(r.year)}년 ${esc(r.report)} · ${esc(r.fs)} 기준</div>
    <ol class="pts"><li>단위는 <b>억원</b>입니다(DART 원 단위 원본 ÷ 1억, 반올림). 숫자에 마우스를 올리면 원 단위 원본이 보입니다.</li><li>상세 화면(재무제표·주가·사업부문·수주)은 오른쪽 <b>재무 대시보드</b> 탭과 새 창에 자동으로 열립니다.</li></ol>
    <table class="mt"><tr><th>계정</th><th style="text-align:right">${esc(t0?.thstrm_nm||"당기")}</th><th style="text-align:right">${esc(t0?.frmtrm_nm||"전기")}</th></tr>${rows}</table>
    <div class="src">(단위: 억원) · 원본 통화 ${esc(t0?.currency||"KRW")} · 출처: ${esc(r.source)} · <a href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${encodeURIComponent(r.rcept_no)}" target="_blank" rel="noopener">DART 원문 ${esc(r.rcept_no)}</a> · 키: ${esc(r.key_src)}<br>※ 계측제어 지식과 섞지 않습니다. 분석·추정이 필요하면 원문을 확인하세요.</div>`;
    logLine("A[fin]: "+r.corp.corp_name+" "+r.year);
  }catch(e){d.innerHTML=`<div class="who">공시 재무제표 에이전트</div>서버 응답을 받지 못했습니다(미확인): ${esc(e.message)}`}
}

const finBC=("BroadcastChannel" in window)?new BroadcastChannel("ic-fin"):null;let finWin=null,finLoaded=false;
function finURL(c){return "/fin/"+(c?"?"+new URLSearchParams({corp_code:c.corp_code,corp_name:c.corp_name,stock_code:c.stock_code||""}):"")}
function finSync(c){
  const fr=$("#finframe");
  if(!finLoaded){fr.src=finURL(c);finLoaded=true}else if(finBC)finBC.postMessage({type:"pick",corp:c});else try{fr.contentWindow.postMessage({type:"pick",corp:c},location.origin)}catch(e){}
  if(finLoaded&&finBC&&fr.src.indexOf("corp_code")<0)finBC.postMessage({type:"pick",corp:c});
  if(!finBC&&finWin&&!finWin.closed){try{finWin.postMessage({type:"pick",corp:c},location.origin)}catch(e){}}
  $("#finst").textContent="연동: "+c.corp_name+" · "+new Date().toLocaleTimeString("ko-KR");selTab("finp");window.__finLast=c;
}
$("#finpop").onclick=()=>{if(!location.protocol.startsWith("http")){alert("python app/server.py 실행 후 http://127.0.0.1:8790 에서 사용하세요.");return}finWin=window.open(finURL(window.__finLast),"ic-fin-dash","width=1280,height=860")};
document.querySelector('.tab[data-t="finp"]').addEventListener("click",()=>{if(!finLoaded&&location.protocol.startsWith("http")){$("#finframe").src=finURL(window.__finLast);finLoaded=true}});

/* ---- 3D Anatomy ---- */
const tip=$("#v3tip");
const V=V3D.Viewer($("#v3"),{
  onHover:(p,x,y)=>{const m=V.model;if(!p||!m){tip.style.display="none";return}tip.textContent=m.parts[p]+"  ·  part:"+p;tip.style.display="block";tip.style.left=Math.min(x+12,$("#v3wrap").clientWidth-tip.offsetWidth-4)+"px";tip.style.top=(y+14)+"px"},
  onPick:p=>logLine("Anatomy pick: "+p),
  onSim:t=>{const e=$("#simro");if(e)e.textContent=t},
});
function buildSim(m){
  const box=$("#simbox");const sm=m.sim;if(!sm){box.innerHTML="";return}
  const S=V.sim;let h=`<h5>▶ 시뮬레이션 — ${esc(byId[m.id].n)}</h5>`;
  for(const c of sm.controls||[]){
    if(c.t==="slider")h+=`<div class="row"><label>${esc(c.label)}</label><input type="range" data-k="${c.k}" min="${c.min}" max="${c.max}" step="${c.step}" value="${S[c.k]}"><span class="val" data-v="${c.k}">${S[c.k]} ${esc(c.unit||"")}</span></div>`;
  }
  const tg=(sm.controls||[]).filter(c=>c.t==="toggle");
  if(tg.length)h+=`<div class="row" style="flex-wrap:wrap">`+tg.map(c=>`<label class="tg" style="width:auto"><input type="checkbox" data-k="${c.k}" ${S[c.k]?"checked":""}>${esc(c.label)}</label>`).join("")+`</div>`;
  const acts=Object.keys(sm.act||{});if(acts.length)h+=`<div class="acts">${acts.map(a=>`<button class="btn" data-a="${esc(a)}">${esc(a)}</button>`).join("")}</div>`;
  h+=`<div id="simro">-</div><div class="src" style="margin-top:6px;font-size:11.5px;color:var(--sub)">개념 시뮬레이션 · 설정값은 예시(프로젝트 Spec 대조 전 미확인)</div>`;
  box.innerHTML=h;
  box.querySelectorAll("input[type=range]").forEach(i=>i.oninput=()=>{autoX();const c=sm.controls.find(x=>x.k===i.dataset.k);V.simSet(i.dataset.k,+i.value);box.querySelector(`[data-v="${i.dataset.k}"]`).textContent=i.value+" "+(c.unit||"")});
  box.querySelectorAll("input[type=checkbox]").forEach(i=>i.onchange=()=>{autoX();V.simSet(i.dataset.k,i.checked)});
  box.querySelectorAll("[data-a]").forEach(b=>b.onclick=()=>{autoX();V.simAct(b.dataset.a);logLine("SIM "+m.id+": "+b.dataset.a);sync()});
  const sync=()=>{box.querySelectorAll("input[type=range]").forEach(i=>{const v=V.sim[i.dataset.k];if(+i.value!==v){i.value=v;const c=sm.controls.find(x=>x.k===i.dataset.k);box.querySelector(`[data-v="${i.dataset.k}"]`).textContent=v+" "+(c.unit||"")}});box.querySelectorAll("input[type=checkbox]").forEach(i=>i.checked=!!V.sim[i.dataset.k])};
}
/* ---- 창 크기 조절(열 경계 드래그) ---- */
(function(){const root=document.documentElement;const ld=(k,d)=>{try{return +localStorage.getItem(k)||d}catch(e){return d}};const sv=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
  let wl=ld("ic-wl",250),wr=ld("ic-wr",560);const ap=()=>{root.style.setProperty("--wl",wl+"px");root.style.setProperty("--wr",wr+"px");V.kick()};ap();
  const drag=(el,fn,key,def)=>{el.addEventListener("pointerdown",e=>{e.preventDefault();el.setPointerCapture(e.pointerId);el.classList.add("on");const x0=e.clientX;const st=fn(0,true);
    const mv=ev=>{fn(ev.clientX-x0,false,st);ap()};const up=()=>{el.classList.remove("on");el.removeEventListener("pointermove",mv);el.removeEventListener("pointerup",up);sv("ic-wl",wl);sv("ic-wr",wr)};
    el.addEventListener("pointermove",mv);el.addEventListener("pointerup",up)});el.addEventListener("dblclick",()=>{key==="l"?wl=250:wr=560;ap();sv("ic-wl",wl);sv("ic-wr",wr)})};
  const W=()=>innerWidth;
  drag($("#sp1"),(dx,init,st)=>{if(init)return wl;wl=Math.max(160,Math.min(W()-wr-320,st+dx))},"l");
  drag($("#sp2"),(dx,init,st)=>{if(init)return wr;wr=Math.max(320,Math.min(W()-wl-320,st-dx))},"r");
})();
function showModel(id,open){
  if(!V3D.MODELS[id])return;
  if(!V.model||V.model.id!==id){V.load(id);const m=V.model;$("#v3t").textContent=m.title;$("#v3sel").value=id;
    $("#plist").innerHTML=Object.entries(m.parts).map(([k,v])=>`<span class="tag" data-i="${id}" data-p="${k}" title="${esc(v)}">${esc(v)}</span>`).join("");bindTags($("#plist"));
    $("#v3x").style.display=m.shell.length?"":"none";buildSim(m)}
  if(open)selTab("anap");
}
$("#v3sel").innerHTML=Object.values(V3D.MODELS).map(m=>`<option value="${m.id}">${esc(byId[m.id].n)} — ${esc(m.title.split("—")[1]||"")}</option>`).join("");
$("#v3sel").onchange=e=>showModel(e.target.value,true);
$("#v3auto").onclick=e=>{V.auto=!V.auto;e.target.textContent="자동회전 "+(V.auto?"ON":"OFF")};
function autoX(){if(!V.xray){V.xray=true;$("#v3x").classList.add("p")}}
$("#v3x").onclick=e=>{V.xray=!V.xray;e.target.classList.toggle("p",V.xray)};
$("#v3zi").onclick=()=>V.zoomBy(1.25);$("#v3zo").onclick=()=>V.zoomBy(0.8);$("#v3r").onclick=()=>V.reset();

/* ---- 밝은/어두운 화면 ---- */
function applyTheme(t){document.documentElement.dataset.theme=t;$("#theme").textContent=t==="dark"?"☀ 밝은 화면":"🌙 어두운 화면";try{localStorage.setItem("ic-theme",t)}catch(e){}
  try{const d=$("#finframe").contentDocument;if(d&&d.documentElement)d.documentElement.dataset.theme=t}catch(e){}finBC&&finBC.postMessage({type:"theme",theme:t});V.kick()}
$("#theme").onclick=()=>applyTheme(document.documentElement.dataset.theme==="dark"?"light":"dark");
$("#finframe").addEventListener("load",()=>{try{$("#finframe").contentDocument.documentElement.dataset.theme=document.documentElement.dataset.theme||"light"}catch(e){}});
let t0="light";try{t0=localStorage.getItem("ic-theme")||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light")}catch(e){}
$("#f").onsubmit=e=>{e.preventDefault();const q=$("#q").value.trim();if(!q)return;$("#q").value="";handle(q)};
buildOrg();showModel("ball-valve");select("orch");paint();selTab("orgp");applyTheme(t0);
