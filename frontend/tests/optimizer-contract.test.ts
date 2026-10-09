import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, test } from "node:test";
import { POST } from "../src/app/api/optimize/route.ts";
import { parseOptimizerResponse } from "../src/lib/optimizer-response.ts";
import type { OptimizerResponse } from "../src/lib/types.ts";

const root = path.resolve(process.cwd(), "..");
const script = `import sys,os
sys.path.insert(0,os.getcwd())
from src.ascend_optimizer.data_loader import load_strategies, load_snapshots
from src.ascend_optimizer.live_optimize import optimize_live
from src.ascend_optimizer.amount_optimizer import run_amount_optimizer
import json,sys
from datetime import datetime, timezone
s=load_strategies(); snapshots=load_snapshots(s, 'data/demo_strategy_snapshots.csv')
a=sys.argv[1:]
def arg(name, default):
 return a[a.index(name)+1] if name in a else default
run=optimize_live(s,snapshots,amount=float(arg('--amount','1000')),horizon_days=float(arg('--horizon-days','90')),profile=arg('--profile','Balanced'),price_usd=1,include_modelled='--include-modelled' in a)
amount_run=run_amount_optimizer(s,snapshots,decision_amount=run.amount,price_usd=run.asset_price_usd,horizon_days=run.horizon_days,profile=run.profile,as_of=datetime(2026,10,9,10,0,tzinfo=timezone.utc))
print(json.dumps(run.to_dict(amount_aware=amount_run), allow_nan=False))
`;
const fixture: OptimizerResponse = parseOptimizerResponse(execFileSync(process.env.PYTHON_BIN ?? "python", ["-c", script], {cwd: root, encoding: "utf8"}));
const temporary = mkdtempSync(path.join(tmpdir(), "ascend-contract-"));
const executable = path.join(temporary, "python-fixture");
const originalPython = process.env.PYTHON_BIN;
// Exercise the actual API subprocess boundary using synthetic local snapshots.
writeFileSync(executable, "#!/usr/bin/env python\n" + script, {mode: 0o755});
process.env.PYTHON_BIN = executable;
after(() => {
  if (originalPython === undefined) delete process.env.PYTHON_BIN;
  else process.env.PYTHON_BIN = originalPython;
  rmSync(temporary, {recursive: true, force: true});
});
function request(body: unknown): Request {
  return new Request("http://localhost/api/optimize", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
}

test("actual API forwards the complete Python schema 1.3 result", async () => {
  const response = await POST(request({amount: 1000, horizon_days: 90, profile: "Balanced"}));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), fixture);
  assert.equal(fixture.run_scope.whole_portfolio_compliance, "NOT_ASSESSED");
  assert.equal(fixture.strategies.filter(s => s.structural_candidate).length, 5);
});

test("API compatibility flag preserves membership, gates and allocations", async () => {
  const response = await POST(request({amount: 1000, horizon_days: 90, profile: "Balanced", include_modelled: true}));
  assert.equal(response.status, 200);
  const result = parseOptimizerResponse(await response.text());
  assert.equal(result.input.include_modelled, true);
  assert.deepEqual(result.portfolio, fixture.portfolio);
  assert.deepEqual(result.strategies, fixture.strategies);
});

test("contract guard rejects old version and missing authoritative state", () => {
  assert.throws(() => parseOptimizerResponse(JSON.stringify({...fixture, schema_version: "1.2"})));
  const malformed: {strategies: Record<string, unknown>[]} = JSON.parse(JSON.stringify(fixture));
  delete malformed.strategies[0].allocation_gate;
  assert.throws(() => parseOptimizerResponse(JSON.stringify(malformed)));
});

test("API rejects invalid compatibility flag without running optimizer", async () => {
  const response = await POST(request({amount: 1000, include_modelled: "yes"}));
  assert.equal(response.status, 400);
});

test("API fails rather than returning an incompatible result as success", async () => {
  const invalidExecutable = path.join(temporary, "old-schema");
  writeFileSync(invalidExecutable, '#!/bin/sh\nprintf \'{"schema_version":"1.2"}\'\n', {mode: 0o755});
  process.env.PYTHON_BIN = invalidExecutable;
  try {
    const response = await POST(request({amount: 1000}));
    assert.equal(response.status, 500);
    const body: unknown = await response.json();
    assert.equal((body as {error: string}).error, "Optimizer execution failed");
  } finally { process.env.PYTHON_BIN = executable; }
});


test("optional amount-aware comparison retains unknown admission and failure semantics", () => {
  assert.equal(fixture.schema_version, "1.3");
  assert.equal(fixture.amount_aware?.scope, "DECISION_SLEEVE");
  assert.equal(fixture.amount_aware?.recommendation?.idle_weight, 1);
  assert.equal(fixture.amount_aware?.outcome, "NO_POSITIVE_ALLOCATION");
  assert.equal(fixture.amount_aware?.candidates.filter(c => c.weight > 0 && c.eligible).length, 0);
  const malformed = {...fixture, amount_aware: {...fixture.amount_aware,
    selected_amount_revalidation: "FAILED", recommendation: {allocations: {}}}};
  assert.throws(() => parseOptimizerResponse(JSON.stringify(malformed)));
});


test("repository admission diagnostics remain additive and unknown", () => {
  const positives = fixture.amount_aware?.candidates.filter(c => c.weight > 0 && c.strategy_id !== "ASCEND_STAKE_A0G") ?? [];
  assert.ok(positives.length > 0);
  for (const candidate of positives) {
    assert.equal(candidate.technical_admission, "UNKNOWN");
    assert.equal(candidate.admission_evidence?.capture, null);
    assert.ok(candidate.admission_evidence?.diagnostics?.includes("NO_MATCHING_CAPTURE"));
    assert.equal(candidate.admission_evidence?.validity?.state, "MISSING");
    assert.equal(candidate.admission_evidence?.validity?.as_of, "2026-10-09T10:00:00+00:00");
    assert.equal(candidate.admission_evidence?.validity?.observation_age_seconds, null);
    assert.equal(candidate.admission_evidence?.validity?.policy_version, "ADMISSION_VALIDITY_V1");
  }
});
