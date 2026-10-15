**1. Settle the precise novelty claim — highest priority**

The current contribution combines frozen layouts, profile-specific reachability, atomic purchases, shared physical assets, collision constraints, and an exact interface algorithm. The paper must identify precisely what is new in that combination.

Actions:

- Create a table comparing the proposed problem with labelled connectivity, simultaneous network design, connectivity with conflicts/resources, and bounded-width connectivity algorithms.
- For each comparison, state the input, purchase semantics, compatibility constraints, demand structure, decomposition parameter, and optimization objective.
- Separate three questions: whether prior work can *express* this problem; whether it provides an applicable *algorithm*; and whether it provides the *same parameter dependence*.
- Identify a specific proposition that the paper contributes: a semantics-preserving reduction, an exact interface construction, an improved parameter dependence under stated assumptions, or a previously untreated combination with a rigorous algorithm.
- Explicitly acknowledge any known general formulation that can encode the problem.

**Completion criterion:** Replace “Originality remains unresolved” with a precise, supported boundary. For example: “Existing formulation X can express these instances, but its stated algorithm depends on parameter Y; our construction establishes bound Z under assumptions A–D.” Use this only if the comparison actually supports it.

Do not remove the uncertainty sentence merely to sound confident.

**2. Make the algorithmic advance understandable through one complete example**

The motivating example should demonstrate the difficulty solved by the algorithm, not only that installing a lift improves accessibility.

Construct one small instance containing:

- At least two floors and multiple rooms.
- Two mobility profiles.
- One purchased action with disconnected graph effects.
- Two compatible uses of the same physical asset.
- A competing asset that overlaps its footprint.
- A paid footprint that remains occupied even when its associated graph effect is not used in the connectivity witness.

Show, in a single figure or figure sequence:

1. Original rooms and access edges.
2. Candidate actions, costs, owners, and footprints.
3. An incorrect repair produced by an explicitly defined simplification.
4. The correct optimum.
5. The interface state that preserves the missing information.

**Completion criterion:** A reader can explain why ordinary edge selection or a naïve purchase vertex gives the wrong answer without reading the appendix.

**3. Strengthen the theorem presentation and proof package**

The proof is central to the paper. It needs to be inspectable rather than merely present.

Required edits:

- Put every parameter in one notation table: definition, how it is measured, whether it is supplied or computed, and which part of the runtime it controls.
- State the recognized input class before the theorem.
- Explain whether the decomposition is given, constructed, or recognized, and include its construction cost.
- Distinguish the mathematical algorithm from the implementation’s state/cut-column/time caps.
- Give pseudocode for recognition, event construction, state transitions, representative reduction, and final reconstruction.
- State the invariant maintained after every event.
- Explain why forgetting a floor or a completed action–asset unit loses no information.
- State what happens to paid but unused effects, costs, and footprints.
- Explain infeasible instances and empty/trivial demand sets.
- Explain why the cost/count/identifier tie-break remains valid under state dominance and representative reduction.
- Include the bit complexity of costs and labels, not only the number of states.

Suggested pseudocode names:

```text
RecognizeStrictInstance
BuildOwnedCollisionCells
BuildActionAssetUnits
BuildFloorEventSchedule
IntroduceAction
UpdatePhysicalOccupancy
UpdateProfileWitnesses
ForgetCompletedInterface
ReduceRepresentativePartitions
ReconstructAndReplayRepair
```

**Completion criterion:** Each operation in the pseudocode points to a lemma establishing its safety or completeness. Every term in the runtime bound has an explicit derivation.

**4. Make the hardness boundary earn its place**

The two-floor hardness result should explain why the restrictions enabling the algorithm are meaningful.

Required edits:

- State the decision version and threshold explicitly.
- Name the source problem and describe the reduction.
- Specify which parameters remain constant and which grow.
- Explain the geometric realization of the constructed instance, if geometry is part of the hardness claim.
- Show that the construction preserves the relevant costs and feasibility.
- State exactly what the result rules out.

**Completion criterion:** The theorem supports a clear sentence such as “Two floors alone do not imply tractability because …” without suggesting a stronger parameterized lower bound than is proved.

**5. Add meaningful multi-room building experiments — highest empirical priority**

The present public-source cases use one room per selected floor and therefore have empty within-floor adjacency. They cannot demonstrate preservation of a nontrivial floor topology.

New experiments should include:

- Connected subsets containing multiple rooms on each selected floor.
- Multiple destinations distributed across those rooms.
- At least some instances spanning three or more floors.
- Existing horizontal circulation that materially affects which vertical intervention is optimal.
- Cases where a locally attractive intervention becomes inferior after considering another floor or profile.
- Existing obstacles retained consistently.

