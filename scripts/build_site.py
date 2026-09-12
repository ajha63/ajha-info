#!/usr/bin/env python3
"""Build a deterministic, allowlisted artifact for ajha.info."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit


EXACT_FILES = {"index.html", "LICENSE.txt"}
PREFIX_RULES = (
    ("posts/", (".html",)),
    ("assets/css/", None),
    ("assets/js/", None),
    ("assets/webfonts/", None),
    ("images/", None),
)
TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".svg", ".txt"}
SECRET_PATTERNS = (
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"ASIA[0-9A-Z]{16}"),
    re.compile(rb"aws_secret_access_key\s*[:=]", re.IGNORECASE),
    re.compile(rb"aws_session_token\s*[:=]", re.IGNORECASE),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", re.IGNORECASE)


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for name in ("href", "src", "poster"):
            value = values.get(name)
            if value:
                self.references.append(value)
        srcset = values.get("srcset")
        if srcset:
            self.references.extend(item.strip().split()[0] for item in srcset.split(",") if item.strip())


def is_publishable(key: str) -> bool:
    path = PurePosixPath(key)
    if path.is_absolute() or ".." in path.parts or any(part.startswith(".") for part in path.parts):
        return False
    if key in EXACT_FILES:
        return True
    for prefix, suffixes in PREFIX_RULES:
        if key.startswith(prefix) and (suffixes is None or key.endswith(suffixes)):
            return True
    return False


def content_type(key: str) -> str:
    overrides = {
        ".css": "text/css",
        ".eot": "application/vnd.ms-fontobject",
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript",
        ".json": "application/json",
        ".mp4": "video/mp4",
        ".svg": "image/svg+xml",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }
    suffix = Path(key).suffix.lower()
    return overrides.get(suffix, mimetypes.guess_type(key)[0] or "application/octet-stream")


def git_files(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repo, check=True, capture_output=True
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def source_sha(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def scan_for_secrets(path: Path, key: str) -> None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return
    data = path.read_bytes()
    if any(pattern.search(data) for pattern in SECRET_PATTERNS):
        raise ValueError(f"possible secret detected in publishable file: {key}")


def resolve_reference(source_key: str, raw_reference: str) -> str | None:
    parsed = urlsplit(raw_reference.strip())
    if parsed.scheme or parsed.netloc or raw_reference.startswith(("//", "#", "data:")):
        return None
    decoded = unquote(parsed.path)
    if not decoded:
        return None
    if decoded.startswith("/"):
        candidate = PurePosixPath(decoded.lstrip("/"))
    else:
        candidate = PurePosixPath(source_key).parent / decoded
    parts: list[str] = []
    for part in candidate.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError(f"reference escapes site root in {source_key}: {raw_reference}")
            parts.pop()
        else:
            parts.append(part)
    resolved = PurePosixPath(*parts)
    if decoded.endswith("/"):
        resolved /= "index.html"
    return resolved.as_posix()


def validate_references(site_dir: Path, keys: set[str]) -> None:
    missing: list[str] = []
    for html_path in sorted(site_dir.rglob("*.html")):
        key = html_path.relative_to(site_dir).as_posix()
        parser = ReferenceParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
        for reference in parser.references:
            resolved = resolve_reference(key, reference)
            if resolved and resolved not in keys:
                missing.append(f"{key}: {reference} -> {resolved}")
    for css_path in sorted(site_dir.rglob("*.css")):
        key = css_path.relative_to(site_dir).as_posix()
        text = css_path.read_text(encoding="utf-8")
        for match in CSS_URL_RE.finditer(text):
            reference = match.group(2)
            resolved = resolve_reference(key, reference)
            if resolved and resolved not in keys:
                missing.append(f"{key}: {reference} -> {resolved}")
    if missing:
        raise ValueError("missing local references:\n" + "\n".join(missing))


def artifact_digest(source: str, files: list[dict[str, object]]) -> str:
    payload = json.dumps(
        {"source_sha": source, "files": files}, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build(repo: Path, output: Path) -> dict[str, object]:
    repo = repo.resolve()
    output = output.resolve()
    if output == repo or repo in output.parents and output.name in {".", ".."}:
        raise ValueError("unsafe output directory")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    site_dir = output / "site"
    site_dir.mkdir(parents=True, exist_ok=True)

    selected = sorted(key for key in git_files(repo) if is_publishable(key))
    if "index.html" not in selected:
        raise ValueError("index.html is missing from the artifact")

    files: list[dict[str, object]] = []
    for key in selected:
        source = repo / key
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"publishable path must be a regular file: {key}")
        if repo not in source.resolve().parents:
            raise ValueError(f"publishable path escapes repository: {key}")
        scan_for_secrets(source, key)
        destination = site_dir / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        data = destination.read_bytes()
        files.append(
            {
                "key": key,
                "sha256": hashlib.sha256(data).hexdigest(),
                "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
                "size": len(data),
                "content_type": content_type(key),
            }
        )

    validate_references(site_dir, set(selected))
    sha = source_sha(repo)
    manifest = {
        "schema": 1,
        "source_sha": sha,
        "artifact_sha256": artifact_digest(sha, files),
        "files": files,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.repo, args.output)
    print(
        json.dumps(
            {
                "source_sha": manifest["source_sha"],
                "artifact_sha256": manifest["artifact_sha256"],
                "file_count": len(manifest["files"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
