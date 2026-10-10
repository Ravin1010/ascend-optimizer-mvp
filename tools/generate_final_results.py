"""Generate or verify Iteration 24 outputs from hash-pinned Iteration 23 artifacts."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ascend_optimizer.final_results import ROOT,generate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--output-root',type=Path,default=ROOT,help='Optional isolated generated-output destination')
    args=parser.parse_args();outputs=generate()
    for name,content in outputs.items():
        target=args.output_root/name
        if args.check:
            if not target.exists() or target.read_bytes()!=content:raise SystemExit('Final results replay mismatch: '+name)
        else:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    print(f'SYNTHETIC_EVALUATION_ONLY: 7 tables / 8 figures / {len(outputs)} files '+('replay exactly' if args.check else 'generated'))


if __name__=='__main__':main()
