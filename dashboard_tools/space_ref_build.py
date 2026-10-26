# -*- coding: utf-8 -*-
"""판넬 공간확보 Ref. PJT Room Layout 만들기 → dashboard/apps/space/ref.js

사용자가 보낸 'CCR and Electronic Room Arrangement' 도면 사진(F3 · NT34 · Tanajib · Amiral · QFE · UAD)을
사람이 읽어 옮긴 것. 치수 = 도면 치수선 · Equipment List 의 W x D x H, 자리 = 치수선 + 사진 눈금으로 읽은 근사값(±200~300 mm).
곡선 · 비스듬한 콘솔은 앱이 90° 회전만 다루므로 곧은 줄로 폈음. 벽걸이(시계 · Mimic) · 책상 위 물건(EPB · RDLI)은 뺌.

새 Ref 를 더하려면 아래 REFS 에 함수 하나 더 쓰고 `python3 dashboard_tools/space_ref_build.py`.
같이 '학습' 통계(줄 사이 통로 · 벽 이격 · 콘솔 ↔ 대형 화면 거리 …)를 뽑아 ref.js 의 rules 로 넣음 → Option A 자동 배치 시작값.
"""
import json, os, re, statistics

OUT = os.path.join(os.path.dirname(__file__), '..', 'dashboard', 'apps', 'space', 'ref.js')

# ---------------------------------------------------------------- 물건 분류 · Type
COL = {'cab': '#2f6db5', 'net': '#7a59b0', 'pwr': '#b8642a', 'ows': '#4f6a8a', 'prn': '#6b7280', 'ls': '#34495e', 'hv': '#2f8a6a'}


def kind_of(desc, w, d, h):
    u = desc.upper()
    if re.search(r'LARGE SCREEN|LVS|LSD|CCTV DISPLAY|VIDEO WALL', u) and 'CONTROLLER' not in u and 'WORKSTATION' not in u:
        return 'ls'
    if re.search(r'PANEL|CABINET|CUBICLE|RACK', u) and not re.search(r'OWS|EWS|WORKSTATION|CLIENT|DESK', u):
        return 'cab'
    if 'PRINTER' in u or 'FAX' in u or ('SCANNER' in u and not re.search(r'CLIENT|WORKSTATION|OWS', u)) or (h and h <= 800 and w <= 850 and d <= 850):
        return 'prn'
    if h and (h <= 1000 or (h <= 1300 and re.search(r'OWS|EWS|WORKSTATION|DESK|CONSOLE|CLIENT|STATION', u))):
        return 'ows'
    return 'cab'


def cab_family(desc):
    u = desc.upper()
    if re.search(r'POWER|PDP|DIST', u): return 'pwr'
    if re.search(r'NETWORK|SERVER|RACK|OPC|SCADA|HISTORIAN|CYBER|TEL|LAN|PAGA|PABX|FDM|PCM', u): return 'net'
    if re.search(r'HVAC|FIRE|FA PANEL|FGC|SMOKE', u): return 'hv'
    return 'cab'


class Room:
    def __init__(self, rid, project, doc, room, W, L, note=''):
        self.rid, self.project, self.doc, self.room, self.W, self.L, self.note = rid, project, doc, room, W, L, note
        self.types, self.panels, self.tags = {}, [], {}

    def typ(self, k, w, d, h, desc):
        fam = cab_family(desc) if k == 'cab' else k
        key = (k, fam, w, d, h)
        if key in self.types:
            return self.types[key]['id']
        tid = 't%d' % (len(self.types) + 1)
        if k == 'ows':
            mon = 2 if w >= 1000 else 1
            t = {'name': f'OWS / EWS Desk {w}×{d}', 'pre': 'WS-', 'kind': 'desk', 'w': w, 'd': d, 'top': min(h or 750, 950), 'bays': 1,
                 'mon': mon, 'monIn': 24, 'tiers': 1, 'front': 1500, 'rear': 0, 'door': 'none', 'hinge': 'L'}
        elif k == 'ls':
            inch = 75 if not d or d < 1000 else 100
            t = {'name': f'Large Screen {inch}"', 'pre': 'LS-', 'kind': 'screen', 'w': 0, 'd': max(d or 600, 400), 'cols': 1, 'rows': 1,
                 'tileIn': w if w and w < 200 else inch, 'elev': 900, 'front': 1000, 'rear': 0, 'door': 'none', 'hinge': 'L'}
        elif k == 'prn':
            t = {'name': f'Printer {w}×{d}', 'pre': 'PR-', 'kind': 'cabinet', 'w': w, 'd': d, 'h': h or 750,
                 'front': 800, 'rear': 0, 'door': 'none', 'hinge': 'L'}
        else:
            nm = {'pwr': 'Power Dist. Panel', 'net': 'Network / Server Cabinet', 'hv': 'HVAC / Fire Panel', 'cab': 'System Cabinet'}[fam]
            t = {'name': f'{nm} {w}×{d}×{h}', 'pre': {'pwr': 'PD-', 'net': 'NW-', 'hv': 'HV-', 'cab': 'SC-'}[fam], 'kind': 'cabinet',
                 'w': w, 'd': d, 'h': h or 2200, 'front': 1000, 'rear': 0, 'door': 'front', 'hinge': 'LR' if w >= 800 else 'L'}
        t['id'] = tid
        t['color'] = COL[fam]
        # 같은 이름이 있으면 번호
        names = {x['name'] for x in self.types.values()}
        base, n = t['name'], 2
        while t['name'] in names:
            t['name'] = f'{base} ({n})'; n += 1
        self.types[key] = t
        return tid

    def tag(self, no):
        no = str(no)
        k = self.tags.get(no, 0) + 1
        self.tags[no] = k
        if k == 2:   # 같은 번호가 둘 이상 = 1, 2 … 로 (도면에 같은 번호가 여러 대)
            for p in self.panels:
                if p['tag'] == no:
                    p['tag'] = no + '-1'
        return no if k == 1 else f'{no}-{k}'

    def row(self, x, y, rot, items):
        """items: (No, desc, w, d, h) 또는 ('gap', mm). rot 0/180 = x 방향으로, 90/270 = y 방향으로 붙여 놓음.
        앞면(rot 0 위 · 90 오른쪽 · 180 아래 · 270 왼쪽)을 한 줄에 맞춤. 놓은 끝 좌표를 돌려줌."""
        pos = x if rot in (0, 180) else y
        dmax = max([it[3] for it in items if it[0] != 'gap'] or [0])
        for it in items:
            if it[0] == 'gap':
                pos += it[1]; continue
            no, desc, w, d, h = it
            k = kind_of(desc, w, d, h)
            if k == 'ls':
                inch = w if w < 200 else 75
                w = round(inch * 25.4 * 0.8716 + 80)
            tid = self.typ(k, w if k != 'ls' else inch, d, h, desc)
            if rot == 0:
                px, py = pos, y
            elif rot == 180:
                px, py = pos, y + dmax - d
            elif rot == 90:
                px, py = x + dmax - d, pos
            else:
                px, py = x, pos
            self.panels.append({'type': tid, 'tag': self.tag(no), 'desc': desc, 'x': round(px), 'y': round(py), 'rot': rot, 'scope': ''})
            pos += w
        return pos

    def data(self):
        types = []
        for t in self.types.values():
            t = dict(t)
            if t['kind'] == 'screen':
                t['tileIn'] = t['tileIn']
            types.append(t)
        for i, p in enumerate(self.panels):
            p['id'] = f'{self.rid}-p{i + 1}'
        return {'room': {'w': self.W, 'l': self.L, 'spX': '', 'spY': '', 'col': 600, 'margin': 0, 'spare': 0, 'spareDir': 'x', 'gapP': 0, 'gapD': 0,
                         'touchOK': True, 'enforce': False, 'autoFit': False},
                'snap': 50, 'types': types, 'panels': self.panels,
                'info': {'project': self.project + ' (Ref)', 'room': self.room, 'author': '', 'rev': ''}}


def C(no, desc, w, d, h):
    return (no, desc, w, d, h)


G = lambda mm: ('gap', mm)
OWS = lambda no, desc, w=1200, d=1100, h=930: (no, desc, w, d, h)
PRN = lambda no, desc='PRINTER', w=800, d=800: (no, desc, w, d, 750)

