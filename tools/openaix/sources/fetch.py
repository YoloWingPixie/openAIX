import argparse
import hashlib
import subprocess
import urllib.request
import urllib.error

from openaix import ROOT
from openaix.sources.authorities import load_authorities


def verify_payload(name, source, payload):
    """Accept a downloaded or cached publication only when it matches the pinned edition."""
    signature = b"%PDF" if source["format"] == "pdf" else b"PK"
    if not payload.startswith(signature):
        raise SystemExit(name + ": unexpected document format")
    digest = hashlib.sha256(payload).hexdigest()
    if "sha256" not in source:
        raise SystemExit(name + ": no pinned sha256; review the publication and pin " + digest + " in sources/authorities.json before caching")
    if source["sha256"] != digest:
        raise SystemExit(name + ": publication differs from the pinned source edition")
    return digest


def main():
    sources = load_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=sorted(sources))
    args = parser.parse_args()
    source = sources[args.source]
    directory = ROOT / ".cache/authorities"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (args.source + "." + source["format"])
    if not target.exists():
        if not source.get("url"):
            raise SystemExit(args.source + ": no public URL is recorded; place a copy with the pinned SHA-256 at " + str(target))
        request = urllib.request.Request(source["url"], headers={"User-Agent": "openAIX-source-audit/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            reason = "HTTP " + str(error.code) if isinstance(error, urllib.error.HTTPError) else "network failure"
            raise SystemExit(args.source + ": document unavailable (" + reason + ")") from None
        verify_payload(args.source, source, payload)
        target.write_bytes(payload)
    digest = verify_payload(args.source, source, target.read_bytes())
    if source["format"] == "pdf":
        subprocess.run(["pdftotext", "-layout", str(target), str(target.with_suffix(".txt"))], check=True)
    print(args.source + ": " + digest)
