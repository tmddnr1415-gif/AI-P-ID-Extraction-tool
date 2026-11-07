"""ALZip `.egg` (분할 포함) 에서 파일을 꺼낸다 — 54회차가 TC2 에 쓴 방법을 도구로.

    python3 spike/egg_extract.py <out_dir> <vol1.egg> [vol2.egg …]

구조 (EGG 1.0 명세):
    EGG 헤더   0x41474745 'EGGA' · version(2) · header_id(4) · reserved(4) · 확장 헤더들
      분할     0x24F5A262 · flag(1) · size(2) · prev_id(4) · next_id(4)
      끝       0x08E28222
    파일 헤더  0x0A8590E3 · file_id(4) · length(8) · 확장 헤더들(이름 0x0A8591AC …) · 끝
    블록 헤더  0x02B50C13 · method(1) · hint(1) · usize(4) · csize(4) · crc(4) · 끝 · 데이터
    끝         0x08E28222
분할본은 각 권이 자기 EGG 헤더를 갖고 **그 뒤 바이트가 이어진다** — 권 순서는 분할
헤더의 prev/next id 로 잇는다.  method 1 = raw deflate · 0 = 저장.
"""
from __future__ import annotations

import pathlib
import struct
import sys
import zlib

EGG, SPLIT, END = 0x41474745, 0x24F5A262, 0x08E28222
FILE, NAME, BLOCK = 0x0A8590E3, 0x0A8591AC, 0x02B50C13


def _egg_header(b: bytes):
    """(헤더 길이, header_id, prev_id, next_id)."""
    magic, _ver, hid, _res = struct.unpack_from("<IHII", b, 0)
    assert magic == EGG, "EGGA 머리가 아니다"
    p, prev, nxt = 14, None, None
    while True:
        (m,) = struct.unpack_from("<I", b, p)
        if m == END:
            return p + 4, hid, prev, nxt
        flag, size = struct.unpack_from("<BH", b, p + 4)
        if m == SPLIT:
            prev, nxt = struct.unpack_from("<II", b, p + 7)
        p += 7 + size


def _order(paths):
    vols = []
    for pth in paths:
        b = pathlib.Path(pth).read_bytes()
        hlen, hid, prev, nxt = _egg_header(b)
        vols.append({"path": pth, "body": b[hlen:], "id": hid, "prev": prev, "next": nxt})
    if len(vols) == 1:
        return vols
    by_id = {v["id"]: v for v in vols}
    first = [v for v in vols if not v["prev"]]
    assert len(first) == 1, f"첫 권이 {len(first)}개"
    out, cur = [], first[0]
    while cur:
        out.append(cur)
        cur = by_id.get(cur["next"]) if cur["next"] else None
    assert len(out) == len(vols), "권이 이어지지 않는다"
    return out


def extract(paths, out_dir):
    vols = _order(paths)
    data = b"".join(v["body"] for v in vols)
    out_dir = pathlib.Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    p, written = 0, []
    name = None
    while p + 4 <= len(data):
        (m,) = struct.unpack_from("<I", data, p)
        if m == FILE:
            _fid, _flen = struct.unpack_from("<IQ", data, p + 4)
            p += 16
            name = None
        elif m == NAME:
            flag, size = struct.unpack_from("<BH", data, p + 4)
            raw = data[p + 7:p + 7 + size]
            if flag & 0x08:
                raw = raw[4:]           # parent path id
            if flag & 0x10:
                raw = raw[2:]           # locale
            name = raw.decode("utf-8", "replace")
            p += 7 + size
        elif m == BLOCK:
            method, _hint, usize, csize, crc = struct.unpack_from("<BBIII", data, p + 4)
            p += 18
            if struct.unpack_from("<I", data, p)[0] == END:   # 블록 헤더도 END 로 닫힌다
                p += 4
            chunk = data[p:p + csize]
            p += csize
            if method == 0:
                raw = chunk
            elif method == 1:
                raw = zlib.decompress(chunk, -15)
            else:
                raise SystemExit(f"압축 방식 {method} 은 지원하지 않는다 ({name})")
            assert len(raw) == usize, f"{name}: 크기 {len(raw)} != {usize}"
            got = zlib.crc32(raw) & 0xFFFFFFFF
            assert got == crc, f"{name}: crc {got:08x} != {crc:08x}"
            target = out_dir / pathlib.Path(name or f"file_{len(written)}").name
            target.write_bytes(raw)
            written.append((target, usize, f"{crc:08x}"))
            print(f"{target}  {usize:,} bytes  crc {crc:08x} OK")
        elif m == END:
            p += 4
        else:
            # 모르는 확장 헤더 — flag(1)·size(2) 꼴로 건너뛴다
            flag, size = struct.unpack_from("<BH", data, p + 4)
            p += 7 + size
    return written


if __name__ == "__main__":
    extract(sys.argv[2:], sys.argv[1])
