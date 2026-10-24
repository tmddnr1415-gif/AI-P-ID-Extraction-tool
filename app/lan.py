"""hotfix50 — 사내망에서 열 때의 규칙 (부서 대시보드 안에 들어가기 위해).

이 프로그램은 처음부터 `127.0.0.1` 에만 열렸다 — 그 자체가 접근 제한이었다.  부서
대시보드(포트 8080)가 이 화면을 iframe 으로 띄우려면 다른 PC 가 들어와야 하므로
사내망 주소로 열어야 하고, 그 순간 그 제한이 사라진다.  그래서 대시보드 서버와
**같은 규칙**을 둔다 (DASHBOARD_ARCHITECTURE.md §5):

    루프백 · 사설망 · 이 서버 PC 의 /16 대역 · `PID_ALLOW` 로 더한 대역

만 받고 나머지는 403.  켜는 것은 실행기다 — `start.bat --lan` · `run.sh --lan` ·
`PID_Extract.exe --lan` 이 `PID_LAN=1` 을 두고 `0.0.0.0` 에 연다.  꺼져 있으면
(예전처럼 127.0.0.1) 운영체제가 이미 루프백만 받으므로 이 검사는 하지 않는다 —
그래서 시험(TestClient 의 가짜 주소 `testclient`)과 기존 실행은 한 줄도 달라지지
않는다.

대역은 코드에 적지 않는다 — 이 PC 의 주소에서 그때 잰다 (부서장 PC 65.3.30.234 →
65.3.0.0/16).  사설망 판정은 표준 라이브러리 `ipaddress` 가 한다.
"""

from __future__ import annotations

import ipaddress
import os
import socket

ENV_ON = "PID_LAN"
ENV_ALLOW = "PID_ALLOW"


def enabled() -> bool:
    return os.environ.get(ENV_ON, "") == "1"


def local_ipv4() -> list[str]:
    """이 PC 의 IPv4 주소 (루프백 제외).  패킷은 보내지 않는다 — UDP connect 는
    경로만 고른다."""
    found: list[str] = []
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            found.append(ip)
    except OSError:
        pass
    for probe in ("10.255.255.255", "192.168.255.255"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((probe, 1))
                found.append(s.getsockname()[0])
        except OSError:
            continue
    out = []
    for ip in found:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if a.version == 4 and not a.is_loopback and not a.is_unspecified and ip not in out:
            out.append(ip)
    return out


def extra_networks(raw: str | None = None) -> list[ipaddress._BaseNetwork]:
    """`PID_ALLOW=65.4.0.0/16,10.20.0.0/16` — 쉼표로 더한 대역.  못 읽는 항목은 버린다."""
    raw = os.environ.get(ENV_ALLOW, "") if raw is None else raw
    nets = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            continue
    return nets


def allowed_networks(local: list[str] | None = None,
                     extra: list | None = None) -> list[ipaddress._BaseNetwork]:
    """이 서버의 /16 대역 + 더한 대역.  (루프백·사설망은 `client_allowed` 가 따로 본다.)"""
    local = local_ipv4() if local is None else local
    nets = [ipaddress.ip_network(f"{ip}/16", strict=False) for ip in local]
    nets += extra_networks() if extra is None else extra
    return nets


def client_allowed(host: str | None, nets) -> bool:
    """대시보드 서버와 같은 규칙.  주소를 못 읽으면 받지 않는다.

    hotfix52 — `nets` 는 목록이거나 목록을 내는 함수다.  루프백 · 사설망은 대역을 재지
    않고 먼저 받는다: 대역을 재는 `local_ipv4` 는 이 PC 이름을 DNS 로 푸는데, 그것이
    이벤트 루프 안에서 막히면 **이 PC 자신(localhost)의 요청까지** 기다리게 된다.
    """
    if not host:
        return False
    try:
        a = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    if a.is_loopback or a.is_private:
        return True
    if callable(nets):
        nets = nets()
    return any(a in n for n in nets if n.version == a.version)


def urls(port: int) -> list[str]:
    """다른 PC 가 들어올 주소 — PC 이름 먼저, 그 다음 IP (대시보드의 DEFAULT_SERVERS 와 같은 순서)."""
    out = []
    try:
        out.append(f"http://{socket.gethostname()}:{port}/")
    except OSError:
        pass
    out += [f"http://{ip}:{port}/" for ip in local_ipv4()]
    return out


class Gate:
    """ASGI 미들웨어 — 사내망 모드일 때만 주소를 본다.

    대역은 처음 요청 때 한 번 재고 들고 있는다 (요청마다 소켓을 열지 않는다).
    """

    def __init__(self, app, nets: list | None = None):
        self.app = app
        self._nets = nets

    def nets(self):
        if self._nets is None:
            self._nets = allowed_networks()
        return self._nets

    async def __call__(self, scope, receive, send):
        if scope.get("type") in ("http", "websocket") and enabled():
            client = scope.get("client") or (None, None)
            if not client_allowed(client[0], self.nets):
                if scope["type"] == "websocket":
                    await send({"type": "websocket.close", "code": 1008})
                    return
                body = ("사내망에서만 접속할 수 있습니다 "
                        "(P&ID 분석 서버 — 허용 대역은 PID_ALLOW 로 더할 수 있습니다).").encode("utf-8")
                await send({"type": "http.response.start", "status": 403,
                            "headers": [(b"content-type", b"text/plain; charset=utf-8"),
                                        (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)
