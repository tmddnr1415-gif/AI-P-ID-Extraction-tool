"""LOGIC 작도 — 분석한 로직과 **같은 양식**으로 새 로직 시트를 그린다 (L54).

문서(그림) 하나 = JSON 하나 · 저장 자리 `{data}/logic/drawings/<id>/drawing.json` (jsonstore · 작성자 필수).
좌표는 전부 **PDF 포인트**(A3 가로 1191×842 · y 는 아래로)라 화면(SVG) · PDF · DXF 가 같은 수를 쓴다.

양식 — 분석기가 읽는 그 꼴 (tests/test_logic_l23_generic.py 의 합성 장과 같다):
  왼쪽 표  FROM | NO. | TAG NO. | SERVICE   (행 1..N)
  가운데   LOGIC 영역
  오른쪽 표 SERVICE | TAG NO. | NO. | TO   (행 N+1..2N)
  타이틀블록  문서 번호 · 제목 · 캡션 `SHEET NO.` 아래 시트 이름

기호는 범례 어휘(config/logic_symbols.yaml)의 **글자 상자**로 그린다 — AND · OR · NOT · NAND · NOR · GT · DT · PD 는
글자가 든 네모(AND/OR/NAND/NOR 는 왼쁜 입력 막대) · 메모리는 S/R 두 칸 · 투표는 `2/3` · 누름단추는 `PB` + 이름 ·
연결 기호는 글자 든 원.  **분석기가 글자 상자를 읽는 규칙(blocks.isa_word · _drawn)이 곧 이 작도기의 기호 정의**라,
그려서 내보낸 PDF 를 분석기에 다시 넣으면 같은 블록 · 같은 선 · 같은 행이 나온다 (verify 가 그것을 잰다).

판정 코드는 한 줄도 부르지 않는다 — 이 모듈은 그리기 · 내보내기 · 되읽기(검증)만 한다.
"""
from __future__ import annotations

import bisect
import io
import json
import math
import re
import tempfile
import time
import uuid
from pathlib import Path

import pymupdf

from app import jsonstore

from . import store

W, H = 1191.0, 842.0            # A3 가로
TOP = 70.0                      # 표 첫 행 윗변
PITCH = 11.3                    # 행 간격 (합성 장과 같다 · 분석기는 장마다 다시 잰다)
N_DEFAULT = 50
N_MIN, N_MAX = 45, 62        # 표 괘선이 종이 높이의 0.6 을 넘어야 분석기가 표로 읽는다 (geom · 45 행) · 62 행이면 770.6 — 타이틀블록(780) 위
LCOLS = [30.0, 90.0, 110.0, 180.0, 320.0]        # FROM | NO. | TAG | SERVICE
RCOLS = [870.0, 1010.0, 1080.0, 1100.0, 1160.0]  # SERVICE | TAG | NO. | TO
LX0, LX1 = LCOLS[-1], RCOLS[0]                   # LOGIC 영역 좌우
K = (0, 0, 0)
LW = 0.72
ID_RE = re.compile(r"^[0-9a-f]{12}$")
MAX_TEXT = 200

# 기호 사전 — 화면(팔레트 · 그리기) · PDF · DXF 가 같은 것을 읽는다.  logic 은 범례 어휘(logic_symbols.yaml)의 동작 이름.
#   text  : 상자 안에 인쇄하는 글자 (분석기 blocks.isa_word 가 그대로 읽는다)
#   bar   : 왼쪽 입력 막대 (여러 입력이 붙는 자리)
#   cells : 2 = 위·아래 두 칸 (메모리 S/R)
#   w · h : 기본 크기 (pt)
SYMBOLS = {
    "AND":    {"name": "AND",            "text": "AND",  "bar": True,  "w": 16, "h": 9,  "logic": "and"},
    "OR":     {"name": "OR",             "text": "OR",   "bar": True,  "w": 16, "h": 9,  "logic": "or"},
    "NAND":   {"name": "NAND",           "text": "NAND", "bar": True,  "w": 18, "h": 9,  "logic": "nand"},
    "NOR":    {"name": "NOR",            "text": "NOR",  "bar": True,  "w": 16, "h": 9,  "logic": "nor"},
    "NOT":    {"name": "NOT",            "text": "NOT",  "bar": False, "w": 16, "h": 9,  "logic": "not"},
    "GT":     {"name": "켜짐 지연 (GT)",  "text": "GT",   "bar": False, "w": 16, "h": 9,  "logic": "delay_on",  "time": True},
    "DT":     {"name": "꺼짐 지연 (DT)",  "text": "DT",   "bar": False, "w": 16, "h": 9,  "logic": "delay_off", "time": True},
    "PD":     {"name": "펄스 (PD)",       "text": "PD",   "bar": False, "w": 16, "h": 9,  "logic": "pulse",     "time": True},
    "VOTE":   {"name": "투표 A/B",        "text": "2/3",  "bar": True,  "w": 16, "h": 9,  "logic": "vote",      "ab": True},
    "MEMORY": {"name": "메모리 S-R",      "text": "S|R",  "bar": False, "w": 12, "h": 22, "logic": "memory",    "cells": 2},
    "PB":     {"name": "누름단추 PB",     "text": "PB",   "bar": False, "w": 14, "h": 9,  "logic": "source",    "label": True},
    "ANN":    {"name": "경보 ANN",        "text": "ANN",  "bar": False, "w": 18, "h": 9,  "logic": "sink"},
    "SOE":    {"name": "기록 SOE",        "text": "SOE",  "bar": False, "w": 18, "h": 9,  "logic": "sink"},
    "CONN":   {"name": "연결 기호 (원)",   "text": "A",    "bar": False, "w": 8,  "h": 8,  "logic": "connector", "circle": True},
    "TEXT":   {"name": "글 (주석)",       "text": "NOTE", "bar": False, "w": 40, "h": 8,  "logic": "",          "note": True},
    # L56 — 표시등: 원 안 글자 하나(G · R · W …) · 들어오는 선만 (분석기 _lamp_fallback 이 그렇게 읽는다)
    "LAMP":   {"name": "표시등 (램프)",    "text": "G",    "bar": False, "w": 10, "h": 10, "logic": "sink",      "circle": True, "lamp": True},
    # L56 — 글자 상자: 분석기가 상자 안 **글자**로 뜻을 읽는 블록 (DI · 신호 이름 · 아날로그 연산 이름 …).  뜻은 그 글자가 정한다.
    "BOX":    {"name": "글자 상자",        "text": "DI",   "bar": False, "w": 16, "h": 9,  "logic": "",          "box": True},
    # L56 — 매크로 블록: 이름(Typical 시트 제목) + 단자 이름을 안에 인쇄한 큰 상자.  내부 동작은 그 묶음의 Typical 시트가 정한다
    # (분석기 macro.link 가 단자 이름 ↔ Typical 행(TAG NO. 칸의 약어 · 설명)으로 맞댄다).  단자 자리는 param.pins_in/pins_out 의 dy.
    "MACRO":  {"name": "매크로 블록",      "text": "",     "bar": False, "w": 90, "h": 60, "logic": "macro",     "macro": True},
}
# L57 — 글자 상자 보기 (팔레트 둘째 묶음).  **뜻은 상자 안 글자가 정한다** — 분석기(blocks.isa_word · aops · analog)와 작도
# 시뮬레이터(draw_sim._box_meaning)가 같은 글자를 같은 뜻으로 읽는다.  식별한 로직에 나온 종류를 전부 그릴 수 있게 둔다.
# note = 그 장 NOTES 에 있어야 뜻이 서는 것 (토글 — NOTE 문장이 그 낱말을 따옴표로 부르고 INVERT 를 말한다).
BOX_PRESETS = [
    {"text": "1",     "name": "상수 1 (FORCED INPUT)", "hint": "언제나 1 — 들어오는 선 없이 나가는 선만", "w": 10, "h": 9},
    {"text": "0",     "name": "상수 0",                "hint": "언제나 0", "w": 10, "h": 9},
    {"text": "DI",    "name": "DI (켜짐 지연 · ISA)",   "hint": "ISA 약어 — 켜짐 지연 (시간은 속성)", "time": True},
    {"text": "PO",    "name": "PO (펄스 · ISA)",        "hint": "ISA 약어 — 펄스 출력", "time": True},
    {"text": "PASS",  "name": "이음점 (그대로 넘김)",    "hint": "입력 하나 = 출력 — 선을 잇기만", "w": 10, "h": 9},
    {"text": "SRST",  "name": "토글 (NOTE 정의)",        "hint": "입력이 참으로 바뀔 때마다 출력이 뒤집힌다 — 장 NOTE 가 정의한다",
     "note": 'OUTPUT STATE IS INVERTED BY EACH MOMENTARY TRUE SIGNAL ON "SRST"'},
    {"text": "STEP",  "name": "STEP 상자",              "hint": "순서 제어 단계 — STEP IN · CRIT → STEP OUT · C-STEP CMD (근사 모델)", "w": 40, "h": 48,
     "lines": [[2.0, 6.8, "STEP", 5.0], [2.0, 18.0, "STEP IN", 3.6], [2.0, 29.3, "CRIT", 3.6], [16.0, 18.0, "STEP OUT", 3.6], [12.0, 40.6, "C-STEP CMD", 3.6]]},
    {"text": "HH/",   "name": "감시 HH (높음)",          "hint": "값이 설정값을 넘으면 1 — 설정값은 '블록 위 글' (예: 191 barg)", "above": "191 barg"},
    {"text": "/L",    "name": "감시 L (낮음)",           "hint": "값이 설정값에 못 미치면 1", "above": "14 %"},
    {"text": "MED",   "name": "중간값 선택 (MED)",       "hint": "아날로그 — 입력의 중간값"},
    {"text": "Σ",     "name": "합 (Σ)",                 "hint": "아날로그 — 입력의 합 (계수는 선 글)"},
    {"text": "△",     "name": "차 (△)",                 "hint": "아날로그 — X1 − X2"},
    {"text": "×",     "name": "곱 (×)",                 "hint": "아날로그 — X1 × X2"},
    {"text": "÷",     "name": "나눗셈 (÷)",             "hint": "아날로그 — X1 ÷ X2"},
    {"text": "√",     "name": "제곱근 (√)",             "hint": "아날로그 — √X"},
    {"text": "K",     "name": "비례 (K)",               "hint": "아날로그 — K·X (K 는 블록 위 글 'K : 2')", "above": "K : 1"},
    {"text": "T",     "name": "전환 (T)",               "hint": "아날로그 — 조건 1 이면 IN1 · 0 이면 IN2"},
    {"text": "F(X)",  "name": "함수 F(X)",              "hint": "아날로그 — 꺾은선 표 (표가 없으면 그대로 넘김)"},
    {"text": "PID",   "name": "PID 제어기",             "hint": "아날로그 — 시뮬레이션에서는 수동 출력값"},
    {"text": "A",     "name": "아날로그 상수 (A)",       "hint": "들어오는 선 없이 값 하나 — 블록 위 글 'A : 5%'", "above": "A : 5"},
    {"text": "DEV",   "name": "편차 감시 (DEV)",         "hint": "|X1 − X2| > D 이면 1 (D 는 블록 위 글)", "above": "D : 10"},
    {"text": "EQUAL", "name": "같음 비교 (EQUAL)",       "hint": "IN1 = IN2 이면 1", "w": 22},
    {"text": "SIG",   "name": "신호 상자 (이름)",        "hint": "들어오는 선 없이 이름 붙은 신호 — 글자를 그 신호 이름으로", "w": 24},
    {"text": "RUN",   "name": "상태 표시 (받기만)",      "hint": "들어오는 선만 — 글자 셋 이하", "w": 16, "sink": True},
    # L59 — 삼성(알다프라 · 19VA) 범례 'SIGNAL PROCESSING SYMBOLS' 의 나머지 기호 전부.  뜻은 분석기 어휘(config/logic_analog.yaml ·
    # logic_symbols.yaml legend_functions · analog._MON)가 이미 읽는 글자라 작도 → PDF → 분석 왕복에서 같은 기능으로 선다.
    {"text": "ON",    "name": "ACTIVATION (언제나 1)",   "hint": "범례 ACTIVATION — 들어오는 선 없이 언제나 1", "w": 10, "h": 9, "src": True},
    {"text": "FL",    "name": "주기 펄스 (FL)",          "hint": "범례 SPECIAL — 입력이 1 인 동안 되풀이 펄스 (시뮬레이션은 펄스 하나로 근사)", "time": True},
    {"text": "I",     "name": "지시 (INDICATION)",       "hint": "받기만 — 운전원 화면 표시", "w": 10, "h": 9, "sink": True},
    {"text": "S",     "name": "기록 (SER)",              "hint": "받기만 — 사건 기록 (SEQUENCE OF EVENTS)", "w": 10, "h": 9, "sink": True},
    {"text": "HHH/",  "name": "감시 HHH (매우 높음)",     "hint": "값이 설정값을 넘으면 1 — 설정값은 블록 위 글", "above": "202.4 barg"},
    {"text": "H/",    "name": "감시 H (높음)",            "hint": "값이 설정값을 넘으면 1", "above": "180 barg"},
    {"text": "/LL",   "name": "감시 LL (매우 낮음)",      "hint": "값이 설정값에 못 미치면 1", "above": "10 %"},
    {"text": "/LLL",  "name": "감시 LLL",                "hint": "값이 설정값에 못 미치면 1", "above": "5 %"},
    {"text": "AVG",   "name": "평균 (Σ/n)",              "hint": "아날로그 — 입력의 평균"},
    {"text": "|△|",   "name": "차의 절댓값",             "hint": "아날로그 — |X1 − X2|"},
    {"text": "ABS",   "name": "절댓값 (ABS)",            "hint": "아날로그 — |X|"},
    {"text": "-K",    "name": "역비례 (−K)",             "hint": "아날로그 — −K·X (K 는 블록 위 글)", "above": "K : 1"},
    {"text": "±",     "name": "바이어스 (±b)",           "hint": "아날로그 — X ± b (b 는 블록 위 글 'b : 5')", "above": "b : 5"},
    {"text": "∫",     "name": "적분 (∫)",                "hint": "아날로그 — 시간에 따라 쌓인다 (멈춘 값은 사람이 넣는다)"},
    {"text": "D/DT",  "name": "미분 (d/dt)",             "hint": "아날로그 — 값이 멈춰 있으면 0"},
    {"text": "Xⁿ",    "name": "거듭제곱 (Xⁿ)",           "hint": "아날로그 — Xⁿ (n 은 블록 위 글 'n : 2')", "above": "n : 2"},
    {"text": "F(T)",  "name": "시간 함수 F(T)",          "hint": "아날로그 — f(t) (멈춘 값은 사람이 넣는다)"},
    {"text": ">",     "name": "높은 값 선택 (>)",        "hint": "아날로그 — 입력 중 큰 값", "w": 10, "h": 9},
    {"text": "<",     "name": "낮은 값 선택 (<)",        "hint": "아날로그 — 입력 중 작은 값", "w": 10, "h": 9},
    {"text": "HL",    "name": "상한 제한 (HIGH LIMIT)",  "hint": "아날로그 — X 가 H 를 넘으면 H (H 는 블록 위 글)", "above": "H : 100"},
    {"text": "LL",    "name": "하한 제한 (LOW LIMIT)",   "hint": "아날로그 — X 가 L 에 못 미치면 L", "above": "L : 0"},
    {"text": "V>",    "name": "변화율 제한",             "hint": "아날로그 — 멈춘 값에서는 입력과 같다"},
    {"text": "LAG",   "name": "1차 지연 (LAG)",          "hint": "아날로그 — 멈춘 값에서는 k·X"},
    {"text": "I/P",   "name": "신호 변환 (X1/X2)",       "hint": "아날로그 — 신호 종류만 바뀐다 (I/P · E/P · P/I · A/D · D/A)"},
    {"text": "A/T",   "name": "수동/자동 조작기 (A/T)",   "hint": "제어 스테이션 — 시뮬레이션에서는 수동 출력값 (PID 와 같다)"},
    {"text": "BIT_CNT", "name": "참 입력 수 (BIT COUNTER)", "hint": "1 인 디지털 입력의 수 (정수) — IN1 … → OUT", "w": 24},
    {"text": "COUNTER", "name": "카운터 (EN · IN · RESET · SV → OUT · UL)", "hint": "범례 SPECIAL — IN 의 오르는 변을 센다 · 셈이 SV 에 닿으면 UL (시간이 흐르는 셈이라 멈춘 값은 사람이 넣는다)",
     "w": 36, "h": 40, "lines": [[2.0, 6.0, "COUNTER", 4.4], [2.0, 14.0, "EN", 3.4], [2.0, 21.0, "IN", 3.4], [2.0, 28.0, "RESET", 3.4], [2.0, 35.0, "SV", 3.4], [23.0, 14.0, "OUT", 3.4], [25.0, 28.0, "UL", 3.4]]},
    {"text": "STATEMENT OF SPECIAL REQUIREMENTS", "name": "특수 요구 문장 (글)", "hint": "범례 SPECIAL — 상자 안에 요구 문장을 적는 주석 (판정 없음)", "kind": "TEXT", "w": 70, "h": 10},
]


