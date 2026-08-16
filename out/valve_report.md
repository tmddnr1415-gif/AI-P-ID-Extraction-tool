# Spike 4 - valve detection

Rules are derived from legend pages 2 (LINE VALVES, VALVE OPERATION),
3 (VALVES ACTUATORS) and 4 (VALVE BODY WITH ACTUATOR); see the module
docstring in `spike/detect_valves.py` for each citation.

## 1. Text-anchor reach vs geometry

- valve bodies found on 56 drawings: **2896**
- carrying a tag bubble (MOV / HOV / HV / XV / FCV / ...): **185 (6.4%)**
- reachable by geometry only: **2711 (93.6%)**

Text anchors are not a viable primary route for valves: the tag bubble
is drawn only where a valve is instrumented.  Everything else has to be
found from the symbol.

## 2. Body types found

| body | count |
|---|---:|
| GLOBE | 1360 |
| GATE | 779 |
| BALL | 311 |
| CHECK | 264 |
| BUTTERFLY | 136 |
| DIAPHRAGM | 46 |

## 3. Actuators found

| actuator | count |
|---|---:|
| NONE | 2711 |
| MOTOR | 118 |
| UNREAD | 60 |
| HYDRAULIC | 7 |

`NONE` means no actuator enclosure stands on the stem - a manual valve.
`UNREAD` means an enclosure is there but the letter inside it could not
be named; it is reported rather than guessed.

## 4. Against the valve deliverables

### CZI - CZI_Butterfly_Valve.xlsx (21 rows, family BUTTERFLY)

| drawing | page | excel rows | excel actuators | bodies in family | actuated | detected actuators | unread | delta |
|---|---|---:|---|---:|---:|---|---:|---:|
| D00P-00PAB10-M05-0001 | 26 | 5 | HYDRAULIC 3, MOTOR 2 | 11 | 4 | HYDRAULIC 2, MOTOR 2 | 0 | -1 |
| D00P-00PAB10-M05-0002 | 27 | 5 | HYDRAULIC 3, MOTOR 2 | 8 | 7 | HYDRAULIC 2, MOTOR 5 | 0 | +2 |
| D00P-00PAB10-M05-0003 | 28 | 3 | MOTOR 2, PNEUMATIC 1 | 4 | 3 | MOTOR 3 | 0 | +0 |
| D00P-10PAC10-M05-0001 | 30 | 8 | MOTOR 8 | 14 | 8 | MOTOR 8 | 0 | +0 |
| **total** | | **21** | | | **22** | | | **+1** |

### CZH - CZH_MOV_Gate_Globe.xlsx (63 rows, family GATE/GLOBE)

| drawing | page | excel rows | excel actuators | bodies in family | actuated | detected actuators | unread | delta |
|---|---|---:|---|---:|---:|---|---:|---:|
| D00P-00EGD00-M05-0002 | 33 | 12 | MOTOR 12 | 74 | 16 | MOTOR 16 | 1 | +4 |
| D00P-00GHB10-M05-0001 | 49 | 2 | MOTOR 2 | 63 | 5 | MOTOR 5 | 0 | +3 |
| D00P-00GHC10-M05-0001 | 46,47 | 2 | MOTOR 2 | 157 | 8 | MOTOR 8 | 0 | +6 |
| D00P-00GKB10-M05-0001 | 51 | 1 | MOTOR 1 | 56 | 1 | MOTOR 1 | 0 | +0 |
| D00P-10LBA10-M05-0001 | 6 | 6 | MOTOR 6 | 58 | 7 | MOTOR 7 | 2 | +1 |
| D00P-10LBA30-M05-0001 | 9 | 4 | MOTOR 4 | 57 | 6 | MOTOR 6 | 2 | +2 |
| D00P-10LBC40-M05-0001 | 7 | 4 | MOTOR 4 | 66 | 8 | MOTOR 8 | 0 | +4 |
| D00P-10LBC50-M05-0001 | 8 | 5 | MOTOR 5 | 37 | 6 | MOTOR 6 | 0 | +1 |
| D00P-10LBG10-M05-0001 | 12,15 | 3 | MOTOR 3 | 46 | 4 | MOTOR 4 | 1 | +1 |
| D00P-10LCA10-M05-0001 | 16 | 3 | MOTOR 3 | 77 | 3 | MOTOR 3 | 2 | +0 |
| D00P-10LCM10-M05-0001 | 14 | 2 | MOTOR 2 | 32 | 2 | MOTOR 2 | 0 | +0 |
| D00P-10MAJ10-M05-0001 | 18 | 4 | MOTOR 4 | 16 | 4 | MOTOR 4 | 0 | +0 |
| D00P-10MAN10-M05-0001 | 10 | 3 | MOTOR 3 | 53 | 3 | MOTOR 3 | 1 | +0 |
| D00P-10MAN10-M05-0002 | 11 | 3 | MOTOR 3 | 50 | 3 | MOTOR 3 | 0 | +0 |
| D00P-11LAB00-M05-0001 | 20 | 3 | MOTOR 3 | 99 | 3 | MOTOR 3 | 1 | +0 |
| **total** | | **57** | | | **79** | | | **+22** |

Drawings named by a deliverable but absent from the PDF index:

- CZH: D00P-00EKG10-M05-0004
- CZH: D00P-00GBL10-M05-0001

These are the same title-block mismatches `out/revision_gap.md`
already records from the instrument side, not a detection failure:
page 46's title block reads `D00P-00GHC10-M05-0001` while the
deliverables address it as `D00P-00GBL10-M05-0001`.  That is why the
GHC row above spans pages 46 and 47 and carries both drawings'
valves; it is left uncorrected here on purpose - the drawing number
is the client's to reconcile, not a rule to patch around.

## 5. What this comparison cannot measure

`data/Valve_List_2512xx.xlsx` - the 194-row master with the BODY and
ACTUATOR columns - is not in the repository.  The two files above are
filtered cuts of it (their NO column runs 1..178 with gaps), and neither
carries a body column.  So:

- **GATE vs GLOBE confusion matrix: not measurable.**  CZH files gate and
  globe together under one heading and has no per-row body column, so
  there is no ground truth to confuse against.
- **BUTTERFLY 21: partly measurable.**  CZI's 21 rows are all butterfly,
  so their drawings can be checked for butterfly bodies - but CZI holds
  only the *I&C* butterflies, so a drawing may legitimately carry more
  butterflies than the file lists.
- **SELF ACTING 68: not measurable.**  Those rows are in neither file.
  What is reported instead is how many detected bodies have no actuator
  drawn on the stem at all.
- **ANGLE 70 / BALL 4: not measurable.**  Neither file contains them.

