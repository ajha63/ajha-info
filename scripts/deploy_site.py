#!/usr/bin/env python3
"""Plan, apply, and verify an approved ajha.me S3 release."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request


MANAGED_BY = "ajha-me-deploy"


def aws(args: list[str], profile: str | None = None) -> object:
    command = ["aws", *args]
    if profile:
        command.extend(["--profile", profile])
    command.extend(["--no-cli-pager", "--output", "json"])
    env = os.environ.copy()
    env["AWS_PAGER"] = ""
    result = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
    return json.loads(result.stdout or "{}")


def load_manifest(release_dir: Path) -> dict[str, object]:
    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if manifest.get("schema") != 1 or not isinstance(files, list):
        raise ValueError("unsupported release manifest")
    canonical_files: list[dict[str, object]] = []
    for entry in files:
        key = str(entry["key"])
        path = release_dir / "site" / key
        data = path.read_bytes()
        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != entry["sha256"] or len(data) != entry["size"]:
            raise ValueError(f"artifact file does not match manifest: {key}")
        canonical_files.append(entry)
    payload = json.dumps(
        {"source_sha": manifest["source_sha"], "files": canonical_files},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    actual_digest = hashlib.sha256(payload).hexdigest()
    if actual_digest != manifest.get("artifact_sha256"):
        raise ValueError("artifact digest does not match manifest")
    return manifest


def valid_key(key: str) -> bool:
    path = PurePosixPath(key)
    return bool(key) and not path.is_absolute() and ".." not in path.parts and not key.endswith("/")


def object_head(bucket: str, key: str, profile: str | None) -> dict[str, object]:
    return aws(["s3api", "head-object", "--bucket", bucket, "--key", key], profile)  # type: ignore[return-value]


def list_objects(bucket: str, profile: str | None) -> dict[str, dict[str, object]]:
    response = aws(["s3api", "list-objects-v2", "--bucket", bucket], profile)
    return {item["Key"]: item for item in response.get("Contents", [])}  # type: ignore[union-attr]


def preserved_headers(head: dict[str, object]) -> dict[str, str]:
    mapping = {
        "CacheControl": "cache_control",
        "ContentDisposition": "content_disposition",
        "ContentEncoding": "content_encoding",
        "ContentLanguage": "content_language",
    }
    return {target: str(head[source]) for source, target in mapping.items() if head.get(source)}


def calculate_plan(
    release_dir: Path,
    bucket: str,
    delete_paths: list[str],
    profile: str | None,
) -> dict[str, object]:
    manifest = load_manifest(release_dir)
    remote = list_objects(bucket, profile)
    target_keys = {str(item["key"]) for item in manifest["files"]}  # type: ignore[index]
    uploads: list[dict[str, object]] = []

    existing_keys = [
        str(entry["key"])
        for entry in manifest["files"]  # type: ignore[index]
        if str(entry["key"]) in remote
    ]
    with ThreadPoolExecutor(max_workers=8) as executor:
        heads = dict(
            zip(
                existing_keys,
                executor.map(lambda key: object_head(bucket, key, profile), existing_keys),
            )
        )

    for entry in manifest["files"]:  # type: ignore[index]
        key = str(entry["key"])
        remote_entry = remote.get(key)
        if not remote_entry:
            uploads.append({**entry, "reason": "missing", "preserve_headers": {}})
            continue
        etag = str(remote_entry.get("ETag", "")).strip('"')
        head = heads[key]
        same_body = "-" not in etag and etag == entry["md5"]
        same_type = str(head.get("ContentType", "")).lower() == str(entry["content_type"]).lower()
        if not same_body or not same_type:
            uploads.append(
                {
                    **entry,
                    "reason": "content" if not same_body else "content-type",
                    "preserve_headers": preserved_headers(head),
                    "remote_etag": etag,
                }
            )

    deletes: list[dict[str, str]] = []
    for key in sorted(set(delete_paths)):
        if not valid_key(key):
            raise ValueError(f"invalid delete key: {key}")
        if key in target_keys:
            raise ValueError(f"cannot delete a key present in the release: {key}")
        if key not in remote:
            raise ValueError(f"delete key does not exist: {key}")
        head = object_head(bucket, key, profile)
        metadata = {str(k).lower(): str(v) for k, v in head.get("Metadata", {}).items()}
        if metadata.get("managed-by") != MANAGED_BY:
            raise ValueError(f"delete key is not managed by this pipeline: {key}")
        deletes.append({"key": key, "remote_etag": str(remote[key].get("ETag", "")).strip('"')})

    paths: set[str] = set()
    for item in [*uploads, *deletes]:
        key = str(item["key"])
        paths.add("/" + key)
        if key == "index.html":
            paths.add("/")
    plan_body = {
        "schema": 1,
        "bucket": bucket,
        "source_sha": manifest["source_sha"],
        "artifact_sha256": manifest["artifact_sha256"],
        "uploads": sorted(uploads, key=lambda item: str(item["key"])),
        "deletes": deletes,
        "invalidations": sorted(paths),
    }
    payload = json.dumps(plan_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**plan_body, "plan_sha256": hashlib.sha256(payload).hexdigest()}


def write_outputs(plan: dict[str, object], output_path: Path | None) -> None:
    if not output_path:
        return
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(f"plan_sha256={plan['plan_sha256']}\n")
        handle.write(f"artifact_sha256={plan['artifact_sha256']}\n")


def write_summary(plan: dict[str, object], summary_path: Path | None) -> None:
    if not summary_path:
        return
    lines = [
        "## Plan de despliegue ajha.me",
        "",
        f"- Source SHA: `{plan['source_sha']}`",
        f"- Artifact SHA-256: `{plan['artifact_sha256']}`",
        f"- Plan SHA-256: `{plan['plan_sha256']}`",
        f"- Altas/cambios: {len(plan['uploads'])}",
        f"- Bajas: {len(plan['deletes'])}",
        "",
        "### Altas y cambios",
        "",
    ]
    lines.extend(f"- `{item['key']}` ({item['reason']})" for item in plan["uploads"])
    lines.extend(["", "### Bajas", ""])
    lines.extend(f"- `{item['key']}`" for item in plan["deletes"])
    if not plan["deletes"]:
        lines.append("- Ninguna")
    lines.extend(["", "### Invalidaciones", ""])
    lines.extend(f"- `{path}`" for path in plan["invalidations"])
    with summary_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def metadata_arg(entry: dict[str, object], source_sha: str) -> str:
    return ",".join(
        (
            f"managed-by={MANAGED_BY}",
            f"source-sha256={entry['sha256']}",
            f"source-commit={source_sha}",
        )
    )


def apply_plan(
    release_dir: Path,
    approved_plan_path: Path,
    distribution_id: str,
    profile: str | None,
) -> dict[str, object]:
    approved = json.loads(approved_plan_path.read_text(encoding="utf-8"))
    delete_paths = [item["key"] for item in approved.get("deletes", [])]
    current = calculate_plan(release_dir, str(approved["bucket"]), delete_paths, profile)
    if current["plan_sha256"] != approved.get("plan_sha256"):
        raise ValueError("live deployment plan changed after approval; create and approve a new plan")

    uploads = sorted(current["uploads"], key=lambda item: str(item["key"]).endswith(".html"))
    for entry in uploads:
        key = str(entry["key"])
        command = [
            "s3api", "put-object", "--bucket", str(current["bucket"]), "--key", key,
            "--body", str(release_dir / "site" / key), "--content-type", str(entry["content_type"]),
            "--metadata", metadata_arg(entry, str(current["source_sha"])),
        ]
        for option, value in entry.get("preserve_headers", {}).items():
            command.extend(["--" + option.replace("_", "-"), str(value)])
        aws(command, profile)

    for entry in current["deletes"]:
        aws(["s3api", "delete-object", "--bucket", str(current["bucket"]), "--key", str(entry["key"])], profile)

    invalidation_id = None
    if current["invalidations"]:
        response = aws(
            ["cloudfront", "create-invalidation", "--distribution-id", distribution_id, "--paths", *current["invalidations"]],
            profile,
        )
        invalidation_id = response["Invalidation"]["Id"]  # type: ignore[index]
        command = [
            "aws", "cloudfront", "wait", "invalidation-completed",
            "--distribution-id", distribution_id, "--id", invalidation_id, "--no-cli-pager",
        ]
        if profile:
            command.extend(["--profile", profile])
        subprocess.run(command, check=True, env={**os.environ, "AWS_PAGER": ""})
    return {"uploads": len(uploads), "deletes": len(current["deletes"]), "invalidation_id": invalidation_id}


def verify_release(release_dir: Path, base_url: str, plan_path: Path) -> None:
    manifest = load_manifest(release_dir)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    by_key = {item["key"]: item for item in manifest["files"]}
    for planned in plan["uploads"]:
        key = planned["key"]
        url = base_url.rstrip("/") + "/" + urllib.parse.quote(key, safe="/")
        request = urllib.request.Request(url, headers={"User-Agent": "ajha-info-deploy/1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
        actual = hashlib.sha256(body).hexdigest()
        if actual != by_key[key]["sha256"]:
            raise ValueError(f"published content hash mismatch: {key}")


def parse_deletes(raw: str) -> list[str]:
    value = json.loads(raw)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("delete paths must be a JSON array of strings")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--release-dir", type=Path, required=True)
    plan_parser.add_argument("--bucket", required=True)
    plan_parser.add_argument("--delete-paths-json", default="[]")
    plan_parser.add_argument("--profile")
    plan_parser.add_argument("--output", type=Path, required=True)
    plan_parser.add_argument("--github-output", type=Path)
    plan_parser.add_argument("--github-summary", type=Path)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--release-dir", type=Path, required=True)
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--distribution-id", required=True)
    apply_parser.add_argument("--profile")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--release-dir", type=Path, required=True)
    verify_parser.add_argument("--plan", type=Path, required=True)
    verify_parser.add_argument("--base-url", required=True)

    args = parser.parse_args()
    if args.command == "plan":
        plan = calculate_plan(args.release_dir, args.bucket, parse_deletes(args.delete_paths_json), args.profile)
        args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_outputs(plan, args.github_output)
        write_summary(plan, args.github_summary)
        print(json.dumps({"plan_sha256": plan["plan_sha256"], "uploads": len(plan["uploads"]), "deletes": len(plan["deletes"])}))
    elif args.command == "apply":
        print(json.dumps(apply_plan(args.release_dir, args.plan, args.distribution_id, args.profile), sort_keys=True))
    else:
        verify_release(args.release_dir, args.base_url, args.plan)
        print("published files match the approved artifact")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as error:
        print(f"deployment error: {error}", file=sys.stderr)
        raise SystemExit(1)
