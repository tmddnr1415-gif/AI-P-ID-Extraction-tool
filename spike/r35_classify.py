"""35회차 [E]/[F] — 상수 하나하나에 판정을 붙이고(㉠~㉤) 다섯 목록과 ㉮㉯㉰ 로 가른다.

    python3 spike/r35_classify.py      # → out/round35_classified.md · out/round35_remaining.md · out/round35_human_vs_rule.md

입력은 전부 이미 있는 기록이다 — 새로 돌리지 않는다:
  out/round35_strip_list.md            지운 목록 199 (+project.code)
  out/round35/replay_late_pass1.json   1차 되살린 3
  out/round35/replay_pass2_final.json  2차 되살린 20 (+ 다음 차례 1)
  out/round35/pass2_prerestored.json   2차에서 덩이로 미리 되살린 D 표 91
  out/round35/groups.json              묶음 토글 11
  out/round35/moved.json               `_fit_layout` 이 얹는 키 (spike/r35_moved.py)
  out/round35/full58.json              전량 58장 확인 실행 (있으면)
"""
from __future__ import annotations
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
O = ROOT / "out/round35"
lst = (ROOT / "out/round35_strip_list.md").read_text()
MOD = {"app/engine/detect_symbols.py": "ds", "app/engine/detect_valves.py": "dv", "app/engine/extract_titleblocks.py": "tb"}
dc = [(f"{MOD[f]}.{field}", val, grade, f"{f}:{ln}") for f, ln, field, val, grade in
      re.findall(r"^\| `([^:`]+):(\d+)` \| `([a-z_]+)` \| `(.+?)` \| (\S+) \|", lst, re.M)]
cfg = [("cfg." + k, val, grade.split("(")[0], "config/project_alnouf1.yaml") for k, val, grade in
       re.findall(r"^\| `([a-zA-Z_][^`]*)` \| `(.*?)` \| ([^|]+?) \|$", lst, re.M) if not k.startswith("app/")]
seen = set(); ALL = []
for row in dc + cfg:
    if row[0] in seen: continue
    seen.add(row[0]); ALL.append(row)
assert len(ALL) == 199, len(ALL)
ALL.append(("cfg.project.code", '"ALNOUF1"', "E→지움", "config/project_alnouf1.yaml"))

def load(p, default):
    p = O / p
    return json.loads(p.read_text()) if p.exists() else default
p1 = load("replay_late_pass1.json", {"restored": [], "runs": []})
p2 = load("replay_pass2_final.json", {"restored": [], "runs": []})
pre = load("pass2_prerestored.json", [])
groups = load("groups.json", {})
moved = load("moved.json", {}).get("moved", [])
mv = load("moved.json", {}).get("values", {})
full = load("full58.json", None)
full1 = load("full58_try1.json", None)
overlay = load("overlay.json", None)
mv58 = load("moved58.json", {}).get("values", {})          # 58장에서 실제로 옮긴 값 (10장보다 이것이 기준)
iv58 = load("moved58.json", {}).get("item_values", {})     # 58장 유도 항목 전부 (옮기지 않은 것 포함)
chain = [r["missing"] for r in p1["runs"] if not r.get("ok") and r.get("missing")]   # 1차 멈춘 순서
chain2 = [r["missing"] for r in p2["runs"] if not r.get("ok") and r.get("missing")]
restored_seq = chain[:3] + chain2[:20]                     # 실제로 되살린 23
next_up = chain2[20] if len(chain2) > 20 else None
moved_keys = {"cfg." + k for k in moved}
D_BLOCK = [n for n in pre if n not in restored_seq]
grade_of = {n: g for n, _, g, _ in ALL}

# 코드 기본값이 config 값과 같은 잎 — 지워도 코드가 같은 값을 쓴다 (sentinel 은 `if got` 에서 터진다)
CODE_DEFAULT_SAME = {"cfg.qty_note.same_words", "cfg.qty_note.unit_words", "cfg.qty_note.range_words"}
# 범례가 답하는 폴백 — AL NOUF1 은 범례 p2·p3·p5 가 전부 답하므로 이 값은 읽히지 않는다 (지문 불변 실측)
LEGEND_FALLBACK = {n for n, *_ in ALL if n.startswith("cfg.valves.legend_fallback.") or n.startswith("cfg.unit_multiplier_fallback.")}
# dataclass 기본값을 config 잎이 덮는 것 — `_layout_from_config` 실측 (기본값은 config 가 없을 때만 산다)
CONFIG_FED = {"ds.mark_blob": "vendor_marks.blob_span", "ds.mark_glyph_span": "vendor_marks.glyph_span", "ds.mark_cluster_gap": "vendor_marks.cluster_gap",
              "ds.mark_above": "vendor_marks.above", "ds.note_mark_row_tol": "vendor_marks.note_row_tol", "ds.note_line_gap": "vendor_marks.note_line_gap",
              "ds.box_mark_margin": "vendor_marks.package_box.mark_margin", "ds.scope_text_tol": "sct_scope.text_tol", "ds.drop_x_tol": "sct_scope.drop_x_tol",
              "ds.drop_end_tol": "sct_scope.drop_end_tol", "ds.brk_max_mark": "broken_line.brk_max_mark"}
