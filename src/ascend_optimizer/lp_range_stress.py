"""Synthetic V3 inventory evaluation only; no admission or portfolio-risk integration."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import hashlib
import json
from pathlib import Path
import re

from .data_loader import DEFAULT_DATA_DIR

CONFIG_VERSION = "LP_EVALUATION_CONFIG_V1"
SCENARIO_VERSION = "LP_SHOCKS_V1"
METHOD_VERSION = "V3_RANGE_INVENTORY_V1"
LABEL = "SYNTHETIC_EVALUATION_ONLY"
ARTIFACT_TYPE = "SYNTHETIC_EVALUATION_CONFIGURATION"
PRECISION = 60
STRATEGIES = {"JAINE_LP_0G_USDC": ("JAINE", "V1"), "OKU_LP_0G_USDC": ("OKU", "ROUTER02")}
SHOCKS = {"DOWN_20": "-0.20", "DOWN_10": "-0.10", "UP_10": "0.10", "UP_20": "0.20"}
FIELDS = {"config_id", "strategy_id", "venue", "chain_id", "chain_role", "evidence_class", "label",
          "w0g", "usdce", "w0g_decimals", "usdce_decimals", "token0", "token1", "price_orientation",
          "pool_price_orientation", "router_mode", "fee_tier", "tick_spacing", "tick_lower", "tick_upper",
          "sqrt_lower", "sqrt_upper", "reference_price", "target_usdc_bps", "composition_rule",
          "notional_convention", "pool_context", "notes"}


class LPStressError(ValueError):
    pass


def number(value, *, positive=False):
    """Identity inputs are decimal strings, never binary floating point."""
    if not isinstance(value, str):
        raise LPStressError("decimal string required")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise LPStressError("invalid decimal") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise LPStressError("finite positive decimal required")
    return result


def text(value: Decimal) -> str:
    return format(value, "f")


def tick_sqrt(tick: int) -> str:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        return text((Decimal("1.0001") ** tick).sqrt())


def config_identity(config: dict) -> str:
    payload = {k: v for k, v in config.items() if k != "config_id"}
    encoded = json.dumps({"version": CONFIG_VERSION, "config": payload}, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
    return CONFIG_VERSION + ":" + config["strategy_id"] + ":" + hashlib.sha256(encoded).hexdigest()


def pool_price(config: dict, economic_price: Decimal) -> Decimal:
    """Atomic token1/token0 ratio, including the explicit decimal scale."""
    if not economic_price.is_finite() or economic_price <= 0:
        raise LPStressError("positive economic price required")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        w0g_first = config["token0"] == config["w0g"]
        whole_ratio = economic_price if w0g_first else 1 / economic_price
        decimals0, decimals1 = ((config["w0g_decimals"], config["usdce_decimals"]) if w0g_first
                               else (config["usdce_decimals"], config["w0g_decimals"]))
        return whole_ratio * Decimal(10) ** (decimals1 - decimals0)


@dataclass(frozen=True)
class Inventory:
    w0g: Decimal
    usdce: Decimal
    range_state: str


def inventory(config: dict, liquidity: Decimal, economic_price: Decimal) -> Inventory:
    """L and x/y use atomic token units. Results use whole economic token units."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        if not liquidity.is_finite() or liquidity <= 0:
            raise LPStressError("positive liquidity required")
        a, b = number(config["sqrt_lower"], positive=True), number(config["sqrt_upper"], positive=True)
        if a >= b:
            raise LPStressError("inverted sqrt range")
        s = pool_price(config, economic_price).sqrt()
        # Snap only decimal-rounding noise at an inclusive boundary. This is
        # far below one tick; it is not an economic price/range tolerance.
        if abs(s / a - 1) <= Decimal("1e-55"):
            s = a
        elif abs(s / b - 1) <= Decimal("1e-55"):
            s = b
        if s <= a:
            x, y, state = liquidity * (1 / a - 1 / b), Decimal(0), "BELOW_RANGE"
        elif s >= b:
            x, y, state = Decimal(0), liquidity * (b - a), "ABOVE_RANGE"
        else:
            x, y, state = liquidity * (1 / s - 1 / b), liquidity * (s - a), "IN_RANGE"
        if config["token0"] == config["w0g"]:
            w, u = x / Decimal(10) ** config["w0g_decimals"], y / Decimal(10) ** config["usdce_decimals"]
        else:
            w, u = y / Decimal(10) ** config["w0g_decimals"], x / Decimal(10) ** config["usdce_decimals"]
        return Inventory(w, u, state)


