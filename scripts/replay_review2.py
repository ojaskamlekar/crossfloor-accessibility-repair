"""Standalone deduplicated feasibility replay and eligible optimum certificates.

Every worker already replayed its returned solution. This extra pass verifies
each distinct input/selection once and re-enumerates eligible oracle optima.
It never claims that feasibility alone certifies an optimum.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from cfar.actions import apply_actions
from cfar.certificates import make_certificate,verify_certificate
from cfar.independent_selection import check_selection
from cfar.io import fingerprint,write_json
from cfar.objective import action_cost
from cfar.obligations import verify_obligations


def replay(roots,output):
    if output.exists()and any(output.iterdir()):raise ValueError("fresh replay output required")
    if subprocess.check_output(["git","status","--porcelain"],text=True).strip():raise ValueError("commit checker before evidence")
    verified={};optima={};references=0;sources={}
    for root in roots:
        protocol=json.loads((root/"protocol.json").read_text())
        if protocol["dirty"]or protocol["smoke"]:raise ValueError("nonpublication evidence")
        for folder in sorted(p for p in root.iterdir()if p.is_dir()):
            path=folder/"input.json"
            if not path.exists():continue
            instance=json.loads(path.read_text());digest=fingerprint(instance)
            for sample in sorted(folder.glob("*.json")):
                if sample.name in{"input.json","description.json"}or sample.name.endswith(".manifest.json"):continue
                metadata=sample.with_suffix(".manifest.json")
                if not metadata.exists():continue
                m=json.loads(metadata.read_text());raw=json.loads(sample.read_text())
                if m["git_dirty"]or m["input_fingerprint"]!=digest or m["git_revision"]!=protocol["code_commit"]:raise ValueError("replay source provenance mismatch")
                sources[str(sample.resolve())]=hashlib.sha256(sample.read_bytes()).hexdigest()
                result=raw.get("result",{});selected=result.get("selected")
                if selected is None:selected=result.get("incumbent",{}).get("selected")
                if selected is not None:
                    references+=1;key=(digest,tuple(selected))
                    if key not in verified:
                        repair=apply_actions(instance,selected)
                        routes=verify_obligations(repair["instance"],repair["active"])
                        independent=check_selection(instance,selected)
                        if not(routes["satisfied"]and independent["obligations_satisfied"]and independent["paid_footprints_compatible"]and all(r["preserved"]for r in repair["adjacency"].values())):
                            raise ValueError("independent/full replay failed: "+str(sample))
                        verified[key]=dict(instance_sha256=digest,selected=selected,cost=str(action_cost(instance,selected)),
                            topology_preserved=True,routes_satisfied=True,independent=independent,source=str(sample.resolve()))
                    reported=result.get("cost")or result.get("incumbent",{}).get("cost")
                    if reported!=verified[key]["cost"]:raise ValueError("reported price mismatch")
                if sample.name.startswith("oracle-")and digest not in optima:
                    certificate=make_certificate(instance,result)
                    verification=verify_certificate(instance,certificate,max_actions=8)
                    if not verification["valid"]:raise ValueError("oracle certificate failed")
                    write_json(output/"optimality-certificates"/(digest+".json"),certificate)
                    optima[digest]=dict(source=str(sample.resolve()),verification=verification,action_count=len(instance["actions"]))
    report=dict(solution_measurement_references=references,distinct_selections=len(verified),
        optimum_certificates=len(optima),selected_set_replays=list(verified.values()),optimality_checks=optima,
        checker_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_hashes=sources,
        scope="independent rectangle/graph checks plus shared-kernel full replay; eligible <=8-action optima re-enumerated; long chains use separate analytical cut certificates")
    write_json(output/"replay-summary.json",report)
    print(json.dumps({k:report[k]for k in("solution_measurement_references","distinct_selections","optimum_certificates")}))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--evidence",nargs="+",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args();replay(a.evidence,a.output)