# ---------------------------------------------------------------- F3 PJT (19CN-00GEN00-J28-0001 R0)
def f3():
    P, D = 'F3 PJT', '19CN-00GEN00-J28-0001 R0'
    out = []
    r = Room('f3-cer', P, D, 'Central Electronic Room (G01)', 6000, 17600, '두 줄 마주 봄(앞면 통로 ≈1,750) · 뒤 1,350~1,500 · 1,600 폭 FGC 판넬은 위쪽')
    r.row(200, 200, 90, [C('24', 'HVAC CONTROL PANEL', 1400, 800, 2300)])
    r.row(1490, 2070, 90, [C('23', 'FGC UNIT CONTROL PANEL #4', 1600, 800, 2285), C('22', 'FGC UNIT CONTROL PANEL #3', 1600, 800, 2285)])
    r.row(3900, 2070, 270, [C('21', 'FGC UNIT CONTROL PANEL #2', 1600, 800, 2285), C('20', 'FGC UNIT CONTROL PANEL #1', 1600, 800, 2285)])
    r.row(1490, 6390, 90, [C('19', 'GTG NETWORK CABINET', 800, 600, 2285), C('18', 'STG NETWORK CABINET #2 GROUP #2', 800, 600, 2285),
                           C('17', 'STG NETWORK CABINET #2 GROUP #1', 800, 600, 2285), C('16', 'OPC CABINET #3', 700, 600, 2285),
                           C('15', 'OPC CABINET #2', 700, 600, 2285), C('14', 'OPC CABINET #1', 700, 600, 2285)])
    r.row(3900, 6660, 270, [C('13', 'DB SERVER RACK', 700, 600, 2285), C('12', 'SCADA SERVER CABINET', 700, 600, 2285), C('11', 'NETWORK CABINET #3', 700, 600, 2285),
                            C('10', 'NETWORK CABINET #2', 700, 600, 2285), C('9', 'NETWORK CABINET #1', 700, 600, 2285), C('8', 'PWCS CABINET', 700, 1000, 2285)])
    r.row(1490, 13230, 90, [C('7', 'DCS PDP #3', 700, 600, 2285), C('6', 'DCS PDP #2', 700, 600, 2285), C('5', 'DCS PDP #1', 700, 600, 2285), C('4', 'SIS CABINET', 1400, 600, 2285)])
    r.row(3900, 14670, 270, [C('3', 'DCS RELAY CABINET #1', 700, 600, 2285), C('2', 'DCS SYSTEM CABINET #2', 700, 600, 2285), C('1', 'DCS SYSTEM CABINET #1', 700, 600, 2285)])
    out.append(r)

    r = Room('f3-ccr', P, D, 'Central Control Room (G09)', 17500, 11400, '콘솔 한 줄(1,200 데스크, 그룹 사이 600) · 콘솔 ↔ 대형 화면 1,400 · 뒷줄 데스크 벽에서 2,500 · 프린터는 벽 따라')
    r.row(6100, 2500, 0, [OWS('20', 'WT/WWT OWS'), OWS('21', 'FA OWS'), OWS('22', 'CEMS WORKSTATION'), OWS('23', 'EDL CLIENT WITH SCANNER')])
    r.row(550, 7200, 0, [OWS('1', 'GROUP #1 ST OIS'), G(200), OWS('2', 'GROUP #1 DCS OWS-1'), OWS('3', 'GROUP #1 DCS OWS-2'), OWS('4', 'GROUP #1 GT OPS'), G(600),
                         OWS('5', 'ECMS OWS-1'), OWS('6', 'COMMON DCS OWS-1'), OWS('7', 'COMMON DCS OWS-2'), OWS('8', 'ECMS OWS-2'), G(600),
                         OWS('9', 'GROUP #2 GT OPS'), OWS('10', 'GROUP #2 DCS OWS-1'), OWS('11', 'GROUP #2 DCS OWS-2'), G(200), OWS('12', 'GROUP #2 ST OIS')])
    r.row(3700, 9700, 0, [C('18', 'LARGE SCREEN DISPLAY #1', 75, 600, 0)])
    r.row(11950, 9700, 0, [C('19', 'LARGE SCREEN DISPLAY #2', 75, 600, 0)])
    r.row(180, 10500, 0, [PRN('24', 'GROUP #1 GT OPS PRINTER'), PRN('25', 'ECMS OWS PRINTER'), PRN('26', 'GROUP #1 ST OWS PRINTER')])
    r.row(14050, 10500, 0, [PRN('27', 'COMMON OWS PRINTER-1'), PRN('28', 'COMMON OWS PRINTER-2'), PRN('29', 'GROUP #2 GT OPS PRINTER'), PRN('30', 'GROUP #2 ST OWS PRINTER')])
    r.row(9180, 100, 180, [PRN('31', 'WT/WWT OWS PRINTER'), PRN('32', 'FA OWS PRINTER')])
    r.row(11900, 100, 180, [C('33', 'TR MONITORING PANEL #1', 800, 800, 2200), C('34', 'TR MONITORING PANEL #2', 800, 800, 2200), C('35', 'FA PANEL', 800, 600, 2200)])
    out.append(r)

    r = Room('f3-eng', P, D, 'Engineering Room (G10)', 5900, 9800, '양쪽 벽에 데스크(벽 쪽 모니터, 가운데 통로 ≈2,400) · 프린터는 위 벽 · 데스크 둘이 1,200 하나를 같이 씀')
    r.row(150, 100, 180, [PRN('26', 'GROUP #1 ST EWS PRINTER'), PRN('25', 'GROUP #1 GT EMS PRINTER'), PRN('24', 'GROUP #2 ST EWS PRINTER'),
                          PRN('23', 'GROUP #1 ST EWS PRINTER'), PRN('22', 'DCS EWS PRINTER')])
    r.row(100, 1900, 90, [OWS('1', 'GROUP #1 GT EMS', 800), OWS('2', 'GROUP #2 GT EMS', 800), OWS('3', 'GROUP #1/#2 GT CPFA CLIENT'), OWS('5', 'GROUP #1 GT ACS_A/B'),
                          OWS('7', 'GROUP #1 GT OPC SERVER-1/2'), OWS('9', 'GROUP #2 GT ACS_A/B'), OWS('11', 'GROUP #2 GT OPC SERVER-1/2')])
    r.row(4800, 1900, 270, [PRN('21', 'ECMS EWS PRINTER')])
    r.row(4360, 2790, 270, [OWS('20', 'ECMS EWS', 800), OWS('19', 'COMMON DCS EWS'), OWS('18', 'GROUP #2 DCS EWS'), OWS('17', 'GROUP #1 DCS EWS'),
                            OWS('15', 'GROUP #1/#2 ST EWS'), OWS('13', 'GROUP #1/#2 ST HDMS')])
    out.append(r)

    r = Room('f3-met', P, D, 'Metering Room (G02)', 2650, 5700, '판넬 세 대 한 줄 · 양옆 900 내외')
    r.row(1000, 1710, 270, [C('3', 'ELEC. METERING PANEL', 800, 800, 2200), C('2', 'PASS & FDM', 800, 800, 2200), C('1', 'GAS METERING PANEL', 800, 800, 2200)])
    out.append(r)
    return out


