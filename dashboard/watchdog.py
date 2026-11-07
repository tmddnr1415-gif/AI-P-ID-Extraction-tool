#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
대시보드 서버 감시(watchdog) — 비정상 종료·응답 없음 시 자동 재시작 (표준 라이브러리만 사용)

    pythonw watchdog.py            # 창 없이 실행 (작업 스케줄러 등록용, install_autostart.bat 참고)
    python  watchdog.py            # 콘솔에서 상태를 보며 실행

- 같은 폴더의 server.py 를 --port 8080 --log server.log 로 실행
- 30초마다 http://127.0.0.1:8080/api/info 확인, 3회 연속 응답 없으면 강제 종료 후 재시작
- 서버가 종료되면(오류 포함) 5초 뒤 재시작, 포트 사용 중(종료 코드 2)이면 60초 뒤 재시도
- 이미 다른 대시보드 서버가 8080 에서 정상 동작 중이면 새로 띄우지 않고 감시만 함
- watchdog 은 1개만 실행됨 (watchdog.lock), 기록은 watchdog.log
"""
import datetime, json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('DASHBOARD_PORT', '8080'))
CHECK_SEC, FAIL_LIMIT = 30, 3
LOG = os.path.join(HERE, 'watchdog.log')


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
        if os.path.getsize(LOG) > 2_000_000:                     # 2MB 넘으면 한 번 정리
            os.replace(LOG, LOG + '.old')
    except OSError:
        pass
    if sys.stdout:
        try:
            print(line, flush=True)
        except Exception:
            pass


def healthy():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/info', timeout=8) as r:
            return json.loads(r.read()).get('mode') == 'server'
    except Exception:
        return False


def single_instance():
    """watchdog 중복 실행 방지 (파일 잠금)"""
    import msvcrt
    f = open(os.path.join(HERE, 'watchdog.lock'), 'a+')
    try:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        log('이미 다른 watchdog 이 실행 중이라 종료합니다')
        sys.exit(0)
    return f                                                     # 프로세스 끝날 때까지 잠금 유지


def start_server():
    exe = sys.executable                                         # pythonw 로 실행하면 서버도 창 없이 실행
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    return subprocess.Popen([exe, os.path.join(HERE, 'server.py'), '--root', HERE, '--port', str(PORT), '--log', 'server.log'],
                            cwd=HERE, creationflags=flags,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)


def main():
    lock = single_instance()
    log(f'watchdog 시작 (포트 {PORT}, 폴더 {HERE})')
    while True:
        if healthy():                                            # 수동으로 띄운 서버가 이미 동작 중 → 감시만
            time.sleep(CHECK_SEC)
            continue
        proc = start_server()
        log(f'서버 시작 (PID {proc.pid})')
        time.sleep(5)
        fails = 0
        while True:
            code = proc.poll()
            if code is not None:
                if code == 2:
                    log('포트 사용 중(종료 코드 2) → 60초 뒤 다시 시도')
                    time.sleep(60)
                else:
                    log(f'서버 종료됨(종료 코드 {code}) → 5초 뒤 재시작')
                    time.sleep(5)
                break
            if healthy():
                fails = 0
            else:
                fails += 1
                log(f'서버 응답 없음 ({fails}/{FAIL_LIMIT})')
                if fails >= FAIL_LIMIT:
                    log('응답 없음이 계속되어 서버를 강제 종료 후 재시작합니다')
                    proc.kill()
                    try:
                        proc.wait(10)
                    except Exception:
                        pass
                    break
            time.sleep(CHECK_SEC)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log('watchdog 종료 (Ctrl+C)')
