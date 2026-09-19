# Methodology

RouteScout is an audit-first PCB routing-cost ranking study.

The supervised label is observed routed wire length from PCBench solutions, transformed with `log1p`. Solution geometry is used only for labels/evaluation, never as a pre-routing feature source.

The final split groups related source families and duplicate/near-duplicate risks before train/validation/test assignment. Model selection is train/validation-only. The test set is opened once after the ranking champion is locked.

The final ranking model is terminal MST length. A CatBoost residual model is kept as a secondary magnitude estimator. A GNN was not admitted because relational tabular signal did not justify added graph complexity.

Phase 8 separates prediction from engineering benefit. Phase 8A validates explicit net-order control. Phase 8B then compares natural, MST-hard-first, and easy-first order under a fixed within-net procedure on a locked set of real PCBench-derived boards.
