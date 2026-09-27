"use client";

import { FormEvent, useMemo, useState } from "react";

import type {
  OptimizerResponse,
  OptimizerStrategy,
  RiskProfile,
} from "@/lib/types";

const PROFILES: RiskProfile[] = [
  "Conservative",
  "Balanced",
  "Aggressive",
];

const DISPLAY_NAMES: Record<string, string> = {
  NATIVE_STAKE_0G: "Native 0G",
  GIMO_STAKE_0G: "Gimo st0G",
  OKU_LP_0G_USDC: "Oku LP",
  JAINE_LP_0G_USDC: "Jaine LP",
  ASCEND_STAKE_A0G: "Ascend a0G",
  ASCEND_RESTAKE: "Embedded Restaking",
  MORPHO_LEND_0G: "Morpho",
};

function pct(value: number | null, digits = 2) {
  return value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

function usd(value: number | null) {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function friendlyReason(reason: string) {
  const map: Record<string, string> = {
    "optimizer_eligible=False": "Not currently optimizer-ready",
    "slippage_exceeds_profile_limit": "Slippage exceeds this profile limit",
    "exit_time_exceeds_profile_limit": "Exit time exceeds this profile limit",
    "technical_eligibility=EXCLUDED_LIQUIDITY_CONSTRAINED":
      "Insufficient live liquidity",
    "technical_eligibility=EXCLUDED_LIVE_DATA_INCOMPLETE":
      "Waiting for sufficient live history",
    "technical_eligibility=EXCLUDED_EMBEDDED":
      "Already embedded in a0G backing",
    "technical_eligibility=EXCLUDED_PENDING":
      "Market not yet verified",
    "execution_status=PENDING": "Execution route pending verification",
    "missing_net_return_horizon": "Return data unavailable",
  };

  return map[reason] ?? reason.replaceAll("_", " ");
}

function statusLabel(strategy: OptimizerStrategy) {
  if (strategy.allocation_weight > 0) return "Allocated";
  if (strategy.profile_eligible) return "Eligible";
  if (
    strategy.exclusion_reasons.some((reason) =>
      reason.includes("EXCLUDED_LIQUIDITY_CONSTRAINED"),
    )
  ) {
    return "Liquidity gated";
  }
  if (
    strategy.exclusion_reasons.some((reason) =>
      reason.includes("EXCLUDED_LIVE_DATA_INCOMPLETE"),
    )
  ) {
    return "Collecting data";
  }
  if (
    strategy.exclusion_reasons.some((reason) =>
      reason.includes("EXCLUDED_EMBEDDED"),
    )
  ) {
    return "Embedded";
  }
  return "Excluded";
}

export default function Home() {
  const [amount, setAmount] = useState("1000");
  const [horizon, setHorizon] = useState("90");
  const [profile, setProfile] = useState<RiskProfile>("Balanced");
  const [data, setData] = useState<OptimizerResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const allocated = useMemo(
    () =>
      data?.strategies
        .filter((strategy) => strategy.allocation_weight > 0)
        .sort((a, b) => b.allocation_weight - a.allocation_weight) ?? [],
    [data],
  );

  async function optimize(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: Number(amount),
          horizon_days: Number(horizon),
          profile,
        }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail ?? payload.error ?? "Optimization failed");
      }

      setData(payload as OptimizerResponse);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Optimization failed",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brandMark">A</div>
          <div>
            <div className="brandName">ASCEND</div>
            <div className="brandSub">Strategy Optimizer</div>
          </div>
        </div>
        <div className="networkPill">
          <span className="networkDot" />
          0G Mainnet
        </div>
      </header>

      <section className="hero">
        <div>
          <div className="eyebrow">LIVE YIELD ROUTING</div>
          <h1>Put your 0G to work.</h1>
          <p>
            Compare live staking and DeFi routes, constrain risk, and generate
            a portfolio before approving any on-chain action.
          </p>
        </div>
        <div className="heroStat">
          <span>Optimizer state</span>
          <strong>{data ? "Live" : "Ready"}</strong>
        </div>
      </section>

      <div className="workspace">
        <form className="controlCard" onSubmit={optimize}>
          <div className="sectionLabel">Configure</div>

          <label className="fieldLabel" htmlFor="amount">
            Amount
          </label>
          <div className="amountField">
            <input
              id="amount"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              inputMode="decimal"
            />
            <span>0G</span>
          </div>

          <label className="fieldLabel" htmlFor="horizon">
            Horizon
          </label>
          <div className="amountField compact">
            <input
              id="horizon"
              value={horizon}
              onChange={(event) => setHorizon(event.target.value)}
              inputMode="numeric"
            />
            <span>days</span>
          </div>

          <div className="fieldLabel">Risk profile</div>
          <div className="segmented">
            {PROFILES.map((item) => (
              <button
                key={item}
                type="button"
                className={profile === item ? "active" : ""}
                onClick={() => setProfile(item)}
              >
                {item}
              </button>
            ))}
          </div>

          <button className="primaryButton" type="submit" disabled={loading}>
            {loading ? "Optimizing…" : "Optimize portfolio"}
          </button>

          {error && <div className="errorBox">{error}</div>}

          <div className="controlFootnote">
            Analysis only. Execution always requires explicit user approval.
          </div>
        </form>

        <section className="results">
          <div className="metricGrid">
            <article className="metricCard">
              <span>Portfolio value</span>
              <strong>
                {data ? usd(data.input.portfolio_value_usd) : "—"}
              </strong>
              <small>
                {data ? `${data.input.amount.toLocaleString()} 0G` : "Enter an amount"}
              </small>
            </article>
            <article className="metricCard accent">
              <span>Net APY</span>
              <strong>
                {data
                  ? pct(data.portfolio.annualized_expected_net_apy)
                  : "—"}
              </strong>
              <small>Annualized expected return</small>
            </article>
            <article className="metricCard">
              <span>Expected profit</span>
              <strong>
                {data ? usd(data.portfolio.expected_net_profit_usd) : "—"}
              </strong>
              <small>
                {data ? `${data.input.horizon_days}-day horizon` : "—"}
              </small>
            </article>
            <article className="metricCard">
              <span>Slashing stress</span>
              <strong>
                {data ? pct(data.portfolio.stress.slashing) : "—"}
              </strong>
              <small>Modelled severe scenario</small>
            </article>
          </div>

          <article className="panel allocationPanel">
            <div className="panelHeader">
              <div>
                <div className="sectionLabel">Recommended allocation</div>
                <h2>{profile} portfolio</h2>
              </div>
              {data && (
                <div className="priceBadge">
                  1 0G = {usd(data.input.asset_price_usd)}
                </div>
              )}
            </div>

            {!data ? (
              <div className="emptyState">
                Run the optimizer to generate a live allocation.
              </div>
            ) : (
              <>
                <div className="allocationBar">
                  {allocated.map((strategy) => (
                    <div
                      key={strategy.strategy_id}
                      className="allocationSegment"
                      style={{ width: `${strategy.allocation_weight * 100}%` }}
                      title={DISPLAY_NAMES[strategy.strategy_id] ?? strategy.strategy_id}
                    />
                  ))}
                  {data.portfolio.idle.weight > 0 && (
                    <div
                      className="allocationSegment idle"
                      style={{ width: `${data.portfolio.idle.weight * 100}%` }}
                    />
                  )}
                </div>

                <div className="allocationList">
                  {allocated.map((strategy) => (
                    <div className="allocationRow" key={strategy.strategy_id}>
                      <div>
                        <strong>
                          {DISPLAY_NAMES[strategy.strategy_id] ??
                            strategy.strategy_id}
                        </strong>
                        <span>{pct(strategy.allocation_weight, 0)}</span>
                      </div>
                      <div>{usd(strategy.allocation_usd)}</div>
                    </div>
                  ))}
                  {data.portfolio.idle.weight > 0 && (
                    <div className="allocationRow">
                      <div>
                        <strong>Idle</strong>
                        <span>{pct(data.portfolio.idle.weight, 0)}</span>
                      </div>
                      <div>{usd(data.portfolio.idle.amount_usd)}</div>
                    </div>
                  )}
                </div>
              </>
            )}
          </article>

          <article className="panel">
            <div className="panelHeader">
              <div>
                <div className="sectionLabel">Strategy universe</div>
                <h2>Live routes</h2>
              </div>
              <div className="muted">
                {data ? `${data.strategies.length} tracked` : "Waiting"}
              </div>
            </div>

            <div className="strategyTable">
              <div className="strategyHead">
                <span>Strategy</span>
                <span>Net APY</span>
                <span>Liquidity</span>
                <span>Status</span>
              </div>

              {data?.strategies.map((strategy) => (
                <div className="strategyRow" key={strategy.strategy_id}>
                  <div>
                    <strong>
                      {DISPLAY_NAMES[strategy.strategy_id] ??
                        strategy.strategy_id}
                    </strong>
                    <small>
                      {strategy.exclusion_reasons[0]
                        ? friendlyReason(strategy.exclusion_reasons[0])
                        : strategy.data_status ?? "Live"}
                    </small>
                  </div>
                  <span>{pct(strategy.net_apy)}</span>
                  <span>{usd(strategy.liquidity_usd)}</span>
                  <span
                    className={
                      strategy.profile_eligible
                        ? "status positive"
                        : "status"
                    }
                  >
                    {statusLabel(strategy)}
                  </span>
                </div>
              ))}

              {!data && (
                <div className="emptyState tableEmpty">
                  Strategy status will appear after optimization.
                </div>
              )}
            </div>
          </article>

          {data && (
            <article className="panel stressPanel">
              <div>
                <div className="sectionLabel">Portfolio stress</div>
                <h2>Risk diagnostics</h2>
              </div>
              <div className="stressGrid">
                <div>
                  <span>Bridge</span>
                  <strong>{pct(data.portfolio.stress.bridge_exposure)}</strong>
                </div>
                <div>
                  <span>LP ±20%</span>
                  <strong>{pct(data.portfolio.stress.lp_il)}</strong>
                </div>
                <div>
                  <span>Slashing</span>
                  <strong>{pct(data.portfolio.stress.slashing)}</strong>
                </div>
              </div>
            </article>
          )}
        </section>
      </div>
    </main>
  );
}
