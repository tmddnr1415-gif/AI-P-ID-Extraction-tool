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
| NONE | 2774 |
| MOTOR | 102 |
| UNREAD | 14 |
| HYDRAULIC | 6 |

`NONE` means no actuator enclosure stands on the stem - a manual valve.
`UNREAD` means an enclosure is there but the letter inside it could not
be named; it is reported rather than guessed.  The two reasons an
enclosure stays unread are different problems, so they are counted
apart:

| unread reason | count | meaning |
|---|---:|---|
| ACT_UNREAD_EMPTY | 12 | enclosure holds no strokes at all - most likely not an actuator |
| ACT_UNREAD_STROKE | 2 | strokes are there but match no signature in `valves.stroked_letters` |

## 4. Against the valve deliverables

### CZI - CZI_Butterfly_Valve.xlsx (21 rows, family BUTTERFLY)

| drawing | page | excel rows | excel actuators | bodies in family | actuated | detected actuators | unread | delta |
|---|---|---:|---|---:|---:|---|---:|---:|
| D00P-00PAB10-M05-0001 | 26 | 5 | HYDRAULIC 3, MOTOR 2 | 11 | 4 | HYDRAULIC 2, MOTOR 2 | 0 | -1 |
| D00P-00PAB10-M05-0002 | 27 | 5 | HYDRAULIC 3, MOTOR 2 | 8 | 7 | HYDRAULIC 2, MOTOR 5 | 0 | +2 |
| D00P-00PAB10-M05-0003 | 28 | 3 | MOTOR 2, PNEUMATIC 1 | 4 | 3 | MOTOR 3 | 0 | +0 |
| D00P-10PAC10-M05-0001 | 30 | 8 | MOTOR 8 | 14 | 8 | MOTOR 8 | 0 | +0 |
| **total** | | **21** | | | **22** | | | **+1** |

### CZH - CZH_MOV_Gate_Globe.xlsx (63 rows, family GATE/GLOBE/BALL)

| drawing | page | excel rows | excel actuators | bodies in family | actuated | detected actuators | unread | delta |
|---|---|---:|---|---:|---:|---|---:|---:|
| D00P-00EGD00-M05-0002 | 33 | 12 | MOTOR 12 | 120 | 12 | MOTOR 12 | 0 | +0 |
| D00P-00GHB10-M05-0001 | 49 | 2 | MOTOR 2 | 64 | 2 | MOTOR 2 | 0 | +0 |
| D00P-00GHC10-M05-0001 | 46,47 | 2 | MOTOR 2 | 161 | 4 | MOTOR 4 | 0 | +2 |
| D00P-00GKB10-M05-0001 | 51 | 1 | MOTOR 1 | 58 | 1 | MOTOR 1 | 0 | +0 |
| D00P-10LBA10-M05-0001 | 6 | 6 | MOTOR 6 | 60 | 8 | MOTOR 8 | 0 | +2 |
| D00P-10LBA30-M05-0001 | 9 | 4 | MOTOR 4 | 57 | 6 | MOTOR 6 | 0 | +2 |
| D00P-10LBC40-M05-0001 | 7 | 4 | MOTOR 4 | 66 | 8 | MOTOR 8 | 0 | +4 |
| D00P-10LBC50-M05-0001 | 8 | 5 | MOTOR 5 | 37 | 6 | MOTOR 6 | 0 | +1 |
| D00P-10LBG10-M05-0001 | 12,15 | 3 | MOTOR 3 | 46 | 4 | MOTOR 4 | 0 | +1 |
| D00P-10LCA10-M05-0001 | 16 | 3 | MOTOR 3 | 77 | 3 | MOTOR 3 | 0 | +0 |
| D00P-10LCM10-M05-0001 | 14 | 2 | MOTOR 2 | 32 | 2 | MOTOR 2 | 0 | +0 |
| D00P-10MAJ10-M05-0001 | 18 | 4 | MOTOR 4 | 16 | 4 | MOTOR 4 | 0 | +0 |
| D00P-10MAN10-M05-0001 | 10 | 3 | MOTOR 3 | 53 | 3 | MOTOR 3 | 0 | +0 |
| D00P-10MAN10-M05-0002 | 11 | 3 | MOTOR 3 | 50 | 3 | MOTOR 3 | 0 | +0 |
| D00P-11LAB00-M05-0001 | 20 | 3 | MOTOR 3 | 99 | 3 | MOTOR 3 | 0 | +0 |
| **total** | | **57** | | | **69** | | | **+12** |

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

## 5. Failure types

Counted over the drawings the two deliverables name, so the two
`ACT_UNREAD_*` rows are zero here whenever every unread enclosure
in the document sits on some other drawing; section 3 counts those
document-wide.

