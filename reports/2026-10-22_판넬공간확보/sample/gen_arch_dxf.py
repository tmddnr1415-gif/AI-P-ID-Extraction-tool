"""시험용 건축 actual 평면도 DXF (MEB 1F) 만들기 — 시험 자료 전용 (대시보드에는 안 들어감).
   필요: pip install ezdxf   사용: python3 gen_arch_dxf.py 출력.dxf [R2010|R2000]
   단위 mm, 원점 = 통심 1/A. 벽(두께) · 기둥 블록 · 문 블록(중첩 · 대칭 · 회전) · 그리드 버블(속성) · MTEXT 한글 · 치수 · 꺼진 레이어."""
import sys, ezdxf
from ezdxf.enums import TextEntityAlignment
out = sys.argv[1]; ver = sys.argv[2] if len(sys.argv) > 2 else 'R2010'
doc = ezdxf.new(ver, setup=True); doc.header['$INSUNITS'] = 4
msp = doc.modelspace()
for n, c, lt in [('A-WALL', 7, 'CONTINUOUS'), ('A-COLS', 8, 'CONTINUOUS'), ('A-DOOR', 3, 'CONTINUOUS'), ('A-GLAZ', 4, 'CONTINUOUS'), ('A-GRID', 1, 'DASHED'),
                 ('A-ANNO-TEXT', 2, 'CONTINUOUS'), ('A-ANNO-DIMS', 6, 'CONTINUOUS'), ('A-FLOR-STRS', 5, 'CONTINUOUS'), ('A-FLOR-FIXT', 9, 'CONTINUOUS'), ('A-AREA-IDEN', 30, 'CONTINUOUS'), ('A-HIDDEN', 8, 'CONTINUOUS')]:
    doc.layers.add(n, color=c, linetype=lt)
doc.layers.get('A-HIDDEN').off()   # 꺼진 레이어 — 가져오기에서 기본 끔
G = 8100; XS = [i * G for i in range(9)]; YS = [j * G for j in range(5)]; GX = '123456789'; GY = 'ABCDE'
# 블록: 기둥 800 □ (중심 기준)
b = doc.blocks.new('COL800', base_point=(0, 0))
b.add_lwpolyline([(-400, -400), (400, -400), (400, 400), (-400, 400)], close=True, dxfattribs={'layer': '0'})
h = b.add_hatch(color=8, dxfattribs={'layer': '0'}); h.paths.add_polyline_path([(-400, -400), (400, -400), (400, 400), (-400, 400)], is_closed=True)
# 블록: 외짝문 (경첩 = 원점, 문 폭 1000, +x 방향 벽, +y 로 열림)
d1 = doc.blocks.new('DOOR1000', base_point=(0, 0))
d1.add_line((0, 0), (0, 1000), dxfattribs={'layer': '0'}); d1.add_arc((0, 0), 1000, 0, 90, dxfattribs={'layer': '0'})
d1.add_lwpolyline([(0, 0), (40, 0), (40, 1000), (0, 1000)], close=True, dxfattribs={'layer': '0'})
# 양개문 1800 = 외짝 900 블록 두 개 (중첩 블록 · 대칭 삽입)
d9 = doc.blocks.new('LEAF900', base_point=(0, 0)); d9.add_line((0, 0), (0, 900)); d9.add_arc((0, 0), 900, 0, 90)
d2 = doc.blocks.new('DOOR1800', base_point=(0, 0))
d2.add_blockref('LEAF900', (0, 0)); d2.add_blockref('LEAF900', (1800, 0), dxfattribs={'xscale': -1})
# 그리드 버블 (속성 글자)
gb = doc.blocks.new('GRIDBUB', base_point=(0, 0)); gb.add_circle((0, 0), 450)
gb.add_attdef('NO', (0, 0), dxfattribs={'height': 400}).set_placement((0, 0), align=TextEntityAlignment.MIDDLE_CENTER)
# 변기 · 세면대 (위생기구)
wc = doc.blocks.new('WC', base_point=(0, 0)); wc.add_lwpolyline([(-200, 0), (200, 0), (200, 200), (-200, 200)], close=True); wc.add_ellipse((0, 450), major_axis=(0, 250), ratio=0.7)

