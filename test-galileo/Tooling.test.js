const { expect } = require("chai");
const hre = require("hardhat");
const { buildPlan, IDS } = require("../scripts/galileo/plan");
const { readonlyRpc, broadcastGuard, checkResume, preflight } = require("../scripts/galileo/preflight");
const { rehearse } = require("../scripts/galileo/local-rehearsal");
const config = require("../scripts/galileo/mock-plan.json");
const clone = () => JSON.parse(JSON.stringify(config));
describe("Galileo tooling — no public signing or broadcasts", function () {
  it("defaults to preflight without reading the signer secret", function () {
    const env = { get GALILEO_PRIVATE_KEY() { throw new Error("must not inspect"); } };
    expect(broadcastGuard([], env)).to.equal("PREFLIGHT");
  });
  it("rejects missing broadcast acknowledgement", function () {
    expect(() => broadcastGuard(["--broadcast"], {})).to.throw("acknowledgement missing");
  });
  it("keeps broadcast sealed even with acknowledgement", function () {
    expect(() => broadcastGuard(["--broadcast"], { GALILEO_ALLOW_BROADCAST: "YES" })).to.throw("disabled");
  });
  for (const method of ["eth_sendTransaction", "eth_sendRawTransaction", "eth_sign", "personal_sign", "eth_signTransaction"]) {
    it(`blocks ${method} before provider access`, async function () {
      let called = false;
      try { await readonlyRpc({ send() { called = true; } })(method, []); throw new Error("unexpected"); }
      catch (e) { expect(e.message).to.include("forbidden"); }
      expect(called).to.equal(false);
    });
  }
  it("rejects wrong chain before block calls", async function () {
    let calls = 0;
    try { await preflight(config, { async send() { calls++; return "0x1"; } }, "test", () => {}); throw new Error("unexpected"); }
    catch (e) { expect(e.message).to.include("wrong chain"); }
    expect(calls).to.equal(1);
  });
  it("requires explicit branches", function () {
    const c = clone(); delete c.native.branch;
    expect(() => buildPlan(c)).to.throw("branch must be explicit");
  });
  it("rejects unresolved Native live without choosing a mock", function () {
    const c = clone(); c.native.branch = "LIVE";
    expect(() => buildPlan(c)).to.throw("Native validator"); expect(c.native.branch).to.equal("LIVE");
  });
  it("requires Native live amount and cap", function () {
    const c = clone(); c.native = { branch: "LIVE", validator: "0x0000000000000000000000000000000000000001", registry: "0x0000000000000000000000000000000000000002" };
    expect(() => buildPlan(c)).to.throw("Native LIVE amount");
  });
  it("rejects Ascend LIVE without protocol confirmation", function () {
    const c = clone(); c.ascend = { branch: "LIVE", sourceCore: hre.ethers.ZeroAddress.replace(/0$/, "1"), w0g: hre.ethers.ZeroAddress.replace(/0$/, "2") };
    expect(() => buildPlan(c)).to.throw("protocol confirmation");
  });
  it("rejects unknown secret-bearing config fields without exposing values", function () {
    const c = clone(); c.privateKey = "DO_NOT_LOG_THIS";
    expect(() => buildPlan(c)).to.throw("secret fields are forbidden");
  });
  it("rejects insufficient funding and oversized mock allocations", function () {
    const c = clone(); c.funding0g = "0.0001";
    expect(() => buildPlan(c)).to.throw("Funding insufficient");
    c.allocation0g = "0.01"; expect(() => buildPlan(c)).to.throw("test cap");
  });
  it("constructs the full explicit mock graph with separate V3 modes", function () {
    const p = buildPlan(config);
    expect(p.counts).to.deep.equal({ DEPLOY: 19, CONFIGURE: 9, INTERACT: 5 });
    expect(p.steps.filter(s => s.contract === "V3LiquidityAdapter").map(s => s.args[0].routerMode)).to.deep.equal([0, 1]);
    expect(p.steps.some(s => s.contract === "MockGimoSt0G")).to.equal(false);
    expect(p.steps.filter(s => s.method === "registerStrategy").map(s => s.args[0])).to.deep.equal(IDS.map(hre.ethers.id));
  });
  it("keeps Ascend inactive and omits its allocation", function () {
    const p = buildPlan(config);
    const reg = p.steps.find(s => s.name === "register4");
    expect(reg.args[1].active).to.equal(false);
    expect(p.steps.filter(s => s.method === "executeAllocation")).to.have.length(4);
    expect(p.canonicalAscendGate).to.equal("CLOSED");
  });
  it("accepts only matching transaction-free resume manifests", function () {
    const m = { version: "v1", sourceCommit: "a", chainId: 16602, configHash: "c", planHash: "p", toolingHash: "t", mode: "PREFLIGHT", transactions: [] };
    expect(() => checkResume(m, m)).not.to.throw();
    for (const field of ["version", "sourceCommit", "chainId", "configHash", "planHash", "toolingHash"]) expect(() => checkResume({ ...m, [field]: "changed" }, m)).to.throw("inconsistent");
    expect(() => checkResume({ ...m, transactions: [{}] }, m)).to.throw("transaction-free");
  });
  it("builds a network preflight with explicit unassessed wallet/future-state blockers", async function () {
    const calls = [];
    const p = { async send(method) { calls.push(method); if (method === "eth_chainId") return "0x40da"; return { number: "0x10", timestamp: "0x20", hash: "0xabc" }; } };
    const m = await preflight(config, p, "source", () => {});
    expect(m.plan.counts.DEPLOY).to.equal(19); expect(m.transactions).to.deep.equal([]);
    expect(m.failures).to.include("PUBLIC_WALLET_BALANCE_AND_GAS_NOT_ASSESSED");
    expect(m.broadcastReady).to.equal(false); expect(calls).to.deep.equal(["eth_chainId", "eth_getBlockByNumber"]);
  });
  it("records failure for empty Native live dependency code", async function () {
    const c = clone(); c.native = { branch: "LIVE", validator: "0x0000000000000000000000000000000000000001", registry: "0x0000000000000000000000000000000000000002", amount0g: "0.0001", depositCap0g: "0.001", minShares: "1", approved: true, forwardingMode: "CONSENSUS_THRESHOLD" };
    const p = { async send(method) { if (method === "eth_chainId") return "0x40da"; if (method === "eth_getBlockByNumber") return { number: "0x10", timestamp: "0x20" }; return "0x"; } };
    const m = await preflight(c, p, "source", () => {});
    expect(m.failures).to.include("STOP: Native LIVE preflight failed"); expect(m.plan.composition.native).to.equal("LIVE");
  });
  it("rehearses 33 local transactions through the existing contracts without Ascend activation", async function () {
    const r = await rehearse(hre, buildPlan(config));
    expect(r.transactions).to.equal(33);
    expect(await r.contracts.manager.strategyCount()).to.equal(5n);
    for (const sid of IDS.slice(0, 4)) expect(await r.contracts.vault.strategySharesOf(r.user.address, hre.ethers.id(sid))).to.be.gt(0n);
    expect(await r.contracts.manager.isStrategyActive(hre.ethers.id(IDS[4]))).to.equal(false);
    expect(await r.contracts.vault.strategySharesOf(r.user.address, hre.ethers.id(IDS[4]))).to.equal(0n);
    expect(await r.contracts.jaineAdapter.tokenId()).not.to.equal(await r.contracts.okuAdapter.tokenId());
    expect(await r.contracts.vault.idleBalanceOf(r.user.address, hre.ethers.ZeroAddress)).to.equal(hre.ethers.parseEther("0.0006"));
    expect(await r.contracts.vault.rewardAccounting()).to.equal(hre.ethers.ZeroAddress);
  });
  it("forbids running local rehearsal on public chain", async function () {
    const fake = { network: { name: "galileo" }, ethers: { provider: { async getNetwork() { return { chainId: 16602n }; } }, getSigners() { throw new Error("must not load signers"); } } };
    try { await rehearse(fake, buildPlan(config)); throw new Error("unexpected"); }
    catch (e) { expect(e.message).to.include("in-process Hardhat"); }
  });
  it("fails Ascend candidate relationship mismatch without promoting readiness", async function () {
    const iface = new hre.ethers.Interface(["function asset() view returns(address)"]);
    const p = { async send(method) {
      if (method === "eth_chainId") return "0x40da";
      if (method === "eth_getBlockByNumber") return { number: "0x10", timestamp: "0x20" };
      if (method === "eth_getCode") return "0x6000";
      if (method === "eth_call") return iface.encodeFunctionResult("asset", [hre.ethers.ZeroAddress]);
      throw new Error("Unexpected RPC");
    } };
    const m = await preflight(config, p, "source", () => {}, true);
    expect(m.checks.find(c => c.label === "ASCEND_CANDIDATE_DIAGNOSTICS_ONLY").state).to.equal("FAIL");
    expect(m.broadcastReady).to.equal(false); expect(m.transactions).to.deep.equal([]);
  });
  it("fails insufficient public funds without accessing a signer", async function () {
    const c = clone(); c.deployer = c.user = "0x0000000000000000000000000000000000000001";
    const p = { async send(method) {
      if (method === "eth_chainId") return "0x40da";
      if (method === "eth_getBlockByNumber") return { number: "0x10", timestamp: "0x20" };
      if (method === "eth_getBalance") return "0x0";
      throw new Error("must not estimate without funds");
    } };
    const m = await preflight(c, p, "source", () => {});
    expect(m.failures).to.include("PUBLIC_BALANCE_OR_ESTIMATION_FAILED");
  });
});
