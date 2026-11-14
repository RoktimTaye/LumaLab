"""Image API handlers; processing and private storage remain in their modules."""

import logging
from pathlib import Path
import re
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.exceptions import HTTPException

from app.errors import error_response, http_error, validation_error
from app.schemas.errors import ErrorResponse
from app.schemas.images import Enhancement, ExportRequest, PreviewRequest, UploadedImage
from app.services.images import ImageError, enhance, normalize, render
from app.uploads import bounded_upload

logger = logging.getLogger("lumalab")
bearer = HTTPBearer(auto_error=False, description="Use the image-specific access_token returned by upload.")

CACHE_HEADERS = {"Cache-Control": {"description": "Always no-store.", "schema": {"type": "string", "const": "no-store"}}}
COMMON_ERRORS = {
    status: {"model": ErrorResponse, "description": description, "headers": CACHE_HEADERS}
    for status, description in {
        400: "Malformed multipart request.", 422: "Invalid request fields or undecodable image.",
        429: "Image processing is busy or session capacity is full.",
        500: "Image operation failed.", 503: "Private image storage is unavailable.",
    }.items()
}
SESSION_ERRORS = {
    status: {"model": ErrorResponse, "description": description, "headers": CACHE_HEADERS}
    for status, description in {
        401: "Missing or invalid image bearer token.", 404: "Image session unavailable, deleted or lost after restart.",
        410: "Authorized session has expired.",
    }.items()
}
SESSION_ERRORS[401] = {**SESSION_ERRORS[401], "headers": {
    **CACHE_HEADERS, "WWW-Authenticate": {"schema": {"type": "string", "const": "Bearer"}},
}}
JPEG_RESPONSE = {
    "description": "JPEG image bytes.", "headers": CACHE_HEADERS,
    "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
}


class ImageRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def guarded(request: Request):
            try:
                store = getattr(request.app.state, "image_store", None)
                if store is None:
                    raise ImageError(503, "service_unavailable", "Image storage is unavailable.")
                if not store.processing.acquire(blocking=False):
                    raise ImageError(429, "capacity_exceeded", "Image processing is busy. Try again shortly.")
                try:
                    if self.name == "upload" and request.method == "POST":
                        request = bounded_upload(request, request.app.state.settings.max_upload_bytes)
                    response = await handler(request)
                finally:
                    store.processing.release()
                response.headers["Cache-Control"] = "no-store"
                return response
            except RequestValidationError as caught:
                return await validation_error(request, caught)
            except HTTPException as caught:
                return await http_error(request, caught)
            except ImageError as caught:
                error = caught
            except Exception:
                logger.error("image_operation_failed")
                error = ImageError(500, "image_processing_failed", "Unable to complete the image operation.")
            headers = {"Cache-Control": "no-store"}
            if error.status == 401:
                headers["WWW-Authenticate"] = "Bearer"
            return error_response(error.status, error.code, error.message, headers)
        return guarded


router = APIRouter(prefix="/images", route_class=ImageRoute, tags=["Images"], responses=COMMON_ERRORS)


def access_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str:
    if credentials is None:
        raise ImageError(401, "unauthorized", "A valid image access token is required.")
    return credentials.credentials


Token = Annotated[str, Depends(access_token)]


@router.post("", status_code=201, response_model=UploadedImage, summary="Create a private image session",
             responses={201: {"description": "Image accepted and normalized.", "headers": CACHE_HEADERS},
                        413: {"model": ErrorResponse, "description": "Upload or decoded dimensions exceed limits.", "headers": CACHE_HEADERS},
                        415: {"model": ErrorResponse, "description": "Unsupported, animated or mismatched image format.", "headers": CACHE_HEADERS}})
def upload(request: Request, file: UploadFile):
    settings = request.app.state.settings
    try:
        data = file.file.read(settings.max_upload_bytes + 1)
    finally:
        file.file.close()
    if len(data) > settings.max_upload_bytes:
        raise ImageError(413, "upload_too_large", "Photograph exceeds the upload size limit.")
    filename = (file.filename or "image").replace("\\", "/").rsplit("/", 1)[-1][:128]
    image, detected = normalize(data, filename, settings)
    try:
        return request.app.state.image_store.create(data, image, filename, detected)
    finally:
        image.close()


@router.get("/{image_id}/original-preview", response_class=Response,
            summary="Read the normalized original preview",
            responses={**SESSION_ERRORS, 200: JPEG_RESPONSE})
def original_preview(image_id: str, request: Request, token: Token):
    with request.app.state.image_store.authorized(image_id, token) as session:
        data = render(session.directory / "normalized.png", None, request.app.state.settings, preview=True)
    return Response(data, media_type="image/jpeg")


@router.post("/{image_id}/preview", response_class=Response,
             summary="Render a preview from the original and complete adjustments",
             responses={**SESSION_ERRORS, 200: {**JPEG_RESPONSE, "headers": {
                 **CACHE_HEADERS, "X-Image-Revision": {"description": "Echo of the request revision.", "schema": {"type": "integer", "minimum": 0}},
             }}})
def preview(image_id: str, body: PreviewRequest, request: Request, token: Token):
    with request.app.state.image_store.authorized(image_id, token) as session:
        data = render(session.directory / "normalized.png", body.adjustments, request.app.state.settings, preview=True)
    return Response(data, media_type="image/jpeg", headers={"X-Image-Revision": str(body.revision)})


@router.post("/{image_id}/enhance", response_model=Enhancement,
             summary="Suggest complete adjustments from the original",
             responses={**SESSION_ERRORS, 200: {"headers": CACHE_HEADERS}})
def automatic_enhancement(image_id: str, request: Request, token: Token):
    with request.app.state.image_store.authorized(image_id, token) as session:
        return enhance(session.directory / "normalized.png")


@router.post("/{image_id}/export", response_class=Response,
             summary="Render a full-resolution JPEG attachment",
             responses={**SESSION_ERRORS, 200: {**JPEG_RESPONSE, "headers": {
                 **CACHE_HEADERS, "Content-Disposition": {"description": "Attachment with a sanitized JPEG filename.", "schema": {"type": "string"}},
             }}})
def export(image_id: str, body: ExportRequest, request: Request, token: Token):
    with request.app.state.image_store.authorized(image_id, token) as session:
        data = render(session.directory / "normalized.png", body.adjustments, request.app.state.settings,
                      preview=False, quality=body.quality)
        stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(session.filename).stem).strip("-")[:80] or "image"
    return Response(data, media_type="image/jpeg", headers={
        "Content-Disposition": f'attachment; filename="lumalab-{stem}.jpg"',
    })


@router.delete("/{image_id}", status_code=204, response_class=Response,
               summary="Delete a private image session",
               responses={**SESSION_ERRORS, 204: {"description": "Session files deleted; no response body.", "headers": CACHE_HEADERS}})
def delete(image_id: str, request: Request, token: Token):
    request.app.state.image_store.delete(image_id, token)
    return Response(status_code=204)