# ---------------------------------------------------------------- NT34 (19HM-00CZA00-J28-0001 R4)
def nt34():
    P, D = 'NT34', '19HM-00CZA00-J28-0001 R4'
    out = []
    r = Room('nt34-ccr', P, D, 'Central Control Room', 14100, 25400, '곡선 콘솔 셋(NT#4 · Common · NT#3)을 곧게 폄 — 운전원은 오른쪽, 대형 화면은 왼쪽 벽 · 프린트 구역 왼쪽 위')
    r.row(560, 1570, 90, [PRN('39', 'PRINTER DESK FOR SCMS #1'), PRN('40', 'PRINTER DESK FOR SCMS #2'), PRN('41', 'DCS/TCS NETWORK PRINTER #1'),
                          PRN('42', 'DCS/TCS NETWORK PRINTER #2'), PRN('43', 'DCS/TCS NETWORK PRINTER #3'), PRN('44', 'CEMS PRINTER')])
    r.row(1570, 500, 180, [PRN('45', 'CCTV PRINTER'), PRN('46', 'ECMS PRINTER'), PRN('53', 'FIRE ALARM PRINTER DESK'), PRN('58', 'HVAC PRINTER DESK')])
    r.row(300, 6800, 90, [C('32', 'LARGE SCREEN #1 FOR NT#3', 75, 600, 0)])
    r.row(300, 10000, 90, [C('33', 'LARGE SCREEN #2 FOR COMMON', 75, 600, 0)])
    r.row(300, 13200, 90, [C('34', 'LARGE SCREEN #3 FOR COMMON', 75, 600, 0)])
    r.row(300, 16400, 90, [C('35', 'LARGE SCREEN #4 FOR NT#4', 75, 600, 0)])
    r.row(2910, 3600, 90, [OWS('6', 'DCS/TCS OWS #1 FOR NT#4', 1200, 1095), OWS('7', 'DCS/TCS OWS #2 FOR NT#4', 1200, 1095), OWS('8', 'DCS/TCS OWS #3 FOR NT#4', 1200, 1095),
                           OWS('9', 'DCS/TCS OWS #4 FOR NT#4', 1200, 1095), OWS('10', 'DCS/TCS OWS #5 FOR NT#4', 1200, 1095)])
    r.row(6050, 9630, 90, [OWS('20', 'FIRE ALARM SYSTEM WORKSTATION', 1200, 1095), OWS('11', 'COMMON DCS OWS #1', 1200, 1095), OWS('12', 'COMMON DCS OWS #2', 1200, 1095),
                           OWS('13', 'COMMON DCS OWS #3', 1200, 1095), OWS('21', 'HVAC WORKSTATION', 1200, 1095), OWS('22', 'CCTV WORKSTATION', 1200, 1095)])
    r.row(2910, 15790, 90, [OWS('5', 'DCS/TCS OWS #5 FOR NT#3', 1200, 1095), OWS('4', 'DCS/TCS OWS #4 FOR NT#3', 1200, 1095), OWS('3', 'DCS/TCS OWS #3 FOR NT#3', 1200, 1095),
                            OWS('2', 'DCS/TCS OWS #2 FOR NT#3', 1200, 1095), OWS('1', 'DCS/TCS OWS #1 FOR NT#3', 1200, 1095)])
    r.row(10300, 7390, 90, [OWS('14', 'SUPERVISOR WORKSTATION #1', 1200, 1095), OWS('15', 'SUPERVISOR WORKSTATION #2', 1200, 1095)])
    r.row(10300, 11300, 90, [OWS('17', 'ECMS OWS #1', 1200, 1095), OWS('18', 'ECMS OWS #2', 1200, 1095), OWS('19', 'CEMS WORKSTATION', 1200, 1095)])
    r.row(10300, 16460, 90, [OWS('23', 'OWS FOR SCMS #1', 1200, 1095), OWS('24', 'OWS FOR SCMS #2', 1200, 1095)])
    r.row(8850, 23700, 0, [OWS('25', 'NT4 DIM PC DESK (#4 MAIN)'), OWS('56', 'NT3 DIM PC DESK (#3 MAIN)'), OWS('16', 'SUPERVISOR WORKSTATION #3')])
    r.row(900, 24400, 0, [PRN('57', 'NT4 DIM PC PRINTER DESK'), PRN('60', 'NT3 DIM PRINTER DESK'), PRN('59', 'NT4 FAX FOR NLDC'), PRN('61', 'NT3 FAX FOR NLDC')])
    out.append(r)

    r = Room('nt34-er', P, D, 'Electronic Room', 7200, 5600, '두 줄 앞면끼리 마주 봄 — 통로 1,560 · 뒤는 벽에 붙임 (판넬 크기는 목록에 없어 800×800×2200 으로 둠)')
    r.row(780, 540, 180, [C(str(i), 'ELECTRONIC ROOM CABINET', 800, 800, 2200) for i in (8, 9, 6, 11, 14, 13, 12)])
    r.row(800, 3700, 0, [C(str(i), 'ELECTRONIC ROOM CABINET', 800, 800, 2200) for i in (10, 5, 4, 3, 2, 1)])
    out.append(r)

    r = Room('nt34-eng', P, D, 'Engineering Room', 16300, 5200, '위 · 아래 벽에 데스크 줄(벽 쪽 모니터) 마주 봄 — 의자 통로 ≈2,800 · 프린터는 오른쪽 벽')
    r.row(1120, 100, 180, [OWS(str(i), 'EWS DESK') for i in ('46', '45', '14', '13', '10', '8', '7', '3', '2', '1')])
    r.row(230, 4000, 0, [OWS(str(i), 'EWS DESK') for i in ('47', '16', '15', '12', '11', '9', '6', '5', '4', '19', '18')])
    r.row(15350, 1680, 270, [PRN(str(i)) for i in ('48', '49', '50', '51')])
    out.append(r)
    return out


