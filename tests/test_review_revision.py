from copy import deepcopy
import json

import pytest

from cfar.actions import apply_actions
from cfar.dp_owned_interface import solve_owned_interface
from cfar.errors import ValidationError
from cfar.greedy import improve_greedy, solve_greedy
from cfar.independent_selection import check_selection
from cfar.interface_scenarios import authored_interface_scenarios
from cfar.interface_recognition import recognize_physical_interface
from cfar.oracle import exact_oracle
from cfar.review_generators import diagnostic_example,generate_instance,FAMILY_EFFECTS


def objective(result):return result["status"],result["cost"],result["selected"]


def test_hand_derived_complete_example():
    instance=diagnostic_example()
    # Every p1 path to L1 uses a or b; without A no upper floor is reachable
    # from L0 except via D, which costs three already. A alone misses R2.
    # A+B attains cost two; the cheaper A+C collides on the paid R1 patch.
    oracle=exact_oracle(instance)
    assert (oracle["cost"],oracle["selected"])==("2",["A","B"])
    for compress in (False,True):assert objective(solve_owned_interface(instance,compress=compress))==objective(oracle)
    assert check_selection(instance,["A","B"])["obligations_satisfied"]
    assert not check_selection(instance,["A"])["obligations_satisfied"]
    assert not check_selection(instance,["A","C"])["paid_footprints_compatible"]
    with pytest.raises(ValidationError,match="PORTAL_COLLISION"):apply_actions(instance,["A","C"])


def test_bounded_exchange_repairs_known_greedy_dead_end():
    instance=authored_interface_scenarios()["shared_asset"]
    instance["actions"]=[a for a in instance["actions"]if a["action_id"]!="A003"]
    assert solve_greedy(instance)["status"]=="heuristic_failed"
    improved=improve_greedy(instance,exchange_budget=256)
    assert (improved["cost"],improved["selected"])==("5",["A000","A001"])
    assert improved["statistics"]["exchange_candidates"]<=256
    assert improve_greedy(instance,exchange_budget=0)["status"]=="heuristic_failed"


@pytest.mark.parametrize("name",sorted(authored_interface_scenarios()))
def test_improvement_does_not_worsen_valid_greedy(name):
    instance=authored_interface_scenarios()[name];original=solve_greedy(instance);actual=improve_greedy(instance)
    if original["status"]=="feasible":
        from decimal import Decimal
        assert actual["status"]=="feasible"and Decimal(actual["cost"])<=Decimal(original["cost"])
    if actual["selected"]is not None:assert check_selection(instance,actual["selected"])["paid_footprints_compatible"]


@pytest.mark.parametrize("family",sorted(FAMILY_EFFECTS))
def test_structural_probes_are_recognized_and_replayable(family):
    instance=generate_instance(family,3,seed=7)
    recognized=recognize_physical_interface(instance)
    assert recognized["parameters"]["p"]>=1
    result=solve_owned_interface(instance,compress=False)
    assert result["status"]=="optimal"
    independent=check_selection(instance,result["selected"])
    assert independent["paid_footprints_compatible"]and independent["obligations_satisfied"]


@pytest.mark.parametrize("mode",["permutation","rename","translate","scale_geometry","scale_costs"])
def test_metamorphic_transformations_preserve_known_optimum(mode):
    instance=diagnostic_example(); expected=exact_oracle(instance)
    # JSON inputs have value semantics; break generator-internal list aliases
    # so a patch appearing as landing and footprint is transformed once each.
    changed=json.loads(json.dumps(instance))
    if mode=="permutation":
        for key in ("actions","connections","floors","profiles","obligations"):changed[key].reverse()
    elif mode=="rename":
        for a in changed["actions"]:a["action_id"]="renamed-"+a["action_id"]
    elif mode=="scale_costs":
        for a in changed["actions"]:a["cost"]*=7
    else:
        scale=2 if mode=="scale_geometry"else 1;shift=0 if scale==2 else 32
        def ring(points):return [[scale*x+shift,scale*y-shift]for x,y in points]
        for f in changed["floors"]:
            f["elevation_m"]*=scale;f["boundary"]=ring(f["boundary"])
            for r in f["rooms"]:r["polygon"]=ring(r["polygon"])
            for field in ("obstacles","reserved_portal_zones"):f[field]=[ring(x)for x in f[field]]
        for c in changed["connections"]:
            g=c["geometry"]
            for field in ("width_m","rise_m","run_m"):
                if field in g:g[field]*=scale
            if "opening"in g:g["opening"]=ring(g["opening"])
            for field in ("landings","footprints"):
                for record in g.get(field,[]):record["polygon"]=ring(record["polygon"])
        for p in changed["profiles"]:
            p["min_width_m"]*=scale;p["clearance_m"]*=scale
    result=solve_owned_interface(changed,compress=False)
    assert result["status"]==expected["status"]
    assert result["selected"]==(["renamed-"+x for x in expected["selected"]]if mode=="rename"else expected["selected"])
    assert result["cost"]==("14"if mode=="scale_costs"else expected["cost"])


