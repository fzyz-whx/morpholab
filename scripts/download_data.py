"""Download and inspect the published Zenodo archive without executing its contents.

Run: uv run python scripts/download_data.py
Only the Python standard library is required. Interrupted .part files are resumed.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

API_URL = "https://zenodo.org/api/records/7660424"
ROOT = Path(__file__).resolve().parents[1]


class ChecksumMismatch(ValueError):
    """A complete cache fails its published checksum and cannot be resumed."""


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def hashes(path: Path) -> dict[str, str]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(chunk)
            sha256.update(chunk)
    return {"md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def verify(path: Path, size: int, checksum: str) -> dict[str, str]:
    if path.stat().st_size != size:
        raise ValueError(f"Size mismatch: {path.stat().st_size} != {size}")
    algorithm, expected = checksum.split(":", 1)
    if algorithm != "md5":
        raise ValueError(f"Unsupported published checksum algorithm: {algorithm}")
    result = hashes(path)
    if result[algorithm] != expected:
        raise ChecksumMismatch("Published MD5 mismatch; cached bytes were not accepted")
    return result


def download(
    url: str,
    target: Path,
    size: int,
    checksum: str,
    *,
    timeout: float = 30,
    attempts: int = 4,
    max_seconds: float = 1800,
) -> dict[str, Any]:
    """Bounded streaming download; only verified content receives its final name."""
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    start = time.monotonic()
    if target.exists():
        return {"cached": True, "attempts": 0, "hashes": verify(target, size, checksum)}
    errors = []
    for attempt in range(1, attempts + 1):
        try:
            offset = part.stat().st_size if part.exists() else 0
            if offset > size:
                raise ValueError("Partial cache exceeds published size; remove it before retrying")
            if offset < size:
                headers = {"User-Agent": "MorphoLab-data-audit/0.1", "Accept-Encoding": "identity"}
                if offset:
                    headers["Range"] = f"bytes={offset}-"
                request = urllib.request.Request(url, headers=headers)
                remaining = max_seconds - (time.monotonic() - start)
                if remaining <= 0:
                    raise TimeoutError("Overall download time budget exhausted")
                with urllib.request.urlopen(request, timeout=min(timeout, remaining)) as response:
                    if response.status == 206:
                        match = re.fullmatch(
                            r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", "")
                        )
                        if (
                            not match
                            or int(match[1]) != offset
                            or not offset <= int(match[2]) < size
                            or int(match[3]) != size
                        ):
                            raise ValueError("Invalid Content-Range; refusing unsafe append")
                        response_end = int(match[2])
                    elif response.status == 200:
                        offset = 0  # Server ignored Range: restart, never append duplicate bytes.
                        response_end = size - 1
                    else:
                        raise ValueError(f"Unexpected HTTP status: {response.status}")
                    last_report = 0.0
                    with part.open("ab" if offset else "wb") as output:
                        while True:
                            if time.monotonic() - start > max_seconds:
                                raise TimeoutError("Overall download time budget exhausted")
                            # One buffered read lets the wall-clock budget be checked even
                            # when a server trickles bytes without a socket timeout.
                            chunk = response.read1(256 * 1024)
                            if not chunk:
                                break
                            output.write(chunk)
                            offset += len(chunk)
                            if offset > size:
                                raise ValueError("Response exceeds published size")
                            if offset > response_end + 1:
                                raise ValueError("Response exceeds declared Content-Range")
                            now = time.monotonic()
                            if now - last_report >= 5:
                                print(
                                    f"attempt {attempt}/{attempts}: {offset}/{size} bytes "
                                    f"({offset / size:.1%}), {now - start:.1f}s",
                                    flush=True,
                                )
                                last_report = now
                    if offset != response_end + 1:
                        raise ValueError("Response ended before its declared range was complete")
            result = verify(part, size, checksum)
            part.replace(target)
            return {"cached": False, "attempts": attempt, "hashes": result, "retry_errors": errors}
        except (OSError, ValueError, urllib.error.URLError, http.client.IncompleteRead) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            print(errors[-1], flush=True)
            if isinstance(exc, ChecksumMismatch):
                # Complete corrupt bytes cannot be repaired by appending. Only our
                # disposable partial cache is removed; verified final files stay put.
                part.unlink(missing_ok=True)
            if time.monotonic() - start >= max_seconds:
                break
            if attempt < attempts:
                time.sleep(min(attempt, max(0, max_seconds - (time.monotonic() - start))))
    raise RuntimeError(f"Download failed after bounded retries: {errors}")


def inventory(archive: Path) -> dict[str, Any]:
    """List central-directory metadata, reading only bounded README/LICENSE text."""
    members = []
    texts = []
    groups: Counter[str] = Counter()
    types: Counter[str] = Counter()
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            path = PurePosixPath(item.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in item.filename
                or (path.parts and ":" in path.parts[0])
            ):
                raise ValueError(f"Unsafe archive path: {item.filename!r}")
            groups[path.parts[0]] += 1
            if not item.is_dir():
                types[path.suffix.lower() or "[no extension]"] += 1
            members.append(
                {
                    "path": item.filename,
                    "size_bytes": item.file_size,
                    "compressed_bytes": item.compress_size,
                    "crc32": f"{item.CRC:08x}",
                    "directory": item.is_dir(),
                }
            )
            if (
                path.name.lower().startswith(("readme", "license", "licence", "copying"))
                and not item.is_dir()
            ):
                text = None
                if item.file_size <= 1024 * 1024:
                    with bundle.open(item) as stream:
                        content = stream.read(1024 * 1024 + 1)
                    if len(content) <= 1024 * 1024:
                        text = content.decode("utf-8", errors="replace")
                texts.append(
                    {"path": item.filename, "text": text, "skipped_too_large": text is None}
                )
    return {
        "archive": "raw/zenodo_7660424/Dataset.zip",
        "scope": "ZIP directory and bounded README/LICENSE text only; images not decoded",
        "member_count": len(members),
        "uncompressed_bytes": sum(m["size_bytes"] for m in members),
        "groups": dict(sorted(groups.items())),
        "file_types": dict(sorted(types.items())),
        "documentation": texts,
        "members": members,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--max-seconds", type=float, default=1800)
    args = parser.parse_args()
    if args.timeout <= 0 or args.attempts < 1 or args.max_seconds <= 0:
        parser.error("timeouts and attempts must be positive")
    base = args.artifacts / "raw" / "zenodo_7660424"
    status: dict[str, Any] = {
        "source": API_URL,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "running",
    }
    started = time.monotonic()
    save_json(base / "download-status.json", status)
    try:
        with urllib.request.urlopen(API_URL, timeout=args.timeout) as response:
            metadata = json.load(response)
        save_json(base / "record-api.json", metadata)
        files = [f for f in metadata["files"] if f["key"] == "Dataset.zip"]
        if len(files) != 1:
            raise ValueError("Expected exactly one Dataset.zip in record API")
        record = files[0]
        status.update(
            {
                "file": record["key"],
                "published_size_bytes": record["size"],
                "published_checksum": record["checksum"],
                "license": metadata["metadata"].get("license"),
                "url": record["links"]["self"],
            }
        )
        target = base / "Dataset.zip"
        status.update(
            download(
                record["links"]["self"],
                target,
                record["size"],
                record["checksum"],
                timeout=args.timeout,
                attempts=args.attempts,
                max_seconds=args.max_seconds,
            )
        )
        save_json(args.artifacts / "audit" / "archive-inventory.json", inventory(target))
        status["status"] = "verified"
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        status.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        print(status["error"], flush=True)
        return 1
    finally:
        status["elapsed_seconds"] = round(time.monotonic() - started, 3)
        status["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save_json(base / "download-status.json", status)


if __name__ == "__main__":
    raise SystemExit(main())