Use the largest admissible subsets supported by the current kernel. Report exclusions rather than silently simplifying incompatible geometry.

For every instance, report:

```text
source_building_id
selected_storeys
room_count_by_storey
original_adjacency_edge_count
baseline_access_edge_count_by_profile
required_destination_count_by_profile
candidate_action_count
physical_asset_count
collision_cell_count
measured_interface_parameters
solver_status
objective_cost
objective_action_count
topology_preservation_result
route_replay_result
```

**Completion criterion:** At least one main-text case has nonempty room adjacency on multiple floors, and the selected intervention depends on that horizontal access structure.

More room polygons alone are insufficient if they never affect optimization.

**6. Separate building diversity from variant count**

Do not pool authored cases, historical Duplex adaptations, and new variants as though each were an independent building.

Required reporting:

- Number of distinct source models.
- Number of distinct selected building subsets.
- Number of variants per subset.
- Number of feasible/infeasible/unsupported instances.
- Whether any historical and new cases share the same geometry.
- Which results are full-building experiments versus extracted-subset experiments.

**Completion criterion:** Every headline experimental count has an unambiguous denominator.

**7. Build a benchmark that exercises the proposed interface**

Current dense-catalogue cases retain approximately constant state counts. They demonstrate catalogue processing, but they do not strongly test the connectivity algorithm.

Create separate generator families:

| Family | Vary | Hold approximately fixed | Purpose |
|---|---|---|---|
| Catalogue size | Number of actions | Interface width | Separate recognition cost from interface complexity |
| Connectivity width | Live boundary terminals | Profiles, owner choices | Test partition-state growth |
| Profile count | Mobility profiles | Geometry and action catalogue | Test profile coupling |
| Ownership | Owners competing per cell | Connectivity width | Test physical-state growth |
| Action support | Floors/interfaces touched | Local room complexity | Test long-lived coupling |
| Compression | Distinct compatible partitions | Occupancy signature | Test representative reduction |

Suggested generator interface:

```python
generate_instance(family, size, seed, settings) -> StrictRepairInstance
```

**Completion criterion:** Each family has a documented expected structural effect, measured parameters, multiple seeds where applicable, and a size range reaching a meaningful computational boundary.

**8. Design a genuine compression stress test**

The manuscript reports little compression benefit and cases where compressed mode hits a cap while full mode completes. This is valuable evidence, but it leaves compression’s practical role unestablished.

Actions:

- Generate many connectivity partitions sharing the same occupancy signature and selected boundary sets—the grouping within which the implementation actually reduces rows.
- Measure generated rows, retained rows, reduction time, memory, and total solver time.
- Compare compressed and full modes under identical computational budgets.
- Include both favorable and unfavorable families.
- Explain the cut-column cap and its practical implications.

**Completion criterion:** Either demonstrate a reproducible regime where compression materially helps, or position compression primarily as part of the theoretical guarantee and describe the implementation accordingly.

Do not search for one favorable instance and present it as general evidence.

**9. Improve the CP-SAT comparison**

CP-SAT already solves all recognized authored inputs. The paper needs to establish where the specialized algorithm adds value.

For all common-class instances:

- Use identical feasibility semantics, objective, hardware, and time budgets.
- Replay every returned solution.
- Compare completion rate, time, memory, and objective quality at termination.
- Distinguish optimal, feasible incumbent, infeasible, unsupported, timeout, and internal cap.
- Report results by measured interface width, not just action count.
- Give timeout results a visible place in plots and tables.
- Publish the CP-SAT formulation in sufficient detail to reproduce every constraint.

For interrupted optimization, report the incumbent and solver bound when available. Define the gap convention explicitly, including zero-cost cases.

**Completion criterion:** The results explain when a practitioner should choose the DP, CP-SAT, or neither. A finding that CP-SAT is generally faster is acceptable; it changes the practical claim, not the correctness of the theorem.

**10. Strengthen the greedy baseline**

The current greedy heuristic is valid, but a reviewer may question whether it is unnecessarily weak.

Implement a documented improvement such as:

```python
greedy_repair(instance)
prune_redundant_actions(instance, selected_actions)
local_exchange_repair(instance, selected_actions, exchange_budget)
```

Requirements:

- Evaluate whole actions with full physical semantics.
- Remove redundant selected actions after construction.
- Consider bounded exchanges where computationally affordable.
- Treat failure as heuristic failure, never as proof of infeasibility.
- Report the construction and improvement budgets.

**Completion criterion:** Exact optimization is compared with a reasonable inexpensive alternative, rather than only the simplest greedy implementation.

**11. Address geometry recognition as a bottleneck**

Table V indicates that recognition accounts for much of the measured runtime.

