// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Burnable} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

contract MockGimoSt0G is ERC20, ERC20Burnable {
    uint256 public constant RATE_SCALE = 1e18;

    address public immutable minter;
    uint256 private _rate = RATE_SCALE;

    error OnlyMinter();
    error InvalidRate();

    constructor(address minter_)
        ERC20("Mock Gimo st0G", "mst0G")
    {
        minter = minter_;
    }

    function getRate()
        external
        view
        returns (uint256)
    {
        return _rate;
    }

    function mint(address to, uint256 amount)
        external
    {
        if (msg.sender != minter) revert OnlyMinter();
        _mint(to, amount);
    }

    function setRate(uint256 rate_)
        external
    {
        if (msg.sender != minter) revert OnlyMinter();
        if (rate_ == 0) revert InvalidRate();
        _rate = rate_;
    }
}

contract MockGimoStakePool {
    using Address for address payable;

    uint256 public constant RATE_SCALE = 1e18;

    MockGimoSt0G public immutable st0g;

    bool public withdrawalsReady;

    mapping(address account => uint256 amount)
        public pendingNative;

    string public lastReferral;

    constructor() {
        st0g = new MockGimoSt0G(
            address(this)
        );
    }

    receive() external payable {}

    function stake(string calldata referral)
        external
        payable
    {
        require(msg.value > 0, "zero stake");

        uint256 rate = st0g.getRate();
        uint256 shares = Math.mulDiv(
            msg.value,
            RATE_SCALE,
            rate
        );

        require(shares > 0, "zero shares");

        lastReferral = referral;
        st0g.mint(msg.sender, shares);
    }

    function unstake(uint256 st0gAmount)
        external
    {
        require(st0gAmount > 0, "zero unstake");

        uint256 rate = st0g.getRate();
        uint256 nativeAmount = Math.mulDiv(
            st0gAmount,
            rate,
            RATE_SCALE
        );

        st0g.burnFrom(
            msg.sender,
            st0gAmount
        );

        pendingNative[msg.sender] +=
            nativeAmount;
    }

    function withdraw() external {
        require(
            withdrawalsReady,
            "not ready"
        );

        uint256 amount =
            pendingNative[msg.sender];

        require(amount > 0, "nothing pending");

        pendingNative[msg.sender] = 0;

        payable(msg.sender).sendValue(
            amount
        );
    }

    function setRate(uint256 rate)
        external
    {
        st0g.setRate(rate);
    }

    function fundRewards()
        external
        payable
    {}

    function setWithdrawalsReady(bool ready)
        external
    {
        withdrawalsReady = ready;
    }
}
