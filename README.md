# Cross-Floor Accessibility Repair

## Manuscript review revision

Independent same-model CP-SAT and whole-action greedy baselines, optional safe
component pruning, a physical two-floor hardness witness, and pinned public IFC
screening are now available. See [review changes and remaining gates](docs/review_action_matrix.md)
and [baseline formulation](docs/revision_optimization_protocol.md).

```bash
python -m pip install -e ".[test,optimization]"
python -m cfar.cli solve-cp-sat YOUR-INPUT.json --time-limit 60 --output runs/cp-review
python -m cfar.cli solve-greedy YOUR-INPUT.json --output runs/greedy-review
python -m cfar.cli solve-owned-interface YOUR-INPUT.json --prune-irrelevant --output runs/pruned-review
```

All commands use fresh output directories. Greedy failure is not infeasibility;
CP-SAT must prove every lexicographic stage before reporting optimal. Public
source subsets have declared hypothetical annotations and do not establish
whole-building renovation or statutory compliance. Originality remains open.

Research repository for minimum-disruption repair of frozen multi-floor layouts.

Status: project development active, with a frozen [working thesis contribution](docs/thesis_contribution.md). Literature originality remains provisional; broad novelty-only searches are parked while demo and controlled evaluation proceed.

## Start with the verified project demo

```powershell
.\.venv\Scripts\python.exe scripts/run_project_demo.py --output runs/project-demo
```

This one command creates a before/after report and the complete repair evidence. On the authored two-profile, two-floor example, satisfied routes increase from 1/4 to 4/4; the solver chooses one cost-three bundle and preserves room adjacency. The exhaustive oracle checks its optimum and the certificate verifier replays it. Open `runs/project-demo/report.md` after the run. Use a new output directory each time.

The implemented [owned-interface solver](docs/owned_interface_solver.md) handles rooted independent physical portal actions with exact collision cells, shared assets and atomic bundles. For compatible input files:

```powershell
.\.venv\Scripts\python.exe -m cfar.cli recognize-interface YOUR-INPUT.json --output runs/recognition
.\.venv\Scripts\python.exe -m cfar.cli solve-owned-interface YOUR-INPUT.json --output runs/repair
```

Its scope excludes candidate doors, dependencies and independent-background metadata corrections. The recognition and solver commands emit manifests; an optimal DP result does not itself include an exhaustive certificate. The demo performs that additional comparison for its small input.

M03 theory audit maps the current jointly feasible multi-profile activation class into existing weighted labelled Steiner forest and compiles the current fixed-geometry kernel into unary/pairwise action constraints. See the [novelty claim registry](docs/novelty_claim_registry.md). These findings validate useful baselines while ruling out unsupported originality claims.

The M01 controlled implementation includes a versioned schema, 18 micro-instances, profile graphs, typed action replay, exhaustive oracle, independent graph/certificate checker, and an initial complexity memo. The five named architectural full-text comparisons are complete; broader novelty and thesis gates remain conditional. See [progress](PROGRESS.md) and [closest-work comparison](docs/closest_work_matrix.md).

## Run locally

Python 3.11 or later is required. No GPU is needed.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m cfar.cli validate examples/micro/01_missing_metadata_link.json
.\.venv\Scripts\python.exe -m cfar.cli solve examples/micro/08_original_not_optimal.json --variant SCFAR --output runs/demo-original
.\.venv\Scripts\python.exe -m cfar.cli verify examples/micro/08_original_not_optimal.json runs/demo-original/certificate.json
.\.venv\Scripts\python.exe -m cfar.cli solve examples/micro/07_strict_vs_relaxed.json --variant RCFAR --topology-weight 1 --output runs/demo-relaxed
```

Use a new empty output directory per run. The CLI creates result, certificate, verification, manifest, and JSONL ledger files; `runs/` is ignored. The oracle guard defaults to at most 20 candidate actions and still takes exponential time. A successful certificate proves the supplied finite model, not all possible building renovations.

`requirements-dev.lock.txt` records the tested Windows/Python 3.12 environment; install it before the editable package for exact versions on a compatible interpreter. The dependency ranges in `pyproject.toml` permit other supported Python versions.

Read [implementation contract](docs/implementation_contract.md), [case catalogue](examples/README.md), [complexity memo](docs/complexity_memo.md), and [master plan](docs/master_plan.md) before extending the model. RCFAR currently supports polygon reshaping with original room IDs; general splits/merges and richer physical construction are deferred explicitly.

The optional exact [partition DP](docs/partition_dp.md) supports multiple profiles and shared-cost action bundles when the activation-only catalogue is jointly geometrically feasible and has no dependencies or exclusions:

```powershell
.\.venv\Scripts\python.exe -m cfar.cli solve-partition examples/micro/06_coupled_portal_actions.json --output runs/demo-partition
```

This command emits a result with repair postchecks and a manifest. Its optimality status follows the documented recurrence; it does not emit an independently checked exhaustive certificate. Component/state limits raise errors rather than returning infeasible. The method is bounded by all retained baseline components, not portal-interface width.

`solve-local-shaft INSTANCE --output runs/NEW-RUN` handles the narrower one-profile full-path class with contiguous original action spans and local geometry/exclusion conflicts. It supports unavailable actions, exact costs and repair replay; it rejects dependencies, nonlocal conflicts and additional profiles. See the [scope, proof and prior-framework audit](docs/local_conflict_interval_candidate.md). Its optimality status follows the recurrence, with a manifest and no exhaustive certificate. The latest full regression checkpoint passed 616 tests; the new project demo has a separately passing targeted integration check. Literature originality remains provisional.

The [nested-profile boundary audit](docs/priority_profile_boundary.md) gives a tight bounded-support argument and a transfer of existing hardness for unrestricted declared exclusions. These are scoped theory witnesses, not a new multi-profile solver or a hardness claim for physically realized collision graphs.

## Research-paper reproduction

See [paper/REPRODUCE.md](paper/REPRODUCE.md) for the frozen benchmark, licensed IFC adaptation and manifest-derived manuscript. Building-derived cases use documented hypothetical assumptions; literature priority remains unconfirmed.


## Second review revision

The merged first review is followed by the 17-item revision in
[review2_workflow.md](docs/review2_workflow.md), including the exact claim boundary,
named proof procedures, stronger heuristic, structural/boundary/ablation protocols,
and a multi-room IFC-derived controlled experiment. Use the pinned campaign and
its audited evidence, not dirty pilot output. Original access annotations remain
hypothetical; broad novelty priority and independent theorem review remain open.