BAR_EXTRA = 2.0 * PITCH
MACRO_TOP = 1.6 * PITCH          # 매크로 상자 머리(이름 글줄) 높이 — 첫 단자는 그 아래 (분석기 _top_line 이 첫 단자 위 글을 이름으로 읽는다)
MACRO_PIN_FS = 4.2
DOT_R = 0.12 * PITCH         # 연결점 반지름 — 지름 0.24P < 분석기 DOT_MAX 0.35P (geom)
MARK_KINDS = ("diamond", "square")
MARK_R = 0.27 * PITCH        # 인터페이스 표시 ◆ ■ 의 반 폭 — 변 0.54P ≥ 분석기 DOT_MAX 0.35P (연결점이 아니라 표시로 읽힌다)


def mark_polygon(x: float, y: float, kind: str) -> list:
    """◆ 는 네 꼭짓점 · ■ 는 네 모서리 — 칠한 다각형으로 그린다 (geom 이 칠한 4점 path 를 표시로 읽는다 · 사각형 항목은 안 된다)."""
    r = MARK_R
    if kind == "square":
        q = r * 0.8
        return [[x - q, y - q], [x + q, y - q], [x + q, y + q], [x - q, y + q]]
    return [[x, y - r], [x + r, y], [x, y + r], [x - r, y]]
MAX_PINS = 64


BASE_SIZES = {k: (v["w"], v["h"]) for k, v in SYMBOLS.items()}      # 학습 스타일을 얹기 전의 기본 크기 (시험 · 되돌리기)


def _font(t: str) -> str:
    """helv 는 한글을 못 그린다 (점으로 나온다) — 라틴 밖 글자가 있으면 PyMuPDF 내장 `korea` 글꼴."""
    return "korea" if any(ord(ch) > 127 for ch in str(t or "")) else "helv"


def apply_style(style: dict | None):
    """학습한 크기(행 간격 배율)를 기호 기본 크기에 얹는다 — `config/logic_draw_style.json` (L56 · 네 묶음에서 잰 중앙값).
    팔레트가 그 크기로 놓고, 들여온 그림은 원래 크기를 그대로 둔다."""
    for k, st in ((style or {}).get("sizes") or {}).items():
        if k in SYMBOLS and isinstance(st, dict) and st.get("w_p") and st.get("h_p"):
            SYMBOLS[k]["w"] = round(max(6.0, float(st["w_p"]) * PITCH), 1)
            SYMBOLS[k]["h"] = round(max(6.0, float(st["h_p"]) * PITCH), 1)
            SYMBOLS[k]["learned"] = st.get("n", 0)


def style_path() -> Path:
    from app import paths as _paths
    return Path(_paths.resource("config", "logic_draw_style.json"))


