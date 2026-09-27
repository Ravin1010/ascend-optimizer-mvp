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

const STRATEGY_META: Record<
  string,
  {
    name: string;
    icon: string;
    protocol: string;
  }
> = {
  NATIVE_STAKE_0G: {
    name: "Native 0G",
    icon: "0G",
    protocol: "0G staking",
  },
  GIMO_STAKE_0G: {
    name: "Gimo st0G",
    icon: "G",
    protocol: "Gimo liquid staking",
  },
  OKU_LP_0G_USDC: {
    name: "Oku LP",
    icon: "O",
    protocol: "Uniswap V3 via Oku",
  },
  JAINE_LP_0G_USDC: {
    name: "Jaine LP",
    icon: "J",
    protocol: "Jaine concentrated liquidity",
  },
  ASCEND_STAKE_A0G: {
    name: "Ascend a0G",
    icon: "A",
    protocol: "Ascend / Mellow",
  },
  ASCEND_RESTAKE: {
    name: "Embedded Restaking",
    icon: "R",
    protocol: "Mellow / Symbiotic exposure",
  },
  MORPHO_LEND_0G: {
    name: "Morpho",
    icon: "M",
    protocol: "Lending route",
  },
};

function meta(strategyId: string) {
  return (
    STRATEGY_META[strategyId] ?? {
      name: strategyId,
      icon: "?",
      protocol: "Strategy",
    }
  );
}

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

