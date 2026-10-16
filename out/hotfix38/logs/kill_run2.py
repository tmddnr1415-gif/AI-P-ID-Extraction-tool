import os, signal, time
me = os.getpid(); pp = os.getppid()
victims = []
for pid in os.listdir("/proc"):
    if not pid.isdigit() or int(pid) in (me, pp): continue
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="ignore")
    except Exception:
        continue
    if ("run2.sh" in cmd or "rev_flow_qfe.py" in cmd or "regression_3p.py" in cmd or "chain.sh" in cmd
            or ("uvicorn" in cmd and "app.main" in cmd)):
        victims.append((int(pid), cmd[:80]))
for pid, cmd in victims:
    try: os.kill(pid, signal.SIGTERM)
    except Exception as e: print("fail", pid, e)
    print("killed", pid, cmd)
time.sleep(2)
for pid, _ in victims:
    try: os.kill(pid, signal.SIGKILL)
    except Exception: pass
