"""Pinned fresh-process comparisons with explicit statuses and null measurements.

Imports/startup excluded from function timings, included in reported process RSS.
All methods receive the same post-READY hard wall budget. CP-SAT's internal
budget includes its recognition; parent termination is authoritative for all.
"""
import argparse
import json
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import resource
import selectors
import subprocess
import sys
from time import perf_counter

from cfar.io import fingerprint,manifest,write_json


def worker(source,method,target,budget,cap,columns,seed):
    from cfar.cp_sat import solve_cp_sat
    from ortools.sat.python import cp_model  # equal declared import boundary
    from cfar.dp_owned_interface import solve_owned_interface
    from cfar.greedy import solve_greedy,improve_greedy
    from cfar.oracle import exact_oracle
    from cfar.errors import ValidationError
    from cfar.actions import apply_actions
    from cfar.obligations import verify_obligations
    from cfar.independent_selection import check_selection
    from cfar.reuse_lifetime import solve_reuse_lifetime
    from cfar.geometry import geometry_memoization,clear_geometry_caches,geometry_cache_info
    instance=json.loads(Path(source).read_text())
    clear_geometry_caches()
    cache_context=geometry_memoization(method!="uncached");cache_context.__enter__()
    print("READY",flush=True);started=perf_counter()
    try:
        if method=="reuse":result=solve_reuse_lifetime(instance,max_states=int(cap),max_cut_columns=int(columns))
        elif method=="cp-sat":result=solve_cp_sat(instance,time_limit=float(budget),seed=int(seed))
        elif method=="greedy":result=solve_greedy(instance)
        elif method=="greedy-exchange":result=improve_greedy(instance,exchange_budget=256)
        elif method=="oracle":result=exact_oracle(instance,max_actions=8)
        else:result=solve_owned_interface(instance,compress=method!="full",prune_irrelevant=method=="pruned",
                                         max_states=int(cap),max_cut_columns=int(columns),event_order="reverse"if method=="reverse"else"canonical")
        elapsed=perf_counter()-started
        status=result["status"]
        if status=="limit_exceeded":status="feasible_incumbent"if result.get("incumbent")else"timeout"
        if status=="model_invalid":status="internal_error"
        payload=dict(status=status,result=result,end_to_end_seconds=elapsed)
        chosen=result.get("selected")
        if chosen is None:chosen=result.get("incumbent",{}).get("selected")
        if chosen is not None:
            replay_started=perf_counter()
            repair=apply_actions(instance,chosen)
            full=verify_obligations(repair["instance"],repair["active"])
            independent=check_selection(instance,chosen)
            if not(full["satisfied"]and independent["obligations_satisfied"]and independent["paid_footprints_compatible"]):
                raise RuntimeError("independent selected-set replay disagreement")
            payload["certificate"]=dict(selected_action_ids=chosen,input_sha256=fingerprint(instance),
                route_replay_result=True,topology_preservation_result=all(r["preserved"]for r in repair["adjacency"].values()),
                independent=independent,scope="feasibility replay; does not certify optimizer optimality")
            payload["independent_replay_seconds"]=perf_counter()-replay_started
    except ValidationError as error:
        status="internal_cap"if error.code in{"INTERFACE_STATE_LIMIT","INTERFACE_CUT_LIMIT","ORACLE_ACTION_LIMIT"}else"unsupported"
        payload=dict(status=status,error_code=error.code,error=str(error),end_to_end_seconds=perf_counter()-started,
            result=dict(statistics=getattr(error,"statistics",{}),timings=getattr(error,"timings",{})))
    except Exception as error:
        payload=dict(status="internal_error",error=repr(error),end_to_end_seconds=perf_counter()-started)
    payload["peak_memory_bytes"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1024 if platform.system()=="Linux"else 1)
    payload["geometry_cache_info"]=geometry_cache_info()
    cache_context.__exit__(None,None,None)
    write_json(target,payload)


