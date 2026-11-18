"""SPA navigation fallback, without masking missing API or asset responses."""

from pathlib import PurePosixPath

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class FrontendStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code != 404:
                return response
        except HTTPException as error:
            if error.status_code != 404:
                raise
        navigation_path = PurePosixPath(path.replace("\\", "/").lstrip("/"))
        parts = navigation_path.parts
        if (scope["method"] in {"GET", "HEAD"}
                and (not parts or parts[0] not in {"api", "assets", "images", "fonts", ".well-known"})
                and not any(part.startswith(".") for part in parts)
                and not navigation_path.suffix):
            return await super().get_response("index.html", scope)
        raise HTTPException(status_code=404)
