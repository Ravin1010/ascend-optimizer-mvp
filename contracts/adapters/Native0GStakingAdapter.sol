// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {IStrategyAdapter} from "../interfaces/IStrategyAdapter.sol";
import {I0GValidator} from "../interfaces/I0GValidator.sol";

/// @title Native0GStakingAdapter
/// @notice Single-validator native 0G delegation adapter for AscendVault.
/// @dev The adapter pools validator shares on behalf of the vault. The vault
///      remains the only execution caller; the off-chain optimizer has no role.
///
///      0G undelegation requires a validator-specific withdrawal fee paid at
///      request time. This reference adapter therefore keeps an explicit,
///      separately-accounted native fee reserve funded through fundFeeReserve().
contract Native0GStakingAdapter is
    IStrategyAdapter,
    Ownable2Step,
    ReentrancyGuard
{
    using Address for address payable;

    address public immutable vault;
    I0GValidator public immutable validator;

    uint256 public feeReserveWei;
    uint256 public totalPendingWithdrawalAmount;
    uint256 public withdrawalNonce;

    mapping(bytes32 requestId => uint256 amount)
        public pendingWithdrawalAmount;

    error ZeroVault();
    error InvalidValidator(address validator);
    error OnlyVault(address caller);
    error ZeroAmount();
    error ZeroMinShares();
    error ZeroMinAmountOut();
    error UnexpectedData();
    error InvalidNativeValue(uint256 expected, uint256 received);
    error InsufficientShares(
        uint256 minimum,
        uint256 received
    );
    error InsufficientFeeReserve(
        uint256 required,
        uint256 available
    );
    error InsufficientQueuedAmount(
        uint256 minimum,
        uint256 queued
    );
    error UnknownWithdrawal(bytes32 requestId);
    error InsufficientWithdrawalLiquidity(
        bytes32 requestId,
        uint256 required,
        uint256 available
    );
    error ZeroRecipient();

    event FeeReserveFunded(
        address indexed funder,
        uint256 amount
    );

    event FeeReserveWithdrawn(
        address indexed recipient,
        uint256 amount
    );

    event Delegated(
        uint256 amount,
        uint256 sharesReceived
    );

    event UndelegationRequested(
        bytes32 indexed requestId,
        uint256 shares,
        uint256 queuedAmount,
        uint256 feePaid
    );

    event UndelegationClaimed(
        bytes32 indexed requestId,
        uint256 amountOut
    );

    modifier onlyVault() {
        if (msg.sender != vault) {
            revert OnlyVault(msg.sender);
        }
        _;
    }

    constructor(
        address initialOwner,
        address vault_,
        address validator_
    ) Ownable(initialOwner) {
        if (vault_ == address(0)) revert ZeroVault();
        if (
            validator_ == address(0)
            || validator_.code.length == 0
        ) {
            revert InvalidValidator(validator_);
        }

        vault = vault_;
        validator = I0GValidator(validator_);
    }

    receive() external payable {
        // Validator withdrawal processing sends native 0G here.
        // Direct transfers are intentionally not counted as fee reserve.
    }

    function inputAsset()
        external
        pure
        override
        returns (address)
    {
        return address(0);
    }

    function isAsyncWithdrawal()
        external
        pure
        override
        returns (bool)
    {
        return true;
    }

    /// @notice Fund the small native reserve used for 0G undelegation fees.
    function fundFeeReserve() external payable {
        if (msg.value == 0) revert ZeroAmount();

        feeReserveWei += msg.value;

        emit FeeReserveFunded(
            msg.sender,
            msg.value
        );
    }

    /// @notice Recover unused fee reserve without touching staking proceeds.
    function withdrawFeeReserve(
        address payable recipient,
        uint256 amount
    )
        external
        onlyOwner
        nonReentrant
    {
        if (recipient == address(0)) revert ZeroRecipient();
        if (amount == 0) revert ZeroAmount();
        if (amount > feeReserveWei) {
            revert InsufficientFeeReserve(
                amount,
                feeReserveWei
            );
        }

        feeReserveWei -= amount;
        recipient.sendValue(amount);

        emit FeeReserveWithdrawn(
            recipient,
            amount
        );
    }

    function withdrawalFeeWei()
        public
        view
        returns (uint256)
    {
        return uint256(
            validator.withdrawalFeeInGwei()
        ) * 1 gwei;
    }

    /// @notice Delegate native 0G to the fixed validator.
    /// @dev Shares are measured from validator state before/after delegation
    ///      instead of trusting an undocumented return-value name.
    function deposit(
        uint256 amount,
        uint256 minShares,
        bytes calldata data
    )
        external
        payable
        override
        onlyVault
        nonReentrant
        returns (uint256 sharesReceived)
    {
        if (data.length != 0) revert UnexpectedData();
        if (amount == 0) revert ZeroAmount();
        if (minShares == 0) revert ZeroMinShares();
        if (msg.value != amount) {
            revert InvalidNativeValue(
                amount,
                msg.value
            );
        }

        (, uint256 beforeShares) =
            validator.getDelegation(address(this));

        validator.delegate{value: amount}(
            address(this)
        );

        (, uint256 afterShares) =
            validator.getDelegation(address(this));

        sharesReceived = afterShares - beforeShares;

        if (sharesReceived < minShares) {
            revert InsufficientShares(
                minShares,
                sharesReceived
            );
        }

        emit Delegated(
            amount,
            sharesReceived
        );
    }

    /// @notice Begin the official 0G undelegation queue flow.
    function requestWithdraw(
        uint256 shares,
        uint256 minAmountOut,
        bytes calldata data
    )
        external
        override
        onlyVault
        nonReentrant
        returns (
            bytes32 requestId,
            uint256 amountOut,
            bool pending
        )
    {
        if (data.length != 0) revert UnexpectedData();
        if (shares == 0) revert ZeroAmount();
        if (minAmountOut == 0) revert ZeroMinAmountOut();

        uint256 fee = withdrawalFeeWei();
        if (feeReserveWei < fee) {
            revert InsufficientFeeReserve(
                fee,
                feeReserveWei
            );
        }

        feeReserveWei -= fee;

        uint256 queuedAmount =
            validator.undelegate{value: fee}(
                address(this),
                shares
            );

        if (queuedAmount < minAmountOut) {
            revert InsufficientQueuedAmount(
                minAmountOut,
                queuedAmount
            );
        }

        uint256 nonce = withdrawalNonce++;
        requestId = keccak256(
            abi.encode(
                address(this),
                address(validator),
                shares,
                queuedAmount,
                nonce
            )
        );

        pendingWithdrawalAmount[requestId] =
            queuedAmount;
        totalPendingWithdrawalAmount +=
            queuedAmount;

        emit UndelegationRequested(
            requestId,
            shares,
            queuedAmount,
            fee
        );

        return (requestId, 0, true);
    }

    /// @notice Process the validator queue and settle one recorded withdrawal.
    function claimWithdraw(
        bytes32 requestId,
        uint256 minAmountOut,
        bytes calldata data
    )
        external
        override
        onlyVault
        nonReentrant
        returns (uint256 amountOut)
    {
        if (data.length != 0) revert UnexpectedData();
        if (minAmountOut == 0) revert ZeroMinAmountOut();

        uint256 expected =
            pendingWithdrawalAmount[requestId];

        if (expected == 0) {
            revert UnknownWithdrawal(requestId);
        }

        if (expected < minAmountOut) {
            revert InsufficientQueuedAmount(
                minAmountOut,
                expected
            );
        }

        // Official 0G validator contracts allow anyone to process matured
        // withdrawals. If this request is not yet mature, no usable liquidity
        // is expected and the transaction reverts without losing the record.
        validator.processWithdrawQueue();

        uint256 available =
            withdrawalLiquidity();

        if (available < expected) {
            revert InsufficientWithdrawalLiquidity(
                requestId,
                expected,
                available
            );
        }

        delete pendingWithdrawalAmount[requestId];
        totalPendingWithdrawalAmount -= expected;

        payable(vault).sendValue(expected);
        amountOut = expected;

        emit UndelegationClaimed(
            requestId,
            amountOut
        );
    }

    /// @notice Native balance available for completed staking withdrawals.
    /// @dev The explicit fee reserve is excluded from user withdrawal liquidity.
    function withdrawalLiquidity()
        public
        view
        returns (uint256)
    {
        uint256 balance = address(this).balance;

        if (balance <= feeReserveWei) {
            return 0;
        }

        return balance - feeReserveWei;
    }

    function totalAssets()
        external
        view
        override
        returns (uint256)
    {
        (, uint256 shares) =
            validator.getDelegation(address(this));

        return (
            validator.convertToTokens(shares)
            + totalPendingWithdrawalAmount
        );
    }

    function previewRedeem(uint256 shares)
        external
        view
        override
        returns (uint256 amountOut)
    {
        return validator.convertToTokens(shares);
    }
}
