# Reproduce the research-paper package

Run from this repository in PowerShell. No push/submission is performed. Python 3.12 and `requirements-dev.lock.txt` reproduce the tested solver environment; install the editable project as in README. `requirements-ifc.lock.txt` adds the optional IFC reader. Set temporary storage to ignored runs/tmp before package installation/testing.

```powershell
New-Item -ItemType Directory -Force runs/tmp | Out-Null
$env:TEMP = (Resolve-Path runs/tmp).Path
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -m pytest -q
```

Retrieve the architectural IFC from the explicit CC BY 4.0 source below into ignored data/external/duplex. The audit enforces SHA256 b347a2c8aa8fff6db896a4417a9c50c22ac0ccd7c5cfc22b99b8d29336c606ed. Do not commit raw IFC, derived cases, runs, PDFs or compiler caches.

```powershell
New-Item -ItemType Directory -Force data/external/duplex | Out-Null
Invoke-WebRequest 'https://media.githubusercontent.com/media/buildingsmart-community/Community-Sample-Test-Files/main/IFC%202.3.0.1%20(IFC%202x3)/Duplex%20Apartment/Duplex_A_20110907.ifc' -OutFile data/external/duplex/Duplex_A_20110907.ifc
.\.venv\Scripts\python.exe scripts/audit_duplex_ifc.py data/external/duplex/Duplex_A_20110907.ifc --output runs/reproduce-audit
.\.venv\Scripts\python.exe scripts/run_controlled_benchmark.py --output runs/reproduce-controlled
.\.venv\Scripts\python.exe scripts/run_controlled_benchmark.py --building-audit runs/reproduce-audit --output runs/reproduce-building
.\.venv\Scripts\python.exe scripts/run_project_demo.py --output runs/reproduce-demo
.\.venv\Scripts\python.exe scripts/build_paper.py --controlled runs/reproduce-controlled --building runs/reproduce-building --demo runs/reproduce-demo --output runs/reproduce-paper
```

Use new empty output paths. Benchmark collection rejects a dirty checkout; keep tracked/untracked source unchanged throughout a collection run. The final protocol is 37 authored cases and eight building-derived controlled variants, three samples per recognition/DP, one oracle per eligible small case, 60-second process timeout, 100,000 raw states and 65,536 cut columns. Input/source/recipe hashes and clean revision, environment, seeds, errors/limits and exact original action IDs remain in manifests. Summary regeneration and paper building audit fingerprints/statuses; successful modes/oracle must agree. Tiny cell, state-cap and unsupported controls are not infeasibility.

Compile the generated standalone manuscript with a working LaTeX installation (`pdflatex` twice) or `tectonic -X compile --untrusted --keep-logs --outdir runs/reproduce-paper runs/reproduce-paper/manuscript.tex`. The generated source includes its tables and figure; it needs no external project files. Tectonic 0.17.0 was used for delivery, with a workspace cache via TECTONIC_CACHE_DIR. Compiler/runtime binaries are not repository dependencies or committed assets. Its cache must be writable; first compile downloads the TeX bundle. The conventional pdflatex alternative needs geometry, AMS, booktabs, array and url packages. The built-in compiler may also preview this standalone source when the desktop sandbox is configured.

## Source/license and scientific limits

Attribution: BSI (2020) "Duplex Apartment Test Files," buildingSMART International. Source: https://github.com/buildingsmart-community/Community-Sample-Test-Files/tree/main/IFC%202.3.0.1%20(IFC%202x3)/Duplex%20Apartment . Folder README and repository LICENSE explicitly state CC BY 4.0. Changes: world-coordinate mesh projection; room-subset extraction preserving GlobalIds/rings; conservative existing-stair obstacle envelopes; explicitly hypothetical experimental floor domains, reservations, profiles, templates/permissions and abstract costs. No actual construction price, validated building repair, restoration reference or code-compliance claim is supported. Eight variants belong to one source building.

