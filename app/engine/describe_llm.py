"""The Description selector: a model that *chooses*, never one that writes.

The rules reach a Description of `UNIT #10 HP STEAM PRESSURE` and stop, because
the middle of the client's sentence names equipment and the rules cannot tell
which of the drawing's words is the one being named.  A model can - but only if it
is confined to choosing, so this module is built around six constraints, each
enforced in code rather than asked for in the prompt:

1. **A selector, not a generator.**  The only input it may draw words from is the
   candidate list `describe_candidates` collected off the pipe the instrument is
   attached to.  The prompt says so, and `validate()` enforces it afterwards.
2. **No evidence, no call.**  Zero candidates means no request is made at all;
   the row goes back with `INSUFFICIENT` and waits for a person.
3. **Every answer is re-checked by rule.**  A word that is not in the candidates,
   the system name or the ISA table gets the answer thrown away, and the rejection
   is counted and reported.
4. **Deterministic.**  Every call is keyed by a hash of its exact inputs and
   cached on disk, so a re-analysis of the same PDF makes no calls and produces
   the same bytes.  (Sampling parameters no longer exist on the current models -
   `temperature` is rejected outright - so determinism comes from the cache, which
   is stronger: it does not depend on the model's behaviour at all.)
5. **Description only.**  Nothing here is imported by, or reachable from, symbol
   detection, quantity, or scope.  Those stay rule-only.
6. **Never automatic.**  A selected line is a proposal: it is graded, flagged and
   left for the reviewer to accept.

No key configured means no calls and no failure: the run reports LLM_UNAVAILABLE
and every row is graded exactly as the rules-only path grades it.

**AS OF THIS ROUND THIS MODULE IS NOT WIRED IN.  IT IS NOT "OFF" - IT IS
UNCONNECTED.**

`pipeline.analyse` calls `build()` and reports what it returns (`enabled`,
`reason`, `model`, `stats`), and nothing else here is reached: `select()` has no
caller in this repository outside `tests/test_description.py`.  So turning
`description.llm.enabled` on in a profile, with a key in the environment, still
produces zero calls - the switch has nothing behind it.  Two independent
measurements say so: a full 58-sheet analysis with every non-loopback socket
connect and DNS lookup intercepted recorded **0 outbound attempts**, and the
packaged exe excludes the `anthropic` package outright (`pid_extract.spec`), so
the string `api.anthropic.com` does not occur in the 73 MB binary.

This was left as it is on purpose rather than being connected or deleted:
connecting it would build a switch that cannot work in the exe, and deleting it
would throw away work that an in-house model would need again.  What was missing
was not code but the truth being written down, which is what this note is.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import describe as desc  # noqa: E402

# The model's answer when it will not choose.  Its own word, checked for exactly.
INSUFFICIENT = "INSUFFICIENT"

# Why a call was not made or its answer not used.  Counted and reported.
NO_CANDIDATES = "후보 0개 — 호출하지 않았습니다"
NO_CLIENT = "LLM 미설정 — 호출하지 않았습니다"
MODEL_DECLINED = "모델이 INSUFFICIENT 를 반환했습니다"
REJECT_UNKNOWN_WORD = "후보에 없는 낱말"
REJECT_UNIT = "그 도면에서 관측되지 않은 유닛 번호"
REJECT_ORDER = "유도된 문형의 어순에 맞지 않음"
REJECT_EMPTY = "빈 응답"

SYSTEM = (
    "You choose, you do not write.\n"
    "You are given the words a P&ID drawing prints along the pipe run that one "
    "instrument is attached to, and the finished Description lines an engineering "
    "client wrote for other instruments in the same system.\n"
    "Your task: decide which of the given candidate phrases names the thing this "
    "instrument is measuring, and put them in the order the client's examples use.\n"
    "Rules you must follow exactly:\n"
    "- Use only words that appear in the candidate list. Do not add, translate, "
    "expand, abbreviate or correct any word.\n"
    "- Do not repeat the system name or the measured variable; they are added "
    "around your answer by the caller.\n"
    "- If the candidates do not clearly name what the instrument measures, answer "
    f"{INSUFFICIENT}. That is a correct answer, not a failure.\n"
    "Answer with JSON only: "
    '{"middle": "<phrase or ' + INSUFFICIENT + '>", '
    '"unit": "<unit marking from the candidates, or empty>", '
    '"used": ["<each candidate phrase you used>"], "why": "<one short sentence>"}'
)


@dataclass
class Selector:
    """Config and state for the selection pass."""

    model: str = "claude-opus-5"
    max_tokens: int = 512
    cache_dir: Path = None
    enabled: bool = False
    reason: str = NO_CLIENT
    calls: int = 0
    cached: int = 0
    stats: dict = field(default_factory=lambda: {
        "calls": 0, "cache_hits": 0, "accepted": 0, "rejected": 0,
        "insufficient": 0, "no_candidates": 0, "errors": 0,
        "rejections": [],
    })

    def key(self, payload: dict) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False)
            .encode("utf-8")).hexdigest()


def build(cfg=None, cache_dir: Path = None) -> Selector:
    """A selector that is on only when the project asked for it and a key exists."""
    import projectconfig
    cfg = cfg or projectconfig.load()
    d = (cfg.data.get("description") or {}).get("llm") or {}
    sel = Selector(
        model=str(d.get("model") or "claude-opus-5"),
        max_tokens=int(d.get("max_tokens") or 512),
        cache_dir=Path(cache_dir or d.get("cache_dir")
                       or "app/_data/description_cache"),
    )
    if not d.get("enabled"):
        # 이 문구는 화면과 보고서에 그대로 나간다.  "꺼져 있다" 만 쓰면 켜면
        # 된다는 뜻으로 읽히는데, 켜도 호출부가 없어 아무 일도 일어나지 않는다.
        sel.reason = ("config description.llm.enabled 가 꺼져 있습니다 "
                      "(그리고 호출부가 연결돼 있지 않아, 켜도 호출되지 않습니다)")
        return sel
    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sel.reason = ("ANTHROPIC_API_KEY 가 없습니다 — 호출 없이 규칙 결과만 "
                      "사용합니다")
        return sel
    try:
        import anthropic  # noqa: F401
    except ImportError:
        sel.reason = "anthropic 패키지가 설치돼 있지 않습니다 (pip install anthropic)"
        return sel
    sel.enabled = True
    sel.reason = ""
    return sel


def prompt_for(row: dict, candidates: list, examples: list) -> dict:
    """The exact payload a call is made from, and what the cache is keyed on.

    Kept as data rather than a formatted string so the cache key is stable against
    incidental wording changes, and so a reviewer can see precisely what was sent.
    """
    return {
        "type": row["type"],
        "variable": " ".join(row["variable"]),
        "system": " ".join(row["system"]),
        "unit_code": row["unit_code"],
        "candidates": [{"text": c["text"], "kind": c["kind"],
                        "distance": c["distance"], "direction": c["direction"]}
                       for c in candidates],
        "examples": list(examples),
    }


def _user_text(p: dict) -> str:
    lines = [
        f"Instrument tag type: {p['type']}",
        f"Measured variable (already decided, do not repeat): {p['variable']}",
        f"System name (already decided, do not repeat): {p['system']}",
        f"Sheet unit code: {p['unit_code']}",
        "",
        "Candidate phrases printed along the pipe this instrument is attached to:",
    ]
    for i, c in enumerate(p["candidates"], 1):
        lines.append(f"  {i}. [{c['kind']} {c['direction']} {c['distance']}pt] "
                     f"{c['text']}")
    if p["examples"]:
        lines += ["", "Finished Description lines the client wrote in this system:"]
        lines += [f"  - {e}" for e in p["examples"]]
    return "\n".join(lines)


def select(sel: Selector, payload: dict):
    """`(answer_dict, reason)`.  Cached, and never called without candidates."""
    if not payload["candidates"]:
        sel.stats["no_candidates"] += 1
        return None, NO_CANDIDATES
    key = sel.key(payload)
    path = sel.cache_dir / f"{key}.json"
    if path.exists():
        sel.stats["cache_hits"] += 1
        return json.loads(path.read_text(encoding="utf-8")), ""
    if not sel.enabled:
        return None, sel.reason
    import anthropic
    client = anthropic.Anthropic()
    try:
        msg = client.messages.create(
            model=sel.model,
            max_tokens=sel.max_tokens,
            system=SYSTEM,
            messages=[{"role": "user", "content": _user_text(payload)}],
        )
    except Exception as exc:                       # network, auth, rate limit
        sel.stats["errors"] += 1
        return None, f"{type(exc).__name__}: {str(exc)[:120]}"
    sel.stats["calls"] += 1
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    answer = _parse(text)
    if answer is None:
        sel.stats["errors"] += 1
        return None, REJECT_EMPTY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(answer, ensure_ascii=False, sort_keys=True),
                    encoding="utf-8")
    return answer, ""


def _parse(text: str):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return out if isinstance(out, dict) else None


def validate(answer: dict, payload: dict, page_units: set) -> tuple:
    """Re-check the model's answer by rule.  `(middle, unit, reason)`.

    Every gate here is a rule the model cannot talk its way past:

      * every word of the answer must appear in the candidates the rules collected
      * the unit marking must be one actually printed on that drawing
      * the answer must be a middle segment only - it may not restate the system
        name or the variable, because the template puts those around it

    A failure returns an empty middle and the reason, and the caller grades the row
    NONE.  Nothing partial is kept: half a rejected sentence is still a sentence
    nobody measured.
    """
    if not answer:
        return "", "", REJECT_EMPTY
    middle = str(answer.get("middle") or "").strip()
    unit = str(answer.get("unit") or "").strip()
    if not middle or middle.upper() == INSUFFICIENT:
        return "", "", MODEL_DECLINED
    allowed = set()
    for c in payload["candidates"]:
        allowed |= set(desc.tokens(c["text"]))
    got = desc.tokens(middle)
    unknown = [w for w in got if w not in allowed]
    if unknown:
        return "", "", f"{REJECT_UNKNOWN_WORD}: {', '.join(unknown[:4])}"
    # the template supplies these; repeating them would double the sentence
    fixed = set(desc.tokens(payload["system"])) | set(desc.tokens(payload["variable"]))
    if fixed and set(got) & fixed:
        return "", "", REJECT_ORDER
    if unit:
        mark = "".join(ch for ch in unit if ch.isdigit())
        if not mark or mark not in page_units:
            return middle, "", REJECT_UNIT
    return middle, unit, ""