function compactUsd(value: number | null) {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function friendlyReason(reason: string) {
  const map: Record<string, string> = {
    "optimizer_eligible=False": "Not currently optimizer-ready",
    "slippage_exceeds_profile_limit": "Slippage exceeds this profile limit",
    "exit_time_exceeds_profile_limit": "Exit time exceeds this profile limit",
    "technical_eligibility=EXCLUDED_LIQUIDITY_CONSTRAINED":
      "Low live liquidity",
    "technical_eligibility=EXCLUDED_LIVE_DATA_INCOMPLETE":
      "Waiting for ≥24h yield history",
    "technical_eligibility=EXCLUDED_EMBEDDED":
      "Already embedded in a0G backing",
    "technical_eligibility=EXCLUDED_PENDING":
      "Market not yet verified",
    "execution_status=PENDING": "Execution route pending verification",
    "missing_net_return_horizon": "Return data unavailable",
  };

  return map[reason] ?? reason.replaceAll("_", " ");
}

function dataQualityLabel(strategy: OptimizerStrategy) {
  if (strategy.data_status === "PARTIAL_MODELLED") {
    return "Live yield + modelled risk";
  }
  if (strategy.data_status === "LIVE_INCOMPLETE") {
    return "Live market data · runtime checks";
  }
  if (strategy.data_status === "MISSING") {
    return "No verified live snapshot";
  }
  return strategy.data_status ?? "Live route";
}

function primaryReason(strategy: OptimizerStrategy) {
  const reasons = strategy.exclusion_reasons;

  if (
    reasons.some((reason) =>
      reason.includes("EXCLUDED_LIQUIDITY_CONSTRAINED"),
    )
  ) {
    return `Low liquidity (${compactUsd(strategy.liquidity_usd)})`;
  }

  if (
    reasons.some((reason) =>
      reason.includes("EXCLUDED_LIVE_DATA_INCOMPLETE"),
    )
  ) {
    return "Waiting for ≥24h yield history";
  }

  if (
    reasons.some((reason) =>
      reason.includes("EXCLUDED_EMBEDDED"),
    )
  ) {
    return "Embedded beneath a0G · not separately allocatable";
  }

  if (
    reasons.some((reason) =>
      reason.includes("EXCLUDED_PENDING"),
    )
  ) {
    return "Exact market not yet verified";
  }

  const profileReason = reasons.find(
    (reason) =>
      reason === "slippage_exceeds_profile_limit" ||
      reason === "exit_time_exceeds_profile_limit",
  );

  if (profileReason) {
    return friendlyReason(profileReason);
  }

  if (strategy.profile_eligible) {
    return dataQualityLabel(strategy);
  }

  const concrete = reasons.find(
    (reason) => reason !== "optimizer_eligible=False",
  );

  return concrete
    ? friendlyReason(concrete)
    : dataQualityLabel(strategy);
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

function allocationExplanation(
  strategy: OptimizerStrategy,
  allocatedRank: number,
  data: OptimizerResponse,
) {
  const strategyName = meta(strategy.strategy_id).name;
  const concentration =
    data.profile_constraints.max_strategy_concentration;

  if (strategy.allocation_weight > 0) {
    if (allocatedRank === 0) {
      return `${strategyName} ranks first at ${pct(strategy.net_apy)} Net APY and reaches ${data.input.profile}'s ${pct(concentration, 0)} per-strategy concentration ceiling.`;
    }

    return `${strategyName} is the next-highest eligible return at ${pct(strategy.net_apy)} Net APY and receives the remaining ${pct(strategy.allocation_weight, 0)} while satisfying the active profile constraints.`;
  }

  if (strategy.profile_eligible) {
    return `${strategyName} is eligible at ${pct(strategy.net_apy)} Net APY, but lower-ranked than the allocated routes, so the optimizer assigns 0% at this notional.`;
  }

  if (
    strategy.exclusion_reasons.includes("slippage_exceeds_profile_limit") &&
    strategy.max_entry_exit_slippage != null
  ) {
    return `${strategyName} is excluded because live slippage is ${pct(strategy.max_entry_exit_slippage)}, above the ${data.input.profile} limit of ${pct(data.profile_constraints.max_entry_exit_slippage)}.`;
  }

  if (
    strategy.exclusion_reasons.includes("exit_time_exceeds_profile_limit") &&
    strategy.exit_time_days != null
  ) {
    return `${strategyName} is excluded because its ${strategy.exit_time_days.toFixed(1)}d exit time exceeds the ${data.profile_constraints.max_exit_time_days.toFixed(0)}d profile limit.`;
  }

  return `${strategyName} is not allocatable in this run: ${primaryReason(strategy)}.`;
}

export default function Home() {
  const [amount, setAmount] = useState("1000");
  const [horizon, setHorizon] = useState("90");
  const [profile, setProfile] = useState<RiskProfile>("Balanced");
  const [data, setData] = useState<OptimizerResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedStrategy, setExpandedStrategy] = useState<string | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [walletNotice, setWalletNotice] = useState(false);

  const allocated = useMemo(
    () =>
      data?.strategies
        .filter((strategy) => strategy.allocation_weight > 0)
        .sort((a, b) => b.allocation_weight - a.allocation_weight) ?? [],
    [data],
  );

  const explanationRows = useMemo(() => {
    if (!data) return [];

    const allocatedIds = new Map(
      allocated.map((strategy, index) => [strategy.strategy_id, index]),
    );

    return data.strategies
      .filter(
        (strategy) =>
          strategy.allocation_weight > 0 ||
          strategy.profile_eligible ||
          strategy.strategy_id === "JAINE_LP_0G_USDC" ||
          strategy.strategy_id === "ASCEND_STAKE_A0G",
      )
      .slice(0, 5)
      .map((strategy) => ({
        strategy,
        text: allocationExplanation(
          strategy,
          allocatedIds.get(strategy.strategy_id) ?? -1,
        ),
      }));
  }, [allocated, data]);

  async function optimize(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setReviewOpen(false);
    setWalletNotice(false);

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

  function showWalletNotice() {
    setReviewOpen(true);
    setWalletNotice(true);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brandMark">A</div>
          <div>
            <div className="brandName">ASCEND</div>
            <div className="brandSub">Optimizer</div>
          </div>
        </div>

        <nav className="mainNav" aria-label="Primary navigation">
          <button type="button" disabled title="Coming soon">
            Earn
          </button>
          <button type="button" className="active" aria-current="page">
            Optimize
          </button>
          <button type="button" disabled title="Coming soon">
            Portfolio
          </button>
          <button type="button" disabled title="Coming soon">
            Strategies
          </button>
        </nav>

        <div className="topActions">
          <div className="networkPill">
            <span className="networkDot" />
            0G Mainnet
          </div>
          <button
            className="walletButton"
            type="button"
            onClick={showWalletNotice}
          >
            Connect Wallet
          </button>
        </div>
      </header>

      <section className="appHeading">
        <div>
          <div className="eyebrow">LIVE STRATEGY ROUTER</div>
          <h1>Strategy optimizer</h1>
          <p>
            Compare live 0G routes, apply your risk profile, and review the
            proposed allocation before any wallet action.
          </p>
        </div>
        <div className="optimizerState">
          <span className="networkDot" />
          <div>
            <small>Optimizer</small>
            <strong>{data ? "Live" : "Ready"}</strong>
          </div>
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
            {loading ? "Optimizing…" : "Optimize"}
          </button>

          {error && <div className="errorBox">{error}</div>}

          <div className="controlFootnote">
            Analysis only. Every wallet and execution action requires explicit
            user approval.
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
                {data
                  ? `${data.input.amount.toLocaleString()} 0G`
                  : "Enter an amount"}
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
                      title={meta(strategy.strategy_id).name}
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
                        <span className="miniIcon">
                          {meta(strategy.strategy_id).icon}
                        </span>
                        <strong>{meta(strategy.strategy_id).name}</strong>
                        <span>{pct(strategy.allocation_weight, 0)}</span>
                      </div>
                      <div>{usd(strategy.allocation_usd)}</div>
                    </div>
                  ))}
                  {data.portfolio.idle.weight > 0 && (
                    <div className="allocationRow">
                      <div>
                        <span className="miniIcon mutedIcon">—</span>
                        <strong>Idle</strong>
                        <span>{pct(data.portfolio.idle.weight, 0)}</span>
                      </div>
                      <div>{usd(data.portfolio.idle.amount_usd)}</div>
                    </div>
                  )}
                </div>

                <div className="allocationActions">
                  <button
                    type="button"
                    className="secondaryButton"
                    onClick={() => setReviewOpen(true)}
                  >
                    Why this allocation?
                  </button>
                  <button
                    type="button"
                    className="primaryButton inline"
                    onClick={() => setReviewOpen(true)}
                  >
                    Review allocation
                  </button>
                </div>
              </>
            )}
          </article>

          {data && reviewOpen && (
            <article className="panel explainPanel">
              <div className="panelHeader">
                <div>
                  <div className="sectionLabel">Explainability</div>
                  <h2>Why this allocation?</h2>
                </div>
                <button
                  className="textButton"
                  type="button"
                  onClick={() => setReviewOpen(false)}
                >
                  Close
                </button>
              </div>

              <div className="constraintSection">
                <div className="constraintHeading">
                  <div>
                    <div className="sectionLabel">Constraints applied</div>
                    <h3>{data.input.profile} limits</h3>
                  </div>
                  <span className="muted">Binding limits highlighted</span>
                </div>

                <div className="constraintGrid">
                  {[
                    {
                      key: "max_strategy_concentration",
                      label: "Max strategy",
                      value: pct(data.profile_constraints.max_strategy_concentration, 0),
                    },
                    {
                      key: "max_entry_exit_slippage",
                      label: "Max slippage",
                      value: pct(data.profile_constraints.max_entry_exit_slippage),
                    },
                    {
                      key: "max_exit_time_days",
                      label: "Max exit time",
                      value: `${data.profile_constraints.max_exit_time_days.toFixed(0)}d`,
                    },
                    {
                      key: "max_bridge_exposure",
                      label: "Max bridge",
                      value: pct(data.profile_constraints.max_bridge_exposure, 0),
                    },
                    {
                      key: "max_portfolio_lp_il_stress",
                      label: "Max LP stress",
                      value: pct(data.profile_constraints.max_portfolio_lp_il_stress, 0),
                    },
                    {
                      key: "max_slashing_stress_loss",
                      label: "Max slashing",
                      value: pct(data.profile_constraints.max_slashing_stress_loss, 0),
                    },
                  ].map((constraint) => {
                    const binding =
                      data.profile_constraints.binding_constraints.includes(
                        constraint.key,
                      );
                    const triggered =
                      data.profile_constraints.triggered_constraints.includes(
                        constraint.key,
                      );

                    return (
                      <div
                        key={constraint.key}
                        className={[
                          "constraintChip",
                          binding ? "binding" : "",
                          triggered ? "triggered" : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                      >
                        <span>{constraint.label}</span>
                        <strong>{constraint.value}</strong>
                        <small>
                          {binding
                            ? "Binding"
                            : triggered
                              ? "Triggered by excluded route"
                              : "Applied"}
                        </small>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="explanationList">
                {explanationRows.map(({ strategy, text }) => (
                  <div className="explanationRow" key={strategy.strategy_id}>
                    <span className="strategyIcon small">
                      {meta(strategy.strategy_id).icon}
                    </span>
                    <div>
                      <strong>{meta(strategy.strategy_id).name}</strong>
                      <p>{text}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="executionFlow">
                <div className="flowHeading">
                  <div>
                    <div className="sectionLabel">Execution flow</div>
                    <h3>Review → wallet → approval → execution</h3>
                  </div>
                  <span className="safeBadge">Explicit approval only</span>
                </div>

                <div className="flowSteps">
                  <div className="flowStep complete">
                    <span>1</span>
                    <div>
                      <strong>Review allocation</strong>
                      <small>Portfolio generated and visible above.</small>
                    </div>
                  </div>
                  <div className="flowStep next">
                    <span>2</span>
                    <div>
                      <strong>Connect wallet</strong>
                      <small>Wallet integration is the next execution-layer task.</small>
                    </div>
                  </div>
                  <div className="flowStep locked">
                    <span>3</span>
                    <div>
                      <strong>Approve</strong>
                      <small>Locked until a wallet is connected.</small>
                    </div>
                  </div>
                  <div className="flowStep locked">
                    <span>4</span>
                    <div>
                      <strong>Execute</strong>
                      <small>Never automatic; requires a final explicit action.</small>
                    </div>
                  </div>
                </div>

                <div className="flowActions">
                  <button
                    type="button"
                    className="walletButton prominent"
                    onClick={() => setWalletNotice(true)}
                  >
                    Connect Wallet
                  </button>
                  <button type="button" className="lockedButton" disabled>
                    Approve
                  </button>
                  <button type="button" className="lockedButton" disabled>
                    Execute
                  </button>
                </div>

                {walletNotice && (
                  <div className="walletNotice">
                    Wallet integration is not wired yet. No wallet request or
                    transaction was sent.
                  </div>
                )}
              </div>
            </article>
          )}

          <article className="panel strategyPanel">
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
                <span />
              </div>

              {data?.strategies.map((strategy) => {
                const strategyMeta = meta(strategy.strategy_id);
                const expanded = expandedStrategy === strategy.strategy_id;

                return (
                  <div className="strategyEntry" key={strategy.strategy_id}>
                    <button
                      type="button"
                      className="strategyRow"
                      aria-expanded={expanded}
                      onClick={() =>
                        setExpandedStrategy(
                          expanded ? null : strategy.strategy_id,
                        )
                      }
                    >
                      <div className="strategyIdentity">
                        <span className="strategyIcon">
                          {strategyMeta.icon}
                        </span>
                        <div>
                          <strong>{strategyMeta.name}</strong>
                          <small>{primaryReason(strategy)}</small>
                        </div>
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
                      <span className="chevron">
                        {expanded ? "−" : "+"}
                      </span>
                    </button>

                    {expanded && (
                      <div className="strategyDetails">
                        <div className="detailIntro">
                          <div>
                            <span>{strategyMeta.protocol}</span>
                            <strong>{dataQualityLabel(strategy)}</strong>
                          </div>
                          <p>{primaryReason(strategy)}</p>
                        </div>

                        <div className="detailGrid">
                          <div>
                            <span>Net APY</span>
                            <strong>{pct(strategy.net_apy)}</strong>
                          </div>
                          <div>
                            <span>Max slippage</span>
                            <strong>
                              {pct(strategy.max_entry_exit_slippage)}
                            </strong>
                          </div>
                          <div>
                            <span>Exit time</span>
                            <strong>
                              {strategy.exit_time_days == null
                                ? "—"
                                : `${strategy.exit_time_days.toFixed(1)}d`}
                            </strong>
                          </div>
                          <div>
                            <span>Bridge exposure</span>
                            <strong>{pct(strategy.bridge_fraction)}</strong>
                          </div>
                          <div>
                            <span>Slashing stress</span>
                            <strong>
                              {pct(strategy.slashing_stress_loss)}
                            </strong>
                          </div>
                          <div>
                            <span>LP ±20% stress</span>
                            <strong>
                              {pct(strategy.lp_stress_loss_20pct)}
                            </strong>
                          </div>
                        </div>

                        {strategy.exclusion_reasons.length > 0 && (
                          <div className="reasonList">
                            {strategy.exclusion_reasons
                              .filter(
                                (reason) =>
                                  reason !== "optimizer_eligible=False",
                              )
                              .map((reason) => (
                                <span key={reason}>
                                  {friendlyReason(reason)}
                                </span>
                              ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

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
