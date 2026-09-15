// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";

import {IRestakingConnector} from "../interfaces/IRestakingConnector.sol";

contract MockRestakingConnector is IRestakingConnector {
    using Address for address payable;

    address public immutable override inputAsset;
    bool public immutable override isAsyncWithdrawal;

    uint256 public managedAssets;
    uint256 public nonce;
    bool public withdrawalsReady;

    mapping(bytes32 requestId => uint256 amount)
        public pendingAmount;

    constructor(
        address inputAsset_,
        bool async_
    ) {
        inputAsset = inputAsset_;
        isAsyncWithdrawal = async_;
    }

    receive() external payable {}

    function deposit(
        uint256 amount,
        uint256 minShares,
        bytes calldata
    )
        external
        payable
        override
        returns (uint256 sharesReceived)
    {
        require(inputAsset == address(0), "native only");
        require(msg.value == amount, "value");
        require(amount >= minShares, "min shares");

        managedAssets += amount;
        return amount;
    }

    function requestWithdraw(
        uint256 shares,
        uint256 minAmountOut,
        bytes calldata
    )
        external
        override
        returns (
            bytes32 requestId,
            uint256 amountOut,
            bool pending
        )
    {
        require(shares >= minAmountOut, "min out");
        require(managedAssets >= shares, "assets");

        managedAssets -= shares;

        if (!isAsyncWithdrawal) {
            payable(msg.sender).sendValue(shares);
            return (bytes32(0), shares, false);
        }

        requestId = keccak256(
            abi.encode(
                address(this),
                shares,
                nonce++
            )
        );

        pendingAmount[requestId] = shares;

        return (requestId, 0, true);
    }

    function claimWithdraw(
        bytes32 requestId,
        uint256 minAmountOut,
        bytes calldata
    )
        external
        override
        returns (uint256 amountOut)
    {
        require(withdrawalsReady, "not ready");

        uint256 amount =
            pendingAmount[requestId];

        require(amount != 0, "unknown");
        require(amount >= minAmountOut, "min out");

        delete pendingAmount[requestId];

        payable(msg.sender).sendValue(amount);
        return amount;
    }

    function totalAssets()
        external
        view
        override
        returns (uint256)
    {
        return managedAssets;
    }

    function previewRedeem(uint256 shares)
        external
        pure
        override
        returns (uint256 amountOut)
    {
        return shares;
    }

    function setWithdrawalsReady(bool ready)
        external
    {
        withdrawalsReady = ready;
    }
}
