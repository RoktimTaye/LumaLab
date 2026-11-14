"""Generate current API TypeScript shapes; reject unsupported schema constructs."""

import argparse
from hashlib import sha256
import json

from app.config import PROJECT_DIR
from scripts.openapi import schema

TARGET = PROJECT_DIR / "frontend/src/lib/api.generated.ts"


def fields(properties: dict, required: list) -> str:
    return "{ " + "; ".join(f"{json.dumps(name)}{'' if name in required else '?'}: {ts_type(value)}"
                            for name, value in properties.items()) + " }"


def ts_type(value: dict) -> str:
    if any(key in value for key in ("anyOf", "allOf", "oneOf", "not", "prefixItems", "patternProperties")):
        raise ValueError("Unsupported schema composition; review the contract generator.")
    if "$ref" in value:
        prefix = "#/components/schemas/"
        if not value["$ref"].startswith(prefix):
            raise ValueError("Only local component references are supported.")
        return f'components["schemas"][{json.dumps(value["$ref"][len(prefix):])}]'
    if "const" in value:
        return json.dumps(value["const"])
    if "enum" in value:
        return " | ".join(json.dumps(item) for item in value["enum"])
    kind = value.get("type")
    if kind == "object":
        if value.get("additionalProperties"):
            raise ValueError("Review support for map schemas before generating contracts.")
        return fields(value.get("properties", {}), value.get("required", []))
    if kind == "array":
        return f"Array<{ts_type(value['items'])}>"
    if kind == "string":
        return "Blob" if value.get("format") == "binary" or value.get("contentMediaType") == "application/octet-stream" else "string"
    if kind in {"integer", "number"}:
        return "number"
    if kind in {"boolean", "null"}:
        return kind
    raise ValueError("Unsupported schema shape; review the contract generator.")


def content(value: dict) -> str:
    return "{ " + "; ".join(f"{json.dumps(media)}: {ts_type(item['schema'])}"
                            for media, item in value.items()) + " }"


def generate(document: dict) -> str:
    fingerprint = sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()
    lines = ["// Generated from backend OpenAPI; run npm run contracts:generate. Do not edit.",
             f"// Schema SHA-256: {fingerprint}", "export interface components {", "  schemas: {"]
    for name, value in sorted(document["components"]["schemas"].items()):
        lines.append(f"    {json.dumps(name)}: {ts_type(value)};")
    lines += ["  };", "}", "export interface paths {"]
    for path, methods in sorted(document["paths"].items()):
        lines.append(f"  {json.dumps(path)}: {{")
        for method, operation in sorted(methods.items()):
            if method not in {"get", "post", "delete"}:
                raise ValueError("Review new methods before generating contracts.")
            lines.append(f"    {method}: {{")
            parameters = operation.get("parameters", [])
            if any(item["in"] != "path" for item in parameters):
                raise ValueError("Review new parameter locations before generating contracts.")
            if parameters:
                props = {item["name"]: item["schema"] for item in parameters}
                lines.append(f"      parameters: {{ path: {fields(props, list(props))} }};")
            body = operation.get("requestBody")
            if body:
                optional = "" if body.get("required") else "?"
                lines.append(f"      requestBody{optional}: {{ content: {content(body['content'])} }};")
            lines.append("      responses: {")
            for status, response in sorted(operation["responses"].items()):
                if "$ref" in response:
                    raise ValueError("Review referenced response objects before generating contracts.")
                headers = response.get("headers", {})
                header_type = fields({name: item["schema"] for name, item in headers.items()}, [])
                body_type = f"content: {content(response['content'])}" if response.get("content") else "content?: never"
                lines.append(f"        {json.dumps(status)}: {{ headers: {header_type}; {body_type} }};")
            lines += ["      };", "    };"]
        lines.append("  };")
    return "\n".join([*lines, "}", ""])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate/check frontend contracts from actual OpenAPI.")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    generated = generate(schema())
    if arguments.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != generated:
            print("API contracts are stale. Run npm run contracts:generate and review the diff.")
            return 1
        print("API contracts match backend OpenAPI.")
    else:
        TARGET.write_text(generated, encoding="utf-8")
        print("Generated src/lib/api.generated.ts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
