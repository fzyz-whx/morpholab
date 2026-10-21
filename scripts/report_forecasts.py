"""Publish checked forecast evaluation results without rerunning predictions or selecting seeds."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path, PureWindowsPath

import numpy as np
from morpholab_ml.evaluation.learned import (
    SCHEMA,
    VARIANTS,
    read_json,
    require,
    summarize_forecasts,
    verify_source,
)
from morpholab_ml.evaluation.runner import (
    PROJECT_ROOT,
    file_sha256,
    git_dirty,
    git_sha,
    safe_path,
    save_json,
)


def public_value(value):
    if isinstance(value, dict):
        return {key: public_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [public_value(item) for item in value]
    if isinstance(value, str):
        require(
            not Path(value).is_absolute() and not PureWindowsPath(value).is_absolute(),
            "Absolute local path in public report",
        )
    return value


def checked_report(directory: Path):
    report = read_json(directory / "report.json")
    run = read_json(directory / "run.json")
    require(
        report["schema_version"] == SCHEMA and report["status"] == run["status"] == "complete",
        "Evaluation is incomplete",
    )
    require(
        report["git_dirty"] is False
        and run["git_dirty"] is False
        and report["git_sha"] == run["git_sha"]
        and report["split"] == run["split"]
        and report["source_manifest_sha256"] == run["source_manifest_sha256"],
        "Evaluation provenance mismatch",
    )
    verify_source(report["git_sha"], report["implementation_file_sha256"])
    for relative, expected in report["source_files_sha256"].items():
        require(
            file_sha256(safe_path(directory, relative)) == expected,
            f"Evaluation source hash mismatch: {relative}",
        )
    rows = read_json(directory / "metrics.json")
    require(all(row["project_split"] == report["split"] for row in rows), "Mixed evaluation splits")
    rebuilt = summarize_forecasts(rows)
    require(rebuilt["per_sequence"] == report["per_sequence"], "Per-sequence report mismatch")
    require(
        [r for r in rebuilt["summary"] if r["window_protocol"] == "main_L4"] == report["summary"],
        "Main summary mismatch",
    )
    require(
        [r for r in rebuilt["summary"] if r["window_protocol"] == "matched_origin8"]
        == report["input_sensitivity"],
        "Sensitivity summary mismatch",
    )
    require(
        len(report["summary"]) == 6 * 24 and len(report["input_sensitivity"]) == 6 * 3 * 24,
        "Incomplete variant, lead or input-length coverage",
    )
    require(
        {(r["variant"], r["seed"]) for r in report["runs"]}
        == {(v, s) for v in VARIANTS for s in (17, 29, 43)}
        and len(report["runs"]) == 12,
        "Incomplete training matrix in public report",
    )
    for failure in report["failure_cases"]:
        require(
            file_sha256(safe_path(directory, failure["png_relpath"])) == failure["png_sha256"],
            "Failure image hash mismatch",
        )
        require(failure["metrics"] in rows, "Failure metrics absent from evaluated rows")
    report["source_evaluation_files_sha256"] = {
        name: file_sha256(directory / name) for name in ("run.json", "report.json")
    }
    return public_value(report)


def curve_figure(report, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    variants = (*VARIANTS, "persistence", "constant_normal_speed")
    colors = ("#2a678c", "#197763", "#975c9c", "#ba7b27", "#525963", "#a94836")
    with plt.rc_context({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False}):
        fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout="constrained")
        for axis, metric, label in zip(
            axes,
            ("iou", "mean_boundary_distance", "area_mae"),
            ("IoU ↑", "Mean boundary distance (64-grid px) ↓", "Area MAE (64-grid px²) ↓"),
            strict=True,
        ):
            for variant, color in zip(variants, colors, strict=True):
                rows = sorted(
                    (r for r in report["summary"] if r["variant"] == variant),
                    key=lambda r: r["lead"],
                )
                leads = np.array([r["lead"] for r in rows])
                means = np.array([r["metrics_mean"][metric] for r in rows])
                axis.plot(
                    leads,
                    means,
                    color=color,
                    label=variant,
                    linestyle="-" if variant in VARIANTS else "--",
                    linewidth=1.6,
                )
                if variant in VARIANTS:
                    sd = np.array([r["metrics_std"][metric] for r in rows])
                    axis.fill_between(leads, means - sd, means + sd, color=color, alpha=0.1)
            axis.set(
                xlabel="Prediction lead (source frames)",
                ylabel=label,
                xlim=(1, 24),
                xticks=[1, 4, 8, 12, 16, 20, 24],
            )
            axis.grid(alpha=0.15)
        axes[0].legend(frameon=False, fontsize=7)
        n = report["summary"][0]["n_sequences"]
        fig.suptitle(
            f"{report['split'].upper()} · source-sequence proxies n={n} · "
            "mean ± sample SD across 3 training seeds\n"
            "Equal sequence weights; derived annotation targets; baseline SD undefined",
            fontsize=11,
        )
        fig.savefig(destination, dpi=170)
        plt.close(fig)


def sensitivity_figure(report, destination):
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(8, 4), layout="constrained")
    for variant in (*VARIANTS, "persistence", "constant_normal_speed"):
        rows = sorted(
            (r for r in report["input_sensitivity"] if r["variant"] == variant and r["lead"] == 24),
            key=lambda r: r["observations"],
        )
        means = [r["metrics_mean"]["iou"] for r in rows]
        deviation = [r["metrics_std"]["iou"] or 0 for r in rows]
        axis.errorbar(
            [r["observations"] for r in rows],
            means,
            yerr=deviation,
            label=variant,
            marker="o",
            capsize=3,
            linestyle="-" if variant in VARIANTS else "--",
        )
    axis.set(
        xlabel="Historical frames L",
        ylabel="Lead-24 IoU ↑",
        xticks=[2, 4, 8],
        title=f"{report['split'].upper()} sensitivity · shared QC block and origin=start+8",
    )
    axis.legend(frameon=False, fontsize=8, ncol=2)
    axis.grid(alpha=0.15)
    fig.savefig(destination, dpi=170)
    plt.close(fig)


def formatted(row, metric):
    mean, sd = row["metrics_mean"][metric], row["metrics_std"][metric]
    return f"{mean:.4f} ± {sd:.4f}" if sd is not None else f"{mean:.4f} (det.)"


def markdown(report, curves, sensitivity, failures):
    index = {(r["variant"], r["lead"]): r for r in report["summary"]}
    representative = report["summary"][0]
    lines = [
        f"# 形态预测结果 v1 · {report['split']}",
        "",
        "果蝇胚胎 in vivo 激光创面闭合，历史轮廓条件下的派生形态预测。"
        "以下为真实运行结果，所有 seed 均保留，未按 test 成绩选择模型或调整参数。",
        "",
        f"评价 Git：`{report['git_sha']}`；`git_dirty=false`。"
        f"数据清单 SHA256：`{report['source_manifest_sha256']}`。",
        f"有效源序列代理 n={representative['n_sequences']}，"
        f"每个方法/seed 主评价窗口={representative['n_windows']}。",
        "",
        "采用 morpholab-split-v1；官方划分未知（null）。源序列仅作为生物独立性的代理分组；"
        "样本数少，同动物/批次关系未知，不能把序列×seed当作独立生物实验。"
        "任务不包含原始灰度图自动分割或未来显微纹理生成，目标 DERIVED_ANNOTATION "
        "由原始薄轮廓填充、QC、降采样得到，不能冒称原始人工区域真值。",
        "",
        "主评价 L4/H24/stride12，所有方法使用相同最长 H24 连续有效窗口。"
        "先序列内平均窗口，再序列等权得到每 seed 分数，"
        "最后对 seed17/29/43 求均值与样本标准差（ddof=1）。"
        "SD仅描述训练随机种子变化，不是生物学置信区间；未作显著性检验。"
        "重叠窗口不能作为独立实验。确定性基线仅计算一次，n_seeds=0、n_realizations=1，SD=null。",
        "",
        f"![主评价曲线](../../assets/figures/{curves.name})",
        "",
        "| Variant | Lead | n sequences | IoU ↑ | Dice ↑ | Mean boundary distance ↓ "
        "| HD95 ↓ | Area MAE ↓ | Empty mismatch |",
        "|---|---:|---:|---|---|---|---|---|---|",
    ]
    for row in report["summary"]:
        if row["is_endpoint"]:
            values = " | ".join(
                formatted(row, m)
                for m in (
                    "iou",
                    "dice",
                    "mean_boundary_distance",
                    "hausdorff95",
                    "area_mae",
                    "empty_boundary_mismatch",
                )
            )
            lines.append(f"| {row['variant']} | {row['lead']} | {row['n_sequences']} | {values} |")
    lines += [
        "",
        "距离单位为64×64工作网格pixel，面积为pixel²；物理标尺与逐帧实际时间未知。"
        "仅一侧边界为空时，IoU/Dice=0，边界距离保留网格对角线90.509668的有限惩罚；"
        "两侧均为空时IoU/Dice=1、距离=0。Empty mismatch也是序列等权后再跨seed统计的比例，"
        "不能直接乘窗口总数解释为失败次数。",
        "",
        "下列差值直接从主表均值得到（前者减后者）；正负方向随指标而异，"
        "不作显著性或总体优越结论，不通过挑seed改变符号。",
        "",
        "| Comparison | Lead | ΔIoU ↑ | ΔArea MAE ↓ | ΔMean boundary distance ↓ |",
        "|---|---:|---:|---:|---:|",
    ]
    for first, second in (
        ("nca", "persistence"),
        ("nca", "convgru"),
        ("nca_regularized", "nca"),
        ("nca_h1", "nca"),
    ):
        for lead in (4, 12, 24):
            delta = [
                index[(first, lead)]["metrics_mean"][m] - index[(second, lead)]["metrics_mean"][m]
                for m in ("iou", "area_mae", "mean_boundary_distance")
            ]
            lines.append(
                f"| {first} − {second} | {lead} | "
                + " | ".join(f"{value:+.6f}" for value in delta)
                + " |"
            )
    lines += [
        "",
        "NCA正则消融只改变更新平方惩罚权重0→0.001；H1消融保持同NCA、samplingH12，"
        "仅监督前缀H1。H1与H12的600步预算相同，但实际计算量与训练用时不相等，"
        "不能据此主张严格等算力下的因果收益。以下所有数值均按实际结果呈现，不预设正则或多步监督有效。",
        "",
        "| Variant | Seed | Parameters | Best validation step | Actual training seconds "
        "| CUDA peak allocated bytes | Model Git | Best SHA256 |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for run in report["runs"]:
        lines.append(
            f"| {run['variant']} | {run['seed']} | {run['parameter_count']} | "
            f"{run['best_step']} | {run['elapsed_seconds']:.3f} | "
            f"{run['cuda_peak_allocated_bytes']} | `{run['git_sha']}` | `{run['best_sha256']}` |"
        )
    lines += [
        "",
        "显存为PyTorch实际峰值allocated，非整机总内存或FLOPs；CPU峰值内存未测则为null。"
        "每100步用validation多步监督损失选best，test不参与选模。",
        "",
        f"![输入长度敏感性](../../assets/figures/{sensitivity.name})",
        "",
        "L2/4/8敏感性采用共同8帧候选块，forecast origin固定为start+8；"
        "每个L取该块末L帧，未来目标与QC窗口严格相同。它与主评价L4的起点协议不同，"
        "不能把敏感性L4直接当作主表L4重复实验。",
        "",
        "失败案例按所有seed、所有主评价窗口中的最小lead24 IoU自动选取；没有挑好seed。"
        "面板包括真实未来显微影像OBSERVED（仅显示时映射对比度）、历史/未来DERIVED_ANNOTATION"
        "与MODEL_PREDICTION。确定性方法的面板标PREDICTION。",
        "",
    ]
    for path, failure in failures:
        row = failure["metrics"]
        lines += [
            f"![{failure['variant']}最差窗口](../../assets/figures/{path.name})",
            "",
            f"{row['variant']} seed={row['seed']}，{row['sequence_id']}，"
            f"origin={row['forecast_origin']}，源目标帧={row['source_target_index']}，"
            f"IoU={row['iou']:.6f}；empty_boundary_mismatch={row['empty_boundary_mismatch']}。",
            "",
        ]
    lines += [
        "源数据：Backova等（2023），[Zenodo 7660424](https://doi.org/10.5281/zenodo.7660424)，"
        "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。修改包括区域派生、"
        "降采样、预测和可视化；完整署名见[ATTRIBUTION](../../datasets/ATTRIBUTION.md)。",
        "",
        "本报告不声称原作者官方split复现、临床适用、真实干预因果效应或论文新颖性。"
        "是否支持NCA、正则与多步监督，应结合完整负结果、失败案例、少量序列与预算限制判断。",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "docs/research/results/forecast-test-v1.json"
    )
    parser.add_argument(
        "--markdown", type=Path, default=PROJECT_ROOT / "docs/research/forecast-results-v1.md"
    )
    parser.add_argument("--figures", type=Path, default=PROJECT_ROOT / "assets/figures")
    args = parser.parse_args()
    report = checked_report(args.evaluation)
    implementation_sha = git_sha()
    implementation_hash = {"scripts/report_forecasts.py": file_sha256(Path(__file__))}
    verify_source(implementation_sha, implementation_hash)
    import matplotlib

    report["report_implementation"] = {
        "git_sha": implementation_sha,
        "git_dirty": git_dirty(),
        "implementation_file_sha256": implementation_hash,
        "matplotlib": matplotlib.__version__,
    }
    require(
        report["split"] == "test" or args.output.name != "forecast-test-v1.json",
        "Validation output must use an explicit non-test public filename",
    )
    for destination in (args.output, args.markdown, args.figures):
        require(
            not destination.resolve().is_relative_to(args.evaluation.resolve()),
            "Cannot overwrite evaluation source",
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.figures.mkdir(parents=True, exist_ok=True)
    curves = args.figures / f"forecast-{report['split']}-curves-v1.png"
    sensitivity = args.figures / f"forecast-{report['split']}-input-sensitivity-v1.png"
    curve_figure(report, curves)
    sensitivity_figure(report, sensitivity)
    failures = []
    for failure in report["failure_cases"]:
        destination = (
            args.figures / f"forecast-{report['split']}-failure-{failure['variant']}-v1.png"
        )
        shutil.copyfile(safe_path(args.evaluation, failure["png_relpath"]), destination)
        failure["public_png_relpath"] = f"assets/figures/{destination.name}"
        failures.append((destination, failure))
    report["published_figures_sha256"] = {
        path.name: file_sha256(path) for path in (curves, sensitivity, *(p for p, _ in failures))
    }
    save_json(args.output, report)
    args.markdown.write_text(markdown(report, curves, sensitivity, failures), encoding="utf-8")
    print(json.dumps(report["source_evaluation_files_sha256"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
