const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("StrategyManager", function () {
  async function deployFixture() {
    const [owner, other] = await ethers.getSigners();

    const Mock = await ethers.getContractFactory("MockStrategyAdapter");
    const adapter = await Mock.deploy(ethers.ZeroAddress, true);

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const strategyId = ethers.id("NATIVE_STAKE_0G");

    return { owner, other, adapter, manager, strategyId };
  }

  it("registers only adapters whose metadata matches the registry config", async function () {
    const { manager, adapter, strategyId } = await deployFixture();

    await expect(
      manager.registerStrategy(strategyId, {
        adapter: await adapter.getAddress(),
        inputAsset: ethers.ZeroAddress,
        depositCap: ethers.parseEther("1000000"),
        maxAllocationBps: 6000,
        asynchronous: true,
        active: true
      })
    ).to.emit(manager, "StrategyRegistered");

    const config = await manager.getStrategy(strategyId);
    expect(config.adapter).to.equal(await adapter.getAddress());
    expect(config.maxAllocationBps).to.equal(6000n);
    expect(config.asynchronous).to.equal(true);
    expect(config.active).to.equal(true);
  });

  it("rejects duplicate strategy IDs", async function () {
    const { manager, adapter, strategyId } = await deployFixture();

    const config = {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: 1000,
      maxAllocationBps: 6000,
      asynchronous: true,
      active: true
    };

    await manager.registerStrategy(strategyId, config);

    await expect(
      manager.registerStrategy(strategyId, config)
    ).to.be.revertedWithCustomError(
      manager,
      "StrategyAlreadyRegistered"
    );
  });

  it("rejects an adapter whose input asset does not match", async function () {
    const { manager, strategyId, other } = await deployFixture();

    const Mock = await ethers.getContractFactory("MockStrategyAdapter");
    const mismatched = await Mock.deploy(other.address, true);

    await expect(
      manager.registerStrategy(strategyId, {
        adapter: await mismatched.getAddress(),
        inputAsset: ethers.ZeroAddress,
        depositCap: 1000,
        maxAllocationBps: 6000,
        asynchronous: true,
        active: true
      })
    ).to.be.revertedWithCustomError(
      manager,
      "AdapterAssetMismatch"
    );
  });

  it("allows only the owner to change safety limits", async function () {
    const { manager, adapter, strategyId, other } = await deployFixture();

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: 1000,
      maxAllocationBps: 6000,
      asynchronous: true,
      active: true
    });

    await expect(
      manager.connect(other).updateLimits(
        strategyId,
        2000,
        5000,
        true
      )
    ).to.be.revertedWithCustomError(manager, "OwnableUnauthorizedAccount");

    await manager.updateLimits(strategyId, 2000, 5000, false);

    const config = await manager.getStrategy(strategyId);
    expect(config.depositCap).to.equal(2000n);
    expect(config.maxAllocationBps).to.equal(5000n);
    expect(config.active).to.equal(false);
  });
});
