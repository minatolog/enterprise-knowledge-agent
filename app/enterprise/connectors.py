"""Explicit allowlist HTTPS connector for OA JSON and Confluence pages."""
import os
from urllib.parse import urlparse

import httpx
from lxml import html


def fetch_pages(settings, url):
    parsed = urlparse(url)
    allowed = {host.strip() for host in settings.connector_hosts.split(",") if host.strip()}
    if parsed.scheme != "https" or parsed.hostname not in allowed or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("connector requires an explicitly allowlisted HTTPS host")
    headers = {}
    if os.getenv("ENTERPRISE_CONNECTOR_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["ENTERPRISE_CONNECTOR_TOKEN"]
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > settings.max_upload_bytes:
                    raise ValueError("connector response exceeds size limit")
    import json
    payload = json.loads(data)
    rows = payload.get("results", payload.get("documents", []))
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError("connector response must contain at most 100 documents per page")
    result = []
    for row in rows:
        body = row.get("text")
        if body is None:
            tree = html.fromstring(row["body"]["storage"]["value"])
            for element in tree.xpath("//script|//style"):
                element.drop_tree()
            body = tree.text_content()
        if not isinstance(body, str) or not body.strip():
            raise ValueError("connector document has no text")
        result.append({"external_id": str(row["id"]), "title": str(row["title"]), "text": body})
    # Pagination is explicit: caller supplies the next allowlisted page URL.
    return result