METHOD_LIMIT = {n for n, *_ in ALL if n.startswith("cfg.anchors.")}   # import 시점 사전 — 유도 뒤 지우기가 닿지 않는다

judg = {}   # name -> (판정, 근거)
for name, *_ in ALL:
    if name == "cfg.project.code":
        judg[name] = ("—", "프로필 열쇠. 표식 문자열로 바꿔 낯선 프로필 경로를 강제했다 (판정 대상 아님)"); continue
    if name in moved_keys:
        wn = mv.get(name[4:]); judg[name] = ("㉡", f"`_fit_layout` 이 얹는다 (`{wn[0] if wn else '?'}` → `{wn[1] if wn else '?'}`) — strip 훅이 건너뛰어 **지운 적이 없다**. 유도가 이미 덮는 값인데 목록은 A/B 로 적었다. 탐침 지문은 같고, 58장은 §0-1"); continue
    if name in restored_seq:
        judg[name] = ("㉣", f"재현 루프 멈춤 #{restored_seq.index(name)+1} — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행"); continue
    if name == next_up:
        judg[name] = ("㉣", "상한 20 에서 멈춘 뒤 다음 차례(24번째) — 되살리지 못했다"); continue
    if name in CODE_DEFAULT_SAME:
        judg[name] = ("㉠", "config 값 = 코드 기본값 (`projectconfig._DEFAULT_*`). 묶음 토글은 sentinel 의 `if got` 에서 멈췄지만 **키를 실제로 빼면** 코드가 같은 낱말을 쓴다 — 코드 대조로 판정"); continue
    if name in D_BLOCK:
        judg[name] = ("㉣-D", "런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처"); continue
    judg[name] = None
# 묶음 토글
for gname, g in groups.items():
    for m in g["members"]:
        if judg.get(m) is not None: continue
        if m in METHOD_LIMIT:
            judg[m] = ("시험불가", f"묶음 `{gname}` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다**"); continue
        if g.get("ok"):
            same = g.get("fingerprint") == "0087c236" and g.get("rows") == 199
            if m in LEGEND_FALLBACK:
                judg[m] = ("㉡" if same else "㉢", f"묶음 `{gname}` 지워도 {g['rows']}/`{g['fingerprint']}` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다")
            elif m in CONFIG_FED:
                judg[m] = ("㉠" if same else "㉢", f"묶음 `{gname}` 지워도 {g['rows']}/`{g['fingerprint']}` — dataclass 기본값을 **config 잎(`{CONFIG_FED[m]}`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다)")
            else:
                judg[m] = ("㉠" if same else "㉢", f"묶음 `{gname}` 지워도 {g['rows']}/`{g['fingerprint']}` — 탐침 10장 경로에서 읽히지 않는다")
        else:
            if m == g.get("missing"):
                judg[m] = ("㉣", f"묶음 `{gname}` 이 이 상수에서 멈춤 — 유도 없음")
            else:
                judg[m] = ("미실측", f"묶음 `{gname}` 이 `{g.get('missing')}` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함)")
for name, *_ in ALL:
    if judg.get(name) is None:
        judg[name] = ("미실측", "어느 묶음에도 들지 않았고 되살리기 사슬에도 닿지 않았다")

order = ["㉠", "㉡", "㉢", "㉣", "㉣-D", "㉤", "시험불가", "미실측", "—"]
cnt = {k: sum(1 for n, *_ in ALL if judg[n][0] == k) for k in order}
lines = ["# [E] 차이 분류 — 상수 하나하나 (35회차)", "",
         "판정: ㉠ 영향 없음 · ㉡ 유도가 대신하고 지문 같음 · ㉢ 유도가 대신하고 지문 다름 · ㉣ 유도 없음 → 멈춤 · ㉤ None 이 조용히 흘러 틀린 값 ·",
         "**시험불가**(이 방법이 닿지 않는 자리) · **미실측**(상한 안에 개별로 못 잼).  뒤의 둘은 프롬프트의 다섯 판정 밖이고 **숨기지 않고 따로 센다**.", "",
         "탐침(p1~p10) 기준 199행 · `0087c236` · Q'ty 398.  `_fit_layout` 이 얹는 키(㉡ 근거): " + (", ".join(f"`{k}`" for k in moved) if moved else "**(moved.json 없음)**"), "",
         "## 0. 개수", "", "| 판정 | 개수 |", "|---|---:|"] + [f"| {k} | {cnt[k]} |" for k in order] + [f"| 합 | {sum(cnt.values())} (199 + project.code) |", ""]