# ---------------------------------------------------------------- Tanajib (19K9-20GEN00-J28-0001 RX0)
def tanajib():
    P, D = 'Tanajib', '19K9-20GEN00-J28-0001 RX0'
    out = []
    r = Room('tnj-ccr', P, D, 'Central Control Room (106)', 13200, 16000, '콘솔 한 줄(위아래로 김) — 운전원 왼쪽, 콘솔 ↔ 대형 화면 ≈3,600 · 둘째 콘솔 3,300 뒤 · 프린터는 왼쪽 벽 따라')
    r.row(100, 435, 90, [PRN('15', 'CCTV COLOR PRINTER'), PRN('14', 'ECMS COLOR PRINTER'), PRN('13', 'FIRE ALARM COLOR PRINTER'), PRN('12', 'STG COLOR PRINTER'),
                         PRN('11', 'GTG COLOR PRINTER'), PRN('10', 'DCS COLOR PRINTER'), PRN('10', 'DCS COLOR PRINTER'), PRN('10', 'DCS COLOR PRINTER')])
    r.row(7690, 2860, 270, [OWS('6', 'ECMS OWS', 1200, 1100, 750), OWS('3', 'DCS OWS 1 (HRSG/AUX BOILER)', 1200, 1100, 750), OWS('3', 'DCS OWS 2', 1200, 1100, 750),
                            OWS('3', 'DCS OWS 3 (BOP)', 1200, 1100, 750), OWS('2', 'EMERGENCY PUSH BUTTON STATION', 850, 1100, 750),
                            OWS('4', 'GTG OWS 1 CLT', 1200, 1100, 750), OWS('4', 'GTG OWS 2 CLT', 1200, 1100, 750), OWS('4', 'GTG OWS 3 CLT', 1200, 1100, 750),
                            OWS('5', 'STG OWS 1', 1200, 1100, 750), OWS('5', 'STG OWS 2', 1200, 1100, 750)])
    r.row(4500, 5950, 270, [OWS('9', 'FIRE ALARM WORKSTATION', 1000, 1100, 750), OWS('7', 'DCS OWS (SHIFT ENGINEER)', 1200, 1100, 750),
                            OWS('8', 'CCTV WORKSTATION', 1200, 1100, 750), OWS('18', 'LARGE SCREEN CONTROLLER', 1000, 1100, 750)])
    r.row(12300, 5500, 270, [C('1', 'LARGE SCREEN (70")', 70, 700, 0)])
    r.row(12300, 7300, 270, [C('16', 'RDLI CONSOLE', 1400, 500, 1700)])
    r.row(12300, 8900, 270, [C('1', 'LARGE SCREEN (70")', 70, 700, 0)])
    out.append(r)

    r = Room('tnj-er', P, D, 'Electronic Room (104)', 10700, 7900, '세 줄 모두 앞면 아래 — 앞 ↔ 다음 줄 뒤 통로 1,100~1,300 · 줄 끝 ↔ 벽 1,450~2,450')
    r.row(2165, 1705, 180, [C('55', 'FDM/PCM CABINET', 800, 800, 2200), G(900), C('47', 'ST TCS NETWORK PANEL', 600, 800, 2000), G(900),
                            C('46', 'GT OSM RACK', 600, 1086, 1750), C('45', 'GT CONTROL SERVER RACK', 600, 1092, 1994), G(700),
                            C('51', 'DCS PWCS PANEL', 700, 1100, 2285)])
    r.row(2457, 3915, 180, [C('42', 'DCS NETWORK PANEL 1', 700, 600, 2285), C('42', 'DCS NETWORK PANEL 2', 700, 600, 2285), C('43', 'INTERFACE PANEL', 700, 600, 2285),
                            C('44', 'DCS REMOTE I/O PANEL', 700, 600, 2285), G(1407), C('41', 'DCS POWER DIST. PANEL 1', 700, 600, 2285),
                            C('41', 'DCS POWER DIST. PANEL 2', 700, 600, 2285)])
    r.row(1457, 5800, 180, [C('50', 'HVAC CONTROL PANEL', 1000, 600, 2200), G(1001), C('52', 'FOX PANEL', 800, 600, 2200), C('54', 'TEL & LAN CABINET', 802, 800, 2100),
                            C('49', 'PAGA CABINET', 802, 800, 2100), C('49', 'PAGA CABINET', 802, 800, 2100), C('48', 'ECMS PANEL', 800, 800, 2200)])
    out.append(r)

    r = Room('tnj-eng', P, D, 'Engineering Room (105)', 10500, 8000, '위 · 아래 벽에 데스크 줄 마주 봄 · 프린터는 오른쪽 벽')
    r.row(554, 100, 180, [OWS('20', 'DCS EWS 1', 1200, 1100, 750), OWS('20', 'DCS EWS 2', 1200, 1100, 750), OWS('21', 'DCS HISTORIAN SERVER', 1200, 1100, 750),
                          OWS('22', 'DCS PI SERVER', 1200, 1100, 750), OWS('23', 'DCS PMS WORKSTATION', 1000, 1100, 750),
                          OWS('31', 'ECMS EWS', 1000, 1100, 750), OWS('32', 'DGA WORKSTATION', 1000, 1100, 750)])
    r.row(554, 6800, 0, [OWS('24', 'GTG EWS 1 CLT', 1000, 1100, 750), OWS('24', 'GTG EWS 2 CLT', 1000, 1100, 750), OWS('25', 'GTG HISTORIAN SERVER', 1000, 1100, 750),
                         OWS('26', 'GT OPC SERVER', 1000, 1100, 750), OWS('27', 'GTG PPMS WORKSTATION', 1000, 1100, 750), OWS('28', 'GTG VMS STATION', 1000, 1100, 750),
                         OWS('29', 'STG EWS', 1000, 1100, 750), OWS('30', 'STG VMS WORKSTATION', 1000, 1100, 750), OWS('33', 'CEMS WORKSTATION', 1000, 1100, 750)])
    r.row(9600, 2320, 270, [PRN('34', 'DCS COLOR PRINTER'), PRN('35', 'COLOR PRINTER FOR GTG'), PRN('36', 'COLOR PRINTER FOR CEMS'), PRN('37', 'ECMS COLOR PRINTER'),
                            PRN('38', 'GTG VMS COLOR PRINTER')])
    out.append(r)

    r = Room('tnj-met', P, D, 'Metering Control Room (103)', 14200, 8800, '판넬 세 줄 모두 앞면 위 · 줄 사이 1,100~1,200 · 데스크 · 프린터는 위 벽')
    r.row(3480, 100, 180, [PRN('4', 'MDAS COLOR PRINTER'), PRN('5', 'PLC COLOR PRINTER')])
    r.row(7130, 100, 180, [OWS('1', 'MDAS WORKSTATION 1', 1200, 1100, 750), OWS('1', 'MDAS WORKSTATION 2', 1200, 1100, 750),
                           OWS('2', 'PLC OWS (WT/WWT/CPP)', 1000, 1100, 750), OWS('3', 'PLC EWS (WT/WWT/CPP)', 1200, 1100, 750)])
    r.row(855, 3200, 0, [C('15', 'PLC MARSHALLING PANEL (CPP) 1', 1000, 600, 2200), C('15', 'PLC MARSHALLING PANEL (CPP) 2', 1000, 600, 2200),
                         C('15', 'PLC MARSHALLING PANEL (CPP) 3', 1000, 600, 2200), C('14', 'PLC CONTROLLER PANEL (CPP)', 1000, 600, 2200), G(1179),
                         C('17', 'PLC MARSHALLING PANEL WT 2', 1606, 805, 2105), C('17', 'PLC MARSHALLING PANEL WT 1', 1206, 805, 2105),
                         C('17', 'PLC MARSHALLING PANEL WWT 1', 806, 805, 2105), C('16', 'PLC CONTROLLER PANEL (WT/WWT COMMON)', 806, 805, 2105), G(1197),
                         C('19', 'TEL & LAN CABINET', 602, 800, 1435)])
    r.row(1955, 5200, 0, [C('6', 'DCS POWER DIST. PANEL', 700, 600, 2285), G(1200), C('8', 'DCS I/O PANEL 1', 700, 600, 2285), C('8', 'DCS I/O PANEL 2', 700, 600, 2285),
                          C('8', 'DCS I/O PANEL 3', 700, 600, 2285), C('8', 'DCS RELAY PANEL', 700, 600, 2285), C('7', 'DCS CONTROLLER & I/O PANEL', 700, 600, 2285),
                          C('9', 'DCS INTERFACE PANEL', 700, 600, 2285), G(618), C('13', 'METERING PANEL (MDAS) 1', 800, 800, 2000),
                          C('13', 'METERING PANEL (MDAS) 2', 800, 800, 2000), C('13', 'METERING PANEL (MDAS) 3', 800, 800, 2000)])
    r.row(1700, 7200, 0, [C('12', 'SIS PROTECTION PANEL (A)', 1400, 600, 2285), C('11', 'DCS I/O PANEL (A)', 700, 600, 2285), C('11', 'DCS RELAY PANEL (A)', 700, 600, 2285),
                          C('10', 'DCS CONTROLLER PANEL (A)', 700, 600, 2285), G(700), C('12', 'SIS PROTECTION PANEL (B)', 1400, 600, 2285),
                          C('11', 'DCS I/O PANEL (B)', 700, 600, 2285), C('11', 'DCS RELAY PANEL (B)', 700, 600, 2285), C('10', 'DCS CONTROLLER PANEL (B)', 700, 600, 2285),
                          G(800), C('18', 'HVAC CONTROL PANEL', 1000, 600, 2200)])
    out.append(r)
    return out


