"""SYNTHETIC_EVALUATION_ONLY: no public pool/route evidence or market captures."""
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal, ROUND_DOWN, ROUND_UP, localcontext
import json
from pathlib import Path

import pytest

from src.ascend_optimizer import lp_range_stress as m
from src.ascend_optimizer.runtime_config import load_runtime_configs
from src.ascend_optimizer.data_loader import DEFAULT_DATA_DIR, SchemaValidationError, load_strategies
from tools.economics_preflight import repository_baseline


def seal(c):
    c['sqrt_lower'] = m.tick_sqrt(c['tick_lower'])
    c['sqrt_upper'] = m.tick_sqrt(c['tick_upper'])
    c['target_usdc_bps'] = m.implied_target_bps(c)
    c['config_id'] = m.config_identity(c)
    return c


def run(c, scenario=None, notional='1000'):
    return m.evaluate(c, scenario or m.scenarios()[0], notional,
                      mode=m.LABEL, expected_config_id=c['config_id'])


def economic_from_pool(c, q):
    with localcontext() as ctx:
        ctx.prec = m.PRECISION
        w_first = c['token0'] == c['w0g']
        scale = Decimal(10) ** ((c['usdce_decimals']-c['w0g_decimals']) if w_first
                               else (c['w0g_decimals']-c['usdce_decimals']))
        whole = q / scale
        return whole if w_first else 1/whole


def test_exact_two_independent_synthetic_configs():
    j,o = m.load_configs()
    assert {j['strategy_id'],o['strategy_id']} == set(m.STRATEGIES)
    assert j['venue']=='JAINE' and j['router_mode']=='V1'
    assert o['venue']=='OKU' and o['router_mode']=='ROUTER02'
    for field in ('config_id','venue','pool_context','fee_tier','tick_spacing','tick_lower','tick_upper',
                  'target_usdc_bps','reference_price','router_mode','token0','token1'):
        assert j[field] != o[field]
    assert all(c['chain_id']==16661 and c['label']==m.LABEL and c['evidence_class']=='MODELLED' for c in (j,o))
    assert 'W0G' not in m.STRATEGIES


@pytest.mark.parametrize('field,value', [
    ('strategy_id','NATIVE_STAKE_0G'),('strategy_id','W0G'),('chain_id',16602),('chain_id',1),('chain_id',8453),
    ('chain_role','EXECUTION'),('label','LIVE'),('evidence_class','LIVE_OBSERVED'),('router_mode','ROUTER02'),
    ('venue','OKU'),('fee_tier',0),('fee_tier',1000000),('tick_spacing',0),('tick_lower',-277801),
    ('tick_upper',-277800),('tick_upper',-277860),('sqrt_lower','0'),('sqrt_lower','NaN'),
    ('sqrt_upper','Infinity'),('sqrt_upper','0.00000001'),('target_usdc_bps',10001),('target_usdc_bps',-1),
    ('target_usdc_bps',5000),('reference_price','0'),('reference_price','NaN'),('reference_price',1.0),
    ('price_orientation','W0G_PER_USDC.e'),('pool_price_orientation','WHOLE_TOKEN1_PER_TOKEN0'),
    ('config_id','wrong'),('token0','0x0000000000000000000000000000000000000000'),
])
def test_invalid_configuration_rejected(field,value):
    c=deepcopy(m.load_configs()[0]);c[field]=value
    with pytest.raises(m.LPStressError): m.validate_config(c)


def test_identical_tokens_and_mismatched_bounds_rejected():
    c=deepcopy(m.load_configs()[0]);c['usdce']=c['w0g'];c['token1']=c['w0g']
    with pytest.raises(m.LPStressError): m.validate_config(c)
    c=deepcopy(m.load_configs()[0]);c['sqrt_lower']=m.tick_sqrt(c['tick_lower']+1)
    with pytest.raises(m.LPStressError,match='inconsistent'): m.validate_config(c)


@pytest.mark.parametrize('field,value', [('reference_price','1.01'),('fee_tier',500),('tick_lower',-277860),
                                        ('price_orientation','W0G_PER_USDC.e'),('target_usdc_bps',5000)])
def test_identity_covers_economic_parameters(field,value):
    c=deepcopy(m.load_configs()[0]); identity=c['config_id'];c[field]=value
    assert m.config_identity(c) != identity


