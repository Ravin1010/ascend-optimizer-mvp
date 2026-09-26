const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AscendProtocolAdapter", function () {
  async function deployFixture() {
    const [owner, user, user2, other] = await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const W0G = await ethers.getContractFactory("MockAscendW0G");
    const w0g = await W0G.deploy();

    const SourceCore = await ethers.getContractFactory(
      "MockAscendSourceCore"
    );
    const sourceCore = await SourceCore.deploy(
      await w0g.getAddress()
    );

    const Queue = await ethers.getContractFactory(
      "MockAscendWithdrawalQueue"
    );
    const queue = await Queue.deploy(
      await sourceCore.getAddress(),
      await w0g.getAddress()
    );

    await sourceCore.setWithdrawalQueue(
      await queue.getAddress()
    );

    const Adapter = await ethers.getContractFactory(
      "AscendProtocolAdapter"
    );
    const adapter = await Adapter.deploy(
      await vault.getAddress(),
      await sourceCore.getAddress(),
      await w0g.getAddress()
    );

    const strategyId = ethers.id("ASCEND_STAKE_A0G");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: ethers.parseEther("10000"),
      maxAllocationBps: 10000,
      asynchronous: true,
      active: true
    });

    return {
      owner,
      user,
      user2,
      other,
      manager,
      vault,
      w0g,
      sourceCore,
      queue,
      adapter,
      strategyId
    };
  }

  async function deadline() {
    const block = await ethers.provider.getBlock("latest");
    return BigInt(block.timestamp + 3600);
  }

  async function allocate({
    user,
    vault,
    strategyId,
    amount
  }) {
    await vault.connect(user).depositNative({
      value: amount
    });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      1,
      await deadline(),
      "0x"
    );
  }

  async function request({
    user,
    vault,
    strategyId,
    shares,
    minAmountOut = 1n
  }) {
    const tx = await vault.connect(user).requestStrategyWithdraw(
      strategyId,
      shares,
      minAmountOut,
      "0x"
    );

    const receipt = await tx.wait();

    const parsed = receipt.logs
      .map((log) => {
        try {
          return vault.interface.parseLog(log);
        } catch {
          return null;
        }
      })
      .find(
        (event) =>
          event &&
          event.name === "StrategyWithdrawalRequested"
      );

    return parsed.args.withdrawalKey;
  }

  it("wraps native 0G and deposits W0G into live-style a0G SourceCore", async function () {
    const {
      user,
      vault,
      sourceCore,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("10");

    await allocate({
      user,
      vault,
      strategyId,
      amount
    });

    const shares = await vault.strategySharesOf(
      user.address,
      strategyId
    );

    expect(shares).to.equal(amount);
    expect(
      await sourceCore.balanceOf(
        await adapter.getAddress()
      )
    ).to.equal(amount);

    expect(await adapter.totalAssets()).to.equal(amount);
  });

  it("values strategy shares using the live a0G exchange rate", async function () {
    const {
      user,
      vault,
      w0g,
      sourceCore,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("10");

    await allocate({
      user,
      vault,
      strategyId,
      amount
    });

    await sourceCore.setRate(
      ethers.parseEther("1.1")
    );

    await w0g.mint(
      await sourceCore.getAddress(),
      ethers.parseEther("1")
    );

    expect(
      await adapter.previewRedeem(amount)
    ).to.equal(ethers.parseEther("11"));

    expect(
      await adapter.totalAssets()
    ).to.equal(ethers.parseEther("11"));
  });

  it("uses the protocol epoch queue for asynchronous withdrawals", async function () {
    const {
      user,
      vault,
      queue,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("4");

    await allocate({
      user,
      vault,
      strategyId,
      amount
    });

    const shares = await vault.strategySharesOf(
      user.address,
      strategyId
    );

    const key = await request({
      user,
      vault,
      strategyId,
      shares
    });

    const pending = await adapter.pendingRequestOf(
      (await vault.pendingWithdrawalOf(key)).adapterRequestId
    );

    expect(pending.active).to.equal(true);
    expect(pending.epoch).to.equal(0n);

    expect(
      await queue.sharesOf(
        0,
        await adapter.getAddress()
      )
    ).to.equal(shares);
  });

  it("settles one protocol epoch once and distributes same-epoch claims pro rata", async function () {
    const {
      user,
      user2,
      vault,
      w0g,
      sourceCore,
      queue,
      adapter,
      strategyId
    } = await deployFixture();

    const amount1 = ethers.parseEther("6");
    const amount2 = ethers.parseEther("4");

    await allocate({
      user,
      vault,
      strategyId,
      amount: amount1
    });

    await allocate({
      user: user2,
      vault,
      strategyId,
      amount: amount2
    });

    await sourceCore.setRate(
      ethers.parseEther("1.1")
    );

    await w0g.mint(
      await sourceCore.getAddress(),
      ethers.parseEther("1")
    );

    const shares1 = await vault.strategySharesOf(
      user.address,
      strategyId
    );
    const shares2 = await vault.strategySharesOf(
      user2.address,
      strategyId
    );

    const key1 = await request({
      user,
      vault,
      strategyId,
      shares: shares1,
      minAmountOut: ethers.parseEther("6.5")
    });

    const key2 = await request({
      user: user2,
      vault,
      strategyId,
      shares: shares2,
      minAmountOut: ethers.parseEther("4.3")
    });

    await expect(
      vault.connect(user).claimStrategyWithdraw(
        key1,
        ethers.parseEther("6.5"),
        "0x"
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "WithdrawalNotReady"
    );

    await queue.setReady(true);

    await vault.connect(user).claimStrategyWithdraw(
      key1,
      ethers.parseEther("6.5"),
      "0x"
    );

    const idle1 = await vault.idleBalanceOf(
      user.address,
      ethers.ZeroAddress
    );

    expect(idle1).to.equal(
      ethers.parseEther("6.6")
    );

    const epoch = await adapter.epochStateOf(0);
    expect(epoch.settled).to.equal(true);
    expect(epoch.claimedAssets).to.equal(
      ethers.parseEther("11")
    );

    await vault.connect(user2).claimStrategyWithdraw(
      key2,
      ethers.parseEther("4.3"),
      "0x"
    );

    const idle2 = await vault.idleBalanceOf(
      user2.address,
      ethers.ZeroAddress
    );

    expect(idle2).to.equal(
      ethers.parseEther("4.4")
    );

    expect(
      await adapter.pendingWithdrawalEstimate()
    ).to.equal(0n);
  });

  it("allows only AscendVault to execute the live protocol adapter", async function () {
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
});
