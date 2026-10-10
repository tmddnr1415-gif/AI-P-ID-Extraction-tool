"""hotfix82 [C] — 밸브 모양 사전: 규칙이 못 가른 중공 몸체를 **확정된 보기**(규칙이 판정한 몸체 · 사람이 O 로 확인한
행)의 모양에 맞대어 판정한다.

왜 (§9): 몸체 기하 규칙은 양식마다 그리는 법이 달라 계속 깨졌다 (40·41·43·54회차 — 대각선을 네 토막으로 · 끝막대 없음
· 두 삼각형을 따로).  그런데 같은 모양을 **그림으로** 보면 어느 양식이든 같다.  그래서 규칙이 판정한 몸체의 정규화
그림을 보기로 모아 두고, 끝막대 둘은 갖췄는데 어휘에 없는 중공 도형(`unclassified_bodies`)을 그 보기에 맞댄다.

규칙 셋 — 전부 사전 자신에게서 온다 (새 상수 0):
  ① 보기는 **규칙이 판정한 몸체**(종류가 그 문서의 범례 어휘)와 **사람이 O 로 확인한 사전 판정 행**뿐이다.  X 로 거른
     보기는 다시 쓰지 않는다 (`vetoed`).
  ② 그림은 크기·자리·획 굵기와 무관하다 (잉크 마스크 → 잉크로 자르기 → 고정 격자 평균 · `extract_titleblocks._normalise`
     와 같은 길).  회전·뒤집기 여덟 가지 중 가장 가까운 것으로 잰다 — 가로·세로 밸브가 같은 보기에 맞는다.
  ③ **문턱은 사전이 정한다**: 같은 종류끼리의 최근접 거리의 최댓값(`within_max`)과 다른 종류 사이의 최솟값(`cross_min`)
     중 작은 쪽.  사이가 비어 있으면(`cross_min > within_max`) 그 띠가 근거이고, 종류가 하나면 `within_max` 가 문턱이다.
     보기가 하나뿐이면 문턱이 서지 않아 사전은 아무것도 판정하지 않는다.

사전이 없으면 **아무 일도 하지 않는다** — 네 기준 문서의 지문이 구조적으로 안 움직인다.  사전으로 판정한 몸체는
`evidence.body_source == "SHAPE_LIBRARY"` 로 어느 보기(출처 문서·장·자리)에 얼마나 가까웠는지를 말하고, 행은 검토 사유
`BODY_FROM_SHAPE_LIBRARY` 를 단다 (§9 ④ — 조용히 진행하지 않는다).  이 모듈은 `detect_valves` 를 import 하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_titleblocks as _tb   # noqa: E402

FILE_NAME = "shape_library.json"
SCHEMA = 1
GRID = (24, 24)                      # 정사각 격자 — 90° 회전이 같은 격자에 떨어진다
BODY_SOURCE = "SHAPE_LIBRARY"
REVIEW_CODE = "BODY_FROM_SHAPE_LIBRARY"
ENV_OFF = "PID_SHAPE_LIBRARY"        # "0" 이면 사전이 있어도 안 쓴다
ENV_FILE = "PID_SHAPE_LIBRARY_FILE"  # 사전 파일 자리 (기본 <data_dir>/shape_library.json) — 회귀 실험이 쓴다

_LAY = _tb.Layout(grid=GRID)


# ---------------------------------------------------------------- 그림
def descriptor(pc, rect) -> np.ndarray | None:
    """그 자리의 정규화 그림 (GRID · 0~1).  잉크가 없으면 None."""
    r = pymupdf.Rect(*rect) if not isinstance(rect, pymupdf.Rect) else rect
    if r.is_empty or r.width < 1 or r.height < 1:
        return None
    mask = _tb._ink_mask(pc.page, r, _LAY)
    if mask is None:
        return None
    return _tb._normalise(mask, _LAY)


def variants(bm: np.ndarray) -> list[np.ndarray]:
    """회전 넷 × 뒤집기 둘 — 가로·세로 밸브, 거울상이 같은 보기에 맞는다."""
    out = []
    for k in range(4):
        r = np.rot90(bm, k)
        out.append(r)
        out.append(np.fliplr(r))
    return out


def distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.abs(a - b).mean())


def nearest(bm: np.ndarray, stack: np.ndarray) -> tuple[int, float]:
    """`stack` (n, h, w) 에서 가장 가까운 보기 — 여덟 변형 중 최솟값.  (index, distance)."""
    if stack.shape[0] == 0:
        return -1, float("inf")
    best_i, best_d = -1, float("inf")
    for v in variants(bm):
        d = np.abs(stack - v[None]).mean(axis=(1, 2))
        i = int(d.argmin())
        if d[i] < best_d:
            best_i, best_d = i, float(d[i])
    return best_i, best_d


def _hash(bm: np.ndarray) -> str:
    """같은 그림인가 — 0.05 단위로 접은 값.  같은 벡터를 같은 축척으로 그린 것은 똑같이 떨어지고, 얇은 선 하나가
    더 있는 그림(칸 평균 0.2 쯤)은 갈린다.  0.5 문턱 비트로 접으면 그 얇은 선이 사라져 다른 모양이 하나가 됐다."""
    return hashlib.sha1(np.round(bm * 20).astype(np.uint8).tobytes()).hexdigest()[:12]


# ---------------------------------------------------------------- 사전
@dataclass
class Exemplar:
    kind: str
    bitmap: list                  # GRID 행렬 (JSON)
    source: str                   # RULE | VOC_O
    project: str = ""
    doc: str = ""                 # pdf sha256 앞 12자
    page_no: int = 0
    rect: list = field(default_factory=list)
    count: int = 1                # 같은 그림이 몇 번 나왔나 (중복은 하나로)
    id: str = ""

    def as_json(self) -> dict:
        return {"id": self.id, "kind": self.kind, "source": self.source, "project": self.project,
                "doc": self.doc, "page_no": self.page_no, "rect": self.rect, "count": self.count,
                "bitmap": [[round(float(v), 3) for v in row] for row in self.bitmap]}


@dataclass
class Library:
    exemplars: list = field(default_factory=list)
    vetoed: dict = field(default_factory=dict)       # exemplar id -> 사유
    threshold: float | None = None
    basis: dict = field(default_factory=dict)
    built_at: str = ""
    _stack: np.ndarray | None = None
    _live: list | None = None

    def live(self) -> list:
        if self._live is None:
            self._live = [e for e in self.exemplars if e.id not in self.vetoed]
        return self._live

    def stack(self) -> np.ndarray:
        if self._stack is None:
            live = self.live()
            self._stack = (np.stack([np.asarray(e.bitmap, dtype=np.float32) for e in live])
                           if live else np.zeros((0,) + GRID, np.float32))
        return self._stack

    def usable(self) -> bool:
        return self.threshold is not None and len(self.live()) >= 2

    def match(self, bm: np.ndarray):
        """(Exemplar, distance) 또는 None — 문턱 안에 있을 때만."""
        if not self.usable() or bm is None:
            return None
        i, d = nearest(bm, self.stack())
        if i < 0 or d > self.threshold:
            return None
        return self.live()[i], d

    def summary(self) -> dict:
        kinds: dict = {}
        for e in self.live():
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        return {"exemplars": len(self.live()), "vetoed": len(self.vetoed), "kinds": kinds,
                "threshold": self.threshold, "basis": self.basis, "built_at": self.built_at}

    def as_json(self) -> dict:
        return {"schema": SCHEMA, "grid": list(GRID), "built_at": self.built_at,
                "threshold": self.threshold, "basis": self.basis, "vetoed": self.vetoed,
                "exemplars": [e.as_json() for e in self.exemplars]}


def default_path() -> Path:
    override = os.environ.get(ENV_FILE)
    if override:
        return Path(override).expanduser()
    from app import paths
    return paths.data_dir() / FILE_NAME


def enabled() -> bool:
    return os.environ.get(ENV_OFF, "1") != "0"


def load(path: Path | None = None) -> Library | None:
    """사전 파일 → Library.  없거나(기본) 꺼져 있으면 None — 그러면 판정은 예전과 글자 그대로 같다."""
    if not enabled():
        return None
    p = Path(path) if path is not None else default_path()
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or d.get("schema") != SCHEMA or list(d.get("grid") or []) != list(GRID):
        return None
    lib = Library(threshold=d.get("threshold"), basis=d.get("basis") or {}, vetoed=dict(d.get("vetoed") or {}),
                  built_at=d.get("built_at") or "")
    for e in d.get("exemplars") or []:
        bm = e.get("bitmap")
        if not bm or len(bm) != GRID[0] or any(len(r) != GRID[1] for r in bm):
            continue
        lib.exemplars.append(Exemplar(kind=str(e.get("kind") or ""), bitmap=bm, source=str(e.get("source") or "RULE"),
                                      project=str(e.get("project") or ""), doc=str(e.get("doc") or ""),
                                      page_no=int(e.get("page_no") or 0), rect=list(e.get("rect") or []),
                                      count=int(e.get("count") or 1), id=str(e.get("id") or "")))
    return lib


def save(lib: Library, path: Path) -> None:
    from app import jsonstore
    jsonstore.write(Path(path), lib.as_json())


# ---------------------------------------------------------------- 만들기
def add_exemplar(lib: Library, bm: np.ndarray, kind: str, source: str, *, project="", doc="", page_no=0, rect=()) -> Exemplar:
    """같은 그림(0.5 문턱의 비트)은 하나로 — 횟수만 는다."""
    h = f"{kind}:{_hash(bm)}"
    for e in lib.exemplars:
        if e.id == h:
            e.count += 1
            return e
    e = Exemplar(kind=kind, bitmap=[[float(v) for v in row] for row in bm], source=source, project=project,
                 doc=doc, page_no=page_no, rect=[round(float(v), 1) for v in rect], id=h)
    lib.exemplars.append(e)
    lib._stack = None; lib._live = None
    return e


def derive_threshold(lib: Library) -> None:
    """③ — 같은 종류 최근접의 최댓값과 다른 종류 최솟값에서.  보기가 둘 미만이면 문턱 없음."""
    live = lib.live()
    lib._stack = None
    if len(live) < 2:
        lib.threshold, lib.basis = None, {"reason": "보기가 둘 미만 — 문턱을 잴 수 없어 사전은 판정하지 않는다"}
        return
    stack = lib.stack()
    kinds = [e.kind for e in live]
    within, cross = [], []
    for i, e in enumerate(live):
        bm = np.asarray(e.bitmap, dtype=np.float32)
        best = {}
        for v in variants(bm):
            d = np.abs(stack - v[None]).mean(axis=(1, 2))
            for j in range(len(live)):
                if j == i:
                    continue
                best[j] = min(best.get(j, float("inf")), float(d[j]))
        same = [best[j] for j in best if kinds[j] == e.kind]
        diff = [best[j] for j in best if kinds[j] != e.kind]
        if same:
            within.append(min(same))
        if diff:
            cross.append(min(diff))
    within_max = max(within) if within else None
    cross_min = min(cross) if cross else None
    if within_max is None and cross_min is None:
        lib.threshold, lib.basis = None, {"reason": "거리를 잴 짝이 없다"}
        return
    if within_max is None:                      # 종류마다 보기 하나씩 — 같은 종류 짝이 없다
        lib.threshold = round(cross_min / 2, 4)
        lib.basis = {"within_max": None, "cross_min": round(cross_min, 4),
                     "reason": "같은 종류 짝이 없어 다른 종류 최솟값의 절반 — 보기를 더 모으면 다시 선다"}
        return
    if cross_min is None:
        lib.threshold = round(within_max, 4)
        lib.basis = {"within_max": round(within_max, 4), "cross_min": None, "reason": "종류 하나 — 같은 종류 최근접의 최댓값"}
        return
    lib.threshold = round(min(within_max, cross_min), 4)
    lib.basis = {"within_max": round(within_max, 4), "cross_min": round(cross_min, 4),
                 "gap": cross_min > within_max,
                 "reason": ("같은 종류 최댓값 < 다른 종류 최솟값 — 사이가 비어 있다" if cross_min > within_max
                            else "같은 종류와 다른 종류의 거리가 겹친다 — 다른 종류 최솟값 아래만 받는다")}


def new_library() -> Library:
    return Library(built_at=time.strftime("%Y-%m-%dT%H:%M:%S"))


# ---------------------------------------------------------------- 판정
def promote(pc, candidates: list, lib: Library | None) -> list[dict]:
    """규칙이 못 가른 중공 도형(`unclassified_bodies` 의 dict) 중 사전이 알아보는 것.

    돌려주는 것은 `{"kind", "rect", "axis", "evidence"}` — Body 는 부르는 쪽(`detect_valves.analyse`)이 만든다
    (이 모듈은 detect_valves 를 import 하지 않는다).  사전이 없거나 문턱이 없으면 빈 목록."""
    if lib is None or not lib.usable() or not candidates:
        return []
    out = []
    for u in candidates:
        rect = u.get("rect")
        if not rect or len(rect) != 4:
            continue
        bm = descriptor(pc, rect)
        if bm is None:
            continue
        hit = lib.match(bm)
        if hit is None:
            continue
        ex, d = hit
        out.append({"kind": ex.kind, "rect": list(rect), "axis": u.get("axis") or ("H" if rect[2] - rect[0] > rect[3] - rect[1] else "V"),
                    "evidence": {"body_source": BODY_SOURCE, "distance": round(d, 4), "threshold": lib.threshold,
                                 "exemplar": {"id": ex.id, "kind": ex.kind, "source": ex.source, "project": ex.project,
                                              "doc": ex.doc, "page_no": ex.page_no, "rect": ex.rect, "count": ex.count},
                                 "segments": u.get("segments")}})
    return out
