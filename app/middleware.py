import re
from starlette.responses import PlainTextResponse
from starlette.datastructures import MutableHeaders, Headers

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}


class SecurityHeaders:
    """Cover redirects, validation errors and early body-limit responses too."""
    def __init__(self, app, hsts=False):
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def secured_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    # FastAPI's optional API documentation supplies its own inline/CDN
                    # assets. Preserve that existing documentation page behavior.
                    if name == 'Content-Security-Policy' and scope.get('path') in ('/docs', '/redoc', '/docs/oauth2-redirect'):
                        continue
                    headers[name] = value
                if self.hsts and scope.get('scheme') == 'https':
                    headers['Strict-Transport-Security'] = 'max-age=31536000'
                if not scope.get("path", "").startswith("/static/"):
                    headers["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, secured_send)


class RequestBodyLimit:
    """Bound form bodies before Starlette parses or buffers them."""

    def __init__(self, app, max_bytes: int = 16_384):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # Bound URL-encoded Unicode fields without widening unrelated forms.
        pdf_upload = scope.get('method') == 'POST' and scope.get('path') == '/teacher/questions/import'
        question_form = scope.get('method') == 'POST' and bool(re.fullmatch(
            r'/teacher/questions/(?:new|[0-9]+/edit)', scope.get('path', '')))
        image_upload = question_form and Headers(scope=scope).get('content-type', '').lower().startswith('multipart/form-data')
        limit = 10 * 1024 * 1024 + 65536 if pdf_upload else (4 * 1024 * 1024 + 192 * 1024 if image_upload else (192 * 1024 if question_form else self.max_bytes))
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > limit:
                response = PlainTextResponse("PDF upload is too large. Use a PDF under 10 MB." if pdf_upload else "Form is too large. Shorten the input and try again.", status_code=413)
                return await response(scope, receive, send)
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def limited_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, limited_receive, send)