def describe(instance):
    from cfar.interface_recognition import recognize_physical_interface
    from cfar.errors import ValidationError
    from cfar.validation import baseline_active
    pids=[p["profile_id"]for p in instance["profiles"]];baseline=baseline_active(instance)
    row=dict(selected_storeys=[f["floor_id"]for f in instance["floors"]],
        room_count_by_storey={f["floor_id"]:len(f["rooms"])for f in instance["floors"]},
        original_adjacency_edge_count=sum(len(f["adjacency_edges"])for f in instance["floors"]),
        baseline_access_edge_count_by_profile={p:sum(p in ps for ps in baseline.values())for p in pids},
        required_destination_count_by_profile={p:len({o["target"]for o in instance["obligations"]if o["profile_id"]==p})for p in pids},
        candidate_action_count=len(instance["actions"]),physical_asset_count=len({c["geometry"]["asset_id"]for c in instance["connections"]if c["kind"]!="door"}))
    try:
        recognized=recognize_physical_interface(instance)
        row.update(measured_interface_parameters=recognized["parameters"],collision_cell_count=len(recognized["cells"]),
            recognition_counters=recognized["counters"])
    except ValidationError as error:row.update(recognition_error=error.code,measured_interface_parameters=None,collision_cell_count=None)
    return row


def normalized(payload,meta,method,repeat,config,description,commit):
    result=payload.get("result",{});timings=result.get("timings",{});stats=result.get("statistics",{})
    incumbent=result.get("incumbent",{})
    selected=result.get("selected")
    if selected is None:selected=incumbent.get("selected")
    certificate=payload.get("certificate",{})
    return dict(experiment_id=config["experiment_id"],instance_id=meta["instance_id"],
        source_building_id=meta.get("source_building_id"),subset_id=meta.get("subset_id"),variant_id=meta.get("variant_id"),
        generator_family=meta.get("family"),size=meta.get("size"),seed=meta.get("seed",0),
        instance_sha256=meta["instance_sha256"],code_commit=commit,solver=method,
        solver_configuration=dict(post_ready_wall_budget_seconds=config["budget_seconds"],max_states=config["max_states"],
            max_cut_columns=config["max_cut_columns"],cp_sat_workers=1,exchange_candidates=256),
        repeat_index=repeat,status=payload["status"],objective_cost=result.get("cost")or incumbent.get("cost"),
        objective_action_count=len(selected)if selected is not None else None,selected_action_ids=selected,
        solver_parameters=result.get("parameters"),
        best_bound=result.get("best_bound"),bound_precision=result.get("bound_precision"),relative_cost_gap=result.get("relative_cost_gap"),
        end_to_end_seconds=payload.get("end_to_end_seconds"),recognition_seconds=timings.get("recognition_seconds"),
        optimization_seconds=timings.get("optimization_seconds"),replay_seconds=timings.get("replay_seconds"),
        phase_timings=timings or None,independent_replay_seconds=payload.get("independent_replay_seconds"),
        peak_memory_bytes=payload.get("peak_memory_bytes"),peak_raw_states=stats.get("peak_raw_states"),
        geometry_cache_info=payload.get("geometry_cache_info"),geometry_memoization_enabled=method!="uncached",
        peak_retained_states=stats.get("peak_retained_states"),solver_statistics=stats or None,
        certificate_path=meta["instance_id"]+f"/{method}-{repeat}.json"if certificate else None,
        topology_preservation_result=certificate.get("topology_preservation_result"),route_replay_result=certificate.get("route_replay_result"),
        error_code=payload.get("error_code"),instance_description=description)