def implied_target_bps(config: dict) -> int:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        p = number(config["reference_price"], positive=True)
        inv = inventory(config, Decimal(1), p)
        return int((10000 * inv.usdce / (inv.w0g * p + inv.usdce)).to_integral_value())


def validate_config(config: dict) -> dict:
    if not isinstance(config, dict) or set(config) != FIELDS:
        raise LPStressError("evaluation config fields mismatch")
    if config["strategy_id"] not in STRATEGIES:
        raise LPStressError("only Jaine/Oku LP strategies")
    venue, router = STRATEGIES[config["strategy_id"]]
    if config["venue"] != venue or config["router_mode"] != router:
        raise LPStressError("venue/router mode mismatch")
    if type(config["chain_id"]) is not int or config["chain_id"] != 16661 or config["chain_role"] != "INTENDED_EVALUATION_DOMAIN":
        raise LPStressError("evaluation domain must be 16661")
    if config["label"] != LABEL or config["evidence_class"] != "MODELLED":
        raise LPStressError("synthetic label required")
    for key in ("w0g", "usdce", "token0", "token1"):
        v = config[key]
        if not isinstance(v, str) or not re.fullmatch(r"0x[0-9a-f]{40}", v) or int(v, 16) == 0:
            raise LPStressError("nonzero lowercase address required")
    if config["w0g"] == config["usdce"] or {config["token0"], config["token1"]} != {config["w0g"], config["usdce"]}:
        raise LPStressError("distinct W0G/USDC.e pair required")
    for key in ("fee_tier", "tick_spacing", "tick_lower", "tick_upper", "target_usdc_bps", "w0g_decimals", "usdce_decimals"):
        if type(config[key]) is not int:
            raise LPStressError("integer required: " + key)
    if not 0 < config["fee_tier"] < 1000000 or config["tick_spacing"] <= 0:
        raise LPStressError("invalid fee/tick spacing")
    if not -887272 <= config["tick_lower"] < config["tick_upper"] <= 887272:
        raise LPStressError("invalid tick range")
    if any(config[k] % config["tick_spacing"] for k in ("tick_lower", "tick_upper")):
        raise LPStressError("misaligned tick")
    if not 0 <= config["target_usdc_bps"] <= 10000 or any(not 0 <= config[k] <= 36 for k in ("w0g_decimals", "usdce_decimals")):
        raise LPStressError("invalid target/decimals")
    if config["price_orientation"] != "USDC.e_PER_W0G" or config["pool_price_orientation"] != "ATOMIC_TOKEN1_PER_TOKEN0":
        raise LPStressError("inconsistent price orientation")
    if config["composition_rule"] != "RANGE_IMPLIED_FULL_NOTIONAL" or config["notional_convention"] != "USDC.e_VALUE; USDC.e=1_MODELLED_USD":
        raise LPStressError("unsupported composition/notional")
    for key in ("pool_context", "notes"):
        if not isinstance(config[key], str) or not config[key]:
            raise LPStressError("assumption context required")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        number(config["reference_price"], positive=True)
        a, b = number(config["sqrt_lower"], positive=True), number(config["sqrt_upper"], positive=True)
        if a >= b:
            raise LPStressError("invalid sqrt range")
        for key, tick in (("sqrt_lower", "tick_lower"), ("sqrt_upper", "tick_upper")):
            expected = Decimal(tick_sqrt(config[tick]))
            if abs(number(config[key]) / expected - 1) > Decimal("1e-55"):
                raise LPStressError("sqrt bound inconsistent with tick")
        if config["target_usdc_bps"] != implied_target_bps(config):
            raise LPStressError("target must describe rounded range-implied inventory")
    if config["config_id"] != config_identity(config):
        raise LPStressError("config identity mismatch")
    return config


