# MorphoLab

[中文](README.md) · [Results](docs/research/results.md) · [Model card](docs/research/model-card.md)

MorphoLab is a local research workbench for wound-closure morphodynamics in real microscopy time series. It connects an audited public dataset, traceable preprocessing, classical baselines, independently implemented neural cellular automata and ConvGRU models, and persistent prediction jobs.

The domain is **in vivo Drosophila embryonic laser wounds**. The task is **historical annotation-conditioned shape forecasting**, not automatic microscopy segmentation, future texture generation, clinical wound assessment, or biological intervention discovery. Computational grid states are not biological cells.

![Actual forecasting workbench](assets/screenshots/studio-prediction-v1.png)

Real Edge screenshot, WH01: four observed annotation frames condition a 24-step shape forecast. The grayscale background is always an actual OBSERVED frame. Solid pale contours are source ANNOTATION; dashed amber contours are PREDICTION. Source: Backová et al., [Zenodo 7660424](https://doi.org/10.5281/zenodo.7660424), CC BY 4.0. Display contrast, magnification and overlays are modified. [Attribution](datasets/ATTRIBUTION.md).

## Evidence, including negative results

The downloaded archive contains 62 video/annotation pairs and 7,229 frames, despite the publisher's description of 61 sequences. Labels are thin contours. Strict QC and documented filling/resampling produce 7,183 valid 64×64 shape targets; invalid frames retain their original indices.

The original split mapping was unavailable. Our explicit independent protocol has 45 training, 12 validation and 5 held-out source sequences. Source sequences are proxies for independence: animal and batch identities are unknown. Physical pixel scale and verified frame times remain null.

Four learned configurations each use seeds 17/29/43 and 600 training steps. Checkpoints are selected by validation loss, never test scores. Five held-out sequence proxies provide 25 common L4/H24 windows per method/seed. Metrics average windows within sequences, then weight sequences equally before averaging training seeds.

| Method | Lead-24 IoU | Lead-24 mean boundary distance (working-grid px) |
|---|---:|---:|
| Persistence | 0.3368 | 3.624 |
| Constant normal speed | 0.2691 | 31.782 |
| ConvGRU | 0.4128 ± 0.0446 | 6.242 |
| NCA | 0.4596 ± 0.0269 | 4.152 |
| Regularized NCA | 0.4612 ± 0.0255 | 4.153 |
| One-step-supervised NCA | 0.3376 ± 0.0264 | 3.106 |

± denotes **sample SD across three training seeds**, not biological confidence. NCA has higher long-horizon IoU, but its boundary distance remains worse than persistence, and ConvGRU has higher lead-12 IoU. The update penalty offers little improvement. One-step supervision is weaker under this step budget, with less actual compute than multi-step training. Premature empty predictions remain important failures. No statistical significance, overall architectural superiority, cross-domain generalization or novelty is claimed.

![Actual held-out results](assets/figures/forecast-test-curves-v1.png)

[Full report and per-sequence JSON](docs/research/forecast-results-v1.md) · [Limitations](docs/research/limitations.md) · [Frozen model/budget ADR](docs/project/decisions/ADR-0002-local-models-and-training-budget.md).

## Run locally

Use Python 3.12, uv, Node 24 and pnpm 11. No commercial model API or key is required.

```sh
git clone https://github.com/fzyz-whx/morpholab.git
cd morpholab
uv sync --locked --python 3.12 --extra cpu
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
uv run --locked --extra cpu python scripts/download_data.py
uv run --locked --extra cpu python scripts/audit_data.py
uv run --locked --extra cpu python scripts/prepare_data.py
uv run --locked --extra cpu python scripts/download_models.py
uv run --locked --extra cpu python scripts/serve.py
```

Open `http://127.0.0.1:8765`. The server provides the built frontend, API and a separate CPU inference worker. The original dataset is about 199 MB; the pinned 12-checkpoint release bundle is about 2.7 MB. Both downloads are verified. Jobs persist in ignored `artifacts/app`. All network binding is local by default.

Data browsing and classical baselines also work without Torch: omit the CPU extra and model download. Learned models then report unavailable runtime. The model downloader checks the archive and every member SHA256, rejects unsafe extraction, and never overwrites differing existing training runs. Source microscopy is excluded from the weight bundle and Git.

## Reproduce experiments

```sh
uv sync --locked --extra cpu --extra reports
uv run --locked --extra cpu python scripts/train_matrix.py --device cpu --output artifacts/training/forecast-v1
uv run --locked --extra cpu python scripts/evaluate_models.py --split test --device cpu --output artifacts/experiments/reproduction
uv run --locked --extra cpu --extra reports python scripts/report_forecasts.py --evaluation artifacts/experiments/reproduction
```

Use a new matrix directory if pretrained weights already occupy the default path, and pass that directory with `--matrix-root` when evaluating. Formal runs require clean source and full Git history. CUDA is optional and mutually exclusive with the CPU extra. Test must be chosen explicitly; validation is the evaluation CLI default. See [acceptance evidence](docs/development/acceptance.md) for actual execution boundaries.

The NCA uses fixed local identity/Sobel/Laplacian perception, a shared learned update and 16 state channels (14,622 parameters). The 18,417-parameter ConvGRU receives the same history summary. The models never receive future targets during rollout.

![Implemented architecture](assets/diagrams/forecast-architecture.svg)

## Software boundaries

The workbench supports real sequence playback, original labels, persistent prediction/cancellation/history, prediction and FP/FN overlays, lead metrics, area/boundary curves and frozen research reports. FastAPI and a SQLAlchemy/SQLite queue are separate from numerical model code. React/TypeScript provides the scientific canvas. Synthetic tests, real HTTP checks and real browser tests are reported separately.

Virtual control is deliberately excluded from this release under the master plan's conditional M6 gate. Observational training data does not identify intervention responses. Input-length sensitivity is numerical reliability evidence, not a causal control experiment. [Decision](docs/project/decisions/ADR-0004-defer-control-and-bound-reliability.md).

Source code is [MIT](LICENSE); released weights are CC BY 4.0 with source-data attribution. Third-party datasets retain their own terms. Cite the dataset authors separately from the software [CITATION.cff](CITATION.cff). [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md).
