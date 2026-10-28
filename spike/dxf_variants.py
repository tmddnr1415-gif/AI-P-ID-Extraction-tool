"""hotfix74 — DXF 입력 돌발상황.  UAD DXF 32장 전부를 재료로 묶음을 바꿔 분석한다.

⚠ 처음에는 범례 4장 + 도면 2장으로 묶었는데 그 묶음은 **1행**이었다 — 계기 블록의 TYPE·태그 속성은
같은 태그 모양이 두 장 이상에서 되풀이돼야 배우므로(29회차 규칙) 장이 적으면 계기 행이 서지 않는다.
그러면 "원본과 같다" 가 1행끼리의 비교라 아무것도 재지 못한다.  그래서 전부(507행)를 기준으로 하고,
작은 묶음은 따로(`v11_small_set`) — 행이 적은 대신 그 사실을 결과가 말하는지(`roles_note`)를 본다.

    python3 spike/dxf_variants.py out/hotfix74/dxf_variants

같은 내용이어야 하는 변형(폴더 깊이 · 한글 cp949 이름 · 다른 파일 섞임 · CRLF→LF)은 행 수가 원본과 같아야 하고,
깨진 변형(빈 DXF · 잘린 DXF · 이진 쓰레기 · 범례 없는 묶음)은 사람 말로 멈추거나 그 장만 건너뛰어야 한다.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/hotfix74/dxf_variants")
OUT.mkdir(parents=True, exist_ok=True)
SRC = ROOT / "data/uad_dxf"
pick = sorted(SRC.iterdir())
LEGEND = [p for p in pick if p.name[:3] in ("002", "003", "004", "005")]
SHEETS = [p for p in pick if p not in LEGEND]
BASE = LEGEND + SHEETS
SMALL = LEGEND + [p for p in pick if p.name[:3] in ("006", "016")]


def zipit(name, entries, flag_utf8=True):
    p = OUT / name
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in entries:
            zi = zipfile.ZipInfo(n)
            zi.compress_type = zipfile.ZIP_DEFLATED
            if not flag_utf8:
                # cp949 로 이름을 적는 옛 압축 도구 흉내 (UTF-8 깃발 없이)
                zi.filename = n
            z.writestr(zi, b)
    if not flag_utf8:
        raw = p.read_bytes()
        p.write_bytes(raw)          # zipfile 은 비ASCII 면 UTF-8 깃발을 켠다 — 아래에서 직접 바꾼다
    return p


def cp949_zip(name, entries):
    """UTF-8 깃발 없이 cp949 바이트로 이름을 적은 zip (한국 Windows 기본 압축)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in entries:
            z.writestr("__NAME__%04d.dxf" % len(z.infolist()), b)
    raw = bytearray(buf.getvalue())
    for i, (n, _b) in enumerate(entries):
        tag = ("__NAME__%04d.dxf" % i).encode()
        new = n.encode("cp949", "replace")
        # 이름 길이가 다르면 헤더가 깨지므로 같은 길이로 맞춘다 (뒤를 '_' 로 채우거나 자른다)
        new = (new + b"_" * len(tag))[:len(tag) - 4] + b".dxf"
        raw = raw.replace(tag, new)
    p = OUT / name
    p.write_bytes(bytes(raw))
    return p


