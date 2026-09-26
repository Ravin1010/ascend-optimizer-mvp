// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {
    IAscendSourceCore,
    IAscendWithdrawalQueue,
    IAscendW0G
} from "../interfaces/IAscendProtocol.sol";
import {IStrategyAdapter} from "../interfaces/IStrategyAdapter.sol";

/// @title AscendProtocolAdapter
/// @notice Adapter from AscendVault into the live Ascend a0G SourceCore vault.
/// @dev Native 0G is wrapped to W0G and deposited into Ascend's live ERC-4626
///      SourceCore. Strategy shares are the actual a0G shares received.
///
///      a0G is exchange-rate-bearing. Validator/restaking yield is therefore
///      embedded in a0G share value and MUST NOT also be notified through
///      RewardAccounting.
///
///      Live Ascend withdrawals are asynchronous and epoch based. SourceCore
///      transfers requested a0G shares into Mellow's WithdrawalQueue; once an
///      epoch is processed, claim(epoch, receiver) releases W0G. Multiple vault
///      users may request in the same protocol epoch, so this adapter tracks the
///      adapter-wide epoch claim and distributes its assets pro rata across the
///      corresponding AscendVault withdrawal requests.
contract AscendProtocolAdapter is
    IStrategyAdapter,
    ReentrancyGuard
{
    using Address for address payable;
    using SafeERC20 for IAscendW0G;

    address public immutable vault;
    IAscendSourceCore public immutable sourceCore;
    IAscendWithdrawalQueue public immutable withdrawalQueue;
    IAscendW0G public immutable w0g;

    uint256 public withdrawalNonce;

    /// @dev Conservative accounting estimate while protocol requests are
    ///      pending. Final claim values are determined by the protocol epoch.
    uint256 public pendingWithdrawalEstimate;

    struct PendingRequest {
        uint256 epoch;
        uint256 shares;
        uint256 quotedAssets;
        bool active;
    }

    struct EpochState {
        uint256 totalShares;
        uint256 remainingShares;
        uint256 claimedAssets;
        uint256 remainingAssets;
        bool settled;
    }

    mapping(bytes32 requestId => PendingRequest)
        public pendingRequestOf;

    mapping(uint256 epoch => EpochState)
        public epochStateOf;

    error ZeroVault();
    error InvalidContract(address target);
    error AssetMismatch(address expected, address actual);
    error InvalidWithdrawalQueue(address queue);
    error QueueSourceMismatch(address expected, address actual);
    error QueueAssetMismatch(address expected, address actual);
    error OnlyVault(address caller);
    error ZeroAmount();
    error ZeroMinShares();
    error ZeroMinAmountOut();
    error UnexpectedData();
    error InvalidNativeValue(uint256 expected, uint256 received);
    error InsufficientShares(uint256 minimum, uint256 received);
    error InsufficientA0GShares(uint256 available, uint256 requested);
    error InsufficientRedeemableAmount(uint256 minimum, uint256 redeemable);
    error UnknownWithdrawal(bytes32 requestId);
    error WithdrawalNotReady(uint256 epoch);
    error ProtocolClaimMismatch(uint256 reported, uint256 received);
    error InvalidEpochAccounting(uint256 epoch);
    error InsufficientWithdrawalAmount(uint256 minimum, uint256 received);

    event AscendProtocolDeposited(
        uint256 amount0G,
        uint256 a0gSharesReceived
    );

    event AscendProtocolWithdrawalRequested(
        bytes32 indexed requestId,
        uint256 indexed epoch,
        uint256 a0gShares,
        uint256 quotedAssets
    );

    event AscendProtocolEpochSettled(
        uint256 indexed epoch,
        uint256 totalShares,
        uint256 assetsReceived
    );

    event AscendProtocolWithdrawalClaimed(
        bytes32 indexed requestId,
        uint256 indexed epoch,
        uint256 amount0G
    );

    modifier onlyVault() {
        if (msg.sender != vault) {
            revert OnlyVault(msg.sender);
        }
        _;
    }

    constructor(
        address vault_,
        address sourceCore_,
        address w0g_
    ) {
        if (vault_ == address(0)) {
            revert ZeroVault();
        }

        _requireContract(sourceCore_);
        _requireContract(w0g_);

        IAscendSourceCore source =
            IAscendSourceCore(sourceCore_);

        address actualAsset =
            source.asset();

        if (actualAsset != w0g_) {
            revert AssetMismatch(
                w0g_,
                actualAsset
            );
        }

        address queueAddress =
            source.withdrawalQueue();

        _requireContract(queueAddress);

        IAscendWithdrawalQueue queue =
            IAscendWithdrawalQueue(queueAddress);

        address queueSource =
            queue.sourceCore();

        if (queueSource != sourceCore_) {
            revert QueueSourceMismatch(
                sourceCore_,
                queueSource
            );
        }

        address queueAsset =
            queue.asset();

        if (queueAsset != w0g_) {
            revert QueueAssetMismatch(
                w0g_,
                queueAsset
            );
        }

        vault = vault_;
        sourceCore = source;
        withdrawalQueue = queue;
        w0g = IAscendW0G(w0g_);
    }

    receive() external payable {
        // W0G.unwrap() returns native 0G here.
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

        w0g.deposit{value: amount}();

        uint256 beforeShares =
            sourceCore.balanceOf(address(this));

        w0g.forceApprove(
            address(sourceCore),
            amount
        );

        sourceCore.deposit(
            amount,
            address(this)
        );

        w0g.forceApprove(
            address(sourceCore),
            0
        );

        uint256 afterShares =
            sourceCore.balanceOf(address(this));

        sharesReceived =
            afterShares - beforeShares;

        if (sharesReceived < minShares) {
            revert InsufficientShares(
                minShares,
                sharesReceived
            );
        }

        emit AscendProtocolDeposited(
            amount,
            sharesReceived
        );
    }

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

        uint256 available =
            sourceCore.balanceOf(address(this));

        if (available < shares) {
            revert InsufficientA0GShares(
                available,
                shares
            );
        }

        uint256 quotedAssets =
            sourceCore.previewRedeem(shares);

        if (quotedAssets < minAmountOut) {
            revert InsufficientRedeemableAmount(
                minAmountOut,
                quotedAssets
            );
        }

        sourceCore.requestWithdrawal(
            shares
        );

        uint256 epoch =
            withdrawalQueue.currentEpoch();

        EpochState storage epochState =
            epochStateOf[epoch];

        if (epochState.settled) {
            revert InvalidEpochAccounting(
                epoch
            );
        }

        epochState.totalShares += shares;
        epochState.remainingShares += shares;

        uint256 nonce =
            withdrawalNonce++;

        requestId = keccak256(
            abi.encode(
                address(this),
                address(sourceCore),
                epoch,
                shares,
                nonce
            )
        );

        pendingRequestOf[requestId] =
            PendingRequest({
                epoch: epoch,
                shares: shares,
                quotedAssets: quotedAssets,
                active: true
            });

        pendingWithdrawalEstimate +=
            quotedAssets;

        emit AscendProtocolWithdrawalRequested(
            requestId,
            epoch,
            shares,
            quotedAssets
        );

        return (
            requestId,
            0,
            true
        );
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

        PendingRequest memory request =
            pendingRequestOf[requestId];

        if (!request.active) {
            revert UnknownWithdrawal(
                requestId
            );
        }

        EpochState storage epochState =
            epochStateOf[request.epoch];

        if (!epochState.settled) {
            _settleEpoch(
                request.epoch,
                epochState
            );
        }

        amountOut = _consumeEpochClaim(
            request,
            epochState
        );

        if (amountOut < minAmountOut) {
            revert InsufficientWithdrawalAmount(
                minAmountOut,
                amountOut
            );
        }

        delete pendingRequestOf[requestId];

        uint256 estimate =
            request.quotedAssets;

        if (estimate >= pendingWithdrawalEstimate) {
            pendingWithdrawalEstimate = 0;
        } else {
            pendingWithdrawalEstimate -=
                estimate;
        }

        w0g.withdraw(
            amountOut
        );

        payable(vault).sendValue(
            amountOut
        );

        emit AscendProtocolWithdrawalClaimed(
            requestId,
            request.epoch,
            amountOut
        );
    }

    function totalAssets()
        external
        view
        override
        returns (uint256)
    {
        uint256 activeShares =
            sourceCore.balanceOf(address(this));

        uint256 activeAssets =
            activeShares == 0
                ? 0
                : sourceCore.previewRedeem(
                    activeShares
                );

        return (
            activeAssets
            + pendingWithdrawalEstimate
        );
    }

    function previewRedeem(uint256 shares)
        external
        view
        override
        returns (uint256 amountOut)
    {
        if (shares == 0) {
            return 0;
        }

        return sourceCore.previewRedeem(
            shares
        );
    }

    function _settleEpoch(
        uint256 epoch,
        EpochState storage state
    )
        private
    {
        if (
            state.totalShares == 0
            || state.remainingShares == 0
        ) {
            revert InvalidEpochAccounting(
                epoch
            );
        }

        uint256 beforeBalance =
            w0g.balanceOf(address(this));

        uint256 reported =
            withdrawalQueue.claim(
                epoch,
                address(this)
            );

        uint256 received =
            w0g.balanceOf(address(this))
            - beforeBalance;

        if (
            reported == 0
            || received == 0
        ) {
            revert WithdrawalNotReady(
                epoch
            );
        }

        if (reported != received) {
            revert ProtocolClaimMismatch(
                reported,
                received
            );
        }

        state.settled = true;
        state.claimedAssets = received;
        state.remainingAssets = received;

        emit AscendProtocolEpochSettled(
            epoch,
            state.totalShares,
            received
        );
    }

    function _consumeEpochClaim(
        PendingRequest memory request,
        EpochState storage state
    )
        private
        returns (uint256 amountOut)
    {
        if (
            request.shares == 0
            || request.shares > state.remainingShares
            || state.totalShares == 0
        ) {
            revert InvalidEpochAccounting(
                request.epoch
            );
        }

        if (
            request.shares
                == state.remainingShares
        ) {
            amountOut =
                state.remainingAssets;
        } else {
            amountOut = Math.mulDiv(
                state.claimedAssets,
                request.shares,
                state.totalShares
            );
        }

        if (
            amountOut == 0
            || amountOut > state.remainingAssets
        ) {
            revert InvalidEpochAccounting(
                request.epoch
            );
        }

        state.remainingShares -=
            request.shares;

        state.remainingAssets -=
            amountOut;
    }

    function _requireContract(
        address target
    )
        private
        view
    {
        if (
            target == address(0)
            || target.code.length == 0
        ) {
            revert InvalidContract(
                target
            );
        }
    }
}