# ---------------------------------------------------------------- Amiral (19VA-00GEN00-J28-0001 R3)
def amiral():
    P, D = 'Amiral', '19VA-00GEN00-J28-0001 R3'
    out = []
    r = Room('amr-ccr', P, D, 'Central Control Room (303)', 15300, 8700, '콘솔 한 줄 → 대형 화면 2,000 · 뒷줄 데스크 1,800 위 · 프린터는 양쪽 벽')
    r.row(100, 300, 90, [PRN('26', 'SPARE (26)'), PRN('23', 'SHIFT ENGINEER COLOR PRINTER'), PRN('22', 'CCTV COLOR PRINTER')])
    r.row(100, 5550, 90, [PRN('21', 'DCS COLOR PRINTER'), PRN('30', 'WATER SYSTEM COLOR PRINTER'), PRN('28', 'AUX.BOILER COLOR PRINTER')])
    r.row(14400, 4600, 270, [PRN('25', 'FA COLOR PRINTER'), PRN('24', 'HVAC COLOR PRINTER'), PRN('29', 'ECMS COLOR PRINTER'), PRN('27', 'STG COLOR PRINTER'),
                             PRN('20', 'GTG COLOR PRINTER')])
    r.row(3329, 1800, 0, [OWS('18', 'SPARE (18)', 800, 1100, 750), OWS('12', 'CCTV WORKSTATION', 1200, 1100, 750), OWS('13', 'SHIFT ENGINEER OWS', 1200, 1100, 750), G(850),
                          OWS('14', 'LARGE SCREEN CONTROLLER', 800, 1100, 750), OWS('15', 'SPARE (15)', 800, 1100, 750), OWS('16', 'HVAC WORKSTATION', 800, 1100, 750),
                          OWS('17', 'FA WORKSTATION', 800, 1100, 750)])
    r.row(1900, 4960, 0, [OWS('10', 'WATER SYSTEM WORKSTATION', 1200, 1100, 750), OWS('8', 'AUX BOILER OWS', 1200, 1100, 750), G(200),
                          OWS('5-1', 'DCS OWS 1', 1200, 1100, 750), OWS('5-2', 'DCS OWS 2', 1200, 1100, 750), OWS('5-3', 'DCS OWS 3', 1200, 1100, 750),
                          OWS('11', 'EMERGENCY PUSH BUTTON STATION', 850, 1100, 750), OWS('6', 'GTG OWS', 1200, 1100, 750), OWS('7', 'STG OWS', 1200, 1100, 750),
                          OWS('9', 'ECMS OWS', 1200, 1100, 750)])
    r.row(5660, 8000, 0, [C('1', 'LARGE SCREEN (75")', 75, 600, 0)])
    r.row(8500, 8000, 0, [C('1', 'LARGE SCREEN (75")', 75, 600, 0)])
    out.append(r)

    r = Room('amr-er', P, D, 'Electronic Room (302)', 8400, 6800, '두 줄 앞면끼리 마주 봄 — 통로 1,700 · 뒤 1,400~1,500')
    r.row(1630, 1500, 180, [C('61', 'DCS POWER DIST. PANEL', 700, 600, 2285), G(450), C('62', 'DCS CTRL & RELAY PANEL', 700, 600, 2285),
                            C('64', 'DCS OPC PANEL', 700, 600, 2285), C('67', 'DCS NETWORK PANEL', 700, 600, 2285), G(500),
                            C('73', 'FDM/PCM CABINET (BY OWNER)', 810, 1000, 1300)])
    r.row(2030, 3800, 0, [C('65', 'DCS INTERFACE SERVER PANEL (PI/FTP)', 700, 1000, 2285), C('66', 'DCS HISTORIAN SERVER PANEL', 700, 1000, 2285),
                          C('68', 'CYBER SECURITY SERVER PANEL (PWCS)', 700, 1000, 2285), G(500), C('69', 'GT TCS NETWORK PANEL', 860, 600, 2310),
                          C('70', 'GT GMS PANEL', 800, 800, 2350), C('71', 'ST TCS NETWORK PANEL', 800, 800, 2008), C('78', 'ECMS COMMUNICATION PANEL', 800, 800, 2200)])
    r.row(300, 5000, 90, [C('75', 'HVAC CONTROL PANEL', 1200, 800, 2100)])
    out.append(r)

    r = Room('amr-eng', P, D, 'Engineering Room (301)', 12900, 6800, '위 · 아래 벽 데스크 줄(벽에서 650 / 460) · 프린터는 왼쪽 벽')
    r.row(1700, 650, 180, [OWS('38', 'STG EWS', 1200, 1100, 750), OWS('39', 'GTG EWS', 1200, 1100, 750), OWS('40', 'GTG OPC SERVER 1~2', 1200, 1100, 750), G(600),
                           OWS('41', 'GTG ACS WORKSTATION 1~2', 1200, 1100, 750), OWS('42', 'GTG CPFA WORKSTATION', 800, 1100, 750),
                           OWS('43', 'GTG DFPC WORKSTATION', 800, 1100, 750), OWS('44', 'SPARE (44)', 800, 1100, 750)])
    r.row(1700, 5240, 0, [OWS('31', 'DCS EWS', 1200, 1100, 750), OWS('32', 'AMS WORKSTATION', 800, 1100, 750), OWS('33', 'PPMS WORKSTATION', 800, 1100, 750), G(600),
                          OWS('34', 'CEMS WORKSTATION', 800, 1100, 750), OWS('35', 'ECMS EWS', 1200, 1100, 750), OWS('36', 'SPARE (36)', 800, 1100, 750)])
    r.row(100, 1700, 90, [PRN('55', 'SPARE (55)'), PRN('54', 'STG COLOR PRINTER'), PRN('52', 'CEMS COLOR PRINTER'), PRN('51', 'ECMS COLOR PRINTER'),
                          PRN('50', 'DCS COLOR PRINTER')])
    out.append(r)
    return out