The theorem is a scoped project argument; independent review and literature priority remain unconfirmed. Rank-based weighted partitions and the generic weighted logic machinery are attributed, not claimed as inventions. The explicit baseline exponent comparison is not a universal lower bound or guaranteed superiority. Oracle/certificate graph replay is separate but geometry/schema are shared. Larger analytical cases are not exhaustively certified. Read docs/controlled_evaluation_protocol.md, docs/duplex_controlled_protocol.md and docs/consolidated_theory.md for exact assumptions and source locators.

The review ZIP includes manuscript PDF/source, authored source recipes, solver source, protocols, license/provenance record and generated evidence/tables. Raw source IFC and compiler/cache binaries are omitted; the download/hash procedure above regenerates the adaptation. Generated evidence stays outside Git. No package is submitted or uploaded publicly by this workflow.

## Offline review archive

To restore the clean Git source from the included bundle, run git clone repository.bundle review-source, then run the commands above in review-source. The archive also preserves runs/final-controlled, runs/final-building, runs/final-audit, runs/final-demo and runs/final-paper-delivery for direct inspection; copy these into the checkout if desired. Use fresh reproduce-* paths when rerunning. Experimental manifests record revision 9735c0f; subsequent source commits only refine the manuscript and completion records.


## Review extension

Install requirements-review.lock.txt in a fresh Python 3.12 environment, then
`pip install -e ".[test,optimization]"`. The historical recipe remains useful;
`run_controlled_benchmark.py --optimizers` adds corrected-import CP-SAT and greedy
measurements. An external-only checkpoint can use `run_optimization_benchmark.py
--methods cp-sat greedy`. Interrupted external checkpoints can be completed with
`resume_optimization_benchmark.py` only when the frozen runner SHA256, revision,
inputs and existing manifests match; old measurements are never silently replaced.

For public sources follow docs/public_building_review_protocol.md, then run
`replay_optimization_certificates.py --evidence RUN` before the updated IEEE
builder. Every admitted portal pair must be consecutive in the original source
storey order; no intermediate floor is skipped. See paper/ieee/README.md for the
new required builder arguments and actual pdfLaTeX reproduction path.


## Cell-local refinement and final rendering

The 1,317-record campaign is pinned at 11e285f. The additional ten-input,
207-record cell-local checkpoint is pinned at 8dc7a73, using
`generate_reuse_inputs.py` and `review2_reuse.json`. It reuses the same three
Molio controls and adds no source building or selected subset. Subsequent
changes add reporting, CLI dispatch and a defensive CP-SAT telemetry conversion;
they do not alter the measured successful cost/flow constraints or lifetime DP.

Generate the denominator audit from historical Duplex inputs, the twelve
consecutive-storey public inputs, the new multi-room inputs and their copied
checkpoint variants. Rebuild `summarize_review2.py` with `--denominators` and
`summarize_reuse.py` with the saved analytical cut witnesses. Run the standalone
`replay_review2.py` on all five suites to recheck unique selected sets and
re-enumerate eligible small optimum certificates. The current IEEE builder
requires BOTH `--review2 <audited-summary>` and `--reuse <audited-reuse-summary>`;
older argument-only historical builds require their historical source revision.
It rejects stale fixed abstract counts rather than silently dropping a section.

CLI: `python -m cfar.cli solve-reuse-lifetime input.json --output runs/local-NEW`.
Improved heuristic: `python -m cfar.cli solve-greedy input.json --improve
--exchange-budget 256 --output runs/greedy-NEW` (one shell line).

The review archive includes a Git history bundle preserving the actually executed
local commit IDs. GitHub API publication recreates commit metadata; published
Git trees are verified identical and commit trailers retain original IDs. Fetch
the included history bundle for original measurement revisions, or compare tree
and source fingerprints rather than assuming recreated commit SHAs are identical.
Geometry metamorphic checks use cases separated from the absolute EPS threshold;
no scale invariance at that threshold is asserted. Complete-unit and cell-local
proofs remain project arguments, not independently endorsed novelty claims.
