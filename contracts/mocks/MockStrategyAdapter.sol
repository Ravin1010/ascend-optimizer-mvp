// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IStrategyAdapter} from "../interfaces/IStrategyAdapter.sol";

contract MockStrategyAdapter is IStrategyAdapter {
    using Address for address payable;
    using SafeERC20 for IERC20;

    address public immutable override inputAsset;
    bool public immutable override isAsyncWithdrawal;

    uint256 public assets;
    uint256 public requestNonce;

    mapping(bytes32 requestId => uint256 amount)
        public pendingAmount;

    constructor(address asset_, bool async_) {
        inputAsset = asset_;
        isAsyncWithdrawal = async_;
    }

    function deposit(
        uint256 amount,
        uint256 minShares,
        bytes calldata
    ) external payable override returns (uint256 sharesReceived) {
        if (inputAsset == address(0)) {
            require(msg.value == amount, "native value");
        } else {
            require(msg.value == 0, "unexpected native");
            IERC20(inputAsset).safeTransferFrom(
                msg.sender,
                address(this),
                amount
            );
        }

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
        require(shares <= assets, "insufficient assets");
        require(shares >= minAmountOut, "min amount");

        if (isAsyncWithdrawal) {
            requestId = keccak256(
                abi.encode(
                    address(this),
                    msg.sender,
                    shares,
                    requestNonce++
                )
            );
            pendingAmount[requestId] = shares;

            return (requestId, 0, true);
        }

        assets -= shares;
        _sendAsset(msg.sender, shares);

        return (bytes32(0), shares, false);
    }

    function claimWithdraw(
        bytes32 requestId,
        uint256 minAmountOut,
        bytes calldata
    ) external override returns (uint256 amountOut) {
        require(isAsyncWithdrawal, "not async");

        amountOut = pendingAmount[requestId];
        require(amountOut > 0, "unknown request");
        require(amountOut >= minAmountOut, "min amount");

        delete pendingAmount[requestId];
        assets -= amountOut;

        _sendAsset(msg.sender, amountOut);
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

    function _sendAsset(
        address recipient,
        uint256 amount
    ) private {
        if (inputAsset == address(0)) {
            payable(recipient).sendValue(amount);
        } else {
            IERC20(inputAsset).safeTransfer(
                recipient,
                amount
            );
        }
    }
}