# ---------------------------------------------------------------- QFE (1A1Y-00GEN00-J28-0001 R0)
def qfe():
    P, D = 'QFE', '1A1Y-00GEN00-J28-0001 R0'
    out = []
    r = Room('qfe-er', P, D, 'Electronic Equip. & Cabinet Room (213)', 16600, 6650, '긴 두 줄 앞면끼리 마주 봄 — 통로 1,700 · 뒤 1,300 / 1,650')
    r.row(1610, 1300, 180, [C('1', 'SERVER RACK GT OPC-1', 1100, 600, 2085), C('2', 'SERVER RACK GT OPC-2', 1100, 600, 2085),
                            C('3', 'NETWORK PROTECTION PACK (NPP)', 700, 617, 1200), C('4', 'NSGW-1', 600, 600, 2085), C('5', 'NSGW-2', 600, 600, 2085),
                            C('6', 'SPARE', 600, 600, 2085), C('7', 'METERING DATA ACQUISITION SYSTEM (MDAS) PANEL', 800, 1000, 2100),
                            C('8', 'ST NETWORK CABINET-1', 800, 800, 2300), C('9', 'ST NETWORK CABINET-2', 800, 800, 2300), C('10', 'GT NETWORK CABINET-1', 800, 800, 2085),
                            C('11', 'GT NETWORK CABINET-2', 800, 800, 2085), C('12', 'GT VMS CABINET-1', 800, 800, 2085), C('13', 'GT VMS CABINET-2', 800, 800, 2085),
                            C('14', 'VMS SERVER CABINET', 800, 800, 2310), C('15', 'BILL', 800, 800, 2085), C('16', 'HVAC NETWORK PANEL', 1000, 600, 2100)])
    r.row(3670, 4000, 0, [C('17', 'DCS-CYBER SECURITY PANEL', 700, 1000, 2285), C('18', 'DCS-REDUNDANT HISTORIAN CABINET', 700, 1000, 2285),
                          C('19', 'DCS-OPC CABINET #2', 700, 600, 2285), C('20', 'DCS-OPC CABINET #1', 700, 600, 2285),
                          C('21', 'DCS-NETWORK INTERFACE PANEL #3', 700, 600, 2285), C('22', 'DCS-NETWORK INTERFACE PANEL #2', 700, 600, 2285),
                          C('23', 'DCS-NETWORK INTERFACE PANEL #1', 700, 600, 2285), C('24', 'DCS-INTERPOSING RELAY CABINET FOR ELEC MEB', 700, 600, 2285),
                          C('25', 'DCS-I/O EXTENDED CABINET-2 FOR ELEC MEB', 700, 600, 2285), C('26', 'DCS-I/O EXTENDED CABINET-1 FOR ELEC MEB', 700, 600, 2285),
                          C('27', 'DCS-CONTROLLER CABINET FOR ELEC MEB', 700, 600, 2285), C('28', 'DCS-INTERPOSING RELAY CABINET FOR BOP MEB', 700, 600, 2285),
                          C('29', 'DCS-I/O EXTENDED CABINET-1 FOR BOP MEB', 700, 600, 2285), C('30', 'DCS-CONTROLLER CABINET FOR BOP MEB', 700, 600, 2285),
                          C('31', 'DCS-POWER DISTRIBUTION PANEL #2', 800, 600, 2285), C('32', 'DCS-POWER DISTRIBUTION PANEL #1', 800, 600, 2285)])
    out.append(r)

    r = Room('qfe-ccr', P, D, 'Central Control Room (215)', 18600, 13750, '앞 콘솔(양 끝 곡선 → 곧게 폄) ↔ LVS 100" · 뒷줄 데스크 5,300 위(그룹 사이 850) · 프린터 위 벽 · 왼쪽 벽')
    r.row(6870, 100, 180, [PRN('37', 'DCS COLOR PRINTER #1 FOR BLOCK #10'), PRN('38', 'DCS COLOR PRINTER #2 FOR BLOCK #10'), PRN('39', 'SPARE PRINTER-1', 800, 600),
                           PRN('40', 'SPARE PRINTER-2', 800, 600), PRN('41', 'CCTV PRINTER', 800, 600), PRN('42', 'FIRE DETECTION AND ALARM SYSTEM PRINTER', 800, 600),
                           PRN('43', 'SUBSTATION CONTROL SYSTEM PRINTER', 800, 600), PRN('44', 'FAULT MONITORING SYSTEM PRINTER', 800, 600),
                           PRN('45', 'HVAC SYSTEM PRINTER', 800, 600), PRN('46', 'MDAS PRINTER', 800, 600), G(130),
                           C('52', 'HVAC CONTROL PANEL', 1600, 800, 2100), C('50', "FIRE FIGHTER'S CONTROL PANEL", 800, 800, 2100)])
    r.row(100, 590, 90, [PRN('32', 'DCS-COLOR PRINTER #1 FOR COMMON'), PRN('33', 'DCS COLOR PRINTER #1 FOR BLOCK #20')])
    r.row(100, 4270, 90, [PRN('34', 'DCS COLOR PRINTER #2 FOR BLOCK #20'), PRN('35', 'GTG PRINTER FOR POWER BLOCK #20', 800, 600),
                          PRN('36', 'STG PRINTER FOR POWER BLOCK #20', 800, 600)])
    r.row(4900, 5300, 0, [OWS('20', 'SPARE DUAL DESK-1', 1200, 1100, 750), OWS('21', 'PA CALL STATION', 850, 1100, 750), OWS('22', 'CCTV OWS', 1200, 1100, 750),
                          OWS('23', 'SUBSTATION CONTROL SYSTEM OWS', 850, 1100, 750), OWS('24', 'FAULT MONITORING SYSTEM OWS', 1200, 1100, 750),
                          OWS('25', 'HVAC SYSTEM OWS', 850, 1100, 750), OWS('26', 'MDAS OWS', 1200, 1100, 750), OWS('27', 'SPARE DUAL DESK-2', 1200, 1100, 750),
                          OWS('28', 'FIRE DETECTION AND ALARM SYSTEM OWS', 850, 1100, 750)])
    r.row(2000, 6100, 90, [OWS('1', 'STG OWS-1 FOR POWER BLOCK #20', 1200, 1100, 750), OWS('2', 'STG OWS-2 FOR POWER BLOCK #20', 1200, 1100, 750),
                           OWS('4', 'GTG OWS-1 FOR POWER BLOCK #20', 1200, 1100, 750), OWS('5', 'GTG OWS-2 FOR POWER BLOCK #20', 1200, 1100, 750)])
    r.row(4150, 10900, 0, [OWS('6', 'HRSG LEVEL INDICATOR UNIT #22', 858, 924, 750), OWS('7', 'DCS-OPERATOR WORKSTATION #1 FOR BLOCK #20', 1200, 1100, 750),
                           OWS('8', 'DCS-OPERATOR WORKSTATION #2 FOR BLOCK #20', 1200, 1100, 750), OWS('9', 'OWS-1 FOR RO DESAL PLANT', 1200, 1100, 750),
                           OWS('10', 'OWS-2 FOR RO DESAL PLANT', 1200, 1100, 750), OWS('11', 'DCS-OPERATOR WORKSTATION FOR COMMON', 1200, 1100, 750),
                           OWS('12', 'DCS-OPERATOR WORKSTATION #1 FOR BLOCK #10', 1200, 1100, 750), OWS('13', 'DCS-OPERATOR WORKSTATION #2 FOR BLOCK #10', 1200, 1100, 750),
                           OWS('14', 'AUX CONSOLE (BOP EPB & HRSG LEVEL INDICATOR #12)', 858, 924, 750)])
    r.row(15800, 6500, 270, [OWS('19', 'STG OWS-2 FOR POWER BLOCK #10', 1200, 1100, 750), OWS('18', 'STG OWS-1 FOR POWER BLOCK #10', 1200, 1100, 750),
                             OWS('17', 'AUX CONSOLE (GTG/STG EPB #1 & HRSG LEVEL #11)', 858, 924, 750), OWS('16', 'GTG OWS-2 FOR POWER BLOCK #10', 1200, 1100, 750),
                             OWS('15', 'GTG OWS-1 FOR POWER BLOCK #10', 1200, 1100, 750)])
    r.row(1900, 13050, 0, [C('29', 'LVS FOR POWER BLOCK #20', 100, 600, 0)])
    r.row(8200, 13050, 0, [C('30', 'LVS FOR COMMON', 100, 600, 0)])
    r.row(13500, 13050, 0, [C('31', 'LVS FOR POWER BLOCK #10', 100, 600, 0)])
    out.append(r)

    r = Room('qfe-eng1', P, D, 'Engineer Room-1 (216)', 12200, 5450, '위 벽 프린터 + 데스크, 아래 벽 데스크 줄 — 의자 통로 ≈2,000')
    r.row(955, 100, 180, [PRN('13', 'DCS-COLOR PRINTER #3 FOR COMMON'), PRN('14', 'DCS-COLOR PRINTER #4 FOR COMMON'), PRN('15', 'CEMS PRINTER', 800, 600),
                          PRN('16', 'VMS PRINTER', 800, 600), PRN('17', 'SPARE PRINTER-4', 800, 600), G(1000),
                          OWS('1', 'SOE OWS', 1200, 1100, 750), OWS('2', 'FAULT MONITORING SYSTEM OWS', 1200, 1100, 750), OWS('3', 'VMS OWS', 1200, 1100, 750),
                          OWS('4', 'CEMS OWS', 1200, 1100, 750)])
    r.row(2600, 4250, 0, [OWS('5', 'CMMS OWS', 1200, 1100, 750), OWS('6', 'PMS OWS', 1200, 1100, 750), OWS('7', 'OWS FOR CYBER SECURITY SYSTEM', 1200, 1100, 750),
                          OWS('8', 'DCS-PRI. ASSET MANAGEMENT SYSTEM', 1200, 1100, 750), OWS('9', 'DCS-SEC. ASSET MANAGEMENT SYSTEM', 1200, 1100, 750),
                          OWS('10', 'BOP EWS-1 FOR COMMON', 1200, 1100, 750), OWS('11', 'BOP EWS-2 FOR COMMON', 1200, 1100, 750),
                          OWS('12', 'SPARE SINGLE DESK-1', 850, 1100, 750)])
    out.append(r)

    r = Room('qfe-eng2', P, D, 'Engineer Room-2 & Computer Room (217)', 12400, 5000, '위 · 아래 벽 데스크 줄 · 프린터 오른쪽 벽')
    r.row(100, 100, 180, [OWS('1', 'GTG OPC SERVER FOR POWER BLOCK #10', 1200, 1100, 750), OWS('2', 'GTG OPC SERVER FOR POWER BLOCK #20', 1200, 1100, 750),
                          OWS('3', 'GTG VAS FOR POWER BLOCK #20', 850, 1100, 750), OWS('4', 'GTG ACS-2 FOR POWER BLOCK #20', 1200, 1100, 750),
                          OWS('5', 'GTG ACS-1 FOR POWER BLOCK #20', 1200, 1100, 750), OWS('6', 'GTG OPFA-2 FOR POWER BLOCK #20', 850, 1100, 750),
                          PRN('7', 'SPARE PRINTER-3')])
    r.row(11500, 600, 270, [PRN('14', 'GTG PRINTER FOR POWER BLOCK #10', 800, 600), PRN('15', 'GTG PRINTER FOR POWER BLOCK #20', 800, 600),
                            PRN('16', 'STG PRINTER-2', 800, 600)])
    r.row(3080, 3800, 0, [OWS('17', 'GTG VAS FOR POWER BLOCK #10', 850, 1100, 750), OWS('18', 'GTG ACS-1 FOR POWER BLOCK #10', 1200, 1100, 750),
                          OWS('19', 'GTG ACS-2 FOR POWER BLOCK #10', 1200, 1100, 750), OWS('20', 'GTG OPFA-1 FOR POWER BLOCK #10', 850, 1100, 750),
                          OWS('21', 'GTG OPFA-2 FOR POWER BLOCK #10', 850, 1100, 750), OWS('22', 'STG HIS FOR POWER BLOCK #10', 1200, 1100, 750),
                          OWS('23', 'STG VAS FOR COMMON', 850, 1100, 750), OWS('24', 'STG EWS FOR POWER BLOCK #10', 1200, 1100, 750), PRN('25', 'STG PRINTER-1', 800, 600)])
    out.append(r)
    return out


