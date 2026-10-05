import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.sources.fetch import verify_payload


class SourceFetchTests(unittest.TestCase):
    payload = b"%PDF-1.7 publication body"

    def test_unpinned_publication_is_refused_and_its_hash_is_reported(self):
        with self.assertRaises(SystemExit) as raised:
            verify_payload("unpinned", {"format": "pdf"}, self.payload)
        self.assertIn(hashlib.sha256(self.payload).hexdigest(), str(raised.exception))

    def test_pinned_publication_must_match(self):
        pinned = {"format": "pdf", "sha256": hashlib.sha256(self.payload).hexdigest()}
        self.assertEqual(verify_payload("pinned", pinned, self.payload), pinned["sha256"])
        with self.assertRaisesRegex(SystemExit, "differs"):
            verify_payload("pinned", pinned, self.payload + b"changed")


if __name__ == "__main__":
    unittest.main()
