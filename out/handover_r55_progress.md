# 회사 PC 꾸러미 r55 — 진행 기록

기준 `aac64ba` · HEAD `2797626` (프롬프트가 적은 `22b6a19` 뒤에 p11~p15 실행 로그
커밋 하나가 더 있습니다 — 소스는 같습니다).  **엔진 코드 0줄.**

| 단계 | 상태 |
| --- | --- |
| [A] 기준선 세 프로젝트 | AL NOUF1 도는 중 |
| [B] wheel | **끝** — 새 패키지 2 · 의존 닫힘 13 · 오프라인 설치 시험함(리눅스) |
| [C] 파일 목록 | 초안 — A 164 · M 31 · D 0 · R 0 |
| [D] 적용 검증 | 준비 (`spike/verify_r55.py`) |
| [E] 산출물 | — |

## [B] 기록

* `git diff aac64ba..HEAD -- requirements.txt` 가 더한 것은 **둘**: `ezdxf>=1.4` ·
  `matplotlib>=3.8`.
* `pip download --platform win_amd64 --python-version 3.11 --only-binary=:all:` 로
  받은 닫힌 집합은 **13개**.  그중 **셋(numpy 2.4.6 · packaging 26.3 ·
  typing_extensions 4.16.0)은 9/3 이관 꾸러미에 이미 들어 있고 버전이 같습니다**
  (`requirements-win.lock.txt` 와 대조).  그래서 **새로 보내는 것은 열 개**입니다.
* ⚠ **Windows 에서 실제로 설치해 보지는 못했습니다** (이 작업 환경은 리눅스라
  `win_amd64` 휠을 설치할 수 없습니다).  대신 둘을 했습니다:
  1. **win_amd64 태그로 오프라인 해석**(`pip install --no-index --find-links …
     --platform win_amd64 --python-version 3.11 --dry-run`) — 13개가 전부 풀립니다.
  2. **같은 패키지 집합의 리눅스 휠로 진짜 오프라인 설치**를 새 가상환경에서 하고
     `import ezdxf, matplotlib` 와 `ezdxf.addons.drawing.matplotlib` 까지 확인.
     하나(pillow)를 빼고 다시 해서 **실제로 실패하는 것**도 확인했습니다.
