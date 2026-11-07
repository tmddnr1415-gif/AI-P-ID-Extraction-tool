---
name: ic-anatomy-link
description: 계측제어 답변의 문장에 part:* 부품 태그를 붙이고, 기기 Item(밸브·PSV·Transmitter·Gauge 등)의 부품 구조를 Anatomy 스킬로 아이소메트릭 인터랙티브 SVG(부품 점멸)로 만든다. 부품·구조 설명, 3D/도해, 점멸 요청 시 사용한다.
---

# Anatomy 연동

**Anatomy 는 `anatomy` 스킬(Skill 도구)로 사용한다.** 이 스킬은 연결 규칙만 정의한다.

## 1. 태그 규칙
- 답변 항목 끝에 `part:{id}` 를 붙인다. 예: `Fail 방향은 Spring-return 으로 확보 part:actuator`
- id 는 `Parts_{ITEM}_{Type}.json` 매핑표에 있는 것만. 없으면 태그를 붙이지 않고 `부품 맵 미확인`.
- 기본 id 후보(초안): `actuator`, `solenoid`, `positioner`, `limit-switch`, `body`, `ball`, `seat`, `stem`, `bonnet`, `trim`, `spring`, `nozzle`, `disc`, `process-conn`, `electronics`, `sensor`.
- DCS·IPS·MMS·CCS·FGS 는 부품 대신 시스템 구성 블록 id(`controller`, `io`, `network`, `hmi` …) 사용.

## 2. 도해 생성
1. `Skill` 도구로 `anatomy` 스킬을 호출한다.
2. 입력: Item·Type, 부품 목록(Parts JSON), 치수(`Dim_{ITEM}_{Type}.json`, 출처 URL 포함 수치만).
3. 요구: 각 부품에 `data-part="{id}"` 부여, 태그 클릭/호버 시 해당 부품 점멸(애니메이션 eased).
4. 출력: `output/anatomy/{ITEM}_{Type}.html`.
5. 치수 없는 값은 `미확인` 으로 표시, 제조사 도면 원본은 복제하지 않는다(링크만).

## 2-1. 실물 3D (파라메트릭)
- 밸브·PSV·Transmitter·System cabinet 은 `ic-3d-builder` 실물 3D 로도 보여준다(대시보드 Anatomy 탭 **실물 3D**).
- 매핑은 `data/parts/Map_3d.json` 만 사용: `part:{개념 id}` → 실물 3D 프리셋·부품 id. 매핑에 없으면 개념 모델 점멸로 처리한다.
- GA·치수도가 있으면 `ic-ga-to-3d` 스킬로 spec JSON(치수 출처: drawing/user/standard/estimate)을 만들고, 대시보드에서는 같은 엔진이 그 값을 쓴다.
- 실물 3D 의 'standard'(표준 참고표)·'estimate'(비례 추정) 치수는 '미확인'과 같은 취급이다.

## 3. 연동 방식
답변 태그 `part:x` → HTML 의 `data-part="x"` 요소를 점멸하는 `highlight(id)` 함수로 연결한다. 매핑은 JSON 표만 사용한다.
