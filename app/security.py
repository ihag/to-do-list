from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


MAX_REQUEST_BYTES = 1_100_000


class RequestBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        # JSON 검증 전에 누적 바이트 수를 제한해 큰 요청의 메모리 사용을 막는다.
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if len(body) + len(message.get("body", b"")) > MAX_REQUEST_BYTES:
                response = JSONResponse(
                    status_code=413, content={"detail": "Request body too large"}
                )
                await response(scope, receive, send)
                return
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break

        delivered = False

        async def receive_body():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, receive_body, send)


async def validation_error_response(request: Request, exc: RequestValidationError):
    # 비밀번호와 사용자 입력을 검증 오류 응답에 되돌려 보내지 않는다.
    errors = [
        {key: error[key] for key in ("type", "loc", "msg") if key in error}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # 인증 응답과 개인 목록은 브라우저·공유 캐시에 저장하지 않는다.
    path = request.scope["path"]
    if path in {"/signup", "/login", "/users/me"} or path.startswith(
        ("/todos", "/workspaces")
    ):
        response.headers["Cache-Control"] = "no-store"
    return response
