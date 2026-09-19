# RouteScout v1.0.0

First public stable release.

## What this release contains

- leakage-safe pre-routing per-net cost study on PCBench;
- frozen grouped train/validation/test split;
- MST-only final ranking rule;
- held-out ranking evaluation;
- secondary CatBoost magnitude model;
- documented no-GNN decision after relational-signal checks;
- KiCad/PCBWorld order-control feasibility gate;
- real-board Phase 8B intervention;
- compact frozen replay tables and executed HTML evidence;
- clean Python package, tests, static checks, CI, and reproducibility notes.

## Frozen public results

- held-out mean board Spearman: `0.9240179379260456`;
- held-out Top-5 cost capture: `0.9809876927692095`;
- held-out MST log-MAE: `0.1416659671644751`;
- held-out CatBoost log-MAE: `0.12468492613978792`;
- Phase 8B decision: `NO_CLEAR_ROUTABILITY_BENEFIT`.

## Scope of the claim

RouteScout does **not** claim a new router or a proven routing improvement. Its main empirical result
is that a very simple pre-routing geometric signal can rank observed routing cost strongly, while a
subsequent real-router intervention does not establish that hard-first ordering improves routability.

## Development history

The research began in Google Colab and went through roughly two weeks of exploratory work and
failed/retained hypotheses. The public repository was then refactored and re-validated in a clean
Python 3.11 VS Code environment on macOS.

AI-assisted development tools were used for implementation, debugging, review, refactoring, and
documentation. Frozen scientific decisions are guarded by checksums and regression tests.

## License

RouteScout code in this repository is released under the MIT License. Third-party datasets,
repositories, and dependencies remain subject to their own licenses.
