const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("A0GToken", function () {
  async function deployFixture() {
    const [admin, adapter, user, attacker] = await ethers.getSigners();

    const Token = await ethers.getContractFactory("A0GToken");
    const token = await Token.deploy(admin.address, adapter.address);

    return { admin, adapter, user, attacker, token };
  }

  it("allows only the staking adapter to mint and burn", async function () {
    const { adapter, user, attacker, token } = await deployFixture();

    await token.connect(adapter).mint(user.address, 1000);
    expect(await token.balanceOf(user.address)).to.equal(1000n);

    await expect(
      token.connect(attacker).mint(attacker.address, 1)
    ).to.be.reverted;

    await token.connect(adapter).burn(user.address, 400);
    expect(await token.balanceOf(user.address)).to.equal(600n);
  });

  it("can permanently remove the deployment admin's role", async function () {
    const { admin, adapter, attacker, token } = await deployFixture();

    const adminRole = await token.DEFAULT_ADMIN_ROLE();
    const issuerRole = await token.ISSUER_ROLE();

    await token
      .connect(admin)
      .renounceRole(adminRole, admin.address);

    expect(await token.hasRole(adminRole, admin.address)).to.equal(false);
    expect(await token.hasRole(issuerRole, adapter.address)).to.equal(true);

    await expect(
      token.connect(admin).grantRole(issuerRole, attacker.address)
    ).to.be.reverted;
  });
});
