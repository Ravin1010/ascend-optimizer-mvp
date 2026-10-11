"""Semantic representation boundary; no simulated wrapping or pricing claim."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from src.ascend_optimizer import asset_normalization as n
from src.ascend_optimizer import application_contract as app
from src.ascend_optimizer.data_loader import load_strategies
from src.ascend_optimizer.strategy_state import strategy_state

ROOT = Path(__file__).resolve().parents[1]
BASE = '8749d0ae1150b297dbae996ba0ce9155e13908d6'


@pytest.mark.parametrize('representation', list(n.AssetRepresentation))
def test_same_economic_family(representation):
    assert n.normalize_to_economic_asset(representation) == n.EconomicAssetFamily.ZERO_G


def test_representations_distinct():
    assert n.AssetRepresentation.NATIVE_0G != n.AssetRepresentation.W0G
    assert not n.is_internal_execution_representation('NATIVE_0G')
    assert n.is_internal_execution_representation('W0G')
    assert n.DIRECT_W0G_INPUT == 'KIV_FUTURE'


def test_mainnet_reference_chain_bound_and_source_consistent():
    identity = n.w0g_identity(16661, address=n.MAINNET_W0G.lower())
    assert identity.chain_id == 16661
    assert identity.address == n.MAINNET_W0G
    assert identity.state == 'EXTERNAL_PROTOCOL_REFERENCE'
    rows = load_strategies()
    for sid in ('JAINE_LP_0G_USDC', 'OKU_LP_0G_USDC', 'ASCEND_STAKE_A0G'):
        row = rows[rows.strategy_id == sid].iloc[0]
        assert int(row.execution_chain_id) == identity.chain_id
        assert 'W0G=' + identity.address in row.contract_or_pool_id


def test_galileo_unresolved():
    identity = n.w0g_identity(16602)
    assert identity.address is None and identity.state == 'UNRESOLVED_NOT_VERIFIED'


@pytest.mark.parametrize('chain', [16602, 1, 8453])
def test_cross_network_address_substitution_rejected(chain):
    with pytest.raises(ValueError):
        n.w0g_identity(chain, address=n.MAINNET_W0G)


@pytest.mark.parametrize('chain', [1, 8453, 999])
def test_other_chains_not_registered(chain):
    assert n.w0g_identity(chain).address is None
    assert n.w0g_identity(chain).state == 'UNSUPPORTED'


@pytest.mark.parametrize('chain', [0, -1, '16661', True])
def test_invalid_chain_rejected(chain):
    with pytest.raises(ValueError): n.w0g_identity(chain)


def test_wrong_mainnet_address_rejected():
    with pytest.raises(ValueError): n.w0g_identity(16661, address='0x' + '0'*40)


@pytest.mark.parametrize('unknown', ['a0G', 'st0G', 'ETH', 'USDC.e', 'unknown'])
def test_unknown_representation_fails_closed(unknown):
    with pytest.raises(ValueError): n.normalize_to_economic_asset(unknown)
    with pytest.raises(ValueError): n.is_internal_execution_representation(unknown)


def test_exact_five_universe_and_frontend_ids():
    rows = load_strategies()
    canonical = {row.strategy_id for _, row in rows.iterrows() if strategy_state(row).structural_candidate}
    assert len(canonical) == 5 and 'W0G' not in canonical and 'Idle' not in canonical
    assert set(n.strategy_execution_paths()) == canonical
    source = (ROOT/'frontend/src/lib/final-types.ts').read_text()
    import re
    ids = re.findall(r"'([^']+)'", source.split('export const STRATEGY_IDS = ')[1].split(' as const')[0])
    assert len(ids) == 5 and set(ids) == canonical


@pytest.mark.parametrize('sid', ['JAINE_LP_0G_USDC', 'OKU_LP_0G_USDC', 'ASCEND_STAKE_A0G'])
def test_wrapped_internal_paths(sid):
    path = n.strategy_execution_paths()[sid]
    assert path[0] == '0G' and path[1] == 'W0G' and path[-1] == '0G_vault_idle'
    assert 'unwrap' in path
    if sid.startswith('ASCEND'):
        assert 'SourceCore' in path and 'a0G' in path and 'claim_W0G' in path
    else:
        assert 'USDC.e_to_W0G' in path and 'pooled_V3_NFT' in path


@pytest.mark.parametrize('sid,receipt', [('NATIVE_STAKE_0G','validator_shares'), ('GIMO_STAKE_0G','st0G')])
def test_native_paths_no_wrapped_strategy(sid,receipt):
    path = n.strategy_execution_paths()[sid]
    assert path[0] == '0G' and path[-1] == '0G_vault_idle'
    assert receipt in path and 'W0G' not in path


@pytest.mark.parametrize('profile', ['Conservative','Balanced','Aggressive'])
def test_production_idle_and_five_rows(profile):
    q = app.optimize_request(decision_amount_0g=1000, profile=profile,
                             as_of=datetime(2026,10,10,tzinfo=timezone.utc))
    assert q['recommendation']['idle_weight'] == '1'
    assert set(q['recommendation']['allocation_weights']) == set(n.strategy_execution_paths())
    assert len(q['strategies']) == 5
    assert q['recommendation']['allocation_weights']['ASCEND_STAKE_A0G'] == '0'


def test_frozen_data_results_application_and_frontend_unchanged():
    paths = ['data','results','frontend/src','src/ascend_optimizer/application_contract.py',
             'src/ascend_optimizer/amount_optimizer.py','src/ascend_optimizer/optimizer.py',
             'src/ascend_optimizer/economics_evidence.py','src/ascend_optimizer/risk_stress.py',
             'src/ascend_optimizer/exit_liquidity.py','src/ascend_optimizer/evaluation_policy.py']
    assert not subprocess.check_output(['git','diff',BASE,'4bbe78dc621036e9f6b692af386f458c7b9311f3','--',*paths],cwd=ROOT)


@pytest.mark.parametrize('profile,deadline', [('Conservative',None),('Balanced',8),('Aggressive',15)])
def test_representative_synthetic_requests_unchanged(profile,deadline):
    import types
    accepted = types.ModuleType('src.ascend_optimizer._iteration25_contract')
    accepted.__file__ = str(ROOT/'src/ascend_optimizer/application_contract.py')
    accepted.__package__ = 'src.ascend_optimizer'
    source = subprocess.check_output(['git','show',BASE+':src/ascend_optimizer/application_contract.py'],cwd=ROOT)
    exec(compile(source,accepted.__file__,'exec'),accepted.__dict__)
    args = dict(decision_amount_0g=1000, profile=profile, cash_deadline_days=deadline,
                evidence_mode='SYNTHETIC_EVALUATION_ONLY',
                as_of=datetime(2026,10,10,tzinfo=timezone.utc))
    assert app.optimize_request(**args) == accepted.optimize_request(**args)


def test_no_alternate_user_input_added():
    with pytest.raises(TypeError):
        app.optimize_request(decision_amount_0g=1000, input_asset='W0G')
