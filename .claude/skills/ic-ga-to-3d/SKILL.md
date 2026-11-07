---
name: ic-ga-to-3d
description: 계측제어 품목의 General Arrangement(GA) / Dimensional Drawing 을 읽어 부품 단위(anatomy)로 분해된 파라메트릭 3D 모델을 만든다. System cabinet, instrument hook-up, control valve, MOV, gate/globe/ball/butterfly 밸브, PSV 를 다룬다. 사용자가 GA·치수도·데이터시트·훅업 도면(PDF/이미지)을 주고 3D, 모델, 배치·간섭 검토, STL/OBJ, "도면→3D" 를 말할 때 쓴다.
---

# I&C GA → 3D (anatomy)

도면을 읽어 파라메트릭 3D 엔진 `ic-3d-builder/` 의 파라미터(`spec JSON`)를 채운다.
3D 는 이름 붙은 기본 도형으로 만든 부품 조립(anatomy)이고, 모든 치수는 **출처**를 가진다.

| 출처 | 의미 |
|---|---|
| `drawing` | 도면에서 직접 읽은 값. `evidence`(어느 뷰·표·주기에서 읽었는지)를 반드시 단다 |
| `user` | 사용자가 직접 준 값 |
| `standard` | 엔진이 내장 표준표(`src/refdata.js`, 원문 대조 전)로 자동으로 채운 값 |
| `estimate` | 비례 추정값. 형상 참고용 |

**핵심 규칙: `inputs` 에는 도면에 적힌 값만 넣는다.** 빈 칸을 표준값으로 채우지 않는다.
엔진이 채우고 `standard`/`estimate` 로 표시한다. 직접 채우면 도면값과 가정이 섞여 검토에서 구분할 수 없다.

## 순서

1. **품목 분류.** `node ic-3d-builder/dev/spec.mjs presets` 에서 가장 가까운 프리셋을 고른다.
   - Control valve → `cv_globe` / `cv_ball` / `cv_bfv`
   - MOV → `mov_gate` / `mov_globe` / `mov_ball` / `mov_bfv`
   - 수동 → `man_gate` / `man_globe` / `man_ball` / `man_bfv`
   - PSV → `psv`, 캐비닛 → `cabinet`, 훅업 → `hook_pt` / `hook_dpt` / `hook_lt`
2. **템플릿 생성.** `node ic-3d-builder/dev/spec.mjs template <preset> <작업폴더>/spec.json`
3. **도면 판독.** Read 도구로 이미지·PDF 를 연다. [references/parameters.md](references/parameters.md) 의
   key 의미를 보며 도면 치수가 어느 key 를 재는지 대응시킨다.
   - 길이는 mm 로 환산한다 (inch × 25.4). 원문은 `evidence` 에 둔다. 예: `"A = 14.50 in · 정면도 치수표"`
   - 사이즈별 치수표(A/B/H 열)는 사용자가 말한 사이즈·등급 행을 쓴다. 모르면 묻는다.
   - `MAX`/`APPROX`/`REF` 치수는 `"confidence": "medium"` 으로 둔다.
   - 도면에 전체 높이만 있으면 `overall_h` 에 넣는다. 엔진이 추정 높이들을 그 값에 맞춘다.
   - key 가 없는 치수(볼트 길이, 노즐 방위 등)는 사용자에게 따로 보고한다.
4. **점검.** `node ic-3d-builder/dev/spec.mjs check <작업폴더>/spec.json`
   key 별 값·출처·근거, 외곽치수, 설계 점검 경고를 출력한다. exit 1 이면 값이 잘못된 것이다.
5. **보고 비교.** 렌더를 도면 뷰와 나란히 놓고 형상을 확인한다.
   ```
   node ic-3d-builder/dev/render.mjs <작업폴더>/spec.json <작업폴더>/model.png --views iso,front,side
   ```
   네트워크에서 three.js 를 받을 수 없으면 `npm i three@0.128.0` 후
   `--three node_modules/three/build/three.min.js` 를 붙인다.
   정면도의 전체 높이·폭을 도면과 비교한다. 다르면 key 대응(치수선이 어디서 어디까지 재는지)을 다시 읽는다.
6. **전달.** spec JSON 과 PNG 를 넘기고, STL/OBJ 받는 법을 알려준다:
   브라우저로 `ic-3d-builder/index.html` 열기 → "JSON 불러오기" → STL/OBJ 버튼.

## 결과 보고

- `drawing`/`user` 가 아닌 치수(표준·추정)를 하나하나 밝힌다. 간섭 결론을 그 치수에 기대지 않는다.
- `check` 경고(⚠)는 출력된 그대로 전달한다.
- 표준표는 원문 표준과 대조하지 않았다. STL/OBJ 는 배치 검토용이지 제작용이 아니라고 밝힌다.

## 도면이 없을 때

사용자가 형식·모델명만 주면 벤더 치수도를 웹에서 찾는다. 타입별 출처는
[ic-3d-builder/docs/drawing-sources.md](../../../ic-3d-builder/docs/drawing-sources.md) 에서 시작한다.
내려받은 벤더 PDF 는 저장소에 커밋하지 않는다. 링크와 읽어 낸 치수만 남긴다.
그래도 없으면 프리셋 + 표준표로 만들고, 결과가 "표준/추정 기반"임을 분명히 말한다.

## 새 타입·부품 추가

`ic-3d-builder/src/anatomy.js` 의 `PRESETS` 에 넣거나 `build*` 함수를 확장한다. 고친 뒤에는:
```
python3 ic-3d-builder/dev/build.py          # 단일 파일 index.html 재생성
node ic-3d-builder/dev/spec.mjs params      # references/parameters.md 갱신용 출력
```