def wall(x1, y1, x2, y2, t=200, gaps=(), ly='A-WALL'):
    """축 방향 벽: 중심선 (x1,y1)-(x2,y2), 두께 t, gaps = [(시작에서 거리, 폭)] 문 자리"""
    hz = y1 == y2; L = abs(x2 - x1) if hz else abs(y2 - y1); s = 1 if (x2 > x1 if hz else y2 > y1) else -1
    cuts = [0]
    for a, w in sorted(gaps): cuts += [a, a + w]
    cuts.append(L)
    for a, c in zip(cuts[0::2], cuts[1::2]):
        if c - a < 1: continue
        if hz:
            xa, xc = x1 + s * a, x1 + s * c
            msp.add_lwpolyline([(xa, y1 - t / 2), (xc, y1 - t / 2), (xc, y1 + t / 2), (xa, y1 + t / 2)], close=True, dxfattribs={'layer': ly})
        else:
            ya, yc = y1 + s * a, y1 + s * c
            msp.add_lwpolyline([(x1 - t / 2, ya), (x1 + t / 2, ya), (x1 + t / 2, yc), (x1 - t / 2, yc)], close=True, dxfattribs={'layer': ly})

W, H = XS[-1], YS[-1]; CY = 13500   # 복도 남쪽 벽
# 외벽 (250) — 창 자리
wall(0, 0, W, 0, 250, [(2000 + i * 8100, 3000) for i in range(8)])
wall(0, H, W, H, 250, [(52000, 2400)])
wall(0, 0, 0, H, 250, [(4000, 3000)]); wall(W, 0, W, H, 250, [(14000, 1800)])
for i in range(8):
    x = 2000 + i * 8100; msp.add_line((x, -60), (x + 3000, -60), dxfattribs={'layer': 'A-GLAZ'}); msp.add_line((x, 60), (x + 3000, 60), dxfattribs={'layer': 'A-GLAZ'})
# 내벽 (200)
wall(0, YS[2], W, YS[2], 200, [(9000, 1800), (29400, 1800), (45600, 1000), (54000, 1000)])     # C 열 = CCR · CER 남쪽 벽 (문)
wall(0, CY, W, CY, 200, [(6000, 1000), (19000, 1000), (27000, 1000), (40000, 1000), (50000, 1200)])
wall(XS[3], YS[2], XS[3], H, 200, [(9500, 1000)])          # CCR | CER
wall(XS[6], YS[2], XS[6], H, 200)                           # CER | SERVER
wall(XS[6], YS[3] + 2000, W, YS[3] + 2000, 200, [(3000, 1000)])   # SERVER | MEETING
wall(XS[2], 0, XS[2], CY); wall(XS[3], 0, XS[3], CY); wall(36450, 0, 36450, CY); wall(XS[6], 0, XS[6], CY); wall(56700, 0, 56700, CY)
# 기둥
for x in XS:
    for y in YS:
        msp.add_blockref('COL800', (x, y), dxfattribs={'layer': 'A-COLS'})
# 문 (블록 · 회전 · 대칭)
msp.add_blockref('DOOR1800', (9000, YS[2]), dxfattribs={'layer': 'A-DOOR'})                      # CCR 양개 (북쪽으로)
msp.add_blockref('DOOR1800', (29400, YS[2]), dxfattribs={'layer': 'A-DOOR'})                     # CER 양개
msp.add_blockref('DOOR1000', (46600, YS[2]), dxfattribs={'layer': 'A-DOOR', 'xscale': -1})       # CER 외짝 (대칭)
msp.add_blockref('DOOR1000', (XS[3], YS[2] + 9500), dxfattribs={'layer': 'A-DOOR', 'rotation': 90})   # CCR ↔ CER
msp.add_blockref('DOOR1000', (55000, YS[2]), dxfattribs={'layer': 'A-DOOR'})
for x in (6000, 19000, 27000, 40000):
    msp.add_blockref('DOOR1000', (x + 1000, CY), dxfattribs={'layer': 'A-DOOR', 'rotation': 180})
# 그리드 선 + 버블
for x, n in zip(XS, GX):
    msp.add_line((x, -2500), (x, H + 2500), dxfattribs={'layer': 'A-GRID'})
    msp.add_blockref('GRIDBUB', (x, H + 3000), dxfattribs={'layer': 'A-GRID'}).add_auto_attribs({'NO': n})
for y, n in zip(YS, GY):
    msp.add_line((-2500, y), (W + 2500, y), dxfattribs={'layer': 'A-GRID'})
    msp.add_blockref('GRIDBUB', (-3000, y), dxfattribs={'layer': 'A-GRID'}).add_auto_attribs({'NO': n})
