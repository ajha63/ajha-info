from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_site import is_publishable, resolve_reference, scan_for_secrets
from scripts.deploy_site import parse_deletes, valid_key


class BuildRulesTest(unittest.TestCase):
    def test_allowlist_excludes_sources_and_local_files(self) -> None:
        self.assertTrue(is_publishable("index.html"))
        self.assertTrue(is_publishable("posts/example.html"))
        self.assertTrue(is_publishable("images/example.png"))
        self.assertFalse(is_publishable("posts/example.md"))
        self.assertFalse(is_publishable("assets/sass/main.scss"))
        self.assertFalse(is_publishable(".env"))
        self.assertFalse(is_publishable("assets/.DS_Store"))

    def test_references_cannot_escape_site_root(self) -> None:
        self.assertEqual(resolve_reference("posts/example.html", "../images/pic.jpg"), "images/pic.jpg")
        with self.assertRaises(ValueError):
            resolve_reference("index.html", "../../secret.txt")

    def test_secret_pattern_blocks_publishable_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.html"
            marker = "aws_secret_" + "access_key = example"
            path.write_text(marker, encoding="utf-8")
            with self.assertRaises(ValueError):
                scan_for_secrets(path, "index.html")


class DeployRulesTest(unittest.TestCase):
    def test_delete_input_is_explicit_json(self) -> None:
        self.assertEqual(parse_deletes('["old.html"]'), ["old.html"])
        with self.assertRaises(ValueError):
            parse_deletes('"old.html"')

    def test_delete_key_must_be_relative_object_key(self) -> None:
        self.assertTrue(valid_key("posts/old.html"))
        self.assertFalse(valid_key("/posts/old.html"))
        self.assertFalse(valid_key("../old.html"))


if __name__ == "__main__":
    unittest.main()
