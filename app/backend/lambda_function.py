"""Adaptador de AWS Lambda (Function URL). Sirve el frontend, los assets y la API desde un mismo origen."""
import base64

import core


def handler(event, context):
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method", event.get("httpMethod", "GET"))
    path = event.get("rawPath", event.get("path", "/"))
    body = event.get("body") or ""
    raw = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode("utf-8")
    r = core.route(method, path, raw)
    ctype = r["headers"].get("Content-Type", "")
    is_bin = ctype.startswith("image/")
    return {
        "statusCode": r["status"],
        "headers": r["headers"],
        "isBase64Encoded": is_bin,
        "body": base64.b64encode(r["body"]).decode("ascii") if is_bin else r["body"].decode("utf-8"),
    }
