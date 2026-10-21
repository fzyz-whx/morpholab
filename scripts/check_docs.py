"""Check public repository files without contacting external web services.

Only Git-tracked and non-ignored untracked files are inspected. Findings name a
file and rule, never the potentially sensitive matching content. Pattern checks
are a small guardrail, not a comprehensive secret or licensing audit.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

MAX_PUBLIC_BYTES = 5 * 1024 * 1024
PRIVATE_SUFFIXES = {".zip", ".tif", ".tiff", ".avi", ".mp4", ".pt", ".pth", ".ckpt", ".onnx"}
PATTERNS = {
    "personal absolute path": re.compile(r"(?i)(?:[a-z]:[\\/]Users[\\/]|/Users/|/home/)[\w.-]+"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub credential": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"
    ),
    "API credential": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    "credential assignment": re.compile(
        r"(?i)\b(?:api_key|access_token|password|secret_key)\s*[:=]\s*[\"']"
        r"[A-Za-z0-9_./+\-=]{16,}[\"']"
    ),
}
LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)


def public_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return sorted({root / name.decode("utf-8") for name in result.stdout.split(b"\0") if name})


def prose(text: str) -> str:
    """Remove fenced examples, retaining line counts for useful diagnostics."""
    lines = []
    fence = ""
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if not fence:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = ""
            lines.append("")
        else:
            lines.append("" if fence else line)
    return "\n".join(lines)


def heading_ids(text: str) -> set[str]:
    ids: set[str] = set()
    counts: dict[str, int] = {}
    for line in prose(text).splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        slug = re.sub(r"[^\w\- ]", "", match.group(1).lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        ids.add(f"{slug}-{count}" if count else slug)
    ids.update(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', text))
    return ids


def check_link(root: Path, source: Path, destination: str) -> str | None:
    destination = destination.strip("<>")
    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        return None
    relative = unquote(parsed.path)
    target = root / relative.lstrip("/") if relative.startswith("/") else source.parent / relative
    target = target.resolve() if relative else source.resolve()
    if not target.is_relative_to(root.resolve()):
        return "local link escapes repository"
    if not target.exists():
        return "missing local link target"
    if parsed.fragment and target.is_file() and target.suffix.lower() == ".md":
        if unquote(parsed.fragment) not in heading_ids(target.read_text(encoding="utf-8-sig")):
            return "missing local Markdown heading"
    return None


def check_repository(root: Path, files: list[Path]) -> list[str]:
    findings = []
    for path in files:
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            findings.append(f"{name}: public symlink requires manual review")
            continue
        if not path.is_file():
            findings.append(f"{name}: listed public file is missing or not a regular file")
            continue
        if path.stat().st_size > MAX_PUBLIC_BYTES:
            findings.append(f"{name}: exceeds 5 MiB public-file limit")
            continue
        if path.suffix.lower() in PRIVATE_SUFFIXES or (
            path.name.startswith(".env") and path.name != ".env.example"
        ):
            findings.append(f"{name}: private data, weights, archive or environment file")
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{name}: {label}")
        if path.suffix.lower() != ".md":
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line and not (line.endswith("  ") and not line.endswith("   ")):
                findings.append(f"{name}:{number}: trailing whitespace (two-space break allowed)")
        body = prose(text)
        for match in [*LINK.finditer(body), *REFERENCE.finditer(body)]:
            error = check_link(root, path, match.group(1))
            if error:
                line_number = body.count("\n", 0, match.start()) + 1
                findings.append(f"{name}:{line_number}: {error}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().root.resolve()
    try:
        findings = check_repository(root, public_files(root))
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        print("Repository check failed: unable to enumerate or read public files.")
        return 2
    if findings:
        print("\n".join(findings))
        return 1
    print("Public repository and local documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
