from starlette.responses import PlainTextResponse


class RequestBodyLimit:
    """Bound form bodies before Starlette parses or buffers them."""

    def __init__(self, app, max_bytes: int = 16_384):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # Only the authenticated PDF upload endpoint receives a larger envelope.
        pdf_upload = scope.get('method') == 'POST' and scope.get('path') == '/teacher/questions/import'
        limit = 10 * 1024 * 1024 + 65536 if pdf_upload else self.max_bytes
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
