const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AscendVault", function () {
  async function deployNativeFixture({
    maxAllocationBps = 6000,
    depositCap = ethers.parseEther("100")
  } = {}) {
    const [owner, user, other] = await ethers.getSigners();

    const Mock = await ethers.getContractFactory("MockStrategyAdapter");
    const adapter = await Mock.deploy(ethers.ZeroAddress, true);

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const strategyId = ethers.id("NATIVE_STAKE_0G");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap,
      maxAllocationBps,
      asynchronous: true,
      active: true
    });

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    return {
      owner,
      user,
      other,
      adapter,
      manager,
      strategyId,
      vault
    };
  }

  async function futureDeadline() {
    const block = await ethers.provider.getBlock("latest");
    return BigInt(block.timestamp + 3600);
  }

  it("records native 0G as idle balance before allocation", async function () {
    const { user, vault } = await deployNativeFixture();
    const amount = ethers.parseEther("10");

    await expect(
      vault.connect(user).depositNative({ value: amount })
    )
      .to.emit(vault, "NativeDeposited")
      .withArgs(user.address, amount);

    expect(
      await vault.idleBalanceOf(user.address, ethers.ZeroAddress)
    ).to.equal(amount);

    expect(
      await vault.userAssetValue(user.address, ethers.ZeroAddress)
    ).to.equal(amount);
  });

  it("executes only the user's own authorized allocation", async function () {
    const { user, other, vault, adapter, strategyId } =
      await deployNativeFixture();

    const deposited = ethers.parseEther("10");
    const amount = ethers.parseEther("6");

    await vault.connect(user).depositNative({ value: deposited });

    await expect(
      vault.connect(other).executeAllocation(
        strategyId,
        amount,
        amount,
        await futureDeadline(),
        "0x"
      )
    ).to.be.revertedWithCustomError(
      vault,
      "InsufficientIdleBalance"
    );

    await expect(
      vault.connect(user).executeAllocation(
        strategyId,
        amount,
        amount,
        await futureDeadline(),
        "0x"
      )
    )
      .to.emit(vault, "AllocationExecuted")
      .withArgs(
        user.address,
        strategyId,
        ethers.ZeroAddress,
        amount,
        amount
      );

    expect(
      await vault.idleBalanceOf(user.address, ethers.ZeroAddress)
    ).to.equal(ethers.parseEther("4"));

    expect(
      await vault.strategySharesOf(user.address, strategyId)
    ).to.equal(amount);

    expect(await adapter.totalAssets()).to.equal(amount);
  });

  it("enforces the on-chain strategy allocation ceiling", async function () {
    const { user, vault, strategyId } =
      await deployNativeFixture({ maxAllocationBps: 6000 });

    const deposited = ethers.parseEther("10");

    await vault.connect(user).depositNative({ value: deposited });

    await vault.connect(user).executeAllocation(
      strategyId,
      ethers.parseEther("6"),
      ethers.parseEther("6"),
      await futureDeadline(),
      "0x"
    );

    await expect(
      vault.connect(user).executeAllocation(
        strategyId,
        ethers.parseEther("1"),
        ethers.parseEther("1"),
        await futureDeadline(),
        "0x"
      )
    ).to.be.revertedWithCustomError(
      vault,
      "StrategyAllocationCapExceeded"
    );
  });

  it("enforces the strategy-wide deposit cap", async function () {
    const { user, vault, strategyId } =
      await deployNativeFixture({
        maxAllocationBps: 10000,
        depositCap: ethers.parseEther("5")
      });

    await vault
      .connect(user)
      .depositNative({ value: ethers.parseEther("10") });

    await expect(
      vault.connect(user).executeAllocation(
        strategyId,
        ethers.parseEther("6"),
        ethers.parseEther("6"),
        await futureDeadline(),
        "0x"
      )
    ).to.be.revertedWithCustomError(
      vault,
      "StrategyDepositCapExceeded"
    );
  });

  it("rejects stale allocation instructions", async function () {
    const { user, vault, strategyId } =
      await deployNativeFixture();

    await vault
      .connect(user)
      .depositNative({ value: ethers.parseEther("1") });

    const block = await ethers.provider.getBlock("latest");

    await expect(
      vault.connect(user).executeAllocation(
        strategyId,
        ethers.parseEther("0.5"),
        ethers.parseEther("0.5"),
        BigInt(block.timestamp - 1),
        "0x"
      )
    ).to.be.revertedWithCustomError(
      vault,
      "AllocationExpired"
    );
  });

  it("supports approved ERC20 idle deposits and allocation", async function () {
    const [owner, user] = await ethers.getSigners();

    const Token = await ethers.getContractFactory("MockERC20");
    const token = await Token.deploy();

    const Mock = await ethers.getContractFactory("MockStrategyAdapter");
    const adapter = await Mock.deploy(
      await token.getAddress(),
      false
    );

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const strategyId = ethers.id("TOKEN_STRATEGY");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: await token.getAddress(),
      depositCap: ethers.parseEther("1000"),
      maxAllocationBps: 5000,
      asynchronous: false,
      active: true
    });

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const deposited = ethers.parseEther("100");
    const allocated = ethers.parseEther("50");

    await token.mint(user.address, deposited);
    await token
      .connect(user)
      .approve(await vault.getAddress(), deposited);

    await vault
      .connect(user)
      .depositToken(await token.getAddress(), deposited);

    await vault.connect(user).executeAllocation(
      strategyId,
      allocated,
      allocated,
      await futureDeadline(),
      "0x"
    );

    expect(
      await vault.idleBalanceOf(
        user.address,
        await token.getAddress()
      )
    ).to.equal(ethers.parseEther("50"));

    expect(
      await token.balanceOf(await adapter.getAddress())
    ).to.equal(allocated);

    expect(
      await vault.strategySharesOf(user.address, strategyId)
    ).to.equal(allocated);
  });

  it("settles a synchronous strategy withdrawal back to idle balance", async function () {
    const [owner, user] = await ethers.getSigners();

    const Token = await ethers.getContractFactory("MockERC20");
    const token = await Token.deploy();

    const Mock = await ethers.getContractFactory("MockStrategyAdapter");
    const adapter = await Mock.deploy(await token.getAddress(), false);

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);
    const strategyId = ethers.id("SYNC_TOKEN_STRATEGY");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: await token.getAddress(),
      depositCap: ethers.parseEther("1000"),
      maxAllocationBps: 10000,
      asynchronous: false,
      active: true
    });

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(owner.address, await manager.getAddress());

    const deposited = ethers.parseEther("100");
    const allocated = ethers.parseEther("60");
    const withdrawn = ethers.parseEther("20");

    await token.mint(user.address, deposited);
    await token.connect(user).approve(await vault.getAddress(), deposited);
    await vault.connect(user).depositToken(await token.getAddress(), deposited);

    await vault.connect(user).executeAllocation(
      strategyId,
      allocated,
      allocated,
      await futureDeadline(),
      "0x"
    );

    await expect(
      vault.connect(user).requestStrategyWithdraw(
        strategyId,
        withdrawn,
        withdrawn,
        "0x"
      )
    )
      .to.emit(vault, "StrategyWithdrawalCompleted")
      .withArgs(
        user.address,
        strategyId,
        await token.getAddress(),
        withdrawn,
        withdrawn
      );

    expect(
      await vault.strategySharesOf(user.address, strategyId)
    ).to.equal(ethers.parseEther("40"));

    expect(
      await vault.idleBalanceOf(user.address, await token.getAddress())
    ).to.equal(ethers.parseEther("60"));

    expect(await adapter.totalAssets()).to.equal(ethers.parseEther("40"));
  });

  it("records and claims an asynchronous native withdrawal", async function () {
    const { user, vault, adapter, strategyId } =
      await deployNativeFixture({ maxAllocationBps: 10000 });

    const deposited = ethers.parseEther("10");
    const allocated = ethers.parseEther("6");
    const withdrawn = ethers.parseEther("2");

    await vault.connect(user).depositNative({ value: deposited });
    await vault.connect(user).executeAllocation(
      strategyId,
      allocated,
      allocated,
      await futureDeadline(),
      "0x"
    );

    const tx = await vault.connect(user).requestStrategyWithdraw(
      strategyId,
      withdrawn,
      withdrawn,
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
      .find((parsed) => parsed && parsed.name === "StrategyWithdrawalRequested");

    const withdrawalKey = event.args.withdrawalKey;

    expect(
      await vault.strategySharesOf(user.address, strategyId)
    ).to.equal(ethers.parseEther("4"));

    expect(
      await vault.idleBalanceOf(user.address, ethers.ZeroAddress)
    ).to.equal(ethers.parseEther("4"));

    const pending = await vault.pendingWithdrawalOf(withdrawalKey);
    expect(pending.active).to.equal(true);
    expect(pending.user).to.equal(user.address);
    expect(pending.shares).to.equal(withdrawn);

    await expect(
      vault.connect(user).claimStrategyWithdraw(
        withdrawalKey,
        withdrawn,
        "0x"
      )
    )
      .to.emit(vault, "StrategyWithdrawalClaimed")
      .withArgs(
        user.address,
        strategyId,
        withdrawalKey,
        ethers.ZeroAddress,
        withdrawn,
        withdrawn
      );

    expect(
      await vault.idleBalanceOf(user.address, ethers.ZeroAddress)
    ).to.equal(ethers.parseEther("6"));

    expect(await adapter.totalAssets()).to.equal(ethers.parseEther("4"));

    const cleared = await vault.pendingWithdrawalOf(withdrawalKey);
    expect(cleared.active).to.equal(false);
  });

  it("prevents another user from claiming a pending withdrawal", async function () {
    const { user, other, vault, strategyId } =
      await deployNativeFixture({ maxAllocationBps: 10000 });

    const amount = ethers.parseEther("2");

    await vault.connect(user).depositNative({ value: amount });
    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    const tx = await vault.connect(user).requestStrategyWithdraw(
      strategyId,
      ethers.parseEther("1"),
      ethers.parseEther("1"),
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
      .find((parsed) => parsed && parsed.name === "StrategyWithdrawalRequested");

    await expect(
      vault.connect(other).claimStrategyWithdraw(
        event.args.withdrawalKey,
        ethers.parseEther("1"),
        "0x"
      )
    ).to.be.revertedWithCustomError(
      vault,
      "PendingWithdrawalNotOwned"
    );
  });

  it("does not allow claim-time minimum protection to be weakened", async function () {
    const { user, vault, strategyId } =
      await deployNativeFixture({ maxAllocationBps: 10000 });

    const amount = ethers.parseEther("2");
    const minimum = ethers.parseEther("1");

    await vault.connect(user).depositNative({ value: amount });
    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    const tx = await vault.connect(user).requestStrategyWithdraw(
      strategyId,
      minimum,
      minimum,
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
      .find((parsed) => parsed && parsed.name === "StrategyWithdrawalRequested");

    await expect(
      vault.connect(user).claimStrategyWithdraw(
        event.args.withdrawalKey,
        ethers.parseEther("0.9"),
        "0x"
      )
    ).to.be.revertedWithCustomError(
      vault,
      "MinimumAmountBelowRequest"
    );
  });

  it("keeps strategy withdrawal and claim available while allocations are paused", async function () {
    const { owner, user, vault, strategyId } =
      await deployNativeFixture({ maxAllocationBps: 10000 });

    const amount = ethers.parseEther("2");

    await vault.connect(user).depositNative({ value: amount });
    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    await vault.connect(owner).pauseDepositsAndAllocations();

    const tx = await vault.connect(user).requestStrategyWithdraw(
      strategyId,
      amount,
      amount,
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
      .find((parsed) => parsed && parsed.name === "StrategyWithdrawalRequested");

    await vault.connect(user).claimStrategyWithdraw(
      event.args.withdrawalKey,
      amount,
      "0x"
    );

    expect(
      await vault.idleBalanceOf(user.address, ethers.ZeroAddress)
    ).to.equal(amount);
  });

  it("keeps idle withdrawals available while new deposits are paused", async function () {
    const { owner, user, vault } = await deployNativeFixture();

    const amount = ethers.parseEther("1");
    await vault.connect(user).depositNative({ value: amount });

    await vault.connect(owner).pauseDepositsAndAllocations();

    await expect(
      vault.connect(user).depositNative({ value: 1 })
    ).to.be.revertedWithCustomError(vault, "EnforcedPause");

    const before = await ethers.provider.getBalance(user.address);

    const tx = await vault.connect(user).withdrawIdle(
      ethers.ZeroAddress,
      amount,
      user.address
    );
    const receipt = await tx.wait();
    const gas = receipt.gasUsed * receipt.gasPrice;

    const after = await ethers.provider.getBalance(user.address);

    expect(after + gas - before).to.equal(amount);
    expect(
      await vault.idleBalanceOf(user.address, ethers.ZeroAddress)
    ).to.equal(0n);
  });
});
