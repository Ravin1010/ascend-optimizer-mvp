#!/usr/bin/env node
"use strict";
const {sanitizedChildEnv}=require("./subprocess-env");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { JsonRpcProvider, FetchRequest } = require("ethers");
const { broadcastGuard, preflight, checkResume } = require("./preflight");
async function main() {
  const args = process.argv.slice(2);
  const options = new Set(["--preflight", "--broadcast", "--config", "--out", "--resume", "--inspect-candidates"]);
  for (let i = 0; i < args.length; i++) {
    if (!options.has(args[i])) throw new Error("STOP: unknown command option");
    if (["--config", "--out", "--resume"].includes(args[i])) {
      if (!args[++i] || args[i].startsWith("--")) throw new Error("STOP: missing option value");
    }
  }
  broadcastGuard(args, process.env);
  const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
  const root = path.resolve(__dirname, "../..");
  const config = JSON.parse(fs.readFileSync(option("--config", path.join(__dirname, "mock-plan.json")), "utf8"));
  const source = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, env:sanitizedChildEnv(),encoding: "utf8" }).trim();
  const dirty = execFileSync("git", ["status", "--porcelain", "--untracked-files=no"], { cwd: root, env:sanitizedChildEnv(),encoding: "utf8" }).trim();
  const url = process.env.GALILEO_RPC_URL || "https://evmrpc-testnet.0g.ai";
  const parsed = new URL(url);
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.search) throw new Error("STOP: use an HTTPS read-only RPC without embedded credentials");
  const req = new FetchRequest(url); req.timeout = 30000;
  // Respect an existing corporate/workspace HTTPS proxy; never log its value.
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  if (proxy) {
    const { HttpsProxyAgent } = require("https-proxy-agent");
    req.getUrlFunc = FetchRequest.createGetUrlFunc({ agent: new HttpsProxyAgent(proxy) });
  }
  // Suppress implicit network discovery retries. preflight independently issues
  // eth_chainId and rejects anything except 16602 before dependency access.
  const provider = new JsonRpcProvider(req, { chainId: 16602, name: "galileo" }, { batchMaxCount: 1, staticNetwork: true });
  try {
    const result = await preflight(config, provider, source, async (name) => {
      const locations = { StrategyManager: "StrategyManager.sol" };
      return JSON.parse(fs.readFileSync(path.join(root, "artifacts-galileo/contracts", locations[name], name + ".json"), "utf8"));
    }, args.includes("--inspect-candidates"));
    result.sourceWorkingTree = dirty ? "TRACKED_CHANGES_PRESENT" : "TRACKED_FILES_CLEAN";
    const { createHash } = require("node:crypto");
    const fingerprint = createHash("sha256");
    for (const file of ["plan.js", "preflight.js", "run.js"]) fingerprint.update(fs.readFileSync(path.join(__dirname, file)));
    fingerprint.update(fs.readFileSync(path.join(root, "hardhat.galileo.config.js")));
    result.toolingHash = fingerprint.digest("hex");
    result.buildSpecification = { compiler: "0.8.24", evmVersion: "cancun", optimizerRuns: 200, artifacts: "artifacts-galileo", status: "Actual artifacts must be checked before future broadcasts" };
    result.evidenceSchema = { futureReceiptFields: ["step", "transactionHash", "blockNumber", "gasUsed", "effectiveGasPrice", "events", "readbacks", "explorerLink", "errorCode"], note: "No receipts/deployed addresses fabricated. Transaction resume is intentionally unavailable until future execution tooling is reviewed." };
    if (args.includes("--resume")) checkResume(JSON.parse(fs.readFileSync(option("--resume"), "utf8")), result);
    const out = option("--out", path.join(root, "galileo-local/preflight.json"));
    if (fs.existsSync(out)) throw new Error("STOP: output exists; choose a new evidence path");
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, JSON.stringify(result, null, 2) + "\n", { flag: "wx" });
    console.log(JSON.stringify({ status: result.status, chainId: result.chainId, block: result.observedBlock, counts: result.plan?.counts, failures: result.failures, transactionsSubmitted: 0 }, null, 2));
    if (!result.plan || result.checks.some(c => c.state === "FAIL")) process.exitCode = 2;
  } finally { provider.destroy(); }
}
if (require.main === module) main().catch(() => { console.error("STOP: preflight failed; no signing or broadcast attempted. Check configuration/connectivity without exposing secrets."); process.exitCode = 1; });
module.exports = { main };
