const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Native0GStakingAdapter", function () {
  async function deployFixture() {
    const [owner, user, other] = await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const Validator = await ethers.getContractFactory("Mock0GValidator");
    const validator = await Validator.deploy(1);

    const Adapter = await ethers.getContractFactory(
      "Native0GStakingAdapter"
    );
    const adapter = await Adapter.deploy(
      owner.address,
      await vault.getAddress(),
      await validator.getAddress()
    );

    const strategyId = ethers.id("NATIVE_STAKE_0G");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: ethers.parseEther("1000"),
      maxAllocationBps: 10000,
      asynchronous: true,
      active: true
    });

    return {
      owner,
      user,
      other,
      manager,
      vault,
      validator,
      adapter,
      strategyId
    };
  }

  async function futureDeadline() {
    const block = await ethers.provider.getBlock("latest");
    return BigInt(block.timestamp + 3600);
  }

  it("delegates native 0G and reports validator shares to the vault", async function () {
    const { user, vault, validator, adapter, strategyId } =
      await deployFixture();

    const amount = ethers.parseEther("10");

    await vault.connect(user).depositNative({ value: amount });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    const delegation = await validator.getDelegation(
      await adapter.getAddress()
    );

    expect(delegation[1]).to.equal(amount);
    expect(
      await vault.strategySharesOf(user.address, strategyId)
    ).to.equal(amount);
    expect(await adapter.totalAssets()).to.equal(amount);
  });

  it("allows only the vault to execute strategy operations", async function () {
    const { other, adapter } = await deployFixture();

    await expect(
      adapter.connect(other).deposit(
        1,
        1,
        "0x",
        { value: 1 }
      )
    ).to.be.revertedWithCustomError(adapter, "OnlyVault");

    await expect(
      adapter.connect(other).requestWithdraw(
        1,
        1,
        "0x"
      )
    ).to.be.revertedWithCustomError(adapter, "OnlyVault");
  });

  it("requires an explicit withdrawal-fee reserve", async function () {
    const { user, vault, adapter, strategyId } =
      await deployFixture();

    const amount = ethers.parseEther("2");

    await vault.connect(user).depositNative({ value: amount });
    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    await expect(
      vault.connect(user).requestStrategyWithdraw(
        strategyId,
        ethers.parseEther("1"),
        ethers.parseEther("1"),
        "0x"
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "InsufficientFeeReserve"
    );
  });

  it("completes the official async undelegation lifecycle", async function () {
    const {
      user,
      vault,
      validator,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("4");
    const withdrawn = ethers.parseEther("1");
    const fee = ethers.parseUnits("1", "gwei");

    await adapter.fundFeeReserve({ value: fee });

    await vault.connect(user).depositNative({ value: amount });
    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    const requestTx =
      await vault.connect(user).requestStrategyWithdraw(
        strategyId,
        withdrawn,
        withdrawn,
        "0x"
      );
    const receipt = await requestTx.wait();

    const requestEvent = receipt.logs
      .map((log) => {
        try {
          return vault.interface.parseLog(log);
        } catch {
          return null;
        }
      })
      .find(
        (parsed) =>
          parsed &&
          parsed.name === "StrategyWithdrawalRequested"
      );

    const withdrawalKey =
      requestEvent.args.withdrawalKey;

    expect(await adapter.feeReserveWei()).to.equal(0n);
    expect(
      await adapter.totalPendingWithdrawalAmount()
    ).to.equal(withdrawn);
    expect(await adapter.totalAssets()).to.equal(amount);

    await expect(
      vault.connect(user).claimStrategyWithdraw(
        withdrawalKey,
        withdrawn,
        "0x"
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "InsufficientWithdrawalLiquidity"
    );

    await validator.setWithdrawalsReady(true);

    await vault.connect(user).claimStrategyWithdraw(
      withdrawalKey,
      withdrawn,
      "0x"
    );

    expect(
      await vault.idleBalanceOf(
        user.address,
        ethers.ZeroAddress
      )
    ).to.equal(withdrawn);

    expect(
      await adapter.totalPendingWithdrawalAmount()
    ).to.equal(0n);

    expect(await adapter.totalAssets()).to.equal(
      ethers.parseEther("3")
    );
  });

  it("keeps fee reserve separate from staking withdrawal liquidity", async function () {
    const { adapter } = await deployFixture();

    const feeReserve = ethers.parseEther("0.01");
    await adapter.fundFeeReserve({ value: feeReserve });

    expect(await adapter.feeReserveWei()).to.equal(feeReserve);
    expect(await adapter.withdrawalLiquidity()).to.equal(0n);
  });

  it("lets only the owner recover unused fee reserve", async function () {
    const { owner, other, adapter } = await deployFixture();

    const reserve = ethers.parseEther("0.01");
    await adapter.fundFeeReserve({ value: reserve });

    await expect(
      adapter.connect(other).withdrawFeeReserve(
        other.address,
        reserve
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "OwnableUnauthorizedAccount"
    );

    await adapter.connect(owner).withdrawFeeReserve(
      owner.address,
      reserve
    );

    expect(await adapter.feeReserveWei()).to.equal(0n);
  });
});
