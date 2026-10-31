"""DXF 장을 화면 배경 PNG 로 그린다 (55회차 [E]).

픽셀 ↔ 모델 좌표 변환은 **여기 하나**다: 그림은 장의 범위(`Sheet.extents`)를
정확히 덮고, 픽셀/모델단위 배율은 `PX_PER_UNIT` 하나다.  화면은 이미지 폭과
`page.width` 의 비로 사각형을 놓으므로(`sheetPoint`), 여기서 여백을 두면 그
순간 어긋난다 (33·41회차의 회전 좌표와 같은 덫).

레이어 표가 끈 층은 **그리지 않는다** — AutoCAD 가 플롯하는 대로다.  판정에서
걸러낸 것을 화면에서 지우는 것이 아니라(§[E]3), 문서가 스스로 끈 층을 문서대로
안 그리는 것이다.  켜진 개정 클라우드(`REV.7`)는 그대로 보인다.
"""
from __future__ import annotations

import io

PX_PER_UNIT = 4.0        # A3(841 단위) → 3364px.  56회차에 3.0 에서 올렸다 —
                         # 사람이 버블 안 글자를 읽으려고 크게 확대하는데 3.0 에서는
                         # 한 획이 1px 이라 흐려진다 (그림은 장마다 한 번 그려 캐시된다).

# 56회차 — **흰 종이에서 읽히지 않는 밝기의 글자는 읽힐 때까지 어둡게 한다.**
#
# 현장 보고: *"DXF 의 값, PIT · LIT 등이 너무 잘 안 보인다"*.  원인은 검출도
# 글꼴도 아니라 **그 층의 색**이다 — UAD p6 실측으로 글자 색이 `#000000` 317 ·
# `#ffff00` 57 · `#00ffff` 46 · `#00ff00` 34 · `#ffff7f` 18 … 이고, 노랑·하늘색
# ·연두는 CAD 의 검은 바탕에서는 잘 보이지만 흰 종이에서는 거의 사라진다.
#
# 고치는 방법은 **색을 버리지 않는 것**이다: 색상은 그대로 두고 **밝기만**
# 문턱까지 내린다.  이미 어두운 글자(검정 317건)는 한 칸도 안 움직인다.
# 선에는 걸지 않는다 — 배관·신호·경계의 색은 사람이 그 색으로 읽는 값이고,
# 읽기 어려운 것은 글자였지 선이 아니었다.
INK_MAX_LUMA = 0.42      # sRGB 상대휘도.  흰 종이(1.0)에 대해 대비 약 2.2:1
PAPER_LUMA = 0.96        # 이보다 밝으면 잉크가 아니라 종이다 — 건드리지 않는다


def darken_ink(png: bytes, target: float = INK_MAX_LUMA) -> bytes:
    """옅게 그려진 잉크만 **색상은 그대로 두고 밝기만** 문턱까지 내린다.

    ⚠ 엔티티 단계에서 고치려다 **한 번 뒤집었다.**  `Frontend
    .push_property_override_function` 으로 TEXT·MTEXT·ATTRIB 의 색을 바꿔 봤더니
    호출은 되는데(UAD p6 에서 TEXT 221 · MTEXT 101 · ATTDEF 135 · ATTRIB 22)
    그려진 글자 색은 **한 픽셀도 안 바뀐다** — 일부러 자홍으로 덮어써 확인했다.
    그래서 그리고 난 **그림**에서 고친다: 어느 엔티티 종류든 빠지지 않는다.

    종이(거의 흰색)는 건드리지 않고, 이미 어두운 잉크(검정 글자·검정 선)도
    그대로다.  색상을 유지하므로 층 색으로 읽는 값(파랑 배관 · 자홍 경계)은
    살아 있고, 흰 종이에서 사라지던 노랑·하늘색·연두만 읽히는 밝기로 내려온다.
    """
    import numpy as np
    from PIL import Image

    im = Image.open(io.BytesIO(png)).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    ink = (lum > target) & (lum < PAPER_LUMA)
    if not ink.any():
        return png
    k = np.ones_like(lum)
    k[ink] = target / lum[ink]
    out = np.clip(a * k[..., None], 0.0, 1.0)
    buf = io.BytesIO()
    Image.fromarray((out * 255.0 + 0.5).astype("uint8")).save(buf, format="PNG")
    return buf.getvalue()


def render_png(sheet, px_per_unit: float = PX_PER_UNIT) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import BackgroundPolicy, Configuration
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    minx, miny, maxx, maxy = sheet.extents
    W = max(maxx - minx, 1e-6)
    H = max(maxy - miny, 1e-6)
    fig = plt.figure(dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ctx = RenderContext(sheet.doc)
    ctx.set_current_layout(sheet.msp)
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE)
    Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(sheet.msp, finalize=False)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal", adjustable="box")
    fig.set_size_inches(W * px_per_unit / 100, H * px_per_unit / 100, forward=True)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor="white", pad_inches=0)
    plt.close(fig)
    return darken_ink(buf.getvalue())
