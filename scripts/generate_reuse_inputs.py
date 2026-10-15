"""Declared structural/semantic cases and reused public controls, not new BIMs."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from cfar.actions import apply_actions
from cfar.independent_selection import check_selection
from cfar.interface_scenarios import dense_alternative_probe,coupled_owner_probe
from cfar.io import fingerprint,write_json
from cfar.objective import action_cost
from cfar.review_generators import diagnostic_example
from cfar.synthetic_shaft import make_shaft_instance


def build(output,public):
    if output.exists()and any(output.iterdir()):raise ValueError("fresh output required")
    rows=[]
    for floors in(4,8,16,32):
        edges=floors-1
        instance=make_shaft_instance(edges,[(i,i,1)for i in range(edges)],[1]*edges,profiles=1,physical=True)
        instance.update(building_id=f"authored-reuse-chain-{floors}",description="Authored adjacent-floor activations of one proposed shaft; analytical unique-cut optimum, not public BIM evidence.")
        selected=[a["action_id"]for a in instance["actions"]]
        replay=apply_actions(instance,selected);independent=check_selection(instance,selected)
        if not independent["obligations_satisfied"]or not independent["paid_footprints_compatible"]:raise ValueError("invalid analytic witness")
        name=f"chain-{floors}"
        write_json(output/(name+".json"),instance)
        rows.append(dict(instance_id=name,input_sha256=fingerprint(instance),optimum_cost=str(action_cost(instance,selected)),
            selected=selected,proof="Every consecutive floor cut has exactly one supplying original action; reaching the last floor requires all of them. Full action set replayed feasible.",
            topology_preserved=all(r["preserved"]for r in replay["adjacency"].values()),independent=independent))
    for name,instance in(("dense-32",dense_alternative_probe(32)),("coupled-4",coupled_owner_probe(4)),("diagnostic",diagnostic_example())):
        write_json(output/(name+".json"),instance)
    for path in sorted(public.glob("*.json")):
        write_json(output/path.name,json.loads(path.read_text()))
    # Keep sidecar outside input directory so the runner cannot treat it as input.
    write_json(output.parent/(output.name+"-analytic-witnesses.json"),rows)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);parser.add_argument("--public",type=Path,required=True)
    args=parser.parse_args();build(args.output,args.public)
