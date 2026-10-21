import io
import json
import stat
import zipfile
from pathlib import Path

import numpy as np
import pytest
import tifffile
from PIL import Image

from scripts import audit_data


def tiff_bytes(array: np.ndarray) -> bytes:
    stream = io.BytesIO()
    tifffile.imwrite(stream, array, photometric="minisblack")
    return stream.getvalue()


def write_archive(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return path


def arrays(frames: int = 6) -> tuple[np.ndarray, np.ndarray]:
    image = np.stack([np.full((16, 16), index * 400, np.uint16) for index in range(frames)])
    annotation = np.zeros((frames, 16, 16), np.uint8)
    annotation[:, 4:12, 4] = 255
    annotation[:, 4:12, 11] = 255
    annotation[:, 4, 4:12] = 255
    annotation[:, 11, 4:12] = 255
    return image, annotation


@pytest.mark.parametrize("name", ["../evil.tif", "/evil.tif", "Videos\\evil.tif", "C:/evil.tif"])
def test_archive_rejects_path_traversal(tmp_path: Path, name: str) -> None:
    path = write_archive(tmp_path / "bad.zip", {name: b"no"})
    if "\\" in name:
        # Windows' ZIP writer normalizes separators; restore malicious raw names.
        path.write_bytes(path.read_bytes().replace(name.replace("\\", "/").encode(), name.encode()))
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="unsafe"):
        audit_data.safe_members(archive)


def test_archive_rejects_symlink_and_duplicate_names(tmp_path: Path) -> None:
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo("Videos/WH01.tif")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"outside")
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="symlink"):
        audit_data.safe_members(archive)
    write_archive(path, {"Videos/WH01.tif": b"a", "Videos/wh01.tif": b"b"})
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="duplicate"):
        audit_data.safe_members(archive)


def test_archive_size_limit_before_reading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_archive(tmp_path / "large.zip", {"Videos/WH01.tif": b"a" * 32})
    monkeypatch.setattr(audit_data, "MAX_MEMBER_BYTES", 16)
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="size"):
        audit_data.safe_members(archive)


def test_archive_total_count_and_ratio_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_archive(tmp_path / "many.zip", {"a": b"x" * 10, "b": b"x" * 10})
    with monkeypatch.context() as patch:
        patch.setattr(audit_data, "MAX_TOTAL_BYTES", 15)
        with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="size"):
            audit_data.safe_members(archive)
    with monkeypatch.context() as patch:
        patch.setattr(audit_data, "MAX_MEMBERS", 1)
        with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="count"):
            audit_data.safe_members(archive)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("zeros", b"0" * 100_000)
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="ratio"):
        audit_data.safe_members(archive)


def test_tiff_decoded_size_checked_before_array_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = io.BytesIO()
    tifffile.imwrite(
        stream, np.zeros((10, 128, 128), np.uint16), compression="deflate", photometric="minisblack"
    )
    path = write_archive(tmp_path / "compressed-tiff.zip", {"Videos/WH01.tif": stream.getvalue()})
    monkeypatch.setattr(audit_data, "MAX_MEMBER_BYTES", 10_000)
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="bounded"):
        audit_data.read_stack(archive, archive.getinfo("Videos/WH01.tif"))


def test_binary_encoding_and_boundary_metrics() -> None:
    _, annotation = arrays()
    binary, values = audit_data.normalize_annotation(annotation)
    binary_one, one_values = audit_data.normalize_annotation((annotation != 0).astype(np.uint8))
    assert np.array_equal(binary, binary_one)
    assert values == [0, 255]
    assert one_values == [0, 1]
    metrics = audit_data.annotation_metrics(binary[0])
    assert metrics["components_8_connected"] == 1
    assert metrics["filled_area_pixels_derived"] == 64
    assert metrics["enclosed_background_components_4_connected"] == 1
    assert not metrics["touches_border"]
    with pytest.raises(ValueError, match="binary"):
        audit_data.normalize_annotation(np.array([[[0, 2]]], np.uint8))
    with pytest.raises(ValueError, match="binary"):
        audit_data.normalize_annotation(np.array([[[0, 1, 255]]], np.uint8))


def test_missing_pair_and_mismatched_shape_are_reported(tmp_path: Path) -> None:
    image, annotation = arrays()
    path = write_archive(
        tmp_path / "mismatch.zip",
        {
            "Videos/WH01.tif": tiff_bytes(image),
            "Segmentations/WH01.tif": tiff_bytes(annotation[:-1]),
            "Videos/WH02.tif": tiff_bytes(image),
        },
    )
    report = audit_data.audit_archive(path, tmp_path / "audit", tmp_path / "sample", ())
    assert report["parsed_sequence_count"] == 0
    assert report["sequence_count"] == 2
    assert "shape mismatch" in report["sequences"][0]["issues"][0]
    assert "missing" in report["sequences"][1]["issues"][0]


def test_frame_order_samples_and_duplicates_are_measured(tmp_path: Path) -> None:
    image, annotation = arrays()
    path = write_archive(
        tmp_path / "fixture.zip",
        {
            "Videos/WH01.tif": tiff_bytes(image),
            "Segmentations/WH01.tif": tiff_bytes(annotation),
            "Videos/Test01.tif": tiff_bytes(image),
            "Segmentations/Test01.tif": tiff_bytes((annotation != 0).astype(np.uint8)),
        },
    )
    output, sample = tmp_path / "audit", tmp_path / "sample"
    report = audit_data.audit_archive(path, output, sample, ("WH01",))
    assert report["parsed_sequence_count"] == 2
    assert report["frame_pair_count"] == 12
    assert report["duplicates"]["image"]["cross_sequence_group_count"] == 6
    assert report["duplicates"]["annotation"]["cross_sequence_group_count"] == 0
    assert report["duplicates"]["annotation_binary"]["cross_sequence_group_count"] == 1
    test_sequence = next(item for item in report["sequences"] if item["sequence_id"] == "Test01")
    assert test_sequence["name_hint"] == "candidate_test"
    assert test_sequence["split"] == "unknown"
    manifest = json.loads((output / "frame-manifest.json").read_text(encoding="utf-8"))
    assert [row["time_index"] for row in manifest if row["sequence_id"] == "WH01"] == list(range(6))
    samples = json.loads((sample / "sample-manifest.json").read_text(encoding="utf-8"))
    assert [row["source_frame_index"] for row in samples] == list(range(6))
    for row in samples:
        with Image.open(sample / row["image_png"]) as saved:
            assert np.array_equal(np.asarray(saved), image[row["time_index"]])
        assert row["image_file_sha256"] == audit_data.sha256_file(sample / row["image_png"])
    assert (output / "annotation-contact-sheet.png").is_file()


@pytest.mark.parametrize("matches_hash,unexpected", [(False, []), (True, ["extra.bin"])])
def test_cli_rejects_unverified_source_identity(monkeypatch, matches_hash, unexpected):
    from scripts import audit_data

    monkeypatch.setattr("sys.argv", ["audit_data.py"])
    monkeypatch.setattr(
        audit_data,
        "audit_archive",
        lambda *_args: {
            "parsed_sequence_count": 1,
            "sequence_count": 1,
            "frame_pair_count": 6,
            "matches_known_download_sha256": matches_hash,
            "unexpected_members": unexpected,
        },
    )
    assert audit_data.main() == 1
