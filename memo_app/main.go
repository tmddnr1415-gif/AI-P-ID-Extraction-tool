// 내 메모장 단독 실행 파일 (메모장.exe) — 2026-11-20
//
// 더블클릭 → 이 PC 안에서만 열리는 작은 웹서버(127.0.0.1, 다른 PC · 인터넷에서는 접속 불가)를 띄우고
// Edge 앱 창으로 대시보드의 '내 메모장' 화면만 엽니다. 화면(dashboard.html)과 PDF 보기(pdf.js) · 글자 인식(tesseract.js)은
// 이 파일 안에 들어 있고(외부 주소 0), 메모는 exe 옆 '메모장_자료' 폴더(쓸 수 없으면 %LOCALAPPDATA%\메모장)에 저장합니다.
// 저장 규칙은 대시보드 server.py 의 /api/memo 와 같습니다(페이지 · 섹션 · 첨부 · 판 기록 · 휴지통 · 용량 · ID 검사).
// 창을 닫으면 약 3분 뒤 스스로 끝납니다. 이미 켜져 있으면 새로 띄우지 않고 그 창을 다시 엽니다.
package main

import (
	"bytes"
	"crypto/rand"
	"embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"log"
	"mime"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

//go:embed all:web
var webFS embed.FS

const (
	appVersion = "1.0.0 (2026-11-20)"
	defPort    = 18766
	pageMax    = 12 << 20
	fileMax    = 30 << 20
	quota      = 500 << 20
	verKeep    = 20
	verGap     = 600 * time.Second
	idleQuit   = 3 * time.Minute
)

var (
	reUID  = regexp.MustCompile(`^[a-z0-9]{6,40}$`)
	reFID  = regexp.MustCompile(`^f[0-9a-f]{6,30}$`)
	reTS   = regexp.MustCompile(`^\d{14}$`)
	reExt  = regexp.MustCompile(`^\.[a-z0-9]{1,8}$`)
	reNonD = regexp.MustCompile(`\D`)
	meta   = []string{"id", "kind", "sec", "title", "icon", "color", "tags", "pin", "lock", "deleted", "float", "x", "y", "w", "h", "fx", "fy", "text", "todos", "marks", "links", "parent", "ver", "cov", "mail", "files", "date", "lh", "ord", "share", "img", "createdAt", "updatedAt"}
	ftypes = map[string]string{".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
		".txt": "text/plain; charset=utf-8", ".csv": "text/csv; charset=utf-8", ".md": "text/plain; charset=utf-8"}
)

type apiErr struct {
	code int
	msg  string
}

func (e *apiErr) Error() string      { return e.msg }
func bad(code int, msg string) error { return &apiErr{code, msg} }

type app struct {
	dir   string // 자료 폴더 (= server.py 의 notes/{계정ID}/)
	token string
	name  string
	port  int
	mu    sync.Mutex
	seen  time.Time
	html  []byte
}

func stamp() string { return time.Now().UTC().Format("2006-01-02T15:04:05.000Z") }

func (a *app) p(parts ...string) string { return filepath.Join(append([]string{a.dir}, parts...)...) }

func readJSON(fn string) map[string]any {
	b, err := os.ReadFile(fn)
	if err != nil {
		return nil
	}
	d := json.NewDecoder(bytes.NewReader(b))
	d.UseNumber()
	var m map[string]any
	if d.Decode(&m) != nil {
		return nil
	}
	return m
}

func writeJSON(fn string, v any) error {
	if err := os.MkdirAll(filepath.Dir(fn), 0o755); err != nil {
		return err
	}
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	tmp := fn + ".tmp"
	if err := os.WriteFile(tmp, b, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, fn)
}

func listJSON(d string) []string {
	es, err := os.ReadDir(d)
	if err != nil {
		return nil
	}
	var out []string
	for _, e := range es {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".json") {
			out = append(out, e.Name())
		}
	}
	sort.Strings(out)
	return out
}

