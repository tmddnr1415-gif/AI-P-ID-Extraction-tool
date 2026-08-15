# Symbol & Legend

> ⚠️ **아직 생성되지 않은 자리표시자입니다.**
>
> 이 파일은 Symbol & Legend 도면 4장(`D00P-00GEN00-M05-0002` ~ `-0005`, PDF p2~p5)을
> Claude vision으로 판독해 자동 생성합니다. 생성 전까지는 `extract_instruments.py`가
> 기호 정의 없이 판독하게 되므로 **정확도가 떨어집니다.**
>
> ```bash
> export ANTHROPIC_API_KEY=sk-ant-...
> python3 scripts/pdf_to_images.py inputs/D00P_PID_Total_20251125.pdf --pages 2-5 --tiles 3x2
> python3 scripts/parse_legend.py --pages 2,3,4,5 --force
> ```
>
> 생성 후에는 **사람이 검토하고 직접 고쳐 쓰는 규칙 문서**가 됩니다.
> 재생성하면 기존 내용은 `.bak.md`로 백업됩니다.

## 생성될 항목

- 태그 첫 글자 → 측정 변수 대조표
- 태그 뒤 글자 → 기능 대조표
- 계기 심볼(원/사각/육각, 테두리선) → 설치 위치 해석
- 신호선 종류 → 의미 (배선 / 공압 / 소프트웨어 링크 / 캐필러리)
- 밸브 상태 기호 (FO / FC / FL / LO / LC)
- 도면 약어
- Vendor Scope 표기 방법

## 생성 전 임시로 적용되는 것

`rules/naming_convention.md`의 6절(이 프로젝트에서 실제 나타나는 TYPE 조합)과
`rules/extraction_guide.md`의 4절(도면 문자 → TYPE 매핑)이 최소한의 기준 역할을 합니다.
