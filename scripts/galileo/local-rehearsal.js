"use strict";
const { resolve } = require("./plan");
// Used only by local tests. Never reachable from run.js.
async function rehearse(hre, plan) {
  if ((await hre.ethers.provider.getNetwork()).chainId !== 31337n || hre.network.name !== "hardhat") throw new Error("STOP: local rehearsal requires in-process Hardhat 31337");
  if (Object.values(plan.composition).some(v => v !== "MOCK")) throw new Error("STOP: local rehearsal accepts mocks only");
  const [owner, user] = await hre.ethers.getSigners();
  const state = { owner: owner.address, deadline: BigInt((await hre.ethers.provider.getBlock("latest")).timestamp + 3600) };
  const contracts = {}; let transactions = 0;
  for (const step of plan.steps) {
    const args = resolve(step.args, state);
    if (step.kind === "DEPLOY") {
      const factory = await hre.ethers.getContractFactory(step.contract);
      const c = await factory.deploy(...args); await c.waitForDeployment();
      contracts[step.name] = c; state[step.name] = await c.getAddress(); transactions++;
    } else {
      const c = Object.values(contracts).find(c => c.target === resolve(step.target, state));
      if (step.kind === "READ") state[step.name] = await c[step.method](...args);
      else {
        const connected = step.kind === "INTERACT" ? c.connect(user) : c;
        await (await connected[step.method](...args, { value: step.value || 0 })).wait(); transactions++;
      }
    }
  }
  return { contracts, state, transactions, user };
}
module.exports = { rehearse };
