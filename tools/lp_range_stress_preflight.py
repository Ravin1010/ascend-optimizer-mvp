"""Read-only synthetic LP replay. No RPC, wallet, runtime config or transactions."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ascend_optimizer.lp_range_stress import replay

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', type=Path, help='compare with committed results artifact')
    args = parser.parse_args()
    result = replay()
    if args.check:
        if json.loads(args.check.read_text()) != result:
            raise SystemExit('Synthetic replay differs from committed results')
        print('SYNTHETIC_EVALUATION_ONLY: 2 configurations / 8 shock results reproduced exactly.')
    else:
        print(json.dumps(result, indent=2, allow_nan=False))