# ---------------------------------------------------------------- UAD (1A5J-00GEN00-J28-0001 R3)
def uad():
    P, D = 'UAD', '1A5J-00GEN00-J28-0001 R3'
    out = []
    r = Room('uad-ccr', P, D, 'Central Control Room', 11800, 14300, '콘솔 세로 한 줄(운전원 왼쪽) ↔ 75" 화면 2,000 · 둘째 데스크 줄 2,900 뒤 · 프린터 왼쪽 벽')
    r.row(100, 1520, 90, [PRN('24', 'CEMS PRINTER', 800, 800), PRN('25', 'FIRE DETECTION & ALARM SYSTEM PRINTER'), PRN('26', 'BMS PRINTER')])
    r.row(100, 7070, 90, [PRN('27', 'OOS PRINTER 1'), PRN('28', 'OOS PRINTER 2'), PRN('29', 'GT PRINTER 1 FOR GTG #11 & GTG #12'), PRN('30', 'GT PRINTER 2 FOR GTG #13 & GTG #14'),
                          PRN('31', 'ECMS PRINTER'), PRN('32', 'EDL SCANNER')])
    r.row(3200, 300, 180, [C('1', 'MAIN SMOKE CONTROL PANEL', 560, 400, 960)])
    r.row(5200, 1610, 180, [OWS('4', 'ECMS OWS 1', 800), OWS('5', 'ECMS OWS 2', 800)])
    r.row(9400, 300, 180, [C('2', 'FF PANEL', 800, 800, 2600), C('3', 'TMS COMMUNICATION CUBICLE', 800, 800, 2200)])
    r.row(6800, 2800, 270, [OWS('6', 'OOS OWS 1'), OWS('7', 'OOS OWS 2'), OWS('8', 'OOS OWS 3'), OWS('9', 'OOS OWS 4'),
                            OWS('10', 'GT OWS 1 FOR GTG #11 & GTG #12'), OWS('11', 'GT OWS 2 FOR GTG #11 & GTG #12'), OWS('12', 'GT OWS 3 FOR GTG #13 & GTG #14'),
                            OWS('13', 'GT OWS 4 FOR GTG #13 & GTG #14')])
    r.row(3670, 5100, 270, [OWS('18', 'OOS LARGE SCREEN WORKSTATION', 800), OWS('19', 'REMOTE MICROPHONE / PA', 800), OWS('20', 'FIRE DETECTION & ALARM SYSTEM OWS', 800),
                            OWS('21', 'BMS OWS', 800), OWS('22', 'CEMS OWS', 800), OWS('23', 'EDL CLIENT', 800)])
    r.row(4390, 12500, 0, [OWS('16', 'CCTV WORKSTATION', 800), OWS('15', 'GENERATOR MONITORING SYSTEM WORKSTATION', 800), OWS('14', 'GT ADA WORKSTATION', 800)])
    r.row(9900, 5900, 270, [C('33', 'LARGE SCREEN', 75, 600, 0)])
    r.row(9900, 7700, 270, [C('34', 'LARGE SCREEN', 75, 600, 0)])
    out.append(r)

    r = Room('uad-eng', P, D, 'Engineering Room', 10700, 6000, '위 벽 데스크 줄(벽에서 330) · 아래 벽 프린터 줄 — 사이 ≈3,700')
    r.row(500, 330, 180, [OWS('41', 'OOS PPMS', 800), OWS('42', 'OOS EWS 1'), OWS('43', 'OOS EWS 2'), OWS('44', 'GT EWS 1 FOR GTG #11 & GTG #12', 800),
                          OWS('45', 'GT EWS 2 FOR GTG #11 & GTG #12', 800), OWS('46', 'GT EWS 3 FOR GTG #13 & GTG #14', 800), OWS('47', 'GT EWS 4 FOR GTG #13 & GTG #14', 800),
                          OWS('48', 'ECMS EWS', 800), OWS('49', 'VMS EWS', 800)])
    r.row(500, 5100, 0, [PRN('50', 'GT PRINTER 1 FOR GTG #11 & GTG #12'), PRN('51', 'GT PRINTER 2 FOR GTG #13 & GTG #14'), PRN('52', 'OOS PRINTER 1'),
                         PRN('53', 'OOS PRINTER 2'), PRN('54', 'ECMS PRINTER'), PRN('55', 'VMS PRINTER')])
    out.append(r)

    r = Room('uad-er', P, D, 'Electronic Room', 9400, 5460, '두 줄 앞면끼리 마주 봄(도어 궤적 사이) — 통로 ≈1,750 · 크기는 치수선에서 (목록 없음)')
    r.row(800, 400, 180, [C(str(i), 'ELECTRONIC ROOM CABINET', 700, 800, 2200) for i in (62, 63, 64, 65, 66, 67)] + [G(636)] +
          [C(str(i), 'ELECTRONIC ROOM CABINET', 780, 800, 2200) for i in (68, 69, 70)])
    r.row(800, 2960, 0, [C(str(i), 'ELECTRONIC ROOM CABINET', 812, 1000, 2200) for i in (71, 72, 73)] + [C('74', 'ELECTRONIC ROOM CABINET', 800, 1000, 2200), G(1400)] +
          [C(str(i), 'ELECTRONIC ROOM CABINET', 800, 1000, 2200) for i in (75, 76, 77)])
    out.append(r)
    return out


REFS = [f3, nt34, tanajib, amiral, qfe, uad]

# ---------------------------------------------------------------- 학습: Ref 배치에서 거리 통계
def body(p, t):
    sw = p['rot'] % 180 == 0
    w = t['w'] if t['kind'] != 'screen' else round(t['tileIn'] * 25.4 * 0.8716 + 80)
    bw, bh = (w, t['d']) if sw else (t['d'], w)
    return p['x'], p['y'], bw, bh


def learn(rooms):
    S = {'deskRowN': [], 'cabFace': [], 'cabFR': [], 'cabWallEnd': [], 'deskScreen': [], 'deskFace': [], 'deskWall': [], 'groupGap': [], 'prnWall': [], 'rowMax': []}
    for r in rooms:
        d = r.data(); T = {t['id']: t for t in d['types']}; W, L = d['room']['w'], d['room']['l']
        ps = [(p, T[p['type']], body(p, T[p['type']])) for p in d['panels']]
        kind = lambda t: 'ls' if t['kind'] == 'screen' else 'ows' if t['kind'] == 'desk' else 'prn' if t['door'] == 'none' else 'cab'
        # 같은 방향 · 같은 앞줄 = 한 줄
        rows = {}
        for p, t, b in ps:
            k = kind(t)
            if k in ('ls',):
                continue
            hz = p['rot'] % 180 == 0
            front = (b[1] if p['rot'] == 0 else b[1] + b[3]) if hz else (b[0] + b[2] if p['rot'] == 90 else b[0])
            rows.setdefault((k, p['rot'], round(front / 50)), []).append((p, t, b))
        for (k, rot, _), items in rows.items():
            hz = rot % 180 == 0
            items.sort(key=lambda z: z[2][0] if hz else z[2][1])
            a = items[0][2]; z = items[-1][2]
            lo, hi = (a[0], z[0] + z[2]) if hz else (a[1], z[1] + z[3])
            S['rowMax'].append(hi - lo) if k == 'cab' else None
            if k == 'cab':
                S['cabWallEnd'] += [lo, (W if hz else L) - hi]
            for i in range(1, len(items)):
                b0, b1 = items[i - 1][2], items[i][2]
                g = (b1[0] - (b0[0] + b0[2])) if hz else (b1[1] - (b0[1] + b0[3]))
                if g > 150:
                    S['groupGap'].append(g)
            if k == 'ows':
                S['deskRowN'].append(len(items))
            if k in ('ows', 'prn'):
                # 벽까지 (등 쪽)
                b = a
                back = {0: L - (b[1] + b[3]), 180: b[1], 90: b[0], 270: W - (b[0] + b[2])}[rot]
                (S['deskWall'] if k == 'ows' else S['prnWall']).append(back)
        # 마주 보는 줄 / 앞 ↔ 뒤
        keys = list(rows.keys())
        for i in range(len(keys)):
            for j in range(len(keys)):
                (k1, r1, f1), (k2, r2, f2) = keys[i], keys[j]
                if i >= j or k1 != k2 or r1 % 180 != r2 % 180:
                    continue
                A, B = rows[keys[i]], rows[keys[j]]
                hz = r1 % 180 == 0
                ra = (min(b[1] for _, _, b in A), max(b[1] + b[3] for _, _, b in A)) if hz else (min(b[0] for _, _, b in A), max(b[0] + b[2] for _, _, b in A))
                rb = (min(b[1] for _, _, b in B), max(b[1] + b[3] for _, _, b in B)) if hz else (min(b[0] for _, _, b in B), max(b[0] + b[2] for _, _, b in B))
                oa = (min(b[0] for _, _, b in A), max(b[0] + b[2] for _, _, b in A)) if hz else (min(b[1] for _, _, b in A), max(b[1] + b[3] for _, _, b in A))
                ob = (min(b[0] for _, _, b in B), max(b[0] + b[2] for _, _, b in B)) if hz else (min(b[1] for _, _, b in B), max(b[1] + b[3] for _, _, b in B))
                if min(oa[1], ob[1]) - max(oa[0], ob[0]) < 500:
                    continue
                gap = rb[0] - ra[1] if rb[0] >= ra[1] else ra[0] - rb[1]
                if gap <= 0 or gap > 6000:
                    continue
                first, second = (keys[i], keys[j]) if rb[0] >= ra[1] else (keys[j], keys[i])
                # first = 위/왼쪽 줄. 앞면 마주 봄 = first 앞이 아래/오른쪽 + second 앞이 위/왼쪽
                fdown = first[1] in (180, 90); sup = second[1] in (0, 270)
                if k1 == 'cab':
                    (S['cabFace'] if fdown and sup else S['cabFR']).append(gap)
                elif k1 == 'ows' and fdown and sup:
                    S['deskFace'].append(gap)
        # 콘솔 ↔ 대형 화면
        for p, t, b in ps:
            if t['kind'] != 'screen':
                continue
            best = None
            for q, u, c in ps:
                if u['kind'] != 'desk':
                    continue
                if p['rot'] % 180 == 0:
                    if min(b[0] + b[2], c[0] + c[2]) - max(b[0], c[0]) < -1500:
                        continue
                    g = b[1] - (c[1] + c[3]) if b[1] > c[1] else c[1] - (b[1] + b[3])
                else:
                    if min(b[1] + b[3], c[1] + c[3]) - max(b[1], c[1]) < -1500:
                        continue
                    g = b[0] - (c[0] + c[2]) if b[0] > c[0] else c[0] - (b[0] + b[2])
                if g > 0 and (best is None or g < best):
                    best = g
            if best:
                S['deskScreen'].append(best)
    out = {}
    for k, v in S.items():
        v = [x for x in v if x is not None and x >= 0]
        if v:
            v.sort(); out[k] = {'n': len(v), 'min': round(min(v)), 'med': round(statistics.median(v)), 'p75': round(v[min(len(v) - 1, int(len(v) * 0.75))]), 'max': round(max(v))}
    return out


