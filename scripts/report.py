"""Publish a checked, sequence-weighted validation report from an immutable run."""

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
METRICS = (
    "iou",
    "dice",
    "mean_boundary_distance",
    "hausdorff95",
    "area_mae",
    "signed_area_error",
    "empty_boundary_mismatch",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def public_metadata(value):
    """Reject accidental local-machine paths rather than silently publishing them."""
    if isinstance(value, dict):
        return {k: public_metadata(v) for k, v in value.items()}
    if isinstance(value, list):
        return [public_metadata(v) for v in value]
    if isinstance(value, str) and (
        Path(value).is_absolute() or PureWindowsPath(value).is_absolute()
    ):
        raise ValueError("Absolute local path in public metadata")
    return value


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_report(run_dir, manifest_path, root=ROOT):
    run = load(run_dir / "run.json")
    summary = load(run_dir / "summary.json")
    rows = load(run_dir / "metrics.json")
    failures = load(run_dir / "failure-cases.json")
    manifest = load(manifest_path)
    require(
        run["status"] == "complete" and run["git_dirty"] is False,
        "Formal report requires a complete, clean-source run",
    )
    require(
        run["manifest_scope"] == "complete_62_sequence_source" and len(manifest["sequences"]) == 62,
        "Complete 62-sequence manifest required",
    )
    require(digest(manifest_path) == run["source_manifest_sha256"], "Manifest hash mismatch")
    require(
        run["split"] == "validation" and run["protocol"] == manifest["protocol"],
        "Validation split/protocol mismatch",
    )
    require(
        run["horizons"] == [4, 12, 24] and run["observations"] == 4,
        "Report requires L=4 and H=4/12/24",
    )
    require(run["baselines"] == ["persistence", "constant_normal_speed"], "Unexpected baselines")
    require(
        run["target_provenance"] == "DERIVED_ANNOTATION"
        and run["prediction_provenance"] == "PREDICTION",
        "Provenance mismatch",
    )
    require(run["versions"] and run["implementation_file_sha256"], "Missing source metadata")
    for name, expected in run["implementation_file_sha256"].items():
        require(
            not Path(name).is_absolute() and ".." not in Path(name).parts,
            "Invalid implementation path",
        )
        blob = subprocess.run(
            ["git", "show", f"{run['git_sha']}:{name}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        require(hashlib.sha256(blob).hexdigest() == expected, f"Source hash mismatch: {name}")

    selected = {
        q["sequence_id"] for q in manifest["sequences"] if q["project_split"] == "validation"
    }
    require(
        len(selected) == run["n_sequences"] == run["n_sequences_with_windows"],
        "Sequence count mismatch",
    )
    groups = defaultdict(list)
    by_key = {}
    for row in rows:
        require(
            row["project_split"] == "validation" and row["sequence_id"] in selected,
            "Metric row outside validation scope",
        )
        require(
            row["baseline"] in run["baselines"] and row["lead"] in range(1, 25),
            "Unexpected metric baseline/lead",
        )
        require(row["is_endpoint"] == (row["lead"] in run["horizons"]), "Endpoint flag mismatch")
        key = (row["baseline"], row["sequence_id"], row["window_start"], row["lead"])
        require(key not in by_key, "Duplicate metric row")
        by_key[key] = row
        require(all(math.isfinite(row[m]) for m in METRICS), "Nonfinite metric")
        groups[key[:2] + (key[3],)].append(row)
    qc = summary["window_qc"]
    require({q["sequence_id"] for q in qc} == selected, "QC sequence scope mismatch")
    counts = {q["sequence_id"]: q["valid_windows"] for q in qc}
    require(
        sum(counts.values()) == run["n_windows"]
        and sum(q["qc_excluded_windows"] for q in qc) == run["qc_excluded_windows"],
        "QC totals mismatch",
    )
    for q in qc:
        require(
            q["candidate_windows"] == q["valid_windows"] + q["qc_excluded_windows"],
            "QC candidate count mismatch",
        )
    expected_sequence = {}
    aggregate = []
    reference_windows = None
    for baseline in sorted(run["baselines"]):
        for lead in range(1, 25):
            seq = []
            windows = set()
            for sequence_id in sorted(selected):
                values = groups[(baseline, sequence_id, lead)]
                require(len(values) == counts[sequence_id], "Missing lead/window rows")
                windows.update((sequence_id, v["window_start"]) for v in values)
                means = {m: sum(v[m] for v in values) / len(values) for m in METRICS}
                expected_sequence[(baseline, sequence_id, lead)] = means
                seq.append(means)
            if reference_windows is None:
                reference_windows = windows
            require(windows == reference_windows, "Lead windows do not match")
            aggregate.append(
                {
                    "baseline": baseline,
                    "lead": lead,
                    "n_sequences": len(selected),
                    "n_windows": sum(counts.values()),
                    **{m: sum(v[m] for v in seq) / len(seq) for m in METRICS},
                }
            )
    require(len(summary["per_sequence"]) == len(expected_sequence), "Sequence summary size")
    seen_sequences = set()
    for row in summary["per_sequence"]:
        key = (row["baseline"], row["sequence_id"], row["lead"])
        require(
            key in expected_sequence and key not in seen_sequences,
            "Unexpected or duplicate sequence summary",
        )
        seen_sequences.add(key)
        require(row["n_windows"] == counts[row["sequence_id"]], "Sequence windows mismatch")
        for metric in METRICS:
            require(
                math.isclose(row[metric], expected_sequence[key][metric], abs_tol=1e-10),
                f"Sequence aggregate mismatch: {metric}",
            )
    for name, expected in (
        ("aggregate", aggregate),
        ("endpoints", [r for r in aggregate if r["lead"] in run["horizons"]]),
    ):
        require(len(summary[name]) == len(expected), f"{name} length mismatch")
        recorded = {(r["baseline"], r["lead"]): r for r in summary[name]}
        require(len(recorded) == len(expected), f"Duplicate {name}")
        for row in expected:
            actual = recorded[(row["baseline"], row["lead"])]
            for metric in (*METRICS, "n_sequences", "n_windows"):
                require(
                    math.isclose(actual[metric], row[metric], abs_tol=1e-10),
                    f"{name} mismatch: {metric}",
                )
    for failure in failures:
        key = tuple(failure[k] for k in ("baseline", "sequence_id", "window_start", "lead"))
        require(failure["metrics"] == by_key.get(key), "Failure metrics mismatch")
        image_path = (run_dir / failure["png_relpath"]).resolve()
        require(
            image_path.is_relative_to(run_dir.resolve()) and image_path.is_file(),
            "Invalid failure image path",
        )
    return public_metadata(
        {
            "schema_version": "morpholab-baseline-report-v1",
            "run": run,
            "source_files_sha256": {
                name: digest(run_dir / name)
                for name in ("run.json", "summary.json", "metrics.json", "failure-cases.json")
            },
            "source_archive": manifest["source_archive"],
            "qc_parameters": manifest["qc_parameters"],
            "aggregation": summary["aggregation"],
            "aggregate": aggregate,
            "endpoints": [r for r in aggregate if r["lead"] in run["horizons"]],
            "window_qc": qc,
            "failure_cases": failures,
        }
    )


def plot_report(report, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with plt.rc_context(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 160}
    ):
        fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout="constrained")
        for ax, metric, label in zip(
            axes,
            ("iou", "mean_boundary_distance", "area_mae"),
            ("IoU (higher is better)", "Mean boundary distance (grid px)", "Area MAE (grid px²)"),
            strict=True,
        ):
            for baseline, color, style in (
                ("persistence", "#27658a", "-"),
                ("constant_normal_speed", "#b46627", "--"),
            ):
                rows = [r for r in report["aggregate"] if r["baseline"] == baseline]
                ax.plot(
                    [r["lead"] for r in rows],
                    [r[metric] for r in rows],
                    label=baseline.replace("_", " "),
                    color=color,
                    linestyle=style,
                    linewidth=2,
                )
            ax.set(
                xlabel="Prediction lead (source frames)",
                ylabel=label,
                xlim=(1, 24),
                xticks=[1, 4, 8, 12, 16, 20, 24],
            )
            ax.grid(alpha=0.18)
        axes[0].legend(frameon=False, fontsize=8)
        fig.suptitle(
            "VALIDATION · 64×64 working grid · equal sequence weights "
            f"(n={report['run']['n_sequences']})\n"
            f"{report['run']['n_windows']} overlapping windows; "
            "deterministic baselines; no test evaluation",
            fontsize=11,
        )
        fig.savefig(destination, metadata={"Description": "Real validation algorithm results"})
        plt.close(fig)


def write_markdown(report, destination):
    run = report["run"]
    indexed = {(r["baseline"], r["lead"]): r for r in report["aggregate"]}
    require(
        all(
            indexed[("constant_normal_speed", lead)]["iou"] <= indexed[("persistence", lead)]["iou"]
            for lead in range(1, 25)
        ),
        "This report interpretation requires constant-speed IoU never exceeding persistence",
    )
    require(
        all(
            indexed[("constant_normal_speed", lead)]["area_mae"]
            < indexed[("persistence", lead)]["area_mae"]
            for lead in run["horizons"]
        ),
        "This report interpretation requires lower constant-speed endpoint area MAE",
    )
    failure = next(
        f
        for f in report["failure_cases"]
        if f["baseline"] == "constant_normal_speed" and f["sequence_id"] == "WH24"
    )
    lines = [
        "# 几何基线正式 validation 报告 v1",
        "",
        "果蝇胚胎 in vivo 激光创面闭合；真实算法运行结果，非合成效果图。"
        "本报告仅包含确定性几何基线，不包含神经模型结果。",
        "",
        f"来源 Git：`{run['git_sha']}`；源运行 `git_dirty=false`、`status=complete`。",
        f"完整 62 序列源清单 SHA256：`{run['source_manifest_sha256']}`。",
        f"源清单完整性不代表评估了全部序列：本次仅 validation 的 {run['n_sequences']} 序列、"
        f"{run['n_windows']} 个有效窗口，QC 排除 {run['qc_excluded_windows']} 个窗口。",
        "",
        "采用项目新协议 `morpholab-split-v1`；官方实验级划分未知（null），"
        "不是对官方 test 成绩的复现。"
        f"L=4，H=4/12/24，stride={run['stride']}；所有 lead 共用最长 H 的有效窗口。"
        f"先在各序列内平均窗口，再对 {run['n_sequences']} 条序列等权；重叠窗口不是独立实验。"
        "两种基线均确定性，无训练、无三 seed 统计，图中无随机种子误差带，也未进行显著性检验。",
        "",
        "![正式 validation 曲线](../../assets/figures/baselines-validation-v1.png)",
        "",
        "曲线覆盖 lead 1–24。距离单位是 64×64 工作网格 pixel，面积单位是工作网格 pixel²；"
        "不能解释为微米或原始图像像素。目标是骨架化注释经填充与降采样得到的 DERIVED_ANNOTATION，"
        "不是原始人工区域真值。",
        "",
        "| Baseline | Lead | IoU ↑ | Dice ↑ | Mean boundary distance ↓ "
        "| HD95 ↓ | Area MAE ↓ | Empty mismatch |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in report["endpoints"]:
        lines.append(
            f"| {r['baseline']} | {r['lead']} | "
            + " | ".join(
                f"{r[m]:.6f}"
                for m in (
                    "iou",
                    "dice",
                    "mean_boundary_distance",
                    "hausdorff95",
                    "area_mae",
                    "empty_boundary_mismatch",
                )
            )
            + " |"
        )
    lines += [
        "",
        "恒速基线在全部 24 个 lead 的序列等权 IoU 均未超过 persistence；"
        "面积 MAE 在三个正式 endpoint（4/12/24）均更低。"
        "完整曲线中 lead 1 持平、lead 2 略高，其余 22 个 lead 更低。"
        "面积接近并不保证形状与位置重叠更好，不能据此宣称恒速总体优越。"
        "本次不调参追分，也不据此宣称论文新颖性或 NCA 有效性。",
        "",
        "边界采用内数字边界的双向最近距离。两侧均空时 IoU/Dice=1、距离=0；"
        "仅一侧为空时 IoU/Dice=0，距离赋 64×64 网格对角线惩罚 sqrt(64²+64²)=90.509668 pixel。"
        "该有限失败惩罚保留在均值内，解释了恒速长期边界误差的明显增加；"
        "Empty mismatch 是先序列内后序列间平均的比例，不能乘 103 当作原始失败窗口数。",
        "",
        "![恒速 WH24 实际失败案例](../../assets/figures/constant-speed-failure-v1.png)",
        "",
        f"WH24，window_start={failure['window_start']}，lead={failure['lead']}，"
        f"原始目标帧索引 {failure['source_target_index']}。左为最后历史派生区域，"
        "中为未来 DERIVED_ANNOTATION，右为 PREDICTION；恒速已预测为空，而目标仍有 65 工作像素²。"
        "该窗口 IoU=0、边界距离=90.509668 pixel。图直接复制源运行的实际算法产物，未重新生成预测。",
        "",
        "源数据：Backova 等（2023），[Zenodo 7660424](https://doi.org/10.5281/zenodo.7660424)，"
        "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。修改包括注释填充、降采样、预测与面板展示；"
        "完整署名见 [datasets/ATTRIBUTION.md](../../datasets/ATTRIBUTION.md)。",
        "",
        "公开机器摘要：[results/baselines-validation-v1.json](results/baselines-validation-v1.json)，"
        "保留源 Git、实现文件 hash、清单/压缩包 hash、实际依赖版本、"
        "运行配置、QC 和输入报告文件 hash。"
        "脚本从逐窗口指标重算两级均值并对照 summary 与失败 JSON，校验源 Git blob hash；"
        "不读取 test 数组、不覆盖源运行。",
        "",
        "复现：先依数据准备文档取得相同 manifest，再从干净工作树执行（输出目录须不存在或为空）：",
        "",
        "```powershell",
        "uv run --locked python scripts/evaluate.py --output "
        "artifacts/experiments/baselines-validation-v1",
        "uv run --locked --extra reports python scripts/report.py",
        "```",
        "",
        "正式报告拒绝 dirty、不完整或来源 hash 不匹配的运行。源运行依赖版本与报告绘图环境分开记录；"
        "曲线仅是本次 validation 的描述性结果，"
        "尚未验证 test、物理单位、独立外部数据或神经预测模型。",
        "",
    ]
    destination.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", type=Path, default=ROOT / "artifacts/experiments/baselines-validation-v1"
    )
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts/processed/manifest.json")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/research/results/baselines-validation-v1.json"
    )
    parser.add_argument(
        "--figure", type=Path, default=ROOT / "assets/figures/baselines-validation-v1.png"
    )
    parser.add_argument(
        "--failure-figure", type=Path, default=ROOT / "assets/figures/constant-speed-failure-v1.png"
    )
    parser.add_argument(
        "--markdown", type=Path, default=ROOT / "docs/research/baselines-validation-v1.md"
    )
    args = parser.parse_args()
    try:
        for destination in (args.output, args.figure, args.failure_figure, args.markdown):
            require(
                not destination.resolve().is_relative_to(args.run.resolve()),
                "Output must not overwrite source run",
            )
        report = checked_report(args.run, args.manifest)
        failure = next(
            f
            for f in report["failure_cases"]
            if f["baseline"] == "constant_normal_speed" and f["sequence_id"] == "WH24"
        )
        for destination in (args.output, args.figure, args.failure_figure, args.markdown):
            destination.parent.mkdir(parents=True, exist_ok=True)
        plot_report(report, args.figure)
        shutil.copyfile(args.run / failure["png_relpath"], args.failure_figure)
        import matplotlib

        report["report_environment"] = {"matplotlib": matplotlib.__version__}
        report["public_figures_sha256"] = {
            args.figure.name: digest(args.figure),
            args.failure_figure.name: digest(args.failure_figure),
        }
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        write_markdown(report, args.markdown)
    except (OSError, ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as exc:
        print(f"Report rejected: {exc}")
        return 1
    print(json.dumps(report["source_files_sha256"], indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
