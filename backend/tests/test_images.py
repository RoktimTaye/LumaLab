"""Real image workflow through ASGI, using private temporary storage and no database."""

import asyncio
from base64 import urlsafe_b64decode
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
from threading import Event, Thread
import unittest
from unittest.mock import patch
import warnings

from fastapi import FastAPI, Response
from PIL import Image, ImageCms, PngImagePlugin

from app.config import RUNTIME_DIR, Settings
from app.errors import EXCEPTION_HANDLERS
from app.middleware import PrivateImageCache, with_cors
from app.routes import router
from app.schemas.errors import ErrorResponse
from app.schemas.images import Enhancement, UploadedImage
from app.storage.images import ImageStore
from app.uploads import MULTIPART_ALLOWANCE

NEUTRAL = dict(brightness=100, contrast=100, saturation=100, warmth=0, sharpness=0, vignette=0)


class ImageTests(unittest.TestCase):
    def setUp(self):
        RUNTIME_DIR.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="test-c01-", dir=RUNTIME_DIR)
        self.addCleanup(self.temporary.cleanup)
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None, database_url="postgresql://test:secret@db.invalid/db?sslmode=require",
                                preview_max_edge=32)
        self.app = FastAPI(exception_handlers=EXCEPTION_HANDLERS)
        self.app.add_middleware(PrivateImageCache)
        self.app.include_router(router)
        self.app.state.settings = settings
        self.app.state.image_store = ImageStore(Path(self.temporary.name), settings)

    def request(self, method, path, body=b"", content_type=None, token=None, *, extra_headers=(), query_string=b"", chunks=None):
        async def run():
            sent = []
            headers = list(extra_headers)
            if content_type:
                headers.append((b"content-type", content_type.encode()))
            if token is not None:
                headers.append((b"authorization", f"Bearer {token}".encode()))
            pending = iter(chunks) if chunks is not None else None
            async def receive():
                if pending is not None:
                    chunk = next(pending)
                    return {"type": "http.request", "body": chunk, "more_body": True}
                return {"type": "http.request", "body": body, "more_body": False}
            async def send(message):
                sent.append(message)
            await getattr(self, "asgi_app", self.app)({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                            "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                            "query_string": query_string, "root_path": "", "headers": headers,
                            "server": ("localhost", 8000), "client": ("localhost", 12345)}, receive, send)
            start = next(item for item in sent if item["type"] == "http.response.start")
            self.assertEqual(dict(start["headers"])[b"cache-control"], b"no-store")
            return start["status"], dict(start["headers"]), b"".join(item.get("body", b"") for item in sent)
        return asyncio.run(run())

    def upload(self, data=None, filename="photo.png"):
        if data is None:
            output = BytesIO()
            Image.new("RGB", (80, 40), (120, 80, 40)).save(output, "PNG")
            data = output.getvalue()
        body = (f'--test\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                'Content-Type: application/octet-stream\r\n\r\n').encode() + data + b"\r\n--test--\r\n"
        return self.request("POST", "/api/v1/images", body, "multipart/form-data; boundary=test")

    def test_upload_preview_enhance_export_and_delete(self):
        status, _, body = self.upload()
        self.assertEqual(status, 201)
        session = json.loads(body)
        UploadedImage.model_validate_json(body)
        self.assertEqual((session["width"], session["height"], session["format"]), (80, 40, "PNG"))
        token = session["access_token"]
        path = "/api/v1/images/" + session["image_id"]
        status, _, original = self.request("GET", path + "/original-preview", token=token)
        self.assertEqual(status, 200)
        with Image.open(BytesIO(original)) as image:
            self.assertEqual(image.size, (32, 16))
        status, headers, edited = self.request("POST", path + "/preview",
            json.dumps({"revision": 7, "adjustments": NEUTRAL}).encode(), "application/json", token)
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"x-image-revision"], b"7")
        self.assertEqual(edited, original)
        status, _, enhanced = self.request("POST", path + "/enhance", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(set(json.loads(enhanced)["adjustments"]), set(NEUTRAL))
        Enhancement.model_validate_json(enhanced)
        self.assertEqual(self.request("POST", path + "/enhance", token=token)[2], enhanced)
        status, headers, exported = self.request("POST", path + "/export",
            json.dumps({"adjustments": {**NEUTRAL, "brightness": 150}, "format": "jpeg", "quality": 92}).encode(),
            "application/json", token)
        self.assertEqual(status, 200)
        self.assertIn(b"attachment", headers[b"content-disposition"])
        with Image.open(BytesIO(exported)) as image:
            self.assertEqual(image.size, (80, 40))
            self.assertFalse(image.getexif())
        self.assertEqual(self.request("DELETE", path, token=token)[0], 204)
        self.assertEqual(self.request("GET", path + "/original-preview", token=token)[0], 404)
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_replacement_then_explicit_closure_deletes_only_selected_session(self):
        first = json.loads(self.upload()[2])
        replacement = BytesIO()
        Image.new("RGB", (16, 8), "blue").save(replacement, "PNG")
        status, _, body = self.upload(replacement.getvalue(), "replacement.png")
        self.assertEqual(status, 201)
        second = json.loads(body)
        first_path = "/api/v1/images/" + first["image_id"]
        second_path = "/api/v1/images/" + second["image_id"]
        first_dir = self.app.state.image_store.sessions[first["image_id"]].directory
        second_dir = self.app.state.image_store.sessions[second["image_id"]].directory
        self.assertEqual(self.request("GET", first_path + "/original-preview", token=first["access_token"])[0], 200)
        self.assertEqual(self.request("DELETE", first_path, token=second["access_token"])[0], 401)
        self.assertTrue(first_dir.exists())
        self.assertEqual(self.request("DELETE", first_path, token=first["access_token"])[0], 204)
        self.assertFalse(first_dir.exists())
        self.assertEqual(self.request("GET", first_path + "/original-preview", token=first["access_token"])[0], 404)
        self.assertEqual(self.request("GET", second_path + "/original-preview", token=second["access_token"])[0], 200)
        self.assertEqual((second_dir / "original").read_bytes(), replacement.getvalue())
        self.assertEqual(self.request("DELETE", second_path, token=second["access_token"])[0], 204)
        self.assertFalse(second_dir.exists())
        self.assertEqual(self.request("DELETE", second_path, token=second["access_token"])[0], 404)
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_original_upload_bytes_remain_separate_and_unchanged_through_editing(self):
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        for format_name, extension in (("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")):
            with self.subTest(format=format_name):
                output = BytesIO()
                exif = Image.Exif()
                exif[274] = 6
                exif[270] = "original-upload-description"
                image = Image.new("RGB" if format_name == "JPEG" else "RGBA", (80, 40), (120, 80, 40))
                image.save(output, format_name, exif=exif, icc_profile=profile)
                uploaded = output.getvalue()
                status, _, body = self.upload(uploaded, "photo." + extension)
                self.assertEqual(status, 201)
                session = json.loads(body)
                directory = self.app.state.image_store.sessions[session["image_id"]].directory
                original, normalized = directory / "original", directory / "normalized.png"
                self.assertFalse(original.samefile(normalized))
                baseline = normalized.read_bytes()
                self.assertEqual(original.read_bytes(), uploaded)
                self.assertNotEqual(baseline, uploaded)
                with Image.open(original) as preserved:
                    self.assertEqual((preserved.format, preserved.size), (format_name, (80, 40)))
                    self.assertEqual(preserved.getexif()[274], 6)
                    self.assertEqual(preserved.getexif()[270], "original-upload-description")
                    self.assertEqual(preserved.info["icc_profile"], profile)
                path, token = "/api/v1/images/" + session["image_id"], session["access_token"]
                adjusted = {**NEUTRAL, "brightness": 150, "warmth": 15}
                previews = []
                for method, suffix, payload in (
                    ("GET", "/original-preview", None),
                    ("POST", "/preview", {"revision": 1, "adjustments": adjusted}),
                    ("POST", "/enhance", None),
                    ("POST", "/export", {"adjustments": adjusted}),
                    ("GET", "/original-preview", None),
                ):
                    status, _, result = self.request(method, path + suffix,
                        json.dumps(payload).encode() if payload else b"",
                        "application/json" if payload else None, token)
                    self.assertEqual(status, 200)
                    if suffix in ("/original-preview", "/preview"):
                        previews.append(result)
                    self.assertEqual(original.read_bytes(), uploaded)
                    self.assertEqual(normalized.read_bytes(), baseline)
                self.assertNotEqual(previews[0], previews[1])
                self.assertEqual(previews[0], previews[2])
                self.assertEqual(self.request("DELETE", path, token=token)[0], 204)

    def test_upload_ids_and_secret_tokens_are_separate_and_only_hashes_are_stored(self):
        ids, tokens = set(), set()
        for _ in range(3):
            status, _, body = self.upload(filename="same-photo.png")
            self.assertEqual(status, 201)
            session = json.loads(body)
            image_id, token = session["image_id"], session["access_token"]
            self.assertRegex(image_id, r"^[0-9a-f]{32}$")
            self.assertRegex(token, r"^[A-Za-z0-9_-]{43}$")
            self.assertEqual(len(urlsafe_b64decode(token + "=")), 32)
            self.assertNotEqual(image_id, token)
            self.assertNotIn(image_id, ids)
            self.assertNotIn(token, tokens)
            stored = self.app.state.image_store.sessions[image_id]
            self.assertEqual(stored.token_hash, sha256(token.encode()).digest())
            self.assertNotIn(token, repr(stored))
            self.assertEqual(stored.directory.name, image_id)
            ids.add(image_id)
            tokens.add(token)
        self.assertTrue(ids.isdisjoint(tokens))

    def test_submitted_filenames_cannot_choose_or_overwrite_storage_paths(self):
        output = BytesIO()
        Image.new("RGB", (8, 4), "red").save(output, "PNG")
        data = output.getvalue()
        root = Path(self.temporary.name).resolve()
        directories = set()
        for filename in ("../../outside.png", "..\\..\\outside.png", "/absolute/photo.png",
                         "C:\\photos\\photo.png", "\\\\server\\share\\photo.png",
                         "name:stream.png", "original.png", "normalized.png", "same.png", "same.png"):
            with self.subTest(filename=filename):
                status, _, body = self.upload(data, filename)
                self.assertEqual(status, 201)
                session = json.loads(body)
                directory = self.app.state.image_store.sessions[session["image_id"]].directory.resolve()
                self.assertEqual(directory, root / session["image_id"])
                self.assertNotIn(directory, directories)
                self.assertEqual(session["filename"], filename.replace("\\", "/").rsplit("/", 1)[-1])
                self.assertEqual({file.name for file in directory.iterdir()}, {"original", "normalized.png"})
                directories.add(directory)
                self.assertEqual(set(root.iterdir()), directories)
                for existing in directories:
                    self.assertEqual((existing / "original").read_bytes(), data)

    def test_private_files_have_no_public_route_or_generated_file_url(self):
        status, _, body = self.upload()
        self.assertEqual(status, 201)
        session = json.loads(body)
        stored = self.app.state.image_store.sessions[session["image_id"]]
        self.assertTrue(stored.directory.is_relative_to(RUNTIME_DIR))
        for filename in ("original", "normalized.png", "preview.jpg", "export.jpg"):
            for prefix in ("/static/", "/public/", "/.runtime/", "/api/v1/images/"):
                for token in (None, session["access_token"]):
                    status, _, result = self.request("GET", prefix + session["image_id"] + "/" + filename, token=token)
                    self.assertEqual(status, 404)
                    self.assertNotIn(stored.directory.as_posix().encode(), result)
        self.assertNotIn(b"url", body)
        self.assertNotIn(str(stored.directory).encode(), body)
        for method, suffix, payload in (("GET", "/original-preview", None),
                ("POST", "/preview", {"revision": 1, "adjustments": NEUTRAL}),
                ("POST", "/export", {"adjustments": NEUTRAL})):
            status, _, result = self.request(method, "/api/v1/images/" + session["image_id"] + suffix,
                json.dumps(payload).encode() if payload else b"", "application/json" if payload else None,
                session["access_token"])
            self.assertEqual(status, 200)
            self.assertTrue(result.startswith(b"\xff\xd8"))
        self.assertEqual({file.name for file in stored.directory.iterdir()}, {"original", "normalized.png"})

    def test_cleanup_and_deletion_wait_for_active_image_use(self):
        store = self.app.state.image_store
        for action in ("cleanup", "deletion"):
            with self.subTest(action=action):
                session = json.loads(self.upload()[2])
                image_id, token = session["image_id"], session["access_token"]
                directory = store.sessions[image_id].directory
                completed = Event()

                def finish():
                    try:
                        if action == "cleanup":
                            store.purge_expired()
                        else:
                            store.delete(image_id, token)
                    finally:
                        completed.set()

                with store.authorized(image_id, token):
                    if action == "cleanup":
                        store.sessions[image_id].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                    worker = Thread(target=finish)
                    worker.start()
                    self.assertFalse(completed.wait(0.05))
                    self.assertTrue((directory / "normalized.png").exists())
                self.assertTrue(completed.wait(2))
                worker.join(timeout=2)
                self.assertFalse(directory.exists())
                self.assertNotIn(image_id, store.sessions)

    def test_authorization_validation_expiry_and_capacity(self):
        session = json.loads(self.upload()[2])
        path = "/api/v1/images/" + session["image_id"]
        for suffix, method in (("/original-preview", "GET"), ("/enhance", "POST"), ("", "DELETE")):
            self.assertEqual(self.request(method, path + suffix)[0], 401)
            self.assertEqual(self.request(method, path + suffix, token="wrong")[0], 401)
        invalid = json.dumps({"revision": 1, "adjustments": {**NEUTRAL, "warmth": 1.5}}).encode()
        self.assertEqual(self.request("POST", path + "/preview", invalid, "application/json", session["access_token"])[0], 422)
        store = self.app.state.image_store
        store.processing.acquire()
        try:
            self.assertEqual(self.upload()[0], 429)
        finally:
            store.processing.release()
        store.sessions[session["image_id"]].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertEqual(self.request("GET", path + "/original-preview", token=session["access_token"])[0], 410)

    def test_upload_time_and_expiry_are_fixed_for_sixty_minutes(self):
        before = datetime.now(timezone.utc)
        status, _, body = self.upload()
        after = datetime.now(timezone.utc)
        self.assertEqual(status, 201)
        session = UploadedImage.model_validate_json(body)
        stored = self.app.state.image_store.sessions[session.image_id]
        self.assertLessEqual(before, stored.uploaded_at)
        self.assertLessEqual(stored.uploaded_at, after)
        self.assertEqual(stored.uploaded_at.utcoffset(), timedelta(0))
        self.assertEqual(stored.expires_at, stored.uploaded_at + timedelta(minutes=60))
        self.assertEqual(session.expires_at, stored.expires_at)
        path = "/api/v1/images/" + session.image_id
        expiry = stored.expires_at
        for method, suffix, payload in (("GET", "/original-preview", None),
                ("POST", "/preview", {"revision": 1, "adjustments": NEUTRAL}),
                ("POST", "/enhance", None),
                ("POST", "/export", {"adjustments": NEUTRAL})):
            status, _, _ = self.request(method, path + suffix,
                json.dumps(payload).encode() if payload else b"",
                "application/json" if payload else None, session.access_token)
            self.assertEqual(status, 200)
            self.assertEqual(stored.uploaded_at + timedelta(minutes=60), expiry)
            self.assertEqual(stored.expires_at, expiry)
        with patch("app.storage.images.datetime") as clock:
            clock.now.return_value = expiry - timedelta(microseconds=1)
            self.assertEqual(self.request("GET", path + "/original-preview", token=session.access_token)[0], 200)
            clock.now.return_value = expiry
            status, _, body = self.request("GET", path + "/original-preview", token=session.access_token)
        self.assertEqual(status, 410)
        self.assertEqual(json.loads(body)["error"]["code"], "image_expired")

    def test_upload_rejection_leaves_no_files(self):
        self.assertEqual(self.upload(b"corrupt")[0], 422)
        self.assertEqual(self.upload(filename="photo.gif")[0], 415)
        self.app.state.settings = self.app.state.settings.model_copy(update={"max_upload_bytes": 10})
        self.assertEqual(self.upload()[0], 413)
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_openapi_has_all_eight_operations_and_bearer_security(self):
        paths = self.app.openapi()["paths"]
        self.assertEqual(sum(len(methods) for methods in paths.values()), 8)
        self.assertIn("multipart/form-data", paths["/api/v1/images"]["post"]["requestBody"]["content"])
        for path, methods in paths.items():
            if "{image_id}" in path:
                for operation in methods.values():
                    self.assertTrue(operation["security"])

    def test_documented_image_payloads_headers_and_errors_match_runtime(self):
        document = self.app.openapi()
        paths = document["paths"]
        upload = paths["/api/v1/images"]["post"]
        self.assertEqual(upload["responses"]["201"]["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/UploadedImage")
        for suffix, method, request_model in (("preview", "post", "PreviewRequest"), ("export", "post", "ExportRequest")):
            operation = paths[f"/api/v1/images/{{image_id}}/{suffix}"][method]
            self.assertEqual(operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
                             f"#/components/schemas/{request_model}")
        for suffix, method in (("original-preview", "get"), ("preview", "post"), ("export", "post")):
            response = paths[f"/api/v1/images/{{image_id}}/{suffix}"][method]["responses"]["200"]
            self.assertEqual(response["content"], {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}})
        preview = paths["/api/v1/images/{image_id}/preview"]["post"]["responses"]["200"]
        self.assertIn("X-Image-Revision", preview["headers"])
        export = paths["/api/v1/images/{image_id}/export"]["post"]["responses"]["200"]
        self.assertIn("Content-Disposition", export["headers"])
        deleted = paths["/api/v1/images/{image_id}"]["delete"]["responses"]["204"]
        self.assertNotIn("content", deleted)
        for path, methods in paths.items():
            if path.startswith("/api/v1/images"):
                for operation in methods.values():
                    self.assertEqual(operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"],
                                     "#/components/schemas/ErrorResponse")
        status, _, body = self.upload(b"invalid")
        self.assertEqual(status, 422)
        self.assertEqual(ErrorResponse.model_validate_json(body).error.code, "invalid_image")
        metadata = document["components"]["schemas"]["UploadedImage"]["properties"]
        self.assertEqual(metadata["format"]["enum"], ["JPEG", "PNG", "WEBP"])
        self.assertEqual(metadata["width"]["exclusiveMinimum"], 0)
        self.assertEqual(metadata["expires_at"]["format"], "date-time")

    def test_preview_and_export_reject_invalid_adjustments_before_rendering(self):
        session = json.loads(self.upload()[2])
        bounds = {"brightness": (0, 200), "contrast": (0, 200), "saturation": (0, 200),
                  "warmth": (-50, 50), "sharpness": (0, 100), "vignette": (0, 100)}
        invalid = [{**NEUTRAL, "unexpected": 1}]
        for field, (minimum, maximum) in bounds.items():
            invalid.extend({**NEUTRAL, field: value}
                           for value in (minimum - 1, maximum + 1, 1.5, 1.0, "1", True, None))
            invalid.append({key: value for key, value in NEUTRAL.items() if key != field})
        with patch("app.routes.images.render") as render:
            for operation in ("preview", "export"):
                for adjustments in invalid:
                    body = {"adjustments": adjustments}
                    if operation == "preview":
                        body["revision"] = 1
                    with self.subTest(operation=operation, adjustments=adjustments):
                        status, _, response = self.request("POST",
                            f'/api/v1/images/{session["image_id"]}/{operation}',
                            json.dumps(body).encode(), "application/json", session["access_token"])
                        self.assertEqual(status, 422)
                        self.assertEqual(json.loads(response)["error"]["code"], "invalid_request")
            render.assert_not_called()

    def test_upload_requires_a_multipart_file_part_named_file(self):
        multipart = b'--test\r\nContent-Disposition: form-data; name="photo"; filename="photo.png"\r\n\r\ninvalid\r\n--test--\r\n'
        text_part = b'--test\r\nContent-Disposition: form-data; name="file"\r\n\r\nnot-a-file\r\n--test--\r\n'
        cases = ((b'{}', "application/json", 422), (b"raw", "image/png", 422),
                 (multipart, "multipart/form-data; boundary=test", 422),
                 (text_part, "multipart/form-data; boundary=test", 422),
                 (b"invalid", "multipart/form-data", 400))
        with patch("app.routes.images.normalize") as normalize:
            for body, media_type, expected in cases:
                with self.subTest(media_type=media_type, body=body):
                    status, _, response = self.request("POST", "/api/v1/images", body, media_type)
                    self.assertEqual(status, expected)
                    self.assertEqual(json.loads(response)["error"]["code"], "invalid_request")
            normalize.assert_not_called()
        self.assertFalse(self.app.state.image_store.sessions)
        document = self.app.openapi()
        content = document["paths"]["/api/v1/images"]["post"]["requestBody"]["content"]
        self.assertEqual(set(content), {"multipart/form-data"})
        reference = content["multipart/form-data"]["schema"]["$ref"].rsplit("/", 1)[-1]
        schema = document["components"]["schemas"][reference]
        self.assertEqual(schema["required"], ["file"])
        self.assertEqual(schema["properties"]["file"]["type"], "string")
        self.assertEqual(schema["properties"]["file"]["contentMediaType"], "application/octet-stream")

    def test_preview_export_require_json_and_accept_json_with_charset(self):
        session = json.loads(self.upload()[2])
        for operation in ("preview", "export"):
            body = {"adjustments": NEUTRAL}
            if operation == "preview":
                body["revision"] = 1
            encoded = json.dumps(body).encode()
            path = f'/api/v1/images/{session["image_id"]}/{operation}'
            invalid = ((encoded, None), (encoded, "text/plain"),
                       (encoded, "application/x-www-form-urlencoded"),
                       (b"--test--\r\n", "multipart/form-data; boundary=test"),
                       (b'{"adjustments":', "application/json"))
            with patch("app.routes.images.render") as render:
                for data, media_type in invalid:
                    with self.subTest(operation=operation, media_type=media_type):
                        status, _, response = self.request("POST", path, data, media_type, session["access_token"])
                        self.assertEqual(status, 422)
                        self.assertEqual(json.loads(response)["error"]["code"], "invalid_request")
                render.assert_not_called()
            self.assertEqual(self.request("POST", path, encoded, "application/json; charset=utf-8",
                                          session["access_token"])[0], 200)
            content = self.app.openapi()["paths"][path.replace(session["image_id"], "{image_id}")]["post"]["requestBody"]["content"]
            self.assertEqual(set(content), {"application/json"})

    def test_all_image_operations_reject_wrong_cross_session_and_malformed_tokens(self):
        first = json.loads(self.upload()[2])
        second = json.loads(self.upload()[2])
        operations = (("GET", "/original-preview", None),
                      ("POST", "/preview", {"revision": 1, "adjustments": NEUTRAL}),
                      ("POST", "/enhance", None),
                      ("POST", "/export", {"adjustments": NEUTRAL}), ("DELETE", "", None))
        credentials = ((), ((b"authorization", b"Bearer wrong-token"),),
                       ((b"authorization", f'Bearer {second["access_token"]}'.encode()),),
                       ((b"authorization", f'Bearer {first["image_id"]}'.encode()),),
                       ((b"authorization", b"Basic invalid"),),
                       ((b"authorization", b"Bearer"),), ((b"authorization", b"Bearer "),),
                       ((b"authorization", f'Bearer {first["access_token"]} extra'.encode()),))
        with patch("app.routes.images.render") as render, patch("app.routes.images.enhance") as enhance:
            for method, suffix, payload in operations:
                body = json.dumps(payload).encode() if payload is not None else b""
                media_type = "application/json" if payload is not None else None
                for index, headers in enumerate(credentials):
                    with self.subTest(operation=suffix or "delete", credential_case=index):
                        status, response_headers, response = self.request(method,
                            f'/api/v1/images/{first["image_id"]}{suffix}', body, media_type, extra_headers=headers)
                        self.assertEqual(status, 401)
                        self.assertEqual(response_headers[b"www-authenticate"], b"Bearer")
                        self.assertEqual(json.loads(response)["error"]["code"], "unauthorized")
                        self.assertNotIn(first["access_token"].encode(), response)
                        self.assertNotIn(second["access_token"].encode(), response)
            render.assert_not_called()
            enhance.assert_not_called()
        self.assertEqual(len(self.app.state.image_store.sessions), 2)
        self.assertTrue(all(session.directory.exists() for session in self.app.state.image_store.sessions.values()))
        self.assertNotEqual(first["access_token"], second["access_token"])
        self.assertEqual(self.request("GET", f'/api/v1/images/{first["image_id"]}/original-preview',
            extra_headers=((b"authorization", f'bEaReR {first["access_token"]}'.encode()),))[0], 200)

    def test_tokens_in_query_cookie_or_json_do_not_authorize_image_access(self):
        session = json.loads(self.upload()[2])
        path = f'/api/v1/images/{session["image_id"]}'
        token = session["access_token"]
        query = f'access_token={token}&token={token}'.encode()
        for method, suffix, payload in (("GET", "/original-preview", None),
                ("POST", "/preview", {"revision": 1, "adjustments": NEUTRAL}),
                ("POST", "/enhance", None), ("POST", "/export", {"adjustments": NEUTRAL}),
                ("DELETE", "", None)):
            with self.subTest(operation=suffix or "delete"):
                status, _, body = self.request(method, path + suffix,
                    json.dumps({**payload, "access_token": token}).encode() if payload else b"",
                    "application/json" if payload else None, query_string=query,
                    extra_headers=((b"cookie", f'access_token={token}'.encode()),))
                self.assertEqual(status, 401)
                self.assertNotIn(token.encode(), body)
        stored = self.app.state.image_store.sessions[session["image_id"]]
        self.assertNotIn(token, repr(stored))
        self.assertTrue(stored.directory.exists())
        for file in stored.directory.iterdir():
            self.assertNotIn(token.encode(), file.read_bytes())
        document = self.app.openapi()
        for endpoint, methods in document["paths"].items():
            if "{image_id}" in endpoint:
                for operation in methods.values():
                    self.assertEqual(operation["security"], [{"HTTPBearer": []}])
                    self.assertTrue(all(parameter["name"] == "image_id" and parameter["in"] == "path"
                                        for parameter in operation["parameters"]))
        self.assertNotIn("security", document["paths"]["/api/v1/images"]["post"])

    def test_image_endpoints_return_direct_jpeg_bytes(self):
        session = json.loads(self.upload()[2])
        for method, suffix, payload in (("GET", "original-preview", None),
                ("POST", "preview", {"revision": 1, "adjustments": NEUTRAL}),
                ("POST", "export", {"adjustments": NEUTRAL})):
            with self.subTest(operation=suffix):
                status, headers, data = self.request(method,
                    f'/api/v1/images/{session["image_id"]}/{suffix}',
                    json.dumps(payload).encode() if payload else b"",
                    "application/json" if payload else None, session["access_token"])
                self.assertEqual(status, 200)
                self.assertEqual(headers[b"content-type"], b"image/jpeg")
                self.assertEqual(int(headers[b"content-length"]), len(data))
                self.assertTrue(data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9"))
                self.assertNotIn(b"location", headers)
                with Image.open(BytesIO(data)) as image:
                    self.assertEqual(image.format, "JPEG")

    def test_expiry_restart_loss_and_empty_deletion_statuses(self):
        session = json.loads(self.upload()[2])
        path = f'/api/v1/images/{session["image_id"]}'
        store = self.app.state.image_store
        self.app.state.image_store = ImageStore(store.directory, store.settings)
        try:
            status, _, body = self.request("GET", path + "/original-preview", token=session["access_token"])
            self.assertEqual((status, json.loads(body)["error"]["code"]), (404, "image_unavailable"))
        finally:
            self.app.state.image_store = store
        store.sessions[session["image_id"]].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertEqual(self.request("GET", path + "/original-preview", token="wrong")[0], 401)
        status, _, body = self.request("GET", path + "/original-preview", token=session["access_token"])
        self.assertEqual((status, json.loads(body)["error"]["code"]), (410, "image_expired"))
        fresh = json.loads(self.upload()[2])
        status, headers, body = self.request("DELETE", f'/api/v1/images/{fresh["image_id"]}', token=fresh["access_token"])
        self.assertEqual((status, body), (204, b""))
        self.assertNotIn(b"content-type", headers)

    def test_full_capacity_and_missing_storage_are_recoverable(self):
        for _ in range(32):
            status, _, body = self.upload()
            self.assertEqual(status, 201)
        last = json.loads(body)
        status, _, body = self.upload()
        self.assertEqual((status, json.loads(body)["error"]["code"]), (429, "capacity_exceeded"))
        self.assertEqual(len(self.app.state.image_store.sessions), 32)
        self.assertEqual(self.request("DELETE", f'/api/v1/images/{last["image_id"]}', token=last["access_token"])[0], 204)
        self.assertEqual(self.upload()[0], 201)
        store = self.app.state.image_store
        self.app.state.image_store = None
        try:
            status, _, body = self.upload()
            self.assertEqual((status, json.loads(body)["error"]["code"]), (503, "service_unavailable"))
        finally:
            self.app.state.image_store = store

    def test_partial_original_and_normalized_writes_are_removed(self):
        output = BytesIO()
        Image.new("RGB", (8, 4), "red").save(output, "PNG")
        data = output.getvalue()
        original_write = Path.write_bytes

        def fail_original(path, contents):
            original_write(path, contents[:8])
            raise OSError("private partial original")

        def fail_normalized(image, path, **options):
            Path(path).write_bytes(b"partial normalized")
            raise OSError("private partial normalized")

        for failure in (patch.object(Path, "write_bytes", fail_original),
                        patch.object(Image.Image, "save", fail_normalized)):
            with failure, self.assertLogs("lumalab", level="ERROR"):
                status, _, body = self.upload(data)
            self.assertEqual(status, 500)
            self.assertEqual(json.loads(body)["error"]["code"], "image_processing_failed")
            self.assertNotIn(b"private partial", body)
            self.assertEqual(self.app.state.image_store.sessions, {})
            self.assertEqual(list(Path(self.temporary.name).iterdir()), [])
        self.assertEqual(self.upload()[0], 201)

    def test_upload_failures_have_documented_statuses_and_clean_partial_files(self):
        status, _, body = self.upload(b"invalid")
        self.assertEqual((status, json.loads(body)["error"]["code"]), (422, "invalid_image"))
        self.assertEqual(self.upload(filename="photo.gif")[0], 415)
        original = self.app.state.settings
        self.app.state.settings = original.model_copy(update={"max_image_side": 79})
        status, _, body = self.upload()
        self.assertEqual((status, json.loads(body)["error"]["code"]), (413, "image_too_large"))
        self.app.state.settings = original
        output = BytesIO()
        Image.new("RGB", (8, 4), "red").save(output, "PNG")
        with patch.object(Image.Image, "save", side_effect=OSError("private-path private-token")):
            with self.assertLogs("lumalab", level="ERROR"):
                status, _, body = self.upload(output.getvalue())
        self.assertEqual((status, json.loads(body)["error"]["code"]), (500, "image_processing_failed"))
        self.assertNotIn(b"private-", body)
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [])
        self.assertFalse(self.app.state.image_store.sessions)
        self.assertEqual(self.upload()[0], 201)
        paths = self.app.openapi()["paths"]
        upload_responses = paths["/api/v1/images"]["post"]["responses"]
        self.assertTrue({"201", "413", "415", "422", "429", "500", "503"} <= upload_responses.keys())
        for path, methods in paths.items():
            for operation in methods.values():
                self.assertIn("500", operation["responses"])
                self.assertIn("503", operation["responses"])
                if "{image_id}" in path:
                    self.assertTrue({"401", "404", "410"} <= operation["responses"].keys())

    def test_upload_accepts_all_still_extensions_without_trusting_mime(self):
        for format_name, extensions in (("JPEG", ("jpg", "jpeg")), ("PNG", ("png",)), ("WEBP", ("webp",))):
            output = BytesIO()
            Image.new("RGB", (80, 40), "red").save(output, format_name)
            for extension in extensions:
                for suffix in (extension, extension.upper()):
                    with self.subTest(format=format_name, suffix=suffix):
                        # The multipart helper declares application/octet-stream.
                        status, _, body = self.upload(output.getvalue(), "photo." + suffix)
                        self.assertEqual(status, 201)
                        session = UploadedImage.model_validate_json(body)
                        self.assertEqual((session.format, session.width, session.height), (format_name, 80, 40))
                        path = "/api/v1/images/" + session.image_id
                        self.assertEqual(self.request("GET", path + "/original-preview", token=session.access_token)[0], 200)
                        self.assertEqual(self.request("DELETE", path, token=session.access_token)[0], 204)

    def test_upload_checks_extension_against_detected_content(self):
        for format_name in ("JPEG", "PNG", "WEBP", "GIF", "BMP", "TIFF"):
            output = BytesIO()
            Image.new("RGB", (80, 40), "red").save(output, format_name)
            for extension, expected in (("jpg", "JPEG"), ("jpeg", "JPEG"), ("png", "PNG"), ("webp", "WEBP"), ("gif", None), ("", None)):
                if format_name == expected:
                    continue
                with self.subTest(format=format_name, extension=extension):
                    status, _, body = self.upload(output.getvalue(), "photo." + extension)
                    self.assertEqual(status, 415)
                    self.assertEqual(json.loads(body)["error"]["code"], "unsupported_format")
        self.assertEqual(self.app.state.image_store.sessions, {})
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_upload_requires_full_decoding_after_format_detection(self):
        output = BytesIO()
        Image.new("RGB", (80, 40), "red").save(output, "JPEG")
        truncated = output.getvalue()[:-30]
        with Image.open(BytesIO(truncated)) as image:
            self.assertEqual(image.format, "JPEG")
            image.verify()
        status, _, body = self.upload(truncated, "photo.jpeg")
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"]["code"], "invalid_image")
        self.assertEqual(self.app.state.image_store.sessions, {})
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_upload_checks_frame_count_for_allowed_formats(self):
        for format_name, extension in (("PNG", "png"), ("WEBP", "webp")):
            with self.subTest(format=format_name):
                output = BytesIO()
                first = Image.new("RGB", (80, 40), "red")
                second = Image.new("RGB", (80, 40), "blue")
                first.save(output, format_name, save_all=True, append_images=[second], duration=100, loop=0)
                data = output.getvalue()
                with Image.open(BytesIO(data)) as image:
                    self.assertEqual(image.format, format_name)
                    self.assertEqual(image.n_frames, 2)
                status, _, body = self.upload(data, "photo." + extension)
                self.assertEqual(status, 415)
                self.assertEqual(json.loads(body)["error"]["code"], "unsupported_format")
        self.assertEqual(self.app.state.image_store.sessions, {})
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_upload_rejects_corrupt_files_in_each_allowed_format(self):
        cases = [("empty.jpg", b""), ("invalid.png", b"not an image")]
        for format_name, extension in (("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")):
            output = BytesIO()
            Image.new("RGB", (80, 40), "red").save(output, format_name)
            data = output.getvalue()
            cases.append(("truncated." + extension, data[:20]))
            if format_name == "PNG":
                damaged = bytearray(data)
                damaged[data.index(b"IDAT") + 4] ^= 1
                cases.append(("bad-checksum.png", bytes(damaged)))
            else:
                cases.append(("incomplete-pixels." + extension, data[:-30]))
        for filename, data in cases:
            with self.subTest(filename=filename):
                status, _, body = self.upload(data, filename)
                self.assertEqual(status, 422)
                self.assertEqual(json.loads(body), {"error": {
                    "code": "invalid_image", "message": "Unable to decode this photograph.",
                }})
                self.assertEqual(self.app.state.image_store.sessions, {})
                self.assertEqual(list(Path(self.temporary.name).iterdir()), [])
        self.assertEqual(self.upload()[0], 201)

    def test_upload_rejects_unsupported_animated_and_multipage_containers(self):
        for format_name, extension in (("GIF", "gif"), ("TIFF", "tiff")):
            output = BytesIO()
            first = Image.new("RGB", (80, 40), "red")
            second = Image.new("RGB", (80, 40), "blue")
            first.save(output, format_name, save_all=True, append_images=[second])
            data = output.getvalue()
            with Image.open(BytesIO(data)) as image:
                self.assertEqual(image.n_frames, 2)
            for suffix in (extension, "png"):
                with self.subTest(format=format_name, suffix=suffix):
                    status, _, body = self.upload(data, "photo." + suffix)
                    self.assertEqual(status, 415)
                    self.assertEqual(json.loads(body)["error"]["code"], "unsupported_format")
                    self.assertEqual(self.app.state.image_store.sessions, {})
                    self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_upload_byte_limit_accepts_exact_boundary_and_rejects_one_over(self):
        output = BytesIO()
        Image.new("RGB", (8, 4), "red").save(output, "PNG")
        data = output.getvalue()
        original = self.app.state.settings
        for limit in (10_000_000, len(data)):
            with self.subTest(limit=limit):
                self.app.state.settings = original.model_copy(update={"max_upload_bytes": limit})
                exact = data + b"\0" * (limit - len(data))
                status, _, body = self.upload(exact)
                self.assertEqual(status, 201)
                session = json.loads(body)
                self.request("DELETE", "/api/v1/images/" + session["image_id"], token=session["access_token"])
                with patch("app.routes.images.normalize") as decode:
                    status, _, body = self.upload(exact + b"\0")
                    self.assertEqual(status, 413)
                    self.assertEqual(json.loads(body)["error"]["code"], "upload_too_large")
                    decode.assert_not_called()
                self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_upload_dimension_limits_at_default_and_configured_boundaries(self):
        original = self.app.state.settings
        for pixels, side, accepted, rejected in (
            (24_000_000, 10_000, (6000, 4000), ((6000, 4001),)),
            (24_000_000, 10_000, (10_000, 1), ((10_001, 1), (1, 10_001))),
            (32, 10, (8, 4), ((8, 5),)),
            (100, 10, (10, 1), ((11, 1), (1, 11))),
        ):
            self.app.state.settings = original.model_copy(update={"max_image_pixels": pixels, "max_image_side": side})
            for size in (accepted, *rejected):
                with self.subTest(pixels=pixels, side=side, size=size):
                    output = BytesIO()
                    Image.new("RGB", size, "red").save(output, "PNG")
                    if size == accepted:
                        status, _, body = self.upload(output.getvalue())
                        self.assertEqual(status, 201)
                        session = json.loads(body)
                        self.assertEqual((session["width"], session["height"]), size)
                        self.request("DELETE", "/api/v1/images/" + session["image_id"], token=session["access_token"])
                    else:
                        with patch.object(Image.Image, "load") as load:
                            status, _, body = self.upload(output.getvalue())
                            self.assertEqual(status, 413)
                            self.assertEqual(json.loads(body)["error"]["code"], "image_too_large")
                            load.assert_not_called()
                    self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_upload_request_cap_checks_declared_and_streamed_bytes(self):
        original = self.app.state.settings
        self.app.state.settings = self.app.state.settings.model_copy(update={"max_upload_bytes": 100})
        cap = 100 + MULTIPART_ALLOWANCE
        content_type = "multipart/form-data; boundary=test"
        with patch("app.routes.images.normalize") as decode:
            # Declared oversize is rejected without reading the body.
            status, _, body = self.request("POST", "/api/v1/images", content_type=content_type,
                extra_headers=((b"content-length", str(cap + 1).encode()),), chunks=())
            self.assertEqual(status, 413)
            self.assertEqual(json.loads(body)["error"]["code"], "request_too_large")
            for headers in ((), ((b"content-length", b"1"),)):
                opened = []
                def spool(*args, **kwargs):
                    file = tempfile.SpooledTemporaryFile(*args, **kwargs)
                    opened.append(file)
                    return file
                chunks = (
                    b'--test\r\nContent-Disposition: form-data; name="file"; filename="photo.png"\r\n\r\nstart',
                    b"x" * cap,
                    b"must not be consumed",
                )
                with patch("starlette.formparsers.SpooledTemporaryFile", side_effect=spool):
                    status, _, body = self.request("POST", "/api/v1/images", content_type=content_type,
                        extra_headers=headers, chunks=chunks)
                self.assertEqual(status, 413)
                self.assertEqual(json.loads(body)["error"]["code"], "request_too_large")
                self.assertTrue(opened)
                self.assertTrue(all(file.closed for file in opened))
            decode.assert_not_called()
        self.assertEqual(self.app.state.image_store.sessions, {})
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [])
        self.app.state.settings = original
        self.assertEqual(self.upload()[0], 201)

    def test_upload_rejects_both_decompression_bomb_warning_and_error(self):
        output = BytesIO()
        Image.new("RGB", (80, 40), "red").save(output, "PNG")
        for threshold in (2000, 1000):
            with self.subTest(threshold=threshold), patch.object(Image, "MAX_IMAGE_PIXELS", threshold):
                with warnings.catch_warnings(record=True) as emitted:
                    warnings.simplefilter("always")
                    filters = warnings.filters[:]
                    with patch.object(Image.Image, "load") as load:
                        status, _, body = self.upload(output.getvalue())
                        load.assert_not_called()
                    self.assertEqual(warnings.filters, filters)
                self.assertEqual(status, 413)
                self.assertEqual(json.loads(body)["error"]["code"], "image_too_large")
                self.assertEqual(emitted, [])
                self.assertEqual(self.app.state.image_store.sessions, {})
                self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_upload_rejects_malformed_exif_without_emitting_metadata_warnings(self):
        invalid_offset = b"Exif\0\0II*\0\xff\xff\xff\x7f"
        truncated_header = b"Exif\0\0II*\0"
        for format_name, extension, exif in (
            ("JPEG", "jpg", invalid_offset), ("PNG", "png", invalid_offset),
            ("WEBP", "webp", invalid_offset), ("PNG", "png", truncated_header),
            ("WEBP", "webp", truncated_header),
        ):
            with self.subTest(format=format_name, exif=exif):
                output = BytesIO()
                Image.new("RGB", (8, 4), "red").save(output, format_name, exif=exif)
                with warnings.catch_warnings(record=True) as emitted:
                    warnings.simplefilter("always")
                    status, _, body = self.upload(output.getvalue(), "photo." + extension)
                self.assertEqual(status, 422)
                self.assertEqual(json.loads(body), {"error": {
                    "code": "invalid_image", "message": "Unable to decode this photograph.",
                }})
                self.assertEqual(emitted, [])
                self.assertEqual(self.app.state.image_store.sessions, {})
                self.assertEqual(list(Path(self.temporary.name).iterdir()), [])
        self.assertEqual(self.upload()[0], 201)

    def test_upload_validates_colour_profiles_and_accepts_valid_srgb(self):
        valid = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        for format_name, extension in (("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")):
            for profile, expected in ((b"not-an-icc-profile", 422), (valid, 201)):
                with self.subTest(format=format_name, expected=expected):
                    output = BytesIO()
                    Image.new("RGB", (8, 4), "red").save(output, format_name, icc_profile=profile)
                    status, _, body = self.upload(output.getvalue(), "photo." + extension)
                    self.assertEqual(status, expected)
                    if status == 201:
                        session = json.loads(body)
                        self.request("DELETE", "/api/v1/images/" + session["image_id"], token=session["access_token"])
                    else:
                        self.assertEqual(json.loads(body)["error"]["code"], "invalid_image")
                    self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_upload_bounds_decompressed_png_metadata(self):
        text = PngImagePlugin.PngInfo()
        text.add_text("Comment", "x" * (PngImagePlugin.MAX_TEXT_CHUNK + 1), zip=True)
        aggregate = PngImagePlugin.PngInfo()
        aggregate.add_text("One", "x" * 80, zip=True)
        aggregate.add_text("Two", "x" * 80, zip=True)
        for options, memory_limit in (
            ({"pnginfo": text}, PngImagePlugin.MAX_TEXT_MEMORY),
            ({"icc_profile": b"x" * (PngImagePlugin.MAX_TEXT_CHUNK + 1)}, PngImagePlugin.MAX_TEXT_MEMORY),
            ({"pnginfo": aggregate}, 128),
        ):
            output = BytesIO()
            Image.new("RGB", (8, 4), "red").save(output, "PNG", **options)
            with patch.object(PngImagePlugin, "MAX_TEXT_MEMORY", memory_limit):
                status, _, body = self.upload(output.getvalue())
            self.assertEqual(status, 422)
            self.assertEqual(json.loads(body)["error"]["code"], "invalid_image")
            self.assertEqual(self.app.state.image_store.sessions, {})
            self.assertEqual(list(Path(self.temporary.name).iterdir()), [])

    def test_exif_orientation_matches_working_image_preview_export_and_dimensions(self):
        colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
        image = Image.new("RGB", (80, 40))
        for color, box in zip(colors, ((0, 0, 40, 20), (40, 0, 80, 20), (0, 20, 40, 40), (40, 20, 80, 40))):
            image.paste(color, box)
        # Expected quadrant order: top-left, top-right, bottom-left, bottom-right.
        orders = {
            None: (0, 1, 2, 3), 1: (0, 1, 2, 3), 2: (1, 0, 3, 2),
            3: (3, 2, 1, 0), 4: (2, 3, 0, 1), 5: (0, 2, 1, 3),
            6: (2, 0, 3, 1), 7: (3, 1, 2, 0), 8: (1, 3, 0, 2),
        }
        for format_name, extension in (("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")):
            for orientation, order in orders.items():
                with self.subTest(format=format_name, orientation=orientation):
                    output = BytesIO()
                    exif = Image.Exif()
                    if orientation is not None:
                        exif[274] = orientation
                    image.save(output, format_name, exif=exif, quality=95)
                    status, _, body = self.upload(output.getvalue(), "photo." + extension)
                    self.assertEqual(status, 201)
                    session = json.loads(body)
                    size = (40, 80) if orientation in (5, 6, 7, 8) else (80, 40)
                    self.assertEqual((session["width"], session["height"]), size)
                    path = "/api/v1/images/" + session["image_id"]
                    directory = self.app.state.image_store.sessions[session["image_id"]].directory
                    preview_status, _, preview = self.request("GET", path + "/original-preview", token=session["access_token"])
                    export_status, _, exported = self.request("POST", path + "/export",
                        json.dumps({"adjustments": NEUTRAL}).encode(), "application/json", session["access_token"])
                    self.assertEqual((preview_status, export_status), (200, 200))
                    preview_size = (16, 32) if size == (40, 80) else (32, 16)
                    for data, expected_size in ((directory.joinpath("normalized.png").read_bytes(), size),
                                                (preview, preview_size), (exported, size)):
                        with Image.open(BytesIO(data)) as result:
                            self.assertEqual(result.size, expected_size)
                            self.assertNotIn(274, result.getexif())
                            width, height = result.size
                            positions = ((width // 4, height // 4), (3 * width // 4, height // 4),
                                         (width // 4, 3 * height // 4), (3 * width // 4, 3 * height // 4))
                            for position, index in zip(positions, order):
                                actual, expected = result.getpixel(position), colors[index]
                                self.assertLess(sum(abs(a - b) for a, b in zip(actual, expected)), 35)
                    self.assertEqual(self.request("DELETE", path, token=session["access_token"])[0], 204)

    def test_transparent_compositing(self):
        output = BytesIO()
        Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(output, "PNG")
        session = json.loads(self.upload(output.getvalue())[2])
        path = "/api/v1/images/" + session["image_id"] + "/original-preview"
        status, _, data = self.request("GET", path, token=session["access_token"])
        self.assertEqual(status, 200)
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.getpixel((5, 5)), (255, 255, 255))

    def test_private_routing_responses_cannot_be_cached(self):
        status, headers, _ = self.request("GET", "/api/v1/images/unknown/original-preview/")
        self.assertEqual(status, 307)
        self.assertIn(b"location", headers)
        self.assertEqual(self.request("GET", "/api/v1/images/unknown/not-a-route")[0], 404)
        self.assertEqual(self.request("PUT", "/api/v1/images/unknown/original-preview")[0], 405)

        @self.app.get("/api/v1/images/cache-probe")
        def cache_probe():
            return Response(b"probe", headers={"Cache-Control": "public, max-age=3600"})

        status, headers, _ = self.request("GET", "/api/v1/images/cache-probe")
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        paths = self.app.openapi()["paths"]
        for path, methods in paths.items():
            if path.startswith("/api/v1/images") and not path.endswith("cache-probe"):
                for operation in methods.values():
                    for response in operation["responses"].values():
                        self.assertEqual(response["headers"]["Cache-Control"]["schema"]["const"], "no-store")

    def test_preview_revision_header_echoes_only_successful_valid_requests(self):
        first = json.loads(self.upload()[2])
        second = json.loads(self.upload()[2])
        for session, revision in ((first, 0), (first, 2147483647), (second, 7), (first, 3), (first, 1)):
            with self.subTest(revision=revision):
                status, headers, _ = self.request("POST", f'/api/v1/images/{session["image_id"]}/preview',
                    json.dumps({"revision": revision, "adjustments": NEUTRAL}).encode(),
                    "application/json", session["access_token"])
                self.assertEqual(status, 200)
                self.assertEqual(headers[b"x-image-revision"], str(revision).encode())
                self.assertEqual(headers[b"content-type"], b"image/jpeg")
                self.assertNotIn(b"content-disposition", headers)
        path = f'/api/v1/images/{first["image_id"]}/preview'
        for revision in (-1, 1.0, 1.5, "1", True, None):
            with self.subTest(invalid_revision=revision):
                status, headers, _ = self.request("POST", path,
                    json.dumps({"revision": revision, "adjustments": NEUTRAL}).encode(),
                    "application/json", first["access_token"])
                self.assertEqual(status, 422)
                self.assertNotIn(b"x-image-revision", headers)
        status, headers, _ = self.request("POST", path,
            json.dumps({"revision": 9, "adjustments": NEUTRAL}).encode(), "application/json", "wrong")
        self.assertEqual(status, 401)
        self.assertNotIn(b"x-image-revision", headers)

    def test_export_headers_use_a_safe_bounded_jpeg_attachment_filename(self):
        session = json.loads(self.upload()[2])
        stored = self.app.state.image_store.sessions[session["image_id"]]
        for filename in ('portrait.png', '../folder/photo.png', 'C:\\photos\\photo.png',
                         'photo"; other="x.png', 'photo\r\nX-Injected: yes.png',
                         '\u65e5\u672c.png', 'a' * 200 + '.png'):
            with self.subTest(filename=filename):
                stored.filename = filename
                status, headers, data = self.request("POST", f'/api/v1/images/{session["image_id"]}/export',
                    json.dumps({"adjustments": NEUTRAL, "format": "jpeg", "quality": 92}).encode(),
                    "application/json", session["access_token"])
                self.assertEqual(status, 200)
                self.assertEqual(headers[b"content-type"], b"image/jpeg")
                self.assertEqual(int(headers[b"content-length"]), len(data))
                disposition = headers[b"content-disposition"].decode("ascii")
                self.assertRegex(disposition, r'^attachment; filename="lumalab-[A-Za-z0-9_-]{1,80}\.jpg"$')
                self.assertNotIn(b"x-injected", headers)
                self.assertNotIn(b"x-image-revision", headers)
                if filename == 'portrait.png':
                    self.assertEqual(disposition, 'attachment; filename="lumalab-portrait.jpg"')
                if filename == '\u65e5\u672c.png':
                    self.assertEqual(disposition, 'attachment; filename="lumalab-image.jpg"')
        paths = self.app.openapi()["paths"]
        preview = paths["/api/v1/images/{image_id}/preview"]["post"]["responses"]["200"]
        self.assertEqual(preview["headers"]["X-Image-Revision"]["schema"], {"type": "integer", "minimum": 0})
        export = paths["/api/v1/images/{image_id}/export"]["post"]["responses"]["200"]
        self.assertEqual(export["headers"]["Content-Disposition"]["schema"]["type"], "string")

    def test_cors_exposes_actual_preview_export_and_auth_error_headers(self):
        origin = "http://localhost:5173"
        self.asgi_app = with_cors(self.app, (origin,))
        session = json.loads(self.upload()[2])
        for operation in ("preview", "export"):
            payload = {"adjustments": NEUTRAL}
            if operation == "preview":
                payload["revision"] = 12
            status, headers, _ = self.request("POST", f'/api/v1/images/{session["image_id"]}/{operation}',
                json.dumps(payload).encode(), "application/json", session["access_token"],
                extra_headers=((b"origin", origin.encode()),))
            self.assertEqual(status, 200)
            self.assertEqual(headers[b"access-control-allow-origin"], origin.encode())
            self.assertEqual(set(headers[b"access-control-expose-headers"].decode().lower().split(", ")),
                             {"x-image-revision", "content-disposition"})
            self.assertNotIn(b"access-control-allow-credentials", headers)
            self.assertIn(b"origin", headers[b"vary"].lower())
        status, headers, _ = self.request("GET", f'/api/v1/images/{session["image_id"]}/original-preview',
            extra_headers=((b"origin", origin.encode()),))
        self.assertEqual(status, 401)
        self.assertEqual(headers[b"access-control-allow-origin"], origin.encode())

    def test_cors_preflight_restricts_origins_methods_and_request_headers(self):
        origin = "http://localhost:5173"
        self.asgi_app = with_cors(self.app, (origin,))
        for method in ("GET", "POST", "DELETE"):
            status, headers, _ = self.request("OPTIONS", "/api/v1/images/test/preview", extra_headers=(
                (b"origin", origin.encode()), (b"access-control-request-method", method.encode()),
                (b"access-control-request-headers", b"authorization,content-type"),
            ))
            self.assertEqual(status, 200)
            self.assertEqual(headers[b"access-control-allow-origin"], origin.encode())
        for requested_origin, method, requested_headers in (("https://unlisted.example", "POST", "authorization"),
                (origin, "PUT", "authorization"), (origin, "POST", "x-unapproved")):
            status, _, _ = self.request("OPTIONS", "/api/v1/images/test/preview", extra_headers=(
                (b"origin", requested_origin.encode()), (b"access-control-request-method", method.encode()),
                (b"access-control-request-headers", requested_headers.encode()),
            ))
            self.assertEqual(status, 400)
        status, headers, _ = self.request("GET", "/api/v1/images/test/original-preview",
            extra_headers=((b"origin", b"https://unlisted.example"),))
        self.assertEqual(status, 401)
        self.assertNotIn(b"access-control-allow-origin", headers)
        self.assertIs(with_cors(self.app, ()), self.app)

    def test_combined_adjustments_grayscale_and_processing_failure_recovery(self):
        session = json.loads(self.upload()[2])
        path = "/api/v1/images/" + session["image_id"] + "/preview"
        body = json.dumps({"revision": 2, "adjustments": {
            "brightness": 110, "contrast": 120, "saturation": 0,
            "warmth": 25, "sharpness": 30, "vignette": 40,
        }}).encode()
        status, _, data = self.request("POST", path, body, "application/json", session["access_token"])
        self.assertEqual(status, 200)
        with Image.open(BytesIO(data)) as image:
            self.assertTrue(all(r == g == b for r, g, b in image.get_flattened_data()))
        with patch("app.routes.images.render", side_effect=OSError("private-path private-token")):
            with self.assertLogs("lumalab", level="ERROR"):
                status, _, error = self.request("POST", path, body, "application/json", session["access_token"])
        self.assertEqual(status, 500)
        self.assertNotIn(b"private-", error)
        self.assertEqual(self.request("POST", path, body, "application/json", session["access_token"])[0], 200)


if __name__ == "__main__":
    unittest.main()
