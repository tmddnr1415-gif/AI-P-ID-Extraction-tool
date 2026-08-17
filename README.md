# P&ID → 계기·밸브 리스트 추출

P&ID PDF 를 읽어 발주처 Excel 양식(Field Instrument / I&C Butterfly Valve /
MOV Gate&Globe / Control·Shutoff Valve)을 채웁니다. 도면은 100% 벡터이므로 OCR 을
쓰지 않고 텍스트 앵커와 도형 검증으로 판정하며, 판정 규칙은 문서의 Symbol & Legend
시트에서 런타임에 측정합니다. LLM 을 호출하지 않습니다.

## 실행

```bash
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000
# 브라우저에서 http://127.0.0.1:8000
```

PDF 를 창에 끌어다 놓으면 분석이 시작됩니다(도면 58장 기준 약 7분, 진행률은
SSE 로 실시간 표시). 끝나면 좌측 도면 뷰어 / 우측 결과 그리드 화면으로 넘어갑니다.

Excel 템플릿은 `data/` 의 발주처 파일을 기본으로 쓰고, `POST /templates` 로
교체할 수 있습니다.

## 화면

- **탭** 전체 / Field / BFV / MOV / Pneumatic / 검토필요 (각 건수 표시)
- **양방향 선택** 그리드 행 ↔ 도면 위 박스
- **인라인 편집** Type, Q'ty, System, Valve Type, Vendor, Scope, Tag No.,
  Description. 사람이 고친 값은 `user_values` 에 따로 저장되어 **재분석해도
  보존**됩니다
- **판정 근거 패널** 앵커 / Body 판정 / 액추에이터 / 제외 사유 / 수량 근거
- **검토 필요 건수** 상단에 상시 표시

## 출력 게이트

`전체 검토 완료` 를 체크하면 그 시점 데이터가 **revision 스냅샷**으로 저장되고,
Excel 은 **스냅샷에서만** 생성됩니다. 라이브 데이터에서 바로 뽑지 않습니다.
출력은 발주처 파일을 복사한 뒤 데이터 영역만 바꾸므로 서식·필터·열너비·부속시트
5종과 표 하단 기술요구사항 Note 가 그대로 유지됩니다.

## 테스트

```bash
python3 -m pytest -q -m "not slow"   # 병합·충돌·스냅샷 규칙 (1초)
python3 -m pytest -q                 # 결정론성 회귀 포함 (약 15분)
```

## 구조

```
app/engine/   Phase 0 에서 검증된 검출 엔진 (spike/ 에서 git mv, 로직 변경 없음)
app/pipeline  엔진 호출 순서만 담당. 판정은 하지 않음
app/db        ai_values / user_values 분리 저장, revision 스냅샷
app/excel_out 발주처 워크북을 열어 데이터 영역만 교체
app/main      FastAPI: 업로드 / 진행률 SSE / 행 편집 / 스냅샷 / Excel
app/static    리뷰 UI (빌드 도구 없음)
spike/README.md  Phase 0 검증 기록 (수치·근거)
docs/design.md   설계안
```

## 알려진 범위

- **Description** 공란 — 배관 추적이 필요하며 Phase 2 입니다
- **Tag No.** 공란 — 도면 자체가 `.....` 로 미부여 상태입니다
- 마스터 Valve List 는 템플릿이 없어 출력에서 제외됩니다
