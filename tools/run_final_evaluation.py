"""Reproduce Iteration 23 raw artifacts. No figures, RPC, data capture or deployment."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ascend_optimizer.final_evaluation import ROOT, replay, json_bytes, csv_bytes

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Byte-for-byte replay; no writes')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results')
    args=parser.parse_args();raw,summary=replay()
    artifacts={'final_evaluation_iteration23.json':json_bytes(raw),
        'final_evaluation_iteration23.csv':csv_bytes(raw['rows']),
        'final_evaluation_iteration23_summary.json':json_bytes(summary)}
    for name,content in artifacts.items():
        path=args.output_dir/name
        if args.check:
            if path.read_bytes()!=content:raise SystemExit('Replay mismatch: '+name)
        else:
            args.output_dir.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    print(f"SYNTHETIC_EVALUATION_ONLY: {summary['total_scenarios']} scenarios / {summary['normalized_rows']} rows; "+('exact replay passed' if args.check else 'artifacts written'))
