"""Iteration 17 audit-only tests. Synthetic proof flags are never live evidence."""
from copy import deepcopy
import json
from pathlib import Path
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / 'tools/audit_deployment_history.py'))
AUDIT = json.loads((ROOT / 'data/deployment_recovery_audit.json').read_text())


def test_pinned_history_inventory_replays():
    assert MODULE['scan_history']() == AUDIT['history_search']
    assert AUDIT['history_search']['reachable_commit_count'] == 304
    assert AUDIT['history_search']['unique_file_versions'] == 365
    assert AUDIT['history_search']['historical_only_paths'] == []


def test_complete_audit_and_frozen_files_validate():
    MODULE['validate_audit'](AUDIT)
    assert AUDIT['overall_verdict'] == 'NO_RECOVERABLE_CAPSTONE_DEPLOYMENT'
    assert all(s['outcome'] == 'NOT_FOUND' for s in AUDIT['strategies'])
    assert all(s['outcome'] == 'NOT_FOUND' for s in AUDIT['core'])


def test_every_address_literal_is_classified_with_explicit_network_state():
    registered = {v for a in AUDIT['artifacts'] for v in a['addresses']}
    assert registered == set(AUDIT['history_search']['address_literals'])
    assert len(registered) == 36
    assert all('chain_id' in a['network'] and a['network']['state'] for a in AUDIT['artifacts'])
    assert all(not a['capstone_deployment_proven'] for a in AUDIT['artifacts'])


@pytest.mark.parametrize('evidence_class', ['PROTOCOL_REFERENCE', 'SOURCE_CODE_REFERENCE', 'DOCUMENTATION_CLAIM'])
def test_weak_references_cannot_be_promoted_to_deployment_proof(evidence_class):
    audit = deepcopy(AUDIT)
    a = next(a for a in audit['artifacts'] if a['evidence_class'] == evidence_class)
    a['capstone_deployment_proven'] = True
    with pytest.raises(ValueError, match='Reference is not deployment proof'):
        MODULE['validate_audit'](audit)


def test_galileo_cannot_be_promoted_to_mainnet():
    audit = deepcopy(AUDIT)
    audit['artifacts'][0]['network'] = {'chain_id': 16602, 'state': 'SYNTHETIC_TEST_ONLY'}
    audit['artifacts'][0]['mainnet_proof'] = True
    with pytest.raises(ValueError, match='Galileo cannot prove Mainnet'):
        MODULE['validate_audit'](audit)


@pytest.mark.parametrize('deployment,registration,route,partial,expected', [
    (True, False, True, False, 'PARTIALLY_RECOVERED'),
    (False, True, False, False, 'PARTIALLY_RECOVERED'),
    (True, True, False, False, 'PARTIALLY_RECOVERED'),
    (False, False, False, True, 'PARTIALLY_RECOVERED'),
    (False, False, True, False, 'NOT_FOUND'),
    (True, True, True, False, 'RECOVERED'),
])
def test_proof_sufficiency_requires_deployment_registration_and_route(deployment, registration, route, partial, expected):
    assert MODULE['recovery_outcome'](deployment=deployment, registration=registration,
                                      route=route, partial_actual_identity=partial) == expected


def test_duplicate_strategy_verdict_rejected():
    audit = deepcopy(AUDIT)
    audit['strategies'][0] = audit['strategies'][1]
    with pytest.raises(ValueError, match='five unique strategy'):
        MODULE['validate_audit'](audit)


def test_runtime_commits_are_diagnostics_not_public_deployment_proof():
    assert len(AUDIT['runtime_commit_audit']) == 10
    for record in AUDIT['runtime_commit_audit']:
        assert record['classification'] == 'RUNTIME_OPTIMIZER_DIAGNOSTICS_ONLY'
        assert not record['deployment_proof'] and not record['registration_proof']
        assert not record['recorded_public_address_or_tx']
    assert AUDIT['history_search']['transaction_shape_literals'] == {}


def test_repository_configs_admission_and_gate_are_unchanged():
    for path in ['data/runtime_strategy_config.json', 'data/admission_evidence.csv', 'data/strategies.csv']:
        expected = subprocess.check_output(['git', 'show', AUDIT['accepted_baseline'] + ':' + path], cwd=ROOT)
        assert (ROOT / path).read_bytes() == expected
    configs = json.loads((ROOT / 'data/runtime_strategy_config.json').read_text())
    assert all(r['verification_state'] == 'UNRESOLVED' and r['config_identity'] is None
               for r in configs['records'])
    assert len((ROOT / 'data/admission_evidence.csv').read_text().splitlines()) == 1
    from src.ascend_optimizer.data_loader import load_strategies
    strategies = load_strategies()
    ascend = strategies.loc[strategies.strategy_id == 'ASCEND_STAKE_A0G'].iloc[0]
    assert ascend.allocation_gate == 'CLOSED'


def test_repository_only_baseline_is_idle_and_legacy_is_unchanged():
    from datetime import datetime
    from src.ascend_optimizer.amount_optimizer import run_amount_optimizer
    from src.ascend_optimizer.data_loader import load_strategies, load_snapshots, DEFAULT_DATA_DIR
    from src.ascend_optimizer.live_optimize import optimize_live
    from src.ascend_optimizer.profiles import list_profiles
    strategies = load_strategies()
    snapshots = load_snapshots(strategies, DEFAULT_DATA_DIR / 'demo_strategy_snapshots.csv')
    recorded = {r['profile']: r for r in AUDIT['repository_baseline']['runs']}
    for profile in list_profiles():
        run = run_amount_optimizer(strategies, snapshots, decision_amount=1000, price_usd=1,
                                   horizon_days=90, profile=profile,
                                   as_of=datetime.fromisoformat('2026-10-09T12:00:00+00:00'))
        assert run.to_dict()['recommendation'] == recorded[profile.name.value]['amount_aware']
        assert run.to_dict()['recommendation']['idle_weight'] == 1
        legacy = optimize_live(strategies, snapshots, amount=1000, price_usd=1,
                               horizon_days=90, profile=profile.name.value)
        assert legacy.to_dict()['portfolio'] == recorded[profile.name.value]['legacy_benchmark']
