"use strict";
const { id, parseEther, isAddress, ZeroAddress, AbiCoder } = require("ethers");
const { createHash } = require("node:crypto");
const IDS = ["NATIVE_STAKE_0G", "GIMO_STAKE_0G", "JAINE_LP_0G_USDC", "OKU_LP_0G_USDC", "ASCEND_STAKE_A0G"];
const ref = (name) => ({ ref: name });
const fail = (message) => { throw new Error(message); };
const hash = (value) => createHash("sha256").update(JSON.stringify(value)).digest("hex");
function keys(value, allowed, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(`Invalid ${label}`);
  if (Object.keys(value).some(k => !allowed.includes(k))) fail(`Unknown field in ${label}; secret fields are forbidden`);
}
function amount(value, label) {
  if (typeof value !== "string" || !/^\d+(\.\d{1,18})?$/.test(value)) fail(`Invalid ${label}`);
  const n = parseEther(value);
  if (n <= 0n) fail(`Invalid ${label}`);
  return n;
}
function address(value, label) {
  if (!isAddress(value || "") || value.toLowerCase() === ZeroAddress) fail(`Invalid ${label}`);
  return value;
}
function validate(config) {
  keys(config, ["native", "ascend", "funding0g", "allocation0g", "maxGasBudget0g", "deployer", "user"], "config");
  keys(config.native, ["branch", "validator", "registry", "amount0g", "depositCap0g", "minShares", "approved", "codeHash", "implementationCodeHash", "forwardingMode"], "Native");
  keys(config.ascend, ["branch", "sourceCore", "w0g", "confirmed", "codeHash", "w0gCodeHash", "queueCodeHash", "implementationCodeHash", "minShares"], "Ascend");
  for (const [name, route] of [["Native", config.native], ["Ascend", config.ascend]]) {
    if (!["LIVE", "MOCK"].includes(route.branch)) fail(`STOP: ${name} branch must be explicit`);
  }
  const q = amount(config.allocation0g, "allocation");
  const funding = amount(config.funding0g, "funding");
  amount(config.maxGasBudget0g, "gas budget");
  if (q > parseEther("0.001")) fail("Mock allocation exceeds fixed test cap");
  let nativeAmount = q;
  if (config.native.branch === "LIVE") {
    address(config.native.validator, "Native validator");
    address(config.native.registry, "Native registry");
    nativeAmount = amount(config.native.amount0g, "Native LIVE amount");
    const cap = amount(config.native.depositCap0g, "Native LIVE cap");
    if (cap < nativeAmount || config.native.approved !== true) fail("STOP: Native LIVE preflight failed: amount/cap approval required");
    if (!["CONSENSUS_THRESHOLD", "BELOW_THRESHOLD_INTERACTION"].includes(config.native.forwardingMode)) fail("Native forwarding claim must be explicit");
    if (!/^\d+$/.test(config.native.minShares || "") || BigInt(config.native.minShares) <= 0n) fail("Native live minShares unresolved");
  }
  if (config.ascend.branch === "LIVE") {
    address(config.ascend.sourceCore, "Ascend sourceCore"); address(config.ascend.w0g, "Ascend W0G");
    if (config.ascend.confirmed !== true) fail("STOP: Ascend LIVE protocol confirmation required");
    if (!/^\d+$/.test(config.ascend.minShares || "") || BigInt(config.ascend.minShares) <= 0n) fail("Ascend live minShares unresolved");
  }
  if (funding < nativeAmount + 4n * q || funding < 2n * nativeAmount) fail("Funding insufficient for planned amounts / 5000-bps Native cap");
  if (config.deployer) address(config.deployer, "deployer");
  if (config.user) address(config.user, "user");
  return { q, funding, nativeAmount };
}
function buildPlan(config) {
  const { q, funding, nativeAmount } = validate(config);
  const steps = [];
  const deploy = (name, contract, args = []) => steps.push({ name, kind: "DEPLOY", contract, args });
  const call = (name, target, method, args, extra = {}) => steps.push({ name, kind: "CONFIGURE", target: ref(target), method, args, ...extra });
  deploy("manager", "StrategyManager", [ref("owner")]);
  deploy("vault", "AscendVault", [ref("owner"), ref("manager")]);
  if (config.native.branch === "MOCK") deploy("validator", "Mock0GValidator", [1]);
  deploy("nativeAdapter", "Native0GStakingAdapter", [ref("owner"), ref("vault"), config.native.branch === "MOCK" ? ref("validator") : config.native.validator]);
  deploy("gimoPool", "MockGimoStakePool");
  steps.push({ name: "gimoToken", kind: "READ", target: ref("gimoPool"), method: "st0g", args: [] });
  deploy("gimoAdapter", "GimoAdapter", [ref("vault"), ref("gimoPool"), ref("gimoToken"), "ascend-galileo-validation"]);
  deploy("w0g", "MockW0G"); deploy("usdce", "MockUSDCe"); deploy("factory", "MockV3Factory");
  deploy("pool", "MockV3Pool", [ref("factory"), ref("w0g"), ref("usdce"), 3000]);
  call("setPool", "factory", "setPool", [ref("pool")]);
  deploy("npm", "MockV3PositionManager", [ref("factory")]);
  deploy("v1", "MockV3RouterV1", [ref("factory")]); deploy("r02", "MockV3Router02", [ref("factory")]);
  call("seedV1", "usdce", "mint", [ref("v1"), q.toString()]);
  call("seedR02", "usdce", "mint", [ref("r02"), q.toString()]);
  for (const [name, router, mode] of [["jaineAdapter", "v1", 0], ["okuAdapter", "r02", 1]]) {
    deploy(name, "V3LiquidityAdapter", [{ vault: ref("vault"), factory: ref("factory"), router: ref(router), positionManager: ref("npm"), pool: ref("pool"), w0g: ref("w0g"), usdce: ref("usdce"), feeTier: 3000, tickLower: -600, tickUpper: 600, sqrtLowerX96: (2n ** 95n).toString(), sqrtUpperX96: (2n ** 97n).toString(), targetUsdcBps: 5000, routerMode: mode }]);
  }
  if (config.ascend.branch === "MOCK") {
    deploy("ascendW0g", "MockAscendW0G");
    deploy("sourceCore", "MockAscendSourceCore", [ref("ascendW0g")]);
    deploy("queue", "MockAscendWithdrawalQueue", [ref("sourceCore"), ref("ascendW0g")]);
    call("attachQueue", "sourceCore", "setWithdrawalQueue", [ref("queue")]);
  }
  deploy("ascendAdapter", "AscendProtocolAdapter", [ref("vault"), config.ascend.branch === "MOCK" ? ref("sourceCore") : config.ascend.sourceCore, config.ascend.branch === "MOCK" ? ref("ascendW0g") : config.ascend.w0g]);
  const names = ["nativeAdapter", "gimoAdapter", "jaineAdapter", "okuAdapter", "ascendAdapter"];
  IDS.forEach((sid, i) => call(`register${i}`, "manager", "registerStrategy", [id(sid), { adapter: ref(names[i]), inputAsset: ZeroAddress, depositCap: i === 0 && config.native.branch === "LIVE" ? parseEther(config.native.depositCap0g).toString() : parseEther("0.001").toString(), maxAllocationBps: 5000, asynchronous: [0, 1, 4].includes(i), active: i !== 4 }]));
  steps.push({ name: "deposit", kind: "INTERACT", target: ref("vault"), method: "depositNative", args: [], value: funding.toString() });
  IDS.slice(0, 4).forEach((sid, i) => {
    const n = i === 0 ? nativeAmount : q;
    const minShares = i === 0 && config.native.branch === "LIVE" ? config.native.minShares : (i >= 2 ? n / 2n : n).toString();
    steps.push({ name: `allocate${i}`, kind: "INTERACT", target: ref("vault"), method: "executeAllocation", args: [id(sid), n.toString(), minShares, ref("deadline"), i >= 2 ? { executionData: (q / 2n).toString() } : "0x"] });
  });
  const counts = Object.fromEntries(["DEPLOY", "CONFIGURE", "INTERACT"].map(k => [k, steps.filter(s => s.kind === k).length]));
  return { version: "GALILEO_PLAN_V1", chainId: 16602, configHash: hash(config), composition: { native: config.native.branch, gimo: "MOCK", jaine: "MOCK", oku: "MOCK", ascend: config.ascend.branch }, canonicalAscendGate: "CLOSED", steps, counts, optionalAscendExercise: { state: "SEPARATE_REVIEW_REQUIRED", additionalTransactions: 2, description: "Explicit test-instance activation plus manual allocation; never canonical optimizer clearance" }, limitations: ["Entry/allocation exercise only; no withdrawals or rewards proved", "Mock setters/mints are unrestricted; no production-security claim", "V3 fixtures use synthetic raw-unit liquidity and 18-decimal mock USDC.e", "LIVE branches require current protocol/validator approval; no automated fallback"] };
}
function resolve(value, state) {
  if (Array.isArray(value)) return value.map(v => resolve(v, state));
  if (value && typeof value === "object") {
    if (value.ref) { if (state[value.ref] === undefined) fail("Unresolved plan reference"); return state[value.ref]; }
    if (value.executionData) return AbiCoder.defaultAbiCoder().encode(["uint256", "uint256", "uint256", "uint256"], [value.executionData, value.executionData, value.executionData, state.deadline]);
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, resolve(v, state)]));
  }
  return value;
}
module.exports = { IDS, buildPlan, validate, resolve, hash };
