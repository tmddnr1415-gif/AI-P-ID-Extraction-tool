# 합성 시험 도면 (32회차 [D])

`spike/make_synthetic.py` 가 만든다.  재료는 **AL NOUF1 범례 4장 +
P&ID 2장**이고 각 파일은 **한 축만** 바꾼다.  결과는
`out/round32/5_synthetic.md` 에 있다.

| 파일 | 바꾼 축 |
| --- | --- |
| `01_a0.pdf` | A0 3370x2384 (배율 1.41) |
| `02_a4.pdf` | A4 842x595 (배율 0.353) |
| `03a_rotate90.pdf` | /Rotate 90 |
| `03b_rotate180.pdf` | /Rotate 180 |
| `04_tight_lines.pdf` | 0.2 배 — 줄 간격이 버킷(5·7pt) 아래로 내려간다 |
| `05_legend_last.pdf` | 범례가 마지막 장 |
| `06_no_legend.pdf` | 범례 없음 |
| `07_no_history.pdf` | 이력 표 띠를 안 그림 |
| `08_a4_tagged.pdf` | A4 + 버블 안에 태그 활자 |

⚠ **합성은 실제 도면을 대표하지 않는다** — 배율 경로(`show_pdf_page`)는
주석을 옮기지 않으므로 UAD 의 SHX 글자 같은 것은 재현되지 않고, 개정
클라우드 · 패키지 상자 · 도면 오탈자도 여기에 없다.