def room_kind(r):
    ks = [('ls' if t['kind'] == 'screen' else 'desk' if t['kind'] == 'desk' else 'prn' if t['door'] == 'none' else 'cab') for p in r.panels for t in [next(x for x in r.types.values() if x['id'] == p['type'])]]
    if 'ls' in ks: return 'ccr'
    return 'eng' if ks.count('desk') > ks.count('cab') else 'er'


def find_rules(rooms):
    """Ref 배치에서 '어디에 무엇을' 규칙을 셈 (룸 종류별 비율 · 거리)"""
    R = {'ccr': [], 'er': [], 'eng': []}
    for r in rooms:
        R[room_kind(r)].append(r)
    out = []
    def kind(t): return 'ls' if t['kind'] == 'screen' else 'desk' if t['kind'] == 'desk' else 'prn' if t['door'] == 'none' else 'cab'
    def boxes(r):
        d = r.data(); T = {t['id']: t for t in d['types']}
        return d['room']['w'], d['room']['l'], [(p, T[p['type']], kind(T[p['type']]), body(p, T[p['type']])) for p in d['panels']]
    def wall_of(b, W, L):   # 가장 가까운 벽과 그 벽이 긴 벽인지
        ds = {'top': b[1], 'bottom': L - b[1] - b[3], 'left': b[0], 'right': W - b[0] - b[2]}
        w = min(ds, key=ds.get); long_hz = W >= L
        return w, ds[w], (w in ('top', 'bottom')) == long_hz
    # CCR: 대형 화면 = 긴 벽, 콘솔은 화면 벽과 나란히
    n = sum(1 for r in R['ccr'] for p, t, k, b in boxes(r)[2] if k == 'ls')
    lw = sum(1 for r in R['ccr'] for W, L, B in [boxes(r)] for p, t, k, b in B if k == 'ls' and wall_of(b, W, L)[2])
    out.append({'id': 'ccr.screenLongWall', 'kind': 'ccr', 'v': round(lw / max(n, 1), 2), 'text': f'CCR 대형 화면은 긴 벽 쪽 ({lw}/{n})'})
    par = tot = 0
    for r in R['ccr']:
        W, L, B = boxes(r)
        sr = [p['rot'] % 180 for p, t, k, b in B if k == 'ls']
        if not sr: continue
        for p, t, k, b in B:
            if k == 'desk':
                tot += 1; par += 1 if p['rot'] % 180 == sr[0] else 0
    out.append({'id': 'ccr.consoleParallel', 'kind': 'ccr', 'v': round(par / max(tot, 1), 2), 'text': f'CCR 데스크는 화면과 같은 방향(나란히) ({par}/{tot})'})
    # ER: 판넬 줄이 실의 긴 쪽을 따라감 (길이 가중)
    al = tl = 0
    for r in R['er']:
        W, L, B = boxes(r)
        for p, t, k, b in B:
            if k != 'cab': continue
            along = (p['rot'] % 180 == 0) == (W >= L)
            tl += b[2] if p['rot'] % 180 == 0 else b[3]; al += (b[2] if p['rot'] % 180 == 0 else b[3]) if along else 0
    out.append({'id': 'er.rowsAlongLong', 'kind': 'er', 'v': round(al / max(tl, 1), 2), 'text': f'ER 판넬 줄은 실의 긴 쪽을 따라감 (줄 길이의 {round(al / max(tl, 1) * 100)}%)'})
    # 엔지니어링: 데스크는 긴 벽에 붙음 (벽에서 1,000 이내)
    nw = nd = 0
    for r in R['eng']:
        W, L, B = boxes(r)
        for p, t, k, b in B:
            if k != 'desk': continue
            w, dist, lng = wall_of(b, W, L); nd += 1; nw += 1 if dist <= 1000 and lng else 0
    out.append({'id': 'eng.desksLongWall', 'kind': 'eng', 'v': round(nw / max(nd, 1), 2), 'text': f'엔지니어링 룸 데스크는 긴 벽에 붙여 마주 봄 ({nw}/{nd})'})
    # 프린터: 벽에서 500 이내
    np_ = nw2 = 0
    for r in rooms:
        W, L, B = boxes(r)
        for p, t, k, b in B:
            if k != 'prn': continue
            np_ += 1; nw2 += 1 if wall_of(b, W, L)[1] <= 500 else 0
    out.append({'id': 'prn.wall', 'kind': 'all', 'v': round(nw2 / max(np_, 1), 2), 'text': f'프린터는 벽 따라 (벽에서 500 이내 {nw2}/{np_})'})
    # 실 비율 (긴 쪽 / 짧은 쪽)
    for k, rs in R.items():
        ar = sorted(max(r.W, r.L) / min(r.W, r.L) for r in rs)
        if ar:
            out.append({'id': f'{k}.aspect', 'kind': k, 'v': round(statistics.median(ar), 2), 'text': f"{ {'ccr': 'CCR', 'er': 'ER', 'eng': '엔지니어링 룸'}[k]} 실 비율 긴 쪽/짧은 쪽 중앙 {round(statistics.median(ar), 2)} ({round(ar[0], 2)}~{round(ar[-1], 2)}, {len(ar)}곳)"})
    return out, {r.rid: room_kind(r) for r in rooms}


def main():
    rooms = [r for f in REFS for r in f()]
    stats = learn(rooms)
    found, kinds = find_rules(rooms)
    refs = [{'id': r.rid, 'project': r.project, 'doc': r.doc, 'room': r.room, 'kind': kinds[r.rid], 'note': r.note, 'data': r.data()} for r in rooms]
    js = ('/* 판넬 공간확보 — Ref. PJT Room Layout (dashboard_tools/space_ref_build.py 가 만든 파일, 직접 고치지 말 것)\n'
          '   도면 사진에서 사람이 읽어 옮김: 치수 = 도면 치수선 · Equipment List, 자리 = 근사(±200~300 mm), 곡선 콘솔은 곧게 폄.\n'
          '   rules = 이 Ref 들에서 잰 거리 통계(mm) — Option A 자동 배치 시작값. */\n'
          'window.CRSPACE_REF=' + json.dumps({'version': 2, 'rules': stats, 'found': found, 'refs': refs}, ensure_ascii=False, separators=(',', ':')) + ';\n')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(js)
    print(f'{len(rooms)} rooms → {os.path.relpath(OUT)} ({len(js) // 1024} KB)')
    for k, v in stats.items():
        print(f'  {k:11s} {v}')
    for x in found:
        print('  규칙', x['id'], x['v'], x['text'])


if __name__ == '__main__':
    main()
