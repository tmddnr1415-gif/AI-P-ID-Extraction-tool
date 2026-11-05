/* hotfix132 — 공통 셸.  `app/page_stamp.stamp()` 가 모든 화면(P&ID · LOGIC · 작도 · 판넬 · DCS · 도서검토)의 <head> 에 넣는다.
 *
 *  · 상단 띠 `#pidShell`: 제품 이름 › 이 화면 · 앱 전환 · 사용자 이름(누르면 바꾸기) · ? 도움말 · 정보 · 오른쪽 끝에 버전.
 *    `?embed=1`(부서 대시보드 iframe)이면 띠를 그리지 않는다 — 대시보드가 메뉴를 맡는다.  알림·확인·도움말은 그대로 된다.
 *  · 띠를 그리면 body 에 `pid-shell-on` 을 붙인다.  각 화면은 그 클래스가 있을 때만 자기 "← 돌아가기" 를 숨긴다.
 *  · `window.PID_SHELL` 계약(다른 화면이 있으면 쓰고 없으면 기존대로):
 *      app · embed · user() · setUser(name) · toast(text,{kind,ms}) · confirm(text,{ok,cancel,danger})→Promise<boolean>
 *      prompt(text,{placeholder,value,mustEqual})→Promise<string|null> · help(topic?) · info() · version()→Promise<{product,update,…}>
 *      nav(path) · withQuery(href) · errorText(json)
 *  · 사용자 이름은 기존 앱들과 같은 localStorage 'pid.author' 한 키만 쓴다 (`?user=` 가 있으면 그것이 우선).
 *    이름이 바뀌면 document 에 `pid-shell-user` 이벤트.
 *  · 주소의 `embed` · `user` 는 띠의 링크 · 각 화면의 돌아가기 · P&ID 왼쪽 메뉴를 누를 때 이어 붙인다 (이미 있으면 그대로).
 *  · 판정 0 — 화면을 오가게 하고 알림을 보일 뿐, 값을 만들거나 바꾸지 않는다.  외부 호출 없음. */