@pytest.mark.parametrize('index',[0,1])
def test_below_inside_above_atomic_inventory_and_boundaries(index):
    c=m.load_configs()[index]
    a,b=Decimal(c['sqrt_lower']),Decimal(c['sqrt_upper'])
    prices=[economic_from_pool(c,a*a/2),economic_from_pool(c,a*a),
            Decimal(c['reference_price']),economic_from_pool(c,b*b),economic_from_pool(c,b*b*2)]
    with localcontext() as ctx:
        ctx.prec=m.PRECISION
        prices[1]=economic_from_pool(c,a*a)
        prices[3]=economic_from_pool(c,b*b)
    inv=[m.inventory(c,Decimal(1),p) for p in prices]
    assert inv[1].range_state=='BELOW_RANGE'
    assert inv[3].range_state=='ABOVE_RANGE'
    token0=lambda i: i.w0g if c['token0']==c['w0g'] else i.usdce
    token1=lambda i: i.usdce if c['token0']==c['w0g'] else i.w0g
    assert inv[0].range_state=='BELOW_RANGE' and token1(inv[0])==0 and token0(inv[0])>0
    assert inv[2].range_state=='IN_RANGE' and inv[2].w0g>0 and inv[2].usdce>0
    assert inv[4].range_state=='ABOVE_RANGE' and token0(inv[4])==0 and token1(inv[4])>0
    # Boundary inventories converge continuously even at rounding edges.
    assert float(token0(inv[1])) == pytest.approx(float(token0(inv[0])))
    assert float(token1(inv[1])) == pytest.approx(0,abs=1e-25)
    assert float(token1(inv[3])) == pytest.approx(float(token1(inv[4])))
    assert float(token0(inv[3])) == pytest.approx(0,abs=1e-25)
    for bound in (a,b):
        left=m.inventory(c,Decimal(1),economic_from_pool(c,bound*bound*Decimal('0.999999999999')))
        right=m.inventory(c,Decimal(1),economic_from_pool(c,bound*bound*Decimal('1.000000000001')))
        assert float(left.w0g)==pytest.approx(float(right.w0g),abs=1e-24)
        assert float(left.usdce)==pytest.approx(float(right.usdce),abs=1e-18)


@pytest.mark.parametrize('index',[0,1])
@pytest.mark.parametrize('scenario',m.scenarios())
def test_shock_decomposition_hodl_and_loss_definitions(index,scenario):
    c=m.load_configs()[index];r=run(c,scenario);d=lambda k: Decimal(getattr(r,k))
    assert d('shocked_price') == Decimal(c['reference_price'])*(1+Decimal(scenario['shock']))
    assert d('shocked_price')>0
    assert float(d('initial_value'))==pytest.approx(1000)
    assert float(d('hodl_value'))==pytest.approx(float(d('initial_w0g')*d('shocked_price')+d('initial_usdce')))
    assert float(d('lp_value'))==pytest.approx(float(d('w0g')*d('shocked_price')+d('usdce')))
    assert d('impermanent_loss_fraction')<=0
    assert float(d('impermanent_loss_fraction'))==pytest.approx(float(d('lp_value')/d('hodl_value')-1))
    assert float(d('absolute_lp_loss'))==pytest.approx(max(0,float(1-d('lp_value')/d('initial_value'))))
    assert float(d('hodl_market_loss'))==pytest.approx(max(0,float(1-d('hodl_value')/d('initial_value'))))
    assert float(d('lp_value_change'))==pytest.approx(float(d('market_value_change')+d('rebalancing_value_change')))
    assert r.evidence_class=='MODELLED' and r.label==m.LABEL
    assert not r.execution_effects_included and not r.fee_income_included
    if Decimal(scenario['shock'])>0:
        assert d('hodl_market_loss')==0 and d('absolute_lp_loss')==0
        assert d('impermanent_loss_fraction')<0  # IL is not absolute or market loss.


@pytest.mark.parametrize('index',[0,1])
def test_deterministic_normalization_and_zero_shock(index):
    c=m.load_configs()[index]; s=m.scenarios(include_reference=True)[-1]
    r=run(c,s);assert r==run(c,s)
    assert float(r.impermanent_loss_fraction)==pytest.approx(0,abs=1e-55)
    assert float(r.initial_value)==pytest.approx(1000)
    bigger=run(c,s,'2000')
    assert float(bigger.initial_w0g)==pytest.approx(2*float(r.initial_w0g))
    assert float(bigger.initial_usdce)==pytest.approx(2*float(r.initial_usdce))


@pytest.mark.parametrize('scenario',m.scenarios())
def test_token_order_inversion_economic_equivalence(scenario):
    c=m.load_configs()[0]; inverted=deepcopy(c)
    inverted['token0'],inverted['token1']=c['token1'],c['token0']
    inverted['tick_lower'],inverted['tick_upper']=-c['tick_upper'],-c['tick_lower']
    seal(inverted);m.validate_config(inverted)
    a,b=run(c,scenario),run(inverted,scenario)
    for field in ('shocked_price','initial_w0g','initial_usdce','w0g','usdce','lp_value','hodl_value','impermanent_loss_fraction'):
        assert float(getattr(a,field))==pytest.approx(float(getattr(b,field)),abs=1e-12)
    assert float(a.pool_math_price)*float(b.pool_math_price)==pytest.approx(1)


