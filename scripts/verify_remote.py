"""Compare local HEAD with its live remote branch without printing credentials."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


class VerificationError(Exception):
    """A safe-to-display synchronization failure."""


def git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=60, check=True
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise VerificationError(
            "Git command failed; check branch and remote access locally."
        ) from error
    return result.stdout.strip()


def verify_remote(root: Path) -> str:
    head = git(root, "rev-parse", "--verify", "HEAD")
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    remote = git(root, "config", "--get", f"branch.{branch}.remote")
    merge_ref = git(root, "config", "--get", f"branch.{branch}.merge")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote) or remote == ".":
        raise VerificationError("An upstream on a named external remote is required.")
    if not merge_ref.startswith("refs/heads/"):
        raise VerificationError("Upstream must refer to a remote branch.")
    output = git(root, "ls-remote", "--exit-code", "--refs", remote, merge_ref)
    matches = [line.split("\t") for line in output.splitlines()]
    hashes = [parts[0] for parts in matches if len(parts) == 2 and parts[1] == merge_ref]
    if len(hashes) != 1 or not re.fullmatch(r"[0-9a-f]{40,64}", hashes[0]):
        raise VerificationError("Remote branch did not return one valid commit SHA.")
    if head != hashes[0]:
        raise VerificationError(
            "Local HEAD differs from the live remote branch; synchronize first."
        )
    return head


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        sha = verify_remote(args.root.resolve())
    except VerificationError as error:
        print(f"Remote verification failed: {error}")
        return 1
    print(f"Local HEAD matches live remote branch: {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
