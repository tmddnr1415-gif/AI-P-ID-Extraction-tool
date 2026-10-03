import json, sys
from collections import Counter

def facts(path, name):
    r=json.load(open(path)); tb=r["titleblocks"]; rows=r["rows"]; n=len(tb)
    pid=[t for t in tb if t["page_kind"]=="PID"]
    f={}
    f["장"]=n
    f["도면번호 읽음"]="%d / %d" % (sum(1 for t in tb if t["drawing_no"]), n)
    f["제목 읽음"]="%d / %d" % (sum(1 for t in tb if t.get("drawing_title")), n)
    f["프로젝트명 읽음"]="%d / %d" % (sum(1 for t in tb if t.get("project_name")), n)
    f["PID 판정"]=len(pid)
    f["타이틀블록 FAIL"]=sum(1 for t in tb if t.get("status")=="FAIL")
    rv=Counter(t.get("rev") for t in tb)
    f["REV 읽음"]="%d / %d" % (sum(v for k,v in rv.items() if k not in ("?","",None)), n)
    f["REV 신뢰도 HIGH"]=sum(1 for t in tb if t.get("rev_confidence")=="HIGH")
    f["rev_date 있음"]=sum(1 for t in tb if t.get("rev_date"))
    f["행"]=len(rows)
    tabs=Counter(x.get("tab") for x in rows)
    f["탭"]=" · ".join("%s %d" % kv for kv in sorted(tabs.items()))
    f["Q'ty 못 셈"]="%d / %d" % (sum(1 for x in rows if x.get("qty") is None), len(rows))
    f["승수표 출처"]=(r.get("multipliers") or {}).get("source")
    f["승수 코드 수"]=len((r.get("multipliers") or {}).get("table") or {})
    f["검토 필요 행"]="%d / %d" % (sum(1 for x in rows if x.get("needs_review")), len(rows))
    f["미판정 심볼"]=len(r.get("unjudged_symbols") or [])
    leg=r.get("legend") or {}
    f["범례 항목"]=len(leg)
    f["범례 LEGEND 출처"]=sum(1 for v in leg.values() if isinstance(v,dict) and v.get("source")=="LEGEND")
    g=r.get("description_grades") or {}
    f["Description 등급"]=json.dumps(g, ensure_ascii=False)[:80] if g else "-"
    return name, f

a=facts("out/round20/run_base.json","AL NOUF1 (A1·58장)")
b=facts("out/tc2/head.json","TC2 (A3·60장)")
keys=list(a[1].keys())
w=max(len(k) for k in keys)
print("%-*s | %-34s | %s" % (w,"항목",a[0],b[0]))
print("-"*(w+3+36+3+30))
for k in keys:
    print("%-*s | %-34s | %s" % (w,k,a[1][k],b[1][k]))
