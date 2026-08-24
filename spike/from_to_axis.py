"""측정 하네스용 재수출 — 구현은 `app/engine/describe_axis.py` 하나뿐이다.

1부 체크포인트의 측정 드라이버(/tmp)들이 이 이름으로 import 한다.  구현이
두 벌이 되면 측정과 산출물이 갈라지므로, 여기는 심(shim)만 남긴다.  엔진
모듈은 bare name 으로 적재한다 - `app.engine.x` 로도 적재하면 config 싱글턴이
두 벌이 된다 (app/pipeline.py 머리 주석과 같은 이유).
"""
import sys
from pathlib import Path

_ENGINE = Path(__file__).resolve().parent.parent / "app" / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))
from describe_axis import *             # noqa: F401,F403,E402
from describe_axis import (             # noqa: F401,E402
    _touch, _pt_rect_d, _ends, _near_texts, _near_equip, _run_pt_d,
    _covers, _own_body, _crossings, _gap_pair, _strip_conn)
