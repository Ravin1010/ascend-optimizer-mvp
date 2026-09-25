const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("GimoAdapter", function () {
  async function deployFixture() {
    const [owner, user, other] = await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const Gimo = await ethers.getContractFactory(
      "MockGimoStakePool"
    );
    const gimo = await Gimo.deploy();

    const st0gAddress = await gimo.st0g();

    const Adapter = await ethers.getContractFactory(
      "GimoAdapter"
    );
    const adapter = await Adapter.deploy(
      await vault.getAddress(),
      await gimo.getAddress(),
      st0gAddress,
      "ascend"
    );

    const strategyId = ethers.id("GIMO_STAKE_0G");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: ethers.parseEther("1000"),
      maxAllocationBps: 10000,
      asynchronous: true,
      active: true
    });

    const St0G = await ethers.getContractFactory(
      "MockGimoSt0G"
    );
    const st0g = St0G.attach(st0gAddress);

    return {
      owner,
      user,
      other,
      manager,
      vault,
      gimo,
      st0g,
      adapter,
      strategyId
    };
  }

  async function futureDeadline() {
    const block = await ethers.provider.getBlock("latest");
    return BigInt(block.timestamp + 3600);
  }

  async function requestWithdrawal({
    user,
    vault,
    strategyId,
    shares,
    minAmountOut
  }) {
    const tx =
      await vault.connect(user).requestStrategyWithdraw(
        strategyId,
        shares,
        minAmountOut,
        "0x"
      );

    const receipt = await tx.wait();

    const event = receipt.logs
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

    return event.args.withdrawalKey;
  }

  it("stakes native 0G and records actual st0G shares", async function () {
    const {
      user,
      vault,
      gimo,
      st0g,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("10");

    await vault.connect(user).depositNative({
      value: amount
    });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    expect(await gimo.lastReferral()).to.equal("ascend");

    expect(
      await st0g.balanceOf(await adapter.getAddress())
    ).to.equal(amount);

    expect(
      await vault.strategySharesOf(
        user.address,
        strategyId
      )
    ).to.equal(amount);

    expect(await adapter.totalAssets()).to.equal(amount);
  });

  it("values st0G shares using the live exchange rate", async function () {
    const {
      user,
      vault,
      gimo,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("10");

    await vault.connect(user).depositNative({
      value: amount
    });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    await gimo.setRate(
      ethers.parseEther("1.1")
    );

    await gimo.fundRewards({
      value: ethers.parseEther("1")
    });

    expect(
      await adapter.previewRedeem(amount)
    ).to.equal(ethers.parseEther("11"));

    expect(
      await adapter.totalAssets()
    ).to.equal(ethers.parseEther("11"));
  });

  it("allows only AscendVault to execute Gimo operations", async function () {
    const {
      other,
      adapter
    } = await deployFixture();

    await expect(
      adapter.connect(other).deposit(
        1,
        1,
        "0x",
        { value: 1 }
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "OnlyVault"
    );

    await expect(
      adapter.connect(other).requestWithdraw(
        1,
        1,
        "0x"
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "OnlyVault"
    );
  });

  it("burns st0G at the request-time rate and preserves pending value", async function () {
    const {
      user,
      vault,
      gimo,
      st0g,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("10");
    const shares = ethers.parseEther("2");

    await vault.connect(user).depositNative({
      value: amount
    });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    await gimo.setRate(
      ethers.parseEther("1.1")
    );

    await gimo.fundRewards({
      value: ethers.parseEther("1")
    });

    const expected =
      ethers.parseEther("2.2");

    await requestWithdrawal({
      user,
      vault,
      strategyId,
      shares,
      minAmountOut: expected
    });

    expect(
      await st0g.balanceOf(await adapter.getAddress())
    ).to.equal(ethers.parseEther("8"));

    expect(
      await adapter.totalPendingWithdrawalAmount()
    ).to.equal(expected);

    expect(
      await adapter.totalAssets()
    ).to.equal(ethers.parseEther("11"));
  });

  it("serializes Gimo protocol withdrawals to avoid aggregate-claim ambiguity", async function () {
    const {
      user,
      vault,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("4");
    const shares = ethers.parseEther("1");

    await vault.connect(user).depositNative({
      value: amount
    });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    await requestWithdrawal({
      user,
      vault,
      strategyId,
      shares,
      minAmountOut: shares
    });

    await expect(
      vault.connect(user).requestStrategyWithdraw(
        strategyId,
        shares,
        shares,
        "0x"
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "PendingWithdrawalExists"
    );
  });

  it("completes Gimo's delayed withdrawal back to vault idle balance", async function () {
    const {
      user,
      vault,
      gimo,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("4");
    const shares = ethers.parseEther("1");

    await vault.connect(user).depositNative({
      value: amount
    });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    const withdrawalKey =
      await requestWithdrawal({
        user,
        vault,
        strategyId,
        shares,
        minAmountOut: shares
      });

    await expect(
      vault.connect(user).claimStrategyWithdraw(
        withdrawalKey,
        shares,
        "0x"
      )
    ).to.be.revertedWith("not ready");

    await gimo.setWithdrawalsReady(true);

    await vault.connect(user).claimStrategyWithdraw(
      withdrawalKey,
      shares,
      "0x"
    );

    expect(
      await vault.idleBalanceOf(
        user.address,
        ethers.ZeroAddress
      )
    ).to.equal(shares);

    expect(
      await adapter.totalPendingWithdrawalAmount()
    ).to.equal(0n);

    expect(
      await adapter.activeWithdrawalId()
    ).to.equal(ethers.ZeroHash);
  });

  it("rejects arbitrary protocol-specific call data", async function () {
    const {
      user,
      vault,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("1");

    await vault.connect(user).depositNative({
      value: amount
    });

    await expect(
      vault.connect(user).executeAllocation(
        strategyId,
        amount,
        amount,
        await futureDeadline(),
        "0x1234"
      )
    ).to.be.revertedWithCustomError(
      await ethers.getContractAt(
        "GimoAdapter",
        (await (await ethers.getContractFactory("StrategyManager")).attach ? ethers.ZeroAddress : ethers.ZeroAddress)
      ),
      "UnexpectedData"
    );
  });
});