def variants():
    yield "v00_base", zipit("v00_base.zip", [(p.name, p.read_bytes()) for p in BASE]), "base"
    yield "v01_nested", zipit("v01_nested.zip", [(f"UAD/P&ID/{i:02d}/{p.name}", p.read_bytes())
                                                 for i, p in enumerate(BASE)]), "same"
    yield "v02_cp949_names", cp949_zip("v02_cp949.zip", [(f"도면_{i}_{p.name}", p.read_bytes())
                                                         for i, p in enumerate(BASE)]), "same"
    yield "v03_extra_files", zipit("v03_extra.zip", [(p.name, p.read_bytes()) for p in BASE]
                                   + [("readme.txt", b"hello"), ("Thumbs.db", b"\0" * 100),
                                      ("__MACOSX/._x.dxf", b"\0\5\x16\7junk"), ("plot.pdf", b"%PDF-1.4 x")]), "same"
    yield "v04_lf_only", zipit("v04_lf.zip", [(p.name, p.read_bytes().replace(b"\r\n", b"\n")) for p in BASE]), "same"
    yield "v05_one_empty", zipit("v05_empty.zip", [(p.name, p.read_bytes()) for p in BASE]
                                 + [("999. empty.dxf", b"")]), "run"
    yield "v06_one_truncated", zipit("v06_trunc.zip", [(p.name, p.read_bytes()) for p in BASE]
                                     + [("998. cut.dxf", SHEETS[0].read_bytes()[:200000])]), "run"
    yield "v07_one_garbage", zipit("v07_garbage.zip", [(p.name, p.read_bytes()) for p in BASE]
                                   + [("997. bin.dxf", bytes(range(256)) * 400)]), "run"
    yield "v08_no_legend", zipit("v08_nolegend.zip", [(p.name, p.read_bytes()) for p in SHEETS]), "run"
    yield "v09_only_garbage", zipit("v09_onlygarbage.zip", [("a.dxf", b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n"),
                                                           ("b.dxf", b"not a dxf at all")]), "run"
    yield "v10_dup_sheet", zipit("v10_dup.zip", [(p.name, p.read_bytes()) for p in BASE]
                                 + [("copy of " + SHEETS[5].name, SHEETS[5].read_bytes())]), "same"
    yield "v11_small_set", zipit("v11_small.zip", [(p.name, p.read_bytes()) for p in SMALL]), "note"


RUN = r'''
import json, sys, time
sys.path.insert(0, sys.argv[2])
from pathlib import Path
from app import pipeline
t0 = time.time()
try:
    r = pipeline.analyse(Path(sys.argv[1]))
    out = {"ok": True, "rows": len(r["rows"]), "fp": pipeline.fingerprint(r)[:8]}
    out["tabs"] = {}
    for x in r["rows"]:
        out["tabs"][x["tab"]] = out["tabs"].get(x["tab"], 0) + 1
    out["skipped"] = str((r.get("dxf") or {}).get("skipped_inputs") or "")[:200]
    out["roles_note"] = (r.get("dxf") or {}).get("roles_note") or ""
except Exception as e:
    out = {"ok": False, "kind": type(e).__name__, "msg": str(e)[:400]}
out["s"] = round(time.time() - t0, 1)
print("RESULT " + json.dumps(out, ensure_ascii=False))
'''


def analyse(p):
    t0 = time.time()
    try:
        cp = subprocess.run([sys.executable, "-c", RUN, str(p), str(ROOT)], capture_output=True, text=True,
                            timeout=1200, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return {"ok": False, "kind": "TIMEOUT", "s": round(time.time() - t0)}
    line = [x for x in cp.stdout.splitlines() if x.startswith("RESULT ")]
    if not line:
        return {"ok": False, "kind": "CRASH", "msg": (cp.stderr or "")[-600:]}
    return json.loads(line[-1][7:])


res, base = {}, None
for name, p, expect in variants():
    r = analyse(p)
    if expect == "base":
        base = r
        verdict = "기준"
    elif expect == "note":
        verdict = "OK" if r.get("ok") and (r.get("rows", 0) >= base.get("rows", 0) or r.get("roles_note")) \
            else "★ 행이 줄었는데 사유가 없음"
    elif expect == "same":
        verdict = "OK" if r.get("ok") and r.get("rows") == base.get("rows") else "★ 원본과 다름"
    else:
        human = (not r.get("ok")) and any("가" <= ch <= "힣" for ch in r.get("msg", "")) \
            and r.get("kind") not in ("CRASH", "TIMEOUT")
        verdict = ("★ 행 0개로 조용히 성공" if r.get("ok") and not r.get("rows")
                   else "OK" if r.get("ok") or human else "★ 사람 말 없이 멈춤")
    r["verdict"] = verdict
    res[name] = r
    print(f"{name:20} {verdict:12} {json.dumps(r, ensure_ascii=False)[:300]}", flush=True)
(OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
