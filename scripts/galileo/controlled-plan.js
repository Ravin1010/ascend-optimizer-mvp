"use strict";
const { buildPlan, hash } = require("./plan");
const reviewed = Object.freeze(require("./reviewed-execution.json"));
const { formatEther } = require("ethers");
const GAS = [875337,2797009,474532,1219262,1303256,1356230,581777,512602,135859,234092,43910,1108105,305689,292101,68392,51292,2757165,2757177,581765,936505,528414,44084,1574126,147636,130447,130478,130478,130435,77824,241591,259588,495227,472794];
function stop(message) { throw new Error(`STOP: ${message}`); }
function controlledPlan(config = reviewed) {
  for (const key of Object.keys(config)) if (!(key in reviewed)) stop("unknown execution configuration field");
  for (const key of Object.keys(reviewed)) {
    if (["reserveBps", "gasMarginBps", "feeMultiplierBps"].includes(key)) continue;
    if (config[key] !== reviewed[key]) stop(`configuration/branch drift: ${key}`);
  }
  for (const [key, min, max] of [["reserveBps",2000,9000],["gasMarginBps",2000,5000],["feeMultiplierBps",10000,20000]]) {
    if (!Number.isInteger(config[key]) || config[key] < min || config[key] > max) stop(`invalid safety policy: ${key}`);
  }
  // buildPlan's legacy maxGasBudget field is required for syntax validation only.
  // The controlled engine never uses it as a spending limit; it derives the full envelope.
  const plan = buildPlan({ native: {branch:"MOCK"}, ascend: {branch:"MOCK"}, funding0g: formatEther(config.depositWei), allocation0g: formatEther(config.allocationWei), maxGasBudget0g:"0.218449824382287192", deployer:config.deployer, user:config.user });
  let i = 0;
  for (const step of plan.steps) if (step.kind !== "READ") step.referenceGas = GAS[i++];
  if (i !== 33 || plan.steps.find(s=>s.name === "register4").args[1].active) stop("unexpected graph/Ascend activation");
  return { config, plan, fingerprint: hash({config,plan}), transactionSteps: plan.steps.filter(s=>s.kind !== "READ") };
}
const ceilBps = (value, bps) => (BigInt(value) * BigInt(bps) + 9999n) / 10000n;
module.exports = { reviewed, controlledPlan, ceilBps, stop };
