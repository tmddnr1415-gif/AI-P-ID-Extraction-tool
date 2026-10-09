"""hotfix74 — 같은 도면을 **현장에서 흔히 오는 모양**으로 바꿔 분석해 본다.

재료는 `tests/data/synthetic/08b_tagged_same_size.pdf` (AL NOUF1 범례 4장 + P&ID 2장 · 태그 활자).
같은 내용이어야 하는 변형은 **행 수가 원본과 같아야** 하고, 내용이 달라진 변형은 끝까지 돌거나 사람 말로
멈춰야 한다.  분석은 변형마다 새 프로세스 (서로 새지 않게 · 시간 상한 15분).

    python3 spike/variant_inputs.py out/hotfix74/variants
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/hotfix74/variants")
OUT.mkdir(parents=True, exist_ok=True)
SRC = ROOT / "tests/data/synthetic/08b_tagged_same_size.pdf"
VD = OUT / "pdf"
VD.mkdir(exist_ok=True)


def base():
    return pymupdf.open(SRC)


def save(d, name, **kw):
    p = VD / name
    d.save(p, **kw)
    return p


def v_cropbox():
    d = base()
    for pg in d:
        r = pg.mediabox
        pg.set_cropbox(pymupdf.Rect(r.x0 + 6, r.y0 + 6, r.x1 - 6, r.y1 - 6))
    return save(d, "v01_cropbox_inset.pdf"), "same"


def v_mediabox_origin():
    """MediaBox 원점이 0 이 아닌 PDF (CAD 내보내기에서 흔하다) — 내용은 같다."""
    d = base()
    out = pymupdf.open()
    for pg in d:
        r = pg.rect
        np_ = out.new_page(width=r.width, height=r.height)
        np_.show_pdf_page(np_.rect, d, pg.number)   # 보이는 모양 그대로 그린다 — 회전을 다시 걸지 않는다
    p = VD / "v02_reflowed_xobject.pdf"
    out.save(p)
    return p, "run"


def v_owner_pw():
    d = base()
    return save(d, "v03_owner_password_only.pdf", encryption=pymupdf.PDF_ENCRYPT_AES_256,
                owner_pw="o", permissions=pymupdf.PDF_PERM_PRINT), "same"


def v_incremental():
    p = VD / "v04_incremental.pdf"
    d = base(); d.save(p); d.close()
    d = pymupdf.open(p)
    d.set_metadata({"title": "rev update", "author": "someone"})
    d.saveIncr() if hasattr(d, "saveIncr") else d.save(p, incremental=True, encryption=0)
    return p, "same"


def v_blank_cover():
    d = base()
    r = d[0].rect
    d.new_page(0, width=r.width, height=r.height)
    return save(d, "v05_blank_cover.pdf"), "same"


def v_a4_cover():
    d = base()
    pg = d.new_page(0, width=595, height=842)
    pg.insert_text((72, 100), "DOCUMENT COVER SHEET", fontsize=20)
    pg.insert_text((72, 140), "TRANSMITTAL No. 0001 - FOR APPROVAL", fontsize=12)
    return save(d, "v06_a4_cover.pdf"), "same"


def v_annots():
    d = base()
    for pg in d:
        a = pg.add_freetext_annot(pymupdf.Rect(300, 300, 520, 360), "CHECK THIS PIT TAG", fontsize=10)
        a.set_info(title="reviewer.kim"); a.update()
        b = pg.add_text_annot((600, 600), "comment")
        b.set_info(title="reviewer.kim"); b.update()
        pg.add_rect_annot(pymupdf.Rect(700, 700, 900, 800))
    return save(d, "v07_review_annotations.pdf"), "same"


def v_extra_rotation():
    d = base()
    pg = d[4]
    pg.set_rotation((pg.rotation + 90) % 360)
    return save(d, "v08_one_sheet_rotated.pdf"), "run"


def v_many_pages():
    d = base()
    n0 = d.page_count
    for _ in range(12):
        d.insert_pdf(base(), from_page=4, to_page=5)
    return save(d, f"v09_many_pages_{d.page_count}.pdf"), "run"


def v_trailing_garbage():
    p = VD / "v10_trailing_garbage.pdf"
    p.write_bytes(SRC.read_bytes() + b"\n%%garbage after EOF\n" + bytes(range(256)) * 20)
    return p, "same"


def v_tiny_page():
    d = base()
    d.new_page(-1, width=100, height=100)
    return save(d, "v11_tiny_last_page.pdf"), "same"


def v_huge_page():
    d = base()
    src = base()
    pg = d.new_page(-1, width=14000, height=10000)
    pg.show_pdf_page(pg.rect, src, 5)
    return save(d, "v12_huge_page.pdf"), "run"


def v_broken_xref():
    raw = bytearray(SRC.read_bytes())
    i = raw.rfind(b"startxref")
    if i > 0:
        raw[i + 10:i + 20] = b"9999999999"[: len(raw[i + 10:i + 20])]
    p = VD / "v13_broken_xref.pdf"
    p.write_bytes(bytes(raw))
    return p, "same"


def v_page_labels():
    d = base()
    d.set_page_labels([{"startpage": 0, "prefix": "L-", "style": "D", "firstpagenum": 1}])
    return save(d, "v14_page_labels.pdf"), "same"


def v_only_legend():
    d = base()
    d.delete_pages(from_page=4, to_page=d.page_count - 1)
    return save(d, "v15_only_legend.pdf"), "run"


def v_compressed_garbage():
    d = base()
    return save(d, "v16_garbage_collected.pdf", garbage=4, deflate=True, clean=True), "same"


MAKERS = [v_cropbox, v_mediabox_origin, v_owner_pw, v_incremental, v_blank_cover, v_a4_cover, v_annots,
          v_extra_rotation, v_many_pages, v_trailing_garbage, v_tiny_page, v_huge_page, v_broken_xref,
          v_page_labels, v_only_legend, v_compressed_garbage]

RUN = r'''
import json, sys, time
sys.path.insert(0, sys.argv[2])
from pathlib import Path
from app import pipeline
t0 = time.time()
out = {}
try:
    r = pipeline.analyse(Path(sys.argv[1]))
    out = {"ok": True, "rows": len(r["rows"]), "fp": pipeline.fingerprint(r)[:8],
           "tabs": {}, "pages": len(r.get("pages") or [])}
    for x in r["rows"]:
        out["tabs"][x["tab"]] = out["tabs"].get(x["tab"], 0) + 1
except Exception as e:
    out = {"ok": False, "kind": type(e).__name__, "msg": str(e)[:400]}
out["s"] = round(time.time() - t0, 1)
print("RESULT " + json.dumps(out, ensure_ascii=False))
'''


def analyse(p: Path) -> dict:
    t0 = time.time()
    try:
        cp = subprocess.run([sys.executable, "-c", RUN, str(p), str(ROOT)], capture_output=True, text=True,
                            timeout=900, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return {"ok": False, "kind": "TIMEOUT", "msg": "15분 넘김", "s": round(time.time() - t0)}
    line = [x for x in cp.stdout.splitlines() if x.startswith("RESULT ")]
    if not line:
        return {"ok": False, "kind": "CRASH", "msg": (cp.stderr or "")[-400:], "s": round(time.time() - t0)}
    return json.loads(line[-1][7:])


results = {}
b = analyse(SRC)
results["원본 08b"] = b
print("원본", b, flush=True)
only = set(sys.argv[2:])
for mk in MAKERS:
    if only and mk.__name__ not in only:
        continue
    try:
        p, expect = mk()
    except Exception as e:                                             # noqa: BLE001
        results[mk.__name__] = {"ok": False, "kind": "MAKE_FAILED", "msg": str(e)}
        print(mk.__name__, "만들기 실패", e, flush=True)
        continue
    r = analyse(p)
    r["file"] = p.name
    r["expect"] = expect
    verdict = ""
    if expect == "same":
        verdict = "OK" if r.get("ok") and r.get("rows") == b.get("rows") else "★ 원본과 다름"
    else:
        human = (not r.get("ok")) and any("가" <= ch <= "힣" for ch in r.get("msg", "")) \
            and r.get("kind") not in ("CRASH", "TIMEOUT")
        verdict = "OK" if r.get("ok") or human else "★ 사람 말 없이 멈춤"
    r["verdict"] = verdict
    results[mk.__name__] = r
    print(f"{mk.__name__:24} {verdict:12} {json.dumps(r, ensure_ascii=False)[:260]}", flush=True)
(OUT / "result.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
