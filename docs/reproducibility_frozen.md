# Reproducibility and Evidence Chain

## Public release

This repository is RouteScout **v1.0.0**, the first public stable release. Internal `rc` identifiers
used during repository cleanup were pre-release engineering checkpoints and are not part of the
public version history.

## Canonical dataset

PCBench commit:

`dec3be75cbdef74787625f9043c7391cd473bb64`

## What this repository is for

This Git repository is the clean public source and review surface. It intentionally does not carry
the large immutable phase-release ZIPs.

The frozen release archives are retained as release evidence and are identified here by SHA-256:

| Phase | Canonical release SHA-256 |
|---|---|
| 1 | `deaceccba1ef51d46a44cb86724b41b4aea1598dfda07d89557dfa1898f47a50` |
| 2 | `8832a4e3b195f6aeaf4d549e7834558403d9de82ba49274a723132aded4c2708` |
| 3 | `bc407020c70a2a832199706ce2ad3df25a3e8c4ac26d4cadab7a9d31f8513eb9` |
| 4 | `a50233c41991751b09327c8b976721703eaace6d19d144943d58cb633395689a` |
| 5 | `6affb71a9b9a350ae0ff8f7c545b3a587428b1562c30e258ddc82a1d83a618b9` |
| 6 | `f92b69092db96464d83c1f017b4644904333a67abee11f12489c868211b015c4` |
| 7 | `e32432bd7c02c9defe1a40e42f94120ddc07e21a901b1f7d1b8dd166f815fac6` |
| 8A | `cc65bec2fae71ea480f75df04c0d9fa254b9efa6df100f45910d906cea267790` |
| 8B | `da003a672157b5a44e1c6f6cb17802e9735ab02626b0a0b6c89f235300b0b24b` |

## Critical scientific locks

- Phase 4 test manifest:
  `af021fa4777427195a561bc3ecd4c2978943c0d4298d420638518c9fca3b6ffd`
- Phase 7 truth-free prediction lock:
  `ac512b5f6ce45f45e87d0d36525ab7ada78a042cc6bbe7bc99a3e0b9ce468018`
- Phase 8B protocol:
  `7cbea24ee392b7b29ebf134beb3744135f7038b9a25ee5f2b0898e99bdc8f732`
- Phase 8B exact intervention manifest:
  `692357feeaba88bdf978337acd3579233b69cac0edca9172cff1b1b67287fb54`
- Phase 8B frozen runner:
  `ad97beed8ca97ee98f50634724269987c260c2f764642c75c71b4722a15344a0`

## Python version for the public repository

The public package and CI are validated on Python **3.11 and 3.12**. A macOS system Python such as
3.9 is intentionally rejected by `pyproject.toml`.

Use:

```bash
bash scripts/setup_dev_env.sh
```

for the normal development/test environment.

## Three practical reproduction levels

### 1. Verify the public frozen results

No PCB build is required:

```bash
python scripts/static_check.py
python scripts/verify_frozen_results.py
pytest
```

### 2. Re-run the lightweight model notebook

Install the optional ML dependencies:

```bash
pip install -e ".[ml,dev]"
```

The full Phase 1–7 research path is preserved in the frozen report and source notebook. The held-out
test is already consumed and must not be used for a new tuning decision.

### 3. Replay the frozen router evidence

`notebooks/02_router_mechanism.ipynb` and `notebooks/03_real_board_intervention.ipynb` start from compact frozen run tables included under `results/`. This reproduces the public analysis/visuals without a KiCad rebuild.

All tracked public SVG figures are regenerated from frozen `results/` sources by `scripts/regenerate_public_figures.py`; see `docs/figure_provenance.md` for the exact mapping.

### 4. Re-run the router intervention

Phase 8 uses a pinned Linux KiCad/PCBWorld toolchain. The full build is intentionally separate from
the normal package environment and is best run on a Linux/Colab CPU runtime.

The macOS/VS Code validation before publication is a **repository validation**, not a requirement to
rebuild KiCad or rerun the scientific intervention.

## Dependency files

- `environment/phase8_conda.yml` pins the compiled Phase 8 toolchain.
- `environment/phase8_pip.txt` pins the Phase 8 Python layer.
- `environment/phase1_7_requirements.txt` is a convenience list for the historical notebook; the
  canonical scientific identity comes from the frozen artifacts and hashes, not from claiming that
  an old Colab environment can be reconstructed byte-for-byte today.

## Rule

Do not use the consumed Phase 7 held-out test or Phase 8 outcomes for post-hoc model selection.
A future model change needs a new external evaluation source or a newly frozen benchmark.