def load_style() -> dict:
    try:
        return json.loads(style_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


apply_style(load_style())          # 입력 막대 = 상자 높이 + 위아래 한 행씩 (상자보다 길어야 막대로 읽힌다 — graph._bar_gate)


def ry(n: int, N: int) -> float:
    """행 n (1..2N) 의 가운데 y — 오른쪽 표 행 N+k 는 왼쁜 k 와 같은 높이."""
    return TOP + ((n - 1) % N) * PITCH + PITCH / 2


def layout(N: int) -> dict:
    """화면이 표를 그릴 때 쓰는 수 — 서버와 같은 자."""
    N = max(N_MIN, min(N_MAX, int(N or N_DEFAULT)))
    return {"W": W, "H": H, "TOP": TOP, "PITCH": PITCH, "N": N, "LCOLS": LCOLS, "RCOLS": RCOLS,
            "LX0": LX0, "LX1": LX1, "bottom": TOP + N * PITCH, "bar_extra": BAR_EXTRA,
            "title": {"doc": [900.0, 805.0], "caption": [1100.0, 790.0], "sheet": [1098.0, 800.0], "name": [600.0, 805.0]}}


# ─────────────────────────── 문서 ───────────────────────────

def new_doc(name: str, author: str, project: str = "", N: int = N_DEFAULT) -> dict:
    N = max(N_MIN, min(N_MAX, int(N or N_DEFAULT)))
    now = time.time()
    return {
        "id": uuid.uuid4().hex[:12], "name": (name or "새 로직").strip()[:80], "project": (project or "").strip()[:80],
        "sheet_no": "", "title": "", "doc_no": "", "N": N,
        "set": "", "set_name": "", "order": 0, "typical": False,     # L56 — 묶음(여러 장) · 매크로 Typical 시트 여부
        "notes": [],                        # L56 — 장 노트 (NOTES 상자 · 번호 매김 · 왼쪽 아래)
        "left": {}, "right": {},            # 행 번호(str) → {"fm","kks","desc"} / {"desc","kks","to"}
        "blocks": [], "wires": [],
        "author": author, "created": now, "updated": now, "saves": 0, "history": [],
    }


def _num(v, lo=None, hi=None, default=0.0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if f != f or f in (float("inf"), float("-inf")):
        return default
    if lo is not None:
        f = max(lo, f)
    if hi is not None:
        f = min(hi, f)
    return round(f, 2)


def _txt(v, n=MAX_TEXT):
    return str(v if v is not None else "").replace("\n", " ").strip()[:n]


def clean(doc: dict) -> dict:
    """화면이 보낸 그림을 믿지 않고 모양을 맞춘다 (api_fuzz 규율) — 모르는 종류 · 밖으로 나간 좌표 · 긴 글."""
    N = max(N_MIN, min(N_MAX, int(_num(doc.get("N"), 1, 999, N_DEFAULT))))
    out = {"N": N, "sheet_no": _txt(doc.get("sheet_no"), 40), "title": _txt(doc.get("title"), 120),
           "doc_no": _txt(doc.get("doc_no"), 60), "typical": bool(doc.get("typical")),
           "form": str(doc.get("form") or "") if str(doc.get("form") or "") in FORMS else "",
           "project_name": _txt(doc.get("project_name"), 80), "rev": _txt(doc.get("rev"), 10),
           "left": {}, "right": {}, "blocks": [], "wires": [],
           "compact": int(_num(doc.get("compact"), 0, 99, 0)),          # L84 — 들여온 선을 묶은 판 (draw_compact.VERSION)
           "notes": [t for t in (_txt(x, 160) for x in (doc.get("notes") if isinstance(doc.get("notes"), list) else [])[:20]) if t]}
    for side, keys in (("left", ("fm", "kks", "desc")), ("right", ("desc", "kks", "to"))):
        rows = doc.get(side) if isinstance(doc.get(side), dict) else {}
        for k, v in rows.items():
            try:
                n = int(k)
            except (TypeError, ValueError):
                continue
            lo, hi = (1, N) if side == "left" else (N + 1, 2 * N)
            if not (lo <= n <= hi) or not isinstance(v, dict):
                continue
            cell = {kk: _txt(v.get(kk), 60) for kk in keys}
            if any(cell.values()):
                ins = v.get("inst")             # L64c — 계기 리스트가 설명을 바꾼 표시 (앞 설명 · 때)
                if isinstance(ins, dict) and cell.get("desc"):
                    cell["inst"] = {"old": _txt(ins.get("old"), 60), "at": _num(ins.get("at"), 0, 1e11, 0)}
                out[side][str(n)] = cell
    seen = set()
    for b in doc.get("blocks") if isinstance(doc.get("blocks"), list) else []:
        if not isinstance(b, dict) or b.get("kind") not in SYMBOLS:
            continue
        bid = _txt(b.get("id"), 16) or uuid.uuid4().hex[:6]
        if bid in seen:
            bid = uuid.uuid4().hex[:6]
        seen.add(bid)
        spec = SYMBOLS[b["kind"]]
        nb = {"id": bid, "kind": b["kind"],
              "x": _num(b.get("x"), 0, W), "y": _num(b.get("y"), 0, H),
              "w": _num(b.get("w"), 4, 400, spec["w"]), "h": _num(b.get("h"), 4, 300, spec["h"]),
              "text": _txt(b.get("text"), 40) or spec["text"], "label": _txt(b.get("label"), 60)}
        p = b.get("param") if isinstance(b.get("param"), dict) else {}
        param = {}
        if spec.get("time"):
            param["t"] = _num(p.get("t"), 0, 36000, 5)
        if spec.get("ab"):
            param["a"] = int(_num(p.get("a"), 1, 9, 2))
            param["b"] = int(_num(p.get("b"), 1, 9, 3))
            nb["text"] = f"{param['a']}/{param['b']}"
        if spec.get("cells") == 2:
            dom = str(p.get("dominant") or "")
            param["dominant"] = dom if dom in ("set", "reset") else ""
        if spec.get("bar") and isinstance(p.get("bar"), (list, tuple)) and len(p["bar"]) == 2:
            b0, b1 = _num(p["bar"][0], -300, 300, 0), _num(p["bar"][1], -300, 600, 0)
            if b1 - b0 >= 2:
                param["bar"] = [b0, b1]
        if spec.get("circle") and not spec.get("lamp"):
            pt_ = str(p.get("point") or "R").upper()[:1]
            param["point"] = pt_ if pt_ in ("R", "L", "T", "B") else "R"
            if p.get("tipr") is not None:
                param["tipr"] = _num(p.get("tipr"), 1.3, 2.2, TIP_RATIO)
        if spec.get("box") and isinstance(p.get("lines"), list):
            lines = []
            for q in p["lines"][:24]:
                if isinstance(q, (list, tuple)) and len(q) >= 3:
                    lines.append([_num(q[0], -50, 500, 0), _num(q[1], -50, 500, 0), _txt(q[2], 60), _num(q[3] if len(q) > 3 else 4.5, 2, 12, 4.5)])
            if lines:
                param["lines"] = lines
        if spec.get("macro"):
            param["typ"] = _txt(p.get("typ"), 40)                 # Typical 시트 이름 (이 묶음) 또는 lib:<id>
            param["title"] = _txt(p.get("title"), 120)
            for side in ("pins_in", "pins_out"):
                pins = []
                for q in (p.get(side) if isinstance(p.get(side), list) else [])[:MAX_PINS]:
                    if not isinstance(q, dict):
                        continue
                    pins.append({"name": _txt(q.get("name"), 40), "row": int(_num(q.get("row"), 0, 9999, 0)) or None,
                                 "dy": _num(q.get("dy"), 0, 2000, 0)})
                param[side] = pins
            nb["h"] = _num(b.get("h"), 4, 2000, spec["h"])     # 매크로는 상자가 길다 (표 높이까지)
        if spec.get("box") and p.get("mon"):
            param["mon"] = 1                            # L85 — 범례가 정한 감시 블록 (B.Q …)
        if not spec.get("note") and _txt(p.get("above"), 40):
            param["above"] = _txt(p.get("above"), 40)   # L56 — 블록 바로 위 글 (설정값 `202.4 barg` · `HH : 191` · 짧은 주석) — 분석기 analog._read_setpoint 가 읽는 자리
        nb["param"] = param
        out["blocks"].append(nb)
    for w in doc.get("wires") if isinstance(doc.get("wires"), list) else []:
        if not isinstance(w, dict) or not isinstance(w.get("pts"), list):
            continue
        pts = []
        for p in w["pts"]:
            if isinstance(p, (list, tuple)) and len(p) == 2:
                pts.append([_num(p[0], 0, W), _num(p[1], 0, H)])
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        if len(pts) >= 2:
            nw = {"id": _txt(w.get("id"), 16) or uuid.uuid4().hex[:6], "pts": pts, "dashed": bool(w.get("dashed"))}
            dots = [[_num(q[0], 0, W), _num(q[1], 0, H)] for q in (w.get("dots") if isinstance(w.get("dots"), list) else [])[:64]
                    if isinstance(q, (list, tuple)) and len(q) == 2]
            if dots:
                nw["dots"] = dots                       # 연결점 — 선이 다른 선의 몸통에 닿는 자리 (범례: DOT REPRESENTS LOGIC CONNECTION)
            marks = [[_num(q[0], 0, W), _num(q[1], 0, H), q[2]] for q in (w.get("marks") if isinstance(w.get("marks"), list) else [])[:16]
                     if isinstance(q, (list, tuple)) and len(q) == 3 and q[2] in MARK_KINDS]
            if marks:
                nw["marks"] = marks                     # L58 — 선 위의 인터페이스 표시 ◆ ■ (알다프라 양식 · 분석기는 선을 잇는 표시로 읽는다)
            if w.get("arrow") in ("start", "end"):
                nw["arrow"] = w["arrow"]
            if w.get("fx"):
                nw["fx"] = 1                            # L84 — 들여온 토막을 묶은 선 (곧게 펴기에서 붙든다)
            if _txt(w.get("label"), 40):
                nw["label"] = _txt(w.get("label"), 40)  # L56 — 선 아래 글 (아날로그 범위 `0~250 barg` · 신호 이름) — 분석기 analog._read_ranges 가 읽는 자리                # 화살촉 — 받는 쪽 끝 (상자 위·아래·오른쪽 변으로 들어가는 신호는 화살이 방향을 말한다)
            out["wires"].append(nw)
    out["wires"] = orthogonal_wires(out["wires"], blocks=out["blocks"])      # L64 — 사선 금지 · 곧게 직각으로
    return out


ORTHO_TOL = 2.5      # L64 — 이만큼 안에서 어긋난 토막은 곧게 편다 (반 행 격자 ≈ 6pt 의 1/5 · 분석한 도면의 좌표 흔들림 실측 ≤ 1pt)


def _corners(P: list) -> list:
    """남은 사선 토막에 꺾임점을 넣는다 — 첫 토막은 끝점에서 가로로 나가고, 마지막 토막은 가로로 들어가며,
    가운데는 앞 토막과 방향을 엇갈린다.  겹친 점 · 한 줄 위의 가운데 점은 뺀다.  logic_draw.js orthoPts 와 같다."""
    n = len(P)
    if n < 2:
        return P
    out = [list(P[0])]
    for i in range(1, n):
        a, b = out[-1], list(P[i])
        if abs(b[0] - a[0]) > 1e-6 and abs(b[1] - a[1]) > 1e-6:
            first, last = len(out) == 1, i == n - 1
            if first and last:
                mx = round((a[0] + b[0]) / 2, 2)
                out += [[mx, a[1]], [mx, b[1]]]
            elif first:
                out.append([b[0], a[1]])
            elif last:
                out.append([a[0], b[1]])
            else:
                pa = out[-2]
                out.append([a[0], b[1]] if abs(pa[1] - a[1]) < 1e-6 else [b[0], a[1]])
        out.append(b)
    res = [out[0]]
    for q in out[1:]:
        if abs(q[0] - res[-1][0]) < 1e-6 and abs(q[1] - res[-1][1]) < 1e-6:
            continue
        if len(res) >= 2:
            a, b = res[-2], res[-1]
            if (abs(a[0] - b[0]) < 1e-6 and abs(b[0] - q[0]) < 1e-6) or (abs(a[1] - b[1]) < 1e-6 and abs(b[1] - q[1]) < 1e-6):
                res[-1] = q
                continue
        res.append(q)
    return [[round(x, 2), round(y, 2)] for x, y in res]


def orthogonal(pts: list) -> list:
    """한 선만 — 사선 토막에 꺾임점을 넣는다 (곧게 펴기는 그림 전체에서 해야 맞닿은 자리가 지켜진다 — orthogonal_wires)."""
    return _corners([[float(p[0]), float(p[1])] for p in pts])


def _snap_axis(vals: list, fixed: list, tol: float) -> dict:
    """좌표 값 → 맞출 값.  ① 끝점(단자 · 행 자리)의 값이 tol 안의 값들을 가져간다 (가장 가까운 끝점 값) — 끝점은 움직이지 않는다.
    ② 남은 값은 작은 쪽부터 폭 tol 안의 무리로 묶어 가운데 값으로.  무리의 폭을 tol 로 막아 둔다 — 사이 값이 다리가 되어
    따로 있던 두 선(예: 입력 둘 3pt 간격)이 한 높이로 합쳐지지 않게."""
    out = {}
    fx = sorted(set(fixed))
    for v in fx:
        out[v] = v
    rest = []
    for v in sorted(set(vals)):
        if v in out:
            continue
        near = min(fx, key=lambda f: abs(f - v)) if fx else None
        if near is not None and abs(near - v) < tol:
            out[v] = near
        else:
            rest.append(v)
    grp = []
    for v in rest + [None]:
        if grp and (v is None or v - grp[0] >= tol):
            c = min(grp, key=lambda c: sum(abs(c - u) for u in grp))
            for u in grp:
                out[u] = c
            grp = []
        if v is not None:
            grp.append(v)
    return out


def _anchors(blocks: list):
    """끝점이 정말 붙어 있는 자리 — 표의 행 자리(LX0 · LX1) · 블록의 단자 · 블록 상자 · 입력 막대.  여기 닿은 끝은 움직이지 않는다."""
    edges = []
    for b in blocks or []:
        try:
            x, y, w, h = float(b["x"]), float(b["y"]), float(b["w"]), float(b["h"])
        except (KeyError, TypeError, ValueError):
            continue
        sp = SYMBOLS.get(b.get("kind"), {})
        if sp.get("circle") or sp.get("macro"):          # 원(램프 · 연결 기호)은 접점 · 매크로는 단자 행 — 미끄러지면 떨어진다 → 두 축 다
            edges += [("p", None, (x, y), (x + w, y + h))]
            continue
        edges += [("h", y, x, x + w), ("h", y + h, x, x + w), ("v", x, y, y + h), ("v", x + w, y, y + h)]
        if SYMBOLS.get(b.get("kind"), {}).get("bar"):
            bx0, by0, bx1, by1 = bar_of(b)
            edges.append(("v", bx0, min(by0, by1), max(by0, by1)))
    e = 0.6
    cell, idx = 24.0, {}                                 # L65 — 변 상자 색인 (점 근처의 변만 본다 · 답은 같다)
    for i, (k, c, lo, hi) in enumerate(edges):
        if k == "p":
            bx = (lo[0], lo[1], hi[0], hi[1])
        elif k == "h":
            bx = (lo, c, hi, c)
        else:
            bx = (c, lo, c, hi)
        for cx in range(int((bx[0] - e) // cell), int((bx[2] + e) // cell) + 1):
            for cy in range(int((bx[1] - e) // cell), int((bx[3] + e) // cell) + 1):
                idx.setdefault((cx, cy), []).append(i)

    def anchored(p):
        """(x 를 지켜야 하나, y 를 지켜야 하나) — 세로 변(행 자리 · 상자 왼쪽/오른쪽 · 막대)에 닿은 끝은 그 변을 따라 미끄러져도
        닿아 있으니 x 만, 가로 변(상자 위/아래)에 닿은 끝은 y 만 지킨다."""
        if abs(p[0] - LX0) < e or abs(p[0] - LX1) < e:
            return True, True, True                   # 행 자리 — 행 가운데를 떠나면 다른 행이 된다
        fx = fy = False
        for i in idx.get((int(p[0] // cell), int(p[1] // cell)), ()):
            k, c, lo, hi = edges[i]
            if k == "p":
                if lo[0] - e <= p[0] <= hi[0] + e and lo[1] - e <= p[1] <= hi[1] + e:
                    return True, True, True
                continue
            if k == "h" and abs(p[1] - c) < e and lo - e <= p[0] <= hi + e:
                fy = True
            if k == "v" and abs(p[0] - c) < e and lo - e <= p[1] <= hi + e:
                fx = True
        return fx, fy, False
    return anchored


def orthogonal_wires(wires: list, tol: float = ORTHO_TOL, blocks: list | None = None) -> list:
    """L64 — 선은 언제나 가로 · 세로로만 (사용자 지시: *"선은 곧게 직각으로 90도로 꺾여야 하며 사선이어서는 안 된다"*).
    ① 그림 전체의 꺾임점 좌표를 tol 안에서 같은 값으로 모은다 — 같은 자리에 있던 점은 계속 같은 자리, 몸통 위의 T 끝도 몸통 위에 남는다.
       끝점(단자 · 행 자리)은 움직이지 않는다.  ② 그래도 남은 사선 토막은 꺾임점을 넣어 ㄱ/ㄴ 으로."""
    anchored = _anchors(blocks) if blocks is not None else (lambda p: (True, True, True))

    def symbol_stroke(w):
        """기호 외곽 획(◇ · 램프 원을 토막으로 그린 것) — 두 점 · 45° 근처 · 한 행 길이 안.  신호선이 아니라 그대로 둔다."""
        pts = w["pts"]
        if len(pts) != 2:
            return False
        dx, dy = abs(pts[1][0] - pts[0][0]), abs(pts[1][1] - pts[0][1])
        return dx > tol and dy > tol and 0.5 <= dx / dy <= 2.0 and (dx * dx + dy * dy) ** 0.5 <= 1.2 * PITCH
    def settled(w):
        """L84 — 들여온 토막을 묶은 선(fx) 이 아직 가로 · 세로뿐이면 그대로 — 묶여 가운데가 된 꼭짓점은 끝점처럼 붙들 수 없어,
        다시 모으면 다른 선 끝으로 끌려가 연결이 바뀐다 (draw_compact 가 편 모양에서 묶어 견주었다)."""
        return bool(w.get("fx")) and all(abs(a[0] - b[0]) < 0.05 or abs(a[1] - b[1]) < 0.05 for a, b in zip(w["pts"], w["pts"][1:]))
    keep = [symbol_stroke(w) for w in wires]
    stay = [settled(w) for w in wires]
    fixed = []
    for w, k, st in zip(wires, keep, stay):
        pts = w["pts"]
        if k or st:                                  # 묶은 선은 모으기에 끼되(다른 선이 붙을 자리) 그 점은 움직이지 않는다
            fl = [(True, True)] * len(pts)
        else:
            fl = []
            for i, p in enumerate(pts):
                if i not in (0, len(pts) - 1):
                    fl.append((False, False))
                    continue
                ax, ay, full = anchored(p)                  # full — 원 · 매크로 · 행 자리는 두 축 다
                q = pts[1] if i == 0 else pts[-2]          # 끝점은 선의 길이 방향으로는 움직이지 않는다 (틈이 생긴다) — 수직 방향만 맞춘다
                if abs(q[0] - p[0]) <= abs(q[1] - p[1]):     # 세로로 들어오는 끝 — y 는 지키고 x 는 (닿은 가로 변 위라면) 미끄러져도 된다
                    fl.append((True, True) if full else (False, True))
                else:                                       # 가로로 들어오는 끝 — x 는 지키고 y 는 세로 변 · 막대를 따라 미끄러져도 된다
                    fl.append((True, True) if full else (True, False))
        fixed.append(fl)
    maps = []
    for ax_ in (0, 1):                               # 0 = x (세로 토막) · 1 = y (가로 토막)
        par = {}

        def find(v):
            while par.setdefault(v, v) != v:
                par[v] = par[par[v]]
                v = par[v]
            return v

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb
        fixed_vals, cnt = set(), {}
        for w, fl, k in zip(wires, fixed, keep):
            if k:
                continue
            pts = w["pts"]
            for p, f in zip(pts, fl):
                find(p[ax_])
                cnt[p[ax_]] = cnt.get(p[ax_], 0) + 1
                if f[ax_]:
                    fixed_vals.add(p[ax_])
            for a, b in zip(pts, pts[1:]):           # ① 한 토막의 두 끝은 같은 값이어야 한다 (거의 곧은 토막)
                d_ax, d_ot = abs(a[ax_] - b[ax_]), abs(a[1 - ax_] - b[1 - ax_])
                if 0 < d_ax < tol and d_ot >= d_ax:
                    union(a[ax_], b[ax_])
        # ② 끝점 값 가까이(tol 안)의 토막은 그 끝점 값으로 — 단 그 끝점이 토막 곁(다른 축 범위 안)에 있을 때만.
        #    (몸통 위 T 끝은 몸통을 잡아당기고, 3pt 떨어져 나란한 다른 입력은 끌려가지 않는다)
        fpts = sorted((p[ax_], p[1 - ax_]) for w, fl, k in zip(wires, fixed, keep) if not k
                      for p, f in zip(w["pts"], fl) if f[ax_])
        fkeys = [f[0] for f in fpts]
        for w, k in zip(wires, keep):
            if k:
                continue
            for a, b in zip(w["pts"], w["pts"][1:]):
                d_ax, d_ot = abs(a[ax_] - b[ax_]), abs(a[1 - ax_] - b[1 - ax_])
                if not (d_ax < tol and d_ot >= d_ax):
                    continue
                lo, hi = min(a[1 - ax_], b[1 - ax_]) - tol, max(a[1 - ax_], b[1 - ax_]) + tol
                for v in (a[ax_], b[ax_]):
                    if v in fixed_vals:
                        continue
                    best = None
                    for j in range(bisect.bisect_left(fkeys, v - tol), bisect.bisect_right(fkeys, v + tol)):
                        fval, fo = fpts[j]
                        if lo <= fo <= hi and (best is None or abs(fval - v) < abs(best - v)):
                            best = fval
                    if best is not None:
                        union(v, best)
        groups = {}
        for v in par:
            groups.setdefault(find(v), []).append(v)
        m = {}
        for g in groups.values():
            fs = [v for v in g if v in fixed_vals]
            rep = max(fs or g, key=lambda v: (cnt.get(v, 0), -abs(v - sorted(g)[len(g) // 2])))
            for v in g:
                m[v] = rep
        maps.append(m)
    mx, my = maps
    out = []
    for w, fl, k, st in zip(wires, fixed, keep, stay):
        if k or st:
            out.append(w)
            continue
        P = [[p[0] if ax else mx.get(p[0], p[0]), p[1] if ay else my.get(p[1], p[1])] for p, (ax, ay) in zip(w["pts"], fl)]
        out.append({**w, "pts": _corners(P)})
    return out


# ─────────────────────────── 저장 ───────────────────────────

def root() -> Path:
    p = store.root() / "drawings"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _dir(did: str) -> Path:
    if not ID_RE.match(did or ""):
        raise KeyError(did)
    return root() / did


def _path(did: str) -> Path:
    return _dir(did) / "drawing.json"


_DOC_CACHE: dict = {}          # L65 — 경로 → ((mtime_ns, 크기), pickle) · 바뀌지 않은 그림은 다시 파싱하지 않는다 (받을 때마다 새 사본)


def read_doc(p: Path, what=None) -> dict | None:
    import pickle
    try:
        st = p.stat()
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size, st.st_ino)
    hit = _DOC_CACHE.get(str(p))
    if hit and hit[0] == key:
        return pickle.loads(hit[1])
    doc = jsonstore.read(p, what, expect=dict)
    if doc:
        if len(_DOC_CACHE) > 4000:
            _DOC_CACHE.clear()
        _DOC_CACHE[str(p)] = (key, pickle.dumps(doc, protocol=pickle.HIGHEST_PROTOCOL))
    return doc


def load(did: str) -> dict:
    p = _path(did)
    if not p.exists():
        raise KeyError(did)
    return read_doc(p, "LOGIC 작도")


def save_new(doc: dict) -> dict:
    d = _dir(doc["id"])
    d.mkdir(parents=True, exist_ok=True)
    jsonstore.write(_path(doc["id"]), doc)
    return doc


@jsonstore.serialized
def save(did: str, body: dict, author: str) -> dict:
    """그림을 덮어쓴다 — 앞 판의 요약은 history 에 남는다 (지우지 않는다 · P&ID 메모 규율)."""
    author = _txt(author, 60)
    if not author:
        raise ValueError("작성자가 필요합니다.")
    cur = load(did)
    nd = clean(body)
    cur["history"] = (cur.get("history") or [])[-199:] + [{
        "author": cur.get("author", ""), "time": cur.get("updated"), "saves": cur.get("saves", 0),
        "blocks": len(cur.get("blocks") or []), "wires": len(cur.get("wires") or [])}]
    cur.update(nd)
    if "name" in body:
        cur["name"] = _txt(body.get("name"), 80) or cur["name"]
    if "project" in body:
        cur["project"] = _txt(body.get("project"), 80)
    for k, n in (("set", 16), ("set_name", 80)):
        if k in body:
            cur[k] = _txt(body.get(k), n)
    if "order" in body:
        cur["order"] = int(_num(body.get("order"), 0, 9999, 0))
    cur["author"] = author
    cur["updated"] = time.time()
    cur["saves"] = int(cur.get("saves") or 0) + 1
    jsonstore.write(_path(did), cur)
    return cur


def compact_saved(did: str) -> dict | None:
    """L84 — 들여온 그림(분석 시트 · 묶음 · 씨앗)의 선 토막을 연결 그대로 적은 선으로 묶어 다시 적는다 (한 번만 · `compact` 표시).
    계산은 잠금 밖에서 · 적을 때 그 사이 사람이 저장했으면(고친 때 · 저장 횟수 · 선이 다르면) 버린다.  고친 때 · 저장 횟수는 그대로 둔다."""
    import pickle
    from . import draw_compact
    cur = load(did)
    if int(cur.get("compact") or 0) >= draw_compact.VERSION or not draw_compact.imported(cur):
        return None
    work = pickle.loads(pickle.dumps(cur))
    rep = draw_compact.compact_doc(work)
    _commit_compact(did, cur, work)
    return rep


@jsonstore.serialized
def _commit_compact(did: str, cur: dict, work: dict):
    now = load(did)
    if (now.get("updated"), now.get("saves"), now.get("wires")) != (cur.get("updated"), cur.get("saves"), cur.get("wires")):
        return False
    now["wires"] = work["wires"]
    now["compact"] = work.get("compact", 0)
    jsonstore.write(_path(did), now)
    return True


def delete(did: str, author: str, log: list | None = None) -> dict:
    """그림을 지우고 지운 기록을 남긴다 (store.log_deletion — 분석 지우기와 같은 기록 파일 · 같은 꼴).
    log 를 주면 기록 줄을 거기 모아 두고 부르는 쪽이 한 번에 적는다 (프로젝트 지우기 — 수백 장)."""
    import shutil
    cur = load(did)
    d = _dir(did)
    entry = {"kind": "drawing", "id": did, "name": cur.get("name"), "project": cur.get("project"), "set": cur.get("set"),
             "author": _txt(author, 60), "time": time.time(), "blocks": len(cur.get("blocks") or [])}
    if log is None:
        store.log_deletion(entry)
    else:
        log.append(entry)
    shutil.rmtree(d, ignore_errors=True)
    return cur


# L77 — 업데이트에 실어 보내는 그림 묶음 (config/logic_draw_seed/*.json.gz).  처음 목록을 열 때 한 번 들인다 —
# 들인 표시(_seeded/<씨앗>)가 있으면 다시 들이지 않는다 (사람이 지운 묶음이 업데이트마다 되살아나지 않게) ·
# 같은 id 의 그림이 이미 있으면 덮지 않는다 (사람이 고친 판이 이긴다).  PID_DRAW_SEED=0 이면 끈다.
_SEED_DONE: dict = {}


def seed_dir() -> Path:
    from app import paths
    return paths.resource("config", "logic_draw_seed")


def install_seeds() -> list:
    import gzip
    import os
    if os.environ.get("PID_DRAW_SEED", "1") == "0":
        return []
    key = str(store.root())
    if _SEED_DONE.get(key):
        return []
    _SEED_DONE[key] = True
    out = []
    sd = seed_dir()
    if not sd.is_dir():
        return out
    mark = root() / "_seeded"
    for f in sorted(sd.glob("*.json.gz")):
        name = f.name[:-len(".json.gz")]
        try:
            pack = json.loads(gzip.decompress(f.read_bytes()).decode("utf-8"))
        except Exception:
            continue
        rev = int(pack.get("rev") or 1)
        if (mark / name).exists():
            # L78 — 씨앗의 판(rev)이 올랐으면 **사람이 손대지 않은** 그림만 새 판으로 바꾼다.  손대지 않음 = 저장 횟수 ·
            # 고친 때가 씨앗의 것과 같다 (사람이 저장하면 둘 다 바뀐다).  지운 그림은 되살리지 않는다.
            try:
                old = json.loads((mark / name).read_text(encoding="utf-8"))
            except Exception:
                old = {}
            if int(old.get("rev") or 1) >= rev:
                continue
            n = 0
            for doc in pack.get("docs") or []:
                if not ID_RE.match(doc.get("id") or "") or not _path(doc["id"]).exists():
                    continue
                cur = read_doc(_path(doc["id"])) or {}
                if cur == doc or cur.get("saves") != doc.get("saves") or cur.get("updated") != doc.get("updated"):
                    continue
                save_new(doc)
                n += 1
            old.update({"rev": rev, "updated_at": time.time(), "updated_docs": n})
            (mark / name).write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
            out.append({"seed": name, "updated": n, "rev": rev})
            continue
        pj = str(pack.get("project") or "").strip()
        if pj:                                                    # 로직 그리기의 프로젝트 하나로 — 프로젝트 장부에 없으면 만든다
            try:
                from . import projects
                if not any(p["name"].casefold() == pj.casefold() for p in projects.load()):
                    projects.create(pj, "업데이트")
            except Exception:
                pass
        n = 0
        for doc in pack.get("docs") or []:
            if not ID_RE.match(doc.get("id") or "") or _path(doc["id"]).exists():
                continue
            save_new(doc)
            n += 1
        mark.mkdir(parents=True, exist_ok=True)
        (mark / name).write_text(json.dumps({"at": time.time(), "docs": n, "rev": rev, "set": pack.get("set"), "name": pack.get("name")}, ensure_ascii=False), encoding="utf-8")
        out.append({"seed": name, "docs": n})
    return out


_LIST_CACHE: dict = {}      # L80 — 경로 → (파일 도장, 요약).  그림을 통째로 풀지 않고 바뀐 파일만 다시 읽는다


def listing() -> list:
    install_seeds()
    out = []
    seen = set()
    for d in root().iterdir():
        p = d / "drawing.json"
        try:
            st = p.stat()
        except OSError:
            continue
        key = (st.st_mtime_ns, st.st_size, st.st_ino)
        sp = str(p); seen.add(sp)
        hit = _LIST_CACHE.get(sp)
        if hit and hit[0] == key:
            out.append(dict(hit[1]))
            continue
        doc = read_doc(p)
        if not doc:
            continue
        it = ({k: doc.get(k) for k in ("id", "name", "project", "sheet_no", "title", "author", "created", "updated", "saves",
                                       "set", "set_name", "order", "typical")}
              | {"blocks": len(doc.get("blocks") or []), "wires": len(doc.get("wires") or []),
                 "rows": len(doc.get("left") or {}) + len(doc.get("right") or {})})
        _LIST_CACHE[sp] = (key, it)
        out.append(dict(it))
    for k in [k for k in _LIST_CACHE if k not in seen]:
        _LIST_CACHE.pop(k, None)
    out.sort(key=lambda x: (-(x.get("updated") or 0), x.get("id") or ""))
    return out


# ─────────────────────────── 기호 기하 (화면과 같은 규칙) ───────────────────────────

ABOVE_FS = 4.6


def block_geometry(b: dict) -> dict:
    """상자 · 막대 · 칸 · 글자 자리 — 화면의 logic_draw.js `geom()` 과 같은 수를 내야 한다.
    `param.above` 가 있으면 블록 위 변에서 0.5P 위에 가운데 맞춰 한 줄 더 (어느 종류든)."""
    g = _block_geometry(b)
    ab = (b.get("param") or {}).get("above")
    if ab:
        g["texts"].append([b["x"] + b["w"] / 2, b["y"] - 0.5 * PITCH, ab, ABOVE_FS])
    return g


def _block_geometry(b: dict) -> dict:
    spec = SYMBOLS[b["kind"]]
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    g = {"box": [x, y, x + w, y + h], "cells": [], "bar": None, "circle": None, "pointer": None, "texts": []}
    if spec.get("circle") and spec.get("lamp"):
        r = min(w, h) / 2
        cx, cy = x + w / 2, y + h / 2
        g["circle"] = [cx, cy, r]
        g["texts"].append([cx, cy, (b.get("text") or "G")[:2], min(h * 0.7, 7)])
        return g
    if spec.get("circle"):
        r = min(w, h) / 2
        cx, cy = x + w / 2, y + h / 2
        g["circle"] = [cx, cy, r]
        # 꼭지 삼각형 — 밑변이 원 위의 현 · 꼭지가 바깥 (분석기 graph.build 가 이것으로 연결 기호를 알아본다).  방향은 param.point (R·L·T·B)
        a = 0.6
        pt_ = ((b.get("param") or {}).get("point") or "R")
        tr = tip_ratio(b)
        ca, sa = r * math.cos(a), r * math.sin(a)
        g["pointer"] = {"R": [[cx + ca, cy - sa], [cx + ca, cy + sa], [cx + r * tr, cy]],
                        "L": [[cx - ca, cy - sa], [cx - ca, cy + sa], [cx - r * tr, cy]],
                        "T": [[cx - sa, cy - ca], [cx + sa, cy - ca], [cx, cy - r * tr]],
                        "B": [[cx - sa, cy + ca], [cx + sa, cy + ca], [cx, cy + r * tr]]}.get(pt_) or \
                       [[cx + ca, cy - sa], [cx + ca, cy + sa], [cx + r * tr, cy]]
        g["texts"].append([cx, cy, b["text"], min(h * 0.7, 7)])
        return g
    if spec.get("box") and (b.get("param") or {}).get("lines"):
        for dx, dy, t, fs in b["param"]["lines"]:
            g["texts"].append([x + dx, y + dy, t, fs, "start"])
        return g
    if spec.get("bar"):
        g["bar"] = bar_of(b)
    if spec.get("cells") == 2:
        g["cells"] = [[x, y, x + w, y + h / 2], [x, y + h / 2, x + w, y + h]]
        s, r = ("SO", "R") if b["param"].get("dominant") == "set" else (("S", "RO") if b["param"].get("dominant") == "reset" else ("S", "R"))
        g["texts"].append([x + w / 2, y + h / 4, s, min(h / 2 * 0.7, 7)])
        g["texts"].append([x + w / 2, y + 3 * h / 4, r, min(h / 2 * 0.7, 7)])
        return g
    if spec.get("note"):
        g["box"] = None
        g["texts"].append([x + w / 2, y + h / 2, b["text"], min(h * 0.8, 8)])
        return g
    if spec.get("macro"):
        # 머리: 이름 (길면 두 줄 — 분석기 _caption/_top_line 이 첫 단자 위 글을 통째로 이름으로 읽는다)
        title = (b.get("param") or {}).get("title") or b.get("text") or ""
        lines = _wrap(title, max(8, int(w / 2.6)))[:3]
        big = " | " in str(title)                      # 줄을 명시한 이름은 첫 줄을 크게 (원본 매크로 머리 `FG COMPR SYS` / `GRP`)
        for i, ln in enumerate(lines):
            g["texts"].append([x + w / 2, y + 0.5 * PITCH + i * 0.6 * PITCH + (0.15 * PITCH if big and i else 0),
                               ln, fit_fs(ln, w - 2, 6.5 if big and i == 0 else 4.6)])
        for q in (b.get("param") or {}).get("pins_in") or []:
            g["texts"].append([x + 1.5, y + q["dy"], q["name"], MACRO_PIN_FS, "start"])
        for q in (b.get("param") or {}).get("pins_out") or []:
            g["texts"].append([x + w - 1.5, y + q["dy"], q["name"], MACRO_PIN_FS, "end"])
        return g
    g["texts"].append([x + w / 2, y + h / 2, b["text"], fit_fs(b["text"], w - 2.2, min(h * 0.6, 7))])
    if spec.get("time"):
        g["texts"].append([x + w / 2, y + h + 6, f"{b['param'].get('t', 5):g} sec", 5])
    if spec.get("label") and b.get("label"):
        g["texts"].append([x + w / 2, y + h + 6, b["label"], 5])
    return g


_CHAR_W = 0.56       # helv 평균 글자 폭 / 글자 크기 (분석기와 무관 · 글자가 상자 밖으로 나가지 않게 줄이는 용도)


def fit_fs(text: str, width: float, fs: float) -> float:
    """글자가 상자 폭 안에 들게 글자 크기를 줄인다 (상자 밖 글자는 분석기가 상자의 글자로 읽지 않는다)."""
    try:
        tw = pymupdf.get_text_length(str(text or ""), fontname="helv", fontsize=fs)
    except Exception:
        tw = len(str(text or "")) * fs * _CHAR_W
    if tw <= width or tw <= 0:
        return round(fs, 2)
    return round(max(1.6, fs * width / tw * 0.97), 2)


def bar_of(b: dict) -> list:
    """입력 막대 — 기본은 상자 높이 + 위아래 한 행.  param.bar = [위 dy, 아래 dy] (상자 윗변 기준 · 들여온 그림이 원래 막대 길이를 지킨다)."""
    x, y, h = b["x"], b["y"], b["h"]
    p = b.get("param") or {}
    bar = p.get("bar")
    if isinstance(bar, (list, tuple)) and len(bar) == 2:
        return [x, y + float(bar[0]), x, y + float(bar[1])]
    L = h + BAR_EXTRA
    cy = y + h / 2
    return [x, cy - L / 2, x, cy + L / 2]


ARROW_L = 0.22 * PITCH       # 화살촉 길이 · 반폭 (분석기 geom: 칠한 삼각형이면 화살촉 — 크기 제한 없음 · 꼭지 = 가장 짧은 변의 맞은편)


def arrow_of(w: dict):
    """선의 한쪽 끝에 그릴 화살촉 삼각형 (꼭지 = 그 끝 · 밑변은 선 위 뒤쪽)."""
    a = w.get("arrow")
    pts = w.get("pts") or []
    if a not in ("start", "end") or len(pts) < 2:
        return None
    tip, back = (pts[0], pts[1]) if a == "start" else (pts[-1], pts[-2])
    dx, dy = back[0] - tip[0], back[1] - tip[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    bx, by = tip[0] + ux * ARROW_L, tip[1] + uy * ARROW_L
    hx, hy = -uy * ARROW_L * 0.5, ux * ARROW_L * 0.5
    return [[round(tip[0], 2), round(tip[1], 2)], [round(bx + hx, 2), round(by + hy, 2)], [round(bx - hx, 2), round(by - hy, 2)]]


TIP_RATIO = 1.75             # 연결 기호 꼭지 길이 / 반지름 — HRSG 실측 1.8 (2.2 로 두면 바로 뒤에 붙는 NOT 상자를 꼭지가 덮는다)


def tip_ratio(b: dict) -> float:
    try:
        v = float((b.get("param") or {}).get("tipr") or TIP_RATIO)
    except (TypeError, ValueError):
        v = TIP_RATIO
    return max(1.3, min(2.2, v))


def _wrap(text: str, n: int) -> list:
    if " | " in str(text or ""):                     # 줄을 명시한 이름 (`FG COMPR SYS | GRP` — _txt 가 줄바꿈을 지우므로 구분자로)
        return [ln.strip() for ln in str(text).split(" | ") if ln.strip()] or [""]
    words, out, cur = str(text or "").split(), [], ""
    for wd in words:
        if cur and len(cur) + 1 + len(wd) > n:
            out.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur:
        out.append(cur)
    return out or [""]


def macro_pins(typ_doc: dict) -> tuple:
    """Typical 시트(이 양식의 그림)의 행 → 매크로 단자.  왼쪽 행(설명 있음) = 입력 · 오른쪽 = 출력.
    단자 이름은 TAG NO. 칸(약어)이 있으면 그것, 없으면 설명의 머리글자 — 분석기 macro._assign 이 이름 · 설명으로 행과 맞댄다."""
    def name_of(v):
        k = (v.get("kks") or "").strip()
        if k:
            return k[:14]
        return "".join(w[0] for w in (v.get("desc") or "").split() if w[:1].isalnum())[:8]
    ins = [{"name": name_of(v), "row": int(k)} for k, v in sorted(typ_doc.get("left", {}).items(), key=lambda kv: int(kv[0])) if (v.get("desc") or "").strip()]
    outs = [{"name": name_of(v), "row": int(k)} for k, v in sorted(typ_doc.get("right", {}).items(), key=lambda kv: int(kv[0])) if (v.get("desc") or "").strip()]
    return ins[:MAX_PINS], outs[:MAX_PINS]


def macro_block(title: str, typ: str, ins: list, outs: list, x: float, y: float) -> dict:
    """팔레트가 놓는 매크로 상자 — 단자는 한 행 간격 (학습한 양식: 행마다 단자 하나)."""
    n = max(len(ins), len(outs), 1)
    h = round(MACRO_TOP + n * PITCH + 0.4 * PITCH, 2)
    pins_in = [{"name": q["name"], "row": q.get("row"), "dy": round(MACRO_TOP + (i + 0.5) * PITCH, 2)} for i, q in enumerate(ins)]
    pins_out = [{"name": q["name"], "row": q.get("row"), "dy": round(MACRO_TOP + (i + 0.5) * PITCH, 2)} for i, q in enumerate(outs)]
    return {"id": uuid.uuid4().hex[:6], "kind": "MACRO", "x": x, "y": y, "w": SYMBOLS["MACRO"]["w"], "h": h, "text": "", "label": "",
            "param": {"typ": typ, "title": title, "pins_in": pins_in, "pins_out": pins_out}}


def ports_of(b: dict) -> list:
    """붙일 자리 — 화면의 자석.  [x, y, dir, role]"""
    spec = SYMBOLS[b["kind"]]
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    if spec.get("macro"):
        p = b.get("param") or {}
        return [[x, y + q["dy"], "in", q["name"]] for q in p.get("pins_in") or []] + \
               [[x + w, y + q["dy"], "out", q["name"]] for q in p.get("pins_out") or []]
    if spec.get("circle") and spec.get("lamp"):
        r = min(w, h) / 2
        return [[x + w / 2 - r, y + h / 2, "in", ""], [x + w / 2, y + h / 2 - r, "in", ""], [x + w / 2, y + h / 2 + r, "in", ""], [x + w / 2 + r, y + h / 2, "in", ""]]
    if spec.get("circle"):
        r = min(w, h) / 2
        cx, cy = x + w / 2, y + h / 2
        pt_ = ((b.get("param") or {}).get("point") or "R")
        tr = tip_ratio(b)
        tip = {"R": [cx + r * tr, cy], "L": [cx - r * tr, cy], "T": [cx, cy - r * tr], "B": [cx, cy + r * tr]}.get(pt_, [cx + r * tr, cy])
        edges = {"R": [cx - r, cy], "L": [cx + r, cy], "T": [cx, cy + r], "B": [cx, cy - r]}
        return [[edges.get(pt_, [cx - r, cy])[0], edges.get(pt_, [cx - r, cy])[1], "in", ""], [tip[0], tip[1], "out", ""]]
    if spec.get("cells") == 2:
        return [[x, y + h / 4, "in", "set"], [x, y + 3 * h / 4, "in", "reset"],
                [x + w, y + h / 4, "out", "q"], [x + w, y + 3 * h / 4, "out", "qn"]]
    if spec.get("note"):
        return []
    out = [[x + w, y + h / 2, "out", ""]]
    if spec.get("logic") == "source":
        return out
    if spec.get("bar"):
        _, b0, _, b1 = bar_of(b)
        L = b1 - b0
        cy = (b0 + b1) / 2
        k = max(1, int(L // PITCH))
        ys = [cy + (i - (k - 1) / 2) * PITCH for i in range(k)]
        return [[x, yy, "in", ""] for yy in ys] + out
    return [[x, y + h / 2, "in", ""]] + out


# ─────────────────────────── PDF ───────────────────────────

def _line(page, pts, dashes=None):
    sh = page.new_shape()
    for a, b in zip(pts, pts[1:]):
        sh.draw_line(pymupdf.Point(*a), pymupdf.Point(*b))
    sh.finish(color=K, width=LW, closePath=False, dashes=dashes)
    sh.commit()


def _rect(page, r):
    sh = page.new_shape()
    sh.draw_rect(pymupdf.Rect(*r))
    sh.finish(color=K, width=LW)
    sh.commit()


def _ctext(page, cx, cy, text, fs, anchor="middle"):
    """가운데(또는 왼쪽·오른쪽) 맞춘 글자 (helv · 한글이면 korea)."""
    fn = _font(text)
    text = str(text)
    tw = pymupdf.get_text_length(text, fontname=fn, fontsize=fs)
    x = cx if anchor == "start" else cx - tw if anchor == "end" else cx - tw / 2
    page.insert_text((x, cy + fs * 0.35), text, fontsize=fs, fontname=fn)


def _table(page, doc):
    N = doc["N"]
    bottom = TOP + N * PITCH
    for x in LCOLS + RCOLS:
        _line(page, [(x, TOP - 2 * PITCH), (x, bottom)])
    for k in range(N + 1):
        _line(page, [(LCOLS[0], TOP + k * PITCH), (LX0, TOP + k * PITCH)])
        _line(page, [(LX1, TOP + k * PITCH), (RCOLS[-1], TOP + k * PITCH)])
    _line(page, [(LCOLS[0], TOP - 2 * PITCH), (LX0, TOP - 2 * PITCH)])
    _line(page, [(LX1, TOP - 2 * PITCH), (RCOLS[-1], TOP - 2 * PITCH)])
    heads = [((LCOLS[0] + LCOLS[1]) / 2, "FROM"), ((LCOLS[1] + LCOLS[2]) / 2, "NO."), ((LCOLS[2] + LCOLS[3]) / 2, "TAG NO."),
             ((LCOLS[3] + LCOLS[4]) / 2, "SERVICE"),
             ((RCOLS[0] + RCOLS[1]) / 2, "SERVICE"), ((RCOLS[1] + RCOLS[2]) / 2, "TAG NO."), ((RCOLS[2] + RCOLS[3]) / 2, "NO."),
             ((RCOLS[3] + RCOLS[4]) / 2, "TO")]
    for x, t in heads:
        _ctext(page, x, TOP - PITCH, t, 6)
    for k in range(N):
        _ctext(page, (LCOLS[1] + LCOLS[2]) / 2, TOP + k * PITCH + PITCH / 2, str(k + 1), 5)
        _ctext(page, (RCOLS[2] + RCOLS[3]) / 2, TOP + k * PITCH + PITCH / 2, str(N + k + 1), 5)
    for k, v in doc["left"].items():
        yy = ry(int(k), N) + 1.8
        page.insert_text((LCOLS[0] + 2, yy), v.get("fm", ""), fontsize=5, fontname="helv")
        page.insert_text((LCOLS[2] + 2, yy), v.get("kks", ""), fontsize=5, fontname="helv")
        page.insert_text((LCOLS[3] + 2, yy), v.get("desc", ""), fontsize=5, fontname="helv")
    for k, v in doc["right"].items():
        yy = ry(int(k), N) + 1.8
        page.insert_text((RCOLS[0] + 2, yy), v.get("desc", ""), fontsize=5, fontname="helv")
        page.insert_text((RCOLS[1] + 2, yy), v.get("kks", ""), fontsize=5, fontname="helv")
        page.insert_text((RCOLS[3] + 2, yy), v.get("to", ""), fontsize=5, fontname="helv")
    if (doc.get("form") or "") == "a5j":
        _a5j_frame(page, doc)
        return
    # 타이틀블록 — 문서 번호 · 제목 · 캡션 SHEET NO. 아래 시트 이름 (분석기는 캡션 아래 칸에서 시트 이름을 읽는다)
    lay = layout(N)["title"]
    _rect(page, (560, 780, 1170, 830))
    _line(page, [(1060, 780), (1060, 830)])
    _line(page, [(560, 795), (1170, 795)])
    # 제목은 문서 번호 **위** 같은 칸에 · 오른쪽 반(x > W/2)에 — 분석기(glyphs._title_lines)가 도면번호(숫자-숫자 꼴) 위 글줄을 제목으로 읽는다 (19VA 양식)
    page.insert_text((620, 808), doc.get("title") or "", fontsize=8, fontname="helv")
    page.insert_text((620, 824), doc.get("doc_no") or "", fontsize=7, fontname="helv")
    page.insert_text((lay["caption"][0] - 30, lay["caption"][1] + 2), "SHEET NO.", fontsize=5, fontname="helv")
    page.insert_text((lay["sheet"][0] - 30, lay["sheet"][1] + 15), doc.get("sheet_no") or "", fontsize=9, fontname="helv")


def _a5j_frame(page, doc):
    """알다프라 양식 — LOGIC 머리글 칸 · 도면 테두리 · NOTE 상자 · 삼성 C&T 타이틀블록.  글자 자리는 1A5J 원본 그대로:
    SHEET 캡션 아래 시트 이름 · DRAWING TITLE 아래 제목(도면번호 위 글줄) · PROJECT DWG NO. 아래 도면번호."""
    N = doc["N"]
    _line(page, [(LX0, TOP - 2 * PITCH), (LX1, TOP - 2 * PITCH)])
    _ctext(page, (LX0 + LX1) / 2, TOP - PITCH, "LOGIC", 7)
    fx0, fy0, fx1, fy1 = A5J_FRAME
    _rect(page, A5J_FRAME)
    _rect(page, (fx0 + 7, fy0 + 7, fx1 - 7, fy1 - 7))
    for i in range(8):                                 # 구역 번호 8..1 (위·아래) · 글자 H..A (좌·우) — 원본의 테두리 눈금
        xx = fx0 + 7 + (fx1 - fx0 - 14) * (i + 0.5) / 8
        _ctext(page, xx, fy0 + 3.5, str(8 - i), 4)
        _ctext(page, xx, fy1 - 3.5, str(8 - i), 4)
        yy = fy0 + 7 + (fy1 - fy0 - 14) * (i + 0.5) / 8
        _ctext(page, fx0 + 3.5, yy, "HGFEDCBA"[i], 4)
        _ctext(page, fx1 - 3.5, yy, "HGFEDCBA"[i], 4)
    page.insert_text((NOTES_BOX[0] + 4, NOTES_BOX[1] + 12), "NOTE :", fontsize=8, fontname="helv")
    # 타이틀블록
    # 제목 줄은 SHEET 값보다 글자 높이 두 배 넘게 위에 — 분석기 glyphs._title_words 가 SHEET 값 높이 띠(±2h) 안의 글을 부제로 읽어
    # 제목을 도면번호와 시트 이름 사이 조각(`GAS TEST`)으로 자른다 (원본도 제목 줄을 그 띠 밖에 둔다)
    x0, y0, x1, y1 = 900.0, 735.0, 1160.0, 830.0
    _rect(page, (x0, y0, x1, y1))
    rows_ = (y0, y0 + 18, y0 + 50, y0 + 78, y1)       # PROJECT NAME | DRAWING TITLE | PROJECT DWG NO. · SHEET · REV | PROJECT NO. · SCALE · REF
    # (SCALE 캡션은 SHEET 값의 높이 띠(±2h) 밖에 — 안에 들면 Typical 장(숫자 넷 시트 이름)의 부제로 읽힌다)
    for yy in rows_[1:-1]:
        _line(page, [(x0, yy), (x1, yy)])
    cap = lambda x, y, t: page.insert_text((x + 2, y + 5), t, fontsize=3.6, fontname="helv")
    cap(x0, rows_[0], "PROJECT NAME")
    _ctext(page, (x0 + x1) / 2 + 20, rows_[0] + 12, doc.get("project_name") or "", 8)
    cap(x0, rows_[1], "DRAWING TITLE")
    _ctext(page, (x0 + x1) / 2 + 20, rows_[1] + 9, "CONTROL LOGIC & LOOP DIAGRAM", 5.5)
    _ctext(page, (x0 + x1) / 2 + 20, rows_[1] + 17, doc.get("title") or "", 6)
    _line(page, [(x0 + 170, rows_[2]), (x0 + 170, rows_[4])])
    _line(page, [(x0 + 215, rows_[2]), (x0 + 215, rows_[4])])
    cap(x0, rows_[2], "PROJECT DWG NO.")
    _ctext(page, x0 + 85, rows_[2] + 10, doc.get("doc_no") or "", 6.5)
    cap(x0 + 170, rows_[2], "SHEET")
    _ctext(page, x0 + 185, rows_[2] + 13, doc.get("sheet_no") or "", 6.5)   # 캡션 SHEET 의 오른쪽 끝보다 왼쪽에서 시작 (캡션이 부제로 읽히지 않게 — 원본 자리)
    cap(x0 + 215, rows_[2], "REV.")
    _ctext(page, x0 + 237, rows_[2] + 13, doc.get("rev") or "", 6.5)
    cap(x0, rows_[3] + 7, "PROJECT NO.")                # 맨 아랫줄 캡션은 칸 아래쪽에 (SHEET 값의 높이 띠 밖)
    _ctext(page, x0 + 85, rows_[3] + 13, doc.get("project") or "", 5)
    cap(x0 + 170, rows_[3] + 7, "SCALE")
    _ctext(page, x0 + 205, rows_[3] + 13, "NONE", 4.5)
    cap(x0 + 215, rows_[3] + 7, "REF. CODE")
    _ctext(page, x0 + 250, rows_[3] + 13, "-", 4.5)


def _blocks(page, doc):
    form = doc.get("form") or ""
    for b in doc["blocks"]:
        g = block_geometry(b)
        if form == "a5j":
            g = shape_geometry(g, b)
        for ln in g.get("lines") or []:
            _line(page, [(ln[0], ln[1]), (ln[2], ln[3])])
        if g.get("ellipse"):
            sh = page.new_shape()
            sh.draw_oval(pymupdf.Rect(*g["ellipse"]))
            sh.finish(color=K, width=LW)
            sh.commit()
        if g["circle"]:
            sh = page.new_shape()
            sh.draw_circle(pymupdf.Point(g["circle"][0], g["circle"][1]), g["circle"][2])
            sh.finish(color=K, width=LW)
            sh.commit()
            if g["pointer"]:
                sh = page.new_shape()
                sh.draw_polyline([pymupdf.Point(*p) for p in g["pointer"]])
                sh.finish(color=K, fill=K, width=LW, closePath=True)
                sh.commit()
        elif g["cells"]:
            for c in g["cells"]:
                _rect(page, c)
        elif g["box"]:
            _rect(page, g["box"])
        if g["bar"]:
            _line(page, [(g["bar"][0], g["bar"][1]), (g["bar"][2], g["bar"][3])])
        for cx, cy, t, fs, *anc in g["texts"]:
            if t:
                _ctext(page, cx, cy, t, fs, anc[0] if anc else "middle")


LONG_V = 0.58 * H            # 이보다 긴 세로 신호선은 분석기(geom.layout)가 표 괘선(0.6H)으로 읽어 그 장이 통째로 빠진다


def export_wires(doc: dict) -> list:
    """내보낼 선 — 긴 세로선은 둘로 나누고 그 자리에 연결점을 찍는다 (연결점은 범례가 정한 '연결' 표시라 뜻이 같다).
    PDF · DXF 가 같은 목록을 그린다."""
    out = []
    for w in doc["wires"]:
        pts = [list(p) for p in w["pts"]]
        dots = [list(d) for d in (w.get("dots") or [])]
        parts, cur = [], [pts[0]]
        for a, b in zip(pts, pts[1:]):
            if abs(a[0] - b[0]) < 0.2 and abs(b[1] - a[1]) > LONG_V:
                mid = [a[0], round((a[1] + b[1]) / 2, 2)]
                cur.append(mid)
                parts.append(cur)
                cur = [mid]
                dots.append(mid)
            cur.append(b)
        parts.append(cur)
        for i, part in enumerate(parts):
            item = {"pts": part, "dashed": bool(w.get("dashed"))}
            if i == 0:
                item["dots"] = dots
                item["marks"] = [list(m) for m in (w.get("marks") or [])]
                if w.get("arrow") == "start":
                    item["arrow"] = "start"
            if i == len(parts) - 1 and w.get("arrow") == "end":
                item["arrow"] = "end"
            out.append(item)
    return out


NOTES_BOX = (30.0, 780.0, 540.0, 830.0)      # 장 노트 상자 — 표 아래 왼쪽 (타이틀블록 560~1170 의 왼쪽)

# L58 — 양식.  "" = 기본(HRSG 결 · 글자 게이트 · SHEET NO. 캡션) · "a5j" = 알다프라(삼성 C&T) 결:
#   게이트를 모양으로 (AND = 막대 + 빈 네모 · OR = 막대 + 원 · NOT = ⊠) · LOGIC 머리글 칸 · NOTE 상자 · 삼성 타이틀블록(PROJECT NAME ·
#   DRAWING TITLE · PROJECT DWG NO. · SHEET · REV.) · 도면 테두리.  분석기는 모양 게이트를 학습 사전(19VA 범례 열쇠 BAR_BOX · BAR_CIRCLE ·
#   CROSS_BOX)으로, 시트 이름은 SHEET 캡션 아래 칸에서, 제목은 도면번호 위 글줄에서 읽는다 — 1A5J 원본과 같은 자리.
FORMS = ("", "a5j")
DEFAULT_FORM = "a5j"        # L64 — 새 그림은 학습한 프로젝트와 같은 양식(LOGIC 머리글 · 테두리 · NOTE · 아래 타이틀블록)으로 시작한다
TITLE_KEYS = ("form", "project_name", "doc_no", "rev", "project")   # 묶음의 장끼리 같은 타이틀블록 값
SHAPE_KINDS = ("AND", "OR", "NOT")           # 모양으로 그리는 게이트 (그 밖은 글자 그대로 — 분석기가 글자로 읽는다)
A5J_FRAME = (16.0, 16.0, 1175.0, 836.0)


def shape_geometry(g: dict, b: dict) -> dict:
    """a5j 양식의 모양 게이트 — block_geometry 결과를 고친다 (글자 없음 · OR 은 원 · NOT 은 ⊠).  `lines` 는 더 그을 선."""
    k = b["kind"]
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    if k == "PB":
        g = dict(g)
        g["texts"] = [t for t in g["texts"] if t[1] <= y + h]       # 아래 이름 글은 안 쓴다 (칸이 쌓이면 다음 단추와 겹친다)
        g["texts"] = [[x + 2.2, y + h * 0.3, "P", 3.0], [x + 2.2, y + h * 0.72, "B", 3.0],
                      [x + 5.0 + (w - 5.0) / 2, y + h / 2, b.get("label") or "PB", min(h * 0.6, 5.0)]]
        g["lines"] = [[x + 5.0, y, x + 5.0, y + h]]
        return g
    if k == "ANN":
        g = dict(g)
        g["box"] = None
        g["ellipse"] = [x, y, x + w, y + h]
        return g
    if k not in SHAPE_KINDS:
        return g
    g = dict(g)
    g["texts"] = [t for t in g["texts"] if t[1] != b["y"] + b["h"] / 2]      # 상자 가운데 글자만 뺀다 (위 글 · 시간 글은 남긴다)
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    if k == "OR":
        r = min(w, h) / 2
        g["circle"] = [x + r, y + h / 2, r]          # 왼쪽 변이 막대에 닿게 (분석기 _bar_gate: 막대 x = 원 왼쪽)
        g["box"] = None
        g["pointer"] = None
        if w > 2 * r + 0.5:                          # 상자가 원보다 넓으면 원 오른쪽에서 출력 자리(x+w)까지 짧은 줄기 — 출력선이 매달리지 않게
            g["lines"] = [[x + 2 * r, y + h / 2, x + w, y + h / 2]]
    elif k == "NOT":
        g["lines"] = [[x, y, x + w, y + h], [x, y + h, x + w, y]]
    if SHAPE_LABELS and k in ("AND", "OR"):           # L67 — 모양 게이트에도 AND / OR 글자 (사용자: 게이트에 표기되어야 한다)
        if k == "OR":
            cx, d = g["circle"][0], 2 * g["circle"][2]
        else:
            cx, d = x + w / 2, min(w, h)
        g["texts"] = list(g["texts"]) + [[cx, y + h / 2, k, round(min(h * 0.42, d * 0.42 if k == "OR" else w * 0.3), 2)]]
    return g
SHAPE_LABELS = True
NOTES_COL = 170.0
NOTES_PER_COL = 6


def notes_layout(notes: list) -> list:
    """(x, y, 글) — 머리 NOTES 아래 번호 매긴 줄 · 한 열 6줄 · 열 폭 170 (화면 · PDF · DXF 가 같은 자리)."""
    out = []
    for i, t in enumerate(notes[:20]):
        c, r = divmod(i, NOTES_PER_COL)
        out.append([NOTES_BOX[0] + 4 + c * NOTES_COL, NOTES_BOX[1] + 14 + r * 6.2, f"{i + 1}. {t}"])
    return out


def wire_label_pos(w: dict):
    """선 글의 자리 — 첫 가로 토막 가운데에서 0.8P 아래 (분석기 _read_ranges: 가로 토막 아래 1.5P 안)."""
    pts = w["pts"]
    for a, b in zip(pts, pts[1:]):
        if abs(a[1] - b[1]) < 0.2 and abs(b[0] - a[0]) >= 6:
            return [(a[0] + b[0]) / 2, a[1] + 0.8 * PITCH]
    a, b = pts[0], pts[1]
    return [(a[0] + b[0]) / 2, max(a[1], b[1]) + 0.8 * PITCH]


def draw_page(pdf, doc: dict):
    """PDF 한 장 — 한 장짜리(to_pdf)와 묶음(draw_sets.to_pdf_set)이 같은 함수로 그린다."""
    doc = {**doc, **clean(doc)}
    page = pdf.new_page(width=W, height=H)
    _table(page, doc)
    _blocks(page, doc)
    if doc.get("notes"):
        _rect(page, NOTES_BOX)
        page.insert_text((NOTES_BOX[0] + 4, NOTES_BOX[1] + 7), "NOTES", fontsize=5.5, fontname="helv")
        for x, y, t in notes_layout(doc["notes"]):
            page.insert_text((x, y), t, fontsize=4.5, fontname=_font(t))
    for w in doc["wires"]:
        if w.get("label"):
            lx, ly = wire_label_pos(w)
            _ctext(page, lx, ly, w["label"], 4.5)
    for w in export_wires(doc):
        _line(page, [tuple(p) for p in w["pts"]], dashes="[3 3] 0" if w.get("dashed") else None)
        for dx, dy in w.get("dots") or []:
            sh = page.new_shape()
            sh.draw_circle(pymupdf.Point(dx, dy), DOT_R)
            sh.finish(color=K, fill=K, width=0)
            sh.commit()
        for mx, my, kind in w.get("marks") or []:
            sh = page.new_shape()
            sh.draw_polyline([pymupdf.Point(*q) for q in mark_polygon(mx, my, kind)])
            sh.finish(color=K, fill=K, width=0, closePath=True)
            sh.commit()
        tri = arrow_of(w)
        if tri:
            sh = page.new_shape()
            sh.draw_polyline([pymupdf.Point(*q) for q in tri])
            sh.finish(color=K, fill=K, width=0, closePath=True)
            sh.commit()
    return page


def to_pdf(doc: dict) -> bytes:
    pdf = pymupdf.open()
    draw_page(pdf, doc)
    pdf.set_metadata({"title": doc.get("title") or doc.get("name") or "LOGIC", "producer": "PID LOGIC 작도"})
    return pdf.tobytes()


# ─────────────────────────── DXF ───────────────────────────

def to_dxf(doc: dict) -> bytes:
    """같은 그림을 DXF 로 (ezdxf · 모델 공간 · y 는 위로 — PDF y 를 뒤집는다 · 1 단위 = 1 pt).
    층: TABLE · TEXT · LOGIC · SYMBOL · WIRE · DASHED · TITLE."""
    import ezdxf

    doc = {**doc, **clean(doc)}
    N = doc["N"]
    dwg = ezdxf.new("R2010")
    for name, color in (("TABLE", 7), ("TEXT", 7), ("SYMBOL", 7), ("WIRE", 7), ("DASHED", 7), ("TITLE", 7)):
        dwg.layers.add(name, color=color)
    if "DASHED" not in dwg.linetypes:
        dwg.linetypes.add("DASHED", pattern=[6.0, 3.0, -3.0])
    dwg.layers.get("DASHED").dxf.linetype = "DASHED"
    msp = dwg.modelspace()

    def P(x, y):
        return (x, H - y)

    def line(a, b, layer="WIRE", dashed=False):
        e = msp.add_line(P(*a), P(*b), dxfattribs={"layer": layer})
        if dashed:
            e.dxf.linetype = "DASHED"

    def rect(r, layer="SYMBOL"):
        x0, y0, x1, y1 = r
        msp.add_lwpolyline([P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)], close=True, dxfattribs={"layer": layer})

    def text(x, y, t, h, layer="TEXT", align="LEFT"):
        if not t:
            return
        e = msp.add_text(str(t), dxfattribs={"layer": layer, "height": h})
        al = {"CENTER": ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER, "RIGHT": ezdxf.enums.TextEntityAlignment.MIDDLE_RIGHT,
              "MLEFT": ezdxf.enums.TextEntityAlignment.MIDDLE_LEFT}.get(align, ezdxf.enums.TextEntityAlignment.LEFT)
        e.set_placement(P(x, y), align=al)

    bottom = TOP + N * PITCH
    for x in LCOLS + RCOLS:
        line((x, TOP - 2 * PITCH), (x, bottom), "TABLE")
    for k in range(N + 1):
        line((LCOLS[0], TOP + k * PITCH), (LX0, TOP + k * PITCH), "TABLE")
        line((LX1, TOP + k * PITCH), (RCOLS[-1], TOP + k * PITCH), "TABLE")
    line((LCOLS[0], TOP - 2 * PITCH), (LX0, TOP - 2 * PITCH), "TABLE")
    line((LX1, TOP - 2 * PITCH), (RCOLS[-1], TOP - 2 * PITCH), "TABLE")
    for x, t in (((LCOLS[0] + LCOLS[1]) / 2, "FROM"), ((LCOLS[1] + LCOLS[2]) / 2, "NO."), ((LCOLS[2] + LCOLS[3]) / 2, "TAG NO."),
                 ((LCOLS[3] + LCOLS[4]) / 2, "SERVICE"), ((RCOLS[0] + RCOLS[1]) / 2, "SERVICE"),
                 ((RCOLS[1] + RCOLS[2]) / 2, "TAG NO."), ((RCOLS[2] + RCOLS[3]) / 2, "NO."), ((RCOLS[3] + RCOLS[4]) / 2, "TO")):
        text(x, TOP - PITCH, t, 5, "TEXT", "CENTER")
    for k in range(N):
        text((LCOLS[1] + LCOLS[2]) / 2, TOP + k * PITCH + PITCH / 2, str(k + 1), 4, "TEXT", "CENTER")
        text((RCOLS[2] + RCOLS[3]) / 2, TOP + k * PITCH + PITCH / 2, str(N + k + 1), 4, "TEXT", "CENTER")
    for k, v in doc["left"].items():
        yy = ry(int(k), N)
        text(LCOLS[0] + 2, yy, v.get("fm"), 4)
        text(LCOLS[2] + 2, yy, v.get("kks"), 4)
        text(LCOLS[3] + 2, yy, v.get("desc"), 4)
    for k, v in doc["right"].items():
        yy = ry(int(k), N)
        text(RCOLS[0] + 2, yy, v.get("desc"), 4)
        text(RCOLS[1] + 2, yy, v.get("kks"), 4)
        text(RCOLS[3] + 2, yy, v.get("to"), 4)
    rect((560, 780, 1170, 830), "TITLE")
    line((1060, 780), (1060, 830), "TITLE")
    line((560, 795), (1170, 795), "TITLE")
    text(620, 806, doc.get("title"), 7, "TITLE")
    text(620, 822, doc.get("doc_no"), 6, "TITLE")
    text(1070, 790, "SHEET NO.", 4, "TITLE")
    text(1070, 815, doc.get("sheet_no"), 8, "TITLE")
    for b in doc["blocks"]:
        g = block_geometry(b)
        if (doc.get("form") or "") == "a5j":
            g = shape_geometry(g, b)
        for ln in g.get("lines") or []:
            line((ln[0], ln[1]), (ln[2], ln[3]), "SYMBOL")
        if g.get("ellipse"):
            ex0, ey0, ex1, ey1 = g["ellipse"]
            msp.add_ellipse(P((ex0 + ex1) / 2, (ey0 + ey1) / 2), major_axis=((ex1 - ex0) / 2, 0), ratio=(ey1 - ey0) / (ex1 - ex0), dxfattribs={"layer": "SYMBOL"})
        if g["circle"]:
            cx, cy, r = g["circle"]
            msp.add_circle(P(cx, cy), r, dxfattribs={"layer": "SYMBOL"})
            if g.get("pointer"):
                msp.add_solid([P(*p) for p in g["pointer"]], dxfattribs={"layer": "SYMBOL"})
        elif g["cells"]:
            for c in g["cells"]:
                rect(c)
        elif g["box"]:
            rect(g["box"])
        if g["bar"]:
            line((g["bar"][0], g["bar"][1]), (g["bar"][2], g["bar"][3]), "SYMBOL")
        for cx, cy, t, fs, *anc in g["texts"]:
            a = anc[0] if anc else "middle"
            text(cx, cy, t, fs * 0.75, "TEXT", "MLEFT" if a == "start" else "RIGHT" if a == "end" else "CENTER")
    if doc.get("notes"):
        rect(NOTES_BOX, "TITLE")
        text(NOTES_BOX[0] + 4, NOTES_BOX[1] + 7, "NOTES", 4.5, "TITLE")
        for x, y, t in notes_layout(doc["notes"]):
            text(x, y, t, 3.5, "TITLE")
    for w in doc["wires"]:
        if w.get("label"):
            lx, ly = wire_label_pos(w)
            text(lx, ly, w["label"], 3.5, "TEXT", "CENTER")
    for w in export_wires(doc):
        pts = [P(*p) for p in w["pts"]]
        e = msp.add_lwpolyline(pts, dxfattribs={"layer": "DASHED" if w.get("dashed") else "WIRE"})
        if w.get("dashed"):
            e.dxf.linetype = "DASHED"
        tri = arrow_of(w)
        if tri:
            hp = msp.add_hatch(color=7, dxfattribs={"layer": "WIRE"})
            hp.paths.add_polyline_path([P(*q) for q in tri], is_closed=True)
        for mx, my, kind in w.get("marks") or []:
            msp.add_solid([P(*q) for q in mark_polygon(mx, my, kind)], dxfattribs={"layer": "WIRE"})
        for dx, dy in w.get("dots") or []:
            c = msp.add_circle(P(dx, dy), DOT_R, dxfattribs={"layer": "WIRE"})
            try:
                msp.add_hatch(color=7, dxfattribs={"layer": "WIRE"}).paths.add_edge_path().add_arc(P(dx, dy), DOT_R, 0, 360)
            except Exception:
                pass
    buf = io.StringIO()
    dwg.write(buf)
    return buf.getvalue().encode("utf-8")


# ─────────────────────────── 되읽기 (검증) ───────────────────────────

def verify(doc: dict) -> dict:
    """그린 것을 PDF 로 내보내 **분석기에 다시 넣어** 같은 블록 · 선 · 행이 나오는지 센다.
    분석기(analyse.analyse)를 그대로 부른다 — 사본 규칙 없음.  판정은 그 결과의 수를 세는 것뿐이다."""
    from . import analyse as AN
    doc = {**doc, **clean(doc)}
    pdf = to_pdf(doc)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "draw.pdf"
        p.write_bytes(pdf)
        try:
            res = AN.analyse(str(p))
        except AN.NotLogic as e:
            return {"ok": False, "why": str(e), "blocks": [], "rows": {"drawn": 0, "read": 0}, "nets": 0}
    return compare_sheet(doc, res["sheets"][0], res.get("seconds"))


def compare_sheet(doc: dict, s: dict, seconds=None) -> dict:
    """그린 장 하나 ↔ 분석기가 읽은 시트 하나 — 블록 종류 · 입출력 수 · 행 글 · 시트 이름을 센다."""
    res = {"seconds": seconds}
    drawn = [b for b in doc["blocks"] if not SYMBOLS[b["kind"]].get("note")]
    read = [{**v, "id": k} for k, v in s["blocks"].items()]
    used = set()
    items = []
    for b in drawn:
        g = block_geometry(b)
        box = g["box"] or [g["circle"][0] - g["circle"][2], g["circle"][1] - g["circle"][2],
                           g["circle"][0] + g["circle"][2], g["circle"][1] + g["circle"][2]]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        hit = None
        for i, rb in enumerate(read):
            if i in used:
                continue
            bb = rb["bbox"]
            if bb[0] - 2 <= cx <= bb[2] + 2 and bb[1] - 2 <= cy <= bb[3] + 2:
                hit = (i, rb)
                break
        want = SYMBOLS[b["kind"]]["logic"]
        if hit:
            used.add(hit[0])
            got = hit[1].get("logic") or ""
            if b["kind"] == "CONN":
                ok = hit[1].get("kind") == "CONNECTOR" or got == "connector"
            elif b["kind"] == "BOX":
                ok = (hit[1].get("read") or "").strip().upper() == (b.get("text") or "").strip().upper()   # 글자 상자는 그 글자가 읽혔는가
            elif b["kind"] == "MACRO":
                ok = got == "macro"
            else:
                ok = got == want
            ports = [p for p in s["ports"] if p["block"] == hit[1]["id"]]
            item = {"id": b["id"], "kind": b["kind"], "ok": ok, "read": hit[1].get("func", ""), "logic": got,
                    "inputs": sum(1 for p in ports if p["dir"] == "in"), "outputs": sum(1 for p in ports if p["dir"] == "out")}
            if b["kind"] == "MACRO":
                m = hit[1].get("macro") or {}
                want_typ = (b.get("param") or {}).get("typ") or ""
                item["macro"] = {"sheet": m.get("sheet", ""), "want": want_typ, "score": m.get("score"), "why": m.get("why", ""),
                                 "pins": sum(1 for q in (m.get("inputs") or []) + (m.get("outputs") or []) if q.get("row")),
                                 "pins_drawn": len((b.get("param") or {}).get("pins_in") or []) + len((b.get("param") or {}).get("pins_out") or [])}
                if want_typ and not want_typ.startswith("lib:") and m.get("sheet") != want_typ:
                    item["ok"] = False
                    item["why"] = f"Typical 시트가 {m.get('sheet') or '없음'} 으로 읽혔습니다 (그린 것: {want_typ})"
            items.append(item)
        else:
            items.append({"id": b["id"], "kind": b["kind"], "ok": False, "read": "", "logic": "", "inputs": 0, "outputs": 0,
                          "why": "분석기가 이 자리에서 블록을 읽지 못했습니다"})
    extra = [rb for i, rb in enumerate(read) if i not in used]
    tab = {(r["side"], r["n"]): r for r in s.get("table") or []}
    rows_ok, rows_bad = 0, []
    for side, key, col in (("left", "L", "fm"), ("right", "R", "to")):
        for k, v in doc[side].items():
            r = tab.get((key, int(k)))
            want = (v.get(col) or "").strip().upper()
            got = ((r or {}).get(col) or "").strip().upper()
            desc_ok = (v.get("desc") or "").strip().upper() == ((r or {}).get("desc") or "").strip().upper()
            if r is not None and want == got and desc_ok:
                rows_ok += 1
            else:
                rows_bad.append({"side": key, "n": int(k), "want": want, "read": got, "desc_ok": desc_ok})
    nrows_drawn = len(doc["left"]) + len(doc["right"])
    wired_rows = {(r["side"], r["n"]) for r in s.get("rows") or []}
    return {
        "ok": all(i["ok"] for i in items) and not rows_bad and not extra and s.get("sheet_no", "") == doc.get("sheet_no", ""),
        "sheet_no": {"drawn": doc.get("sheet_no", ""), "read": s.get("sheet_no", "")},
        "blocks": items, "extra_blocks": [{"id": e["id"], "func": e.get("func"), "bbox": e["bbox"]} for e in extra],
        "rows": {"drawn": nrows_drawn, "read": rows_ok, "bad": rows_bad, "wired": len(wired_rows)},
        "nets": len(s.get("nets") or {}), "dangling": len(s.get("dangling") or []),
        "findings": s.get("findings") or [], "seconds": res.get("seconds"), "page": s.get("page"),
    }


# ─────────────────────────── 분석 결과 → 그림 ───────────────────────────

_FUNC_KIND = {"AND": "AND", "OR": "OR", "NAND": "NAND", "NOR": "NOR", "NOT": "NOT", "GT": "GT", "DT": "DT", "PD": "PD",
              "VOTE": "VOTE", "MEMORY": "MEMORY", "PB": "PB", "PUSH BUTTON": "PB", "ANN": "ANN", "ALM": "ANN", "SOE": "SOE",
              "CONNECTOR": "CONN"}
_LOGIC_KIND = {"and": "AND", "or": "OR", "nand": "NAND", "nor": "NOR", "not": "NOT", "delay_on": "GT", "delay_off": "DT",
               "pulse": "PD", "vote": "VOTE", "memory": "MEMORY", "source": "PB", "sink": "ANN", "connector": "CONN"}


def _near_seg(px, py, sg, tol):
    x0, y0, x1, y1 = sg
    if abs(y0 - y1) < 0.2:            # 가로
        return abs(py - y0) <= tol and min(x0, x1) - tol <= px <= max(x0, x1) + tol
    if abs(x0 - x1) < 0.2:            # 세로
        return abs(px - x0) <= tol and min(y0, y1) - tol <= py <= max(y0, y1) + tol
    return abs(px - x0) + abs(py - y0) <= tol or abs(px - x1) + abs(py - y1) <= tol


def _mend(segs: list, terms: list, gap: float = 4.0, reach: float = 1.5 * PITCH) -> list:
    """그물 선분을 이어 붙인다.  ① 어느 선분에도 안 닿는 선분 끝 ↔ 4pt 안의 다른 끝은 직각 다리로 잇는다 (모서리 둥글림)
    ② 단자 · 행 자리가 어느 선분에도 안 닿으면 1.5 행 안의 가장 가까운 선분 끝으로 직각 다리 (표 가장자리 토막 · 반올림)."""
    segs = [list(sg) for sg in segs]

    def touched(px, py, skip=None):
        return any(_near_seg(px, py, sg, 0.8) for i, sg in enumerate(segs) if i != skip)

    def bridge(a, b):
        if abs(a[0] - b[0]) < 0.2 or abs(a[1] - b[1]) < 0.2:
            segs.append([a[0], a[1], b[0], b[1]])
        else:
            segs.append([a[0], a[1], b[0], a[1]])
            segs.append([b[0], a[1], b[0], b[1]])

    def set_end(i, k, pt):
        if k == 0:
            segs[i][0], segs[i][1] = pt
        else:
            segs[i][2], segs[i][3] = pt
    for i in range(len(segs)):
        for k in (0, 1):
            sg = segs[i]
            end = (sg[0], sg[1]) if k == 0 else (sg[2], sg[3])
            if touched(*end, skip=i) or any(abs(t[0] - end[0]) + abs(t[1] - end[1]) <= 1.0 for t in terms):
                continue
            best, bd = None, gap
            for j, og in enumerate(segs):
                if j == i:
                    continue
                for kk, oe in enumerate(((og[0], og[1]), (og[2], og[3]))):
                    d = abs(oe[0] - end[0]) + abs(oe[1] - end[1])
                    if d < bd:
                        best, bd = (j, kk, oe), d
            if not best:
                # L78 — 끝이 같은 그물의 직교 선분 몸통 앞 gap 안에서 멈췄으면 (원본은 그 틈을 연결점 ● 이 메웠다 —
                # 19VA QM02_G001 ANN 아래 1.56pt) 몸통까지 늘인다.  같은 그물 안에서만 — 다른 신호를 잇지 않는다.
                v_i = abs(sg[0] - sg[2]) < 0.2
                h_i = abs(sg[1] - sg[3]) < 0.2
                hit, hd = None, gap
                for j, og in enumerate(segs):
                    if j == i:
                        continue
                    if v_i and abs(og[1] - og[3]) < 0.2 and min(og[0], og[2]) - 0.2 <= end[0] <= max(og[0], og[2]) + 0.2:
                        d, pt = abs(og[1] - end[1]), (end[0], og[1])
                    elif h_i and abs(og[0] - og[2]) < 0.2 and min(og[1], og[3]) - 0.2 <= end[1] <= max(og[1], og[3]) + 0.2:
                        d, pt = abs(og[0] - end[0]), (og[0], end[1])
                    else:
                        continue
                    other = (sg[2], sg[3]) if k == 0 else (sg[0], sg[1])     # 늘이는 쪽이 바깥이어야 한다 (선분을 줄이지 않는다)
                    if d < hd and abs(pt[0] - other[0]) + abs(pt[1] - other[1]) > abs(end[0] - other[0]) + abs(end[1] - other[1]):
                        hit, hd = pt, d
                if hit:
                    set_end(i, k, hit)
                continue
            j, kk, oe = best
            og = segs[j]
            v_i, v_j = abs(sg[0] - sg[2]) < 0.2, abs(og[0] - og[2]) < 0.2
            # 작은 다리(1~2pt)는 분석기가 화살촉 획으로 버린다 — 끝을 **옮겨** 한 점(모서리)에서 만나게 한다
            if v_i != v_j:
                corner = (sg[0], og[1]) if v_i else (og[0], sg[1])
                set_end(i, k, corner)
                set_end(j, kk, corner)
            else:
                mid = ((end[0] + oe[0]) / 2, (end[1] + oe[1]) / 2)
                if v_i:
                    mid = (sg[0], mid[1]); set_end(i, k, mid); set_end(j, kk, (og[0], mid[1]))
                    if abs(sg[0] - og[0]) > 0.2:
                        segs.append([sg[0], mid[1], og[0], mid[1]])
                else:
                    mid = (mid[0], sg[1]); set_end(i, k, mid); set_end(j, kk, (mid[0], og[1]))
                    if abs(sg[1] - og[1]) > 0.2:
                        segs.append([mid[0], sg[1], mid[0], og[1]])
    for t in terms:
        if touched(*t):
            continue
        best, bd = None, reach
        for sg in segs:
            for oe in ((sg[0], sg[1]), (sg[2], sg[3])):
                d = abs(oe[0] - t[0]) + abs(oe[1] - t[1])
                if d < bd:
                    best, bd = oe, d
        if best:
            bridge(t, best)
    return [[round(v, 2) for v in sg] for sg in segs]


PIN_FS = 4.0          # L85 — 입력 이름 · 상수 글 크기 (분석 도면의 단자 이름 글씨 ≈ 4pt)


def _note_text(cx, cy, t, fs=PIN_FS) -> dict:
    """글(주석) 블록 하나 — 가운데 (cx, cy) · 글 폭만큼 (화면 · PDF 는 상자 없이 글만 그린다)."""
    w = round(max(4.0, len(t) * fs * _CHAR_W + 1.0), 2)
    h = round(fs / 0.8, 2)
    return {"id": "t" + uuid.uuid4().hex[:7], "kind": "TEXT", "x": round(cx - w / 2, 2), "y": round(cy - h / 2, 2), "w": w, "h": h,
            "text": t, "label": "", "param": {}}


def _fig_symbol(b) -> str:
    """분석이 상자 안 **그림**으로 알아본 연산(aop_fig · 글자 없음)의 기호 글 — 연산 사전의 가장 짧은 글자 (△ · ∫ · HL …)."""
    op = b.get("aop") or ((b.get("param") or {}).get("aop_fig") or {}).get("op")
    if not op:
        return ""
    from . import aops
    labels = [x for x in (aops.info(op).get("labels") or []) if x]
    return min(labels, key=len) if labels else ""


def _numtxt(v) -> str:
    """수를 글로 — 자릿수를 그대로 (99999999.9999 를 1e+08 로 줄이면 되읽을 때 1 이 된다)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f == int(f) and abs(f) < 1e15 else repr(f)


def _aop_texts(s: dict, doc: dict, X, Y):
    """L85 — 분석이 블록 둘레 글에서 읽은 **연산 입력 이름 · 상수 · 매개변수**를 그림에 같은 글로 옮긴다.
    분석 결과에는 읽은 값만 있고(param.pins · a_const · a_drawing) 그 글의 자리는 없어, 예전엔 들여오면 사라졌다 —
    TRANSFER 의 FLAG(어느 입력을 보낼지) · IN1/IN2 순서 · 상수 'A : 5%' 가 없어 작성 시뮬레이션이 검토 화면과 달랐다
    (19VA 차등 시뮬레이션: CO02_G705 등 4장 출력 행 138개).  입력 이름은 그 단자 바깥 · 선 위에, 상수 · 매개변수는 상자 위에 둔다 —
    작성 시뮬레이션(draw_sim)은 분석기와 같은 함수(aops.read_pins)로 이 글을 다시 읽는다 · PDF 로 내보내도 같은 글이다."""
    blocks = {b["id"]: b for b in doc["blocks"]}
    for bid, b in (s.get("blocks") or {}).items():
        p = b.get("param") or {}
        nb = blocks.get(bid)
        if nb is None or not (p.get("pins") or p.get("a_const") or p.get("a_drawing")):
            continue
        x0, y0, x1, y1 = nb["x"], nb["y"], nb["x"] + nb["w"], nb["y"] + nb["h"]
        const_txt = set()
        if isinstance(p.get("a_const"), dict):
            const_txt.add(f"{(p['a_const'].get('text') or '').split(':')[0].strip()} : {_numtxt(p['a_const'].get('v'))}")
        for net, info in (p.get("pins") or {}).items():
            name = str((info or {}).get("name") or "").strip()
            if not name:
                continue
            pt = next((q for q in s.get("ports") or [] if q["block"] == bid and str(q["net"]) == str(net)), None)
            if pt is None:
                continue
            px, py = X(pt["at"][0]), Y(pt["at"][1])
            side = pt.get("side") or ""
            t = name if (info.get("coef") is None or name in ("+", "-")) else f"{name} : {_numtxt(info['coef'])}"
            if t in const_txt:
                continue                                  # 상수 블록의 'A : 5%' 는 아래 상수 글 하나로
            tw = len(t) * PIN_FS * _CHAR_W
            if side == "L":
                cx, cy = min(px, x0) - tw / 2 - 1.0, py - 0.75 * PIN_FS
            elif side == "R":
                cx, cy = max(px, x1) + tw / 2 + 1.0, py - 0.75 * PIN_FS
            elif side == "T":
                cx, cy = px - tw / 2 - 1.0, min(py, y0) - 0.75 * PIN_FS
            else:
                cx, cy = px - tw / 2 - 1.0, max(py, y1) + 0.75 * PIN_FS
            doc["blocks"].append(_note_text(cx, cy, t))
        extra = []
        if isinstance(p.get("a_const"), dict) and p["a_const"].get("text"):
            extra.append(str(p["a_const"]["text"]))
        for k, e in (p.get("a_drawing") or {}).items():
            if isinstance(e, dict) and e.get("text") and str(e["text"]) not in extra:
                extra.append(str(e["text"]))
        for i, t in enumerate(extra[:4]):
            doc["blocks"].append(_note_text((x0 + x1) / 2, y0 - (i + 0.8) * PIN_FS * 1.3, _txt(t, 40)))


def from_sheet(s: dict, name: str, author: str, project: str = "") -> dict:
    """분석한 시트 하나를 이 양식의 그림으로 — 행 글은 그대로 · 블록은 종류와 자리 · 선은 그물의 선분.
    x 는 LOGIC 영역을 비례로, y 는 행 간격으로 옮긴다 (행 n 이 이 양식의 행 n 에 선다)."""
    rows = s.get("rows") or []
    table = s.get("table") or []
    nL = max([r["n"] for r in table if r.get("n") and r["side"] == "L"] + [r["n"] for r in rows if r.get("n") and r["side"] == "L"] + [0])
    nR0 = min([r["n"] for r in table if r.get("n") and r["side"] == "R"] + [r["n"] for r in rows if r.get("n") and r["side"] == "R"] + [10 ** 6])
    No = nL if nR0 == 10 ** 6 else min(nL, nR0 - 1) if nL else nR0 - 1     # 원래 한쪽 행 수 (오른쪽 첫 행 − 1)
    N = max(N_MIN, min(N_MAX, No or N_DEFAULT))
    doc = new_doc(name, author, project, N)
    doc["sheet_no"] = s.get("sheet_no") or ""
    doc["title"] = s.get("title") or ""
    doc["doc_no"] = _txt(s.get("doc_no"), 60)
    doc["project_name"] = _txt(s.get("project_name"), 80)
    doc["rev"] = _txt(s.get("rev"), 10)

    def rn(n):
        """원래 행 번호 → 이 그림의 행 번호 (오른쪽 행은 No 를 빼고 N 을 더한다 — 한쪽 행 수가 다를 때 자리가 밀리지 않게)."""
        return n if n <= No else n - No + N
    def _rev_mark(r):
        """개정 삼각형 안의 숫자(`2`)가 FM/TO 칸에 걸쳐 글로 읽힌 것 — 설명 · 태그 없이 한두 자리 수만 있는 칸은 신호가 아니다."""
        v = (r.get("fm") or r.get("to") or "").strip()
        return bool(v) and v.isdigit() and len(v) <= 2 and not (r.get("desc") or r.get("kks") or r.get("abv"))
    for r in table:
        n = r.get("n")
        if not n or _rev_mark(r):
            continue
        if r["side"] == "L" and 1 <= n <= N:
            doc["left"][str(n)] = {"fm": _txt(r.get("fm"), 60), "kks": _txt(r.get("kks") or r.get("abv"), 60), "desc": _txt(r.get("desc"), 60)}
        elif r["side"] == "R" and N < rn(n) <= 2 * N:
            doc["right"][str(rn(n))] = {"desc": _txt(r.get("desc"), 60), "kks": _txt(r.get("kks") or r.get("abv"), 60), "to": _txt(r.get("to"), 60)}
    lg = s.get("logic") or [LX0, TOP, LX1, TOP + N * PITCH]
    pitch = s.get("pitch") or PITCH
    # 행 1 의 가운데 y — 표(table)의 행 1 칸에서 (신호가 있는 행(rows)만 보면 행 1 이 비었을 때 엉뚱한 행이 기준이 되어 전체가 밀린다)
    t1 = next((r for r in table if r.get("side") == "L" and r.get("n") == 1 and r.get("y0") is not None), None)
    if t1 is not None:
        y1 = (t1["y0"] + t1["y1"]) / 2
    else:
        r1 = next((r for r in rows if r["side"] == "L" and r["n"] == 1), None)
        y1 = r1["at"][1] if r1 else (lg[1] + pitch / 2)
    sx = (LX1 - LX0) / max(1.0, lg[2] - lg[0])

    def X(x):
        return round(LX0 + (x - lg[0]) * sx, 2)

    def Y(y):
        return round(TOP + PITCH / 2 + (y - y1) / pitch * PITCH, 2)

    ports_by = {}
    for pt in s.get("ports") or []:
        ports_by.setdefault(pt["block"], []).append(pt)
    macro_boxes = [b["bbox"] for b in (s.get("blocks") or {}).values() if b.get("func") == "MACRO"]
    for bid, b in (s.get("blocks") or {}).items():
        func = b.get("func") or ""
        kind = _FUNC_KIND.get(func)
        if func != "MACRO" and any(mb[0] - 1 <= b["bbox"][0] and b["bbox"][2] <= mb[2] + 1 and mb[1] - 1 <= b["bbox"][1] and b["bbox"][3] <= mb[3] + 1 for mb in macro_boxes):
            continue                               # 매크로 상자 안에 붙여 그린 운전 버튼 칸 — 단자 이름으로 들어간다 (따로 그리면 상자가 틀이 된다)
        if func == "LIGHT" or (func in ("DISPLAY", "SIGNAL") and b.get("kind") == "CIRCLE" and len((b.get("read") or "").strip()) <= 2):
            kind = "LAMP"                          # 원 안 글자 하나(R · G …)의 표시등 — 분석이 DISPLAY 로 둔 것도 그림은 램프다
        if not kind and func in ("MACRO", "STEP", "SIGNAL", "DISPLAY", "UNKNOWN", "LIGHT", "TOGGLE", "TRANSFER", "CONST"):
            kind = "MACRO" if func == "MACRO" else "BOX"
        mon = func == "SIGNAL MONITOR"                    # L85 — 감시 블록(H/ · /L · B.Q) — 예전엔 logic=source 라 운전 버튼(PB)이 되고 설정값을 잃었다
        fig_op = "" if (b.get("read") or "").strip() else _fig_symbol(b)   # 상자 안 그림(△ · ∫ …)으로 읽은 연산 — 예전엔 글(주석)이 되어 사라졌다
        if not kind and (mon or fig_op):
            kind = "BOX"
        if not kind:
            kind = _LOGIC_KIND.get(b.get("logic") or "")
        if not kind:
            kind = "BOX" if (b.get("read") or "").strip() else "TEXT"
        x0, y0, x1, y1b = b["bbox"]
        nb = {"id": bid, "kind": kind, "x": X(x0), "y": Y(y0), "w": max(4, round((x1 - x0) * sx, 2)),
              "h": max(4, round((y1b - y0) / pitch * PITCH, 2)), "text": SYMBOLS[kind]["text"], "label": "", "param": {}}
        p = b.get("param") or {}
        if SYMBOLS[kind].get("bar"):
            ys = [pt["at"][1] for pt in ports_by.get(bid, []) if pt["dir"] == "in"]
            if ys:
                # 막대는 입력선이 닿는 자리를 **정확히** 덮고 상자보다 조금 길다 (더 늘이면 끝에서 닿던 선이 몸통에 닿아 교차가 된다)
                # 막대는 상자 가운데에 대칭으로 (분석기 _bar_gate: 막대 가운데가 상자 가운데에서 길이의 1/4 안) · 끝 입력선 너머 0.4 행
                cy_ = nb["h"] / 2
                ext = max(abs(Y(min(ys)) - nb["y"] - cy_), abs(Y(max(ys)) - nb["y"] - cy_)) + 0.4 * PITCH
                ext = max(ext, cy_ + 0.3 * PITCH)
                nb["param"]["bar"] = [round(cy_ - ext, 2), round(cy_ + ext, 2)]
        if kind == "LAMP":
            d_ = round((nb["w"] + nb["h"]) / 2, 2)
            cx, cy = nb["x"] + nb["w"] / 2, nb["y"] + nb["h"] / 2
            nb["x"], nb["y"], nb["w"], nb["h"] = round(cx - d_ / 2, 2), round(cy - d_ / 2, 2), d_, d_
            lab = (b.get("label") or "").strip()
            nb["text"] = lab[:2] if lab and lab.isalnum() else "G"
        if kind == "CONN":
            # 원은 둥글게 (x·y 배율이 달라도) · 꼭지 방향은 원래 꼭지가 중심의 어느 쪽인가
            d_ = round((nb["w"] + nb["h"]) / 2, 2)
            cx, cy = nb["x"] + nb["w"] / 2, nb["y"] + nb["h"] / 2
            nb["x"], nb["y"], nb["w"], nb["h"] = round(cx - d_ / 2, 2), round(cy - d_ / 2, 2), d_, d_
            pt_ = "R"
            ptr = b.get("pointer")
            if isinstance(ptr, (list, tuple)) and len(ptr) == 2:
                ddx, ddy = X(ptr[0]) - cx, Y(ptr[1]) - cy
                pt_ = ("R" if ddx > 0 else "L") if abs(ddx) >= abs(ddy) else ("B" if ddy > 0 else "T")
                nb["param"]["tipr"] = round(max(1.3, min(2.2, math.hypot(ddx, ddy) / max(0.1, d_ / 2))), 2)
            nb["param"]["point"] = pt_
            nb["text"] = _txt((b.get("label") or b.get("read") or "A").strip()[:2] or "A", 2)
        if kind in ("TEXT", "BOX"):
            nb["text"] = _txt(fig_op or b.get("read") or b.get("label") or func or "?", 40)
            if mon:
                prm = b.get("param") or {}
                if prm.get("sp_text") and not nb["param"].get("above"):
                    nb["param"]["above"] = _txt(prm["sp_text"], 40)     # 설정값 글 (`HH : 191` · `: 0`) — 작성 시뮬레이션이 분석기와 같은 함수로 읽는다
                from .analog import _MON
                if not _MON.match((nb["text"] or "").upper()):
                    nb["param"]["mon"] = 1                            # 범례가 정한 감시 블록 (B.Q …) — 글자만으로는 모른다
            lines = b.get("lines") or []
            if func == "STEP" and not lines:
                # STEP 상자 — 결과에 글줄 자리가 없다.  단자 역할(roles)로 그 단자 높이에 이름을 적는다 (분석기 _step_roles 가 읽는 낱말)
                nb["text"] = _txt(b.get("label") or "STEP", 20)
                names = {"step_in": "STEP IN", "crit": "CRIT", "step_out": "STEP OUT", "c_step": "C-STEP CMD"}
                hh = max(3.0, min(5.0, nb["h"] / 8))
                ls = [[2.0, round(0.6 * PITCH, 2), nb["text"], 5.0]]
                for pt in ports_by.get(bid, []):
                    role = (b.get("roles") or {}).get(f"{pt['at'][0]},{pt['at'][1]}", "")
                    nm = names.get(role, "")
                    if not nm:
                        continue
                    if pt.get("side") == "R" or (pt["dir"] == "out" and pt.get("side") != "L"):
                        ls.append([round(nb["w"] - 2 - 0.52 * hh * len(nm), 2), round(Y(pt["at"][1]) - nb["y"], 2), nm, hh])
                    else:
                        ls.append([2.0, round(Y(pt["at"][1]) - nb["y"], 2), nm, hh])
                nb["param"]["lines"] = ls
            if kind == "BOX" and len(lines) >= 2:
                # 상자 안 글줄을 제자리에 (STEP · 연산 상자 · 이름 붙은 신호 상자) — 글줄 높이의 0.8 배 크기
                ls = []
                for ly0, ly1, lx0, lx1, t in lines[:24]:
                    if not str(t).strip("-_ "):
                        continue
                    fs = max(2.5, min(7.0, (ly1 - ly0) / pitch * PITCH * 0.8))
                    ls.append([round(X(lx0) - nb["x"], 2), round(Y((ly0 + ly1) / 2) - nb["y"], 2), _txt(t, 60), round(fs, 2)])
                if ls:
                    nb["param"]["lines"] = ls
        if kind == "MACRO":
            m = b.get("macro") or {}
            pins_in, pins_out = [], []
            byat = {}
            for item in (m.get("inputs") or []) + (m.get("outputs") or []):
                byat[item.get("at")] = item
            for pt in sorted(ports_by.get(bid, []), key=lambda q: q["at"][1]):
                key = f"{pt['at'][0]},{pt['at'][1]}"
                item = byat.get(key) or {}
                name = _txt(item.get("pin") or pt.get("pin") or "", 40)
                q = {"name": name or f"P{len(pins_in) + len(pins_out) + 1}", "row": item.get("row"), "dy": round(Y(pt["at"][1]) - Y(y0), 2)}
                (pins_in if pt["dir"] == "in" else pins_out).append(q)
            # 상자 안 글줄 — 첫 단자 위 줄은 원본 이름(`FG COMPR SYS` · `GRP`), 단자 높이의 줄은 **선이 안 닿은 단자**(A_MODE · S_AUTO)
            # 같은 높이의 낱말은 한 줄 (분석은 낱말마다 한 항목) · 개정 삼각형의 `2` 는 뺀다
            rows_ = {}
            for ly0, ly1, lx0, lx1, t in (b.get("lines") or []):
                t = str(t).strip()
                if not t or t.isdigit():
                    continue
                rows_.setdefault(round((ly0 + ly1) / 2, 1), []).append((lx0, lx1, t))
            named = {q["name"] for q in pins_in + pins_out}
            pin_like = [ym for ym, ws in rows_.items() if any("_" in t or t in named for _, _, t in ws)]
            first_pin_y = min(pin_like + [pt["at"][1] for pt in ports_by.get(bid, [])] + [y1b])
            head, extra = [], []
            cxm = (x0 + x1) / 2
            for ym in sorted(rows_):
                ws = sorted(rows_[ym])
                if ym < first_pin_y - pitch * 0.6:
                    head.append(" ".join(t for _, _, t in ws))
                    continue
                for lx0, lx1, t in ws:
                    if t not in named and " " not in t:
                        extra.append((ym, t, (lx0 + lx1) / 2 < cxm))
            title_src = " | ".join(head[:3]) if head else (b.get("caption") or "")
            for ymid, t, left in extra:
                q = {"name": _txt(t, 40), "row": None, "dy": round(Y(ymid) - Y(y0), 2)}
                (pins_in if left else pins_out).append(q)
            pins_in.sort(key=lambda q: q["dy"]); pins_out.sort(key=lambda q: q["dy"])
            nb["param"] = {"typ": _txt(m.get("sheet"), 40), "title": _txt(title_src or m.get("title") or "", 120),
                           "pins_in": pins_in, "pins_out": pins_out}
        if kind in ("GT", "DT", "PD"):
            nb["param"]["t"] = _num(p.get("t_user", p.get("t")), 0, 36000, 5)
        if kind == "VOTE":
            nb["param"] = {"a": int(_num(p.get("a"), 1, 9, 2)), "b": int(_num(p.get("b"), 1, 9, 3))}
            nb["text"] = f"{nb['param']['a']}/{nb['param']['b']}"
        if kind == "MEMORY":
            nb["param"]["dominant"] = p.get("dominant") or ""
        if kind == "PB":
            nb["label"] = _txt((b.get("label") or "").replace("PB", "", 1).strip(" |"), 60)
        doc["blocks"].append(nb)
    _aop_texts(s, doc, X, Y)
    marks_todo = [(X((m[0] + m[2]) / 2), Y((m[1] + m[3]) / 2), m[4]) for m in (s.get("markers") or []) if len(m) == 5 and m[4] in MARK_KINDS]
    # 선 — 그물의 선분 + 교차 홉(jumps · 끊어 그린 교차의 틈을 잇는 짧은 토막) · 같은 그물 안의 T 접합에는 연결점
    port_pts = [(pt[0], pt[1]) for b in doc["blocks"] for pt in ports_of(b)]

    def snap(px, py):
        """선 끝이 단자 · 행 자리에서 2.5pt 안이면 그 자리로 — 배율 반올림 · 원 반지름 차이로 벌어진 틈을 메운다."""
        best, bd = None, 2.5
        for qx, qy in port_pts:
            d = abs(qx - px) + abs(qy - py)
            if d < bd:
                best, bd = (qx, qy), d
        if best:
            return [round(best[0], 2), round(best[1], 2)]
        if abs(px - LX0) < 2.5:
            return [LX0, round(py, 2)]
        if abs(px - LX1) < 2.5:
            return [LX1, round(py, 2)]
        return [round(px, 2), round(py, 2)]
    row_term = {}
    for r in s.get("rows") or []:
        if r.get("net") is not None and r.get("n"):
            nn = rn(r["n"])
            row_term.setdefault(str(r["net"]), []).append((LX0 if r["side"] == "L" else LX1, ry(nn, N)))
    port_term = {}
    bar_by = {b["id"]: bar_of(b) for b in doc["blocks"] if SYMBOLS[b["kind"]].get("bar")}
    for b in doc["blocks"]:
        for pt in ports_of(b):
            port_term.setdefault(b["id"], []).append((pt[0], pt[1]))
    net_ports = {}
    for pt in s.get("ports") or []:
        net_ports.setdefault(str(pt["net"]), []).append(pt)
    for nid, n in (s.get("nets") or {}).items():
        segs = [[X(a), Y(b_), X(c), Y(d_)] for a, b_, c, d_ in (n.get("segs") or []) + (n.get("jumps") or [])]
        segs = [sg for sg in segs if abs(sg[0] - sg[2]) + abs(sg[1] - sg[3]) > 0.2]
        # 그물의 끝(단자 · 행 자리)이 어느 선분에도 닿지 않으면 잇는다 — CAD 의 모서리 둥글림(필릿)과 표 가장자리 토막은 선분 기록에 없다
        terms = list(row_term.get(nid, []))
        for pt in net_ports.get(nid, []):
            cands = port_term.get(pt["block"], [])
            tx, ty = X(pt["at"][0]), Y(pt["at"][1])
            bb_ = bar_by.get(pt["block"])
            if bb_ and pt["dir"] == "in" and bb_[1] - 0.5 <= ty <= bb_[3] + 0.5:
                # 막대 게이트의 입력은 **그 높이에서 막대에 닿는다** — 자석 자리(행 간격으로 고른 점)로 옮기면 반 행 다리가 막대 위에
                # 겹쳐 그려지고, 분석기가 그 겹선을 선으로 읽어 막대가 그물이 된다 (1A5J FG_G-101 입력 29개 AND 가 신호원으로 읽혔다)
                tx, ty = bb_[0], ty
            elif cands:
                tx, ty = min(cands, key=lambda q: abs(q[0] - tx) + abs(q[1] - ty))
            terms.append((tx, ty))
        segs = _mend(segs, terms)
        dots = []
        for i_, sg in enumerate(segs):
            for end in ((sg[0], sg[1]), (sg[2], sg[3])):
                for j_, og in enumerate(segs):
                    if i_ == j_:
                        continue
                    hx = abs(og[1] - og[3]) < 0.2           # og 가로
                    if hx and abs(end[1] - og[1]) < 0.6 and min(og[0], og[2]) + 0.8 < end[0] < max(og[0], og[2]) - 0.8:
                        dots.append([round(end[0], 2), round(og[1], 2)])
                    elif not hx and abs(og[0] - og[2]) < 0.2 and abs(end[0] - og[0]) < 0.6 and min(og[1], og[3]) + 0.8 < end[1] < max(og[1], og[3]) - 0.8:
                        dots.append([round(og[0], 2), round(end[1], 2)])
        # 끝점이 다른 선분 둘 이상(몸통이든 끝이든)에 닿으면 접합 (T · + — 분석기가 접합에서 선분을 끊어 두었고, 반올림으로
        # 가로 행 선의 끝이 세로 모선의 조각 경계에서 1pt 안팎 비켜 선다 · 1A5J FG_G-102 출력 모선).  모서리(하나에만 닿음)는 아니다
        for i_, sg in enumerate(segs):
            for end in ((sg[0], sg[1]), (sg[2], sg[3])):
                near = 0
                for j_, og in enumerate(segs):
                    if i_ == j_:
                        continue
                    if _near_seg(end[0], end[1], og, 1.2):
                        near += 1
                if near >= 2:
                    dots.append([round(end[0], 2), round(end[1], 2)])
        seen = set()
        dots = [d_ for d_ in dots if not (tuple(d_) in seen or seen.add(tuple(d_)))]
        # 파선은 짧은 토막 여럿이다 — 교차 틈(홉)으로 끊긴 실선을 분석이 파선으로 적어 둔 것(1A5J FG_G-201 · 원본 PDF 에 파선 0)은 실선으로
        raw_ = [sg for sg in (n.get("segs") or []) if abs(sg[0] - sg[2]) + abs(sg[1] - sg[3]) > 0.2]
        lens_ = sorted(abs(sg[0] - sg[2]) + abs(sg[1] - sg[3]) for sg in raw_)
        really_dashed = bool(n.get("dashed")) and len(lens_) >= 4 and lens_[len(lens_) // 2] < 1.2 * pitch and lens_[-1] < 3.0 * pitch
        arrow_at = [(X(pt["at"][0]), Y(pt["at"][1])) for pt in net_ports.get(nid, [])
                    if pt["dir"] == "in" and pt.get("side") in ("T", "B", "R")]
        for k_, sg in enumerate(segs):
            w = {"id": f"n{nid}_{k_}", "pts": [snap(sg[0], sg[1]), snap(sg[2], sg[3])], "dashed": really_dashed}
            if k_ == 0 and dots:
                w["dots"] = dots
            for ax_, ay_ in arrow_at:
                if abs(w["pts"][0][0] - ax_) + abs(w["pts"][0][1] - ay_) <= 2.6:
                    w["arrow"] = "start"
                elif abs(w["pts"][1][0] - ax_) + abs(w["pts"][1][1] - ay_) <= 2.6:
                    w["arrow"] = "end"
            doc["wires"].append(w)
    # 인터페이스 표시 ◆ ■ — 그 점을 지나는(또는 가장 가까운) 선에 단다
    for mx, my, kind in marks_todo:
        best, bd = None, 2.0 * PITCH
        for w in doc["wires"]:
            sg = [w["pts"][0][0], w["pts"][0][1], w["pts"][1][0], w["pts"][1][1]]
            if _near_seg(mx, my, sg, 1.0):
                best, bd = w, 0
                break
            for tol_ in (0.5 * PITCH, PITCH, 2.0 * PITCH):          # 선의 몸통에서 가까운 순 (끝점 거리가 아니라 수직 거리)
                if tol_ < bd and _near_seg(mx, my, sg, tol_):
                    best, bd = w, tol_
                    break
        if best is not None:
            best.setdefault("marks", []).append([round(mx, 2), round(my, 2), kind])
    # L81 — 분석기가 그 장 NOTE 로 토글이라 읽은 글자 상자(SRST …)는 그 NOTE 문장을 장 노트에 옮긴다.
    #   안 옮기면 다시 그린 장에서 '판정 못 한 블록' 이 되어 시뮬레이션이 그 매크로마다 수십 번 되풀이된다 (19VA 0009).
    notes = list(doc.get("notes") or [])
    for b in (s.get("blocks") or {}).values():
        if b.get("logic") == "toggle":
            w = re.sub(r"[^0-9A-Z_]", "", str(b.get("label") or b.get("read") or "").upper())
            if w and not any(f'"{w}"' in n.upper() for n in notes):
                notes.append(f'OUTPUT STATE IS INVERTED BY EACH MOMENTARY TRUE SIGNAL ON "{w}"')
    if notes:
        doc["notes"] = notes[:20]
    doc.update(clean(doc))
    try:                                             # L84 — 토막을 연결 그대로 적은 선으로 (작도 화면을 가볍게)
        from . import draw_compact
        draw_compact.compact_doc(doc)
    except Exception:
        pass
    return doc
