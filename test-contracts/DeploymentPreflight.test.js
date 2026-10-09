// LOCAL_SIMULATION / STATICALLY_VALIDATED only. No public RPC or signing path.
const { expect } = require("chai");
const { artifacts, network } = require("hardhat");
const design = require("../data/intended_deployment_architecture.json");

const constructorTypes = {
  StrategyManager: ["address"],
  AscendVault: ["address", "address"],
  RewardAccounting: ["address", "address", "address"],
  Native0GStakingAdapter: ["address", "address", "address"],
  GimoAdapter: ["address", "address", "address", "string"],
  JaineLPAdapter: ["address", "address", "uint24", "int24", "int24", "uint160", "uint160", "uint16"],
  OkuV3Adapter: ["address", "address", "uint24", "int24", "int24", "uint160", "uint160", "uint16"],
  AscendProtocolAdapter: ["address", "address", "address"],
};

describe("Deployment-free architecture preflight (local only)", function () {
  before(function () {
    // This suite reads artifacts only; forbid interpreting it as public-chain validation.
    expect(network.name).to.equal("hardhat");
    expect(network.config.chainId).to.equal(31337);
  });

  for (const row of [...design.core, ...design.strategies]) {
    const name = row.adapter ?? row.component;
    it(`matches ${name} design inputs to the compiled constructor ABI`, async function () {
      const artifact = await artifacts.readArtifact(name);
      const constructor = artifact.abi.find((entry) => entry.type === "constructor");
      expect(constructor.inputs.map((input) => input.name)).to.deep.equal(row.constructor_inputs);
      expect(constructor.inputs.map((input) => input.type)).to.deep.equal(constructorTypes[name]);
      expect(artifact.bytecode).not.to.equal("0x");
    });
  }

  it("matches registration struct and vault/accounting authorization surfaces", async function () {
    const manager = await artifacts.readArtifact("StrategyManager");
    const registration = manager.abi.find((entry) => entry.name === "registerStrategy");
    expect(registration.inputs.map((input) => input.type)).to.deep.equal(["bytes32", "tuple"]);
    expect(registration.inputs[1].components.map((input) => input.name)).to.deep.equal([
      "adapter", "inputAsset", "depositCap", "maxAllocationBps", "asynchronous", "active",
    ]);
    for (const [name, functions] of [
      ["AscendVault", ["executeAllocation", "configureRewardAccounting", "requestStrategyWithdraw", "claimStrategyWithdraw"]],
      ["RewardAccounting", ["syncUserShares", "notifyReward", "claimFor"]],
    ]) {
      const artifact = await artifacts.readArtifact(name);
      for (const name of functions) expect(artifact.abi.some((entry) => entry.name === name)).to.equal(true);
    }
  });
});