func str(v any) string {
	switch x := v.(type) {
	case nil:
		return ""
	case string:
		return x
	case json.Number:
		return x.String()
	case bool:
		if x {
			return "True"
		}
		return ""
	default:
		b, _ := json.Marshal(x)
		return string(b)
	}
}

func cut(s string, n int) string {
	r := []rune(s)
	if len(r) > n {
		return string(r[:n])
	}
	return s
}

func (a *app) usage() int64 {
	var n int64
	filepath.WalkDir(a.dir, func(_ string, d fs.DirEntry, err error) error {
		if err == nil && !d.IsDir() {
			if i, e := d.Info(); e == nil {
				n += i.Size()
			}
		}
		return nil
	})
	return n
}

func pid(s string) (string, error) {
	if !reUID.MatchString(s) {
		return "", bad(400, "잘못된 메모 ID")
	}
	return s, nil
}

// ---------------------------------------------------------------- /api/memo (server.py 와 같은 규칙)
func (a *app) memoList() any {
	pages := []map[string]any{}
	d := a.p("pages")
	for _, n := range listJSON(d) {
		pg := readJSON(filepath.Join(d, n))
		if pg == nil || str(pg["id"]) == "" {
			continue
		}
		m := map[string]any{}
		for _, k := range meta {
			if v, ok := pg[k]; ok {
				m[k] = v
			}
		}
		pages = append(pages, m)
	}
	book := readJSON(a.p("book.json"))
	if book == nil {
		book = map[string]any{}
	}
	return map[string]any{"book": book, "pages": pages, "used": a.usage(), "quota": quota}
}

func (a *app) memoGet(id string) (any, error) {
	if _, err := pid(id); err != nil {
		return nil, err
	}
	pg := readJSON(a.p("pages", id+".json"))
	if pg == nil {
		return nil, bad(404, "없는 메모입니다 (삭제되었을 수 있어요)")
	}
	return pg, nil
}

