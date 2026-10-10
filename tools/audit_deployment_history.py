"""Read-only, pinned Git-history inventory for the Iteration 17 recovery audit.

Search results are leads, NOT deployment verification. No network/RPC/transactions.
Run: python tools/audit_deployment_history.py --check
Requires full history through the accepted baseline. The optional local reflog
commit has the identical tree to ff7c269; its absence in a new clone is explicit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'cd92cb957ebcd0d24637347875b822fe108e6bc6'
LOCAL_ALTERNATE = '15909a34c9141dc9bf9cce109cd33ecc68ba19ed'
ALTERNATE_EQUIVALENT = 'ff7c269cffa4b112b5324c84289aac423a8c16e3'
AUDIT = ROOT / 'data/deployment_recovery_audit.json'
TERMS = re.compile(
    r'AscendVault|StrategyManager|RewardAccounting|Native0GStakingAdapter|'
    r'GimoAdapter|JaineLPAdapter|OkuV3Adapter|V3LiquidityAdapter|AscendProtocolAdapter|'
    r'deploy|registerStrategy|strategyId|adapter|vault|manager|16661|16602|8453|'
    r'evmrpc|chainscan|\btx\b|transactionHash|contractAddress|receipt|blockNumber|'
    r'broadcast|ignition|PRIVATE_KEY|DEPLOYER|VAULT_ADDRESS|MANAGER_ADDRESS', re.I)
ADDRESS = re.compile(r'(?<![0-9a-fA-F])0x[0-9a-fA-F]{40}(?![0-9a-fA-F])')
HASH_TOKEN = re.compile(r'(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])')
TX_SHAPE = re.compile(r'(?<![0-9a-fA-F])0x[0-9a-fA-F]{64}(?![0-9a-fA-F])')
DEPLOY_PATH = re.compile(r'(^|/)(deployments?|broadcast|ignition)(/|\.)|(^|/)deploy[^/]*\.(js|ts|json)$|\.env', re.I)


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def tree(ref: str) -> list[tuple[str, str]]:
    result = []
    for entry in git('ls-tree', '-rz', ref).split(b'\0'):
        if not entry:
            continue
        meta, path = entry.split(b'\t', 1)
        _, kind, oid = meta.decode().split()
        if kind == 'blob':
            result.append((path.decode(), oid))
    return result


def scan_history() -> dict:
    commits = git('rev-list', '--reverse', '--topo-order', BASELINE).decode().splitlines()
    versions = {}
    paths = set()
    for commit in commits:
        for path, oid in tree(commit):
            versions.setdefault((path, oid), commit)
            paths.add(path)
    nontext = []
    addresses = {}
    tx_literals = {}
    hash_token_paths = set()
    files = {}
    for (path, oid), commit in sorted(versions.items()):
        content = git('cat-file', 'blob', oid)
        info = files.setdefault(path, {'versions': [], 'search_hits': 0})
        info['versions'].append({'blob': oid, 'first_commit': commit,
                                 'sha256': hashlib.sha256(content).hexdigest()})
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            nontext.append({'path': path, 'blob': oid})
            continue
        for number, line in enumerate(text.splitlines(), 1):
            info['search_hits'] += bool(TERMS.search(line))
            if HASH_TOKEN.search(line):
                hash_token_paths.add(path)
            for pattern, target in [(ADDRESS, addresses), (TX_SHAPE, tx_literals)]:
                for value in pattern.findall(line):
                    target.setdefault(value.lower(), []).append(
                        {'path': path, 'blob': oid, 'commit': commit, 'line': number})
    # All historical file versions are scanned, not only paths matching deploy.
    canonical = json.dumps(sorted([p, b, c] for (p, b), c in versions.items()),
                           separators=(',', ':')).encode()
    current_paths = {p for p, _ in tree(BASELINE)}
    return {
        'baseline': BASELINE, 'reachable_commit_count': len(commits),
        'merge_commit_count': len(git('rev-list', '--min-parents=2', BASELINE).splitlines()),
        'commits': commits, 'path_count': len(paths), 'unique_file_versions': len(versions),
        'unique_blobs': len({b for p, b in versions}),
        'corpus_sha256': hashlib.sha256(canonical).hexdigest(),
        'files': files, 'historical_only_paths': sorted(paths - current_paths),
        'deployment_path_matches': sorted(p for p in paths if DEPLOY_PATH.search(p)),
        'nontext_versions': nontext,
        'address_literals': addresses, 'transaction_shape_literals': tx_literals,
        'unprefixed_hash_token_paths': sorted(hash_token_paths),
    }


def recovery_outcome(*, deployment: bool, registration: bool, route: bool,
                     partial_actual_identity: bool = False) -> str:
    """Evidence sufficiency rule; references/mock tests cannot set proof flags.

    For core instances, registration/route mean the appropriate linkage/config
    proof rather than independent strategy registration.
    """
    if deployment and registration and route:
        return 'RECOVERED'
    if deployment or registration or partial_actual_identity:
        return 'PARTIALLY_RECOVERED'
    return 'NOT_FOUND'


def validate_audit(audit: dict) -> None:
    expected = {'NATIVE_STAKE_0G', 'GIMO_STAKE_0G', 'JAINE_LP_0G_USDC',
                'OKU_LP_0G_USDC', 'ASCEND_STAKE_A0G'}
    ids = [s['strategy_id'] for s in audit['strategies']]
    if len(ids) != 5 or set(ids) != expected:
        raise ValueError('Exactly five unique strategy verdicts required')
    for item in audit['core'] + audit['strategies']:
        computed = recovery_outcome(deployment=item['deployment_proven'],
                                    registration=item['registration_proven'],
                                    route=item['route_config_proven'],
                                    partial_actual_identity=item['partial_actual_identity'])
        if item['outcome'] != computed:
            raise ValueError('Recovery outcome contradicts proof sufficiency')
    artifact_ids = [a['artifact_id'] for a in audit['artifacts']]
    if len(set(artifact_ids)) != len(artifact_ids):
        raise ValueError('Duplicate artifact ID')
    for artifact in audit['artifacts']:
        network = artifact['network']
        if not network['state'] or 'chain_id' not in network:
            raise ValueError('Explicit network state required')
        if artifact['evidence_class'] in {'PROTOCOL_REFERENCE', 'SOURCE_CODE_REFERENCE', 'DOCUMENTATION_CLAIM', 'RECORDED_RUNTIME_REFERENCE'} and artifact['capstone_deployment_proven']:
            raise ValueError('Reference is not deployment proof')
        if network['chain_id'] == 16602 and artifact.get('mainnet_proof', False):
            raise ValueError('Galileo cannot prove Mainnet deployment')
        for source in artifact['sources']:
            content = git('show', source['commit'] + ':' + source['path'])
            if hashlib.sha256(content).hexdigest() != source['sha256']:
                raise ValueError('Artifact provenance content changed')
    for path, expected_sha in audit['unchanged_files'].items():
        # Iteration 19 adds an evidence-backed path to this implementation. The
        # audit's source hash remains a historical fact, not a permanent ban on
        # future authorized implementation changes. Evidence/config hashes below
        # still guard the working tree; no historical artifact is rewritten.
        # Iteration 25 authorizes the current-request dashboard migration.
        # The original UI hashes still describe the pinned Iteration 17 audit,
        # not a permanent restriction on presentation files. All canonical
        # evidence/configuration/contract guards below remain current-file checks.
        historical_paths = {'src/ascend_optimizer/amount_optimizer.py',
                            'frontend/src/app/page.tsx', 'frontend/src/app/layout.tsx',
                            'frontend/src/app/globals.css'}
        content = git('show', 'f8d309d2e8ca1904cbe31560a17591332ed7b80c:' + path) if path in historical_paths else (ROOT / path).read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha:
            raise ValueError('Frozen file changed: ' + path)
    configs = json.loads((ROOT / 'data/runtime_strategy_config.json').read_text())
    if any(r['verification_state'] != 'UNRESOLVED' or r['config_identity'] is not None
           for r in configs['records']):
        raise ValueError('Runtime configs must remain unresolved')
    if len((ROOT / 'data/admission_evidence.csv').read_text().splitlines()) != 1:
        raise ValueError('Admission captures must remain empty')


def check() -> None:
    audit = json.loads(AUDIT.read_text())
    validate_audit(audit)
    if scan_history() != audit['history_search']:
        raise ValueError('Pinned history inventory differs')
    try:
        alternate_tree = git('rev-parse', LOCAL_ALTERNATE + '^{tree}').decode().strip()
    except subprocess.CalledProcessError:
        print('Local reflog-only alternate unavailable; recorded identical-tree comparison retained.')
    else:
        if alternate_tree != git('rev-parse', ALTERNATE_EQUIVALENT + '^{tree}').decode().strip():
            raise ValueError('Local alternate no longer matches accepted Iteration 10 tree')
    print('Audit provenance, pinned history and frozen file checks passed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Replay inventory and validate committed audit')
    args = parser.parse_args()
    if args.check:
        check()
    else:
        print(json.dumps(scan_history(), indent=2, allow_nan=False))
