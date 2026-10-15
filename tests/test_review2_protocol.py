import importlib.util
from pathlib import Path

import pytest

from cfar.review_generators import diagnostic_example
from cfar.synthetic_star import rectangle
from cfar.dp_owned_interface import solve_owned_interface


def load_script(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).parents[1]/"scripts"/(name+".py"))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def source_audit():
    return dict(provenance=dict(building="authored-public-protocol-test"),background=[],
        storeys=[dict(global_id=f"f{f}",elevation_m=3*f)for f in range(4)],
        spaces=[dict(global_id=f"{side}{f}",name=f"{side}{f}",storey_id=f"f{f}",eligible=True,
            polygon=rectangle(x,0,x+4,4))for f in range(4)for side,x in(("L",0),("R",4))])


def test_source_subset_is_consecutive_and_horizontal_structure_changes_optimum():
    module=load_script("public_multiroom_controlled");audit=source_audit()
    variants,_=module.select_subset(audit)
    for instance in variants.values():
        assert [f["floor_id"]for f in instance["floors"]]==["f0","f1","f2","f3"]
        assert all(len(f["rooms"])==2 and len(f["adjacency_edges"])==1 for f in instance["floors"])
        originals={s["global_id"]:s["polygon"]for s in audit["spaces"]}
        assert all(r["polygon"]==originals[r["room_id"]]for f in instance["floors"]for r in f["rooms"])
    first=solve_owned_interface(variants["open-horizontal"],compress=False)
    second=solve_owned_interface(variants["restricted-horizontal"],compress=False)
    assert (first["cost"],first["selected"])==("3",["L0","L1","L2"])
    assert (second["cost"],second["selected"])==("3.3",["R0","R1","R2"])
    assert solve_owned_interface(variants["no-right-candidates"],compress=False)["status"]=="infeasible"


def test_unrepresented_intermediate_source_storey_is_not_skipped():
    module=load_script("public_multiroom_controlled");audit=source_audit()
    audit["storeys"]=audit["storeys"][:2];audit["spaces"]=[s for s in audit["spaces"]if s["storey_id"]in{"f0","f1"}]
    audit["storeys"].insert(1,dict(global_id="empty",elevation_m=1.5))
    with pytest.raises(ValueError,match="no consecutive multi-room subset"):module.select_subset(audit)


def test_missing_measurements_remain_null_in_standardized_records():
    module=load_script("review2_benchmarks")
    meta=dict(instance_id="test",instance_sha256="hash",seed=0)
    config=dict(experiment_id="test",budget_seconds=1,max_states=1,max_cut_columns=1)
    row=module.normalized(dict(status="timeout"),meta,"compressed",0,config,{},"revision")
    for key in("objective_cost","best_bound","peak_memory_bytes","peak_retained_states","end_to_end_seconds","certificate_path"):
        assert row[key]is None
    assert row["status"]=="timeout"


def test_structural_owner_and_profile_families_change_the_intended_parameters():
    from cfar.review_generators import generate_instance
    from cfar.interface_recognition import recognize_physical_interface
    for family,target,fixed in(("ownership","h",("p","r","z","L")),("profiles","p",("r","z","L","h")),("support","L",("p","r","z","h"))):
        a=recognize_physical_interface(generate_instance(family,2))["parameters"]
        b=recognize_physical_interface(generate_instance(family,4))["parameters"]
        assert b[target]>a[target]
        assert all(a[k]==b[k]for k in fixed)