| type | count |
|---|---:|
| DRAWING_NO_MISMATCH | 2 |
| ANNOTATION_TEXT | 7 |
| ACT_UNREAD_STROKE | 0 |
| ACT_UNREAD_EMPTY | 0 |
| ACT_MISSING | 1 |
| DELIVERABLE_SCOPE | 14 |

| deliverable | drawing | pages | delta | reasons |
|---|---|---|---:|---|
| CZI | D00P-00PAB10-M05-0001 | 26 | -1 | ACT_MISSING x1, ANNOTATION_TEXT |
| CZI | D00P-00PAB10-M05-0002 | 27 | +2 | ANNOTATION_TEXT, DELIVERABLE_SCOPE x2 |
| CZH | D00P-00GHB10-M05-0001 | 49 | +0 | ANNOTATION_TEXT |
| CZH | D00P-00GHC10-M05-0001 | 46,47 | +2 | ANNOTATION_TEXT, DELIVERABLE_SCOPE x2 |
| CZH | D00P-10LBA10-M05-0001 | 6 | +2 | DELIVERABLE_SCOPE x2 |
| CZH | D00P-10LBA30-M05-0001 | 9 | +2 | DELIVERABLE_SCOPE x2 |
| CZH | D00P-10LBC40-M05-0001 | 7 | +4 | DELIVERABLE_SCOPE x4 |
| CZH | D00P-10LBC50-M05-0001 | 8 | +1 | DELIVERABLE_SCOPE x1 |
| CZH | D00P-10LBG10-M05-0001 | 12,15 | +1 | DELIVERABLE_SCOPE x1 |
| CZH | D00P-10LCA10-M05-0001 | 16 | +0 | ANNOTATION_TEXT |
| CZH | D00P-10MAN10-M05-0001 | 10 | +0 | ANNOTATION_TEXT |
| CZH | D00P-10MAN10-M05-0002 | 11 | +0 | ANNOTATION_TEXT |
| CZH | D00P-00EKG10-M05-0004 |  |  | DRAWING_NO_MISMATCH |
| CZH | D00P-00GBL10-M05-0001 |  |  | DRAWING_NO_MISMATCH |

## 6. Rule contributions (`--without`)

Each row is the whole document re-run with one rule switched off.
`bodies` is the total body count, which is why a rule can move
nothing in the actuated column and still be load-bearing.

| rule removed | actuated | vs baseline | drawings changed | exact drawings | bodies |
|---|---:|---:|---:|---:|---:|
| WAIST_DISC | 88 | -3 | 3 | 12 | 4207 |
| VANE_TICK | 69 | -22 | 4 | 9 | 2896 |
| END_BARS | 91 | +0 | 0 | 11 | 4149 |
| STROKE_LETTER | 58 | -33 | 7 | 7 | 2896 |
| ACT_CLEARANCE | 91 | +0 | 0 | 11 | 2896 |
| ACT_STEM | 104 | +13 | 3 | 9 | 2896 |

## 7. Per-deliverable recall / precision

| class | ground truth | rows | detected | matched | recall | precision |
|---|---|---:|---:|---:|---:|---:|
| BFV | CZI | 21 | 22 | 18 | 85.7% | 81.8% |
| MOV | CZH | 63 | 69 | 57 | 90.5% | 82.6% |
| CV | *master needed* | - | 0 | - | - | - |
| XV | *master needed* | - | 0 | - | - | - |
| EXCLUDED | *master needed* | - | 2789 | - | - | - |

### BUTTERFLY roll call (all 21 rows)

