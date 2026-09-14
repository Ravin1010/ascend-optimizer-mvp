// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IStrategyAdapter} from "../interfaces/IStrategyAdapter.sol";

contract MockStrategyAdapter is IStrategyAdapter {
    address public immutable override inputAsset;
    bool public immutable override isAsyncWithdrawal;

    uint256 public assets;

    constructor(address asset_, bool async_) {
        inputAsset = asset_;
        isAsyncWithdrawal = async_;
    }

    function deposit(
        uint256 amount,
        uint256 minShares,
        bytes calldata
    ) external payable override returns (uint256 sharesReceived) {
        sharesReceived = amount;
        require(sharesReceived >= minShares, "min shares");
        assets += amount;
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
        if (isAsyncWithdrawal) {
            return (
                keccak256(abi.encode(msg.sender, shares, assets)),
                0,
                true
            );
        }

        require(shares >= minAmountOut, "min amount");
        assets -= shares;
        return (bytes32(0), shares, false);
    }

    function claimWithdraw(
        bytes32,
        uint256 minAmountOut,
        bytes calldata
    ) external override returns (uint256 amountOut) {
        require(isAsyncWithdrawal, "not async");
        amountOut = minAmountOut;
        if (amountOut <= assets) {
            assets -= amountOut;
        }
    }

    function totalAssets() external view override returns (uint256) {
        return assets;
    }

    function previewRedeem(uint256 shares)
        external
        pure
        override
        returns (uint256 amountOut)
    {
        return shares;
    }
}
