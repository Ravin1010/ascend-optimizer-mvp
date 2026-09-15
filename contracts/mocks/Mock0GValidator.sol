// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";

import {I0GValidator} from "../interfaces/I0GValidator.sol";

contract Mock0GValidator is I0GValidator {
    using Address for address payable;

    struct Pending {
        address recipient;
        uint256 amount;
        bool active;
    }

    uint96 public override withdrawalFeeInGwei;
    bool public withdrawalsReady;

    uint256 public totalDelegated;
    uint256 public pendingCount;

    mapping(address delegator => uint256 shares)
        public sharesOf;

    mapping(uint256 index => Pending)
        public pendingAt;

    constructor(uint96 withdrawalFeeInGwei_) {
        withdrawalFeeInGwei = withdrawalFeeInGwei_;
    }

    function delegate(address delegatorAddress)
        external
        payable
        override
        returns (uint256)
    {
        require(msg.value > 0, "zero delegation");

        sharesOf[delegatorAddress] += msg.value;
        totalDelegated += msg.value;

        return msg.value;
    }

    function undelegate(
        address withdrawalAddress,
        uint256 shares
    )
        external
        payable
        override
        returns (uint256)
    {
        uint256 requiredFee =
            uint256(withdrawalFeeInGwei) * 1 gwei;

        require(msg.value == requiredFee, "withdrawal fee");
        require(sharesOf[msg.sender] >= shares, "insufficient shares");

        sharesOf[msg.sender] -= shares;
        totalDelegated -= shares;

        pendingAt[pendingCount++] = Pending({
            recipient: withdrawalAddress,
            amount: shares,
            active: true
        });

        return shares;
    }

    function getDelegation(address delegator)
        external
        view
        override
        returns (address validatorAddress, uint256 shares)
    {
        return (
            address(this),
            sharesOf[delegator]
        );
    }

    function convertToTokens(uint256 shares)
        external
        pure
        override
        returns (uint256)
    {
        return shares;
    }

    function processWithdrawQueue()
        external
        override
    {
        if (!withdrawalsReady) {
            return;
        }

        for (uint256 i = 0; i < pendingCount; ++i) {
            Pending storage item = pendingAt[i];

            if (!item.active) continue;

            item.active = false;
            payable(item.recipient).sendValue(
                item.amount
            );
        }
    }

    function setWithdrawalsReady(bool ready) external {
        withdrawalsReady = ready;
    }

    receive() external payable {}
}
