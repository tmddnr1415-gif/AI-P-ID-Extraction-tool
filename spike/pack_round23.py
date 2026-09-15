"""23회차 산출 꾸러미 — `out/round23_result.zip`.

이름은 전부 ASCII 이고 txt·md 는 BOM 을 단다 (알집이 CP949 로 읽어 깨지는 것을 막는다).
"""
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "round23_result.zip"

FILES = [
    ("1_report.md",         "out/round23_report.md"),
    ("2_progress.md",       "out/round23_progress.md"),
    ("3_constants.md",      "out/round23_constants.md"),
    ("4_score.md",          "out/round23_score.md"),
    ("5_gap.md",            "out/round23_gap.md"),
    ("6_roadmap.md",        "out/round23_roadmap.md"),
    ("7_regression_3p.json", "out/regression_3p.json"),
    ("8_baselines_3p.json", "spike/baselines_3p.json"),
    ("9_tc2_assessment.md", "docs/tc2_assessment.md"),
]

BOM = b"\xef\xbb\xbf"


def main() -> int:
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name, rel in FILES:
            p = ROOT / rel
            if not p.exists():
                print("없음:", rel)
                continue
            data = p.read_bytes()
            if name.endswith((".md", ".txt")) and not data.startswith(BOM):
                data = BOM + data
            z.writestr(name, data)
    blob = OUT.read_bytes()
    print("%s  %d 바이트  sha256 %s" % (OUT.name, len(blob), hashlib.sha256(blob).hexdigest()))
    with zipfile.ZipFile(OUT) as z:
        for i in z.infolist():
            ok = all(ord(c) < 128 for c in i.filename)
            print("  %s %-24s %7d" % ("OK " if ok else "NG ", i.filename, i.file_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
