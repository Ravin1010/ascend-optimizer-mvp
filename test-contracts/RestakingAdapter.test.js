const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("RestakingAdapter", function () {
  async function deployFixture({ asyncMode = true } = {}) {
    const [owner, user, other] = await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const Connector = await ethers.getContractFactory(
      "MockRestakingConnector"
    );
    const connector = await Connector.deploy(
      ethers.ZeroAddress,
      asyncMode
    );

    const Adapter = await ethers.getContractFactory(
      "RestakingAdapter"
    );
    const adapter = await Adapter.deploy(
      await vault.getAddress(),
      await connector.getAddress(),
      ethers.ZeroAddress,
      asyncMode
    );

    const strategyId = ethers.id("ASCEND_RESTAKE");

    await manager.registerStrategy(strategyId, {
      adapter: await adapter.getAddress(),
      inputAsset: ethers.ZeroAddress,
      depositCap: ethers.parseEther("1000"),
      maxAllocationBps: 10000,
      asynchronous: asyncMode,
      active: true
    });

    return {
      owner,
      user,
      other,
      manager,
      vault,
      connector,
      adapter,
      strategyId
    };
  }

  async function futureDeadline() {
    const block = await ethers.provider.getBlock("latest");
    return BigInt(block.timestamp + 3600);
  }

  it("forwards native 0G into the fixed connector and returns connector shares", async function () {
    const {
      user,
      vault,
      connector,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("5");

    await vault.connect(user).depositNative({ value: amount });

    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x1234"
    );

    expect(await connector.managedAssets()).to.equal(amount);
    expect(await adapter.totalAssets()).to.equal(amount);
    expect(
      await vault.strategySharesOf(user.address, strategyId)
    ).to.equal(amount);
  });

  it("allows only AscendVault to call execution functions", async function () {
    const { other, adapter } = await deployFixture();

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

  it("completes an asynchronous restaking withdrawal through the vault", async function () {
    const {
      user,
      vault,
      connector,
      adapter,
      strategyId
    } = await deployFixture();

    const amount = ethers.parseEther("4");
    const withdrawn = ethers.parseEther("1");

    await vault.connect(user).depositNative({ value: amount });
    await vault.connect(user).executeAllocation(
      strategyId,
      amount,
      amount,
      await futureDeadline(),
      "0x"
    );

    const tx =
      await vault.connect(user).requestStrategyWithdraw(
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
      .find(
        (parsed) =>
          parsed &&
          parsed.name === "StrategyWithdrawalRequested"
      );

    const withdrawalKey = event.args.withdrawalKey;

    await expect(
      vault.connect(user).claimStrategyWithdraw(
        withdrawalKey,
        withdrawn,
        "0x"
      )
    ).to.be.revertedWith("not ready");

    await connector.setWithdrawalsReady(true);

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

    expect(await adapter.totalAssets()).to.equal(
      ethers.parseEther("3")
    );
  });

  it("supports a synchronous connector without changing the vault interface", async function () {
    const {
      user,
      vault,
      adapter,
      strategyId
    } = await deployFixture({ asyncMode: false });

    const amount = ethers.parseEther("3");
    const withdrawn = ethers.parseEther("1");

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

    expect(
      await vault.idleBalanceOf(
        user.address,
        ethers.ZeroAddress
      )
    ).to.equal(withdrawn);

    expect(await adapter.totalAssets()).to.equal(
      ethers.parseEther("2")
    );
  });

  it("rejects connector metadata that does not match deployment expectations", async function () {
    const [owner] = await ethers.getSigners();

    const Manager = await ethers.getContractFactory("StrategyManager");
    const manager = await Manager.deploy(owner.address);

    const Vault = await ethers.getContractFactory("AscendVault");
    const vault = await Vault.deploy(
      owner.address,
      await manager.getAddress()
    );

    const Connector = await ethers.getContractFactory(
      "MockRestakingConnector"
    );
    const connector = await Connector.deploy(
      ethers.ZeroAddress,
      true
    );

    const Adapter = await ethers.getContractFactory(
      "RestakingAdapter"
    );

    await expect(
      Adapter.deploy(
        await vault.getAddress(),
        await connector.getAddress(),
        owner.address,
        true
      )
    ).to.be.revertedWithCustomError(
      Adapter,
      "ConnectorAssetMismatch"
    );

    await expect(
      Adapter.deploy(
        await vault.getAddress(),
        await connector.getAddress(),
        ethers.ZeroAddress,
        false
      )
    ).to.be.revertedWithCustomError(
      Adapter,
      "ConnectorWithdrawalModeMismatch"
    );
  });
});
