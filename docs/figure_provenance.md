# Public figure provenance

Every tracked SVG in `figures/` is derived from frozen release tables under `results/`.
No public figure is illustrative, manually approximated, or reconstructed from memory.

Regenerate all seven figures with:

```bash
pip install -e ".[ml,dev]"
python scripts/regenerate_public_figures.py
```

This is presentation-only: it does not train a model, reopen the held-out test, or rerun the router.

| Figure | Frozen source | Regeneration step |
|---|---|---|
| `phase9_01_validation_to_test.svg` | `results/phase7_validation_to_test_generalization_frozen.csv` | MST validation vs held-out ranking metrics |
| `phase7_heldout_board_spearman_cdf.svg` | `results/phase7_heldout_board_metrics_frozen.csv` | empirical CDF of 154 MST board-wise Spearman values |
| `phase7_heldout_catboost_magnitude.svg` | `results/final_metrics.json` | held-out MST vs CatBoost log-MAE |
| `phase8a_feasibility_gate.svg` | `results/phase8a_runner_summary_frozen.json` | API/order-control pass rates plus board/run counts |
| `phase8b_01_paired_routability.svg` | `results/phase8b_policy_runs_frozen.csv` | paired natural vs MST-hard-first routability |
| `phase8b_02_primary_delta_ci.svg` | `results/phase8b_frozen_result.json` | preregistered primary paired effect and 95% CI |
| `phase8b_03_drc_delta.svg` | `results/phase8b_policy_runs_frozen.csv` | paired whole-board DRC ERROR diagnostic |

The scientific identities of Phase 7, Phase 8A, and Phase 8B are documented in
`docs/reproducibility_frozen.md`. Figure bytes themselves are not scientific locks; the frozen
tables and release identities are.