if full:
    lines += ["## 0-1. 전량 58장 확인 실행 (worktree · 낯선 프로필 경로)", "",
              "| 실행 | 지운 상수 | 결과 | 본선 |", "|---|---:|---|---|",
              f"| ㉠/㉡ 묶음만 지움 (유도가 답한 키는 안 지움) | {len(full.get('stripped', []))} | {json.dumps({k: full.get(k) for k in ('ok','rows','fingerprint','qty','missing')}, ensure_ascii=False)} · {full.get('seconds')}초 | `fb85b039` · 1037 · 1931 |"]
    if full1:
        lines += [f"| (첫 시도 — 유도값=설정값이면 지우던 훅) | {len(full1.get('stripped', []))} | {json.dumps({k: full1.get(k) for k in ('ok','rows','fingerprint','qty','missing')}, ensure_ascii=False)} · {full1.get('seconds')}초 | 방법 결함 (D-0 4) |"]
    if overlay:
        lines += [f"| 아무것도 안 지움 (유도 overlay 만) | 0 | {json.dumps({k: overlay.get(k) for k in ('ok','rows','fingerprint','qty','missing')}, ensure_ascii=False)} | `fb85b039` · 1037 · 1931 |"]
    lines += ["", "**두 실행 다 본선과 같다.**  즉 (가) 낯선 프로필 경로가 얹는 19칸(`moved58.json` — `regions.*`·`title_block.*` 15 · `formats.revision` `^[A-Z][0-9]?$→^[A-Z]$` · `sct_scope.box_from_both_edges None→True` 등)은 58장 지문을 한 칸도 안 옮기고, (나) ㉠/㉡ 61개를 지운 것도 안 옮긴다.  ⚠ 지문 밖 열(REV — `A1` 장 · Description)은 이 실행이 기록하지 않았다 → 조사 목록.", ""]
lines += ["## 1. 표", "", "| 상수 | 현재 값 | 등급(25회차) | 판정 | 근거 |", "|---|---|---|---|---|"]
for name, val, grade, where in ALL:
    j, why = judg[name]
    v = val if len(val) <= 40 else val[:37] + "…"
    lines.append(f"| `{name}` | `{v}` | {grade} | **{j}** | {why} |")