Measure separately:

```text
input_validation_time
geometry_recognition_time
collision_cell_construction_time
unit_and_event_construction_time
optimization_time
solution_reconstruction_time
independent_replay_time
```

Also:

- Count footprint intersection tests and generated cells.
- Explain numerical tolerances and coordinate units.
- Test boundary contact, nearly coincident edges, tiny cells, and invalid input.
- Consider spatial indexing and reuse of immutable recognition results across solver runs.
- Keep end-to-end timing as the main comparison.
- If cached runs are reported, label them separately.

**Completion criterion:** Readers can tell whether an improvement affects geometry processing, optimization, or both.

**12. Improve experimental reliability**

Three repetitions support descriptive timings, but weakly support small runtime differences.

Actions:

- Run the improved experiment suite from a pinned revision.
- Use a declared repetition policy; for example, five fresh-process runs for routine cases and three for expensive cases.
- Keep the seed list fixed before reviewing results.
- Record hardware, package versions, solver settings, and memory limits.
- Show variability rather than only medians.
- Avoid claims based on tiny differences at very short runtimes.
- State whether startup and imports are included.
- Do not silently discard failed runs.

**Completion criterion:** Every plotted value can be traced to raw records, and every exclusion follows a documented rule.

**13. Add focused ablations**

Keep the existing altered-semantics controls, but distinguish them from algorithm ablations.

Useful algorithm ablations include:

- Safe component pruning on/off.
- Representative reduction on/off.
- State dominance on/off, if feasible.
- Alternative valid event/unit processing orders.
- Cached versus uncached recognition, reported separately.

For each, measure correctness agreement, states, memory, and time.

**Completion criterion:** The paper explains which algorithm components provide practical benefit and which mainly establish correctness or theoretical bounds.

**14. Make correctness checks less dependent on shared machinery**

The paper acknowledges shared schema/geometry code across methods.

Add:

- Hand-derived cases with known optima.
- Boundary cases for the geometry contract.
- Independent verification of selected paid footprints and owner compatibility where practical.
- Metamorphic tests: renaming IDs, translating geometry, permuting input order, and consistently rescaling units/costs should have predictable effects.
- Tests where adding a dominated action cannot improve the optimum.
- Tests where adding a feasible candidate cannot worsen the optimum under an otherwise unchanged model.

**Completion criterion:** Agreement among solvers is supplemented by checks capable of detecting shared implementation errors.

**15. Standardize the evidence package**

Use an explicit results schema, such as:

```text
experiment_id
instance_id
source_building_id
instance_sha256
code_commit
generator_family
seed
solver
solver_configuration
repeat_index
status
objective_cost
objective_action_count
selected_action_ids
best_bound
end_to_end_seconds
recognition_seconds
optimization_seconds
replay_seconds
peak_memory_bytes
peak_raw_states
peak_retained_states
certificate_path
```

Use null for unavailable measurements; never substitute zero.

Suggested commands:

```text
validate_instances
run_benchmarks
replay_certificates
summarize_results
render_paper_figures
```

**Completion criterion:** One documented workflow regenerates the submitted tables and figures from raw records. Provide a smaller smoke-test workflow as well.

**16. Rewrite the paper around the strongest result**

Recommended narrative:

1. Practical repair problem and one concrete example.
2. Why physical purchases cannot safely be reduced to ordinary edge choices.
3. Precise problem definition.
4. Exact algorithm and tractability boundary.
5. Experiments testing correctness, computational behavior, and building applicability.
6. Limitations.

Required writing changes:

- Define “topology-preserving” operationally at first use.
- Separate room adjacency from traversable access.
- Explain “shared physical asset” before introducing ownership notation.
- Distinguish intervention candidates supplied to the solver from candidates automatically generated.
- State what “exact” means.
- Avoid suggesting that profile reachability establishes statutory accessibility.
- Preserve qualifications, but consolidate repeated defensive sentences into a focused limitations discussion.
- Remove submission-oriented language such as “acceptance” or comments about IEEE formatting from the scientific narrative.

**Completion criterion:** The introduction ends with three precise contributions, each supported by a theorem, experiment, or artifact later in the paper.


**17. Use these final gates before calling it submission-ready**

Your friend should provide:

- **Novelty gate:** A precise claim supported by a closest-work comparison.
- **Theory gate:** Complete pseudocode, parameter definitions, proof dependencies, and a correctly scoped hardness result.
- **Empirical gate:** Meaningful multi-room, multi-floor cases; interface-scaling experiments; fair solver comparisons.
- **Artifact gate:** Reproducible results and replayable solutions.
- **Presentation gate:** A concise story that makes the problem, difficulty, contribution, and evidence easy to find.