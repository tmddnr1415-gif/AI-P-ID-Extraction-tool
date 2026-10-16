"""학습 사전 — Signal Processing Symbols 와 MACRO(Typical) 를 묶음 밖에 쌓아 두고, 다른 프로젝트 Logic 을 그 기준으로
읽는다 (L22 · 사용자 지시: *"학습시켜놓는다 — 다른 pjt logic 이 들어와도 해당 학습된 기준으로 분석한다"*).

두 자리:
  * `config/logic_library.json` — 저장소에 싣는 씨앗 (19VA "SIGNAL PROCESSING SYMBOLS" 범례 표에서 읽은 모양 열쇠 →
    기능 이름 · 동작, 상자 안 그림).  ISA-S5.2 기호의 모양이지 고객 도면이 아니다.
  * `{data}/logic/library.json` + `{data}/logic/library/` — 이 서버가 분석한 묶음에서 배운 것 (범례 표 · 매크로가 이어진
    Typical 시트 · 사람이 게이트 종류를 정한 모양).  분석이 끝날 때마다 늘어난다.

읽는 순서 (도면이 말하는 것은 도면에서 — §9):
  ① 그 묶음의 범례 표가 이긴다.  사전은 범례가 말하지 않은 열쇠만 보탠다.
  ② 범례 표가 없는 묶음에서는 **블록 안에 진짜 글자가 있고 사전 열쇠와 정확히 맞을 때만** 쓴다
     (선 글자로 그린 HRSG 같은 묶음은 예전 길 그대로 — 모양만으로 맞대지 않는다).
  ③ 매크로 블록의 Typical 시트가 그 묶음에 없을 때만 사전의 Typical 을 단자 이름으로 맞댄다 (문턱이 묶음 안보다 높다).
  ④ 같은 열쇠를 두 출처가 다른 동작으로 말하면 그 열쇠는 쓰지 않는다 (지어내지 않는다).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import threading
import time
from pathlib import Path

from app import paths

from . import store

_LOCK = threading.Lock()
LIB_PAGE0 = 100000           # 사전 Typical 시트의 가짜 쪽 번호 (묶음 쪽과 겹치지 않게)
MATCH_MIN = 0.55             # 사전 Typical 을 고르는 단자 맞음 하한 (묶음 안 0.30 보다 높다 — 다른 프로젝트라서)


def seed_path() -> Path:
    return paths.resource("config", "logic_library.json")


def data_path() -> Path:
    return store.root() / "library.json"


def typ_dir() -> Path:
    p = store.root() / "library"
    p.mkdir(exist_ok=True)
    return p


def _empty():
    return {"symbols": {}, "figures": [], "typicals": {}, "learned_jobs": [], "taught": []}


def _read(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            out = _empty()
            for k in out:
                if isinstance(d.get(k), type(out[k])):
                    out[k] = d[k]
            return out
    except Exception:
        pass
    return _empty()


def specific(key: str) -> bool:
    """열쇠가 블록을 가려낼 만큼 구체적인가 — 블록 안에 인쇄된 진짜 글자가 있어야 한다 (모양만으로는 맞대지 않는다)."""
    if not key or "|" not in key:
        return False
    text = key.split("|", 1)[1].strip()
    return bool(text) and text not in ("?",)


def load() -> dict:
    """씨앗 + 이 서버가 배운 것.  같은 열쇠를 다른 동작으로 말하면 그 열쇠는 뺀다."""
    seed, mine = _read(seed_path()), _read(data_path())
    sym = {}
    bad = set()
    for src, d in (("seed", seed), ("data", mine)):
        for k, v in d["symbols"].items():
            if not isinstance(v, dict):
                continue
            cur = sym.get(k)
            if cur and (cur.get("logic") or "") != (v.get("logic") or ""):
                bad.add(k)
                continue
            if cur:
                cur["sources"] = (cur.get("sources") or []) + (v.get("sources") or [])
                continue
            sym[k] = {**v, "origin": src}
    for k in bad:
        sym.pop(k, None)
    figs = [f for f in seed["figures"] + mine["figures"] if isinstance(f, dict) and f.get("fig")]
    return {"symbols": sym, "figures": figs, "typicals": mine["typicals"], "learned_jobs": mine["learned_jobs"],
            "conflicts": sorted(bad), "taught": [r for r in mine["taught"] if isinstance(r, dict)]}


def as_legend(lib=None) -> dict:
    """legend.read 와 같은 꼴 — blocks._drawn 이 그대로 읽는다."""
    lib = lib or load()
    mp, names = {}, {}
    for k, v in lib["symbols"].items():
        src = (v.get("sources") or [{}])[0]
        hit = {"name": v.get("name", ""), "logic": v.get("logic", ""), "page": None, "label": v.get("label", ""),
               "lib": src.get("from") or v.get("origin", "")}
        if v.get("param"):
            hit["param"] = v["param"]
        if hit["logic"]:
            mp[k] = hit
        elif hit["name"]:
            names[k] = hit["name"]
    figs = [{"fig": f["fig"], "name": f.get("name", ""), "logic": f.get("logic", ""), "page": None,
             "label": f.get("label", ""), "lib": f.get("from", "")} for f in lib["figures"]]
    return {"map": mp, "names": names, "figures": figs, "rows": [], "pages": []}


def merge(leg: dict, lib_leg: dict) -> dict:
    """묶음 범례 + 사전.  묶음 범례가 말한 열쇠 · 그림 이름은 사전이 덮지 않는다."""
    out = {**leg, "map": dict(leg.get("map") or {}), "names": dict(leg.get("names") or {}),
           "figures": list(leg.get("figures") or [])}
    own = set(out["map"]) | set(out["names"])
    for k, v in lib_leg["map"].items():
        if k not in own:
            out["map"][k] = v
    for k, v in lib_leg["names"].items():
        if k not in own:
            out["names"][k] = v
    have = {f["name"] for f in out["figures"]}
    out["figures"] += [f for f in lib_leg["figures"] if f["name"] not in have]
    return out


def _save(d: dict):
    store._atomic(data_path(), json.dumps(d, ensure_ascii=False))


def _add_symbol(d, key, name, logic, label, source, param=None):
    cur = d["symbols"].get(key)
    if cur and (cur.get("logic") or "") != (logic or ""):
        # 다른 동작 — 사람이 정한 것은 새 값이 이긴다 (사람이 고친 것이 최신 판단), 범례끼리 다르면 앞의 것을 둔다
        if source.get("kind") != "USER":
            return False
        cur = None
    if cur:
        if not any(s.get("from") == source.get("from") and s.get("kind") == source.get("kind") for s in cur.get("sources", [])):
            cur.setdefault("sources", []).append(source)
        return False
    ent = {"name": name, "logic": logic, "label": label, "sources": [source], "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    if param:
        ent["param"] = param
    d["symbols"][key] = ent
    return True


def learn_user(key, func, logic, label, author, bundle, param=None) -> dict | None:
    """사람이 판정 못 한 블록의 종류를 정했다 — 그 모양 열쇠를 사전에 남긴다 (다음 묶음 · 다른 프로젝트에서 쓰인다)."""
    if not specific(key):
        return None
    with _LOCK:
        d = _read(data_path())
        new = _add_symbol(d, key, func, logic, label,
                          {"kind": "USER", "from": bundle, "author": author, "at": time.strftime("%Y-%m-%d %H:%M:%S")}, param)
        _save(d)
    return {"key": key, "name": func, "new": new}


def _tid(bundle, sheet):
    h = hashlib.sha1(f"{bundle}|{sheet.get('sheet_no')}|{sheet.get('title')}".encode("utf-8")).hexdigest()
    return h[:12]


def _typical_copy(s):
    """Typical 시트 하나 — 시뮬레이션 · 새 창 그림에 필요한 것만.  다른 묶음을 가리키는 FM/TO 는 뺀다."""
    keep = ("page", "sheet_no", "title", "logic", "pitch", "frame", "nets", "blocks", "ports", "order")
    out = {k: s.get(k) for k in keep}
    out["rows"] = [{k: v for k, v in r.items() if k not in ("fm", "to", "ref", "refs_in", "ft", "user")} for r in s["rows"]]
    out["table"] = [{k: v for k, v in r.items() if k not in ("fm", "to", "ref", "refs_in", "ft", "user")}
                    for r in s.get("table", [])]
    out["findings"] = []
    out["dangling"], out["stray_arrows"] = [], []
    return out


def learn_from_result(res: dict, job_dir: Path, bundle: str, job: str = "") -> dict:
    """끝난 분석 하나에서 배운다 — 범례 표 열쇠 · 그림 · 매크로가 이어진 Typical 시트.  같은 분석은 한 번만."""
    got = {"symbols": 0, "figures": 0, "typicals": 0}
    learn = (res.get("legend") or {}).get("learn") or {}
    if not learn and (res.get("legend") or {}).get("symbols"):
        # 옛 결과(L21) — 열쇠 → 기능 이름만 있다.  동작은 기능 이름 어휘(config legend_functions)로
        from . import blocks as B
        names = {k.upper(): v for k, v in (B.vocab().get("legend_functions") or {}).items()}
        mp = {}
        for k, nm in res["legend"]["symbols"].items():
            lg = names.get((nm or "").upper())
            if lg:
                mp[k] = {"name": nm, "logic": lg, "label": "", "page": None}
        learn = {"map": mp}
    with _LOCK:
        d = _read(data_path())
        if job and job in d["learned_jobs"]:
            return got
        for k, v in (learn.get("map") or {}).items():
            if _add_symbol(d, k, v.get("name", ""), v.get("logic", ""), v.get("label", ""),
                           {"kind": "LEGEND", "from": bundle, "page": v.get("page")}):
                got["symbols"] += 1
        for k, nm in (learn.get("names") or {}).items():
            if _add_symbol(d, k, nm, "", "", {"kind": "LEGEND", "from": bundle}):
                got["symbols"] += 1
        names = {f.get("name") for f in d["figures"]}
        for f in learn.get("figures") or []:
            if f.get("fig") and f.get("name") not in names:
                d["figures"].append({"fig": f["fig"], "name": f.get("name", ""), "logic": f.get("logic", ""),
                                     "label": f.get("label", ""), "from": bundle})
                names.add(f.get("name"))
                got["figures"] += 1
        by_page = {s["page"]: s for s in res.get("sheets", [])}
        used = {}
        for s in res.get("sheets", []):
            for b in s["blocks"].values():
                m = b.get("macro") or {}
                if b.get("func") == "MACRO" and m.get("page") in by_page and not m.get("library"):
                    used.setdefault(m["page"], b.get("caption") or b.get("label") or "")
        for page, cap in used.items():
            s = by_page[page]
            tid = _tid(bundle, s)
            if tid in d["typicals"]:
                continue
            png = None
            src = job_dir / "pages" / f"p{page}_z{store.ZOOM}.png"
            try:
                if not src.exists():
                    src = store.page_png(job_dir, page)
                png = f"typ_{tid}.png"
                shutil.copyfile(src, typ_dir() / png)
            except Exception:
                png = None
            d["typicals"][tid] = {"sheet_no": s.get("sheet_no", ""), "title": s.get("title", ""), "caption": cap[:200],
                                  "from": bundle, "png": png, "zoom": store.ZOOM, "size": None,
                                  "sheet": _typical_copy(s), "at": time.strftime("%Y-%m-%d %H:%M:%S")}
            got["typicals"] += 1
        if job:
            d["learned_jobs"].append(job)
        _save(d)
    return got


def mtime():
    try:
        return data_path().stat().st_mtime_ns
    except OSError:
        return None


def taught_rules(exclude_bundle="") -> list:
    """L25 — 다른 묶음에서 사람이 가르친 게이트 규칙 (모양 서명 + 그림 → 종류).  같은 묶음의 것은 그 묶음 규칙이 이미 있다."""
    out = []
    for r in _read(data_path())["taught"]:
        if not isinstance(r, dict) or not r.get("sig") or r.get("from") == exclude_bundle:
            continue
        out.append({**r, "from": "library", "bundle": r.get("from", "")})
    return out


def learn_rule(rule: dict, bundle: str) -> dict:
    """사람이 가르친 게이트 규칙을 사전에 — 같은 서명 · 같은 그림이면 새 답이 이긴다 (사람이 고친 것이 최신 판단)."""
    from . import teach as T
    with _LOCK:
        d = _read(data_path())
        keep = [r for r in d["taught"] if not (isinstance(r, dict) and
                                                T._same(r.get("sig") or {}, r.get("fig") or "", rule["sig"], rule.get("fig") or ""))]
        if rule.get("choice"):
            keep.append({k: rule.get(k) for k in ("id", "sig", "fig", "choice", "param", "author", "at")} | {"from": bundle})
        d["taught"] = keep
        _save(d)
    return {"rules": len(keep)}


def summary() -> dict:
    lib = load()
    return {"symbols": len(lib["symbols"]), "figures": len(lib["figures"]), "typicals": len(lib["typicals"]),
            "taught": len(lib["taught"]),
            "user_symbols": sum(1 for v in lib["symbols"].values() if any(s.get("kind") == "USER" for s in v.get("sources", []))),
            "conflicts": lib["conflicts"],
            "items": [{"key": k, "name": v.get("name"), "logic": v.get("logic"),
                       "from": sorted({s.get("from") or "" for s in v.get("sources", [])} or {v.get("origin", "")})}
                      for k, v in sorted(lib["symbols"].items())],
            "typical_list": [{"id": k, "sheet_no": v.get("sheet_no"), "title": v.get("title"), "from": v.get("from")}
                             for k, v in lib["typicals"].items()]}


_BACKFILL = {"started": False}
BACKFILL_PAUSE = 0.5


def backfill_async():
    """서버가 처음 LOGIC 목록을 읽을 때 한 번 — 이미 끝난 분석들에서 배운다 (업데이트 전에 분석한 묶음도 사전에 들어간다)."""
    if _BACKFILL["started"]:
        return
    _BACKFILL["started"] = True

    def work():
        try:
            done = set(_read(data_path())["learned_jobs"])
            for j in store.jobs():
                if j.get("state") != "done" or j["id"] in done:
                    continue
                try:
                    d = store.job_dir(j["id"])
                    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
                    learn_from_result(res, d, j.get("name") or j["id"], job=j["id"])
                except Exception:
                    continue
                finally:
                    res = None
                time.sleep(BACKFILL_PAUSE)         # L29 — 한 묶음씩 쉬어 가며 — 그동안 화면 요청이 먼저 돈다
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()
