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

PX_PER_UNIT = 3.0        # A3(841 단위) → 2523px.  PDF 경로의 1191pt × 1.6 과 비슷한 밀도


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
    return buf.getvalue()
