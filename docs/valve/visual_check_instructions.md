# Visual check instructions (valve05) — round 1 (whole page) and round 2 (changed lines)

Packs: `python3 spike/valve_visual_pack.py --ds <PDF> --out /tmp/vis` · score: `python3 spike/valve_visual_score.py /tmp/vis/res`.
Paths below are the defaults used on 2026-10-31; the source PDF path must be changed for another file.

## Visual check of the Valve Datasheet reader — instructions for one batch of pages

Goal: for each page in your batch, compare what is PRINTED on the page (look at the images) with what the
program READ (the pNNN.txt file), and record every disagreement.  You are the independent eye; the result is
used to measure the reader's error rate.  Be exact and honest — do not assume the program is right or wrong.

Files (folder /tmp/vis):  pNNN_1.png (top half) · pNNN_2.png (bottom half, overlaps 40 px) · pNNN.txt (reader output)
Source PDF: /tmp/ext/datasheet/Datasheet.pdf (page N = index N-1).  Read files with the Read tool; use Bash only
for the text-layer check below (python3 -I with pymupdf).

### For a DATASHEET page (pNNN.txt starts with DATASHEET)
1. Header: tag, doc_no, rev, "sheet x of y" — compare with the title block.
2. Each line `F<i> | row | label | value | unit | status | bbox`: find that row number and label on the page and
   decide:
   OK            value (+unit) equals what is printed for that label (ignore spacing, letter case, the unit
                 being in its own column; '-' or blank printed = blank read is OK; status words don't matter)
   WRONG         printed value differs (missing/extra words, wrong cell's text, truncated)
   FALSE_BLANK   reader value empty but a value is printed for that label
   SPURIOUS      reader has a value but the cell for that label is empty
   WRONG_LABEL   the label in the line is not the label printed on that row/cell
   Same words in a different order = WRONG (reading order matters).  A label the reader built from a column header
   plus a sub-label (e.g. 'Torque Min' under 'Torque … Min | Max') is OK when it names the right cell.
   Text present in the text layer but NOT visible on the page (hidden / covered / white): record what you SEE
   (e.g. SPURIOUS) with "hidden": true.
3. MISSING: a printed label WITH a printed value on this page that has no F line at all (row number + label + value).
   Ignore the title block, revision table and NOTES block for this (they are checked separately).
4. Notes `N<no> | text`: OK if number and text match the printed note (a wrapped line joined is OK; tiny spacing
   differences are OK).  A printed note with no N line = MISSING_NOTE.  Wrong number or cut/merged text = WRONG_NOTE.
### For an OTHER page (OTHER PAGE …)
Check doc_no / title / rev against the page when the page shows them (cover / title block); if the page shows a
General Notes list and G lines are given, check each G line (number + text; MISSING_NOTE / WRONG_NOTE as above).
If the page carries none of these (e.g. revision record, blank), record checked = 0.  A cut or wrong title / doc_no /
rev = item "header.title" / "header.doc_no" / "header.rev", kind HEADER.  checked = header items present + G lines.

### Before you record anything that is not OK — confirm it with the text layer
Small print is easy to misread by eye.  For every suspected error run e.g.
  python3 -I -c "import pymupdf;p=pymupdf.open('/tmp/ext/datasheet/Datasheet.pdf')[N-1];print(p.get_text('text',clip=(x0,y0,x1,y1)))"
around the row (bbox in pt; widen x to the whole row: x 40..575, y bbox±3).  Only record it if the page really
says something different from the reader.  If the text layer and the image disagree, trust the image and say so.

### Output — one JSON file per page: /tmp/vis/res/pNNN.json
(checked on a datasheet page = 4 header items + every F line + every N line + each MISSING item you add.)
{"page": N, "kind": "datasheet"|"other", "checked": <number of items you judged: header items + F lines + N/G lines + MISSING items>,
 "errors": [{"item": "F12"|"header.rev"|"N3"|"G5"|"MISSING", "kind": "WRONG|FALSE_BLANK|SPURIOUS|WRONG_LABEL|MISSING|MISSING_NOTE|WRONG_NOTE|HEADER",
             "row": <row or null>, "label": "...", "reader": "...", "page_says": "...", "confirmed_by_text_layer": true|false}]}
Write valid JSON (python3 -c json.dump is safest).  Look at the two halves first; open a zoomed crop (python3 -I + pymupdf get_pixmap clip, save under /tmp/vis/tmp/)
only when the print is too small to read.  Finally reply with ONE line per page: "pNNN checked=X errors=Y" and
nothing else (no explanations — the JSON files carry the details).

## Round 2 — judge only what changed in the reader's output

The reader was fixed after round 1.  For each page in your batch, /tmp/vis2/dNNN.txt lists:
  LINES TO JUDGE — new or changed lines of the reader's output (same formats as round 1: header line DATASHEET/OTHER PAGE,
                   `F | row | label | value | unit | status | bbox`, `N<no>[ (section)] | text`, `G<no> | text`)
  LINES THE READER NO LONGER GIVES — lines it gave before; dropping is right when the page does not print that as a value
                   (e.g. a footer that was glued to a note, hidden text, a unit read as a value) or when a changed line above replaces it.
Images: /tmp/vis/pNNN_1.png (top half) · /tmp/vis/pNNN_2.png (bottom half).  Full new output: /tmp/vis2/pNNN.txt.
Source PDF for the text-layer check: /tmp/ext/datasheet/Datasheet.pdf (page N = index N-1); python3 -I with pymupdf.

Judge each listed line exactly like round 1 (OK / WRONG / FALSE_BLANK / SPURIOUS / WRONG_LABEL / WRONG_NOTE / HEADER; same words
in another order = WRONG; text invisible on the page must not be read).  For a header line check tag / doc_no / rev /
sheet x of y (and title) against the page.  A removed line is an error (kind DROPPED) only if the page really prints it as its own value.
Before recording any error confirm it with the text layer (and trust the image if they disagree).

Output per page: /tmp/vis2/res/pNNN.json
{"page": N, "checked": <number of listed lines you judged, both sections>, "errors": [{"item": "<first 40 chars of the line>",
 "kind": "...", "label": "...", "reader": "...", "page_says": "..."}]}
Reply with one line per page "pNNN checked=X errors=Y" and nothing else.