def load_configs(path=DEFAULT_DATA_DIR / "lp_evaluation_config.json") -> list[dict]:
    artifact = json.loads(Path(path).read_text())
    if set(artifact) != {"config_version", "artifact_type", "label", "configurations"} or artifact["config_version"] != CONFIG_VERSION or artifact["artifact_type"] != ARTIFACT_TYPE or artifact["label"] != LABEL:
        raise LPStressError("synthetic evaluation artifact required")
    configs = artifact["configurations"]
    if len(configs) != 2 or {c["strategy_id"] for c in configs} != set(STRATEGIES):
        raise LPStressError("exactly Jaine and Oku required")
    return [validate_config(c) for c in configs]


def scenarios(*, include_reference=False) -> list[dict]:
    shocks = SHOCKS | ({"REFERENCE_ZERO": "0"} if include_reference else {})
    return [{"scenario_id": SCENARIO_VERSION + ":" + name, "shock": shock,
             "evidence_class": "MODELLED", "label": LABEL} for name, shock in shocks.items()]


@dataclass(frozen=True)
class StressResult:
    strategy_id: str
    config_id: str
    scenario_id: str
    evidence_class: str
    label: str
    method_version: str
    shock: str
    notional: str
    reference_price: str
    shocked_price: str
    pool_math_price: str
    liquidity: str
    initial_w0g: str
    initial_usdce: str
    initial_value: str
    initial_range_state: str
    range_state: str
    w0g: str
    usdce: str
    lp_value: str
    hodl_value: str
    lp_vs_hodl_difference: str
    impermanent_loss_fraction: str
    absolute_lp_loss: str
    hodl_market_loss: str
    market_value_change: str
    rebalancing_value_change: str
    lp_value_change: str
    execution_effects_included: bool = False
    fee_income_included: bool = False


def evaluate(config: dict, scenario: dict, notional: str, *, mode: str, expected_config_id: str) -> StressResult:
    if mode != LABEL:
        raise LPStressError("explicit synthetic evaluation mode required")
    validate_config(config)
    if expected_config_id != config["config_id"]:
        raise LPStressError("evaluation config mismatch")
    if scenario not in scenarios(include_reference=True):
        raise LPStressError("scenario identity mismatch")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        n, p = number(notional, positive=True), number(config["reference_price"], positive=True)
        shock = number(scenario["shock"])
        ps = p * (1 + shock)
        unit = inventory(config, Decimal(1), p)
        liquidity = n / (unit.w0g * p + unit.usdce)
        initial, stressed = inventory(config, liquidity, p), inventory(config, liquidity, ps)
        vi = initial.w0g * p + initial.usdce
        vlp = stressed.w0g * ps + stressed.usdce
        vh = initial.w0g * ps + initial.usdce
        return StressResult(config["strategy_id"], config["config_id"], scenario["scenario_id"], "MODELLED", LABEL,
                            METHOD_VERSION, scenario["shock"], notional, text(p), text(ps), text(pool_price(config, ps)),
                            text(liquidity), text(initial.w0g), text(initial.usdce), text(vi), initial.range_state,
                            stressed.range_state, text(stressed.w0g), text(stressed.usdce), text(vlp), text(vh),
                            text(vlp-vh), text(vlp/vh-1), text(max(Decimal(0), (vi-vlp)/vi)),
                            text(max(Decimal(0), (vi-vh)/vi)), text(vh-vi), text(vlp-vh), text(vlp-vi))


def replay() -> dict:
    configs = load_configs()
    return {"config_version": CONFIG_VERSION, "scenario_version": SCENARIO_VERSION, "method_version": METHOD_VERSION,
            "label": LABEL, "evidence_class": "MODELLED", "decimal_precision": PRECISION,
            "configurations": configs, "scenarios": scenarios(),
            "assumptions": ["No fee accrual or execution loss; USDC.e held at 1 modelled USD",
                            "Continuous V3 inventory, no atomic rounding or on-chain TickMath execution",
                            "Synthetic token ordering is mathematical, not a selected pool/registered route",
                            "Deterministic shocks are experiments, not probabilities or return predictions"],
            "results": [asdict(evaluate(c, s, "1000", mode=LABEL, expected_config_id=c["config_id"]))
                        for c in configs for s in scenarios()]}
