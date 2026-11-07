"""DXF 32장 판독 · 인벤토리 (55회차 [B]).

    python3 spike/dxf_inventory.py data/uad_dxf out/round55

장마다: DXF 버전 · 복구 감사 오류 · 엔티티 수 · INSERT/속성 INSERT · 블록 이름 ·
속성 태그 이름(ATTDEF) · 레이어 · 타이틀블록 속성.  **판정은 하지 않는다** —
등급 규칙은 이 표의 분포를 보고 [B-3] 에서 세운다.
"""
from __future__ import annotations
import collections, json, re, sys, time
from pathlib import Path
import ezdxf
from ezdxf import recover

src = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
NUM = re.compile(r"^\s*(\d+)\s*\.")


def order_key(p: Path):
    m = NUM.match(p.name)
    return (0, int(m.group(1))) if m else (1, p.name)


rows = []
for p in sorted(src.glob("*.dxf"), key=order_key):
    t = time.perf_counter()
    rec = {"file": p.name, "no": (NUM.match(p.name) or [None, None])[1]}
    try:
        doc, aud = recover.readfile(str(p))
    except Exception as exc:                      # 한 장 실패해도 계속
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(rec); print("★ 실패", p.name, rec["error"]); continue
    msp = doc.modelspace()
    ents = collections.Counter(e.dxftype() for e in msp)
    ins = [e for e in msp if e.dxftype() == "INSERT"]
    blocks = collections.Counter(e.dxf.name for e in ins)
    attr_tags = collections.Counter()      # 속성 태그 이름 → 몇 INSERT 에
    attr_blocks = collections.Counter()    # 속성 붙은 INSERT 의 블록 이름
    attr_samples = {}
    for e in ins:
        if not e.attribs:
            continue
        attr_blocks[e.dxf.name] += 1
        for a in e.attribs:
            attr_tags[a.dxf.tag] += 1
        attr_samples.setdefault(e.dxf.name, [(a.dxf.tag, a.dxf.text) for a in e.attribs][:4])
    layers = collections.Counter(e.dxf.layer for e in msp)
    title = {}
    for e in ins:
        if e.dxf.name.upper() == "TITLE" and e.attribs:
            title = {a.dxf.tag: a.dxf.text for a in e.attribs}
    rec.update({
        "version": doc.dxfversion, "audit_errors": len(aud.errors),
        "seconds": round(time.perf_counter() - t, 2),
        "entities": dict(ents), "insert": len(ins),
        "insert_with_attribs": sum(attr_blocks.values()),
        "block_kinds": len(blocks), "blocks": dict(blocks.most_common()),
        "attr_blocks": dict(attr_blocks.most_common()),
        "attr_tags": dict(attr_tags.most_common()),
        "attr_samples": attr_samples,
        "layers": dict(layers.most_common()),
        "pdf_layers": sorted(l for l in layers if l.upper().startswith("PDF")),
        "block_defs": len(list(doc.blocks)),
        "layouts": [l.name for l in doc.layouts],
        "title": title,
    })
    rows.append(rec)
    print(f"{rec['no']} {doc.dxfversion} {rec['seconds']}s INSERT {len(ins)} attr {rec['insert_with_attribs']}"
          f" CIRCLE {ents.get('CIRCLE',0)} LWPOLY {ents.get('LWPOLYLINE',0)} PDF층 {len(rec['pdf_layers'])}")

(out / "dxf_inventory.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
print("→", out / "dxf_inventory.json")