(ROOT / "out/round35_classified.md").write_text("\n".join(lines) + "\n")
json.dump({n: judg[n] for n, *_ in ALL}, open(O / "judgements.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(cnt, ensure_ascii=False))

# ---------------------------------------------------------------- [F] 다섯 목록 (합 = 200)
def five(name):
    j, _ = judg[name]; g = grade_of.get(name, "")
    if name == "cfg.project.code": return "삭제", "프로필 열쇠 — 지운 것은 실험 장치였다. 본선에서는 남긴다(E). 합계를 맞추려 여기 둔다"
    if j == "㉠": return "삭제", "지워도 지문 불변 · 코드 기본값과 같다"
    if j == "㉡" and name in LEGEND_FALLBACK: return "삭제", "범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단"
    if j == "㉡":
        k = name[4:]
        was_now = mv58.get(k) if k in mv58 else (["(58장 유도값 = 설정값)", iv58.get(k)] if k in iv58 else mv.get(k))
        if was_now and (str(was_now[0]) == str(was_now[1]) or str(was_now[0]).startswith("(58장")): return "삭제", f"58장 유도값 = 설정값 ({was_now[1]}) — 설정은 유도의 사본이다 (10장 탐침에서는 `{mv.get(name[4:], ['?'])[1] if name[4:] in mv else '같음'}` 로 달랐다 — 정의줄이 두 크기를 다 주는 장이 p10 뒤에 있다)"
        return "조사", f"유도값 ≠ 설정값 ({was_now[0] if was_now else '?'} → {was_now[1] if was_now else '?'}) — 지문은 같지만 지문 밖 열(REV·Description)을 58장에서 대조해야 한다"
    if j == "시험불가": return "결함", "`anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리)"
    if j == "미실측": return "조사", "개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분)"
    if j == "㉣-D" or (j == "㉣" and g == "D"): return "사람 지정", "도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조)"
    if j == "㉣": return "유도 구현", {"A": "찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다", "A/C": "정의줄이 획이면 A · 텍스트면 본문 실물", "B": "인쇄돼 있는데 안 찾는다 — 읽기 추가", "C": "본문 실물에서 잰다 (분포 · 비율)"}.get(g, g)
    return "조사", j
F = {n: five(n) for n, *_ in ALL}
FO = ["삭제", "조사", "유도 구현", "사람 지정", "결함"]
fc = {k: sum(1 for n in F if F[n][0] == k) for k in FO}
assert sum(fc.values()) == len(ALL)
def bucket(name):
    k = name[4:] if name.startswith("cfg.") else name
    if k.startswith(("description.", "anchors.", "valves.valve_type_actuator", "valves.cv_tags", "valves.xv_tags", "qty_note.")) or k in ("multi_signal_bundle.merged_type", "multi_signal_bundle.description_signal", "scope.vendor_description"):
        return "㉮"
    if k.startswith(("excel.", "valves.excel.", "valves.deliverables", "revision.", "client_form.", "supplier_interface_span.", "qty_scope_overrides", "scope.")) or k in ("multi_signal_bundle.merge_quantity", "scope_box_both_edges", "project.code"):
        return "㉰"
    return "㉯"
B = {n: bucket(n) for n, *_ in ALL}
rem = [n for n, *_ in ALL if F[n][0] != "삭제"]
bc = {b: sum(1 for n in rem if B[n] == b) for b in ("㉮", "㉯", "㉰")}
lines = ["# [F] 남은 일 목록 — 다섯으로 가른다 (35회차)", "",
         "이 회차의 산출물이다.  **어느 목록도 이 회차에 본선에 적용하지 않는다** — 다음 회차다.", "",
         "| 목록 | 개수 | 뜻 |", "|---|---:|---|",
         "| 삭제 | %d | 지워도 지문이 안 움직인다 — 설정이 코드·범례·유도의 사본이다 |" % fc["삭제"],
         "| 조사 | %d | 이 회차 방법으로 판정이 안 섰다 — 개별 실측 · 지문 밖 열 대조 |" % fc["조사"],
         "| 유도 구현 | %d | 유도가 없어 멈춘다 — 도면(범례·본문)에 근거가 있다 |" % fc["유도 구현"],
         "| 사람 지정 | %d | 도면에 없다 — 프로필·사람 지정 화면 |" % fc["사람 지정"],
         "| 결함 | %d | 코드 구조가 유도를 막는다 |" % fc["결함"],
         "| 합 | %d | = 지운 목록 199 + project.code |" % sum(fc.values()), ""]
for k in FO:
    lines += [f"## {k} ({fc[k]})", "", "| 상수 | 등급 | 판정 | 왜 이 목록인가 |", "|---|---|---|---|"]
    for n, *_ in ALL:
        if F[n][0] == k: lines.append(f"| `{n}` | {grade_of.get(n,'')} | {judg[n][0]} | {F[n][1]} |")
    lines.append("")
(ROOT / "out/round35_remaining.md").write_text("\n".join(lines) + "\n")
lines = ["# [F] 사람이 답할 것과 규칙이 답할 것 — ㉮㉯㉰ (35회차)", "",
         "대상은 **삭제 목록을 뺀 나머지 %d개**.  ㉮ 어휘·문형(발주처가 쓰는 낱말 — LLM 또는 규칙, **이 회차에 구현하지 않는다**) · ㉯ 범례·구조(기하 · 유도 구현 대상) · ㉰ 도면에 없음(양식 · 실무 판단 · 사람 지정)." % len(rem), "",
         "| 갈래 | 개수 | 어디서 답이 오나 |", "|---|---:|---|",
         "| ㉮ 어휘·문형 | %d | 발주처 리스트(557행)에서 센 값 · 프로젝트 프로필 · 다음 회차의 LLM/규칙 후보 |" % bc["㉮"],
         "| ㉯ 범례·구조 | %d | 그 도면의 범례·본문 실물 — 유도 구현 |" % bc["㉯"],
         "| ㉰ 도면에 없음 | %d | 발주처 양식 · 실무 판단 · 사람 지정 화면 |" % bc["㉰"],
         "| 합 | %d | |" % sum(bc.values()), ""]
for b in ("㉮", "㉯", "㉰"):
    lines += [f"## {b} ({bc[b]})", "", "| 상수 | 등급 | 목록 |", "|---|---|---|"]
    for n in rem:
        if B[n] == b: lines.append(f"| `{n}` | {grade_of.get(n,'')} | {F[n][0]} |")
    lines.append("")
(ROOT / "out/round35_human_vs_rule.md").write_text("\n".join(lines) + "\n")
json.dump({"five": fc, "buckets": bc, "F": F, "B": B}, open(O / "lists.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({"five": fc, "buckets": bc}, ensure_ascii=False))
