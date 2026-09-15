// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {A0GToken} from "../A0GToken.sol";
import {I0GValidator} from "../interfaces/I0GValidator.sol";
import {IStrategyAdapter} from "../interfaces/IStrategyAdapter.sol";

/// @title AscendStakingAdapter
/// @notice Native 0G staking adapter backing Ascend's non-rebasing a0G principal.
/// @dev Vault-managed positions mint a0G 1:1 to this adapter, not to the user.
///      Vault strategy shares therefore equal a0G principal units.
///
///      Validator yield is deliberately excluded from a0G principal redemption.
///      Separately realized/notified rewards belong in RewardAccounting instead
///      of silently increasing a0G's exchange rate.
contract AscendStakingAdapter is
    IStrategyAdapter,
    Ownable2Step,
    ReentrancyGuard
{
    using Address for address payable;

    address public immutable vault;
    I0GValidator public immutable validator;
    A0GToken public immutable a0g;

    uint256 public feeReserveWei;
    uint256 public totalPrincipalShares;
    uint256 public totalPendingWithdrawalAmount;
    uint256 public withdrawalNonce;

    mapping(bytes32 requestId => uint256 amount)
        public pendingWithdrawalAmount;

    error ZeroVault();
    error InvalidValidator(address validator);
    error InvalidA0GToken(address token);
    error OnlyVault(address caller);
    error ZeroAmount();
    error ZeroMinShares();
    error ZeroMinAmountOut();
    error UnexpectedData();
    error InvalidNativeValue(uint256 expected, uint256 received);
    error InsufficientShares(uint256 minimum, uint256 received);
    error InsufficientPrincipalShares(uint256 available, uint256 requested);
    error InsufficientRedeemableAmount(uint256 minimum, uint256 redeemable);
    error InsufficientValidatorShares(uint256 targetAmount);
    error PrincipalAmountExceeded(uint256 maximumPrincipal, uint256 queuedAmount);
    error InsufficientFeeReserve(uint256 required, uint256 available);
    error InsufficientQueuedAmount(uint256 minimum, uint256 queued);
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

    event AscendStaked(
        uint256 amount,
        uint256 validatorSharesReceived,
        uint256 a0gMinted
    );

    event AscendUnstakeRequested(
        bytes32 indexed requestId,
        uint256 a0gBurned,
        uint256 validatorShares,
        uint256 queuedPrincipal,
        uint256 feePaid
    );

    event AscendUnstakeClaimed(
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
        address validator_,
        address a0g_
    ) Ownable(initialOwner) {
        if (vault_ == address(0)) revert ZeroVault();
        if (
            validator_ == address(0)
            || validator_.code.length == 0
        ) {
            revert InvalidValidator(validator_);
        }
        if (
            a0g_ == address(0)
            || a0g_.code.length == 0
        ) {
            revert InvalidA0GToken(a0g_);
        }

        vault = vault_;
        validator = I0GValidator(validator_);
        a0g = A0GToken(a0g_);
    }

    receive() external payable {
        // Mature validator withdrawals are received here.
        // Direct transfers are not counted as fee reserve.
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

    /// @notice Whether A0GToken currently authorizes this adapter to mint/burn.
    function issuerConfigured()
        external
        view
        returns (bool)
    {
        return a0g.hasRole(
            a0g.ISSUER_ROLE(),
            address(this)
        );
    }

    function fundFeeReserve() external payable {
        if (msg.value == 0) revert ZeroAmount();

        feeReserveWei += msg.value;

        emit FeeReserveFunded(
            msg.sender,
            msg.value
        );
    }

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

    /// @notice Stake native 0G and mint adapter-held a0G principal 1:1.
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

        sharesReceived = amount;

        if (sharesReceived < minShares) {
            revert InsufficientShares(
                minShares,
                sharesReceived
            );
        }

        (, uint256 beforeValidatorShares) =
            validator.getDelegation(address(this));

        validator.delegate{value: amount}(
            address(this)
        );

        (, uint256 afterValidatorShares) =
            validator.getDelegation(address(this));

        uint256 validatorSharesReceived =
            afterValidatorShares - beforeValidatorShares;

        if (validatorSharesReceived == 0) {
            revert InsufficientValidatorShares(amount);
        }

        totalPrincipalShares += amount;
        a0g.mint(address(this), amount);

        emit AscendStaked(
            amount,
            validatorSharesReceived,
            amount
        );
    }

    /// @notice Request principal redemption while keeping staking yield outside
    ///         the non-rebasing a0G principal value.
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

        uint256 principalBefore = totalPrincipalShares;
        if (shares > principalBefore) {
            revert InsufficientPrincipalShares(
                principalBefore,
                shares
            );
        }

        (
            uint256 validatorShares,
            uint256 activeAssets
        ) = _activeStake();

        uint256 redeemable =
            _previewRedeemFromTotals(
                shares,
                principalBefore,
                activeAssets
            );

        if (redeemable < minAmountOut) {
            revert InsufficientRedeemableAmount(
                minAmountOut,
                redeemable
            );
        }

        uint256 validatorSharesToRedeem =
            Math.mulDiv(
                validatorShares,
                redeemable,
                activeAssets
            );

        if (validatorSharesToRedeem == 0) {
            revert InsufficientValidatorShares(
                redeemable
            );
        }

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
                validatorSharesToRedeem
            );

        if (queuedAmount < minAmountOut) {
            revert InsufficientQueuedAmount(
                minAmountOut,
                queuedAmount
            );
        }

        // a0G represents principal only. If a validator conversion would put
        // reward value into this principal withdrawal, reject the operation.
        if (queuedAmount > redeemable) {
            revert PrincipalAmountExceeded(
                redeemable,
                queuedAmount
            );
        }

        totalPrincipalShares =
            principalBefore - shares;
        a0g.burn(address(this), shares);

        uint256 nonce = withdrawalNonce++;
        requestId = keccak256(
            abi.encode(
                address(this),
                address(validator),
                shares,
                validatorSharesToRedeem,
                queuedAmount,
                nonce
            )
        );

        pendingWithdrawalAmount[requestId] =
            queuedAmount;
        totalPendingWithdrawalAmount +=
            queuedAmount;

        emit AscendUnstakeRequested(
            requestId,
            shares,
            validatorSharesToRedeem,
            queuedAmount,
            fee
        );

        return (requestId, 0, true);
    }

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

        emit AscendUnstakeClaimed(
            requestId,
            amountOut
        );
    }

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

    /// @notice Total managed staking value, including rewards and pending exits.
    /// @dev Reward value may exceed totalPrincipalShares but does not increase
    ///      a0G principal redemption.
    function totalAssets()
        external
        view
        override
        returns (uint256)
    {
        (, uint256 activeAssets) =
            _activeStake();

        return (
            activeAssets
            + totalPendingWithdrawalAmount
        );
    }

    /// @notice Principal redemption value for a0G strategy shares.
    /// @dev Upside from validator rewards is capped out. Slashing can reduce
    ///      principal value pro rata.
    function previewRedeem(uint256 shares)
        external
        view
        override
        returns (uint256 amountOut)
    {
        if (shares == 0 || totalPrincipalShares == 0) {
            return 0;
        }

        (, uint256 activeAssets) =
            _activeStake();

        return _previewRedeemFromTotals(
            shares,
            totalPrincipalShares,
            activeAssets
        );
    }

    function _activeStake()
        private
        view
        returns (
            uint256 validatorShares,
            uint256 activeAssets
        )
    {
        (, validatorShares) =
            validator.getDelegation(address(this));

        activeAssets =
            validator.convertToTokens(
                validatorShares
            );
    }

    function _previewRedeemFromTotals(
        uint256 shares,
        uint256 principal,
        uint256 activeAssets
    )
        private
        pure
        returns (uint256)
    {
        if (
            shares == 0
            || principal == 0
            || activeAssets == 0
        ) {
            return 0;
        }

        uint256 proRataBacking =
            Math.mulDiv(
                shares,
                activeAssets,
                principal
            );

        return Math.min(
            shares,
            proRataBacking
        );
    }
}
