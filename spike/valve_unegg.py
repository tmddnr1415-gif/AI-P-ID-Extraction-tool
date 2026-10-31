"""Minimal EGG (ALZip) split-archive extractor: store/deflate only — standard library.

    python3 spike/valve_unegg.py <out_dir> part.vol1.egg part.vol2.egg …   (any order; volumes are chained by id)

Used to open the CO2 PJT reference files (2026-10-31).  AZO / bzip2 / LZMA / encrypted archives are refused."""
import struct, sys, zlib, os
def vol_payload(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'EGGA'
    hid, = struct.unpack_from('<I', b, 6)
    p = 14; prev = nxt = None
    while True:
        sig, = struct.unpack_from('<I', b, p)
        if sig == 0x08E28222: p += 4; break
        if sig == 0x24F5A262:
            flag = b[p+4]; size, = struct.unpack_from('<H', b, p+5)
            prev, nxt = struct.unpack_from('<II', b, p+7); p += 7 + size
        else:
            flag = b[p+4]; size, = struct.unpack_from('<H', b, p+5); p += 7 + size
    return hid, prev, nxt, b[p:]
def extract(paths, out):
    vols = {}
    for f in paths:
        hid, prev, nxt, data = vol_payload(f); vols[hid] = (prev, nxt, data)
    first = [h for h, v in vols.items() if v[0] == 0]
    assert len(first) == 1, first
    h = first[0]; stream = b''
    while h:
        prev, nxt, data = vols[h]; stream += data; h = nxt
    p = 0; os.makedirs(out, exist_ok=True)
    while p + 4 <= len(stream):
        sig, = struct.unpack_from('<I', stream, p)
        if sig != 0x0A8590E3: print('stop at', p, hex(sig)); break
        fid, flen = struct.unpack_from('<IQ', stream, p+4); p += 16
        name = None
        while True:
            s, = struct.unpack_from('<I', stream, p)
            if s == 0x08E28222: p += 4; break
            flag = stream[p+4]; size, = struct.unpack_from('<H', stream, p+5)
            body = stream[p+7:p+7+size]
            if s == 0x0A8591AC: name = body.decode('utf-8', 'replace')
            p += 7 + size
        data = b''
        while p + 4 <= len(stream) and struct.unpack_from('<I', stream, p)[0] == 0x02B50C13:
            meth, hint, usz, csz, crc = struct.unpack_from('<BBIII', stream, p+4)
            p += 4 + 14 + 4
            comp = stream[p:p+csz]; p += csz
            if meth == 0: chunk = comp
            elif meth == 1: chunk = zlib.decompress(comp, -15)
            else: raise SystemExit(f'unsupported method {meth}')
            assert zlib.crc32(chunk) & 0xffffffff == crc, 'crc'
            data += chunk
        safe = os.path.basename(name.replace('\\', '/'))
        open(os.path.join(out, safe), 'wb').write(data)
        print('extracted', safe, len(data), 'expected', flen)
if __name__ == '__main__':
    extract(sys.argv[2:], sys.argv[1])
