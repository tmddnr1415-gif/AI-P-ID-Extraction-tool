"""기존 도구의 행 스키마를 그대로 읽어 온다. 여기서 스키마를 정의하지 않는다.

기존 저장소는 **읽기만** 한다 (pid-instrument-tool/config/excel_format.json).
행의 모양이 바뀌면 기존 화면과 Excel 출력기가 같이 바뀌어야 하므로,
이 실험은 스키마를 바꾸지 않고 AI 출력을 여기에 맞춘다.

기존 행이 실제로 갖는 칸 (web/app.js · web/claude.js 에서 확인):

    source='drawing'  system · pid_no · type · qty · description
                      inst_typical_type · remark      ← AI 가 채운다
    source='typical'  sensing_type · element_type · mounting_type
                      signal_type · base_option       ← inst_typical_type 에서 결정적으로 파생
    source='auto_index'  no                           ← 출력 시 순번
    source='design_table' / 'blank'                   ← 이 도구 범위 밖. 공란
    부가 칸          source_tokens · confidence · _page

`rect` 는 **기존 행에 없다.** 기존 화면은 표이지 오버레이가 아니다.
이 실험은 rect 를 부가 칸으로 덧붙인다 — 기존 코드는 모르는 키를 무시하므로
화면과 Excel 은 그대로 돌아가고, 좌표 정확도(D-3)를 잴 수 있게 된다.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "pid-instrument-tool" / "config" / "excel_format.json"
TYPICALS_PATH = REPO_ROOT / "pid-instrument-tool" / "config" / "typicals.json"

# AI 가 채우는 칸에 대한 설명. web/claude.js 의 COL_HINT 와 같은 문장을 쓴다.
COL_HINT = {
    "system": "계통명. 도면 제목과 아래 SYSTEM 목록에서 고른다 (예: HP Steam System)",
    "pid_no": "이 도면의 P&ID 도면번호. 타이틀블록 값을 그대로 쓴다",
    "type": "계기 타입 약어",
    "qty": "같은 사양·같은 용도로 중복 설치되는 수량. 숫자만. 도면이 말하지 않으면 빈 문자열",
    "description": "UNIT 번호 + 설비/계통 + 측정 대상 + 서브 식별자. 예: 'UNIT #11 HP STEAM PRESSURE A'",
    "inst_typical_type": "INST. TYPICAL TYPE (예: PIT-1, TIT-3). 허용 목록에서만 고른다",
    "remark": "벤더 공급 범위·개정 표기 등 특기사항. 없으면 '-'",
}


class Spec:
    """excel_format.json + typicals.json 을 묶어 든다."""

    def __init__(self, spec: dict, typicals: dict):
        self.raw = spec
        self.columns = spec["columns"]
        self.instrument_types = spec["instrument_types"]
        self.systems = spec["systems"]
        self.type_to_typical_types = spec["type_to_typical_types"]
        self.typicals = typicals
        self.sheet = spec["sheet"]
        self.data_start_row = spec["data_start_row"]

    # ── 칸 갈래 ─────────────────────────────────────────
    def keys_of(self, source: str) -> list[str]:
        return [c["key"] for c in self.columns if c["source"] == source]

    @property
    def drawing_keys(self) -> list[str]:
        return self.keys_of("drawing")

    @property
    def typical_keys(self) -> list[str]:
        return self.keys_of("typical")

    def label(self, key: str) -> str:
        for c in self.columns:
            if c["key"] == key:
                return c["label"] or key
        return key

    def col_letter(self, key: str) -> str:
        for c in self.columns:
            if c["key"] == key:
                return c["col"]
        return ""

    # ── typical 파생 ────────────────────────────────────
    def fill_typical(self, row: dict) -> dict:
        """inst_typical_type 에서 Y·Z·AA·AB·AI 를 결정적으로 채운다.

        AI 가 채우는 칸이 아니다. 같은 입력이면 같은 출력이어야 하므로 코드가 한다.
        """
        out = dict(row)
        entry = self.typicals.get((row.get("inst_typical_type") or "").strip())
        if entry:
            for k in self.typical_keys:
                if k in entry:
                    out[k] = entry[k]
        return out

    def top_typical(self, type_: str) -> str:
        """TYPE 의 기본 INST. TYPICAL TYPE — 허용 목록의 첫 값."""
        xs = self.type_to_typical_types.get(type_) or []
        return xs[0] if xs else ""


def load_spec(spec_path: Path | None = None, typicals_path: Path | None = None) -> Spec:
    sp = Path(spec_path or SPEC_PATH)
    tp = Path(typicals_path or TYPICALS_PATH)
    if not sp.exists():
        raise FileNotFoundError(
            f"기존 도구의 스키마를 찾지 못했습니다: {sp}\n"
            "이 실험은 스키마를 스스로 정의하지 않습니다. 저장소 배치를 확인하세요."
        )
    spec = json.loads(sp.read_text(encoding="utf-8"))
    typicals = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
    return Spec(spec, typicals)


# ── AI 출력 강제용 JSON 스키마 ────────────────────────────
def build_json_schema(spec: Spec, with_valves: bool = False) -> dict:
    """자유 서술을 받지 않는다. 모든 응답을 이 모양으로 강제한다.

    `rect` 와 `qty` 는 **null 을 허용**한다. 모른다고 말할 수 있어야
    지어내지 않는다 — 지어내면 재현율만 오르고 정밀도가 죽는다.
    """
    props: dict = {}
    for k in spec.drawing_keys:
        if k == "qty":
            props[k] = {
                "type": ["string", "null"],
                "description": COL_HINT[k] + " · 승수를 못 읽으면 null",
            }
        elif k == "type":
            props[k] = {
                "type": "string",
                "enum": list(spec.instrument_types),
                "description": COL_HINT[k],
            }
        else:
            props[k] = {"type": "string", "description": COL_HINT.get(k, spec.label(k))}

    props["rect"] = {
        "type": ["array", "null"],
        "description": (
            "이 계기 심볼을 감싸는 상자. 도면 전체 대비 정규화 [x0,y0,x1,y1] "
            "(0~1, 원점 좌상단). 위치를 특정 못 하면 null. 어림짐작으로 채우지 말 것"
        ),
        "items": {"type": "number"},
        "minItems": 4,
        "maxItems": 4,
    }
    props["source_tokens"] = {
        "type": "string",
        "description": "이 행의 근거가 된 도면상 글자와 대략 위치. 예: 'PT ×2 @ 좌상단 HP스팀 헤더'",
    }
    props["confidence"] = {
        "type": "string",
        "enum": ["high", "medium", "low"],
        "description": "판독 확신도. 글자가 흐리거나 맥락 추정이 섞였으면 low",
    }

    required = [*spec.drawing_keys, "rect", "source_tokens", "confidence"]

    schema: dict = {
        "type": "object",
        "properties": {
            "instruments": {
                "type": "array",
                "description": "이 도면에서 판독한 Field Instrument. 도면 위→아래, 좌→우 순서.",
                "items": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                    "additionalProperties": False,
                },
            },
            "excluded": {
                "type": "array",
                "description": "계기 문자로 보였지만 제외한 것과 그 이유. 누락 추적용이므로 반드시 남긴다.",
                "items": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string"},
                        "location": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["token", "location", "reason"],
                    "additionalProperties": False,
                },
            },
            "review_findings": {
                "type": "array",
                "description": "사람이 확인해야 할 사항 (판독 불가·승수 미정·규칙 충돌 등)",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "location": {"type": "string"},
                        "finding": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["severity", "location", "finding", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "scope_notes": {
                "type": "string",
                "description": "이 장 NOTES 가 정의한 별표(*/**) 뜻. 정의가 없으면 빈 문자열",
            },
            "qty_basis": {
                "type": "string",
                "description": "Q'ty 를 그렇게 판정한 근거 문장. 도면이 말하지 않으면 '승수 미정'",
            },
            "page_summary": {"type": "string", "description": "이 도면에서 무엇을 몇 건 뽑았는지 2~3문장"},
        },
        "required": [
            "instruments",
            "excluded",
            "review_findings",
            "scope_notes",
            "qty_basis",
            "page_summary",
        ],
        "additionalProperties": False,
    }

    if with_valves:
        schema["properties"]["valves"] = {
            "type": "array",
            "description": "밸브 목록. 기본 출력 스키마 밖이라 감사용으로만 쓴다.",
            "items": {
                "type": "object",
                "properties": {
                    "valve_type": {"type": "string"},
                    "actuator": {"type": "string"},
                    "scope": {"type": "string"},
                    "rect": {"type": ["array", "null"], "items": {"type": "number"}},
                },
                "required": ["valve_type", "actuator", "scope", "rect"],
                "additionalProperties": False,
            },
        }
        schema["required"].append("valves")

    return schema


def normalize_row(row: dict, spec: Spec, page: int) -> dict:
    """AI 가 준 한 행을 기존 스키마 모양으로 맞춘다. 없는 칸은 만들지 않는다."""
    out = {k: (row.get(k) or "") for k in spec.drawing_keys}
    out["qty"] = "" if row.get("qty") in (None, "") else str(row["qty"]).strip()
    if not out.get("inst_typical_type"):
        out["inst_typical_type"] = spec.top_typical(out.get("type", ""))
    if not out.get("remark"):
        out["remark"] = "-"
    out = spec.fill_typical(out)
    rect = row.get("rect")
    out["rect"] = [float(v) for v in rect] if isinstance(rect, list) and len(rect) == 4 else None
    out["source_tokens"] = row.get("source_tokens") or ""
    out["confidence"] = row.get("confidence") or "low"
    out["_page"] = page
    return out
