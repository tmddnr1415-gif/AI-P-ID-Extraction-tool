"""hotfix70 — `pidcache.Rot` 가 PyMuPDF 의 `* m` 과 비트까지 같은 값을 내는지 한 문서 전 장에서 맞대 본다.

    python3 spike/rot_exact_check.py data/TC2_260821.pdf [첫장 끝장]

모든 그림 항목의 점(선 두 끝 · 곡선 네 점 · 사변형 모서리)과 사각형(그림 rect · `re` 항목 · 낱말 상자)을
두 길로 옮겨 하나라도 다르면 실패.  시간도 같이 잰다.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "app" / "engine")]
import pymupdf  # noqa: E402
import pidcache  # noqa: E402


def main():
    pdf = sys.argv[1]
    doc = pymupdf.open(pdf)
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else doc.page_count
    n_pt = n_rect = bad = 0
    t_old = t_new = 0.0
    rots = {}
    for pno in range(lo, hi + 1):
        pg = doc[pno - 1]
        m = pg.rotation_matrix
        R = pidcache.Rot(m)
        rots[pg.rotation] = rots.get(pg.rotation, 0) + 1
        pts, rects = [], []
        for d in pg.get_drawings():
            rects.append(d["rect"])
            for it in d["items"]:
                if it[0] == "l":
                    pts += [it[1], it[2]]
                elif it[0] == "c":
                    pts += [it[1], it[2], it[3], it[4]]
                elif it[0] == "qu":
                    pts += [it[1].ul, it[1].lr]
                elif it[0] == "re":
                    rects.append(it[1])
        rects += [pymupdf.Rect(w[:4]) for w in pg.get_text("words")]
        t = time.perf_counter(); old_p = [pymupdf.Point(p) * m for p in pts]
        old_r = [pymupdf.Rect(r) * m for r in rects]; t_old += time.perf_counter() - t
        t = time.perf_counter(); new_p = [R.pt(p) for p in pts]
        new_r = [R.rect(r) for r in rects]; t_new += time.perf_counter() - t
        lines = [(it[1], it[2]) for d in pg.get_drawings() for it in d["items"] if it[0] == "l"]
        old_s = [(pymupdf.Point(a) * m, pymupdf.Point(b) * m) for a, b in lines]
        new_s = R.segs(lines)
        old_p += [p for ab in old_s for p in ab]
        new_p += [p for ab in new_s for p in ab]

        def same(a, b):
            return type(a) is type(b) and vars(a) == vars(b) and tuple(map(repr, a)) == tuple(map(repr, b))
        bad += sum(not same(a, b) for a, b in zip(old_p, new_p)) + abs(len(old_p) - len(new_p))
        bad += sum(not same(a, b) for a, b in zip(old_r, new_r)) + abs(len(old_r) - len(new_r))
        n_pt += len(pts); n_rect += len(rects)
    print(f"{Path(pdf).name} p{lo}-{hi} rotations {rots} · points {n_pt} · rects {n_rect} · "
          f"mismatch {bad} · old {t_old:.1f}s new {t_new:.1f}s · fast={pidcache._ROT_OK}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
