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
import json,sys
s=load_strategies(); snapshots=load_snapshots(s, 'data/demo_strategy_snapshots.csv')
a=sys.argv[1:]
def arg(name, default):
 return a[a.index(name)+1] if name in a else default
run=optimize_live(s,snapshots,amount=float(arg('--amount','1000')),horizon_days=float(arg('--horizon-days','90')),profile=arg('--profile','Balanced'),price_usd=1,include_modelled='--include-modelled' in a)
print(json.dumps(run.to_dict(), allow_nan=False))
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