def run(config_path,output,instances=None,smoke=False):
    config=json.loads(config_path.read_text());output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise ValueError("fresh output required")
    dirty=subprocess.check_output(["git","status","--porcelain"],text=True).strip()
    if dirty and not smoke:raise ValueError("commit before evidence; --smoke is explicitly nonpublication testing")
    commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    write_json(output/"protocol.json",dict(config,code_commit=commit,dirty=bool(dirty),smoke=smoke,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        environment=dict(python=sys.version,platform=platform.platform(),cpu_count=os.cpu_count(),
            cpu_model=next((line.split(':',1)[1].strip()for line in Path('/proc/cpuinfo').read_text().splitlines()if line.startswith('model name')),None)if Path('/proc/cpuinfo').exists()else platform.processor(),
            affinity_cpus=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else None,
            cgroup_memory_max=Path('/sys/fs/cgroup/memory.max').read_text().strip()if Path('/sys/fs/cgroup/memory.max').exists()else None,
            address_space_rlimit=list(resource.getrlimit(resource.RLIMIT_AS)),
            packages={p:importlib.metadata.version(p)for p in('ortools','shapely','numpy','jsonschema')}),
        timing="imports/startup excluded; post-READY hard timeout; end-to-end includes recognition and optimizer replay; extra independent replay separate",
        memory="fresh-process peak RSS including imports; no added address-space limit; inherited cgroup/rlimit recorded",seed_policy="fixed before results; cost perturbation of fixed geometry; identical deterministic solver seed per instance"))
    recipes=[]
    if instances:
        for p in sorted(instances.glob("*.json")):
            inst=json.loads(p.read_text());name=p.stem
            authored=inst["building_id"].startswith("authored-")
            recipes.append((dict(instance_id=name,source_building_id=None if authored else name.split('-')[0],
                subset_id=None if authored else inst["building_id"],family="authored-external"if authored else None,variant_id=name,seed=0),inst))
    else:
        from cfar.review_generators import generate_instance,diagnostic_example
        recipes.append((dict(instance_id="diagnostic",family="diagnostic",size=3,seed=0),diagnostic_example()))
        for family,sizes in config["families"].items():
            for size in sizes:
                for seed in config["seeds"]:
                    name=f"{family}-{size}-s{seed}"
                    recipes.append((dict(instance_id=name,family=family,size=size,seed=seed),generate_instance(family,size,seed,settings={"cost_jitter":True})))
    records=[]
    for meta,instance in recipes:
        folder=output/meta["instance_id"];write_json(folder/"input.json",instance)
        meta["instance_sha256"]=fingerprint(instance);description=describe(instance)
        write_json(folder/"description.json",description)
        methods=list(config["methods"])
        if len(instance["actions"])<=8 and "oracle"not in methods:methods.append("oracle")
        labels=[]
        for method in methods:
            for repeat in range(1 if method=="oracle"else config["repetitions"]):
                target=folder/f"{method}-{repeat}.json"
                command=[sys.executable,str(Path(__file__).resolve()),"--worker",str(folder/"input.json"),method,str(target),
                    str(config["budget_seconds"]),str(config["max_states"]),str(config["max_cut_columns"]),str(meta.get("seed",0))]
                process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
                ready=bool(selector.select(timeout=30));line=process.stdout.readline()if ready else""
                selector.close()
                try:
                    if line.strip()!="READY":raise RuntimeError("worker failed startup: "+line)
                    _,stderr=process.communicate(timeout=config["budget_seconds"])
                    if process.returncode or not target.exists():raise RuntimeError("worker error: "+stderr)
                    payload=json.loads(target.read_text())
                except subprocess.TimeoutExpired:
                    process.kill();process.communicate();payload=dict(status="timeout",end_to_end_seconds=None,timeout_seconds=config["budget_seconds"])
                    write_json(target,payload)
                except Exception as error:
                    process.kill();process.communicate();payload=dict(status="internal_error",error=repr(error))
                    write_json(target,payload)
                result=payload.get("result",{})
                if method not in{"greedy","greedy-exchange"}and payload["status"]in{"optimal","infeasible"}:
                    labels.append((payload["status"],result.get("cost"),result.get("selected")))
                record=normalized(payload,meta,method,repeat,config,description,commit)
                write_json(target.with_suffix(".manifest.json"),manifest(instance,dict(config,method=method,repeat=repeat),payload["status"],meta.get("seed",0)))
                records.append(record);write_json(output/"results.json",records)
        if labels and any(label!=labels[0]for label in labels):raise RuntimeError("exact label disagreement: "+meta["instance_id"])
        print(meta["instance_id"],len(records),"records",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--worker",nargs=7);parser.add_argument("--config",type=Path)
    parser.add_argument("--output",type=Path);parser.add_argument("--instances",type=Path);parser.add_argument("--smoke",action="store_true")
    args=parser.parse_args()
    if args.worker:worker(*args.worker)
    else:run(args.config,args.output,args.instances,args.smoke)