func (a *app) memoPut(id string, raw []byte) (any, error) {
	if _, err := pid(id); err != nil {
		return nil, err
	}
	if len(raw) > pageMax {
		return nil, bad(413, "메모 한 장이 너무 큽니다 (12MB) — 큰 그림 · 파일은 📎 첨부로 넣어 주세요")
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	var b map[string]any
	if dec.Decode(&b) != nil || b == nil {
		return nil, bad(400, "잘못된 요청")
	}
	fn := a.p("pages", id+".json")
	a.mu.Lock()
	defer a.mu.Unlock()
	old := readJSON(fn)
	base := str(b["base"])
	delete(b, "base")
	force := b["force"] == true
	delete(b, "force")
	if old != nil && base != "" && str(old["updatedAt"]) != "" && str(old["updatedAt"]) != base && !force {
		return nil, bad(409, "다른 창 · 다른 PC 에서 이 메모를 먼저 고쳤습니다")
	}
	if old == nil && a.usage() > quota {
		return nil, bad(413, "메모장 용량(500MB)을 다 썼습니다 — 휴지통 · 첨부를 정리해 주세요")
	}
	now := stamp()
	b["id"] = id
	if old != nil && str(old["createdAt"]) != "" {
		b["createdAt"] = old["createdAt"]
	} else {
		b["createdAt"] = now
	}
	b["updatedAt"] = now
	for _, k := range []string{"title", "icon", "color", "sec", "kind"} {
		b[k] = cut(str(b[k]), 200)
	}
	if old != nil && str(old["html"]) != str(b["html"]) && strings.TrimSpace(str(old["html"])) != "" { // 이전 판 (10분에 한 번, 최근 20개)
		vd := a.p("ver", id)
		vers := listJSON(vd)
		ou := str(old["updatedAt"])
		if ou == "" {
			ou = now
		}
		ts := reNonD.ReplaceAllString(ou, "")
		if len(ts) > 14 {
			ts = ts[:14]
		}
		gap := verGap
		if len(vers) > 0 {
			t1, e1 := time.Parse("20060102150405", ts)
			t0, e0 := time.Parse("20060102150405", strings.TrimSuffix(vers[len(vers)-1], ".json"))
			if e1 == nil && e0 == nil {
				gap = t1.Sub(t0)
			}
		}
		if gap >= verGap {
			writeJSON(filepath.Join(vd, ts+".json"), map[string]any{"at": old["updatedAt"], "title": old["title"], "html": old["html"]})
			vs := listJSON(vd)
			for i := 0; i < len(vs)-verKeep; i++ {
				os.Remove(filepath.Join(vd, vs[i]))
			}
		}
	}
	if err := writeJSON(fn, b); err != nil {
		return nil, bad(500, "저장하지 못했습니다: "+err.Error())
	}
	return map[string]any{"status": "ok", "updatedAt": now, "createdAt": b["createdAt"]}, nil
}

func (a *app) memoDel(id string) (any, error) {
	if _, err := pid(id); err != nil {
		return nil, err
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	os.Remove(a.p("pages", id+".json"))
	os.RemoveAll(a.p("ver", id))
	return map[string]any{"status": "ok"}, nil
}

func (a *app) memoBook(raw []byte) (any, error) {
	var b struct {
		Secs []map[string]any `json:"secs"`
		Nav  []any            `json:"nav"`
	}
	if json.Unmarshal(raw, &b) != nil || b.Secs == nil || len(b.Secs) > 200 {
		return nil, bad(400, "잘못된 섹션 목록")
	}
	secs := []map[string]any{}
	for _, x := range b.Secs {
		if str(x["id"]) == "" {
			continue
		}
		secs = append(secs, map[string]any{"id": cut(str(x["id"]), 40), "name": cut(str(x["name"]), 60), "color": cut(str(x["color"]), 20)})
	}
	nav := []string{}
	for _, x := range b.Nav {
		if s, ok := x.(string); ok && len(nav) < 40 {
			nav = append(nav, cut(s, 16))
		}
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	if err := writeJSON(a.p("book.json"), map[string]any{"secs": secs, "nav": nav, "updatedAt": stamp()}); err != nil {
		return nil, bad(500, err.Error())
	}
	return map[string]any{"status": "ok"}, nil
}

func (a *app) memoVers(id, ts string) (any, error) {
	if _, err := pid(id); err != nil {
		return nil, err
	}
	vd := a.p("ver", id)
	if ts != "" {
		if !reTS.MatchString(ts) {
			return nil, bad(400, "잘못된 판")
		}
		v := readJSON(filepath.Join(vd, ts+".json"))
		if v == nil {
			return nil, bad(404, "없는 판입니다")
		}
		return v, nil
	}
	out := []map[string]any{}
	vs := listJSON(vd)
	for i := len(vs) - 1; i >= 0; i-- {
		v := readJSON(filepath.Join(vd, vs[i]))
		if v == nil {
			v = map[string]any{}
		}
		out = append(out, map[string]any{"ts": strings.TrimSuffix(vs[i], ".json"), "at": v["at"], "title": v["title"], "size": len([]rune(str(v["html"])))})
	}
	return map[string]any{"vers": out}, nil
}

func (a *app) filePut(name, want string, data []byte) (any, error) {
	name = strings.TrimSpace(path.Base(strings.ReplaceAll(name, "\\", "/")))
	name = cut(name, 120)
	if name == "" || name == "." || name == "/" {
		name = "file"
	}
	ext := strings.ToLower(filepath.Ext(name))
	if !reExt.MatchString(ext) {
		ext = ".bin"
	}
	if len(data) == 0 {
		return nil, bad(400, "빈 파일입니다")
	}
	if a.usage()+int64(len(data)) > quota {
		return nil, bad(413, "메모장 용량(500MB)을 다 썼습니다 — 휴지통 · 첨부를 정리해 주세요")
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	rb := make([]byte, 3)
	rand.Read(rb)
	fid := "f" + strconv.FormatInt(time.Now().UnixMilli(), 16) + hex.EncodeToString(rb)
	d := a.p("files")
	if reFID.MatchString(want) {
		if _, err := os.Stat(filepath.Join(d, want+".json")); errors.Is(err, os.ErrNotExist) {
			fid = want // 서버가 꺼져 있을 때 먼저 붙인 첨부 · 백업에서 가져온 첨부: 그 ID 그대로 (메모 안의 연결 유지)
		}
	}
	os.MkdirAll(d, 0o755)
	tmp := filepath.Join(d, fid+".tmp")
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return nil, bad(500, err.Error())
	}
	if err := os.Rename(tmp, filepath.Join(d, fid+ext)); err != nil {
		return nil, bad(500, err.Error())
	}
	m := map[string]any{"id": fid, "name": name, "ext": ext, "size": len(data), "at": stamp()}
	writeJSON(filepath.Join(d, fid+".json"), m)
	return m, nil
}

func (a *app) fileMeta(fid string) (map[string]any, error) {
	if !reFID.MatchString(fid) {
		return nil, bad(400, "잘못된 파일 ID")
	}
	m := readJSON(a.p("files", fid+".json"))
	if m == nil || !reExt.MatchString(str(m["ext"])) {
		return nil, bad(404, "첨부파일이 없습니다")
	}
	if st, err := os.Stat(a.p("files", fid+str(m["ext"]))); err != nil || st.IsDir() {
		return nil, bad(404, "첨부파일이 없습니다")
	}
	return m, nil
}

// ---------------------------------------------------------------- HTTP
func (a *app) send(w http.ResponseWriter, code int, v any) {
	b, _ := json.Marshal(v)
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(code)
	w.Write(b)
}

func (a *app) okHost(r *http.Request) bool { // 다른 사이트가 이 PC 주소 이름을 바꿔 끼워 들어오는 것(DNS rebinding) 막기
	h := r.Host
	p := ":" + strconv.Itoa(a.port)
	return h == "127.0.0.1"+p || h == "localhost"+p
}

func (a *app) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	ip, _, _ := net.SplitHostPort(r.RemoteAddr)
	if ip != "127.0.0.1" && ip != "::1" || !a.okHost(r) {
		http.Error(w, "forbidden", 403)
		return
	}
	h := w.Header()
	h.Set("X-Content-Type-Options", "nosniff")
	h.Set("Referrer-Policy", "no-referrer")
	h.Set("X-Frame-Options", "DENY")
	// 외부 주소로는 아무것도 보내거나 받지 않음 (글자 인식 · PDF 는 이 파일 안의 것만)
	h.Set("Content-Security-Policy", "default-src 'self' data: blob: 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval'; connect-src 'self' data: blob:; img-src 'self' data: blob:; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
	if strings.HasPrefix(r.URL.Path, "/api/") {
		a.api(w, r)
		return
	}
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method", 405)
		return
	}
	if r.URL.Path == "/" || r.URL.Path == "/index.html" || r.URL.Path == "/dashboard.html" {
		h.Set("Content-Type", "text/html; charset=utf-8")
		h.Set("Cache-Control", "no-store")
		w.Write(a.html)
		return
	}
	if strings.HasPrefix(r.URL.Path, "/apps/pdfjs/") || strings.HasPrefix(r.URL.Path, "/apps/translate/ocr/") || r.URL.Path == "/apps/translate/README.txt" {
		fp := "web" + path.Clean(r.URL.Path)
		b, err := webFS.ReadFile(fp)
		if err != nil {
			http.NotFound(w, r)
			return
		}
		ct := mime.TypeByExtension(path.Ext(fp))
		switch path.Ext(fp) {
		case ".js", ".mjs":
			ct = "text/javascript; charset=utf-8"
		case ".wasm":
			ct = "application/wasm"
		case "", ".bcmap", ".pfb", ".gz", ".traineddata":
			ct = "application/octet-stream"
		}
		if ct == "" {
			ct = "application/octet-stream"
		}
		h.Set("Content-Type", ct)
		h.Set("Cache-Control", "max-age=86400")
		w.Write(b)
		return
	}
	http.NotFound(w, r)
}

func (a *app) api(w http.ResponseWriter, r *http.Request) {
	defer func() {
		if e := recover(); e != nil {
			log.Printf("오류: %v", e)
			a.send(w, 500, map[string]any{"error": "메모장 프로그램 오류"})
		}
	}()
	seg := strings.Split(strings.Trim(strings.TrimPrefix(r.URL.Path, "/api/"), "/"), "/")
	m := r.Method
	if len(seg) == 1 && seg[0] == "info" { // 토큰 없이도 (같은 프로그램이 켜져 있는지 확인용) — 메모 내용은 없음
		a.send(w, 200, map[string]any{"mode": "server", "memoApp": true, "app": "dept-memo", "version": appVersion, "admin": false})
		return
	}
	if r.Header.Get("X-Auth-Token") != a.token { // 다른 웹사이트가 이 PC 의 메모장을 몰래 부르는 것 막기 (이 화면만 아는 값)
		a.send(w, 401, map[string]any{"error": "메모장 창을 다시 열어 주세요"})
		return
	}
	a.mu.Lock()
	a.seen = time.Now()
	a.mu.Unlock()
	var raw []byte
	if m == http.MethodPut || m == http.MethodPost {
		lim := int64(pageMax + 1<<20)
		if len(seg) >= 2 && seg[0] == "memo" && seg[1] == "f" {
			lim = fileMax
		}
		b, err := io.ReadAll(io.LimitReader(r.Body, lim+1))
		if err != nil {
			a.send(w, 400, map[string]any{"error": "잘못된 요청"})
			return
		}
		if int64(len(b)) > lim {
			a.send(w, 413, map[string]any{"error": "요청이 너무 큽니다"})
			return
		}
		raw = b
	}
	res, err := a.route(m, seg, r.URL.Query(), raw, w)
	if err != nil {
		var ae *apiErr
		if errors.As(err, &ae) {
			a.send(w, ae.code, map[string]any{"error": ae.msg})
		} else {
			a.send(w, 500, map[string]any{"error": err.Error()})
		}
		return
	}
	if res != nil {
		a.send(w, 200, res)
	}
}

func (a *app) route(m string, seg []string, q url.Values, raw []byte, w http.ResponseWriter) (any, error) {
	n := len(seg)
	switch {
	case n == 2 && seg[0] == "auth" && seg[1] == "me":
		return map[string]any{"id": "me", "name": a.name}, nil
	case n == 2 && seg[0] == "memoapp" && seg[1] == "alive":
		return map[string]any{"ok": true, "dir": a.dir}, nil
	case n == 3 && seg[0] == "memoapp" && seg[1] == "open" && m == "POST": // 메일 파일(.eml · .msg)을 Windows 기본 프로그램(Outlook)으로 열기 — 다른 종류는 열지 않음
		fm, err := a.fileMeta(seg[2])
		if err != nil {
			return nil, err
		}
		ext := str(fm["ext"])
		if ext != ".eml" && ext != ".msg" {
			return nil, bad(400, "메일 파일만 열 수 있습니다")
		}
		if err := openFile(a.p("files", seg[2]+ext)); err != nil {
			return nil, bad(500, "열지 못했습니다: "+err.Error())
		}
		return map[string]any{"ok": true}, nil
	case seg[0] != "memo":
		return nil, bad(404, "메모장 프로그램에는 없는 기능입니다")
	case n == 1 && m == "GET":
		return a.memoList(), nil
	case n == 2 && seg[1] == "shared" && m == "GET":
		return map[string]any{"shared": []any{}}, nil
	case n == 2 && seg[1] == "book" && m == "PUT":
		return a.memoBook(raw)
	case n == 3 && seg[1] == "p":
		switch m {
		case "GET":
			return a.memoGet(seg[2])
		case "PUT":
			return a.memoPut(seg[2], raw)
		case "DELETE":
			return a.memoDel(seg[2])
		}
	case (n == 4 || n == 5) && seg[1] == "p" && seg[3] == "vers" && m == "GET":
		ts := ""
		if n == 5 {
			ts = seg[4]
		}
		return a.memoVers(seg[2], ts)
	case n == 2 && seg[1] == "f" && m == "PUT":
		return a.filePut(q.Get("name"), q.Get("id"), raw)
	case n == 3 && seg[1] == "f":
		fm, err := a.fileMeta(seg[2])
		if err != nil {
			return nil, err
		}
		if m == "DELETE" {
			a.mu.Lock()
			defer a.mu.Unlock()
			os.Remove(a.p("files", seg[2]+str(fm["ext"])))
			os.Remove(a.p("files", seg[2]+".json"))
			return map[string]any{"status": "ok"}, nil
		}
		if m == "GET" {
			b, err := os.ReadFile(a.p("files", seg[2]+str(fm["ext"])))
			if err != nil {
				return nil, bad(404, "첨부파일이 없습니다")
			}
			ct := ftypes[str(fm["ext"])]
			if ct == "" {
				ct = "application/octet-stream"
			}
			w.Header().Set("Content-Type", ct)
			w.Header().Set("Cache-Control", "no-store")
			w.Header().Set("Content-Disposition", "attachment; filename*=UTF-8''"+strings.ReplaceAll(url.PathEscape(str(fm["name"])), "%2F", "/"))
			w.WriteHeader(200)
			w.Write(b)
			return nil, nil
		}
	}
	return nil, bad(404, "없는 요청")
}

// ---------------------------------------------------------------- 시작
func exeDir() string {
	p, err := os.Executable()
	if err != nil {
		return "."
	}
	if r, err := filepath.EvalSymlinks(p); err == nil {
		p = r
	}
	return filepath.Dir(p)
}

func writable(d string) bool {
	if os.MkdirAll(d, 0o755) != nil {
		return false
	}
	f, err := os.CreateTemp(d, ".w*")
	if err != nil {
		return false
	}
	n := f.Name()
	f.Close()
	os.Remove(n)
	return true
}

func pickDir(flagDir string) string {
	if flagDir != "" {
		return flagDir
	}
	d := filepath.Join(exeDir(), "메모장_자료")
	if writable(d) {
		return d
	}
	base := os.Getenv("LOCALAPPDATA")
	if base == "" {
		base, _ = os.UserConfigDir()
	}
	return filepath.Join(base, "메모장")
}

func openWindow(u string) {
	if runtime.GOOS != "windows" {
		for _, c := range []string{"xdg-open", "open"} {
			if exec.Command(c, u).Start() == nil {
				return
			}
		}
		return
	}
	var cands []string
	for _, env := range []string{"ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"} {
		if b := os.Getenv(env); b != "" {
			cands = append(cands, filepath.Join(b, "Microsoft", "Edge", "Application", "msedge.exe"), filepath.Join(b, "Google", "Chrome", "Application", "chrome.exe"))
		}
	}
	for _, c := range cands {
		if st, err := os.Stat(c); err == nil && !st.IsDir() {
			if exec.Command(c, "--app="+u, "--window-size=1400,900").Start() == nil {
				return
			}
		}
	}
	exec.Command("rundll32", "url.dll,FileProtocolHandler", u).Start() // 기본 브라우저
}

func openFile(p string) error { // 기본 프로그램으로 열기 (eml · msg = Outlook)
	if runtime.GOOS == "windows" {
		return exec.Command("rundll32", "url.dll,FileProtocolHandler", p).Start()
	}
	if os.Getenv("MEMOAPP_TEST_OPEN") != "" { // 시험: 연 파일 이름을 남김
		return os.WriteFile(os.Getenv("MEMOAPP_TEST_OPEN"), []byte(p), 0o644)
	}
	return exec.Command("xdg-open", p).Start()
}

func alreadyRunning(port int) bool { // 같은 프로그램이 이미 켜져 있으면 true
	c := &http.Client{Timeout: 1500 * time.Millisecond}
	r, err := c.Get(fmt.Sprintf("http://127.0.0.1:%d/api/info", port))
	if err != nil {
		return false
	}
	defer r.Body.Close()
	var v map[string]any
	json.NewDecoder(r.Body).Decode(&v)
	return v["app"] == "dept-memo"
}

func main() {
	port := flag.Int("port", defPort, "포트 (127.0.0.1 만)")
	dataDir := flag.String("data", "", "자료 폴더 (기본: exe 옆 메모장_자료)")
	noWin := flag.Bool("no-browser", false, "창을 열지 않음 (시험용)")
	stay := flag.Bool("stay", false, "창을 닫아도 끝내지 않음 (시험용)")
	name := flag.String("name", "", "메모장 이름 (기본: Windows 사용자 이름)")
	flag.Parse()

	a := &app{dir: pickDir(*dataDir), seen: time.Now()}
	os.MkdirAll(a.dir, 0o755)
	if lf, err := os.OpenFile(filepath.Join(a.dir, "메모장.log"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644); err == nil {
		log.SetOutput(lf)
	}
	a.name = *name
	if a.name == "" {
		a.name = os.Getenv("USERNAME")
	}
	if a.name == "" {
		a.name = "나"
	}
	tb := make([]byte, 24)
	rand.Read(tb)
	a.token = hex.EncodeToString(tb)

	ln, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", *port))
	if err != nil {
		if alreadyRunning(*port) { // 이미 켜져 있음 → 그 창을 다시 열고 끝 (새 창은 새 열쇠를 받음)
			if !*noWin {
				openWindow(fmt.Sprintf("http://127.0.0.1:%d/", *port))
			}
			return
		}
		ln, err = net.Listen("tcp", "127.0.0.1:0") // 다른 프로그램이 그 포트를 쓰면 빈 포트로
		if err != nil {
			log.Fatal(err)
		}
	}
	a.port = ln.Addr().(*net.TCPAddr).Port

	page, err := webFS.ReadFile("web/dashboard.html")
	if err != nil {
		log.Fatal(err)
	}
	cfg, _ := json.Marshal(map[string]any{"token": a.token, "name": a.name, "dir": a.dir, "version": appVersion})
	a.html = bytes.Replace(page, []byte("<head>"), []byte("<head><script>window.MEMO_APP="+string(cfg)+"</script>"), 1)

	log.Printf("메모장 %s 시작 — http://127.0.0.1:%d/ · 자료 %s", appVersion, a.port, a.dir)
	fmt.Printf("메모장 http://127.0.0.1:%d/  자료: %s\n", a.port, a.dir)
	srv := &http.Server{Handler: a, ReadHeaderTimeout: 10 * time.Second}
	go func() {
		if err := srv.Serve(ln); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()
	if !*noWin {
		openWindow(fmt.Sprintf("http://127.0.0.1:%d/", a.port))
	}
	// 창을 닫으면(화면이 더 이상 부르지 않으면) 끝냄. 절전에서 깨어난 직후에는 기다림을 다시 셈
	last := time.Now()
	for range time.Tick(10 * time.Second) {
		now := time.Now()
		a.mu.Lock()
		if now.Sub(last) > 40*time.Second {
			a.seen = now
		}
		idle := now.Sub(a.seen)
		a.mu.Unlock()
		last = now
		if !*stay && idle > idleQuit {
			log.Printf("창이 닫혀 끝냄")
			return
		}
	}
}