# 실 이름 (MTEXT 한글 + 영문) · 면적
rooms = [((0, YS[2], XS[3], H), 'CENTRAL CONTROL ROOM\\P중앙제어실 (Access Floor 600)'), ((XS[3], YS[2], XS[6], H), 'ELECTRONIC ROOM\\P전자기기실 (Access Floor 600)'),
         ((XS[6], YS[3] + 2000, W, H), 'SERVER ROOM\\P서버실'), ((XS[6], YS[2], W, YS[3] + 2000), 'MEETING\\P회의실'),
         ((0, CY, W, YS[2]), 'CORRIDOR 복도'), ((0, 0, XS[2], CY), 'ENGINEERING ROOM\\P엔지니어링실'), ((XS[2], 0, XS[3], CY), 'SHIFT SUPERVISOR\\P근무책임자실'),
         ((XS[3], 0, 36450, CY), 'UPS ROOM\\PUPS실'), ((36450, 0, XS[6], CY), 'BATTERY ROOM\\P축전지실'), ((XS[6], 0, 56700, CY), 'TOILET\\P화장실'), ((56700, 0, W, CY), 'STAIR\\P계단실')]
for (x0, y0, x1, y1), name in rooms:
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    m = msp.add_mtext(name, dxfattribs={'layer': 'A-ANNO-TEXT', 'char_height': 450 if 'CORRIDOR' not in name else 300})
    m.set_location((cx, cy + 500), attachment_point=5)
    a = (x1 - x0) * (y1 - y0) / 1e6
    msp.add_text(f'A={a:.1f} m2', dxfattribs={'layer': 'A-AREA-IDEN', 'height': 250}).set_placement((cx, cy - 900), align=TextEntityAlignment.MIDDLE_CENTER)
# 계단
for k in range(16):
    msp.add_line((57500, 1500 + k * 280), (60500, 1500 + k * 280), dxfattribs={'layer': 'A-FLOR-STRS'})
    msp.add_line((61300, 1500 + k * 280), (64000, 1500 + k * 280), dxfattribs={'layer': 'A-FLOR-STRS'})
msp.add_line((60900, 1200), (60900, 9000), dxfattribs={'layer': 'A-FLOR-STRS'})
msp.add_lwpolyline([(59000, 2000), (59000, 6000), (58800, 5700), (59200, 5700), (59000, 6000)], dxfattribs={'layer': 'A-FLOR-STRS'})
# 화장실 기구 (회전)
for k in range(4):
    msp.add_blockref('WC', (50000 + k * 1100, 300), dxfattribs={'layer': 'A-FLOR-FIXT'})
    msp.add_blockref('WC', (50000 + k * 1100, CY - 300), dxfattribs={'layer': 'A-FLOR-FIXT', 'rotation': 180})
# CER 안 바닥 트렌치 (점선 대신 얇은 사각) · Access Floor 경계 호
msp.add_lwpolyline([(26000, 17200), (46500, 17200), (46500, 17800), (26000, 17800)], close=True, dxfattribs={'layer': 'A-FLOR-FIXT'})
msp.add_text('CABLE TRENCH W600', dxfattribs={'layer': 'A-ANNO-TEXT', 'height': 250}).set_placement((26200, 18000))
msp.add_lwpolyline([(1500, 30000), (5000, 30000, 0.4142), (7000, 32000)], dxfattribs={'layer': 'A-FLOR-FIXT'})   # bulge 호
msp.add_circle((12000, 24300), 300, dxfattribs={'layer': 'A-FLOR-FIXT'})   # 바닥 배수
msp.add_spline([(1000, 18000), (3000, 19500), (5000, 18200), (7000, 19800)], dxfattribs={'layer': 'A-FLOR-FIXT'})
msp.add_line((0, 0), (W, H), dxfattribs={'layer': 'A-HIDDEN'})   # 꺼진 레이어 (안 보여야 함)
# 치수 (mm 도면: 글자 250)
DIMO = {'dimtxt': 250, 'dimlfac': 1, 'dimasz': 200, 'dimexe': 150, 'dimexo': 150, 'dimgap': 80, 'dimtsz': 0, 'dimdec': 0}
for i in range(8):
    msp.add_linear_dim(base=(0, H + 1500), p1=(XS[i], H), p2=(XS[i + 1], H), dimstyle='EZDXF', override=DIMO, dxfattribs={'layer': 'A-ANNO-DIMS'}).render()
msp.add_linear_dim(base=(-1500, 0), p1=(0, YS[2]), p2=(0, H), angle=90, dimstyle='EZDXF', override=DIMO, dxfattribs={'layer': 'A-ANNO-DIMS'}).render()
# 도면 표제
msp.add_text('MEB 1F FLOOR PLAN (ACTUAL)  DWG NO. A-101  REV.0', dxfattribs={'layer': 'A-ANNO-TEXT', 'height': 700}).set_placement((0, -5500))
msp.add_text('건축 실시설계 평면도 — 계장 판넬 배치 검토용 (시험 도면)', dxfattribs={'layer': 'A-ANNO-TEXT', 'height': 450}).set_placement((0, -6600))
doc.saveas(out)
print('saved', out, ver)
