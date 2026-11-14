"""Bound multipart input before the framework parses or spools it."""

from fastapi import Request
from starlette.exceptions import HTTPException

MULTIPART_ALLOWANCE = 65_536


def bounded_upload(request: Request, max_file_bytes: int) -> Request:
    # File size is checked separately; this allowance bounds multipart overhead.
    limit = max_file_bytes + MULTIPART_ALLOWANCE
    declared = request.headers.get("content-length", "")
    if declared.isdecimal() and int(declared) > limit:
        raise HTTPException(413)
    received = 0

    async def receive():
        nonlocal received
        message = await request.receive()
        if message["type"] == "http.request":
            received += len(message.get("body", b""))
            if received > limit:
                raise HTTPException(413)
        return message

    return Request(request.scope, receive)
