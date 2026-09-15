const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AscendStakingAdapter", function () {
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

    const nextNonce = await ethers.provider.getTransactionCount(
      owner.address
    );
    const predictedAdapter = ethers.getCreateAddress({
      from: owner.address,
      nonce: nextNonce + 1
    });

    const Token = await ethers.getContractFactory("A0GToken");
    const a0g = await Token.deploy(
      owner.address,
      predictedAdapter
    );

    const Adapter = await ethers.getContractFactory(
      "AscendStakingAdapter"
    );
    const adapter = await Adapter.deploy(
      owner.address,
      await vault.getAddress(),
      await validator.getAddress(),
      await a0g.getAddress()
    );

    expect(await adapter.getAddress()).to.equal(predictedAdapter);

    const strategyId = ethers.id("ASCEND_STAKE_A0G");

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
      a0g,
      adapter,
      strategyId
    };
  }

  async function futureDeadline() {
    const block = await ethers.provider.getBlock("latest");
    return BigInt(block.timestamp + 3600);
  }

  it("mints adapter-held a0G 1:1 for vault-managed principal", async function () {
    const {
      user,
      vault,
      validator,
      a0g,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("10");

    expect(await adapter.issuerConfigured()).to.equal(true);

    await vault.connect(user).depositNative({ value: amount });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    const adapterAddress = await adapter.getAddress();
    const delegation = await validator.getDelegation(
      adapterAddress
    );

    expect(delegation[1]).to.equal(amount);
    expect(await a0g.balanceOf(adapterAddress)).to.equal(amount);
    expect(await a0g.balanceOf(user.address)).to.equal(0n);
    expect(await adapter.totalPrincipalShares()).to.equal(amount);
    expect(
      await vault.strategySharesOf(user.address, strategyId)
    ).to.equal(amount);
    expect(await adapter.previewRedeem(amount)).to.equal(amount);
  });

  it("allows only the vault to execute staking operations", async function () {
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

  it("burns a0G when principal enters the async withdrawal queue", async function () {
    const {
      user,
      vault,
      a0g,
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

    await vault.connect(user).requestStrategyWithdraw(
      strategyId,
      withdrawn,
      withdrawn,
      "0x"
    );

    expect(await adapter.totalPrincipalShares()).to.equal(
      ethers.parseEther("3")
    );
    expect(
      await a0g.balanceOf(await adapter.getAddress())
    ).to.equal(ethers.parseEther("3"));
    expect(
      await vault.strategySharesOf(user.address, strategyId)
    ).to.equal(ethers.parseEther("3"));
    expect(
      await adapter.totalPendingWithdrawalAmount()
    ).to.equal(withdrawn);
  });

  it("completes the async a0G redemption lifecycle back to vault idle balance", async function () {
    const {
      user,
      vault,
      validator,
      a0g,
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
      await a0g.balanceOf(await adapter.getAddress())
    ).to.equal(ethers.parseEther("3"));

    expect(await adapter.totalPrincipalShares()).to.equal(
      ethers.parseEther("3")
    );
    expect(
      await adapter.totalPendingWithdrawalAmount()
    ).to.equal(0n);
  });

  it("requires the explicit withdrawal-fee reserve", async function () {
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
});