| no | drawing | type | expected | detected | verdict | description |
|---:|---|---|---|---|---|---|
| 89 | D00P-00PAB10-M05-0001 | MOV_I | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 AUX CIRCULATING WATER PUMP A DISCHARGE HYDRAULIC VA |
| 90 | D00P-00PAB10-M05-0001 | MOV_I | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 AUX CIRCULATING WATER PUMP B DISCHARGE HYDRAULIC VA |
| 91 | D00P-00PAB10-M05-0001 | HOV | HYDRAULIC | BUTTERFLY HYDRAULIC | MATCHED | UNIT #10 CIRCULATING WATER PUMP A DISCHARGE HYDRAULIC VALVE |
| 92 | D00P-00PAB10-M05-0001 | HOV | HYDRAULIC | BUTTERFLY HYDRAULIC | MATCHED | UNIT #10 CIRCULATING WATER PUMP B DISCHARGE HYDRAULIC VALVE |
| 93 | D00P-00PAB10-M05-0001 | HOV | HYDRAULIC |   | NOT_FOUND | UNIT #10 CIRCULATING WATER PUMP C DISCHARGE HYDRAULIC VALVE |
| 94 | D00P-00PAB10-M05-0002 | MOV_I | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #20 AUX CIRCULATING WATER PUMP A DISCHARGE HYDRAULIC VA |
| 95 | D00P-00PAB10-M05-0002 | MOV_I | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #20 AUX CIRCULATING WATER PUMP B DISCHARGE HYDRAULIC VA |
| 96 | D00P-00PAB10-M05-0002 | HOV | HYDRAULIC | BUTTERFLY HYDRAULIC | MATCHED | UNIT #20 CIRCULATING WATER PUMP A DISCHARGE HYDRAULIC VALVE |
| 97 | D00P-00PAB10-M05-0002 | HOV | HYDRAULIC | BUTTERFLY HYDRAULIC | MATCHED | UNIT #20 CIRCULATING WATER PUMP B DISCHARGE HYDRAULIC VALVE |
| 98 | D00P-00PAB10-M05-0002 | HOV | HYDRAULIC | BUTTERFLY MOTOR | ACTUATOR_MISMATCH | UNIT #20 CIRCULATING WATER PUMP C DISCHARGE HYDRAULIC VALVE |
| 99 | D00P-00PAB10-M05-0003 | MOV_I | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #00 EC & RO FEED PUMP A DISCHARGE HYDRAULIC VALVE |
| 100 | D00P-00PAB10-M05-0003 | MOV_I | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #00 EC & RO FEED PUMP B DISCHARGE HYDRAULIC VALVE |
| 101 | D00P-00PAB10-M05-0003 | CV | PNEUMATIC | BUTTERFLY MOTOR | ACTUATOR_MISMATCH | UNIT #00 EC & RO FEED PUMP RECIRCULATION VALVE |
| 102 | D00P-10PAC10-M05-0001 | MOV | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 SURFACE CONDENSER WATERBOX OUTLET 1 MOV |
| 103 | D00P-10PAC10-M05-0001 | MOV | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 SURFACE CONDENSER WATERBOX OUTLET 2 MOV |
| 104 | D00P-10PAC10-M05-0001 | MOV | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 SURFACE CONDENSER WATERBOX INLET 1 MOV |
| 105 | D00P-10PAC10-M05-0001 | MOV | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 SURFACE CONDENSER WATERBOX INLET 2 MOV |
| 175 | D00P-10PAC10-M05-0001 | MOV | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 SURFACE CONDENSER WATERBOX OUTLET 3 MOV |
| 176 | D00P-10PAC10-M05-0001 | MOV | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 SURFACE CONDENSER WATERBOX OUTLET 4 MOV |
| 177 | D00P-10PAC10-M05-0001 | MOV | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 SURFACE CONDENSER WATERBOX INLET 3 MOV |
| 178 | D00P-10PAC10-M05-0001 | MOV | MOTOR | BUTTERFLY MOTOR | MATCHED | UNIT #10 SURFACE CONDENSER WATERBOX INLET 4 MOV |

Unclaimed butterfly detections on those drawings: **2** - the file lists only the I&C butterflies, so a drawing may legitimately carry more.

## 8. Cross-validation - Steam-only ruleset

Rules no Steam drawing could have taught, switched off: `ACT_STEM`, `STROKE_LETTER`, `VANE_TICK`.

| group | | drawings | excel | detected | matched | recall | precision | exact |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| STEAM (training) | full | 11 | 40 | 50 | 40 | 100.0% | 80.0% | 6 |
| STEAM (training) | steam-only | 11 | 40 | 50 | 40 | 100.0% | 80.0% | 6 |
| | **drop** | | | | | **-0.0pp** | **-0.0pp** | |
| HOLDOUT PGB/PAB/EGD | full | 4 | 25 | 26 | 24 | 96.0% | 92.3% | 2 |
| HOLDOUT PGB/PAB/EGD | steam-only | 4 | 25 | 0 | 0 | 0.0% | 0.0% | 0 |
| | **drop** | | | | | **-96.0pp** | **-92.3pp** | |
| ALL | full | 19 | 78 | 91 | 77 | 98.7% | 84.6% | 11 |
| ALL | steam-only | 19 | 78 | 50 | 40 | 51.3% | 80.0% | 6 |
| | **drop** | | | | | **-47.4pp** | **-4.6pp** | |

## 9. Against the master valve list

`data/Valve_List_2512xx.xlsx` is not present in this checkout, so the
gate-vs-globe confusion matrix, the self-acting exclusion count
and the CV / XV split are still unmeasured. Section 10 below
states what that leaves open. Drop the file in and re-run:
nothing else needs changing - `load_master_rows` locates its
columns by header name.

## 10. What this comparison cannot measure

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

