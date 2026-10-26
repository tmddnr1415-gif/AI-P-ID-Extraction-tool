# 17회차 [A-2] — 시험이 실 DB 를 연다.  전수 조사와 차단

## 왜 급건인가

16회차에 `app/_data/app.db` 의 sha256 이 시험을 돌리는 중에 바뀌었다.

```
df9875e5a84f929a…87d2324   →   643748dc0efe1681…26ecd40a
32MB → 15.7MB (죽은 페이지 정리 · 저널 모드 전환)
```

내용은 같았다 (분석 4건 · item 824/824/824/75 · `pid_page` 183 ·
`feedback`·`review_state`·`revision`·`report`·`revision_state`·
`deleted_candidate` 전부 0).  캡처는 그 전에 끝나 있었다.  **그래서 그
회차는 무해했지만, 운이 좋았던 것이다.**

회사 PC 에는 팀원 여러 명의 분석이 그 파일 하나에 들어 있다.  누가 시험을
한 번 돌리면 그 파일이 열린다.  `db.connect` 는 읽기 전용이 아니다 —
`PRAGMA journal_mode=WAL` 과 `executescript(SCHEMA)` 를 돌린다.

## 전수 조사 — 닿는 길은 **하나**다

`app.db.connect` 를 감싸 경로가 `app/_data` 밑이면 시험 이름과 스택을
적는 pytest 플러그인으로 쟀다 (막지 않고 적기만 하는 조사판).

```
app/main.py:50   CON = db.connect(DB_PATH)          ← import 시점에 실행
DB_PATH = paths.data_dir() / "app.db"
```

`from app import main` 을 하는 자리는 다섯이다.

| 자리 | 마커 | 언제 도나 |
| --- | --- | --- |
| `tests/test_axis_overrides.py:85` | 없음 | 빠른 |
| `tests/test_axis_overrides.py:105` | 없음 | 빠른 |
| `tests/test_determinism.py:392` (`test_the_answer_key_is_opt_in`) | 없음 | 빠른 |
| `tests/test_package.py:103` | 없음 | 빠른 |
| `tests/test_package.py:128` | 없음 | 빠른 |

**실측**: 빠른 스위트 한 번에 실 DB 를 여는 횟수는 **1** 이다 — 가장 먼저
도는 자리(`test_axis_overrides.py::test_candidate_noise_filter_keeps_names`)
가 열고, 그 뒤로는 `app.main` 모듈이 캐시되어 다시 열지 않는다.

**수집(collect)만으로는 0** 이다 (11개 시험 파일 전수 확인).  모듈 최상위에서
`app.main` 을 가져오는 파일이 없기 때문이고, 그래서 `-m ui` · `-m slow` 처럼
그 다섯이 전부 deselect 되는 실행에서는 **in-process 로는 안 열린다.**

**UI 스위트가 실 DB 에 하는 일은 읽기뿐이다** — `shutil.copyfile(REAL_DB, …)`
와 `sha256(REAL_DB.read_bytes())`.  서버는 사본에 `PID_DATA_DIR` 로 붙는다.
읽기는 원본을 건드리지 않으므로 막지 않았다.

**14회차의 방어가 왜 못 잡았나**: `test_zzz_the_suite_left_the_real_database
_alone` 은 `tests/test_ui_edits.py` 안에 있어 **UI 스위트에서만** 돈다.
위 다섯 자리는 전부 빠른 스위트에 있다.

## 막는 방법 — 두 겹, 둘 다 이미 있는 것

`conftest.py` 를 **저장소 뿌리**에 둔다 (rootdir).  pytest 는 시험 모듈보다
먼저 이것을 import 하므로, `app.main` 이 import 되기 전에 손을 쓸 수 있다.

### 1겹 — `PID_DATA_DIR` 을 버릴 폴더로

`app/paths.py` 가 **이미 그 용도로** 두고 문서화해 둔 변수다 (14회차 UI
스위트가 쓴다).  새 개념을 만들지 않았다 — 16회차의 교훈 그대로
"없는 것을 만들기 전에 있는 것을 찾는다".

바깥에서 이미 정해 두었으면 **그것을 존중한다**.  회사 PC 에서 따로 폴더를
잡아 돌리는 길을 닫지 않기 위해서다.  세션이 끝나면 우리가 만든 것만 지운다.

### 2겹 — 실 `app/_data` 밑을 열면 예외

1겹은 **환경변수를 읽는 코드**만 돌린다.  `ROOT / "app" / "_data"` 처럼
경로를 직접 만드는 코드는 그것을 지나친다.  그래서 `db.connect` 를 감싸
그 밑을 열려고 하면 `RuntimeError` 를 던진다.

**건너뛰지 않고 실패시킨다.**  14회차 [B]4 에서 확립한 방식이다 —
건너뛰기가 세 회차 동안 침묵을 만들었다.

### 합격 기준 — 세션 전체에서 바이트 불변

`pytest_sessionfinish` 가 실 DB 의 sha256 을 세션 시작 값과 대조하고,
다르면 **종료 상태를 1로 만든다**.  걸림이 여는 것을 막는 것과, 막았다는
것을 증명하는 것은 다른 일이다.

## 검증 — 실측

| | 걸림 전 | 걸림 후 |
| --- | --- | --- |
| 빠른 스위트가 실 DB 를 연 횟수 | **1** | **0** (일부러 여는 시험 1건은 예외로 막힌 것을 확인) |
| `app.db` sha256 | `643748dc…` | `643748dc…` **불변** |
| `app.db-shm` 수정 시각 | 13:48:07 로 **움직임** | 13:48:07 그대로 **안 움직임** |
| 빠른 시험 | 170 통과 | **173 통과** (격리 시험 3건 추가) |

## 추가된 시험 — `tests/test_data_isolation.py`

1. `test_the_writing_root_is_not_the_real_one` — 1겹이 걸려 있나
2. `test_opening_the_real_database_is_an_error` — 2겹이 **실패**로 막나
3. `test_reading_the_real_database_is_still_allowed` — 사본을 여는 길은 열려 있나
   (UI 스위트가 그 길로 돈다.  막아야 하는 것은 *여는 것*이지 읽는 것이 아니다)
