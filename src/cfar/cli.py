from __future__ import annotations

import argparse
from decimal import InvalidOperation
import json
import time
from pathlib import Path

from .certificates import make_certificate, verify_certificate
from .errors import ValidationError
from .io import manifest, write_json
from .oracle import exact_oracle
from .dp_partition import solve_partition
from .dp_local_intervals import solve_local_shaft
from .interface_recognition import recognize_physical_interface
from .dp_owned_interface import solve_owned_interface
from .reuse_lifetime import solve_reuse_lifetime
from .schema import load_instance


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlled CFAR exhaustive oracle and replay verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)
    solve = subparsers.add_parser("solve")
    solve.add_argument("instance")
    solve.add_argument("--variant", choices=("SCFAR","RCFAR"), default="SCFAR")
    solve.add_argument("--topology-weight", default="1")
    solve.add_argument("--max-actions", type=int, default=20)
    solve.add_argument("--output", required=True, help="directory for ignored runtime artifacts")
    partition = subparsers.add_parser("solve-partition", help="strict jointly feasible activation catalogue only")
    partition.add_argument("instance")
    partition.add_argument("--max-components", type=int, default=16)
    partition.add_argument("--max-states", type=int, default=100000)
    partition.add_argument("--output", required=True)
    local = subparsers.add_parser("solve-local-shaft", help="one-profile full path with local geometric conflicts")
    local.add_argument("instance")
    local.add_argument("--max-actions", type=int, default=100)
    local.add_argument("--max-states", type=int, default=100000)
    local.add_argument("--output", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("instance")
    verify.add_argument("certificate")
    verify.add_argument("--max-actions", type=int, default=20)
    validate = subparsers.add_parser("validate")
    validate.add_argument("instance")
    recognize = subparsers.add_parser("recognize-interface", help="check M09 physical-interface assumptions; no solver")
    recognize.add_argument("instance")
    recognize.add_argument("--output", required=True)
    for command in ("solve-owned-interface", "solve-reuse-lifetime"):
        owned = subparsers.add_parser(command, help="exact recognized physical-interface DP")
        owned.add_argument("instance")
        owned.add_argument("--max-states", type=int, default=100000)
        owned.add_argument("--max-cut-columns", type=int, default=65536)
        owned.add_argument("--no-compression", action="store_true")
        owned.add_argument("--prune-irrelevant", action="store_true")
        owned.add_argument("--output", required=True)
    cp = subparsers.add_parser("solve-cp-sat", help="flow baseline on the strict recognized model")
    cp.add_argument("instance")
    cp.add_argument("--time-limit", type=float, default=60)
    cp.add_argument("--seed", type=int, default=0)
    cp.add_argument("--output", required=True)
    greedy = subparsers.add_parser("solve-greedy", help="whole-action heuristic; failure is not infeasibility")
    greedy.add_argument("instance")
    greedy.add_argument("--improve", action="store_true")
    greedy.add_argument("--exchange-budget", type=int, default=256)
    greedy.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        instance = load_instance(args.instance)
        if args.command == "validate":
            print(json.dumps({"valid":True,"building_id":instance["building_id"]}))
        elif args.command == "verify":
            certificate = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
            print(json.dumps(verify_certificate(instance, certificate, args.max_actions)))
        else:
            output = Path(args.output)
            output.mkdir(parents=True, exist_ok=True)
            if any(output.iterdir()):
                raise ValidationError("OUTPUT_NOT_EMPTY", "choose a new run directory")
            started = time.perf_counter()
            if args.command in {"solve-cp-sat", "solve-greedy"}:
                if args.command == "solve-cp-sat":
                    from .cp_sat import solve_cp_sat
                    result = solve_cp_sat(instance, time_limit=args.time_limit, seed=args.seed)
                else:
                    from .greedy import solve_greedy, improve_greedy
                    result = improve_greedy(instance, exchange_budget=args.exchange_budget) if args.improve else solve_greedy(instance)
                write_json(output/"result.json", result)
                settings = dict(method=result["method"], variant="SCFAR",
                                timeout=getattr(args, "time_limit", None),
                                exchange_budget=args.exchange_budget if getattr(args,"improve",False) else None,
                                elapsed_seconds=time.perf_counter()-started)
                write_json(output/"manifest.json", manifest(instance, settings, result["status"], getattr(args, "seed", 0)))
                print(json.dumps({k: result[k] for k in ("status", "cost", "selected")}))
                return
            elif args.command in {"solve-owned-interface", "solve-reuse-lifetime"}:
                solver = solve_reuse_lifetime if args.command == "solve-reuse-lifetime" else solve_owned_interface
                result = solver(instance, compress=not args.no_compression,
                                               max_states=args.max_states, max_cut_columns=args.max_cut_columns,
                                               prune_irrelevant=args.prune_irrelevant)
                write_json(output/"result.json", result)
                settings = dict(method=result["method"], variant="SCFAR", compression=not args.no_compression,
                                max_states=args.max_states, max_cut_columns=args.max_cut_columns,
                                prune_irrelevant=args.prune_irrelevant,
                                timeout=None, elapsed_seconds=time.perf_counter()-started)
                write_json(output/"manifest.json", manifest(instance,settings,result["status"]))
                print(json.dumps({"status":result["status"], "cost":result["cost"],
                                  "selected":result["selected"], "statistics":result["statistics"],
                                  "optimality_evidence":result["optimality_evidence"]}))
                return
            if args.command == "recognize-interface":
                result = recognize_physical_interface(instance)
                write_json(output/"recognition.json", result)
                write_json(output/"manifest.json", manifest(instance,
                           {"method": "physical_interface_recognition_v1", "variant": "SCFAR",
                            "timeout": None, "elapsed_seconds": time.perf_counter()-started}, "recognized"))
                print(json.dumps({"recognized": True, "parameters": result["parameters"],
                                  "blocked_actions": len(result["blocked"])}))
                return
            if args.command in {"solve-partition", "solve-local-shaft"}:
                result = (solve_partition(instance, args.max_components, args.max_states) if args.command == "solve-partition"
                          else solve_local_shaft(instance, args.max_actions, args.max_states))
                settings = {"method": result["method"], "variant": "SCFAR",
                            "max_components": getattr(args, "max_components", None),
                            "max_actions": getattr(args, "max_actions", None), "max_states": args.max_states,
                            "timeout": None, "elapsed_seconds": time.perf_counter()-started}
                write_json(output/"result.json", result)
                write_json(output/"manifest.json", manifest(instance, settings, result["status"]))
                print(json.dumps({"status": result["status"], "cost": result["cost"],
                                  "selected": result["selected"], "optimality_evidence": result["optimality_evidence"]}))
                return
            result = exact_oracle(instance,args.variant,args.topology_weight,args.max_actions)
            certificate = make_certificate(instance,result)
            verification = verify_certificate(instance,certificate,args.max_actions)
            settings = {"method":"exhaustive_oracle","variant":args.variant,
                        "topology_weight":args.topology_weight,"max_actions":args.max_actions,
                        "timeout":None,"elapsed_seconds":time.perf_counter()-started}
            write_json(output/"result.json",result)
            write_json(output/"certificate.json",certificate)
            write_json(output/"verification.json",verification)
            write_json(output/"manifest.json",manifest(instance,settings,result["status"]))
            (output/"ledger.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in result["ledger"]),encoding="utf-8")
            print(json.dumps({"status":result["status"],"cost":result["cost"],"selected":result["selected"],"certificate_valid":True}))
    except (ValidationError, KeyError, TypeError, ValueError, InvalidOperation) as error:
        parser.exit(2,f"{error}\n")


if __name__ == "__main__":
    main()
