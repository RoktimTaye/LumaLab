"""Private response caching and optional cross-origin access policy."""

from starlette.datastructures import MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class PrivateImageCache:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        private = path == "/api/v1/images" or path.startswith("/api/v1/images/")
        if scope["type"] != "http" or not private:
            await self.app(scope, receive, send)
            return

        async def no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, no_store)


def with_cors(app: ASGIApp, origins: tuple[str, ...]) -> ASGIApp:
    if not origins:
        return app
    # Wrap outside FastAPI's server-error layer so handled 500s also carry CORS.
    return PrivateImageCache(CORSMiddleware(
        app, allow_origins=list(origins), allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Image-Revision", "Content-Disposition"],
        allow_credentials=False,
    ))
