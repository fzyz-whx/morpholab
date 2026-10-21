from pathlib import Path

from scripts.check_docs import MAX_PUBLIC_BYTES, check_repository, public_files


def test_local_links_anchors_and_two_space_breaks(tmp_path: Path) -> None:
    source = tmp_path / "README.md"
    target = tmp_path / "guide.md"
    source.write_text("Start  \n[Guide](guide.md#用法)\n", encoding="utf-8")
    target.write_text("# 用法\n", encoding="utf-8")
    assert check_repository(tmp_path, [source, target]) == []
    source.write_text("[Missing](guide.md#absent)\n[Outside](../other.md)\n", encoding="utf-8")
    findings = check_repository(tmp_path, [source, target])
    assert any("missing local Markdown heading" in item for item in findings)
    assert any("escapes repository" in item for item in findings)


def test_missing_links_and_reference_links_but_no_network(tmp_path: Path) -> None:
    source = tmp_path / "README.md"
    source.write_text(
        "[Missing](missing.md)\n[remote](https://invalid.example)\n"
        "[guide]: missing-too.md\n```md\n[example](template.md)\n```\n",
        encoding="utf-8",
    )
    assert len(check_repository(tmp_path, [source])) == 2


def test_secret_paths_and_large_files_are_reported_without_content(tmp_path: Path) -> None:
    source = tmp_path / "README.md"
    secret = "gh" + "p_" + "a" * 36
    source.write_text(secret + "\n" + "C:" + "\\Users\\PrivatePerson\\data", encoding="utf-8")
    big_file = tmp_path / "large.bin"
    with big_file.open("wb") as stream:
        stream.truncate(MAX_PUBLIC_BYTES + 1)
    archive = tmp_path / "dataset.zip"
    archive.write_bytes(b"fixture")
    findings = check_repository(tmp_path, [source, big_file, archive])
    assert len(findings) == 4
    assert secret not in "\n".join(findings)
    assert "PrivatePerson" not in "\n".join(findings)


def test_git_enumeration_excludes_ignored_local_data(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("data/\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "private.txt").write_text("local", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Public\n", encoding="utf-8")
    assert {path.name for path in public_files(tmp_path)} == {".gitignore", "README.md"}