(function () {
  "use strict";
  if (window.PID_SHELL) return;

  var me = document.currentScript || document.querySelector('script[src*="/static/shell.js"]');
  var DS = (me && me.dataset) || {};
  var q;
  try { q = new URLSearchParams(location.search); } catch (e) { q = new URLSearchParams(""); }
  var EMBED = q.get("embed") === "1";
  var PRODUCT = { name: "계장 설계 도구", name_en: "", version: "", company: "", support: "" };

  var APPS = {
    pid: { name: "P&ID 리스트 추출", path: "/" },
    logic: { name: "LOGIC 검토", path: "/logic" },
    draw: { name: "LOGIC 작도", path: "/logic/draw" },
    space: { name: "판넬 공간확보", path: "/space" },
    dcs: { name: "DCS 그래픽", path: "/dcs" },
    books: { name: "계장 도서검토", path: "/books/" },
  };
  var ORDER = ["pid", "logic", "draw", "space", "dcs", "books"];
  var SCREENS = { "/logic/test": "블록 시험", "/logic/commission": "시운전", "/logic/signal": "신호 처리", "/help/manual": "사용 설명서" };
  var BACK_LINKS = ".lg-home,.hd-home,.dw-back,.gt-back,#back,.sp-back";

  function cleanPath(p) { return (p || "/").replace(/\/+$/, "") || "/"; }
  function appFromPath(p) {
    p = cleanPath(p);
    if (p === "/") return "pid";
    if (p.indexOf("/logic/draw") === 0) return "draw";
    if (p.indexOf("/logic") === 0) return "logic";
    if (p.indexOf("/space") === 0) return "space";
    if (p.indexOf("/dcs") === 0 || p.indexOf("/hmi") === 0) return "dcs";
    if (p.indexOf("/books") === 0) return "books";
    if (p.indexOf("/help") === 0) return "help";            // 사용 설명서 — 앱 전환에서 어느 것도 고르지 않는다
    return "pid";
  }
  var APP = APPS[DS.app] ? DS.app : appFromPath(location.pathname);
  var SCREEN = cleanPath(location.pathname);
  var screenName = SCREENS[SCREEN] || (APPS[APP] || APPS.pid).name;
  var helpKey = { "/logic/test": "test", "/logic/commission": "commission", "/logic/signal": "signal" }[SCREEN] || APP;

  /* ---------------- 사용자 이름 */
  function lsGet(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } }
  function user() { return (q.get("user") || "").trim().slice(0, 40) || lsGet("pid.author").trim(); }
  function setUser(name) {
    name = String(name || "").replace(/\s+/g, " ").trim().slice(0, 40);
    try { if (name) localStorage.setItem("pid.author", name); else localStorage.removeItem("pid.author"); } catch (e) { /* 막힌 저장소 */ }
    if (q.has("user")) {                                   // 주소의 이름이 우선이므로 주소도 같이 바꾼다 (새로 고침해도 그대로)
      try {
        var u = new URL(location.href);
        if (name) u.searchParams.set("user", name); else u.searchParams.delete("user");
        history.replaceState(history.state, "", u.pathname + u.search + u.hash);
        q = u.searchParams;
      } catch (e) { /* 옛 브라우저 */ }
    }
    renderUser();
    try { document.dispatchEvent(new CustomEvent("pid-shell-user", { detail: { name: name } })); } catch (e) { /* */ }
    return name;
  }

  /* ---------------- 주소의 embed · user 이어 붙이기 */
  function carryKeys() { return ["embed", "user"].filter(function (k) { return q.has(k); }); }
  function isAppPath(pathname) {
    return ORDER.some(function (k) {
      var p = APPS[k].path;
      return p === "/" ? pathname === "/" : pathname.indexOf(p.replace(/\/$/, "")) === 0;
    });
  }
  function withQuery(href) {
    var keys = carryKeys();
    if (!keys.length || !href) return href;
    var u;
    try { u = new URL(href, location.href); } catch (e) { return href; }
    if (u.origin !== location.origin || !isAppPath(u.pathname)) return href;
    var changed = false;
    keys.forEach(function (k) { if (!u.searchParams.has(k)) { u.searchParams.set(k, q.get(k)); changed = true; } });
    return changed ? u.pathname + u.search + u.hash : href;
  }
  function nav(path) { location.href = withQuery(path); }
  function isAppLink(a) {
    if (a.closest("#pidShell")) return true;
    try { return a.matches('#sidebar a.nav-item[href^="/"]') || a.matches(BACK_LINKS); } catch (e) { return false; }
  }
  document.addEventListener("click", function (ev) {           // 누르는 순간에만 고친다 — 나중에 다시 쓰인 href · 동적 링크도 안전
    var a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
    if (!a || !isAppLink(a)) return;
    var h0 = a.getAttribute("href"), h1 = withQuery(h0);
    if (h1 !== h0) a.setAttribute("href", h1);
  }, true);

  /* ---------------- 알림 */
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function toast(text, o) {
    o = o || {};
    var box = document.getElementById("pidToasts");
    if (!box) { box = el("div"); box.id = "pidToasts"; box.setAttribute("role", "status"); box.setAttribute("aria-live", "polite"); document.body.appendChild(box); }
    var t = el("div", "ps-toast " + (o.kind || ""), String(text == null ? "" : text));
    box.appendChild(t);
    var ms = o.ms || (o.kind === "err" ? 6000 : 3200);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, ms);
    return t;
  }
  function errorText(r) {
    if (!r) return "";
    if (typeof r === "string") return r;
    var d = r.detail !== undefined && r.detail !== null ? r.detail : r.error;
    if (Array.isArray(d)) d = d.map(function (x) { return (x && x.msg) || x; }).join(", ");
    return d == null ? "" : String(d);
  }

  /* ---------------- 모달 (브라우저 기본 확인 창 대신) */
  function modal(opts) {
    return new Promise(function (resolve) {
      var back = el("div", "ps-back"); back.setAttribute("role", "dialog"); back.setAttribute("aria-modal", "true");
      var dlg = el("div", "ps-dlg" + (opts.wide ? " wide" : ""));
      var h = el("div", "ps-dlg-h", opts.title || "");
      var x = el("button", "ps-x", "×"); x.type = "button"; x.setAttribute("aria-label", "닫기"); h.appendChild(x);
      var b = el("div", "ps-dlg-b" + (typeof opts.body === "string" ? " pre" : ""));
      if (typeof opts.body === "string") b.textContent = opts.body; else if (opts.body) b.appendChild(opts.body);
      var f = el("div", "ps-dlg-f");
      var prev = document.activeElement, done = false;
      function close(v) {
        if (done) return;
        done = true;
        document.removeEventListener("keydown", onKey, true);
        if (back.parentNode) back.parentNode.removeChild(back);
        try { if (prev && prev.focus) prev.focus(); } catch (e) { /* */ }
        resolve(v);
      }
      function val(v) { return typeof v === "function" ? v() : v; }
      function onKey(ev) {
        if (ev.isComposing || ev.keyCode === 229) return;      // 한글 조합 중의 Enter · Esc 는 입력기 몫
        if (ev.key === "Escape") { ev.stopPropagation(); ev.preventDefault(); close(opts.cancelValue); }
        else if (ev.key === "Enter" && opts.enterValue !== undefined && !(ev.target && ev.target.tagName === "TEXTAREA")) {
          ev.stopPropagation(); ev.preventDefault(); var v = val(opts.enterValue); if (v !== undefined) close(v);
        }
      }
      (opts.buttons || []).forEach(function (bt) {
        var btn = el("button", "ps-btn " + (bt.cls || ""), bt.label); btn.type = "button";
        btn.onclick = function () { var v = val(bt.value); if (v !== undefined) close(v); };
        f.appendChild(btn);
        if (bt.autofocus) setTimeout(function () { btn.focus(); }, 0);
      });
      x.onclick = function () { close(opts.cancelValue); };
      back.addEventListener("mousedown", function (ev) { if (ev.target === back) close(opts.cancelValue); });
      document.addEventListener("keydown", onKey, true);
      dlg.appendChild(h);
      if (opts.tabs) dlg.appendChild(opts.tabs);
      dlg.appendChild(b);
      if (opts.buttons && opts.buttons.length) dlg.appendChild(f);
      back.appendChild(dlg);
      document.body.appendChild(back);
      if (opts.onOpen) opts.onOpen(b, close);
    });
  }
  function confirm(text, o) {
    o = o || {};
    return modal({
      title: o.title || "확인", body: String(text == null ? "" : text), cancelValue: false,
      enterValue: o.danger ? undefined : true,                 // 위험한 일(지우기)은 Enter 로 지나가지 않게
      buttons: [{ label: o.cancel || "취소", value: false, autofocus: !!o.danger },
                { label: o.ok || "확인", cls: o.danger ? "danger" : "pri", value: true, autofocus: !o.danger }],
    });
  }
  function prompt(text, o) {
    o = o || {};
    var wrap = el("div"), p = el("div", null, String(text == null ? "" : text)), inp = el("input", "ps-in");
    inp.type = "text"; inp.placeholder = o.placeholder || ""; inp.value = o.value || ""; inp.maxLength = o.maxLength || 80;
    inp.setAttribute("aria-label", o.title || "입력");
    wrap.appendChild(p); wrap.appendChild(inp);
    setTimeout(function () { inp.focus(); inp.select(); }, 0);
    var get = function () {
      var v = inp.value.trim();
      if (o.mustEqual !== undefined && v !== o.mustEqual) { toast("정확히 '" + o.mustEqual + "' 라고 적어야 진행합니다.", { kind: "warn" }); inp.focus(); return undefined; }
      return v;
    };
    return modal({ title: o.title || "입력", body: wrap, cancelValue: null, enterValue: get,
                   buttons: [{ label: o.cancel || "취소", value: null }, { label: o.ok || "확인", cls: "pri", value: get }] });
  }

  /* ---------------- 버전 · 제품 정보 (/version 한 번만) */
  var verP = null;
  function version() {
    if (verP) return verP;
    verP = fetch("/version", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; })
      .then(function (j) {
        j = j && typeof j === "object" ? j : {};
        var p = j.product && typeof j.product === "object" ? j.product : {};
        Object.keys(PRODUCT).forEach(function (k) { if (p[k] != null && String(p[k]).trim()) PRODUCT[k] = String(p[k]).trim(); });
        j.product = Object.assign({}, PRODUCT);
        return j;
      });
    return verP;
  }
  function revText(u) {                     // 업데이트 번호 — 양의 정수일 때만 (없으면 그 토막을 뺀다)
    var r = u && u.rev;
    if (typeof r === "boolean" || r == null) return "";
    r = String(r).trim();
    return /^[0-9]+$/.test(r) && Number(r) > 0 ? r : "";
  }
  function fmtVersion(j) {
    var v = PRODUCT.version || (j && j.version) || "";
    var rev = revText(j && j.update);
    var d = ((j && j.update && j.update.created_at) || "").slice(0, 10) || ((j && j.built_at) || "").slice(0, 10);
    return v ? "버전 " + v + (rev ? " · 업데이트 " + rev : "") + (d ? " · " + d : "") : "";
  }
  function info() {
    return version().then(function (j) {
      var dl = el("dl", "ps-kv");
      function row(k, v) { if (!v) return; dl.appendChild(el("dt", null, k)); dl.appendChild(el("dd", null, v)); }
      row("제품", PRODUCT.name + (PRODUCT.name_en ? " (" + PRODUCT.name_en + ")" : ""));
      row("이 화면", screenName);
      row("버전", PRODUCT.version || j.version || "");
      row("업데이트 번호", revText(j.update));
      row("업데이트 날짜", ((j.update && j.update.created_at) || "").slice(0, 10) || (j.built_at || "").slice(0, 10));
      row("실행 방식", j.kind === "exe" ? "설치판(exe)" : j.kind === "source" ? "소스 실행" : "");
      row("사용자 이름", user() || "(아직 없음 — 위 띠에서 넣을 수 있습니다)");
      row("문의", PRODUCT.support);
      var wrap = el("div", "ps-help"); wrap.appendChild(dl);
      return modal({ title: "정보", body: wrap, cancelValue: undefined, buttons: [{ label: "닫기", cls: "pri", value: true, autofocus: true }] });
    });
  }

  /* ---------------- 도움말 */
  var HELP = {
    pid: { what: "P&ID 도면(PDF)에서 계기·밸브 리스트를 뽑아 사람이 검토하는 화면입니다.",
      steps: ["왼쪽 메뉴에서 프로젝트를 고르거나 새로 만듭니다.", "P&ID PDF 를 끌어다 놓으면 분석이 시작됩니다 (장수에 따라 몇 분).",
              "결과 표에서 값을 고칩니다. 고친 내용은 누가 언제 바꿨는지와 함께 남습니다.", "내려받기에서 Excel 리스트를 받습니다."] },
    logic: { what: "Logic 도면(PDF) 한 벌을 읽어 블록·신호·From-To 를 검토하는 화면입니다.",
      steps: ["프로젝트를 고르고 Logic PDF 묶음을 넣습니다.", "왼쪽 장 목록에서 장을 고르면 가운데에 도면, 오른쪽에 읽어 낸 내용이 보입니다.",
              "위 메뉴로 작도 · 신호 처리 · 시운전 · 블록 시험 화면에 갑니다.", "검토 결과는 PDF/Excel 로 내려받습니다."] },
    draw: { what: "표준 블록으로 Logic 을 직접 그리고 돌려 보는 화면입니다.",
      steps: ["왼쪽 블록 모음에서 블록을 끌어다 놓습니다.", "블록의 입·출력을 선으로 잇고 이름을 적습니다.", "저장하면 LOGIC 검토 화면에서도 같은 도면을 봅니다."] },
    test: { what: "LOGIC 블록 묶음(그룹)에 입력을 넣어 출력이 기대대로 나오는지 시험하는 화면입니다.",
      steps: ["LOGIC 검토에서 분석한 묶음을 고릅니다.", "시험할 그룹과 입력 값을 정하고 돌립니다.", "결과를 Excel 로 내려받습니다."] },
    commission: { what: "시운전 단계별로 어떤 신호와 블록이 살아야 하는지 확인하는 화면입니다.",
      steps: ["LOGIC 검토에서 분석한 묶음을 고릅니다.", "단계를 고르면 그 단계에 관련된 신호·블록이 표시됩니다.", "확인한 내용은 기록으로 남습니다."] },
    signal: { what: "신호 처리(필터 · 지연 · 비교) 블록이 시간에 따라 어떻게 움직이는지 그려 보는 화면입니다.",
      steps: ["블록 종류와 매개변수를 고릅니다.", "입력 파형을 정하고 돌리면 출력이 그래프로 보입니다."] },
    space: { what: "판넬 치수와 수량으로 전기실·계기실에 필요한 면적을 계산하고 배치해 보는 화면입니다.",
      steps: ["프로젝트를 고르거나 새로 만듭니다.", "판넬 종류·치수·수량을 적습니다.", "배치를 끌어 맞추고 3D 보기로 확인합니다.", "결과는 저장되며 Excel 로 받을 수 있습니다."] },
    dcs: { what: "P&ID · Logic 자료로 DCS 운전 화면 초안을 만드는 화면입니다.",
      steps: ["출처(분석한 P&ID 또는 예시)를 고릅니다.", "전체 화면에서 심볼을 옮기고 태그를 잇습니다.", "그림(PNG/SVG)으로 내려받습니다."] },
    books: { what: "사내 계장 도서(규격 · 절차서)를 찾고 필요한 부분을 번역하는 화면입니다.",
      steps: ["검색창에 낱말을 적으면 문서와 쪽을 찾아 줍니다.", "문서를 열어 필요한 부분을 고르면 번역할 수 있습니다.", "문서 폴더와 번역 설정은 운영자만 바꿉니다."] },
  };
  var TERMS = [
    ["프로젝트", "도면과 검토 결과를 묶는 가장 큰 단위. 공사(현장) 하나가 보통 프로젝트 하나입니다."],
    ["리비전", "같은 도면의 개정판. 새 리비전을 넣으면 이전 판과 무엇이 달라졌는지 비교합니다."],
    ["묶음", "한 번에 분석한 Logic PDF 한 벌. 묶음마다 분석 번호가 붙습니다."],
    ["SCOPE", "발주처 리스트의 공급 범위 열 — SCT(우리 공급)인지 VENDOR(업체 공급)인지."],
    ["Typical", "도면이 '여기와 같다' 고 가리키는 표준 상세. 대표 도면 한 장으로 여러 계기를 설명합니다."],
    ["분석 번호", "분석 한 번마다 붙는 짧은 번호. 결과를 다시 열거나 다른 사람에게 알려 줄 때 씁니다."],
    ["From-To", "신호가 어디서 나와 어디로 가는지(출발 블록 → 도착 블록)를 적은 표."],
    ["입찰 / 실행", "프로젝트 단계. 입찰은 수량 산출 위주, 실행은 설계 검토 위주로 화면이 맞춰집니다."],
    ["절전모드", "서버가 꺼져 있어도 이 PC 에 보관된 화면과 자료로 계속 보고 고치는 상태. 서버가 켜지면 고친 것을 되보냅니다."],
    ["자료 점검", "저장된 자료에 빠지거나 어긋난 것이 없는지 훑어 보는 기능. 이상이 없으면 보이지 않습니다."],
  ];
  function helpBody(key) {
    var k = HELP[key] ? key : HELP[APP] ? APP : "pid", h = HELP[k], wrap = el("div", "ps-help");
    var title = { test: SCREENS["/logic/test"], commission: SCREENS["/logic/commission"], signal: SCREENS["/logic/signal"] }[k] || APPS[k].name;
    wrap.appendChild(el("h4", null, title + " — 무엇을 하는 화면인가"));
    wrap.appendChild(el("p", null, h.what));
    wrap.appendChild(el("h4", null, "첫 단계"));
    var ol = el("ol"); h.steps.forEach(function (s) { ol.appendChild(el("li", null, s)); }); wrap.appendChild(ol);
    wrap.appendChild(el("p", "ps-muted", "이름은 위 띠의 이름 단추로 바꿉니다. 저장·기록에 그 이름이 남습니다."));
    if (PRODUCT.support) wrap.appendChild(el("p", "ps-muted", "문의: " + PRODUCT.support));
    return wrap;
  }
  function termsBody() {
    var wrap = el("div", "ps-help"), dl = el("dl");
    TERMS.forEach(function (t) { dl.appendChild(el("dt", null, t[0])); dl.appendChild(el("dd", null, t[1])); });
    wrap.appendChild(dl);
    return wrap;
  }
  function manualBody() {
    var wrap = el("div", "ps-help");
    wrap.appendChild(el("p", null, "화면별 사용 설명서는 새 창으로 엽니다."));
    var a = el("a", null, "사용 설명서 열기"); a.href = "/help/manual"; a.target = "_blank"; a.rel = "noopener";
    // 그냥 링크로 연다 — 서버는 설명서 파일이 없어도 짧은 안내 화면으로 답한다 (먼저 묻고 열면 팝업 차단에 걸릴 수 있다)
    var p = el("p"); p.appendChild(a); wrap.appendChild(p);
    if (PRODUCT.support) wrap.appendChild(el("p", "ps-muted", "문의: " + PRODUCT.support));
    return wrap;
  }
  function help(topic) {
    return version().then(function () {
      var key = HELP[topic] ? topic : helpKey;
      var tabs = el("div", "ps-tabs"); tabs.setAttribute("role", "tablist");
      var panes = { screen: helpBody(key), terms: termsBody(), manual: manualBody() };
      var names = [["screen", "이 화면"], ["terms", "용어"], ["manual", "설명서"]];
      var body = el("div"); body.appendChild(panes.screen);
      names.forEach(function (n, i) {
        var b = el("button", null, n[1]); b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", i === 0 ? "true" : "false");
        b.onclick = function () {
          tabs.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-selected", "false"); });
          b.setAttribute("aria-selected", "true"); body.textContent = ""; body.appendChild(panes[n[0]]);
        };
        tabs.appendChild(b);
      });
      return modal({ title: "도움말", tabs: tabs, body: body, wide: true, cancelValue: undefined,
                     buttons: [{ label: "닫기", cls: "pri", value: true }] });
    });
  }

  /* ---------------- 띠 */
  function renderUser() {
    var ub = document.querySelector("#pidShell .ps-user");
    if (!ub) return;
    var n = user();
    ub.textContent = "";
    if (n) ub.appendChild(el("span", "ps-user-l", "이름"));
    ub.appendChild(el("b", null, n || "이름 넣기"));
    ub.title = n ? "사용자 이름 바꾸기 (지금: " + n + ")" : "저장·기록에 남길 이름을 넣습니다";
  }
  function askName() {
    prompt("저장·기록에 남길 이름을 적어 주세요.", { title: "사용자 이름", value: user(), placeholder: "예: 홍길동", ok: "저장", maxLength: 40 })
      .then(function (v) {
        if (v === null) return;
        setUser(v);
        toast(v ? "이름을 '" + v + "' 으로 바꿨습니다." : "이름을 지웠습니다.", { kind: "ok" });
      });
  }
  function renderBar() {
    if (document.getElementById("pidShell")) return;
    var bar = el("header"); bar.id = "pidShell"; bar.setAttribute("role", "banner"); bar.setAttribute("aria-label", "공통 메뉴");
    var brand = el("div", "ps-brand");
    var co = el("span", "ps-co", PRODUCT.company); co.hidden = !PRODUCT.company;
    brand.appendChild(co); brand.appendChild(el("span", "ps-name", PRODUCT.name)); brand.appendChild(el("span", "ps-crumb", screenName));
    var nav = el("nav", "ps-nav"); nav.setAttribute("aria-label", "화면 이동");
    ORDER.forEach(function (k) {
      var a = el("a", null, APPS[k].name); a.href = withQuery(APPS[k].path); a.dataset.app = k;
      if (k === APP) a.setAttribute("aria-current", "page");
      nav.appendChild(a);
    });
    var right = el("div", "ps-right");
    var ub = el("button", "ps-user"); ub.type = "button"; ub.onclick = askName;
    var hb = el("button", "ps-help-btn", "? 도움말"); hb.type = "button"; hb.onclick = function () { help(); };
    var ib = el("button", "ps-info-btn", "정보"); ib.type = "button"; ib.onclick = function () { info(); };
    var ver = el("span", "ps-ver", DS.version || "");
    right.appendChild(ub); right.appendChild(hb); right.appendChild(ib); right.appendChild(ver);
    bar.appendChild(brand); bar.appendChild(nav); bar.appendChild(right);
    document.body.insertBefore(bar, document.body.firstChild);
    document.body.classList.add("pid-shell-on");
    document.documentElement.classList.add("has-shell");
    renderUser();
  }
  function refreshBrand(j) {
    var bar = document.getElementById("pidShell");
    if (!bar) return;
    var co = bar.querySelector(".ps-co"); co.textContent = PRODUCT.company; co.hidden = !PRODUCT.company;
    bar.querySelector(".ps-name").textContent = PRODUCT.name;
    var ver = bar.querySelector(".ps-ver"); if (!ver.textContent) ver.textContent = fmtVersion(j);
  }

  function init() {
    if (!document.body) return;
    if (!EMBED) renderBar();
    var ours = screenName + " · " + PRODUCT.name;
    document.title = ours;                                   // 처음 한 번만 — 그 뒤 화면이 바꾸는 제목과 다투지 않는다
    version().then(function (j) {
      refreshBrand(j);
      var now = screenName + " · " + PRODUCT.name;
      if (document.title === ours && now !== ours) document.title = now;
    });
    window.addEventListener("storage", function (ev) { if (ev.key === "pid.author") renderUser(); });
  }

  window.PID_SHELL = {
    app: APP, embed: EMBED, apps: APPS, screen: screenName,
    user: user, setUser: setUser, toast: toast, confirm: confirm, prompt: prompt, help: help, info: info,
    version: version, nav: nav, withQuery: withQuery, errorText: errorText,
    product: function () { return Object.assign({}, PRODUCT); },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
