"""hotfix82 [C] — 밸브 모양 사전 만들기 (학습).

    python3 spike/shape_train.py --pdf data/pid_total.pdf [--pdf data/TC2_260821.pdf …]
                                 [--verdicts out/verdicts/QFE.json …] [--out <data_dir>/shape_library.json]
                                 [--tagged-only]

보기는 둘에서 온다 (`app/engine/shape_library.py` 머리 규칙 ①):
  RULE   그 문서의 범례 규칙이 판정한 몸체 — 종류는 범례 어휘 그대로.  `--tagged-only` 면 태그 버블이 붙은 몸체만.
  VOC_O  사람이 식별 VOC 탭에서 O 로 확인한 **사전 판정** 행 — 그 자리의 그림을 보기로 더한다 (PDF 가 --pdf 에 있을 때).
그리고 X 로 거른 사전 판정 행의 보기는 `vetoed` 에 올라 다시 쓰지 않는다.

문턱은 사전이 스스로 잰다 (규칙 ③).  만든 뒤 요약(종류별 보기 수 · 문턱 · 근거)을 찍는다.  운영 PC 에 두는 자리는
`<data_dir>/shape_library.json` — 없으면 분석은 예전과 글자 그대로 같다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app" / "engine"))


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def learn_pdf(lib, pdf: Path, *, tagged_only=False, project="", log=print) -> dict:
    """한 PDF 의 규칙 판정 몸체를 보기로.  돌려주는 것은 집계."""
    import pidcache
    import detect_valves as dv
    from app.engine import shape_library as sl
    doc_id = _sha(pdf)[:12]
    _d, pages = pidcache.load_pages(pdf)
    lay, _derived = dv.derive_layout(pages)
    dv.LAYOUT = lay                                  # 이 프로세스(학습 도구)에서만
    results, _lib = dv.analyse_all(pages, derive=False)
    n_added = n_seen = 0
    kinds: dict = {}
    for pno, res in sorted(results.items()):
        pc = next(p for p in pages if p.page_no == pno)
        for b in res["bodies"]:
            if (b.evidence or {}).get("body_source") == sl.BODY_SOURCE:
                continue                             # 사전이 판정한 것은 보기가 아니다 (순환)
            if tagged_only and not b.tag:
                continue
            n_seen += 1
            bm = sl.descriptor(pc, b.rect)
            if bm is None:
                continue
            e = sl.add_exemplar(lib, bm, b.kind, "RULE", project=project or pdf.stem, doc=doc_id, page_no=pno,
                                rect=(b.rect.x0, b.rect.y0, b.rect.x1, b.rect.y1))
            kinds[b.kind] = kinds.get(b.kind, 0) + 1
            n_added += 1
    log(f"  {pdf.name}: 몸체 {n_seen} → 보기 {n_added} (종류 {kinds})")
    return {"pdf": str(pdf), "doc": doc_id, "bodies": n_seen, "added": n_added, "kinds": kinds, "pages": pages}


def apply_verdicts(lib, vfile: Path, pdfs_by_doc: dict, log=print) -> dict:
    """정답지(out/verdicts/<이름>.json)의 사전 판정 행 — X 는 보기 거름 · O 는 보기 더함."""
    from app.engine import shape_library as sl
    vs = json.loads(vfile.read_text(encoding="utf-8"))
    vetoed = added = skipped = 0
    for it in vs.get("items") or []:
        if it.get("body_source") != sl.BODY_SOURCE:
            continue
        if it.get("verdict") == "X":
            ex = it.get("exemplar") or ""
            if ex:
                lib.vetoed[ex] = f"{vs.get('project')} {it.get('drawing_no')} {it.get('type')} X — {it.get('author') or ''}"
                vetoed += 1
            continue
        if it.get("verdict") != "O":
            continue
        doc = (it.get("pdf_sha256") or "")[:12]
        pages = pdfs_by_doc.get(doc)
        rect, kind = it.get("rect"), it.get("kind") or ""
        if not pages or not rect or not kind or not it.get("page_no"):
            skipped += 1
            continue
        pc = next((p for p in pages if p.page_no == it["page_no"]), None)
        bm = sl.descriptor(pc, rect) if pc is not None else None
        if bm is None:
            skipped += 1
            continue
        sl.add_exemplar(lib, bm, kind, "VOC_O", project=vs.get("project") or "", doc=doc, page_no=it["page_no"], rect=rect)
        added += 1
    log(f"  {vfile.name}: 사전 판정 행 중 X 로 거른 보기 {vetoed} · O 로 더한 보기 {added} · PDF 가 없어 못 더한 것 {skipped}")
    return {"vetoed": vetoed, "added": added, "skipped": skipped}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", action="append", default=[], help="보기를 모을 PDF (여러 번)")
    ap.add_argument("--verdicts", action="append", default=[], help="정답지 json (spike/voc.py verdicts 가 만든 것)")
    ap.add_argument("--out", help="사전 파일 (기본 <data_dir>/shape_library.json)")
    ap.add_argument("--tagged-only", action="store_true", help="태그 버블이 붙은 몸체만 보기로")
    ap.add_argument("--project", default="", help="보기에 적을 프로젝트 이름 (기본 PDF 이름)")
    a = ap.parse_args(argv)
    from app.engine import shape_library as sl
    out = Path(a.out) if a.out else sl.default_path()
    lib = sl.load(out) if out.exists() else None
    if lib is None:
        lib = sl.new_library()
    else:
        print(f"기존 사전을 잇습니다: {out} (보기 {len(lib.exemplars)} · 거른 것 {len(lib.vetoed)})")
    lib.built_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    by_doc = {}
    t0 = time.time()
    for p in a.pdf:
        r = learn_pdf(lib, Path(p), tagged_only=a.tagged_only, project=a.project)
        by_doc[r["doc"]] = r["pages"]
    for v in a.verdicts:
        apply_verdicts(lib, Path(v), by_doc)
    sl.derive_threshold(lib)
    sl.save(lib, out)
    s = lib.summary()
    print(f"사전: {out}")
    print(f"  보기 {s['exemplars']} (거른 것 {s['vetoed']}) · 종류 {s['kinds']}")
    print(f"  문턱 {s['threshold']} — {s['basis']}")
    print(f"  {time.time() - t0:.0f}초")
    if not lib.usable():
        print("  ⚠ 이 사전은 판정하지 않습니다 — 보기가 둘 미만이거나 문턱이 서지 않았습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
