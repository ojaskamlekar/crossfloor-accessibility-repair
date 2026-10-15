import random

import pytest

from cfar.interface_scenarios import authored_interface_scenarios,coupled_owner_probe,dense_alternative_probe
from cfar.reuse_lifetime import recognize_reuse_lifetime,solve_reuse_lifetime
from cfar.oracle import exact_oracle
from cfar.synthetic_shaft import make_shaft_instance
from cfar.review_generators import diagnostic_example


def label(result):return result["status"],result["cost"],result["selected"]


@pytest.mark.parametrize("name",sorted(authored_interface_scenarios()))
def test_cell_last_use_matches_full_action_oracle(name):
    instance=authored_interface_scenarios()[name]
    for compressed in(False,True):assert label(solve_reuse_lifetime(instance,compress=compressed))==label(exact_oracle(instance))


@pytest.mark.parametrize("seed",range(20))
def test_last_use_preserves_shared_owner_and_disconnected_bundle_semantics(seed):
    rng=random.Random(seed)
    intervals=[(rng.randrange(3),2,rng.randint(1,2))for _ in range(5)]
    instance=make_shaft_instance(3,intervals,[rng.randint(0,6)for _ in intervals],profiles=2,
        physical=True,asset_groups=[rng.randrange(3)for _ in intervals])
    expected=exact_oracle(instance)
    for compressed in(False,True):assert label(solve_reuse_lifetime(instance,compress=compressed))==label(expected)


def test_continuous_asset_does_not_force_a_whole_building_window():
    n=32
    instance=make_shaft_instance(n,[(i,i,1)for i in range(n)],[1]*n,profiles=1,physical=True)
    recognized=recognize_reuse_lifetime(instance)
    assert recognized["parameters"]["L_unit"]==n+1
    assert recognized["parameters"]["L"]==2
    assert recognized["parameters"]["kappa"]==1
    result=solve_reuse_lifetime(instance)
    # Each unique vertical cut has exactly one available action. All are required.
    assert result["cost"]==str(n)and result["selected"]==[f"A{i:03d}"for i in range(n)]
    assert result["reachability"]["satisfied"]


def test_private_alternatives_expire_names_immediately():
    instance=dense_alternative_probe(32)
    recognized=recognize_reuse_lifetime(instance)
    assert recognized["parameters"]["kappa"]==1
    result=solve_reuse_lifetime(instance)
    assert result["cost"]=="1"and result["selected"]==["A0000"]


def test_disconnected_bundle_and_competing_paid_geometry_are_not_shortened():
    instance=diagnostic_example()
    assert label(solve_reuse_lifetime(instance))==label(exact_oracle(instance))
    recognized=recognize_reuse_lifetime(instance)
    assert recognized["parameters"]["L"]==3 # A's disconnected full support remains three floors.


def test_competing_owners_can_remain_live_together():
    instance=coupled_owner_probe(4)
    recognized=recognize_reuse_lifetime(instance)
    assert recognized["parameters"]["kappa"]>=4
    assert label(solve_reuse_lifetime(instance))==label(exact_oracle(instance))


def test_last_use_cannot_follow_a_different_schedule_without_recomputation():
    with pytest.raises(ValueError,match="INTERFACE_ORDER"):
        solve_reuse_lifetime(diagnostic_example(),event_order="reverse")
