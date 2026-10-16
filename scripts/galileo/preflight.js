"use strict";
const { Interface, keccak256, ZeroAddress, parseEther } = require("ethers");
const { buildPlan, hash } = require("./plan");
const SLOT = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50";
const IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
const allowed = new Set(["eth_chainId", "eth_blockNumber", "eth_getBlockByNumber", "eth_getCode", "eth_getStorageAt", "eth_call", "eth_getBalance", "eth_estimateGas", "eth_gasPrice", "eth_getTransactionReceipt"]);
function readonlyRpc(provider) {
  return async (method, params) => {
    if (!allowed.has(method)) throw new Error("STOP: RPC method forbidden in preflight");
    return provider.send(method, params);
  };
}
function broadcastGuard(args, env) {
  if (!args.includes("--broadcast")) return "PREFLIGHT";
  if (env.GALILEO_ALLOW_BROADCAST !== "YES") throw new Error("STOP: broadcast acknowledgement missing");
  // Intentional release seal: no signing implementation in this iteration.
  throw new Error("STOP: broadcasting is disabled in this tooling release; separate readiness review required");
}
function checkResume(previous, current) {
  for (const key of ["version", "sourceCommit", "chainId", "configHash", "planHash", "toolingHash"]) {
    if (previous[key] !== current[key]) throw new Error("STOP: inconsistent resume manifest");
  }
  if (previous.mode !== "PREFLIGHT" || !Array.isArray(previous.transactions) || previous.transactions.length) throw new Error("STOP: only transaction-free preflight manifests can resume in this release");
}
async function preflight(config, provider, sourceCommit, artifacts, inspectCandidates = false) {
  const rpc = readonlyRpc(provider);
  const result = { version: "GALILEO_PREFLIGHT_V1", mode: "PREFLIGHT", sourceCommit, chainId: null, configHash: null, transactions: [], deployments: [], failures: [], checks: [], broadcastReady: false, executionState: "NO_TRANSACTIONS_SUBMITTED" };
  let context = "NETWORK";
  const check = async (label, fn) => {
    try { const value = await fn(); result.checks.push({ label, state: "PASS", value }); return value; }
    catch (error) {
      result.failures.push(label);
      const code = ["CALL_EXCEPTION", "TIMEOUT", "NETWORK_ERROR", "SERVER_ERROR", "BAD_DATA"].includes(error.code) ? error.code : "READ_OR_VALIDATION_FAILED";
      result.checks.push({ label, state: "FAIL", stage: context, errorCode: code });
      return null;
    }
  };
  const chain = Number(BigInt(await rpc("eth_chainId", [])));
  if (chain !== 16602) throw new Error("STOP: wrong chain ID; expected 16602");
  result.chainId = chain;
  const latest = await rpc("eth_getBlockByNumber", ["latest", false]);
  if (!latest || !latest.number || !latest.timestamp) throw new Error("STOP: latest block unavailable");
  result.observedBlock = { number: BigInt(latest.number).toString(), hash: latest.hash, timestamp: BigInt(latest.timestamp).toString() };
  // Pin all dependent calls to this observed block.
  const pinned = latest.number;
  let plan;
  try { plan = buildPlan(config); result.plan = plan; result.configHash = plan.configHash; result.planHash = hash(plan); }
  catch { result.failures.push("STOP: invalid/unapproved branch configuration; no fallback performed"); }
  async function read(to, signature, args = []) {
    context = signature;
    const abi = new Interface([signature]); const fn = abi.fragments[0];
    const raw = await rpc("eth_call", [{ to, data: abi.encodeFunctionData(fn, args) }, pinned]);
    return abi.decodeFunctionResult(fn, raw);
  }
  async function code(to) {
    context = "DEPENDENCY_BYTECODE";
    const raw = await rpc("eth_getCode", [to, pinned]);
    if (!raw || raw === "0x") throw new Error("no bytecode");
    return { address: to, bytes: (raw.length - 2) / 2, codeHash: keccak256(raw) };
  }
  async function pinnedCode(to, expected) {
    const c = await code(to);
    if (!/^0x[0-9a-fA-F]{64}$/.test(expected || "") || c.codeHash.toLowerCase() !== expected.toLowerCase()) throw new Error("unapproved code");
    return c;
  }
  if (config.native?.branch === "LIVE") await check("STOP: Native LIVE preflight failed", async () => {
    const n = config.native;
    const c = await pinnedCode(n.validator, n.codeHash);
    await code(n.registry);
    const pub = (await read(n.validator, "function consensusPubkey() view returns(bytes)"))[0];
    const resolved = (await read(n.registry, "function getValidator(bytes) view returns(address)", [pub]))[0];
    if (resolved.toLowerCase() !== n.validator.toLowerCase()) throw new Error("registry mismatch");
    const status = (await read(n.validator, "function bondStatus() view returns(uint8)"))[0];
    if (status !== 3n) throw new Error("validator not bonded; operational confirmation required");
    const delegation = await read(n.validator, "function getDelegation(address) view returns(address,uint256)", [ZeroAddress]);
    const converted = (await read(n.validator, "function convertToTokens(uint256) view returns(uint256)", [1n]))[0];
    const fee = (await read(n.validator, "function withdrawalFeeInGwei() view returns(uint96)"))[0];
    const threshold = (await read(n.registry, "function effectiveDelegationInGwei() view returns(uint96)"))[0] * 1000000000n;
    if (n.forwardingMode === "CONSENSUS_THRESHOLD" && parseEther(n.amount0g) < threshold) throw new Error("below threshold");
    const beaconRaw = await rpc("eth_getStorageAt", [n.validator, SLOT, pinned]);
    const beacon = "0x" + beaconRaw.slice(-40);
    const implementation = (await read(beacon, "function implementation() view returns(address)"))[0];
    const implementationCode = await pinnedCode(implementation, n.implementationCodeHash);
    // Readbacks alone cannot certify all write methods; keep the human ABI review mandatory.
    result.failures.push("NATIVE_VERIFIED_ABI_AND_OPERATIONAL_REVIEW_REQUIRED");
    return { ...c, bondStatus: status.toString(), zeroAddressShares: delegation[1].toString(), converted: converted.toString(), withdrawalFeeWei: (fee * 1000000000n).toString(), forwardingThresholdWei: threshold.toString(), implementationCode, limitation: n.forwardingMode === "BELOW_THRESHOLD_INTERACTION" ? "real Galileo validator-contract delegation interaction below the confirmed consensus-forwarding threshold" : "Consensus forwarding still requires transaction evidence" };
  });
  const a = config.ascend?.branch === "LIVE" ? config.ascend : inspectCandidates ? { sourceCore: "0xc07510228bB180985C6009C24ED5D05fdfC82F84", w0g: "0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c" } : null;
  if (a) await check(config.ascend.branch === "LIVE" ? "STOP: Ascend LIVE preflight failed" : "ASCEND_CANDIDATE_DIAGNOSTICS_ONLY", async () => {
    const live = config.ascend.branch === "LIVE";
    if (live && a.confirmed !== true) throw new Error("confirmation missing");
    const source = live ? await pinnedCode(a.sourceCore, a.codeHash) : await code(a.sourceCore);
    const wrapped = live ? await pinnedCode(a.w0g, a.w0gCodeHash) : await code(a.w0g);
    const asset = (await read(a.sourceCore, "function asset() view returns(address)"))[0];
    if (asset.toLowerCase() !== a.w0g.toLowerCase()) throw new Error("asset mismatch");
    const queue = (await read(a.sourceCore, "function withdrawalQueue() view returns(address)"))[0];
    const queueCode = live ? await pinnedCode(queue, a.queueCodeHash) : await code(queue);
    const back = (await read(queue, "function sourceCore() view returns(address)"))[0];
    const qa = (await read(queue, "function asset() view returns(address)"))[0];
    if (back.toLowerCase() !== a.sourceCore.toLowerCase() || qa.toLowerCase() !== a.w0g.toLowerCase()) throw new Error("queue mismatch");
    const symbol = (await read(a.sourceCore, "function symbol() view returns(string)"))[0];
    const preview = (await read(a.sourceCore, "function previewRedeem(uint256) view returns(uint256)", [1n]))[0];
    const epoch = (await read(queue, "function currentEpoch() view returns(uint256)"))[0];
    const duration = (await read(queue, "function epochDuration() view returns(uint256)"))[0];
    const delay = (await read(queue, "function withdrawalDelay() view returns(uint256)"))[0];
    await read(queue, "function sharesOf(uint256,address) view returns(uint256)", [epoch, ZeroAddress]);
    const implRaw = await rpc("eth_getStorageAt", [a.sourceCore, IMPL, pinned]);
    const impl = "0x" + implRaw.slice(-40);
    const implementationCode = live ? await pinnedCode(impl, a.implementationCodeHash) : await code(impl);
    if (live) result.failures.push("ASCEND_POSITIVE_DEPOSIT_REQUEST_CLAIM_REVIEW_REQUIRED");
    return { source, wrapped, queueCode, implementationCode, symbol, previewOneShare: preview.toString(), epoch: epoch.toString(), epochDuration: duration.toString(), withdrawalDelay: delay.toString(), confirmation: live ? "CONFIG_ASSERTED_REQUIRES_REVIEW" : "NOT_APPROVED_CANDIDATE_ONLY", canonicalGate: "CLOSED" };
  });
  if (plan && config.deployer && config.user) await check("PUBLIC_BALANCE_OR_ESTIMATION_FAILED", async () => {
    const gasBudget = parseEther(config.maxGasBudget0g);
    const ownerBalance = BigInt(await rpc("eth_getBalance", [config.deployer, pinned]));
    const userBalance = BigInt(await rpc("eth_getBalance", [config.user, pinned]));
    const funding = parseEther(config.funding0g);
    if (ownerBalance < gasBudget + (config.user.toLowerCase() === config.deployer.toLowerCase() ? funding : 0n) || userBalance < funding + gasBudget) throw new Error("balance insufficient");
    const artifact = await artifacts("StrategyManager");
    const { ContractFactory } = require("ethers");
    const tx = await new ContractFactory(artifact.abi, artifact.bytecode).getDeployTransaction(config.deployer);
    const gas = await rpc("eth_estimateGas", [{ from: config.deployer, data: tx.data }, pinned]);
    const price = await rpc("eth_gasPrice", []);
    if (BigInt(gas) * BigInt(price) > gasBudget) throw new Error("gas exceeds budget");
    return { deployer: config.deployer, user: config.user, deployerBalanceWei: ownerBalance.toString(), userBalanceWei: userBalance.toString(), managerDeploymentGasEstimate: BigInt(gas).toString(), gasPriceWei: BigInt(price).toString(), scope: "Manager only; remaining future-state estimates NOT_ASSESSED" };
  });
  else result.failures.push("PUBLIC_WALLET_BALANCE_AND_GAS_NOT_ASSESSED");
  result.failures.push("FUTURE_STATE_CONSTRUCTOR_AND_ALLOCATION_ESTIMATES_REQUIRED", "BROADCAST_RELEASE_SEAL");
  result.status = result.failures.length ? "BLOCKED_FOR_BROADCAST" : "PREFLIGHT_PASSED";
  return result;
}
module.exports = { readonlyRpc, broadcastGuard, checkResume, preflight };