@pytest.mark.parametrize('lo,hi',[(-276360,-276300),(-288000,-264000)])
def test_narrow_and_wide_ranges(lo,hi):
    c=deepcopy(m.load_configs()[0]);c['tick_lower'],c['tick_upper']=lo,hi;seal(c)
    for s in m.scenarios():
        r=run(c,s)
        assert Decimal(r.lp_value)>0 and Decimal(r.w0g)>=0 and Decimal(r.usdce)>=0


def test_synthetic_mode_config_and_scenario_binding_required():
    c=m.load_configs()[0];s=m.scenarios()[0]
    with pytest.raises(m.LPStressError): m.evaluate(c,s,'1000',mode='PRODUCTION',expected_config_id=c['config_id'])
    with pytest.raises(m.LPStressError): m.evaluate(c,s,'1000',mode=m.LABEL,expected_config_id='other')
    for changes in ({'shock':'0.2'},{'scenario_id':'OTHER'},{'label':'LIVE'}):
        with pytest.raises(m.LPStressError): run(c,s|changes)
    for n in ('0','-1','NaN','Infinity'):
        with pytest.raises(m.LPStressError): run(c,s,n)


def test_no_fee_or_execution_effects_or_legacy_dependency():
    c=m.load_configs()[0];r=run(c);changed=deepcopy(c);changed['fee_tier']=500
    changed['config_id']=m.config_identity(changed);r2=run(changed)
    assert r.lp_value==r2.lp_value
    source=Path(m.__file__).read_text()
    assert 'lp_stress_loss_20pct' not in source and 'lp_execution' not in source


def test_reproducible_committed_artifact():
    path=DEFAULT_DATA_DIR.parent/'results/lp_range_stress_iteration20.json'
    assert json.loads(path.read_text())==m.replay()


def test_configs_not_runtime_evidence_and_frozen_baseline():
    with pytest.raises(SchemaValidationError): load_runtime_configs(DEFAULT_DATA_DIR/'lp_evaluation_config.json')
    assert all(c['verification_state']=='UNRESOLVED' for c in load_runtime_configs())
    assert len((DEFAULT_DATA_DIR/'admission_evidence.csv').read_text().splitlines())==1
    for filename in ('strategy_return_evidence.json','lp_quote_evidence.json','lifecycle_cost_evidence.json'):
        assert json.loads((DEFAULT_DATA_DIR/filename).read_text())['records']==[]
    s=load_strategies(); assert s.loc[s.strategy_id=='ASCEND_STAKE_A0G','allocation_gate'].item()=='CLOSED'
    assert all(r['idle_weight']==1 and r['positive_selected_count']==0 for r in repository_baseline()['runs'])


def test_local_precision_independent_of_ambient_context():
    c=m.load_configs()[1];expected=run(c)
    with localcontext() as ctx:
        ctx.prec=12
        ctx.rounding=ROUND_DOWN
        assert run(c)==expected
        low=m.pool_price(c,Decimal('1.32'))
    with localcontext() as ctx:
        ctx.prec=100
        ctx.rounding=ROUND_UP
        assert run(c)==expected
        assert m.pool_price(c,Decimal('1.32'))==low


def test_legacy_proxy_documented_compatibility_only():
    report=(DEFAULT_DATA_DIR.parent/'docs/lp_range_stress_iteration20.md').read_text()
    assert 'lp_stress_loss_20pct' in report and 'legacy compatibility only' in report
    assert 'resolve_runtime_lp_exposures' in report and 'evaluate_candidate' in report


@pytest.mark.parametrize('price,w,u,state', [
    ('0.25','6','0','BELOW_RANGE'),
    ('2.25','2','6','IN_RANGE'),
    ('9','0','12','ABOVE_RANGE'),
])
def test_hand_calculated_inventory_anchors(price,w,u,state):
    # Independent analytical anchor: a=1, b=2, L=12, whole-token scales.
    # Deliberately not a route configuration; tests the inventory formula only.
    c=deepcopy(m.load_configs()[0]);c.update(sqrt_lower='1',sqrt_upper='2',w0g_decimals=0,usdce_decimals=0)
    i=m.inventory(c,Decimal(12),Decimal(price))
    assert i==m.Inventory(Decimal(w),Decimal(u),state)
