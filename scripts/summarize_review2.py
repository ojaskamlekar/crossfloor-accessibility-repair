"""Audit every raw record before rendering repeat-aware figures and paper text."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from statistics import median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cfar.io import fingerprint,write_json


def tex(value):
    return str(value).replace("\\",r"\textbackslash{}").replace("_",r"\_").replace("%",r"\%").replace("&",r"\&").replace("$",r"\$")


def audit(root):
    protocol=json.loads((root/"protocol.json").read_text())
    if protocol["dirty"]or protocol["smoke"]:raise ValueError("smoke/dirty records cannot support paper results")
    rows=json.loads((root/"results.json").read_text());keys=set();fingerprints=None
    groups=defaultdict(list)
    for row in rows:
        key=(row["instance_id"],row["solver"],row["repeat_index"])
        if key in keys:raise ValueError("duplicate record")
        keys.add(key);groups[(row["instance_id"],row["solver"])].append(row)
        folder=root/row["instance_id"];instance=json.loads((folder/"input.json").read_text())
        target=folder/f"{row['solver']}-{row['repeat_index']}.json"
        raw=json.loads(target.read_text());m=json.loads(target.with_suffix(".manifest.json").read_text())
        parameters=raw.get("result",{}).get("parameters")
        if "solver_parameters"in row and row["solver_parameters"]!=parameters:raise ValueError("reported parameters mismatch")
        row["solver_parameters"]=parameters
        if m["git_dirty"]or row["code_commit"]!=protocol["code_commit"]or m["git_revision"]!=row["code_commit"]:
            raise ValueError("revision/dirty mismatch")
        if row["instance_sha256"]!=fingerprint(instance)or m["input_fingerprint"]!=row["instance_sha256"]:
            raise ValueError("input fingerprint mismatch")
        if raw["status"]!=row["status"]:raise ValueError("raw status mismatch")
        if fingerprints is None:fingerprints=m["source_fingerprints"]
        if m["source_fingerprints"]!=fingerprints:raise ValueError("mixed solver sources")
        if row["selected_action_ids"]is not None:
            c=raw.get("certificate",{})
            if not(c.get("route_replay_result")and c.get("topology_preservation_result")):
                raise ValueError("missing feasible-solution replay")
        if row["status"]=="internal_error":raise ValueError("internal error retained; resolve before paper generation")
    instance_ids={r["instance_id"]for r in rows}
    for name in instance_ids:
        instance=json.loads((root/name/"input.json").read_text())
        methods=protocol["methods"]+(["oracle"]if len(instance["actions"])<=8 and "oracle"not in protocol["methods"]else[])
        exact=[]
        for method in methods:
            group=groups[name,method];expected=1 if method=="oracle"else protocol["repetitions"]
            if sorted(r["repeat_index"]for r in group)!=list(range(expected)):raise ValueError("missing or extra repetition")
            for r in group:
                if method not in{"greedy","greedy-exchange"}and r["status"]in{"optimal","infeasible"}:
                    exact.append((r["status"],r["objective_cost"],r["selected_action_ids"]))
        if exact and any(label!=exact[0]for label in exact):raise ValueError("exact disagreement: "+name)
    return rows,protocol,fingerprints


def summarize(roots,output,denominators=None):
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise ValueError("fresh output required")
    rows=[];protocols=[];sources={};all_fingerprints=None
    for root in roots:
        current,protocol,fps=audit(root)
        if all_fingerprints is None:all_fingerprints=fps
        if all_fingerprints!=fps:raise ValueError("cross-suite source mismatch")
        rows.extend(current);protocols.append(protocol)
        for file in root.rglob("*.json"):sources[str(file.resolve())]=hashlib.sha256(file.read_bytes()).hexdigest()
    counts={m:dict(Counter(r["status"]for r in rows if r["solver"]==m))for m in sorted({r["solver"]for r in rows})}
    cases={(r["experiment_id"],r["instance_id"])for r in rows}
    source_models=sorted({r["source_building_id"]for r in rows if r["source_building_id"]})
    source_subsets=sorted({(r["source_building_id"],r["subset_id"])for r in rows if r["source_building_id"]})
    public={}
    for r in rows:
        if r["source_building_id"]and r["solver"]=="cp-sat"and r["repeat_index"]==0:public[r["instance_id"]]=r
    summaries={}
    for method in counts:
        complete=[r for r in rows if r["solver"]==method and r["end_to_end_seconds"]is not None]
        summaries[method]=dict(status_counts=counts[method],measured_time_count=len(complete))
    core={"compressed","full","cp-sat","greedy-exchange"}
    present=defaultdict(set)
    for r in rows:present[r["experiment_id"],r["instance_id"]].add(r["solver"])
    common={key for key,methods in present.items()if core<=methods}
    common_rows=[r for r in rows if (r["experiment_id"],r["instance_id"])in common and r["solver"]in core]
    common_counts={m:dict(Counter(r["status"]for r in common_rows if r["solver"]==m))for m in sorted(core)}
    denominators_by_method={m:sum(c.values())for m,c in common_counts.items()}
    if len(set(denominators_by_method.values()))!=1:raise ValueError("unequal common-cohort repetition counts")
    exact={(r["experiment_id"],r["instance_id"],r["repeat_index"]):r for r in common_rows if r["solver"]=="cp-sat"}
    quality=[]
    for r in common_rows:
        if r["solver"]!="greedy-exchange"or r["status"]!="feasible":continue
        c=exact[r["experiment_id"],r["instance_id"],r["repeat_index"]]
        if c["status"]!="optimal":continue
        gap=Fraction(r["objective_cost"])-Fraction(c["objective_cost"])
        if gap<0:raise ValueError("heuristic beat certified optimum")
        quality.append(dict(experiment_id=r["experiment_id"],instance_id=r["instance_id"],repeat=r["repeat_index"],
            instance_sha256=r["instance_sha256"],
            cost_matches=gap==0,full_label_matches=gap==0 and r["selected_action_ids"]==c["selected_action_ids"],
            relative_excess=float(gap/max(Fraction(1),abs(Fraction(c["objective_cost"]))))))
    quality_inputs=defaultdict(list)
    for q in quality:quality_inputs[q["instance_sha256"]].append(q)
    compression_measurements={}
    for size in sorted({r["size"]for r in rows if r["generator_family"]=="compression"}):
        compression_measurements[str(size)]={}
        for method in("compressed","full"):
            samples=[r for r in rows if r["generator_family"]=="compression"and r["size"]==size and r["solver"]==method]
            compression_measurements[str(size)][method]=dict(median_seconds=median(r["end_to_end_seconds"]for r in samples),
                median_rows_removed=median(r["solver_statistics"]["representative_rows_removed"]for r in samples),
                median_peak_retained=median(r["peak_retained_states"]for r in samples))
    report=dict(protocols=protocols,measurement_count=len(rows),experiment_case_count=len(cases),
        unique_input_fingerprints=len({r["instance_sha256"]for r in rows}),source_models=source_models,
        source_subsets=source_subsets,public_variants=public,methods=summaries,
        solver_source_fingerprints=all_fingerprints,
        common_case_pairs=len(common),common_status_counts=common_counts,common_runs_per_method=next(iter(denominators_by_method.values())),
        heuristic_quality=dict(compared_feasible_runs=len(quality),cost_matching_runs=sum(q["cost_matches"]for q in quality),
            distinct_serialized_inputs=len(quality_inputs),cost_matching_inputs=sum(all(q["cost_matches"]for q in qs)for qs in quality_inputs.values()),
            full_label_matching_runs=sum(q["full_label_matches"]for q in quality),max_relative_excess=max((q["relative_excess"]for q in quality),default=None),runs=quality),
        compression_measurements=compression_measurements,
        interpretation="Measurements, price-seeded variants, selected subsets and original source models are distinct denominators. No full-building experiment. Molio also occurs in historical evidence.")
    if denominators:
        report["building_denominators"]=json.loads(denominators.read_text())
        sources[str(denominators.resolve())]=hashlib.sha256(denominators.read_bytes()).hexdigest()
    write_json(output/"summary.json",report);write_json(output/"results.json",rows)
    plots(rows,output)
    write_json(output/"provenance.json",dict(source_hashes=sources,
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in output.iterdir()if p.is_file()}))
    print(json.dumps(dict(records=len(rows),cases=len(cases),methods=counts,public_models=source_models)))


def plots(rows,out):
    plt.rcParams.update({"font.family":"serif","font.size":8,"pdf.fonttype":42})
    methods=[m for m in ("compressed","full","cp-sat","greedy-exchange")if any(r["solver"]==m for r in rows)]
    colors={"compressed":"#174d78","full":"#ba5a1c","cp-sat":"#23764b","greedy-exchange":"#8b4486"}
    mapping={"catalogue":"candidate_action_count","connectivity":"r","profiles":"p","ownership":"h","support":"L","compression":"L","compression-unfavorable":"candidate_action_count"}
    fig,axes=plt.subplots(2,4,figsize=(10,5.3));axes=axes.flatten()
    for ax,(family,param)in zip(axes,mapping.items()):
        for method in methods:
            subset=[r for r in rows if r["generator_family"]==family and r["solver"]==method]
            by=defaultdict(list)
            for r in subset:
                d=r["instance_description"];p=d.get("measured_interface_parameters")or{}
                x=d.get(param)if param in d else p.get(param)
                if x is not None:by[x].append(r)
            xs=[];ys=[];low=[];high=[]
            for x,group in sorted(by.items()):
                times=[r["end_to_end_seconds"]for r in group if r["status"]in{"optimal","infeasible","feasible","heuristic_failed"}and r["end_to_end_seconds"]is not None]
                if times:
                    q=np.percentile(times,[25,50,75]);xs.append(x);ys.append(q[1]);low.append(q[1]-q[0]);high.append(q[2]-q[1])
                for r in group:
                    if r["status"]in{"timeout","feasible_incumbent","internal_cap"}:
                        y=r["end_to_end_seconds"]or r["solver_configuration"]["post_ready_wall_budget_seconds"]
                        ax.scatter(x,y,marker="^"if r["status"]!="internal_cap"else"x",s=28,color=colors[method],zorder=5)
            if xs:ax.errorbar(xs,ys,yerr=[low,high],marker="o",markersize=3,label=method,color=colors[method],capsize=2)
        ax.set_title(family);ax.set_xlabel("measured "+param);ax.set_ylabel("function seconds");ax.set_yscale("log");ax.grid(alpha=.2)
    axes[-1].axis("off");handles,labels=axes[0].get_legend_handles_labels();axes[-1].legend(handles,labels,loc="center",fontsize=8)
    axes[-1].text(.05,.05,"Median / IQR across declared runs.\nTriangles: wall limit / incumbent.\nCrosses: internal state/cut cap.\nNo timeout imputation into medians.",transform=axes[-1].transAxes,fontsize=8)
    fig.tight_layout();fig.savefig(out/"review2_scaling.pdf",bbox_inches="tight");plt.close(fig)
    # All declared compression and unfavorable cases, not one selected winner.
    data=[r for r in rows if r["generator_family"]in{"compression","compression-unfavorable"}and r["solver"]in{"compressed","full"}]
    fig,axes=plt.subplots(1,3,figsize=(9,2.7))
    for method,color in (("compressed",colors["compressed"]),("full",colors["full"])):
        for favorable,marker in (("compression","o"),("compression-unfavorable","s")):
            subset=[r for r in data if r["solver"]==method and r["generator_family"]==favorable and r["solver_statistics"]]
            for ax,key in zip(axes,("representative_rows_removed","peak_retained_states","representative_seconds")):
                by=defaultdict(list)
                for r in subset:
                    value=r["solver_statistics"].get(key)
                    if value is not None:by[r["size"]].append(value)
                xs=sorted(by);ax.plot(xs,[median(by[x])for x in xs],marker=marker,color=color,ls="-"if marker=="o"else"--",label=method+" / "+("cyclic"if marker=="o"else"unfavorable"))
                ax.set_xlabel("declared family size");ax.set_ylabel(key.replace("_"," "));ax.grid(alpha=.2)
    axes[-1].legend(fontsize=6);fig.tight_layout();fig.savefig(out/"review2_compression.pdf",bbox_inches="tight");plt.close(fig)
    counts={m:Counter(r["status"]for r in rows if r["solver"]==m)for m in sorted({r["solver"]for r in rows})}
    statuses=[s for s in("optimal","feasible","infeasible","heuristic_failed","internal_cap","timeout","feasible_incumbent","unsupported","internal_error")if any(c[s]for c in counts.values())]
    fig,ax=plt.subplots(figsize=(7,2.8));bottom=np.zeros(len(counts))
    for status in statuses:
        values=[counts[m][status]for m in counts];ax.bar(list(counts),values,bottom=bottom,label=status);bottom+=values
    ax.set_ylabel("fresh-process measurements");ax.tick_params(axis="x",rotation=20);ax.legend(fontsize=7,ncol=3,loc="upper center",bbox_to_anchor=(.5,1.3))
    fig.tight_layout();fig.savefig(out/"review2_statuses.pdf",bbox_inches="tight");plt.close(fig)


def paper_section(output):
    prov=json.loads((output/"provenance.json").read_text())
    for name,digest in prov["outputs"].items():
        if hashlib.sha256((output/name).read_bytes()).hexdigest()!=digest:raise ValueError("summary output changed")
    d=json.loads((output/"summary.json").read_text())
    lines=[r"\section{Additional Interface and Multi-Room Experiments}\label{sec:review2}",
        "These measurements are separate from the historical corpus above. They contain "+str(d["measurement_count"])+" fresh-process measurements over "+str(d["experiment_case_count"])+" experiment/case pairs, not that many independent buildings. Routine structural cases use five repetitions, declared boundary and expensive public cases three, with price seeds 0, 1 and 2 fixed before collection. Only costs vary across seeded copies of fixed geometric families. Raw failures remain in the status counts. Imports/startup are excluded from function times; peak process RSS includes imports. All methods share the same post-ready wall budget in each suite. Memory limits are not imposed and the workstation is not hardware-isolated.",
        r"\subsection{Fair Baselines and Geometry Processing}",
        "The strengthened heuristic prunes redundant actions and examines a deterministic budget of 256 whole-action 0--2-out/0--2-in exchanges, including rescue of failed construction. Every candidate retains full paid geometry; failure is not infeasibility. CP-SAT records cost-stage bounds and interrupted incumbents separately from later identifier tie stages. When available, the reported relative cost gap is max(0,U--L)/max(1,abs(U)); zero-cost optima have gap zero. Solver-reported floating bounds are identified as estimates; unsafe large-integer floating bounds are unavailable rather than silently exact.",
        "Recognition timings split validation, activation-geometry compilation, footprint preparation, cells and unit/component construction. Compilation includes its semantic revalidation; the geometry field is not a pure GEOS-only profile. DP event construction, optimization, replay and extra independent selected-set checks are separate. End-to-end function time remains the primary metric. The memoized mode caches only immutable coordinate polygons and room free-space, never an action-set feasibility verdict or solver result; caches begin empty in each process. The uncached ablation disables both. Footprint-intersection and cell-coverage counts identify their exact compiler scopes.",
        r"\begin{table}[t]\caption{Common-Cohort Measurement Outcomes (Same Run Denominator)}\label{tab:review2-status}\centering\scriptsize\begin{tabular}{p{.29\columnwidth}p{.60\columnwidth}}\toprule Method & Outcome counts\\\midrule"]
    for method,details in d["common_status_counts"].items():
        status=", ".join(str(n)+" "+s.replace("_"," ")for s,n in details.items())
        lines.append(tex(method)+" & "+tex(status)+r"\\")
    lines += [r"\bottomrule\end{tabular}\end{table}","The common cohort contains "+str(d["common_case_pairs"])+" experiment/case pairs and exactly "+str(d["common_runs_per_method"])+" run positions per listed method; separate ablations and correctness-only oracle calls are excluded from these completion counts. The improved heuristic matches the exact cost on "+str(d["heuristic_quality"]["cost_matching_runs"])+" of "+str(d["heuristic_quality"]["compared_feasible_runs"])+" comparable feasible runs. Full original-action label matches are "+str(d["heuristic_quality"]["full_label_matching_runs"])+". Heuristic cost excess is measured against the known optimum, normalized by max(1,abs(optimum)); it is distinct from the CP-SAT incumbent/bound gap.",r"\begin{figure*}[t]\centering\includegraphics[width=.98\textwidth]{figures/review2_scaling.pdf}\caption{Declared structural families, plotted against measured parameters. Medians and interquartile ranges across cost seeds and fresh-process repeats retain timeout and internal-cap markers. Connectivity width also increases collision-cell count; cyclic size also increases span, so these are not perfectly isolated factorial effects.}\label{fig:review2-scaling}\end{figure*}",
        r"\begin{figure*}[t]\centering\includegraphics[width=.96\textwidth]{figures/review2_compression.pdf}\caption{Every declared cyclic and unfavorable compression family. Removed rows, retained states and reduction time are separate measurements; row reduction alone does not establish a net runtime benefit.}\label{fig:review2-compression}\end{figure*}",
        r"\subsection{Multi-Room Horizontal-Access Intervention}"]
    lines.append("The heuristic comparison covers "+str(d["heuristic_quality"]["distinct_serialized_inputs"])+" distinct serialized inputs; all observed feasible runs match the optimum cost on "+str(d["heuristic_quality"]["cost_matching_inputs"])+" of them. These are price-seeded/controlled inputs, not independent source buildings.")
    public=d["public_variants"]
    largest=max(d["compression_measurements"],key=int)
    comp=d["compression_measurements"][largest]["compressed"];full=d["compression_measurements"][largest]["full"]
    lines.append("The largest declared cyclic size is "+largest+": compressed mode removes a median "+str(comp["median_rows_removed"])+" rows, yet its median function time is "+f"{comp['median_seconds']:.3f}"+" seconds versus "+f"{full['median_seconds']:.3f}"+" for full mode. The declared compression families do not establish a net runtime advantage. We therefore position representative compression primarily as part of the completion-preserving theoretical state bound, with its measured overhead and cut-column limits explicit. Safe component pruning tightens the recorded component bound, but irrelevant-room probes need not reduce states because the implementation already introduces optional positions lazily. Reversed-order and memoization measurements are algorithm ablations, separate from altered-semantics controls.")
    if "building_denominators"in d:
        b=d["building_denominators"]
        lines.append("Across all historical and current building-derived evidence, the mechanical source/room-ID audit counts "+str(b["distinct_audited_source_models"])+" audited source models, "+str(b["distinct_used_source_models"])+" used source models, "+str(b["distinct_selected_subsets"])+" distinct selected subsets and "+str(b["deduplicated_variant_definitions"])+" deduplicated variant definitions. There are "+str(b["full_building_experiments"])+" full-building experiments. Historical and new Duplex subsets use different room IDs; Molio's two-room and eight-room subsets likewise differ. The separate local-expiration checkpoint copies the same three multi-room controls and adds no new building, subset or variant definition.")
    if public:
        lines.append("Five pinned source audits were screened for consecutive-storey connected room subsets. Molio admits one four-storey subset with two original rooms per floor and one shared-boundary adjacency edge on every floor; the other four sources are excluded under the documented admission rule. This is one distinct selected subset and three controlled variants, not three new buildings. Molio also appears in the historical two-room suite, with different selected rooms. No full-building accessibility experiment is claimed. All original room rings/GlobalIds are unchanged and every conservative background obstacle remains in the same union; exact duplicate obstacle rectangles may be deduplicated. Door locations/permissions, profiles, reservations, lift proposals and costs are explicitly hypothetical annotations, not authenticated original IFC openings.")
        lines.append(r"\begin{table}[t]\caption{Same Eight Rooms on Four Consecutive Molio Storeys}\label{tab:review2-multiroom}\centering\scriptsize\begin{tabular}{lrrp{.24\columnwidth}}\toprule Variant & Cost & Actions & Status\\\midrule")
        aliases={"open-horizontal":"open horizontal","restricted-horizontal":"restricted p1","no-right-candidates":"no right options"}
        for name,row in sorted(public.items()):
            alias=next((v for k,v in aliases.items()if name.endswith(k)),name)
            lines.append(tex(alias)+" & "+tex(row["objective_cost"]if row["objective_cost"]is not None else"--")+" & "+tex(row["objective_action_count"]if row["objective_action_count"]is not None else"--")+" & "+tex(row["status"])+r"\\")
        lines.append(r"\bottomrule\end{tabular}\end{table}")
        lines.append("With both-profile horizontal doors, the optimum is the three left-chain actions of total cost three. Restricting only the two interior horizontal doors to profile zero switches the optimum to the three right-chain actions of total cost 3.3. Profile zero must reach both rooms on each upper floor; profile one must reach each upper right room. Thus the horizontal access structure materially changes the selected vertical intervention. Removing all right-chain candidates under restricted permissions makes these demands infeasible. Full paid-action replay checks unchanged adjacency on all four floors, while a separate coordinate-interval footprint/graph checker supplements the shared geometry kernel. These synthetic access annotations demonstrate the model's mechanism, not statutory or original-building accessibility.")
    lines += [r"\subsection{Ablations and Independent Checks}",
        "Pruning on/off, representative reduction on/off, reversed valid within-floor unit/action order and immutable-geometry memoization on/off are separate algorithm ablations. Identical-state least-label dominance is retained as part of the state representation; no dominance-off experiment is asserted. Hand-derived optima, input-order and identifier renaming, coordinate translation, consistent geometry/price rescaling, dominated-candidate and candidate-monotonicity checks supplement common solver agreement. The independent paid-rectangle checker does not replace the full containment/obstacle/clearance kernel. Compression is positioned as a completion-preserving theoretical ingredient unless the full timing and memory records establish a useful measured regime; no universal speed advantage is inferred."]
    return "\n\n".join(lines)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--evidence",nargs="+",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);parser.add_argument("--denominators",type=Path)
    args=parser.parse_args();summarize(args.evidence,args.output,args.denominators)
