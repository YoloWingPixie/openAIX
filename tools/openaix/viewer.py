import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlsplit
import yaml

from openaix import ROOT
from openaix.sources.authorities import load_authorities


ASSETS = {
    "/": ("viewer/index.html", "text/html"),
    "/app/index.mjs": ("viewer/app/index.mjs", "text/javascript"),
    "/app/styles.css": ("viewer/app/styles.css", "text/css"),
    "/pages/explorer/index.mjs": ("viewer/pages/explorer/index.mjs", "text/javascript"),
    "/pages/explorer/model.mjs": ("viewer/pages/explorer/model.mjs", "text/javascript"),
}


def example_yaml(document):
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100)


def review_data(root=ROOT):
    def documents(directory):
        return [{"path": str(path.relative_to(root)), "document": json.loads(path.read_text())}
                for path in sorted((root / directory).rglob("*.json"))]

    def shown(document):
        return {"document": document, "yaml": example_yaml(document)}

    generated = ("examples/minimal/", "examples/maximal/")
    examples = [entry for entry in documents("examples") if not entry["path"].startswith(generated)]
    for entry in examples:
        entry["yaml"] = example_yaml(entry["document"])
    # The minimal and maximal example of each schema, by schema identifier; common.schema.json has one pair for each definition.
    notes = json.loads((root / "catalogues/example-notes.json").read_text())
    pairs = {}
    for label in ("minimal", "maximal"):
        for entry in documents("examples/" + label):
            document = entry["document"]
            pair = pairs.setdefault(document["$schema"], {"notes": notes.get(document["$schema"], []), "definitions": {}})
            pair[label] = {"path": entry["path"], **shown(document)}
            if document["$schema"].startswith("urn:openaix:schema:common:"):
                for name, value in document.items():
                    if name != "$schema":
                        definition = pair["definitions"].setdefault(name, {"notes": [
                            {**note, "path": note["path"].removeprefix(name).lstrip("/") or "/"}
                            for note in pair["notes"] if note["path"] == name or note["path"].startswith(name + "/")]})
                        definition[label] = shown(value)
    return {"schemas": documents("schemas"), "examples": examples, "example_pairs": pairs,
            "authorities": load_authorities(),
            "catalogue": json.loads((root / "catalogues/control-measures.json").read_text())}


def response(path, root=ROOT):
    route = urlsplit(path).path
    if route == "/api/review":
        return "application/json", json.dumps(review_data(root), ensure_ascii=False).encode()
    asset = ASSETS.get(route)
    if asset is None:
        return None
    filename, content_type = asset
    return content_type, (root / filename).read_bytes()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            result = response(self.path)
        except (OSError, ValueError):
            self.send_error(500, "Review data could not be loaded. Check the repository files.")
            return
        if result is None:
            self.send_error(404)
            return
        content_type, body = result
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Read-only local openAIX schema viewer")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"openAIX viewer: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
