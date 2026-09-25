const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("V3LiquidityAdapter", function () {
  const Q96 = 2n ** 96n;
  const FEE = 3000;
  const TICK_LOWER = -600;
  const TICK_UPPER = 600;
  const SQRT_LOWER = Q96 / 2n;
  const SQRT_UPPER = Q96 * 2n;

  async function deployFixture({ routerMode = 0 } = {}) {
    const [owner, user, user2, other] = await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const W0G = await ethers.getContractFactory("MockW0G");
    const w0g = await W0G.deploy();

    const USDC = await ethers.getContractFactory("MockUSDCe");
    const usdce = await USDC.deploy();

    const Factory = await ethers.getContractFactory("MockV3Factory");
    const factory = await Factory.deploy();

    const Pool = await ethers.getContractFactory("MockV3Pool");
    const pool = await Pool.deploy(
      await factory.getAddress(),
      await w0g.getAddress(),
      await usdce.getAddress(),
      FEE
    );

    await factory.setPool(await pool.getAddress());

    const PositionManager = await ethers.getContractFactory(
      "MockV3PositionManager"
    );
    const positionManager = await PositionManager.deploy(
      await factory.getAddress()
    );

    let router;
    if (routerMode === 0) {
      const Router = await ethers.getContractFactory("MockV3RouterV1");
      router = await Router.deploy(await factory.getAddress());
    } else {
      const Router = await ethers.getContractFactory("MockV3Router02");
      router = await Router.deploy(await factory.getAddress());
    }

    // Seed the mock router with both output assets for deterministic 1:1 swaps.
    await w0g.mint(
      await router.getAddress(),
      ethers.parseEther("1000")
    );
    await usdce.mint(
      await router.getAddress(),
      ethers.parseEther("1000")
    );

    const Adapter = await ethers.getContractFactory(
      "V3LiquidityAdapter"
    );

    const adapter = await Adapter.deploy(
      await vault.getAddress(),
      await factory.getAddress(),
      await router.getAddress(),
      await positionManager.getAddress(),
      await pool.getAddress(),
      await w0g.getAddress(),
      await usdce.getAddress(),
      FEE,
      TICK_LOWER,
      TICK_UPPER,
      SQRT_LOWER,
      SQRT_UPPER,
      routerMode
    );

    const strategyId = ethers.id(
      routerMode === 0
        ? "JAINE_LP_0G_USDC"
        : "OKU_LP_0G_USDC"
    );

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: ethers.parseEther("10000"),
      maxAllocationBps: 10000,
      asynchronous: false,
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
      usdce,
      factory,
      pool,
      positionManager,
      router,
      adapter,
      strategyId
    };
  }

  async function deadline() {
    const block = await ethers.provider.getBlock("latest");
    return BigInt(block.timestamp + 3600);
  }

  async function data({
    swapMin = 1n,
    amount0Min = 1n,
    amount1Min = 1n,
    deadlineValue
  } = {}) {
    return ethers.AbiCoder.defaultAbiCoder().encode(
      ["uint256", "uint256", "uint256", "uint256"],
      [
        swapMin,
        amount0Min,
        amount1Min,
        deadlineValue ?? await deadline()
      ]
    );
  }

  async function allocate({
    user,
    vault,
    strategyId,
    amount,
    minShares = 1n
  }) {
    await vault.connect(user).depositNative({
      value: amount
    });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      minShares,
      await deadline(),
      await data()
    );
  }

  it("executes a Jaine-style V1-router LP deposit with immutable venue metadata", async function () {
    const {
      user,
      vault,
      adapter,
      positionManager,
      strategyId
    } = await deployFixture({ routerMode: 0 });

    const amount = ethers.parseEther("10");

    await allocate({
      user,
      vault,
      strategyId,
      amount
    });

    expect(await adapter.tokenId()).to.equal(1n);
    expect(await adapter.totalStrategyShares()).to.be.gt(0n);
    expect(
      await vault.strategySharesOf(
        user.address,
        strategyId
      )
    ).to.equal(await adapter.totalStrategyShares());

    const position = await positionManager.positions(1);
    expect(position[7]).to.be.gt(0n);
  });

  it("executes the same LP lifecycle through a Router02 deployment", async function () {
    const {
      user,
      vault,
      adapter,
      strategyId
    } = await deployFixture({ routerMode: 1 });

    await allocate({
      user,
      vault,
      strategyId,
      amount: ethers.parseEther("6")
    });

    expect(await adapter.tokenId()).to.equal(1n);
    expect(
      await vault.strategySharesOf(
        user.address,
        strategyId
      )
    ).to.be.gt(0n);
  });

  it("mints later shares against NAV so earlier accrued fees are not diluted", async function () {
    const {
      owner,
      user,
      user2,
      vault,
      w0g,
      usdce,
      positionManager,
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

    const firstShares =
      await vault.strategySharesOf(
        user.address,
        strategyId
      );

    const feeAmount = ethers.parseEther("1");
    await w0g.mint(owner.address, feeAmount);
    await usdce.mint(owner.address, feeAmount);

    await w0g.approve(
      await positionManager.getAddress(),
      feeAmount
    );
    await usdce.approve(
      await positionManager.getAddress(),
      feeAmount
    );

    await positionManager.addFees(
      1,
      feeAmount,
      feeAmount
    );

    const navWithFees =
      await adapter.totalAssets();

    await allocate({
      user: user2,
      vault,
      strategyId,
      amount
    });

    const secondShares =
      await vault.strategySharesOf(
        user2.address,
        strategyId
      );

    expect(navWithFees).to.be.gt(firstShares);
    expect(secondShares).to.be.lt(firstShares);
  });

  it("a partial withdrawal cannot sweep fees belonging to remaining shares", async function () {
    const {
      owner,
      user,
      user2,
      vault,
      w0g,
      usdce,
      positionManager,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("10");

    await allocate({ user, vault, strategyId, amount });
    await allocate({ user: user2, vault, strategyId, amount });

    const feeAmount = ethers.parseEther("2");
    await w0g.mint(owner.address, feeAmount);
    await usdce.mint(owner.address, feeAmount);
    await w0g.approve(
      await positionManager.getAddress(),
      feeAmount
    );
    await usdce.approve(
      await positionManager.getAddress(),
      feeAmount
    );

    await positionManager.addFees(
      1,
      feeAmount,
      feeAmount
    );

    const userShares =
      await vault.strategySharesOf(
        user.address,
        strategyId
      );

    const halfShares = userShares / 2n;

    await vault.connect(user).requestStrategyWithdraw(
      strategyId,
      halfShares,
      1,
      await data()
    );

    const position = await positionManager.positions(1);

    // Some fee entitlement must remain attached to the pooled NFT.
    expect(position[10]).to.be.gt(0n);
    expect(position[11]).to.be.gt(0n);
    expect(await adapter.totalStrategyShares()).to.be.gt(0n);
  });

  it("unwinds synchronously and returns native 0G to the user's idle balance", async function () {
    const {
      user,
      vault,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("8");

    await allocate({
      user,
      vault,
      strategyId,
      amount
    });

    const shares =
      await vault.strategySharesOf(
        user.address,
        strategyId
      );

    const idleBefore =
      await vault.idleBalanceOf(
        user.address,
        ethers.ZeroAddress
      );

    await vault.connect(user).requestStrategyWithdraw(
      strategyId,
      shares,
      1,
      await data()
    );

    const idleAfter =
      await vault.idleBalanceOf(
        user.address,
        ethers.ZeroAddress
      );

    expect(idleAfter).to.be.gt(idleBefore);
    expect(
      await vault.strategySharesOf(
        user.address,
        strategyId
      )
    ).to.equal(0n);
    expect(await adapter.totalStrategyShares()).to.equal(0n);
  });

  it("rejects malformed execution data and stale adapter deadlines", async function () {
    const {
      user,
      vault,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("2");

    await vault.connect(user).depositNative({
      value: amount
    });

    await expect(
      vault.connect(user).executeAllocation(
        strategyId,
        amount,
        1,
        await deadline(),
        "0x1234"
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "InvalidExecutionData"
    );

    const block = await ethers.provider.getBlock("latest");
    const stale = BigInt(block.timestamp - 1);

    await expect(
      vault.connect(user).executeAllocation(
        strategyId,
        amount,
        1,
        await deadline(),
        await data({ deadlineValue: stale })
      )
    ).to.be.revertedWithCustomError(
      adapter,
      "AllocationExpired"
    );
  });

  it("rejects a pool that is not the factory's configured pair", async function () {
    const [owner] = await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const W0G = await ethers.getContractFactory("MockW0G");
    const w0g = await W0G.deploy();

    const USDC = await ethers.getContractFactory("MockUSDCe");
    const usdce = await USDC.deploy();

    const Factory = await ethers.getContractFactory("MockV3Factory");
    const factory = await Factory.deploy();

    const Pool = await ethers.getContractFactory("MockV3Pool");
    const pool = await Pool.deploy(
      await factory.getAddress(),
      await w0g.getAddress(),
      await usdce.getAddress(),
      FEE
    );

    const otherPool = await Pool.deploy(
      await factory.getAddress(),
      await w0g.getAddress(),
      await usdce.getAddress(),
      FEE
    );

    await factory.setPool(await pool.getAddress());

    const PositionManager = await ethers.getContractFactory(
      "MockV3PositionManager"
    );
    const positionManager = await PositionManager.deploy(
      await factory.getAddress()
    );

    const Router = await ethers.getContractFactory("MockV3RouterV1");
    const router = await Router.deploy(await factory.getAddress());

    const Adapter = await ethers.getContractFactory(
      "V3LiquidityAdapter"
    );

    await expect(
      Adapter.deploy(
        await vault.getAddress(),
        await factory.getAddress(),
        await router.getAddress(),
        await positionManager.getAddress(),
        await otherPool.getAddress(),
        await w0g.getAddress(),
        await usdce.getAddress(),
        FEE,
        TICK_LOWER,
        TICK_UPPER,
        SQRT_LOWER,
        SQRT_UPPER,
        0
      )
    ).to.be.revertedWithCustomError(
      Adapter,
      "InvalidPool"
    );
  });
});
