const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("RewardAccounting", function () {
  async function deployFixture() {
    const [owner, user1, user2, outsider] =
      await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const Mock = await ethers.getContractFactory("MockStrategyAdapter");
    const adapter = await Mock.deploy(ethers.ZeroAddress, false);

    const strategyId = ethers.id("REWARD_TEST_STRATEGY");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: ethers.parseEther("1000"),
      maxAllocationBps: 10000,
      asynchronous: false,
      active: true
    });

    const RewardToken = await ethers.getContractFactory("MockERC20");
    const rewardToken = await RewardToken.deploy();

    const Accounting = await ethers.getContractFactory("RewardAccounting");
    const accounting = await Accounting.deploy(
      owner.address,
      await vault.getAddress(),
      await manager.getAddress()
    );

    await vault.configureRewardAccounting(
      await accounting.getAddress()
    );

    await accounting.registerRewardToken(
      strategyId,
      await rewardToken.getAddress()
    );

    return {
      owner,
      user1,
      user2,
      outsider,
      vault,
      strategyId,
      rewardToken,
      accounting
    };
  }

  async function futureDeadline() {
    const block = await ethers.provider.getBlock("latest");
    return BigInt(block.timestamp + 3600);
  }

  async function allocate(vault, user, strategyId, amount) {
    await vault.connect(user).depositNative({ value: amount });
    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );
  }

  async function notifyTokenReward(
    owner,
    rewardToken,
    accounting,
    strategyId,
    amount
  ) {
    await rewardToken.mint(owner.address, amount);
    await rewardToken
      .connect(owner)
      .approve(await accounting.getAddress(), amount);

    await accounting
      .connect(owner)
      .notifyReward(
        strategyId,
        await rewardToken.getAddress(),
        amount
      );
  }

  it("checkpoints users with accumulative reward-per-share accounting", async function () {
    const {
      owner,
      user1,
      user2,
      vault,
      strategyId,
      rewardToken,
      accounting
    } = await deployFixture();

    const shares = ethers.parseEther("10");
    const reward = ethers.parseEther("100");

    await allocate(vault, user1, strategyId, shares);

    await notifyTokenReward(
      owner,
      rewardToken,
      accounting,
      strategyId,
      reward
    );

    await allocate(vault, user2, strategyId, shares);

    await notifyTokenReward(
      owner,
      rewardToken,
      accounting,
      strategyId,
      reward
    );

    expect(
      await accounting.claimable(
        user1.address,
        strategyId,
        await rewardToken.getAddress()
      )
    ).to.equal(ethers.parseEther("150"));

    expect(
      await accounting.claimable(
        user2.address,
        strategyId,
        await rewardToken.getAddress()
      )
    ).to.equal(ethers.parseEther("50"));

    await vault.connect(user1).claimRewards(
      strategyId,
      await rewardToken.getAddress(),
      user1.address
    );
    await vault.connect(user2).claimRewards(
      strategyId,
      await rewardToken.getAddress(),
      user2.address
    );

    expect(
      await rewardToken.balanceOf(user1.address)
    ).to.equal(ethers.parseEther("150"));

    expect(
      await rewardToken.balanceOf(user2.address)
    ).to.equal(ethers.parseEther("50"));
  });

  it("checkpoints accrued rewards before strategy shares decrease", async function () {
    const {
      owner,
      user1,
      vault,
      strategyId,
      rewardToken,
      accounting
    } = await deployFixture();

    const shares = ethers.parseEther("10");
    const reward = ethers.parseEther("100");

    await allocate(vault, user1, strategyId, shares);

    await notifyTokenReward(
      owner,
      rewardToken,
      accounting,
      strategyId,
      reward
    );

    await vault.connect(user1).requestStrategyWithdraw(
      strategyId,
      ethers.parseEther("5"),
      ethers.parseEther("5"),
      "0x"
    );

    expect(
      await accounting.totalStrategyShares(strategyId)
    ).to.equal(ethers.parseEther("5"));

    await notifyTokenReward(
      owner,
      rewardToken,
      accounting,
      strategyId,
      reward
    );

    expect(
      await accounting.claimable(
        user1.address,
        strategyId,
        await rewardToken.getAddress()
      )
    ).to.equal(ethers.parseEther("200"));
  });

  it("allows only the vault to synchronize user shares", async function () {
    const {
      outsider,
      accounting,
      strategyId
    } = await deployFixture();

    await expect(
      accounting.connect(outsider).syncUserShares(
        outsider.address,
        strategyId,
        1
      )
    ).to.be.revertedWithCustomError(
      accounting,
      "OnlyVault"
    );
  });

  it("rejects reward notifications from an unapproved notifier", async function () {
    const {
      user1,
      outsider,
      vault,
      strategyId,
      rewardToken,
      accounting
    } = await deployFixture();

    await allocate(
      vault,
      user1,
      strategyId,
      ethers.parseEther("1")
    );

    await rewardToken.mint(
      outsider.address,
      ethers.parseEther("1")
    );
    await rewardToken
      .connect(outsider)
      .approve(
        await accounting.getAddress(),
        ethers.parseEther("1")
      );

    await expect(
      accounting.connect(outsider).notifyReward(
        strategyId,
        await rewardToken.getAddress(),
        ethers.parseEther("1")
      )
    ).to.be.revertedWithCustomError(
      accounting,
      "UnauthorizedNotifier"
    );
  });

  it("keeps reward claims available while vault allocations are paused", async function () {
    const {
      owner,
      user1,
      vault,
      strategyId,
      rewardToken,
      accounting
    } = await deployFixture();

    await allocate(
      vault,
      user1,
      strategyId,
      ethers.parseEther("1")
    );

    await notifyTokenReward(
      owner,
      rewardToken,
      accounting,
      strategyId,
      ethers.parseEther("10")
    );

    await vault.connect(owner).pauseDepositsAndAllocations();

    await vault.connect(user1).claimRewards(
      strategyId,
      await rewardToken.getAddress(),
      user1.address
    );

    expect(
      await rewardToken.balanceOf(user1.address)
    ).to.equal(ethers.parseEther("10"));
  });

  it("locks reward-accounting configuration after allocation has started", async function () {
    const [owner, user] = await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const Mock = await ethers.getContractFactory("MockStrategyAdapter");
    const adapter = await Mock.deploy(ethers.ZeroAddress, false);
    const strategyId = ethers.id("NO_REWARD_YET");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: ethers.parseEther("10"),
      maxAllocationBps: 10000,
      asynchronous: false,
      active: true
    });

    await allocate(
      vault,
      user,
      strategyId,
      ethers.parseEther("1")
    );

    const Accounting = await ethers.getContractFactory("RewardAccounting");
    const accounting = await Accounting.deploy(
      owner.address,
      await vault.getAddress(),
      await manager.getAddress()
    );

    await expect(
      vault.configureRewardAccounting(
        await accounting.getAddress()
      )
    ).to.be.revertedWithCustomError(
      vault,
      "RewardAccountingConfigurationLocked"
    );
  });
});
