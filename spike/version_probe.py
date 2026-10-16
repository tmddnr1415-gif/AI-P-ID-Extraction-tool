"""Upload a PDF, then GET /version every 0.5s (timeout 3s) and log latency + stage."""
import json, sys, time, urllib.request, http.client
base = sys.argv[1]; pdf = sys.argv[2]; out = sys.argv[3]; dur = float(sys.argv[4])
import uuid
b = uuid.uuid4().hex
body = (f"--{b}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"t.pdf\"\r\nContent-Type: application/pdf\r\n\r\n").encode() + open(pdf,'rb').read() + f"\r\n--{b}--\r\n".encode()
req = urllib.request.Request(base + "/jobs", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
job = json.load(urllib.request.urlopen(req, timeout=60))["job_id"]
t0 = time.time(); f = open(out, "w")
while time.time() - t0 < dur:
    s = time.time(); ok = "ok"
    try: urllib.request.urlopen(base + "/version", timeout=3).read()
    except Exception as e: ok = type(e).__name__
    lat = time.time() - s
    try: st = json.load(urllib.request.urlopen(base + f"/jobs/{job}", timeout=30))
    except Exception as e: st = {"message": "?"+type(e).__name__}
    f.write(f"{time.time()-t0:7.1f} {lat:6.2f} {ok} {st.get('status')} {st.get('message')}\n"); f.flush()
    if st.get("status") in ("done", "failed"): break
    time.sleep(0.5)
