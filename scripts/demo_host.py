"""Single-process Render demo launcher, not a production course entry point."""
from collections import deque
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class DemoLimits:
    """Bound all dynamic traffic and admitted writes without trusting client IPs.

    One ASGI worker; counters are updated without an await, on its event loop.
    Rejected requests do not allocate per-client state or consume request bodies.
    """
    allowed = re.compile(
        r'/(?:login|logout|student/(?:goal|check-in|questions/[0-9]+/(?:answer|bookmark)|'
        r'assignments/[0-9]+/questions/[0-9]+/answer)|teacher/(?:'
        r'groups/[0-9]+/lessons|lessons/[0-9]+/(?:close|reopen|finish)|'
        r'enrollments/[0-9]+/renew))')

    def __init__(self, app, clock=time.monotonic, request_limit=300, write_limit=60, lifetime_limit=5000):
        self.app, self.clock = app, clock
        self.requests, self.writes = deque(), deque()
        self.request_limit, self.write_limit = request_limit, write_limit
        self.lifetime_limit, self.total = lifetime_limit, 0

    async def __call__(self, scope, receive, send):
        from starlette.responses import HTMLResponse
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        path = scope.get('path', '').rstrip('/')
        safe = scope['method'] in ('GET', 'HEAD', 'OPTIONS')
        status, message = None, ''
        if not safe and (scope['method'] != 'POST' or not self.allowed.fullmatch(path)):
            status, message = 403, 'This action is unavailable in the public demo. Try practice, check-in, lesson controls or renewals.'
        elif not (safe and (path == '/healthz' or path.startswith('/static/'))):
            now = self.clock()
            for queue in (self.requests, self.writes):
                while queue and queue[0] <= now - 60:
                    queue.popleft()
            if len(self.requests) >= self.request_limit or (not safe and len(self.writes) >= self.write_limit):
                status, message = 429, 'The shared demo is busy. Wait one minute and try again.'
            elif not safe and self.total >= self.lifetime_limit:
                status, message = 503, 'The demo activity limit has been reached. Browsing remains available; the owner must restart the demo to reset it.'
            else:
                self.requests.append(now)
                if not safe:
                    self.writes.append(now)
                    self.total += 1
        if status:
            response = HTMLResponse(f'<h1>Portfolio demo</h1><p>{message}</p><a href="/login">Return to demo access</a>',
                status_code=status, headers={'Cache-Control':'no-store', **({'Retry-After':'60'} if status == 429 else {})})
            return await response(scope, receive, send)
        await self.app(scope, receive, send)


def settings(environ):
    if environ.get('RENDER') != 'true' or environ.get('SAT_FACTORY_PUBLIC_DEMO') != '1':
        raise ValueError('Public demo requires Render and explicit SAT_FACTORY_PUBLIC_DEMO=1.')
    host = environ.get('RENDER_EXTERNAL_HOSTNAME', '')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.onrender\.com', host):
        raise ValueError('A Render-assigned onrender.com hostname is required.')
    port = int(environ.get('PORT', '10000'))
    if not 1024 <= port <= 65535:
        raise ValueError('PORT must be between 1024 and 65535.')
    return host, port


def main():
    import uvicorn
    from scripts.portfolio_demo import portfolio_demo
    host, port = settings(os.environ)
    with portfolio_demo(public=True, allowed_hosts=[host, '127.0.0.1', 'localhost']) as app:
        # Render terminates TLS and forwards traffic to the bound port. This trust
        # is appropriate only behind that platform proxy, never on a bare VPS.
        uvicorn.run(app, host='0.0.0.0', port=port, workers=1, access_log=False,
                    proxy_headers=True, forwarded_allow_ips='*', limit_concurrency=20,
                    timeout_keep_alive=5)


if __name__ == '__main__':
    main()
