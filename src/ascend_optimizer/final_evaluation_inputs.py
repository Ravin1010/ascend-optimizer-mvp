"""In-memory synthetic package adapter. Never writes canonical evidence."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from . import economics_evidence as e, risk_stress as r, lp_range_stress as lp
from .amount_optimizer import AdmissionEvidence, AdmissionState
from .data_loader import load_strategies, load_snapshots, DEFAULT_DATA_DIR


def number(value):
    return format(Decimal(str(value)).normalize(), 'f')


class SyntheticInputs:
    def __init__(self, config, scenario):
        if config['label'] != e.SYNTHETIC or scenario['label'] != e.SYNTHETIC:
            raise ValueError('explicit synthetic package required')
        self.scenario = scenario
        self.package = deepcopy(config['package'])
        changes = scenario['modified_assumptions']
        for name in ('returns', 'fixed_costs'):
            self.package[name].update(changes.get(name, {}))
        for name in ('quote_base', 'quote_slope'):
            if name in changes:
                self.package[name] = changes[name]
        self.strategies = load_strategies()
        # Snapshot route columns are compatibility inputs only. Return/cost/quote
        # economics always come from this explicit package, not demo observations.
        self.snapshots = load_snapshots(self.strategies, DEFAULT_DATA_DIR/'demo_strategy_snapshots.csv')
        self.metadata = {row.strategy_id: row for _, row in self.strategies.iterrows() if row.strategy_id in r.STRATEGIES}
        self.as_of = datetime.fromisoformat(self.package['as_of'])
        self.valuation = dict(price_usd=self.package['price_usd'], evidence_class='MODELLED',
            source_id='SYNTHETIC_ECONOMIC_PACKAGE_V1_VALUATION', source_verified=False,
            observation_timestamp=None, retrieval_timestamp=None, scenario_id=scenario['scenario_id'])
        self.returns, self.costs, self.contexts = [], [], {}
        for sid in r.STRATEGIES:
            common = self.common(sid)
            self.contexts[sid] = {'config_context': common['config_context']}
            if sid not in changes.get('missing_returns', []):
                self.returns.append(common | dict(evidence_id=sid+'-return', metric='gross_apy',
                    value=self.package['returns'][sid], unit='FRACTION_PER_YEAR', fee_basis='NET_OF_PROTOCOL_FEES',
                    fees_embedded=['protocol_fee'], return_components=['base_yield'],
                    incentive_policy='EXCLUDED_NO_REALIZABLE_EVIDENCE', economically_realizable=False,
                    compounding_periods_per_year=365))
            for name in sorted(e.REQUIRED_COSTS[sid]):
                if name == 'entry_gas' and sid in changes.get('missing_costs', []):
                    continue
                value = self.package['fixed_costs'][sid] if name == 'entry_gas' else '0'
                structural = Decimal(value) == 0
                cost_common = common | (dict(evidence_class='STATIC_CONFIG', capture_status='STATIC', source_verified=True, scenario_id=None) if structural else {})
                self.costs.append(cost_common | dict(evidence_id=sid+'-'+name, cost_type=name,
                    structure='STRUCTURAL_ZERO' if structural else 'FIXED_PER_LIFECYCLE', value=value, unit='USD',
                    structural_zero_basis='Explicit synthetic experiment zero; not measured protocol cost' if structural else None,
                    horizon_days=None, quote_id=None))
            if sid in lp.STRATEGIES:
                for direction in ('ENTRY', 'EXIT'):
                    self.contexts[sid][direction] = self.quote_context(sid, direction)
        self.provider = e.EconomicsProvider(returns=self.returns, costs=self.costs, quotes=[],
            mode=e.SYNTHETIC, scenario_id=scenario['scenario_id'], valuation=self.valuation, contexts=self.contexts)
        self.generated = set()

    def common(self, sid):
        return dict(strategy_id=sid, evidence_class='MODELLED', source_id='SYNTHETIC_ECONOMIC_PACKAGE_V1',
            source_role='EVALUATION_ASSUMPTION', source_verified=False, observation_timestamp=None,
            retrieval_timestamp=None, period_start=None, period_end=None, block_number=None, block_hash=None,
            chain_id=16661, amount_0g=None, amount_usd=None, config_context='EVALUATION_ONLY_'+sid,
            capture_status='SYNTHETIC', scenario_id=self.scenario['scenario_id'], notes=e.SYNTHETIC)

    def quote_context(self, sid, direction):
        return dict(path=sid+'_'+direction, market_context='SYNTHETIC_MARKET_'+sid,
            token_in='W0G' if direction == 'ENTRY' else 'USDC.e',
            token_out='USDC.e' if direction == 'ENTRY' else 'W0G',
            fee_tier=3000 if sid == r.JAINE else 500, output_unit='USDC.e' if direction == 'ENTRY' else '0G')

    def economics(self, **kwargs):
        sid = kwargs['strategy'].strategy_id
        amount = Decimal(str(kwargs['canonical_amount_0g']))
        key = (sid, amount)
        if sid in lp.STRATEGIES and key not in self.generated:
            for direction in ('ENTRY', 'EXIT'):
                rate = Decimal(self.package['quote_base']) + Decimal(self.package['quote_slope'])*amount/Decimal(self.package['quote_reference_amount_0g'])
                mismatch = sid in self.scenario['modified_assumptions'].get('quote_mismatch', [])
                q = self.common(sid) | self.quote_context(sid, direction) | dict(
                    quote_id=sid+direction+number(amount), venue='JAINE' if sid == r.JAINE else 'OKU', direction=direction,
                    quoted_output=number(amount*(1-rate)), slippage_rate=number(rate),
                    configuration_binding='SYNTHETIC_SCENARIO', quote_validity_state='UNASSESSED',
                    embedded_cost_types=['lp_swap_fee'], amount_0g=number(amount+Decimal('0.000000000000000001') if mismatch else amount))
                e.validate_record(q, 'quote')
                self.provider.quotes.append(q)
            self.generated.add(key)
        return self.provider(**kwargs)

    def point(self, sid, amount):
        return self.economics(strategy=self.metadata[sid], canonical_amount_0g=number(amount),
            price_usd=self.package['price_usd'], horizon_days=self.scenario['holding_horizon_days'], as_of=self.as_of)

    def admission(self, **kwargs):
        sid = kwargs['strategy'].strategy_id
        rejected = sid in self.scenario['modified_assumptions'].get('admission_rejected', [])
        return AdmissionEvidence(AdmissionState.UNSUPPORTED if rejected else AdmissionState.SUPPORTED,
            sid, kwargs['amount_0g'], 16661, e.SYNTHETIC, 'Explicit modelled point admission; no runtime binding', 'MODELLED',
            capture={'scenario_id':self.scenario['scenario_id'], 'amount_0g':str(kwargs.get('canonical_amount_0g', kwargs['amount_0g']))})

    def apparent_returns(self):
        rates, reasons = {}, {}
        for sid in r.STRATEGIES:
            if sid == r.ASCEND:
                reasons[sid] = ['ASCEND_GATE_CLOSED']; continue
            if sid in self.scenario['modified_assumptions'].get('admission_rejected', []):
                reasons[sid] = ['SYNTHETIC_ADMISSION_REJECTED']; continue
            try:
                normalized = e.normalize_return(self.returns, strategy_id=sid,
                    amount_0g=self.scenario['decision_amount_0g'], price_usd=self.package['price_usd'],
                    horizon_days=self.scenario['holding_horizon_days'], mode=e.SYNTHETIC,
                    scenario_id=self.scenario['scenario_id'], config_context=self.contexts[sid]['config_context'], as_of=self.as_of)
                rates[sid] = normalized['base_apy']
            except e.EconomicsError as exc:
                reasons[sid] = [str(exc)]
        return rates, reasons
