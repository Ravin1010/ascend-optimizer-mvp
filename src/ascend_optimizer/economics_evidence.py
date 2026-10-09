"""Deployment-independent economics. No acquisition, admission or risk inference.

Canonical records never default missing numbers/times to zero/now. Policy tables
are empty until a source-specific observation budget is justified. Test policies
and scenarios are caller-supplied, never written into canonical evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from .data_loader import MVP_STRATEGY_IDS, DEFAULT_DATA_DIR

PRODUCTION = "PRODUCTION"
SYNTHETIC = "SYNTHETIC_EVALUATION_ONLY"
HISTORICAL = "HISTORICAL_EVALUATION_ONLY"
LP_IDS = {"JAINE_LP_0G_USDC", "OKU_LP_0G_USDC"}
RETURN_CLASSES = {"LIVE_OBSERVED", "LIVE_DERIVED", "HISTORICAL", "MODELLED", "STATIC_CONFIG", "MISSING"}
COST_CLASSES = {"LIVE_OBSERVED", "QUOTE_DERIVED", "HISTORICAL", "MODELLED", "STATIC_CONFIG", "MISSING"}
DEFAULT_ECONOMIC_POLICIES = {}  # Deliberately no defensible numeric source TTL yet.
QUOTE_CLASSES = RETURN_CLASSES - {"STATIC_CONFIG"}
COMMON = {"strategy_id", "evidence_class", "source_id", "source_role", "source_verified",
          "observation_timestamp", "retrieval_timestamp", "period_start", "period_end",
          "block_number", "block_hash", "chain_id", "amount_0g", "amount_usd",
          "config_context", "capture_status", "scenario_id", "notes"}
RETURN_FIELDS = COMMON | {"evidence_id", "metric", "value", "unit", "fee_basis",
                         "fees_embedded", "return_components", "incentive_policy",
                         "economically_realizable", "compounding_periods_per_year"}
QUOTE_FIELDS = COMMON | {"quote_id", "venue", "direction", "path", "token_in", "token_out",
                        "market_context", "fee_tier", "quoted_output", "output_unit",
                        "slippage_rate", "configuration_binding", "quote_validity_state",
                        "embedded_cost_types"}
COST_FIELDS = COMMON | {"evidence_id", "cost_type", "structure", "value", "unit",
                       "structural_zero_basis", "horizon_days", "quote_id"}
RETURN_METRICS = {
    "exchange_rate": "0G_PER_SHARE", "gross_apy": "FRACTION_PER_YEAR",
    "gross_apr": "FRACTION_PER_YEAR", "lp_fee_apr": "FRACTION_PER_YEAR",
    "validator_yield_benchmark": "FRACTION_PER_YEAR", "holding_period_return": "FRACTION",
    "protocol_fee_rate": "FRACTION", "commission": "FRACTION", "fee_rate": "FRACTION",
    "incentive_apy": "FRACTION_PER_YEAR", "realized_incentive": "USD", "points": "NON_FINANCIAL",
}
BASE_METRICS = {"exchange_rate", "gross_apy", "gross_apr", "lp_fee_apr",
                "validator_yield_benchmark", "holding_period_return"}
STRUCTURES = {"FIXED_PER_LIFECYCLE", "FIXED_PER_ENTRY", "FIXED_PER_EXIT", "VARIABLE_BPS",
              "AMOUNT_DEPENDENT_QUOTE", "STRUCTURAL_ZERO"}
# Explicit conservative lifecycle coverage; costs may be collapsed only into a
# documented lifecycle aggregate (not mixed with individual lines).
REQUIRED_COSTS = {
    sid: {"entry_gas", "exit_gas", "protocol_entry_fee", "protocol_exit_fee", "bridge_cost"}
    | ({"claim_gas"} if sid not in LP_IDS else set())
    | ({"native_withdrawal_fee"} if sid == "NATIVE_STAKE_0G" else set())
    for sid in MVP_STRATEGY_IDS
}


class EconomicsError(ValueError):
    pass


def decimal(value, *, positive=False, nonnegative=False):
    if value is None or isinstance(value, bool):
        raise EconomicsError("missing/invalid decimal")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise EconomicsError("invalid decimal") from exc
    if not d.is_finite() or (positive and d <= 0) or (nonnegative and d < 0):
        raise EconomicsError("invalid decimal domain")
    return d


def timestamp(value):
    if not isinstance(value, (str, datetime)):
        raise EconomicsError("explicit timezone-aware timestamp required")
    try:
        t = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EconomicsError("invalid timestamp") from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise EconomicsError("explicit timezone-aware timestamp required")
    return t


def fingerprint(record):
    return "sha256:" + sha256(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def growth(base, exponent):
    try:
        if not isfinite(base) or base <= 0 or not isfinite(exponent):
            raise EconomicsError("INVALID_GROWTH_DOMAIN")
        result = base ** exponent
        if not isfinite(result):
            raise EconomicsError("NONFINITE_RETURN")
        return result - 1
    except OverflowError as exc:
        raise EconomicsError("NONFINITE_RETURN") from exc


def validate_record(record, kind):
    fields, classes = {"return": (RETURN_FIELDS, RETURN_CLASSES), "quote": (QUOTE_FIELDS, QUOTE_CLASSES),
                       "cost": (COST_FIELDS, COST_CLASSES)}[kind]
    if not isinstance(record, dict) or set(record) != fields:
        raise EconomicsError(f"{kind} schema requires exact fields")
    r = record
    key = "quote_id" if kind == "quote" else "evidence_id"
    if not isinstance(r[key], str) or not r[key] or r["strategy_id"] not in MVP_STRATEGY_IDS:
        raise EconomicsError("evidence identity/strategy invalid")
    if r["evidence_class"] not in classes or type(r["source_verified"]) is not bool:
        raise EconomicsError("evidence class/source verification invalid")
    if r["capture_status"] not in {"CAPTURED", "STATIC", "SYNTHETIC", "MISSING"}:
        raise EconomicsError("capture status invalid")
    for field in ("source_id", "source_role", "notes"):
        if not isinstance(r[field], str):
            raise EconomicsError("text metadata invalid")
    for field in ("observation_timestamp", "retrieval_timestamp", "period_start", "period_end"):
        if r[field] is not None:
            timestamp(r[field])
    if r["observation_timestamp"] is not None and r["retrieval_timestamp"] is not None:
        if timestamp(r["retrieval_timestamp"]) < timestamp(r["observation_timestamp"]):
            raise EconomicsError("retrieval precedes observation")
    if (r["period_start"] is None) != (r["period_end"] is None):
        raise EconomicsError("period needs both endpoints")
    if r["period_start"] is not None and timestamp(r["period_start"]) >= timestamp(r["period_end"]):
        raise EconomicsError("period must be ordered")
    if r["chain_id"] is not None and (type(r["chain_id"]) is not int or r["chain_id"] != 16661):
        raise EconomicsError("strategy economics execution chain must be 16661")
    if r["block_number"] is not None and (type(r["block_number"]) is not int or r["block_number"] < 0):
        raise EconomicsError("invalid block number")
    if r["block_hash"] is not None:
        import re
        if not isinstance(r["block_hash"], str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", r["block_hash"]):
            raise EconomicsError("invalid block hash")
    if r["config_context"] is not None and not isinstance(r["config_context"], str):
        raise EconomicsError("context must be explicit string/null")
    for field in ("amount_0g", "amount_usd"):
        if r[field] is not None:
            decimal(r[field], positive=True)
    cls = r["evidence_class"]
    if cls == "MISSING":
        value = r["quoted_output"] if kind == "quote" else r["value"]
        if value is not None or r["capture_status"] != "MISSING":
            raise EconomicsError("missing evidence cannot carry a number")
    else:
        if not r["source_id"] or not r["source_role"]:
            raise EconomicsError("nonmissing evidence requires provenance")
        if cls == "MODELLED":
            if r["capture_status"] != "SYNTHETIC" or not isinstance(r["scenario_id"], str) or not r["scenario_id"]:
                raise EconomicsError("modelled evidence requires explicit scenario")
        elif cls == "STATIC_CONFIG":
            if r["capture_status"] != "STATIC":
                raise EconomicsError("static evidence requires static capture")
        else:
            if r["capture_status"] != "CAPTURED" or r["observation_timestamp"] is None or r["retrieval_timestamp"] is None:
                raise EconomicsError("observational evidence requires separate actual timestamps")
    if kind == "return":
        if r["metric"] not in RETURN_METRICS or r["unit"] != RETURN_METRICS[r["metric"]]:
            raise EconomicsError("return metric/unit invalid")
        if cls != "MISSING":
            value = decimal(r["value"])
            if r["metric"] == "exchange_rate" and value <= 0:
                raise EconomicsError("exchange rate must be positive")
            if r["metric"] in {"protocol_fee_rate", "commission", "fee_rate"} and not 0 <= value <= 1:
                raise EconomicsError("fee fraction invalid")
            if r["metric"] in BASE_METRICS - {"exchange_rate", "gross_apr", "lp_fee_apr"} and value <= -1:
                raise EconomicsError("return must exceed -1")
        if r["fee_basis"] not in {"NET_OF_PROTOCOL_FEES", "GROSS_BEFORE_FEES", "UNKNOWN"}:
            raise EconomicsError("fee basis invalid")
        if any(not isinstance(r[k], list) or any(not isinstance(x, str) or not x for x in r[k]) or len(set(r[k])) != len(r[k]) for k in ("fees_embedded", "return_components")):
            raise EconomicsError("embedded fee/return lists required")
        if r["incentive_policy"] not in {"EXCLUDED_NO_REALIZABLE_EVIDENCE", "REQUIRE_REALIZABLE_EVIDENCE"}:
            raise EconomicsError("incentive policy required")
        if type(r["economically_realizable"]) is not bool:
            raise EconomicsError("realizability must be explicit")
        if type(r["compounding_periods_per_year"]) is not int or r["compounding_periods_per_year"] <= 0:
            raise EconomicsError("compounding convention required")
    elif kind == "quote":
        if r["strategy_id"] not in LP_IDS or r["direction"] not in {"ENTRY", "EXIT"}:
            raise EconomicsError("LP quote strategy/direction invalid")
        if r["venue"] != ("JAINE" if r["strategy_id"] == "JAINE_LP_0G_USDC" else "OKU"):
            raise EconomicsError("venue mismatch")
        if r["configuration_binding"] not in {"UNBOUND_TO_DEPLOYED_ROUTE", "SYNTHETIC_SCENARIO", "BOUND_TO_VERIFIED_RUNTIME"}:
            raise EconomicsError("quote binding invalid")
        if r["quote_validity_state"] != "UNASSESSED":
            raise EconomicsError("persisted quote must not self-certify validity")
        if not isinstance(r["embedded_cost_types"], list) or any(not isinstance(x, str) or not x for x in r["embedded_cost_types"]):
            raise EconomicsError("quote embedded cost coverage required")
        if cls != "MISSING":
            if r["chain_id"] != 16661:
                raise EconomicsError("LP quote chain required")
            if "lp_swap_fee" not in r["embedded_cost_types"]:
                raise EconomicsError("quote loss must explicitly cover pool swap fee")
            decimal(r["amount_0g"], positive=True)
            decimal(r["quoted_output"], positive=True)
            if not 0 <= decimal(r["slippage_rate"]) <= 1:
                raise EconomicsError("quote slippage fraction invalid")
            for field in ("path", "token_in", "token_out", "market_context", "output_unit"):
                if not isinstance(r[field], str) or not r[field]:
                    raise EconomicsError("quote context incomplete")
            if type(r["fee_tier"]) is not int or not 0 < r["fee_tier"] < 2**24:
                raise EconomicsError("quote fee tier invalid")
            if cls == "MODELLED" and r["configuration_binding"] != "SYNTHETIC_SCENARIO":
                raise EconomicsError("synthetic quote cannot claim runtime binding")
    else:
        if r["structure"] not in STRUCTURES or r["unit"] not in {"USD", "0G", "BPS"}:
            raise EconomicsError("cost structure/unit invalid")
        if not isinstance(r["cost_type"], str) or not r["cost_type"]:
            raise EconomicsError("cost type required")
        if r["horizon_days"] is not None:
            decimal(r["horizon_days"], positive=True)
        if cls != "MISSING":
            value = decimal(r["value"], nonnegative=True)
            if r["structure"] == "STRUCTURAL_ZERO":
                if value != 0 or cls != "STATIC_CONFIG" or not r["structural_zero_basis"] or not r["source_verified"]:
                    raise EconomicsError("structural zero needs explicit static source/basis")
            elif value == 0:
                raise EconomicsError("zero requires structural zero evidence")
            if (r["structure"] == "VARIABLE_BPS") != (r["unit"] == "BPS"):
                raise EconomicsError("variable cost needs BPS; fixed/quoted cost needs monetary unit")
            if r["structure"] == "AMOUNT_DEPENDENT_QUOTE" and r["amount_0g"] is None:
                raise EconomicsError("amount-dependent cost needs exact amount")
            if cls == "QUOTE_DERIVED" and not r["quote_id"]:
                raise EconomicsError("quote-derived cost needs quote identity")
    return r


def load_evidence(path, kind):
    obj = json.loads(Path(path).read_text())
    if set(obj) != {"schema_version", "kind", "records"} or obj["schema_version"] != "ECONOMICS_EVIDENCE_V1" or obj["kind"] != kind or not isinstance(obj["records"], list):
        raise EconomicsError("invalid evidence envelope")
    records = tuple(validate_record(r, kind) for r in obj["records"])
    key = "quote_id" if kind == "quote" else "evidence_id"
    if len({r[key] for r in records}) != len(records):
        raise EconomicsError("duplicate evidence identity")
    return records


def qualify(record, kind, *, mode, scenario_id, as_of, policies):
    """Return independent economic freshness qualification, not admission."""
    validate_record(record, kind)
    if mode not in {PRODUCTION, SYNTHETIC, HISTORICAL}:
        raise EconomicsError("explicit economics mode invalid")
    cls = record["evidence_class"]
    if cls == "MISSING":
        return "MISSING"
    if cls == "MODELLED":
        return "VALID" if mode == SYNTHETIC and scenario_id and scenario_id == record["scenario_id"] else "SYNTHETIC_MODE_REQUIRED"
    if cls == "HISTORICAL":
        if not record["source_verified"]:
            return "SOURCE_UNVERIFIED"
        if timestamp(record["retrieval_timestamp"]) > timestamp(as_of):
            return "FUTURE_TIMESTAMP"
        return "VALID" if mode in {SYNTHETIC, HISTORICAL} else "HISTORICAL_NOT_CURRENT"
    if not record["source_verified"]:
        return "SOURCE_UNVERIFIED"
    if cls == "STATIC_CONFIG":
        return "VALID"
    metric = record["metric"] if kind == "return" else record["direction"] if kind == "quote" else record["cost_type"]
    policy = policies.get((kind, record["source_id"], metric))
    if not policy:
        return "POLICY_UNDEFINED" if kind == "quote" else "NO_VALID_POLICY"
    if set(policy) != {"max_age_seconds", "rationale"} or not policy["rationale"]:
        raise EconomicsError("freshness policy requires explicit rationale")
    ttl = decimal(policy["max_age_seconds"], positive=True)
    now, observed = timestamp(as_of), timestamp(record["observation_timestamp"])
    if timestamp(record["retrieval_timestamp"]) > now or observed > now:
        return "FUTURE_TIMESTAMP"
    return "VALID" if Decimal(str((now - observed).total_seconds())) <= ttl else "STALE"


def _records_context(records, amount, config_context, usd):
    for r in records:
        if r["amount_0g"] is not None and decimal(r["amount_0g"]) != amount:
            raise EconomicsError("AMOUNT_MISMATCH")
        if r["amount_usd"] is not None and decimal(r["amount_usd"]) != usd:
            raise EconomicsError("VALUATION_AMOUNT_MISMATCH")
        if r["config_context"] is not None and r["config_context"] != config_context:
            raise EconomicsError("CONTEXT_MISMATCH")


def normalize_return(records, *, strategy_id, amount_0g, price_usd, horizon_days,
                     mode=PRODUCTION, scenario_id=None, config_context=None, as_of=None, policies=None):
    amount = decimal(amount_0g, positive=True)
    price = decimal(price_usd, positive=True)
    horizon = float(decimal(horizon_days, positive=True))
    rows = [validate_record(r, "return") for r in records if r["strategy_id"] == strategy_id]
    base = [r for r in rows if r["metric"] in BASE_METRICS]
    if not base:
        raise EconomicsError("MISSING_RETURN")
    # Exactly one primitive basis, or one exchange-rate history. No addition of
    # standalone embedded Symbiotic yield to the SourceCore exchange-rate return.
    if len({r["metric"] for r in base}) != 1 or (base[0]["metric"] != "exchange_rate" and len(base) != 1):
        raise EconomicsError("AMBIGUOUS_OR_DOUBLE_COUNTED_RETURN")
    _records_context(rows, amount, config_context, amount * price)
    used = base + [r for r in rows if r["metric"] in {"protocol_fee_rate", "commission", "fee_rate"}]
    incentive_rows = [r for r in rows if r["metric"] in {"incentive_apy", "realized_incentive"}]
    principal = float(amount * price)
    first = base[0]
    if first["incentive_policy"] == "REQUIRE_REALIZABLE_EVIDENCE":
        if not incentive_rows or any(not r["economically_realizable"] for r in incentive_rows):
            raise EconomicsError("MISSING_REALIZABLE_INCENTIVE")
        used += incentive_rows
    for r in used:
        state = qualify(r, "return", mode=mode, scenario_id=scenario_id, as_of=as_of, policies=policies or {})
        if state != "VALID":
            raise EconomicsError(state + ":" + r["evidence_id"])
    # Configured-validator identity applies to the return basis, not separate
    # commission/fee metadata, which still passes qualification above.
    if mode == PRODUCTION and strategy_id == "NATIVE_STAKE_0G":
        for r in base:
            if r["metric"] == "validator_yield_benchmark" or r["source_role"] != "CONFIGURED_VALIDATOR_RETURN":
                raise EconomicsError("NATIVE_BENCHMARK_NOT_CONFIGURED_ROUTE")
    if first["fee_basis"] == "UNKNOWN" or any(r["fee_basis"] != first["fee_basis"] for r in base):
        raise EconomicsError("FEE_BASIS_UNRESOLVED")
    if mode == PRODUCTION and any(r["evidence_class"] == "STATIC_CONFIG" for r in base):
        raise EconomicsError("STATIC_RETURN_NOT_CURRENT")
    metric = first["metric"]
    method = metric
    if metric == "exchange_rate":
        if len(base) < 2:
            raise EconomicsError("INSUFFICIENT_RATE_HISTORY")
        base = sorted(base, key=lambda r: timestamp(r["observation_timestamp"]))
        if any(r["source_id"] != first["source_id"] or r["config_context"] != first["config_context"] or r["fees_embedded"] != first["fees_embedded"] or r["return_components"] != first["return_components"] for r in base):
            raise EconomicsError("INCOMPATIBLE_RATE_HISTORY")
        days = (timestamp(base[-1]["observation_timestamp"]) - timestamp(base[0]["observation_timestamp"])).total_seconds() / 86400
        if days <= 0:
            raise EconomicsError("INSUFFICIENT_RATE_HISTORY")
        annual = growth(float(decimal(base[-1]["value"]) / decimal(base[0]["value"])), 365 / days)
        if strategy_id in {"GIMO_STAKE_0G", "ASCEND_STAKE_A0G"} and first["fee_basis"] != "NET_OF_PROTOCOL_FEES":
            raise EconomicsError("EXCHANGE_RATE_FEE_BASIS_UNRESOLVED")
        method = "ENDPOINT_RATE_GROWTH_ANNUALIZED; extrapolation assumption"
    elif metric in {"gross_apr", "lp_fee_apr"}:
        n = first["compounding_periods_per_year"]
        if 1 + float(decimal(first["value"])) / n <= 0:
            raise EconomicsError("INVALID_APR_DOMAIN")
        annual = growth(1 + float(decimal(first["value"])) / n, n)
    elif metric == "holding_period_return":
        days = (timestamp(first["period_end"]) - timestamp(first["period_start"])).total_seconds() / 86400
        annual = growth(1 + float(decimal(first["value"])), 365 / days)
        method = "HOLDING_PERIOD_ANNUALIZATION; extrapolation assumption"
    else:
        annual = float(decimal(first["value"]))
    incentive_annual = 0.0
    realized = 0.0
    if first["incentive_policy"] == "REQUIRE_REALIZABLE_EVIDENCE":
        if len(incentive_rows) != 1:
            raise EconomicsError("AMBIGUOUS_INCENTIVE_STREAM")
        r = incentive_rows[0]
        if set(r["return_components"]) & set(first["return_components"]):
            raise EconomicsError("EMBEDDED_RETURN_DOUBLE_COUNT")
        if r["metric"] == "incentive_apy":
            incentive_annual = float(decimal(r["value"], nonnegative=True))
        else:
            if r["amount_0g"] is None or r["period_start"] is None:
                raise EconomicsError("REALIZED_INCENTIVE_REQUIRES_AMOUNT_AND_HORIZON")
            days = (timestamp(r["period_end"]) - timestamp(r["period_start"])).total_seconds() / 86400
            if days != horizon:
                raise EconomicsError("INCENTIVE_HORIZON_MISMATCH")
            realized = float(decimal(r["value"], nonnegative=True))
    income = principal * growth(1 + annual + incentive_annual, horizon / 365) + realized
    fees = [r for r in used if r["metric"] in {"protocol_fee_rate", "commission", "fee_rate"}]
    if first["fee_basis"] == "GROSS_BEFORE_FEES" and len(fees) != 1:
        raise EconomicsError("MISSING_OR_AMBIGUOUS_PROTOCOL_FEE")
    deduction = max(0, income) * float(decimal(fees[0]["value"])) if first["fee_basis"] == "GROSS_BEFORE_FEES" else 0.0
    if not all(isfinite(v) for v in (annual, income, deduction)):
        raise EconomicsError("NONFINITE_RETURN")
    classes = {r["evidence_class"] for r in used}
    derived_class = ("MODELLED" if "MODELLED" in classes else "HISTORICAL" if "HISTORICAL" in classes
                     else "LIVE_DERIVED" if classes & {"LIVE_OBSERVED", "LIVE_DERIVED"} else "STATIC_CONFIG")
    return {"strategy_id": strategy_id, "horizon_days": horizon, "base_apy": annual,
            "expected_return_rate": income / principal, "expected_gross_income_usd": income,
            "additional_fee_usd": deduction, "income_after_protocol_fee_usd": income - deduction,
            "fees_already_embedded": first["fees_embedded"], "fee_basis": first["fee_basis"],
            "incentive_apy": incentive_annual, "realized_incentive_usd": realized,
            "incentive_policy": first["incentive_policy"], "excluded_nonfinancial_points": [r["evidence_id"] for r in rows if r["metric"] == "points"],
            "evidence_class": derived_class, "evidence_classes": sorted(classes), "provenance": deepcopy(used),
            "normalization_method": method, "qualification": "VALID", "mode": mode,
            "reasons": ["Economic qualification does not establish admission, risk or public deployment"]}


def assess_quote(record, *, strategy_id, amount_0g, direction, path, market_context,
                 config_context, mode=PRODUCTION, scenario_id=None, as_of=None, policies=None):
    if record is None:
        return {"validity": "MISSING"}
    validate_record(record, "quote")
    if record["evidence_class"] == "MISSING":
        return {"validity": "MISSING"}
    if decimal(record["amount_0g"]) != decimal(amount_0g):
        return {"validity": "AMOUNT_MISMATCH"}
    if any(record[k] != value for k, value in {"strategy_id": strategy_id, "direction": direction,
        "path": path, "market_context": market_context, "config_context": config_context}.items()):
        return {"validity": "CONTEXT_MISMATCH"}
    state = qualify(record, "quote", mode=mode, scenario_id=scenario_id, as_of=as_of, policies=policies or {})
    if state == "VALID" and mode == PRODUCTION and (record["configuration_binding"] != "BOUND_TO_VERIFIED_RUNTIME" or not config_context):
        state = "CONTEXT_MISMATCH"
    return {"validity": state, "quote_id": record["quote_id"], "fingerprint": fingerprint(record),
            "configuration_binding": record["configuration_binding"], "evidence_class": record["evidence_class"],
            "technical_admission": "NOT_ASSESSED", "capacity": "NOT_ASSESSED"}


def validate_valuation(valuation, price_usd, *, mode, scenario_id, as_of, policies):
    if not isinstance(valuation, dict) or set(valuation) != {"price_usd", "evidence_class", "source_id", "source_verified", "observation_timestamp", "retrieval_timestamp", "scenario_id"}:
        raise EconomicsError("VALUATION_PROVENANCE_REQUIRED")
    if decimal(valuation["price_usd"], positive=True) != decimal(price_usd, positive=True):
        raise EconomicsError("VALUATION_MISMATCH")
    if valuation["evidence_class"] == "MODELLED":
        if mode != SYNTHETIC or not scenario_id or valuation["scenario_id"] != scenario_id or not valuation["source_id"]:
            raise EconomicsError("MODELLED_VALUATION_REQUIRES_SYNTHETIC_MODE")
    elif valuation["evidence_class"] == "LIVE_OBSERVED":
        if not valuation["source_verified"]:
            raise EconomicsError("VALUATION_SOURCE_UNVERIFIED")
        now = timestamp(as_of)
        observed = timestamp(valuation["observation_timestamp"])
        retrieved = timestamp(valuation["retrieval_timestamp"])
        policy = policies.get(("valuation", valuation["source_id"], "0G_USD"))
        if not policy or not policy.get("rationale"):
            raise EconomicsError("VALUATION_NO_VALID_POLICY")
        age = (now - observed).total_seconds()
        if retrieved < observed or retrieved > now or age < 0 or age > float(decimal(policy["max_age_seconds"], positive=True)):
            raise EconomicsError("VALUATION_STALE_OR_INVALID_TIME")
    else:
        raise EconomicsError("UNQUALIFIED_VALUATION")
    return valuation


def normalize_costs(records, *, strategy_id, amount_0g, price_usd, horizon_days, valuation,
                    mode=PRODUCTION, scenario_id=None, config_context=None, as_of=None,
                    policies=None, quotes=(), required_costs=None):
    amount, price = decimal(amount_0g, positive=True), decimal(price_usd, positive=True)
    if required_costs is not None and mode != SYNTHETIC:
        raise EconomicsError("COST_COVERAGE_OVERRIDE_SYNTHETIC_ONLY")
    policy = policies or {}
    validate_valuation(valuation, price, mode=mode, scenario_id=scenario_id, as_of=as_of, policies=policy)
    rows = [validate_record(r, "cost") for r in records if r["strategy_id"] == strategy_id]
    _records_context(rows, amount, config_context, amount * price)
    names = [r["cost_type"] for r in rows]
    if len(set(names)) != len(names):
        raise EconomicsError("DUPLICATE_COST_COMPONENT")
    required = REQUIRED_COSTS[strategy_id] if required_costs is None else set(required_costs)
    if set(names) < required or required - set(names):
        raise EconomicsError("MISSING_COST:" + ",".join(sorted(required - set(names))))
    if "lifecycle_aggregate" in names and len(names) > 1:
        raise EconomicsError("AGGREGATE_COMPONENT_DOUBLE_COUNT")
    total = fixed = Decimal(0)
    components = []
    for r in rows:
        state = qualify(r, "cost", mode=mode, scenario_id=scenario_id, as_of=as_of, policies=policy)
        if state != "VALID":
            raise EconomicsError(state + ":" + r["evidence_id"])
        if r["horizon_days"] is not None and decimal(r["horizon_days"]) != decimal(horizon_days):
            raise EconomicsError("COST_HORIZON_MISMATCH")
        if r["cost_type"] == "bridge_cost" and r["structure"] != "STRUCTURAL_ZERO":
            raise EconomicsError("NO_USER_CAPITAL_BRIDGE_IN_FROZEN_ROUTES")
        if r["cost_type"] in {"protocol_yield_fee", "commission", "embedded_reward"}:
            raise EconomicsError("RETURN_COST_DOUBLE_COUNT")
        if any(r["cost_type"] in q["embedded_cost_types"] for q in quotes):
            raise EconomicsError("QUOTE_COST_DOUBLE_COUNT")
        if r["evidence_class"] == "QUOTE_DERIVED" and not any(q["quote_id"] == r["quote_id"] for q in quotes):
            raise EconomicsError("MISSING_PARENT_QUOTE")
        if r["evidence_class"] == "QUOTE_DERIVED":
            parent = next(q for q in quotes if q["quote_id"] == r["quote_id"])
            assessment = assess_quote(parent, strategy_id=strategy_id, amount_0g=amount,
                direction=parent["direction"], path=parent["path"], market_context=parent["market_context"],
                config_context=config_context, mode=mode, scenario_id=scenario_id, as_of=as_of, policies=policy)
            if assessment["validity"] != "VALID":
                raise EconomicsError("INVALID_PARENT_QUOTE:" + assessment["validity"])
        value = decimal(r["value"], nonnegative=True)
        if r["structure"] == "VARIABLE_BPS":
            usd = amount * price * value / 10000
        else:
            usd = value * price if r["unit"] == "0G" else value
        if r["structure"].startswith("FIXED_PER_"):
            fixed += usd
        total += usd
        components.append({"evidence": r, "cost_usd": float(usd), "native_unit_amount": r["value"] if r["unit"] == "0G" else None,
                           "valuation": valuation, "fingerprint": fingerprint(r)})
    if not isfinite(float(total)) or not isfinite(float(fixed)):
        raise EconomicsError("NONFINITE_COST")
    return {"total_cost_usd": float(total), "fixed_cost_usd": float(fixed), "components": components,
            "qualification": "VALID", "mode": mode, "valuation": valuation}


@dataclass(frozen=True)
class EconomicPoint:
    strategy_id: str
    canonical_amount_0g: str
    net_profit_usd: float
    net_return_horizon: float
    net_apy: float | None
    fixed_cost_usd: float
    entry_slippage_rate: float
    exit_slippage_rate: float
    evidence: dict


class EconomicsProvider:
    """Read-only, deterministic provider. Does not create/support admission."""
    def __init__(self, *, returns=(), quotes=(), costs=(), mode=PRODUCTION, scenario_id=None,
                 valuation=None, contexts=None, policies=None, required_costs=None):
        if mode not in {PRODUCTION, SYNTHETIC, HISTORICAL} or (mode == SYNTHETIC and not scenario_id):
            raise EconomicsError("explicit mode/scenario required")
        self.returns, self.quotes, self.costs = list(returns), list(quotes), list(costs)
        for kind, rows in (("return", returns), ("quote", quotes), ("cost", costs)):
            ids = []
            for r in rows:
                validate_record(r, kind)
                ids.append(r["quote_id"] if kind == "quote" else r["evidence_id"])
            if len(set(ids)) != len(ids):
                raise EconomicsError("duplicate evidence identity")
        self.mode, self.scenario_id, self.valuation = mode, scenario_id, valuation
        self.contexts, self.policies, self.required_costs = contexts or {}, dict(DEFAULT_ECONOMIC_POLICIES if policies is None else policies), required_costs
        self.repository_backed = False

    @classmethod
    def repository(cls):
        obj = cls(returns=load_evidence(DEFAULT_DATA_DIR / "strategy_return_evidence.json", "return"),
                   quotes=load_evidence(DEFAULT_DATA_DIR / "lp_quote_evidence.json", "quote"),
                   costs=load_evidence(DEFAULT_DATA_DIR / "lifecycle_cost_evidence.json", "cost"))
        obj.repository_backed = True
        return obj

    def __call__(self, *, strategy, canonical_amount_0g, price_usd, horizon_days, as_of,
                 management_fee_rate=0, performance_fee_rate=0, **kwargs):
        sid = str(strategy.strategy_id)
        if self.repository_backed:
            self.returns = list(load_evidence(DEFAULT_DATA_DIR / "strategy_return_evidence.json", "return"))
            self.quotes = list(load_evidence(DEFAULT_DATA_DIR / "lp_quote_evidence.json", "quote"))
            self.costs = list(load_evidence(DEFAULT_DATA_DIR / "lifecycle_cost_evidence.json", "cost"))
        amount = decimal(canonical_amount_0g, positive=True)
        price = decimal(price_usd, positive=True)
        context = self.contexts.get(sid, {})
        common = dict(strategy_id=sid, amount_0g=amount, price_usd=price, horizon_days=horizon_days,
                      mode=self.mode, scenario_id=self.scenario_id, config_context=context.get("config_context"),
                      as_of=as_of, policies=self.policies)
        applicable_returns = [r for r in self.returns if r["amount_0g"] is None or decimal(r["amount_0g"]) == amount]
        result = normalize_return(applicable_returns, **common)
        valid_quotes, assessments = [], []
        entry = exit_ = 0.0
        if sid in LP_IDS:
            for direction in ("ENTRY", "EXIT"):
                expected = context.get(direction)
                if not expected:
                    raise EconomicsError("MISSING_QUOTE_CONTEXT")
                found = [q for q in self.quotes if q["strategy_id"] == sid and q["direction"] == direction and q["evidence_class"] != "MISSING" and decimal(q["amount_0g"]) == amount]
                if len(found) != 1:
                    raise EconomicsError("MISSING_OR_AMBIGUOUS_QUOTE")
                q = found[0]
                if any(q[k] != expected.get(k) for k in ("token_in", "token_out", "fee_tier", "output_unit")):
                    raise EconomicsError("CONTEXT_MISMATCH")
                if q["amount_usd"] is not None and decimal(q["amount_usd"]) != amount * price:
                    raise EconomicsError("QUOTE_VALUATION_MISMATCH")
                assessment = assess_quote(q, strategy_id=sid, amount_0g=amount, direction=direction,
                    path=expected["path"], market_context=expected["market_context"],
                    config_context=context.get("config_context"), mode=self.mode, scenario_id=self.scenario_id,
                    as_of=as_of, policies=self.policies)
                if assessment["validity"] != "VALID":
                    raise EconomicsError(assessment["validity"])
                valid_quotes.append(q)
                assessments.append(assessment)
                if direction == "ENTRY":
                    entry = float(decimal(q["slippage_rate"]))
                else:
                    exit_ = float(decimal(q["slippage_rate"]))
        applicable_costs = [r for r in self.costs if r["amount_0g"] is None or decimal(r["amount_0g"]) == amount]
        costs = normalize_costs(applicable_costs, **common, valuation=self.valuation, quotes=valid_quotes,
                                required_costs=None if self.required_costs is None else self.required_costs.get(sid))
        principal = float(amount * price)
        m, p = float(decimal(management_fee_rate, nonnegative=True)), float(decimal(performance_fee_rate, nonnegative=True))
        if m > 1 or p > 1:
            raise EconomicsError("invalid management/performance fee")
        management = principal * m * float(horizon_days) / 365
        performance = max(0, result["expected_gross_income_usd"]) * p
        quote_cost = principal * (entry + exit_)
        profit = result["income_after_protocol_fee_usd"] - costs["total_cost_usd"] - quote_cost - management - performance
        rate = profit / principal
        annual = growth(1 + rate, 365 / float(horizon_days)) if rate > -1 else None
        proof = {"mode": self.mode, "scenario_id": self.scenario_id, "return": result, "costs": costs,
                 "quotes": valid_quotes, "quote_assessments": assessments, "quote_cost_usd": quote_cost,
                 "management_fee_usd": management, "performance_fee_usd": performance,
                 "valuation": self.valuation, "technical_admission": "NOT_ASSESSED", "risk_stress": "NOT_ASSESSED",
                 "public_deployment_proof": "NOT_ESTABLISHED"}
        # Freeze the evidence snapshot for equality-based selected revalidation.
        # A mutable provider must not retroactively change evaluated candidates.
        return EconomicPoint(sid, str(amount), profit, rate, annual, costs["fixed_cost_usd"], entry, exit_, deepcopy(proof))
