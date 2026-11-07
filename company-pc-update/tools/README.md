# 회사 업데이트 파일 도구 (오케스트레이터용 · 통합 때 적용)

> 업데이트 파일은 **요청 때만** 만든다. 여기 있는 것은 그때 쓸 준비물이다.

## `apply_delta_overwrite.patch` — 적용기에 `--overwrite` 추가 (덮어쓰기 원칙)

대상: S2 브랜치 `spike/apply_delta.py` (hotfix132 판). 통합 브랜치에서 `git apply company-pc-update/tools/apply_delta_overwrite.patch`.

바뀌는 것:
- `--overwrite` 옵션. 회사 PC 에서 따로 고친 파일을 **충돌(안 덮음) 대신 `forced`(백업 뒤 덮음)** 로 처리한다. 저장소에서 없앤 파일도 회사가 고쳤든 지운다.
- 보호 폴더(`app\_data` · `data` · `.venv` · `logs`)는 그대로 거부. 실패 시 자동 되돌림(hotfix132 안전장치) · `--restore` 그대로.
- 끝에 "회사에서 고친 파일 N개를 최신으로 덮었습니다" 목록을 찍는다 → `1_먼저읽기` 맨 위에 같은 목록을 넣는다.

시험(가짜 꾸러미, 2026-11-07): 기본은 `충돌 - 안 덮음` · `--overwrite` 는 `덮어씀 - 회사에서 고친 파일` 뒤 파일이 최신, 백업에 회사 수정본, `--restore` 로 되돌아감.

## 통합 때 같이 바꿀 것 (아직 안 함)

| 파일 (S2 브랜치) | 바꿀 내용 |
|---|---|
| `config/release_sources.json` | `company_owned` 삭제(Valve 를 통합에 싣기) · PANEL `imported` 갱신 · BOOKS(`dashboard/apps/books` → `app/static/books`) · IC3D(`app/` → `app/static/ic3d`) 항목 추가 |
| `docs/handoff/branches.md` | 세션 ↔ 브랜치 표 갱신 · "꾸러미는 오케스트레이터가 만든다" |
| `spike/pack_delta.py --base` | 마지막 **적용 확인** 커밋 (지금: 2026-11-02 valve29 시점) |
| `apply_to_PID_ops.bat` | `--overwrite` 를 붙인 줄 |
| `out/hotfix133/readme_head.txt` | 덮어쓴 회사 수정 파일 목록 · 무엇이 바뀌었나 · 적용 순서 |