def test_dominated_candidate_cannot_improve_and_feasible_candidate_cannot_worsen():
    instance=diagnostic_example();first=exact_oracle(instance)
    extra=deepcopy(instance["actions"][0]);extra.update(action_id="dominated",cost=9)
    instance["actions"].append(extra)
    assert objective(exact_oracle(instance))==objective(first)
    extra["cost"]=0
    from decimal import Decimal
    assert Decimal(exact_oracle(instance)["cost"])<=Decimal(first["cost"])


def test_vacuous_demands_have_zero_cost_empty_repair():
    instance=diagnostic_example();instance["obligations"]=[]
    for compress in (False,True):
        result=solve_owned_interface(instance,compress=compress)
        assert (result["status"],result["cost"],result["selected"])==("optimal","0",[])


def test_reverse_valid_schedule_matches_exact_oracle():
    instance=diagnostic_example()
    for compress in (False,True):
        assert objective(solve_owned_interface(instance,compress=compress,event_order="reverse"))==objective(exact_oracle(instance))


def test_geometry_memoization_is_optional_and_does_not_hide_input_changes():
    from cfar.geometry import geometry_memoization,clear_geometry_caches
    instance=diagnostic_example();clear_geometry_caches()
    with geometry_memoization(True):cached=solve_owned_interface(instance)
    with geometry_memoization(False):uncached=solve_owned_interface(instance)
    assert objective(cached)==objective(uncached)
    changed=deepcopy(instance);changed["floors"][0]["rooms"][0]["polygon"][1][0]=3
    with pytest.raises(ValidationError):solve_owned_interface(changed)


def test_cap_exception_preserves_measurements_without_claiming_an_optimum():
    with pytest.raises(ValidationError)as info:solve_owned_interface(diagnostic_example(),max_cut_columns=1)
    assert info.value.code=="INTERFACE_CUT_LIMIT"
    assert info.value.statistics["max_cut_columns"]>1
    assert info.value.timings["optimization_seconds"]>=0


def test_naive_purchase_vertex_invents_a_connection():
    from cfar.validation import baseline_active
    instance=diagnostic_example();catalog={c["connection_id"]:c for c in instance["connections"]}
    graph={r["room_id"]:set()for f in instance["floors"]for r in f["rooms"]}
    for cid,ps in baseline_active(instance).items():
        if "p1"in ps:
            c=catalog[cid];graph[c["u"]].add(c["v"]);graph[c["v"]].add(c["u"])
    graph["purchase:A"]=set()
    for effect in instance["actions"][0]["effects"]:
        c=catalog[effect["connection_id"]]
        for v in (c["u"],c["v"]):graph[v].add("purchase:A");graph["purchase:A"].add(v)
    seen={"L0"};stack=["L0"]
    while stack:
        for v in graph[stack.pop()]-seen:seen.add(v);stack.append(v)
    assert "R2"in seen # false positive of the explicitly defined simplification
    assert not check_selection(instance,["A"])["obligations_satisfied"]


def test_cp_sat_cost_bound_and_vacuous_zero_cost_gap():
    pytest.importorskip("ortools")
    from cfar.cp_sat import solve_cp_sat
    result=solve_cp_sat(diagnostic_example())
    assert result["best_bound"]=="2"and result["relative_cost_gap"]==0
    instance=diagnostic_example();instance["obligations"]=[]
    result=solve_cp_sat(instance)
    assert result["selected"]==[]and result["best_bound"]=="0"and result["relative_cost_gap"]==0


def test_cost_stage_optimality_does_not_claim_completed_identifier_optimization(monkeypatch):
    pytest.importorskip("ortools")
    import cfar.cp_sat as module
    ticks=iter([0.,0.,0.,0.,100.])
    monkeypatch.setattr(module,"perf_counter",lambda:next(ticks,100.))
    result=module.solve_cp_sat(diagnostic_example())
    assert result["status"]=="limit_exceeded"and result["selected"]is None
    assert result["incumbent"]["cost"]=="2"
    assert result["best_bound"]=="2"and result["relative_cost_gap"]==0


def test_bound_telemetry_handles_subnormal_price_denominators():
    from cfar.cp_sat import reported_cost_bound
    assert reported_cost_bound(1.,10**324)==0.
    assert reported_cost_bound(float("inf"),1)is None
