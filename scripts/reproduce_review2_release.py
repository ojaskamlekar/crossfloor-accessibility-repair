"""Regenerate final tables, figures, certificates and paper from the review archive.

Use the documented campaign separately to collect new benchmark measurements.
This workflow audits and rerenders the recorded evidence without substituting
new workstation timings into the submitted results.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--evidence",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--skip-compile",action="store_true")
    args=parser.parse_args();e=args.evidence.resolve();out=args.output.resolve()
    if out.exists()and any(out.iterdir()):raise ValueError("fresh output required")
    if subprocess.check_output(["git","status","--porcelain"],text=True).strip():raise ValueError("commit before release reproduction")
    out.mkdir(parents=True,exist_ok=True);h=e/"historical";r=e/"review2"
    def run(script,*arguments):
        subprocess.run([sys.executable,"scripts/"+script,*map(str,arguments)],check=True)
    run("audit_building_denominators.py","--groups",h/"duplex",h/"public-inputs/instances",r/"public-inputs/instances",e/"reuse-inputs",
        "--audits",h/"public-inputs/audits","--output",out/"denominators.json")
    roots=[r/name for name in("routine","boundary","ablations","public")]
    run("summarize_review2.py","--evidence",*roots,"--denominators",out/"denominators.json","--output",out/"summary")
    run("summarize_reuse.py","--evidence",e/"reuse","--analytic",e/"reuse-inputs-analytic-witnesses.json","--output",out/"reuse-summary")
    run("replay_review2.py","--evidence",*roots,e/"reuse","--output",out/"replay")
    run("make_ieee_figures.py","--controlled",h/"core","--building",h/"duplex","--demo",h/"demo","--controls",h/"controls",
        "--optimizers",h/"optimizers","--output",out/"figures")
    run("build_ieee_master.py","--controlled",h/"core","--building",h/"duplex","--demo",h/"demo","--controls",h/"controls",
        "--optimizers",h/"optimizers","--public-audit",h/"public-inputs","--public-results",h/"public-results",
        "--figures",out/"figures","--review2",out/"summary","--reuse",out/"reuse-summary","--output",out/"paper")
    if not args.skip_compile:
        compiler=shutil.which("pdflatex")
        if not compiler:raise RuntimeError("pdflatex missing; install TeX or use --skip-compile for source-only regeneration")
        for iteration in range(5):
            transcript=out/"paper"/f"compile-{iteration+1}.txt"
            with transcript.open("w")as stream:
                process=subprocess.run([compiler,"-interaction=nonstopmode","-halt-on-error","master.tex"],cwd=out/"paper",stdout=stream,stderr=subprocess.STDOUT,text=True)
            if process.returncode:raise RuntimeError("LaTeX failed:\n"+transcript.read_text()[-5000:])
        log=(out/"paper/master.log").read_text(errors="replace")
        if "Overfull"in log or "There were undefined references"in log or "undefined on input line"in log:
            raise RuntimeError("inspect LaTeX layout/reference warnings before delivery")
        extractor=shutil.which("pdftotext")
        if extractor:
            rendered=subprocess.check_output([extractor,str(out/"paper/master.pdf"),"-"],text=True)
            if "??"in rendered:raise RuntimeError("unresolved reference visible in rendered PDF")
        print(out/"paper/master.pdf")


if __name__=="__main__":main()
