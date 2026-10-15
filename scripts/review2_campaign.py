"""One sequential pinned workflow; every suite retains every timeout/cap/failure."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--audits",type=Path,required=True);args=parser.parse_args()
    if args.output.exists()and any(args.output.iterdir()):raise ValueError("fresh campaign directory required")
    if subprocess.check_output(["git","status","--porcelain"],text=True).strip():raise ValueError("commit first")
    args.output.mkdir(parents=True,exist_ok=True)
    commands=[
        ["scripts/public_multiroom_controlled.py","--audits",str(args.audits),"--output",str(args.output/"public-inputs")],
        ["scripts/review2_benchmarks.py","--config","docs/review2_protocol.json","--output",str(args.output/"routine")],
        ["scripts/review2_benchmarks.py","--config","docs/review2_boundary.json","--output",str(args.output/"boundary")],
        ["scripts/review2_benchmarks.py","--config","docs/review2_ablation.json","--output",str(args.output/"ablations")],
        ["scripts/review2_benchmarks.py","--config","docs/review2_public.json","--instances",str(args.output/"public-inputs/instances"),"--output",str(args.output/"public")],
        ["scripts/summarize_review2.py","--evidence",*[str(args.output/name)for name in("routine","boundary","ablations","public")],"--output",str(args.output/"summary")]]
    for command in commands:
        print("Running",command[0],command[-1],flush=True)
        subprocess.run([sys.executable,*command],check=True)


if __name__=="__main__":main()
