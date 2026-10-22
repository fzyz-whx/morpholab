"""Bounded PNG assets from already computed regions; no inference or scientific scoring."""

from __future__ import annotations

import hashlib
import io
import os
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def _png(path: Path, pixels: np.ndarray, url: str) -> dict[str, str]:
    stream = io.BytesIO()
    Image.fromarray(pixels).save(stream, format="PNG")
    content = stream.getvalue()
    descriptor = {"url": url, "sha256": hashlib.sha256(content).hexdigest()}
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == descriptor["sha256"]:
        # Do not rewrite legacy assets while browsers read them.
        return descriptor
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)
    return descriptor


def image_assets(result: dict[str, Any], directory: Path, identifier: str) -> dict[str, Any]:
    """Convert private numerical arrays to immutable PNG links, including old local jobs."""
    if not 1 <= len(result["frames"]) <= 24:
        raise ValueError("Invalid result length")
    frames = []
    for frame in result["frames"]:
        if "images" in frame and "region" not in frame:
            frames.append(frame)
            continue
        lead = frame["lead"]
        if type(lead) is not int or not 1 <= lead <= 24:
            raise ValueError("Invalid asset lead")
        region = np.asarray(frame["region"])
        target = None if frame["target_region"] is None else np.asarray(frame["target_region"])
        if region.shape != (64, 64) or (target is not None and target.shape != (64, 64)):
            raise ValueError("Invalid result image grid")
        if not np.isin(region, (0, 1)).all() or (
            target is not None and not np.isin(target, (0, 1)).all()
        ):
            raise ValueError("Result image is not binary")

        def write(layer: str, pixels: np.ndarray, lead: int = lead) -> dict[str, str]:
            return _png(
                directory / identifier / f"lead-{lead}-{layer}.png",
                pixels,
                f"/api/v1/jobs/{identifier}/frames/{lead}?layer={layer}",
            )

        images = {
            "prediction": write("prediction", region.astype(np.uint8) * 255),
            "target": None,
            "error": None,
        }
        if target is not None:
            images["target"] = write("target", target.astype(np.uint8) * 255)
            errors = np.zeros((64, 64, 4), dtype=np.uint8)
            errors[(region == 1) & (target == 0)] = (226, 184, 117, 150)
            errors[(region == 0) & (target == 1)] = (215, 149, 171, 150)
            images["error"] = write("error", errors)
        frames.append(
            {key: value for key, value in frame.items() if key not in {"region", "target_region"}}
            | {
                "images": images,
                "target_area": int(target.sum()) if target is not None else None,
            }
        )
    return {
        **result,
        "provenance": "MODEL_PREDICTION",
        "frames": frames,
        "run_id": result.get("run_id", result.get("model", {}).get("run_id")),
    }
